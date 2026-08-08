#!/usr/bin/env python3
"""Benchmark the CAD batch boost: render N real parts serially vs across CPU cores. Host-side."""
import os, sys, time, sqlite3
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import cad_render
DB = os.path.abspath(os.path.join(HERE, "..", "index", "viewer.db"))

def _work(t):
    name, chars, nsn = t
    try: cad_render.render(name, chars, nsn, w=320, h=250, style="v3"); return 1
    except Exception: return 0

def main():
    N = 120
    if "--n" in sys.argv:
        try: N = int(sys.argv[sys.argv.index("--n")+1])
        except Exception: pass
    items = []
    try:
        con = sqlite3.connect("file:%s?mode=ro" % DB, uri=True); con.row_factory = sqlite3.Row
        rows = con.execute("SELECT nsn,item_name,characteristics FROM ref_nsn WHERE characteristics LIKE '%DIAMETER%' "
                           "OR characteristics LIKE '%LENGTH%' LIMIT ?", (N,)).fetchall()
        con.close()
        items = [((r["item_name"] or ""), (r["characteristics"] or ""), (r["nsn"] or "")) for r in rows]
    except Exception as e:
        print("DB read failed, using synthetic parts:", e)
    while len(items) < N:
        items.append(("BEARING, BALL", "OUTSIDE DIAMETER 52 MM; INSIDE DIAMETER 25 MM; WIDTH 15 MM", "TEST-%d" % len(items)))
    items = items[:N]
    cores = os.cpu_count() or 0
    workers = max(2, min(cores - 1, 12))
    print("CPU cores: %s   ·   parts: %d   ·   workers: %d   ·   CAD_VERSION %s (SS4, colour+texture)" % (cores, N, workers, cad_render.CAD_VERSION))

    t0 = time.time()
    for it in items: _work(it)
    ts = time.time() - t0

    from multiprocessing import Pool
    t1 = time.time()
    with Pool(processes=workers) as pool:
        list(pool.imap_unordered(_work, items, chunksize=8))
    tp = time.time() - t1

    print("  serial   : %6.2fs  (%.1f img/s)" % (ts, N/ts if ts else 0))
    print("  parallel : %6.2fs  (%.1f img/s)  on %d workers" % (tp, N/tp if tp else 0, workers))
    print("  SPEEDUP  : %.1fx" % (ts/tp if tp else 0))
    full = 98000
    print("  => full ~%d-render set (3 tiers): serial ~%.0f min  ->  parallel ~%.0f min"
          % (full, (full*ts/N)/60.0, (full*tp/N)/60.0))

if __name__ == "__main__":
    main()
