#!/usr/bin/env python3
"""Precompute Living-Schematic netlists for every VECTOR schematic page in the corpus into
index/schemcache/<doc>_<page>.json, and write a coverage report (index/schemgraph_coverage.tsv).

Read-only on the index (R1); sidecar output only (R6). Resumable (skips docs already done) and parallel
(one worker per document — the PDF is opened once per doc). RUN ON WINDOWS (host).

  python build_schemgraph.py                 # whole corpus, all cores
  python build_schemgraph.py --limit 40      # first N documents (quick test)
  python build_schemgraph.py --workers 8     # cap workers
  python build_schemgraph.py --min-edges 8   # min wire-segments to count a page as a schematic (default 8)
  python build_schemgraph.py --serial        # single-threaded (debug)
"""
import os, sys, sqlite3, time, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import schem_overlay, schemgraph

DB = os.path.abspath(os.path.join(HERE, "..", "index", "viewer.db"))
IDX = os.path.dirname(DB)
SCHEMDIR = os.path.join(IDX, "schemcache")
COV = os.path.join(IDX, "schemgraph_coverage.tsv")
DONE = os.path.join(IDX, "schemgraph_done.txt")
MIN_EDGES = 8


def _process_doc(task):
    """Open one PDF once, scan its pages, cache netlists for vector schematic pages. Returns (doc_id, rows)."""
    doc_id, path, min_edges = task
    rows = []
    if not path or not str(path).lower().endswith(".pdf") or not os.path.exists(path):
        return (doc_id, rows)
    try:
        import fitz
        doc = fitz.open(path); n = doc.page_count; doc.close()
    except Exception:
        return (doc_id, rows)
    for pg in range(1, n + 1):
        try:
            raw = schem_overlay.schem_paths(path, pg)
        except Exception:
            continue
        if not raw.get("has_vector"):
            continue
        try:
            g = schemgraph.graph_from_paths(raw)
        except Exception:
            continue
        c = g.get("counts", {})
        if c.get("edges", 0) < min_edges:
            continue
        g["page"] = pg
        try:
            os.makedirs(SCHEMDIR, exist_ok=True)
            json.dump(g, open(schemgraph.cache_path(SCHEMDIR, doc_id, pg), "w", encoding="utf-8"))
        except Exception:
            pass
        rows.append((doc_id, pg, c.get("segments", 0), c.get("nodes", 0), c.get("edges", 0),
                     c.get("nets", 0), c.get("components", 0), g.get("confidence", 0.0)))
    return (doc_id, rows)


def _auto_workers():
    n = os.cpu_count() or 4
    return max(2, min(n - 1, 12))


def main():
    if not os.path.exists(DB):
        print("[ERROR] index not found:", DB); return 1
    limit = None
    if "--limit" in sys.argv:
        try: limit = int(sys.argv[sys.argv.index("--limit") + 1])
        except Exception: limit = 40
    min_edges = MIN_EDGES
    if "--min-edges" in sys.argv:
        try: min_edges = int(sys.argv[sys.argv.index("--min-edges") + 1])
        except Exception: pass
    serial = "--serial" in sys.argv
    workers = _auto_workers()
    if "--workers" in sys.argv:
        try: workers = max(1, int(sys.argv[sys.argv.index("--workers") + 1]))
        except Exception: pass
    os.makedirs(SCHEMDIR, exist_ok=True)

    done = set()
    if os.path.exists(DONE):
        try: done = set(int(x) for x in open(DONE, encoding="utf-8").read().split() if x.strip().isdigit())
        except Exception: done = set()

    con = sqlite3.connect("file:%s?mode=ro" % DB, uri=True); con.row_factory = sqlite3.Row
    docs = con.execute("SELECT id, path FROM documents ORDER BY id").fetchall()
    con.close()
    tasks = [(r["id"], r["path"], min_edges) for r in docs if r["id"] not in done]
    if limit:
        tasks = tasks[:limit]
    total_docs = len(tasks)
    cores = os.cpu_count() or 0
    if serial or workers <= 1 or total_docs < 2:
        workers = 1
    print("=== schemgraph batch: %d documents to scan (%d already done) · workers %d/%d · min-edges %d ==="
          % (total_docs, len(done), workers, cores, min_edges))
    if not os.path.exists(COV):
        open(COV, "w", encoding="utf-8").write("doc_id\tpage\tsegments\tnodes\tedges\tnets\tcomponents\tconfidence\n")

    t0 = time.time(); pages = 0; docs_done = 0
    covf = open(COV, "a", encoding="utf-8"); donef = open(DONE, "a", encoding="utf-8")

    def _emit(doc_id, rows):
        nonlocal pages, docs_done
        for r in rows:
            covf.write("\t".join(str(x) for x in r) + "\n"); pages += 1
        donef.write(str(doc_id) + "\n"); docs_done += 1
        if docs_done % 25 == 0 or docs_done == total_docs:
            covf.flush(); donef.flush()
            el = time.time() - t0; rate = docs_done / el if el else 0
            eta = (total_docs - docs_done) / rate if rate else 0
            print("  docs %d/%d  schematic-pages found=%d  %.1f doc/s  ETA %dm%02ds"
                  % (docs_done, total_docs, pages, rate, eta // 60, eta % 60))

    if workers == 1:
        for tsk in tasks:
            did, rows = _process_doc(tsk); _emit(did, rows)
    else:
        from multiprocessing import Pool
        with Pool(processes=workers) as pool:
            for did, rows in pool.imap_unordered(_process_doc, tasks, chunksize=1):
                _emit(did, rows)
    covf.close(); donef.close()
    el = time.time() - t0
    print("=== Done: scanned %d docs, cached %d schematic-page netlists in %.0fs. Coverage: %s ==="
          % (docs_done, pages, el, COV))
    return 0


if __name__ == "__main__":
    sys.exit(main())
