#!/usr/bin/env python3
"""Pre-vectorize every FIGURE-bearing page in the corpus into crisp cached SVGs (index/veccache/) + a coverage
report (index/vectorize_coverage.tsv). Read-only on the index (R1), sidecar-only (R6). Parallel + resumable.
RUN ON WINDOWS (host). Reuses engine/vectorize.py (OpenCV potrace-style).

  python build_vectorize.py                 # every figure page, all cores
  python build_vectorize.py --limit 100     # first N figure pages (quick test)
  python build_vectorize.py --dpi 200 --workers 8
  python build_vectorize.py --serial
"""
import os, sys, sqlite3, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vectorize

DB = os.path.abspath(os.path.join(HERE, "..", "index", "viewer.db"))
IDX = os.path.dirname(DB)
VECDIR = os.path.join(IDX, "veccache")
COV = os.path.join(IDX, "vectorize_coverage.tsv")
DPI = 200


def _one(task):
    doc_id, page, path, dpi = task
    try:
        p = vectorize.ensure(VECDIR, doc_id, page, path, dpi)
        if not p:
            return (doc_id, page, 0, 0)
        try:
            svg = open(p, encoding="utf-8").read(); return (doc_id, page, os.path.getsize(p), svg.count("Z"))
        except Exception:
            return (doc_id, page, os.path.getsize(p) if os.path.exists(p) else 0, 0)
    except Exception:
        return (doc_id, page, -1, 0)


def _auto_workers():
    n = os.cpu_count() or 4
    return max(2, min(n - 1, 10))   # vectorize is memory-heavier than CAD; slightly lower cap


def _figure_pages(limit):
    con = sqlite3.connect("file:%s?mode=ro" % DB, uri=True); con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT DISTINCT p.document_id AS doc, p.page AS page, d.path AS path "
        "FROM parts p JOIN documents d ON d.id=p.document_id "
        "WHERE p.fig_no IS NOT NULL AND p.page IS NOT NULL AND COALESCE(d.path,'')<>'' "
        "ORDER BY p.document_id, p.page").fetchall()
    con.close()
    seen = set(); out = []
    for r in rows:
        k = (r["doc"], r["page"])
        if k in seen: continue
        seen.add(k); out.append((r["doc"], int(r["page"]), r["path"]))
    return out[:limit] if limit else out


def main():
    if not vectorize.available():
        print("[ERROR] vectorizer unavailable — needs OpenCV (cv2) + numpy + Pillow on the host."); return 1
    if not os.path.exists(DB):
        print("[ERROR] index not found:", DB); return 1
    limit = None
    if "--limit" in sys.argv:
        try: limit = int(sys.argv[sys.argv.index("--limit") + 1])
        except Exception: limit = 100
    dpi = DPI
    if "--dpi" in sys.argv:
        try: dpi = max(72, min(600, int(sys.argv[sys.argv.index("--dpi") + 1])))
        except Exception: pass
    serial = "--serial" in sys.argv
    workers = _auto_workers()
    if "--workers" in sys.argv:
        try: workers = max(1, int(sys.argv[sys.argv.index("--workers") + 1]))
        except Exception: pass
    os.makedirs(VECDIR, exist_ok=True)

    pages = _figure_pages(limit)
    # resumable: skip pages already cached at this dpi
    todo = []; skipped = 0
    for doc, page, path in pages:
        out = vectorize.cache_path(VECDIR, doc, page, dpi)
        if os.path.exists(out) and os.path.getsize(out) > 0:
            skipped += 1
        else:
            todo.append((doc, page, path, dpi))
    total = len(pages); cores = os.cpu_count() or 0
    if serial or workers <= 1 or len(todo) < 2:
        workers = 1
    print("=== vectorize batch: %d figure pages (%d cached), %d to render · workers %d/%d · dpi %d ==="
          % (total, skipped, len(todo), workers, cores, dpi))
    if not os.path.exists(COV):
        open(COV, "w", encoding="utf-8").write("doc_id\tpage\tsvg_bytes\tcontours\n")

    t0 = time.time(); done = failed = 0; n = len(todo)
    covf = open(COV, "a", encoding="utf-8")

    def emit(row):
        nonlocal done, failed
        doc, page, sz, cz = row
        if sz > 0: done += 1
        else: failed += 1
        covf.write("%s\t%s\t%s\t%s\n" % (doc, page, sz, cz))
        i = done + failed
        if i % 50 == 0 or i == n:
            covf.flush(); el = time.time() - t0; rate = i / el if el else 0; eta = (n - i) / rate if rate else 0
            print("  %d/%d  ok=%d fail=%d  %.1f pg/s  ETA %dm%02ds" % (i, n, done, failed, rate, eta // 60, eta % 60))

    if workers == 1:
        for tsk in todo: emit(_one(tsk))
    else:
        from multiprocessing import Pool
        with Pool(processes=workers) as pool:
            for row in pool.imap_unordered(_one, todo, chunksize=4): emit(row)
    covf.close()
    el = time.time() - t0
    print("=== Done: vectorized %d pages, %d cached, %d failed in %.0fs. Cache: %s ==="
          % (done, skipped, failed, el, VECDIR))
    return 0


if __name__ == "__main__":
    sys.exit(main())
