#!/usr/bin/env python3
"""Pre-render a CAD image for every part in the representative 3-D library into index/cadcache/ (sidecar).
Read-only on the index; resumable (skips already-rendered parts). RUN ON WINDOWS (host).

PARALLEL: renders are independent, so this fans out across CPU cores (Alder Lake etc.) — auto-sized to the
machine. Each worker renders + caches one part to its own file (no write contention).

  python make_cad.py                 # whole representative set, all cores
  python make_cad.py --style v1      # a specific tier (v1/v2/v3)
  python make_cad.py --workers 8     # cap worker count
  python make_cad.py --limit 50      # quick test
  python make_cad.py --serial        # force single-threaded (debug)
"""
import os, sqlite3, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cad_render
DB = os.path.abspath(os.path.join(HERE, "..", "index", "viewer.db"))
CDIR = os.path.join(os.path.dirname(DB), "cadcache")

_THREED_WHERE = ("characteristics IS NOT NULL AND characteristics<>'' AND ("
                 "upper(characteristics) LIKE '%DIAMETER%' OR upper(characteristics) LIKE '%LENGTH%' OR "
                 "upper(characteristics) LIKE '%HEIGHT%' OR upper(characteristics) LIKE '%WIDTH%' OR "
                 "upper(characteristics) LIKE '%THICKNESS%')")

_STYLE = "v3"   # set in main(); workers read it (inherited on fork / re-imported on spawn via the task tuple)


def _render_one(task):
    """Render+cache one part. Runs in a worker process. Returns ('done'|'fail', nsn, err) -- `err` is
    None on success, else a short exception summary (medium finding #32: a bare `except Exception:
    return ('fail', nsn)` used to swallow the reason entirely, so a systemic problem across a
    ~98,000-item batch -- bad font, full disk, a corrupted install -- surfaced only as an aggregate
    failure count with no way to diagnose it)."""
    nsn, name, chars, style = task
    try:
        p = cad_render.ensure(nsn, name, chars, CDIR, style=style)
        return ("done", nsn, None) if p else ("fail", nsn, "cad_render.ensure() returned no path")
    except Exception as e:
        return ("fail", nsn, "%s: %s" % (type(e).__name__, e))


def _auto_workers():
    n = os.cpu_count() or 4
    # leave one core for the OS/UI; cap so per-process PIL+numpy memory stays sane on a laptop
    return max(2, min(n - 1, 12))


def _collect(limit, style):
    con = sqlite3.connect("file:%s?mode=ro" % DB, uri=True); con.row_factory = sqlite3.Row
    seen = {}
    for r in con.execute("SELECT nsn, item_name, characteristics FROM ref_nsn WHERE " + _THREED_WHERE).fetchall():
        n = (r["nsn"] or "").strip()
        if n and n not in seen: seen[n] = (r["item_name"] or "", r["characteristics"] or "")
    try:
        prows = con.execute("SELECT p.nsn AS nsn, MAX(p.fig_title) AS ft, MAX(r.characteristics) AS ch "
                            "FROM parts p LEFT JOIN ref_nsn r ON r.nsn=p.nsn "
                            "WHERE p.fig_no IS NOT NULL AND COALESCE(TRIM(p.nsn),'')<>'' GROUP BY p.nsn").fetchall()
        for r in prows:
            n = (r["nsn"] or "").strip()
            if n and n not in seen: seen[n] = (r["ft"] or "", r["ch"] or "")
    except Exception:
        pass
    con.close()
    items = list(seen.items())
    if limit: items = items[:limit]
    return items


def main():
    if cad_render.Image is None:
        print("[ERROR] Pillow not available — install it (the app's preflight normally does)."); return 1
    if not os.path.exists(DB):
        print("[ERROR] index not found:", DB); return 1
    limit = None
    if "--limit" in sys.argv:
        try: limit = int(sys.argv[sys.argv.index("--limit")+1])
        except Exception: limit = 50
    style = "v3"
    if "--style" in sys.argv:
        try: style = sys.argv[sys.argv.index("--style")+1]
        except Exception: style = "v3"
        if style not in ("v1", "v2", "v3"): style = "v3"
    serial = "--serial" in sys.argv
    force = "--force" in sys.argv   # re-render even if a cache file already exists (push a new CAD_VERSION)
    workers = _auto_workers()
    if "--workers" in sys.argv:
        try: workers = max(1, int(sys.argv[sys.argv.index("--workers")+1]))
        except Exception: pass
    os.makedirs(CDIR, exist_ok=True)

    items = _collect(limit, style)
    total = len(items)
    # pre-filter already-cached (resumable) so the pool only does real work
    todo = []
    skipped = 0
    for nsn, (name, chars) in items:
        out = cad_render.cache_path(CDIR, nsn, style)
        if (not force) and os.path.exists(out) and os.path.getsize(out) > 0:
            skipped += 1
        else:
            if force:
                try: os.remove(out)   # ensure() skips existing files — clear so it re-renders at the new version
                except Exception: pass
            todo.append((nsn, name, chars, style))

    cores = os.cpu_count() or 0
    if serial or workers <= 1 or len(todo) < 8:
        workers = 1
    print("=== CAD render (style %s): %d parts, %d already cached, %d to render ===" % (style, total, skipped, len(todo)))
    print("=== CPU cores=%s, using %d worker%s -> %s ===" % (cores, workers, "" if workers == 1 else "s", CDIR))

    t0 = time.time(); done = failed = 0; n = len(todo)
    fail_log_path = os.path.join(CDIR, "render_failures.log")
    fail_log = open(fail_log_path, "a", encoding="utf-8")   # append: keeps history across resumed runs

    def _progress(i):
        el = time.time() - t0; rate = i/el if el else 0; eta = (n-i)/rate if rate else 0
        print("  %d/%d  (%.0f%%)  new=%d fail=%d  %.0f/s  ETA %dm%02ds"
              % (i, n, 100.0*i/max(1, n), done, failed, rate, eta//60, eta % 60))

    def _log_fail(nsn, err):
        fail_log.write("%s\t%s\t%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), nsn, err))
        fail_log.flush()

    try:
        if workers == 1:
            for i, task in enumerate(todo, 1):
                st, nsn, err = _render_one(task)
                if st == "done": done += 1
                else: failed += 1; _log_fail(nsn, err)
                if i % 200 == 0 or i == n: _progress(i)
        else:
            from multiprocessing import Pool
            with Pool(processes=workers) as pool:
                for i, (st, nsn, err) in enumerate(pool.imap_unordered(_render_one, todo, chunksize=16), 1):
                    if st == "done": done += 1
                    else: failed += 1; _log_fail(nsn, err)
                    if i % 200 == 0 or i == n: _progress(i)
    finally:
        fail_log.close()

    el = time.time() - t0
    print("=== Done: %d rendered, %d already cached, %d failed in %.0fs (%.0f/s). Cache: %s ==="
          % (done, skipped, failed, el, (done/el if el else 0), CDIR))
    if failed:
        print("=== %d failure(s) logged with reasons -> %s ===" % (failed, fail_log_path))
    # Review finding: this used to unconditionally `return 0` regardless of `failed`, so
    # RE-RENDER-CAD.bat/RUN-CAD-TIERS.bat's new errorlevel checks (added alongside this exact
    # fix) could never fire for the scenario finding #32's own docstring describes -- a systemic
    # problem (bad font, full disk, a corrupted install) failing every render in a ~98,000-item
    # batch would still print an unconditional "all tiers rendered" success message.
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
