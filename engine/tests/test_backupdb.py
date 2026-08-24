#!/usr/bin/env python3
"""Regression coverage for safeguard.py's backupdb() (recommendations annex #1: backup-dr). Per
docs/MASTER-RECONCILIATION.md's own "still open" list, backupdb() was "documented, manual, still
never actually run" -- this proves it end to end against a real, nontrivial SQLite DB: a genuine
VACUUM INTO backup, disk-space guard, rotation, and a full corrupt-then-recover round-trip that
restores identical row-level content. Never touches the real project (patches safeguard's module-
level ROOT/DB_BACKUP_DIR the same way test_truncation.py does). Pure stdlib runner."""
import hashlib
import os
import shutil
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE)
import safeguard as SG


def _build_real_db(path):
    """A nontrivial DB -- several tables, an index, several thousand rows -- so VACUUM INTO exercises
    real B-tree/page structure, not an empty schema."""
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE documents(id INTEGER PRIMARY KEY, tm_number TEXT, vehicle TEXT)")
    con.execute("CREATE TABLE pages(id INTEGER PRIMARY KEY, document_id INTEGER, body_text TEXT)")
    con.execute("CREATE INDEX ix_pages_doc ON pages(document_id)")
    con.executemany("INSERT INTO documents VALUES(?,?,?)",
                     [(i, "TM 9-%04d-%03d-24" % (2000 + i, 100 + i), "HMMWV") for i in range(1, 51)])
    con.executemany("INSERT INTO pages(document_id, body_text) VALUES(?,?)",
                     [((i % 50) + 1, "Page body text for row %d with some repeated padding content "
                                      "so the page is a realistic size not a one-liner." % i)
                      for i in range(4000)])
    con.commit()
    con.close()


def _row_checksum(db_path):
    """A content fingerprint independent of file bytes (VACUUM INTO legitimately reorders pages, so
    comparing raw file bytes between source and backup would be the wrong check) -- hash every row
    of every real table, order-independent."""
    con = sqlite3.connect(db_path)
    h = hashlib.sha256()
    for table in ("documents", "pages"):
        rows = con.execute("SELECT * FROM %s ORDER BY id" % table).fetchall()
        for row in rows:
            h.update(repr(row).encode("utf-8"))
    con.close()
    return h.hexdigest()


def _zero_header(db_path):
    b = bytearray(open(db_path, "rb").read())
    b[0:16] = b"\x00" * 16
    open(db_path, "wb").write(bytes(b))


def run():
    passed, failed = [], []

    def check(name, cond):
        (passed if cond else failed).append(name)

    root = tempfile.mkdtemp(prefix="backupdb_test_")
    orig_root, orig_dbdir = SG.ROOT, SG.DB_BACKUP_DIR
    try:
        os.makedirs(os.path.join(root, "index"), exist_ok=True)
        db = os.path.join(root, "index", "viewer.db")
        _build_real_db(db)
        dest_dir = os.path.join(root, "backups", "db")
        SG.ROOT = root
        SG.DB_BACKUP_DIR = dest_dir

        baseline_checksum = _row_checksum(db)

        # ---- a genuine backup round-trip -----------------------------------------------------
        out1 = SG.backupdb(db=db, dest_dir=dest_dir, keep=2)
        check("backupdb() actually wrote a file", os.path.exists(out1))
        check("the backup passes its own integrity check", SG.db_integrity(out1) == "ok")
        check("the backup's row content matches the source exactly (VACUUM INTO can reorder pages, "
              "so this checks rows, not raw file bytes)", _row_checksum(out1) == baseline_checksum)

        # ---- disk-space guard: must refuse, not attempt a doomed copy ------------------------
        real_disk_usage = shutil.disk_usage

        class _FakeUsage:
            def __init__(self, free):
                self.free = free
        shutil.disk_usage = lambda path: _FakeUsage(1)   # 1 byte free -- nowhere near 1.3x the DB
        try:
            raised = False
            try:
                SG.backupdb(db=db, dest_dir=dest_dir, keep=2)
            except RuntimeError as e:
                raised = "disk" in str(e).lower() or "free" in str(e).lower()
            check("backupdb() refuses to start when free disk is far below 1.3x the DB size",
                  raised)
        finally:
            shutil.disk_usage = real_disk_usage
        check("a refused backup leaves no partial file behind",
              all(not f.endswith(".db-journal") and "partial" not in f for f in os.listdir(dest_dir)))

        # ---- rotation: keep=2 means a 3rd backup prunes the oldest -----------------------------
        import time
        time.sleep(1.1)   # backupdb()'s filename is minute-granular; force a distinct mtime/name
        out2 = SG.backupdb(db=db, dest_dir=dest_dir, keep=2)
        check("a second backup into the same dir is a distinct file", out2 != out1)
        copies_after_2 = sorted(f for f in os.listdir(dest_dir) if f.startswith("viewer-") and f.endswith(".db"))
        check("with keep=2, two backups means both are still present", len(copies_after_2) == 2)

        time.sleep(1.1)
        out3 = SG.backupdb(db=db, dest_dir=dest_dir, keep=2)
        copies_after_3 = sorted(f for f in os.listdir(dest_dir) if f.startswith("viewer-") and f.endswith(".db"))
        check("with keep=2, a third backup rotates out the oldest -- exactly 2 remain",
              len(copies_after_3) == 2)
        check("the newest backup (out3) survives rotation", os.path.basename(out3) in copies_after_3)

        # ---- the actual disaster-recovery scenario this whole fix exists for -------------------
        latest_backup = max((os.path.join(dest_dir, f) for f in copies_after_3),
                             key=os.path.getmtime)
        _zero_header(db)
        corrupted = SG.db_integrity(db)
        check("the corrupted source DB is genuinely detected as bad", corrupted != "ok")
        shutil.copyfile(latest_backup, db)   # the actual recovery action a unit admin would take
        recovered = SG.db_integrity(db)
        check("after restoring from the backup, integrity check passes again", recovered == "ok")
        check("after restoring from the backup, the row content is identical to the original",
              _row_checksum(db) == baseline_checksum)
    finally:
        SG.ROOT, SG.DB_BACKUP_DIR = orig_root, orig_dbdir
        shutil.rmtree(root, ignore_errors=True)

    return passed, failed


if __name__ == "__main__":
    p, f = run()
    for n in p:
        print("PASS", n)
    for n in f:
        print("FAIL", n)
    print("\n%d passed, %d failed" % (len(p), len(f)))
    sys.exit(1 if f else 0)

# END OF FILE
