#!/usr/bin/env python3
"""THE VIEWER — data safeguard: integrity manifest, atomic writes, versioned snapshots, and
recovery ("the treasure vault"). Stdlib-only, Windows-friendly.

Why: this program is data-heavy. Files can be damaged by a process killed mid-write, power loss,
disk errors, sync glitches, or a truncated copy. This module lets you (1) take consistent
SNAPSHOTS of every critical file, (2) VERIFY current files against the last good snapshot and
classify any damage (TRUNCATED / CORRUPTED / SHRUNK / MISSING / MODIFIED / GREW), and
(3) RECOVER any file byte-for-byte from the vault — like an archaeologist restoring a lost relic.

The heavy index (viewer.db, multi-GB) is snapshotted via SQLite's consistent `VACUUM INTO` only
when you pass --with-db (otherwise it's tracked by size + SQLite integrity_check, not copied).

CLI:
  python safeguard.py snapshot [--label TAG] [--with-db]
  python safeguard.py verify   [--snap ID]            # default: latest
  python safeguard.py recover  (--all | PATH...) [--snap ID]
  python safeguard.py list
  python safeguard.py gc       [--keep N]             # prune old snapshots (default: keep 10)
  python safeguard.py backupdb [--keep N] [--to DIR] [--auto]
                                                      # v1.13.0: full DB backup via VACUUM INTO ->
                                                      # backups/db/viewer-YYYYMMDD-HHMM.db, rotate to
                                                      # the newest 2; needs free disk > 1.3x DB size.
                                                      # --auto also runs gc --keep 10 afterwards.
  python safeguard.py dbcheck  [--db PATH]            # SQLite integrity_check
"""
import argparse, hashlib, json, os, shutil, sqlite3, sys, time, fnmatch, threading
from contextlib import contextmanager

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                                   # project root (THE VIEWER)
VAULT = os.path.join(ROOT, "backups", "vault")                 # the treasure vault
CHUNK = 1 << 20

# Critical files to protect (globs, relative to project root). The corpus (E:\...) is read-only
# source and is NOT included; we protect the engine, UI, derived small DBs, docs, and launchers.
CRITICAL_GLOBS = [
    "engine/*.py", "engine/**/*.py", "engine/ui/*.html", "engine/ui/*.js", "engine/ui/*.css",
    "engine/*.bat", "engine/*.json", "engine/migrations/*.sql",
    "docs/*.md", "docs/diagrams/*.py", "docs/diagrams/*.svg",
    "index/correlations.db",                                   # small derived sidecar (~3.6MB)
    "index/collections.db", "index/reviews.db",               # user Smart Collections + NIIN-review decisions (small; skipped until created)
]
DB_DEFAULT = os.path.join(ROOT, "index", "viewer.db")

def sha256_bytes(b): return hashlib.sha256(b).hexdigest()
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""): h.update(chunk)
    return h.hexdigest()

def iter_critical():
    seen = set()
    for g in CRITICAL_GLOBS:
        for p in _glob(g):
            ap = os.path.abspath(p)
            if ap not in seen and os.path.isfile(ap):
                seen.add(ap); yield ap

def _glob(pattern):
    # supports ** ; walk root and fnmatch on the relpath (posix-style)
    out = []
    if "**" in pattern:
        base = pattern.split("**")[0].strip("/")
        start = os.path.join(ROOT, base) if base else ROOT
        tail = pattern.split("**")[-1].lstrip("/")
        for dp, _, fns in os.walk(start):
            for fn in fns:
                rp = os.path.relpath(os.path.join(dp, fn), ROOT).replace("\\", "/")
                if fnmatch.fnmatch(rp, (base + "/" if base else "") + "*/" + tail) or fnmatch.fnmatch(rp, (base + "/" if base else "") + tail):
                    out.append(os.path.join(ROOT, rp))
    else:
        import glob as _g
        out = _g.glob(os.path.join(ROOT, pattern))
    return out

def entry_for(path):
    st = os.stat(path)
    return {"rel": os.path.relpath(path, ROOT).replace("\\", "/"), "size": st.st_size,
            "sha256": sha256_file(path), "lines": _count_lines(path), "mtime": round(st.st_mtime, 3)}

def _count_lines(path):
    n = 0
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""): n += chunk.count(b"\n")
    return n

def _replace_retry(tmp, path, tries=6):
    """os.replace, retried on Windows PermissionError (WinError 5): a transient lock from antivirus, the
    search indexer, or a lingering read handle can deny the swap for a few ms. Back off and retry rather
    than fail the whole write. Never leaves a half-written file (the temp is the new content)."""
    import time
    for i in range(tries):
        try:
            os.replace(tmp, path); return
        except PermissionError:
            if i == tries - 1:
                raise
            time.sleep(0.15 * (i + 1))

def remove_retry(path, tries=6):
    """os.remove, retried on Windows PermissionError -- the same transient-lock scenario
    _replace_retry exists for (antivirus/search-indexer scanning the file), for callers that need
    to delete rather than swap. A no-op if `path` doesn't exist. Public: intended for cleaning up
    a stale temp/scratch file left behind by an interrupted build, e.g. build_publog.py's
    `.building-<pid>` file from a prior crashed run -- exactly the kind of leftover large file
    AV/an indexer is likely to be scanning right when the next run tries to clear it."""
    if not os.path.exists(path):
        return
    import time
    for i in range(tries):
        try:
            os.remove(path); return
        except PermissionError:
            if i == tries - 1:
                raise
            time.sleep(0.15 * (i + 1))

def _tmp_name(d, basename):
    """Temp filename for an atomic write, unique per (process, thread) -- not just per-process.
    PID alone used to be the whole key: fine for single-threaded callers, but this module is also
    called from viewer_app.py's ThreadingHTTPServer request handlers (schemgraph.py/vectorize.py's
    ensure(), keyed by doc/page), where two threads of the SAME process can legitimately race on
    the identical destination path (two browser tabs requesting the same not-yet-cached page).
    Two threads sharing one PID would previously collide on the exact same temp filename and could
    corrupt each other's write before either's os.replace() ran -- the same "truncated file served
    forever" failure class atomic_write exists to prevent, just reached via a race instead of a
    crash. threading.get_ident() makes the temp path unique per writer as well as per process."""
    return os.path.join(d, ".tmp_%s_%d_%d" % (basename, os.getpid(), threading.get_ident()))

def atomic_write(path, data, mode="wb"):
    """Write to a temp file in the same dir, flush+fsync, then os.replace (atomic on Win+POSIX).
    A crash leaves either the old file or the new file intact — never a half-written one."""
    d = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)
    tmp = _tmp_name(d, os.path.basename(path))
    if isinstance(data, str): data = data.encode("utf-8")
    with open(tmp, "wb") as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    _replace_retry(tmp, path)

def atomic_replace(tmp, dst):
    """Swap an already-built file into place atomically (retried on a transient Windows lock).
    For callers that build a large file themselves (e.g. a multi-GB SQLite database written
    directly via sqlite3.connect(tmp_path), not through atomic_write's in-memory `data` argument)
    and just need the final rename-into-place step to be crash-safe: `dst` is never deleted ahead
    of time, so a crash mid-build leaves the last-good `dst` untouched and only `tmp` is garbage.
    Creates dst's directory first, matching atomic_write/atomic_copy -- both of those tolerate a
    not-yet-existing destination directory; this used to be the one atomic_* helper that didn't."""
    d = os.path.dirname(os.path.abspath(dst)) or "."
    os.makedirs(d, exist_ok=True)
    _replace_retry(tmp, dst)

@contextmanager
def atomic_sqlite_build(dst_path):
    """Build-to-temp-then-atomic-swap scaffold for a SQLite sidecar, shared by kg.py's build() and
    build_publog.py's build() -- previously two near-identical ~20-line copies of this same
    remove_retry/connect/try/except-BaseException/atomic_replace orchestration around calls that were
    already delegating the actually safety-critical bits (remove_retry, atomic_replace) to this module.

    Yields (con, tmp_path): `con` is a fresh sqlite3.Connection open on a temp file next to `dst_path`
    (named "<dst_path>.building-<pid>"), for the caller's build body to populate + commit against.
    `dst_path` itself is NEVER touched until the `with` block exits cleanly -- only then is `con` closed
    and `tmp_path` swapped into `dst_path` via atomic_replace(). Any exception raised anywhere inside the
    `with` block instead closes `con` best-effort, removes the orphaned `tmp_path` best-effort, and
    re-raises the ORIGINAL exception unchanged -- `dst_path` is never even approached on that path, so
    the last-good file already on disk is left exactly as it was; only the `.building-<pid>` temp file is
    orphaned (and cleaned up here, best-effort).

    Callers that need PRAGMAs in effect for the whole build (e.g. build_publog.py's
    journal_mode=OFF / synchronous=OFF -- kg.py's kg.db is small enough it doesn't bother) should set
    them on `con` first, right after entering the `with` block, before doing real work.

    Callers with a best-effort, non-fatal step that must run AFTER the main body but must NOT trigger
    this scaffold's failure-cleanup if it errors (e.g. build_publog.py's trailing `PRAGMA optimize` --
    query-planner statistics only; a transient failure there must not discard an otherwise valid,
    already-committed build) should wrap just that step in their OWN try/except, still inside the `with`
    block, after the main body. This scaffold's cleanup only fires for exceptions that escape the
    caller's own handling and reach here -- exactly matching the pre-refactor behavior in both files.
    """
    tmp_path = dst_path + ".building-%d" % os.getpid()
    remove_retry(tmp_path)   # stale leftover from a prior crashed run -- just scratch space
    con = None
    try:
        con = sqlite3.connect(tmp_path)
        yield con, tmp_path
        con.close()
    except BaseException:
        try: con.close()
        except Exception: pass
        try: remove_retry(tmp_path)
        except OSError: pass
        raise

    atomic_replace(tmp_path, dst_path)   # only now does the new build become the live file

def atomic_copy(src, dst):
    d = os.path.dirname(os.path.abspath(dst)) or "."
    os.makedirs(d, exist_ok=True)
    tmp = _tmp_name(d, os.path.basename(dst))
    with open(src, "rb") as fi, open(tmp, "wb") as fo:
        for chunk in iter(lambda: fi.read(CHUNK), b""): fo.write(chunk)
        fo.flush(); os.fsync(fo.fileno())
    _replace_retry(tmp, dst)

# ---------------- snapshot ----------------
def snapshot(label="", with_db=False, db=DB_DEFAULT):
    snapid = time.strftime("SNAP_%Y%m%d_%H%M%S") + (("_" + label) if label else "")
    sdir = os.path.join(VAULT, snapid); fdir = os.path.join(sdir, "files")
    os.makedirs(fdir, exist_ok=True)
    entries = []
    for p in iter_critical():
        e = entry_for(p)
        dst = os.path.join(fdir, e["rel"])
        atomic_copy(p, dst)
        # paranoia: verify the copy matches before trusting it
        if sha256_file(dst) != e["sha256"]:
            raise RuntimeError("snapshot copy mismatch for %s" % e["rel"])
        entries.append(e)
    dbinfo = None
    if os.path.exists(db):
        dbinfo = {"rel": os.path.relpath(db, ROOT).replace("\\", "/"), "size": os.path.getsize(db),
                  "integrity": db_integrity(db)}
        if with_db:
            outdb = os.path.join(fdir, dbinfo["rel"])
            os.makedirs(os.path.dirname(outdb), exist_ok=True)
            _sqlite_backup(db, outdb)
            dbinfo["copied"] = True; dbinfo["sha256"] = sha256_file(outdb)
    man = {"snapid": snapid, "created": time.strftime("%Y-%m-%d %H:%M:%S"), "root": ROOT,
           "count": len(entries), "entries": entries, "db": dbinfo}
    atomic_write(os.path.join(sdir, "manifest.json"), json.dumps(man, indent=2))
    return snapid, man

def _sqlite_backup(src, dst):
    """Consistent copy of a live SQLite DB via the online backup API (safe while the app runs)."""
    # v1.13.4: `with d:` only wraps d's transaction (commit/rollback) -- it does NOT close either
    # connection, and re-raises on failure. If s.backup(d) throws (source locked/busy or corrupted --
    # a scenario this module explicitly designs around elsewhere), both s and d used to leak past this
    # point since s.close()/d.close() sat unreached after the with-block. Same "connect() succeeds, the
    # real operation throws, close() skipped" shape as db_integrity() a few lines below, fixed the same
    # way: close both in finally regardless of outcome.
    s = None; d = None
    try:
        s = sqlite3.connect(src); d = sqlite3.connect(dst)
        with d: s.backup(d)
    finally:
        if s is not None: s.close()
        if d is not None: d.close()

def db_integrity(db):
    c = None
    try:
        c = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
        r = c.execute("PRAGMA quick_check").fetchone()[0]
        return r
    except Exception as e:
        return "ERROR: %s" % e
    finally:
        # Always close, even on the exception path: sqlite3.connect() succeeds even against a
        # corrupted header (validation is lazy), so a bad DB throws INSIDE the try and used to
        # skip close() -- leaking the connection. On Windows that leaves the file locked, which
        # deterministically breaks the very next atomic_copy()/os.replace() over the same path
        # (the recover-after-detect flow in test_truncation.py; also reachable from snapshot()
        # and backupdb() if either is ever run against an actually-corrupted DB).
        if c is not None:
            c.close()

# ---------------- verify ----------------
def latest_snapid():
    if not os.path.isdir(VAULT): return None
    snaps = sorted(d for d in os.listdir(VAULT) if d.startswith("SNAP_"))
    return snaps[-1] if snaps else None

def load_manifest(snapid):
    return json.load(open(os.path.join(VAULT, snapid, "manifest.json"), encoding="utf-8"))

def classify(cur_path, e, snap_file):
    """Compare the current file to a snapshot entry + the snapshot's stored bytes.
    Returns (status, detail)."""
    if not os.path.exists(cur_path): return "MISSING", "file is gone"
    cs = os.path.getsize(cur_path)
    if cs == 0 and e["size"] > 0: return "EMPTY", "0 bytes (was %d)" % e["size"]
    cur_sha = sha256_file(cur_path)
    if cur_sha == e["sha256"]: return "OK", ""
    # hash differs — figure out how
    if cs < e["size"]:
        # truncated? = current is an exact prefix of the snapshot bytes
        if snap_file and os.path.exists(snap_file):
            with open(snap_file, "rb") as f: head = f.read(cs)
            with open(cur_path, "rb") as f: cur = f.read()
            if head == cur:
                return "TRUNCATED", "lost %d of %d bytes (clean prefix)" % (e["size"] - cs, e["size"])
        return "SHRUNK", "%d -> %d bytes, content diverged" % (e["size"], cs)
    if cs == e["size"]:
        return "CORRUPTED", "same size, content changed (byte-flip?)"
    return "MODIFIED", "%d -> %d bytes (grew / edited)" % (e["size"], cs)

def verify(snapid=None):
    snapid = snapid or latest_snapid()
    if not snapid: return None, []
    man = load_manifest(snapid)
    fdir = os.path.join(VAULT, snapid, "files")
    results = []
    for e in man["entries"]:
        cur = os.path.join(ROOT, e["rel"]); snap_file = os.path.join(fdir, e["rel"])
        status, detail = classify(cur, e, snap_file)
        results.append((e["rel"], status, detail))
    return snapid, results

# ---------------- recover ----------------
def recover(rels, snapid=None):
    snapid = snapid or latest_snapid()
    if not snapid: raise RuntimeError("no snapshots in the vault")
    man = load_manifest(snapid); fdir = os.path.join(VAULT, snapid, "files")
    by_rel = {e["rel"]: e for e in man["entries"]}
    done = []
    targets = list(by_rel.keys()) if rels == "ALL" else rels
    for rel in targets:
        e = by_rel.get(rel)
        if not e: done.append((rel, "NOT_IN_SNAPSHOT")); continue
        src = os.path.join(fdir, rel); dst = os.path.join(ROOT, rel)
        atomic_copy(src, dst)
        ok = sha256_file(dst) == e["sha256"]
        done.append((rel, "RECOVERED" if ok else "RECOVER_FAILED_HASH"))
    return snapid, done

def mirror(to_dir, snapid=None, all_snaps=False):
    """Copy snapshot(s) from the vault to a SECOND location (USB / external / network share) so a single
    disk failure can't lose both the data and its backups. Verifies every copied file's sha256. Stdlib
    only -> works on any Windows build (RPS-safe)."""
    if not os.path.isdir(VAULT):
        raise RuntimeError("no vault yet -- run 'snapshot' first")
    snaps = sorted(d for d in os.listdir(VAULT) if d.startswith("SNAP_"))
    if not snaps:
        raise RuntimeError("vault is empty")
    targets = snaps if all_snaps else [snapid or snaps[-1]]
    dst_vault = os.path.join(to_dir, "THE_VIEWER_vault")
    copied = verified = 0; bad = []
    for sid in targets:
        src = os.path.join(VAULT, sid)
        for dp, _, fns in os.walk(src):
            for fn in fns:
                s = os.path.join(dp, fn)
                rel = os.path.relpath(s, src)
                d = os.path.join(dst_vault, sid, rel)
                atomic_copy(s, d); copied += 1
                if sha256_file(d) == sha256_file(s): verified += 1
                else: bad.append(rel)
    return {"to": dst_vault, "snaps": targets, "files": copied, "verified": verified, "mismatched": bad}

def gc(keep=10):
    if not os.path.isdir(VAULT): return []
    snaps = sorted(d for d in os.listdir(VAULT) if d.startswith("SNAP_"))
    drop = snaps[:-keep] if keep > 0 else []
    for d in drop: shutil.rmtree(os.path.join(VAULT, d), ignore_errors=True)
    return drop

# ---------------- backupdb (v1.13.0) ----------------
DB_BACKUP_DIR = os.path.join(ROOT, "backups", "db")

def backupdb(db=DB_DEFAULT, dest_dir=None, keep=2):
    """Full consistent backup of the big index DB via `VACUUM INTO` (safe while the app reads it),
    written to backups/db/viewer-YYYYMMDD-HHMM.db, then rotate so only the newest `keep` copies
    remain (these are OUR generated backups -- rotation is allowed; R6 applies to source data, not
    to redundant backup copies). Fails LOUD (R13):
      * refuses to start unless free disk > 1.3x the DB size (VACUUM INTO needs the full copy),
      * verifies the copy with PRAGMA quick_check before rotating anything,
      * deletes its own partial output on any error -- never leaves a half-written backup behind."""
    if not os.path.exists(db):
        raise RuntimeError("DB not found: %s" % db)
    dest_dir = dest_dir or DB_BACKUP_DIR
    os.makedirs(dest_dir, exist_ok=True)
    size = os.path.getsize(db)
    need = int(size * 1.3)
    free = shutil.disk_usage(dest_dir).free
    if free < need:
        raise RuntimeError("NOT ENOUGH FREE DISK for a safe backup: need %.2f GB (1.3x the %.2f GB DB), "
                           "only %.2f GB free on the backup drive. Free space and re-run."
                           % (need / 1e9, size / 1e9, free / 1e9))
    out = os.path.join(dest_dir, time.strftime("viewer-%Y%m%d-%H%M") + ".db")
    n = 1
    while os.path.exists(out):                       # same-minute re-run: never overwrite a backup
        out = os.path.join(dest_dir, time.strftime("viewer-%Y%m%d-%H%M") + ("-%d.db" % n)); n += 1
    print("backupdb: source %s (%.2f GB)" % (db, size / 1e9))
    print("backupdb: free disk %.2f GB (need %.2f GB) -- OK" % (free / 1e9, need / 1e9))
    print("backupdb: VACUUM INTO %s  (this copies the whole DB; expect minutes, not seconds)..." % out)
    t0 = time.time()
    try:
        c = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
        try:
            c.execute("VACUUM INTO ?", (out,))
        finally:
            c.close()
        print("backupdb: copy done in %.1fs (%.2f GB) -- verifying with PRAGMA quick_check..."
              % (time.time() - t0, os.path.getsize(out) / 1e9))
        chk = db_integrity(out)
        if chk != "ok":
            raise RuntimeError("backup FAILED integrity check: %s" % chk)
    except BaseException:
        if os.path.exists(out):                      # fail loud AND clean: no half-written backups
            try: os.remove(out)
            except OSError: pass
        raise
    print("backupdb: verified ok -> %s" % out)
    # rotation: keep only the newest `keep` viewer-*.db in dest_dir. Sort by mtime, NOT name:
    # a same-minute re-run gets a "-N" suffix which sorts lexicographically BEFORE ".db", so a
    # name sort would rotate out the wrong (newer) copy.
    copies = sorted((f for f in os.listdir(dest_dir)
                     if f.startswith("viewer-") and f.endswith(".db")),
                    key=lambda f: os.path.getmtime(os.path.join(dest_dir, f)))
    drop = copies[:-keep] if keep > 0 else []
    for f in drop:
        try:
            os.remove(os.path.join(dest_dir, f))
            print("backupdb: rotated out old copy %s" % f)
        except OSError as e:
            print("backupdb: [warn] could not delete old copy %s: %s" % (f, e))
    print("backupdb: DONE -- %d cop%s kept in %s" % (min(len(copies), keep) if keep > 0 else len(copies),
                                                     "y" if (keep == 1) else "ies", dest_dir))
    return out

# ---------------- CLI ----------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="THE VIEWER data safeguard (snapshot / verify / recover).")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("snapshot"); s.add_argument("--label", default=""); s.add_argument("--with-db", action="store_true"); s.add_argument("--db", default=DB_DEFAULT)
    v = sub.add_parser("verify"); v.add_argument("--snap", default=None)
    r = sub.add_parser("recover"); r.add_argument("paths", nargs="*"); r.add_argument("--all", action="store_true"); r.add_argument("--snap", default=None)
    sub.add_parser("list")
    g = sub.add_parser("gc"); g.add_argument("--keep", type=int, default=10)
    b = sub.add_parser("backupdb"); b.add_argument("--db", default=DB_DEFAULT); b.add_argument("--keep", type=int, default=2); b.add_argument("--to", default=None); b.add_argument("--auto", action="store_true", help="after the DB backup, also prune old snapshots (gc --keep 10) in one shot")
    dc = sub.add_parser("dbcheck"); dc.add_argument("--db", default=DB_DEFAULT)
    mi = sub.add_parser("mirror"); mi.add_argument("--to", required=True); mi.add_argument("--snap", default=None); mi.add_argument("--all", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "snapshot":
        sid, man = snapshot(a.label, a.with_db, a.db)
        print("snapshot:", sid, "| files:", man["count"], "| db:", (man["db"] or {}).get("integrity"))
    elif a.cmd == "verify":
        sid, res = verify(a.snap)
        if not sid: print("no snapshots yet — run: safeguard.py snapshot"); return 1
        bad = [x for x in res if x[1] != "OK"]
        for rel, st, detail in res:
            if st != "OK": print("  %-10s %s  %s" % (st, rel, detail))
        print("verify vs %s: %d files, %d OK, %d DAMAGED" % (sid, len(res), len(res)-len(bad), len(bad)))
        return 2 if bad else 0
    elif a.cmd == "recover":
        sid, done = recover("ALL" if a.all else a.paths, a.snap)
        for rel, st in done: print("  %-18s %s" % (st, rel))
        print("recovered from", sid)
    elif a.cmd == "list":
        if not os.path.isdir(VAULT): print("vault empty"); return 0
        for d in sorted(os.listdir(VAULT)):
            if d.startswith("SNAP_"):
                try: m = load_manifest(d); print("  %s  (%d files, %s)" % (d, m["count"], m["created"]))
                except Exception: print("  %s  (manifest unreadable)" % d)
    elif a.cmd == "gc":
        # v1.13.0: this branch was MISSING -- `safeguard.py gc` used to fall through to print_help
        # and exit 0 (a silent no-op that looked green). Now it actually prunes, and says so.
        drop = gc(a.keep)
        if drop:
            for d in drop: print("  pruned %s" % d)
        print("gc: pruned %d old snapshot(s), keeping the newest %d" % (len(drop), a.keep))
    elif a.cmd == "backupdb":
        try:
            backupdb(a.db, a.to, a.keep)
        except Exception as e:
            print("backupdb: FAILED -- %s" % e)
            return 2
        if a.auto:
            drop = gc(10)
            print("gc --auto: pruned %d old snapshot(s), keeping the newest 10" % len(drop))
    elif a.cmd == "dbcheck":
        print("integrity:", db_integrity(a.db))
    elif a.cmd == "mirror":
        r = mirror(a.to, a.snap, a.all)
        print("mirrored %d files (%d verified) of %d snapshot(s) -> %s" % (r["files"], r["verified"], len(r["snaps"]), r["to"]))
        if r["mismatched"]: print("  [warn] %d files failed verify: %s" % (len(r["mismatched"]), ", ".join(r["mismatched"][:5])))
    else:
        ap.print_help()
    return 0

if __name__ == "__main__":
    sys.exit(main())
