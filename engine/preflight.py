#!/usr/bin/env python3
"""THE VIEWER -- preflight health gate + lightweight runtime guards.  Stdlib-only, RPS-aware.

Run this BEFORE the server / OCR start so problems FAIL FAST with a clear message instead of
crash-looping. It also exposes `disk_ok()`, used as a runtime guard so OCR and the page-render cache
can't silently fill the disk.

Checks (each -> OK / WARN / FAIL / INFO):
  python   interpreter >= 3.6
  disk     free space on the index drive >= threshold (default 1 GB; env VIEWER_MIN_FREE_MB)
  index    viewer.db present + SQLite quick_check ok (read-only)
  schema   schema_meta.schema_version matches the highest migration (drift -> WARN, fixable)
  gpu      CUDA provider present -- INFO ONLY; absence is normal on lite/legacy and is never a FAIL

RPS-safe by design: GPU is informational, thresholds are modest, nothing assumes a modern OS, and there
are no third-party dependencies -- so it runs identically on modern, lite, and legacy (Win7/Vista) builds.

CLI:
  python preflight.py [--db=PATH] [--strict] [--json]
  exit 0 = good to start, 1 = a fatal check failed (or, with --strict, a warning)
"""
import os, sys, sqlite3, shutil, glob, re, json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_DB = os.path.join(ROOT, "index", "viewer.db")
MIN_FREE_MB_DEFAULT = 1024                       # 1 GB floor; override via VIEWER_MIN_FREE_MB
LARGE_DB_MB_DEFAULT = 512                         # above this, startup does a FAST probe, not a full scan
DEEP_BUDGET_S_DEFAULT = 20                        # max seconds a --deep quick_check may run before we bail

def _free_mb(path):
    try:
        d = path if os.path.isdir(path) else (os.path.dirname(os.path.abspath(path)) or ".")
        return shutil.disk_usage(d).free // (1024 * 1024)
    except Exception:
        return None

def disk_ok(path, min_free_mb=None):
    """Runtime guard. Returns (ok, free_mb, threshold_mb). FAIL-OPEN (ok=True) when free space can't be
    measured, so a probe glitch never halts real work."""
    if min_free_mb is None:
        try: min_free_mb = int(os.environ.get("VIEWER_MIN_FREE_MB", MIN_FREE_MB_DEFAULT))
        except Exception: min_free_mb = MIN_FREE_MB_DEFAULT
    f = _free_mb(path)
    return (True if f is None else f >= min_free_mb), f, min_free_mb

def _highest_migration():
    hi = 0
    try:
        for p in glob.glob(os.path.join(HERE, "migrations", "*.sql")):
            m = re.match(r"(\d+)", os.path.basename(p))
            if m: hi = max(hi, int(m.group(1)))
    except Exception:
        pass
    return hi

def _schema_version(db):
    try:
        c = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
        try: row = c.execute("SELECT schema_version FROM schema_meta").fetchone()
        except Exception: row = None
        c.close()
        return row[0] if row else None
    except Exception:
        return None

def _db_mb(db):
    try: return os.path.getsize(db) // (1024 * 1024)
    except Exception: return None

def _index_probe(db):
    """FAST, size-independent integrity probe (milliseconds, even on a multi-GB index). Confirms the file
    opens as SQLite, its page header is internally consistent, the catalog is readable, and at least one
    real table can be queried. This is what runs at startup -- a full PRAGMA quick_check on a multi-GB file
    reads every page and made preflight look like it hung, so it is no longer the default."""
    try:
        c = sqlite3.connect("file:%s?mode=ro" % db, uri=True, timeout=10)
        try:
            # header / page-count read (instant) -- a torn or truncated file fails here
            pc = c.execute("PRAGMA page_count").fetchone()[0]
            ps = c.execute("PRAGMA page_size").fetchone()[0]
            ntab = c.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
            # sentinel read of one real table if present (catalog + b-tree root readable)
            row = c.execute("SELECT name FROM sqlite_master WHERE type='table' "
                            "AND name NOT LIKE 'sqlite_%' LIMIT 1").fetchone()
            if row:
                c.execute("SELECT 1 FROM \"%s\" LIMIT 1" % row[0].replace('"', '""')).fetchone()
        finally:
            c.close()
        return "ok", "opened ok: %s tables, %d pages x %d B" % (ntab, pc, ps)
    except Exception as e:
        return "fail", "could not read index: %s" % e

def _quick_check(db, budget_s=None):
    """FULL integrity scan (reads every page). Only on demand (--deep). A progress handler enforces a wall-
    clock budget so even a huge/slow file can't hang the gate -- if the budget is hit we abort and report it
    rather than blocking. Returns the quick_check string, or 'TIMEOUT...'/'ERROR...'."""
    if budget_s is None:
        try: budget_s = int(os.environ.get("VIEWER_DEEP_BUDGET_S", DEEP_BUDGET_S_DEFAULT))
        except Exception: budget_s = DEEP_BUDGET_S_DEFAULT
    import time
    try:
        c = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
        deadline = time.time() + max(1, int(budget_s))
        # set_progress_handler: returning non-zero aborts the running statement (stdlib, 3.6+)
        c.set_progress_handler(lambda: 1 if time.time() > deadline else 0, 100000)
        try:
            r = c.execute("PRAGMA quick_check").fetchone()[0]
        except sqlite3.OperationalError:
            r = "TIMEOUT: exceeded %ss budget (file too large to fully verify at startup)" % budget_s
        c.close(); return r
    except Exception as e:
        return "ERROR: %s" % e

def _gpu_present():
    try:
        import onnxruntime as o
        return "CUDAExecutionProvider" in o.get_available_providers()
    except Exception:
        return None                              # not installed / unknown -> INFO, never FAIL

def checks(db=DEFAULT_DB, min_free_mb=None, want_gpu=None, deep=False):
    """Return a list of (name, status, detail). `want_gpu`: if False (lite/legacy), GPU check is skipped.
    `deep`: run the FULL page-by-page integrity scan (time-budgeted). Default is a fast probe so a multi-GB
    index never makes the gate hang."""
    out = []
    out.append(("python", "OK" if sys.version_info[:2] >= (3, 6) else "FAIL",
                "%d.%d" % sys.version_info[:2]))
    ok, free, thr = disk_ok(db, min_free_mb)
    if free is None:
        out.append(("disk", "WARN", "could not read free space"))
    else:
        out.append(("disk", "OK" if ok else "FAIL", "%d MB free (need >= %d)" % (free, thr)))
    if not os.path.exists(db):
        out.append(("index", "WARN", "viewer.db not found yet (first run?) at %s" % db))
    else:
        try: large_mb = int(os.environ.get("VIEWER_LARGE_DB_MB", LARGE_DB_MB_DEFAULT))
        except Exception: large_mb = LARGE_DB_MB_DEFAULT
        mb = _db_mb(db)
        st, detail = _index_probe(db)                # fast: open + header + catalog + sentinel read
        if st != "ok":
            out.append(("index", "FAIL", detail))
        elif deep:
            qc = _quick_check(db)
            if qc == "ok":
                out.append(("index", "OK", "deep quick_check: ok (%s MB)" % (mb if mb is not None else "?")))
            elif str(qc).startswith("TIMEOUT"):
                out.append(("index", "WARN", qc))    # couldn't finish in budget -> not a hard fail
            else:
                out.append(("index", "FAIL", "quick_check: %s" % qc))
        elif mb is not None and mb >= large_mb:
            out.append(("index", "OK", "%s; full scan skipped on large DB (%s MB) -- run --deep to force" % (detail, mb)))
        else:
            qc = _quick_check(db)                     # small DB: a full scan is cheap, so do it
            out.append(("index", "OK" if qc == "ok" else "FAIL", "quick_check: %s" % qc))
        sv = _schema_version(db); hi = _highest_migration()
        if sv is None:
            out.append(("schema", "WARN", "no schema_meta yet"))
        elif hi and sv < hi:
            out.append(("schema", "WARN", "schema_version=%s < migrations=%s -> run fix_schema_version.py" % (sv, hi)))
        else:
            out.append(("schema", "OK", "schema_version=%s" % sv))
    if want_gpu is not False:
        g = _gpu_present()
        out.append(("gpu", "OK" if g else "INFO",
                    "CUDA provider present" if g else "no CUDA provider (CPU / lite / legacy is fine)"))
    return out

def worst(results):
    order = {"FAIL": 3, "WARN": 2, "INFO": 1, "OK": 0}
    return max((order.get(s, 0) for _, s, _ in results), default=0)

def gate(db=DEFAULT_DB, strict=False, min_free_mb=None, want_gpu=None, log=print, deep=False):
    """Print the checks and decide go/no-go. FAIL on python/disk/index is fatal everywhere; schema drift
    and GPU are non-fatal (RPS-safe). With strict=True, any WARN also stops. Returns True = good to start."""
    res = checks(db, min_free_mb, want_gpu, deep=deep)
    for name, st, detail in res:
        log("  [%-4s] %-7s %s" % (st, name, detail))
    fatal = [n for n, s, _ in res if s == "FAIL"]
    if fatal:
        log("PREFLIGHT: FAIL -> " + ", ".join(fatal) + "  (fix the above before starting)")
        return False
    if strict and worst(res) >= 2:
        log("PREFLIGHT: strict mode -> a WARN is treated as stop")
        return False
    log("PREFLIGHT: OK")
    return True

if __name__ == "__main__":
    db = DEFAULT_DB; strict = "--strict" in sys.argv; as_json = "--json" in sys.argv
    deep = "--deep" in sys.argv
    for a in sys.argv[1:]:
        if a.startswith("--db="): db = a.split("=", 1)[1]
    if as_json:
        res = checks(db, deep=deep)
        print(json.dumps({"checks": [{"name": n, "status": s, "detail": d} for n, s, d in res],
                          "ok": not any(s == "FAIL" for _, s, _ in res)}, indent=2))
        sys.exit(0 if not any(s == "FAIL" for _, s, _ in res) else 1)
    sys.exit(0 if gate(db, strict=strict, deep=deep) else 1)
