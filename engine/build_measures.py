#!/usr/bin/env python3
"""THE VIEWER -- MEASUREMENTS SIDECAR BUILDER (v1.1.0). Walks every OCR'd/native-text page in viewer.db (READ-ONLY) and
runs measures.extract over it, writing every measured quantity into a separate measures.db sidecar (append-only, never
touches the corpus or the big index -- R1/R6). Resumable: skips docs already at their current page-count. Run host-side
(BUILD-MEASURES.bat) whenever OCR is paused. The /measures page works WITHOUT this (on-the-fly FTS); the sidecar just
enables corpus-wide browsing/counts (e.g. 'every torque spec in the fleet')."""
import os, sys, sqlite3, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import measures  # noqa: E402
try:
    import leadingspecs  # noqa: E402  (named leading-particulars → measurements; optional)
except Exception:
    leadingspecs = None

DB = os.environ.get("VIEWER_DB", os.path.join(os.path.dirname(HERE), "index", "viewer.db"))
SIDE = os.environ.get("MEASURES_DB", os.path.join(os.path.dirname(HERE), "index", "measures.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS meas(
  id INTEGER PRIMARY KEY, doc INTEGER, page INTEGER, type TEXT, unit TEXT,
  value TEXT, value2 TEXT, tolerance TEXT, raw TEXT, context TEXT);
CREATE INDEX IF NOT EXISTS ix_meas_doc  ON meas(doc);
CREATE INDEX IF NOT EXISTS ix_meas_type ON meas(type);
CREATE TABLE IF NOT EXISTS meas_done(doc INTEGER PRIMARY KEY, pages INTEGER, ts REAL);
"""


def main():
    if not os.path.exists(DB):
        print("viewer.db not found at", DB); return 2
    src = sqlite3.connect("file:%s?mode=ro" % DB, uri=True); src.row_factory = sqlite3.Row
    side = sqlite3.connect(SIDE); side.executescript(SCHEMA)
    done = {r[0]: r[1] for r in side.execute("SELECT doc, pages FROM meas_done")}
    docs = src.execute("SELECT id, COALESCE(vehicle,'') v, "
                       "(SELECT COUNT(*) FROM pages WHERE document_id=documents.id) n "
                       "FROM documents ORDER BY id").fetchall()
    total_docs = len(docs); built = skipped = nmeas = 0; t0 = time.time()
    for d in docs:
        doc_id, npages = d["id"], d["n"]
        if done.get(doc_id) == npages:
            skipped += 1; continue
        side.execute("DELETE FROM meas WHERE doc=?", (doc_id,))
        cnt = 0
        for pr in src.execute("SELECT page_number pg, body_text bt FROM pages WHERE document_id=? ORDER BY page_number",
                              (doc_id,)):
            body = pr["bt"] or ""
            page_rows = measures.extract(body, page=pr["pg"], cap=120)
            # also pull NAMED leading-particulars ("Length: 180 in") so labelled specs reach the Masterfile (§3.6)
            try:
                page_rows = page_rows + leadingspecs.as_measurements(body, page=pr["pg"])
            except Exception:
                pass
            for m in page_rows:
                side.execute("INSERT INTO meas(doc,page,type,unit,value,value2,tolerance,raw,context) "
                             "VALUES(?,?,?,?,?,?,?,?,?)",
                             (doc_id, pr["pg"], m["type"], m["unit"], m["value"], m.get("value2"),
                              m.get("tolerance"), m.get("raw"), m.get("context")))
                cnt += 1
        side.execute("INSERT OR REPLACE INTO meas_done(doc,pages,ts) VALUES(?,?,?)", (doc_id, npages, time.time()))
        side.commit(); built += 1; nmeas += cnt
        if built % 25 == 0:
            print("  %d/%d docs  (%d measurements, %.0fs)" % (built, total_docs, nmeas, time.time() - t0), flush=True)
    side.execute("ANALYZE"); side.commit()
    tot = side.execute("SELECT COUNT(*) FROM meas").fetchone()[0]
    bytype = side.execute("SELECT type, COUNT(*) c FROM meas GROUP BY type ORDER BY c DESC").fetchall()
    print("DONE: built %d docs, skipped %d, +%d measurements this run. Sidecar total: %d" %
          (built, skipped, nmeas, tot))
    print("by type:", {r[0]: r[1] for r in bytype})
    src.close(); side.close(); return 0


if __name__ == "__main__":
    raise SystemExit(main())
# END OF FILE
