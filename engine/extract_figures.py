#!/usr/bin/env python3
"""THE VIEWER -- bulk pre-extract every part's cited figure crop into the figcache sidecar.

The app extracts crops on demand and caches them, but this warms the WHOLE corpus up front so the 3D
collection previews and the "Manual illustration" tab are instant. Read-only on the index; writes only PNGs
into index/figcache/ (never the index, R1/R6). RUN ON WINDOWS (host) -- the multi-GB PDFs + index can't be
read coherently through a sandbox mount.

  python extract_figures.py [--db PATH] [--dpi 150] [--limit N]

Note on the GPU: figure-region detection here is a fast CPU/PyMuPDF heuristic (caption-anchored + graphic
union). The GPU pays off for OCR (already done) and an OPTIONAL image-similarity pass to pick the best crop
per part -- not for the page render itself, which is CPU/IO-bound. Kept honest and simple.
"""
import os, sqlite3, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import figures_feature as ff

DEFAULT_DB = os.path.join(HERE, "..", "index", "viewer.db")


def _connect(db):
    try:
        c = sqlite3.connect("file:%s?mode=ro" % db, uri=True, timeout=60); c.row_factory = sqlite3.Row
        c.execute("PRAGMA query_only=ON"); c.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone(); return c
    except sqlite3.OperationalError:
        c = sqlite3.connect("file:%s?immutable=1" % db, uri=True, timeout=60); c.row_factory = sqlite3.Row; return c


def main():
    db = DEFAULT_DB; dpi = 150; limit = 0; args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--db" and i + 1 < len(args): db = args[i + 1]
        if a == "--dpi" and i + 1 < len(args):
            try: dpi = int(args[i + 1])
            except Exception: pass
        if a == "--limit" and i + 1 < len(args):
            try: limit = int(args[i + 1])
            except Exception: pass
    db = os.path.abspath(db)
    if ff.fitz is None:
        print("[ERROR] PyMuPDF (fitz) not installed: pip install pymupdf"); return 1
    if not os.path.exists(db):
        print("[ERROR] index not found: %s" % db); return 1

    # point figures_feature at this db dir for the figcache location
    class _Core: pass
    ff.core = _Core(); ff.core.DB_PATH = db
    def _db():
        c = sqlite3.connect("file:%s?mode=ro" % db, uri=True); c.row_factory = sqlite3.Row; return c
    ff.core.db = _db

    con = _connect(db)
    rows = con.execute(
        "SELECT DISTINCT p.document_id AS doc_id, p.page AS page, d.path AS path "
        "FROM parts p JOIN documents d ON d.id=p.document_id "
        "WHERE p.page IS NOT NULL AND d.path IS NOT NULL "
        "ORDER BY p.document_id, p.page").fetchall()
    con.close()
    if limit: rows = rows[:limit]
    total = len(rows); done = ok = skip = fail = 0; t0 = time.time()
    print("=== Pre-extracting %d figure crops (dpi=%d) into index/figcache/ ===" % (total, dpi))
    cache = ff._figcache_dir()
    for r in rows:
        done += 1
        out = os.path.join(cache, "%d_%d_%d.png" % (r["doc_id"], r["page"], dpi))
        if os.path.exists(out) and os.path.getsize(out) > 0:
            skip += 1
        else:
            good, _ = ff.extract(r["path"], r["page"], dpi, out)
            ok += 1 if good else 0; fail += 0 if good else 1
        if done % 50 == 0 or done == total:
            rate = done / max(0.001, time.time() - t0)
            print("  %d/%d  (new %d, cached %d, failed %d)  %.1f/s" % (done, total, ok, skip, fail, rate))
    print("\nDone: %d crops cached in %s" % (ok + skip, cache))
    return 0


if __name__ == "__main__":
    sys.exit(main())
