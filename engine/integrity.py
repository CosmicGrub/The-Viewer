"""integrity.py -- data integrity & recovery for THE VIEWER's databases (R13 resilience). The index and the
sidecars are the app's memory; they must never be silently corrupted or lost. This module provides:

  * integrity_check(db)   -- SQLite PRAGMA integrity_check / quick_check (detects on-disk corruption)
  * checksum(path)        -- streamed SHA-256 of a file (tamper / change evidence)
  * manifest(paths)       -- {path: {size, sha256, mtime}} snapshot of the important DBs
  * verify_manifest       -- compare a saved manifest to disk -> missing / changed / corrupt
  * backup(db, dest)      -- ONLINE-safe SQLite backup (copies a consistent snapshot even while in use)

Read-only except backup() (which only writes a NEW .bak file, never the source). Complements safeguard.py
(the off-disk mirror) by adding corruption detection + tamper-evident checksums. Pure stdlib; unit-testable."""

from __future__ import annotations
import hashlib, os, sqlite3, time


def checksum(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def integrity_check(db_path, quick=True):
    """Returns {ok, result, error?}. quick_check is fast; full integrity_check is thorough (slow on big DBs)."""
    if not os.path.exists(db_path):
        return {"ok": False, "result": "missing", "error": "file not found"}
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
        pragma = "quick_check" if quick else "integrity_check"
        rows = con.execute("PRAGMA %s" % pragma).fetchall()
        con.close()
        res = [r[0] for r in rows]
        return {"ok": res == ["ok"], "result": res}
    except sqlite3.DatabaseError as e:
        return {"ok": False, "result": "corrupt", "error": str(e)}
    except Exception as e:
        return {"ok": False, "result": "error", "error": str(e)}


def manifest(paths):
    """Snapshot the important files -> {path: {size, sha256, mtime, integrity}}. Skips missing files."""
    out = {}
    for p in paths:
        if not os.path.exists(p):
            out[p] = {"present": False}
            continue
        try:
            st = os.stat(p)
            entry = {"present": True, "size": st.st_size, "mtime": int(st.st_mtime), "sha256": checksum(p)}
            if p.lower().endswith((".db", ".sqlite", ".sqlite3")):
                entry["integrity"] = integrity_check(p).get("ok")
            out[p] = entry
        except Exception as e:
            out[p] = {"present": True, "error": str(e)}
    return out


def verify_manifest(saved, paths=None):
    """Compare a saved manifest dict to the current disk state. Returns {ok, missing, changed, corrupt}."""
    paths = paths or list(saved.keys())
    missing, changed, corrupt = [], [], []
    for p in paths:
        cur = manifest([p])[p]
        old = saved.get(p, {})
        if not cur.get("present"):
            missing.append(p); continue
        if cur.get("integrity") is False:
            corrupt.append(p)
        if old.get("present") and old.get("sha256") and cur.get("sha256") and old["sha256"] != cur["sha256"]:
            changed.append(p)
    return {"ok": not (missing or corrupt), "missing": missing, "changed": changed, "corrupt": corrupt}


def backup(db_path, dest_path):
    """Online-safe SQLite backup: writes a consistent snapshot to dest_path even if the DB is in use.
    Returns {ok, dest, bytes, sha256}. Never touches the source."""
    if not os.path.exists(db_path):
        return {"ok": False, "error": "source not found"}
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
    try:
        src = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
        dst = sqlite3.connect(dest_path)
        with dst:
            src.backup(dst)
        dst.close(); src.close()
        return {"ok": True, "dest": dest_path, "bytes": os.path.getsize(dest_path),
                "sha256": checksum(dest_path), "ts": int(time.time())}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def status(paths):
    """One-call health for the command center / integrity route: per-file present/size/integrity + a roll-up."""
    m = manifest(paths)
    dbs = {p: e for p, e in m.items() if e.get("present") and "integrity" in e}
    all_ok = all(e.get("integrity") for e in dbs.values()) if dbs else None
    return {"files": m, "databases_ok": all_ok, "n_files": sum(1 for e in m.values() if e.get("present"))}


# --------------------------------------------------------------------------- #
# self-test: `python integrity.py`                                            #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import tempfile
    d = tempfile.mkdtemp(prefix="integ_")
    db = os.path.join(d, "t.db")
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE x(a,b)"); con.executemany("INSERT INTO x VALUES(?,?)", [(i, i * i) for i in range(50)])
    con.commit(); con.close()

    ic = integrity_check(db)
    assert ic["ok"], ic
    print("integrity_check OK ->", ic["result"])

    cs = checksum(db)
    assert len(cs) == 64 and cs == checksum(db), "checksum unstable"
    print("checksum OK ->", cs[:16], "...")

    man = manifest([db, os.path.join(d, "nope.db")])
    assert man[db]["present"] and man[db]["integrity"] is True, man
    assert man[os.path.join(d, "nope.db")]["present"] is False
    print("manifest OK")

    bak = backup(db, os.path.join(d, "t.bak"))
    assert bak["ok"] and bak["bytes"] > 0 and integrity_check(bak["dest"])["ok"], bak
    print("backup OK -> %d bytes, valid copy" % bak["bytes"])

    # tamper: flip a byte in a copy -> verify_manifest catches the change/corruption
    import shutil
    db2 = os.path.join(d, "t2.db"); shutil.copy(db, db2)
    saved = manifest([db2])
    with open(db2, "r+b") as f:
        f.seek(90); f.write(b"\xff\xff\xff\xff")
    vm = verify_manifest(saved, [db2])
    assert (db2 in vm["changed"]) or (db2 in vm["corrupt"]), vm
    print("verify_manifest catches tampering OK ->", "corrupt" if vm["corrupt"] else "changed")
    print("integrity self-test PASS")

# END OF FILE
