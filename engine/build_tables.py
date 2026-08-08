#!/usr/bin/env python3
"""THE VIEWER -- TABLES SIDECAR BUILDER (v1.1.1). Walks every page of every PDF in the corpus (READ-ONLY) via
tables.extract_page (PyMuPDF find_tables) and records which pages carry structured tables -- especially SPEC/dimension
tables (cells with measurement units). Writes a tables.db sidecar (append-only; never touches the corpus/index -- R1/R6).
Resumable per-doc. Run host-side (BUILD-TABLES.bat) when OCR is paused. Lets /api/tables and coverage report 'this doc
has N spec tables on pages X,Y,Z' without re-parsing PDFs at query time."""
import os, sys, sqlite3, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tables  # noqa: E402

DB = os.environ.get("VIEWER_DB", os.path.join(os.path.dirname(HERE), "index", "viewer.db"))
SIDE = os.environ.get("TABLES_DB", os.path.join(os.path.dirname(HERE), "index", "tables.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS tbl(
  id INTEGER PRIMARY KEY, doc INTEGER, page INTEGER, n_rows INTEGER, n_cols INTEGER,
  spec INTEGER, units TEXT);
CREATE INDEX IF NOT EXISTS ix_tbl_doc  ON tbl(doc);
CREATE INDEX IF NOT EXISTS ix_tbl_spec ON tbl(spec);
CREATE TABLE IF NOT EXISTS tbl_done(doc INTEGER PRIMARY KEY, ts REAL);
"""


def main():
    if not tables.available():
        print("PyMuPDF (fitz) not installed; cannot extract tables. pip install pymupdf"); return 2
    if not os.path.exists(DB):
        print("viewer.db not found at", DB); return 2
    src = sqlite3.connect("file:%s?mode=ro" % DB, uri=True); src.row_factory = sqlite3.Row
    side = sqlite3.connect(SIDE); side.executescript(SCHEMA)
    done = {r[0] for r in side.execute("SELECT doc FROM tbl_done")}
    docs = src.execute("SELECT id, path, "
                       "(SELECT COUNT(*) FROM pages WHERE document_id=documents.id) n "
                       "FROM documents ORDER BY id").fetchall()
    built = skipped = ntab = nspec = 0; t0 = time.time()
    for d in docs:
        doc_id, path, npages = d["id"], d["path"], d["n"]
        if doc_id in done:
            skipped += 1; continue
        if not path or not os.path.exists(path):
            side.execute("INSERT OR REPLACE INTO tbl_done(doc,ts) VALUES(?,?)", (doc_id, time.time()))
            side.commit(); continue
        side.execute("DELETE FROM tbl WHERE doc=?", (doc_id,))
        for pg in range(1, (npages or 0) + 1):
            for t in tables.extract_page(path, pg):
                side.execute("INSERT INTO tbl(doc,page,n_rows,n_cols,spec,units) VALUES(?,?,?,?,?,?)",
                             (doc_id, pg, t["n_rows"], t["n_cols"], 1 if t["spec"] else 0, ",".join(t["units"])))
                ntab += 1; nspec += 1 if t["spec"] else 0
        side.execute("INSERT OR REPLACE INTO tbl_done(doc,ts) VALUES(?,?)", (doc_id, time.time()))
        side.commit(); built += 1
        if built % 10 == 0:
            print("  %d docs  (%d tables, %d spec, %.0fs)" % (built, ntab, nspec, time.time() - t0), flush=True)
    side.execute("ANALYZE"); side.commit()
    tot = side.execute("SELECT COUNT(*) FROM tbl").fetchone()[0]
    sp = side.execute("SELECT COUNT(*) FROM tbl WHERE spec=1").fetchone()[0]
    print("DONE: built %d docs, skipped %d. Sidecar total: %d tables (%d spec/dimension)." % (built, skipped, tot, sp))
    src.close(); side.close(); return 0


if __name__ == "__main__":
    raise SystemExit(main())
# END OF FILE
