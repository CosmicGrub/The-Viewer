#!/usr/bin/env python3
"""THE VIEWER -- shared corpus FTS retrieval (v1.13.0). ONE implementation of the standard
"FTS-match pages + join documents" query that measures / ask / faulttree / cautions / pmcs each
carried privately -- every copy opened its own sqlite3.connect("file:...mode=ro") and LEAKED the
handle whenever the query raised (close() sat after the execute, inside the try). Centralizing it:

  * inside the running app (viewer_app injects `core`) it reuses the per-thread POOLED connection
    (core.db(); its .close() is a harmless no-op), so no fresh connect per request;
  * standalone (tests / CLI: `core is None` or a different db_path) it opens a private read-only
    connection and guarantees close via try/finally -- the leak class is gone;
  * the SQL is identical for every consumer (R13: same retrieval everywhere, cited the same way).

DI pattern matches the other feature modules: `core = None` here; viewer_app assigns at startup.
Read-only always; sqlite3.OperationalError (bad MATCH syntax / FTS missing) degrades to []."""
import re, sqlite3

core = None          # injected by viewer_app at startup; None when used standalone (tests/CLI)

_SQL = ("SELECT d.id AS doc_id, d.vehicle, d.tm_number, d.title, "
        "p.page_number, p.body_text AS body, p.ocr_confidence "
        "FROM pages_fts JOIN pages p ON p.id=pages_fts.rowid "
        "JOIN documents d ON d.id=p.document_id "
        "WHERE pages_fts MATCH ?%s ORDER BY rank LIMIT ?")


def _snippet(body, width=240):
    return re.sub(r"\s+", " ", (body or "")[: width * 2]).strip()[:width]


def fts_pages(match, limit=20, vehicle=None, with_body=False, db_path=None):
    """Standard corpus retrieval: FTS-match `match`, best-ranked pages first.
    Returns a list of dicts: {doc_id, vehicle, tm_number, title, page_number,
    body_text (with_body=True) | snippet (default), source:'corpus'}.
    `vehicle` filters on documents.vehicle (LIKE, substring). `db_path` is only needed
    standalone; inside the app the injected core's pooled connection is used (when the
    requested db IS the app db). OperationalError -> [] (degrade safe, never a 500)."""
    if not (match or "").strip():
        return []
    sql = _SQL % (" AND d.vehicle LIKE ?" if vehicle else "")
    params = [match]
    if vehicle:
        params.append("%" + str(vehicle).strip() + "%")
    params.append(int(limit))
    use_core = core is not None and (not db_path or db_path == getattr(core, "DB_PATH", None))
    try:
        if use_core:
            con = core.db()          # pooled per-thread; .close() is a no-op
        else:
            if not db_path:
                return []
            con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
            con.row_factory = sqlite3.Row
        try:
            rows = con.execute(sql, params).fetchall()
        finally:
            con.close()              # real close standalone; harmless no-op on the pool
    except sqlite3.OperationalError:
        return []
    out = []
    for r in rows:
        rec = {"doc_id": r["doc_id"], "vehicle": r["vehicle"], "tm_number": r["tm_number"],
               "title": r["title"], "page_number": r["page_number"], "source": "corpus",
               # real, engine-reported per-page OCR confidence (migration 0009; RapidOCR only --
               # NULL for Tesseract-fallback/native-text pages). Additive: existing consumers that
               # don't read this key are completely unaffected. See textquality.annotate()'s
               # real_confidence param -- this is what feeds it.
               "ocr_confidence": r["ocr_confidence"]}
        if with_body:
            rec["body_text"] = r["body"]
        else:
            rec["snippet"] = _snippet(r["body"])
        out.append(rec)
    return out


# --------------------------------------------------------------------------- #
# self-test: `python -m features.corpus` / `python features/corpus.py`        #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import os, tempfile
    d = tempfile.mkdtemp(); db = os.path.join(d, "c.db"); c = sqlite3.connect(db)
    c.execute("CREATE TABLE documents(id INTEGER PRIMARY KEY, vehicle TEXT, tm_number TEXT, title TEXT)")
    c.execute("CREATE TABLE pages(id INTEGER PRIMARY KEY, document_id INT, page_number INT, body_text TEXT, ocr_confidence REAL)")
    c.execute("CREATE VIRTUAL TABLE pages_fts USING fts5(body_text, content='pages', content_rowid='id')")
    c.execute("INSERT INTO documents VALUES(1,'HMMWV M998','TM 9-2320-280-10','Operator')")
    c.execute("INSERT INTO pages(document_id,page_number,body_text) VALUES(1,44,'Bleed the CTIS lines at each wheel valve.')")
    c.execute("INSERT INTO pages_fts(rowid, body_text) SELECT id, body_text FROM pages")
    c.commit(); c.close()
    rows = fts_pages("CTIS", db_path=db, with_body=True)
    assert len(rows) == 1 and rows[0]["doc_id"] == 1 and rows[0]["page_number"] == 44, rows
    assert rows[0]["tm_number"] == "TM 9-2320-280-10" and "CTIS" in rows[0]["body_text"], rows
    assert rows[0]["source"] == "corpus", rows
    snip = fts_pages("CTIS", db_path=db)
    assert "snippet" in snip[0] and "body_text" not in snip[0], snip
    veh = fts_pages("CTIS", db_path=db, vehicle="HMMWV")
    assert len(veh) == 1, veh
    assert fts_pages("CTIS", db_path=db, vehicle="ABRAMS") == []
    assert fts_pages('bad"syntax(', db_path=db) == []          # OperationalError -> []
    assert fts_pages("", db_path=db) == []
    assert fts_pages("CTIS") == []                             # no core, no db_path -> []
    print("corpus fts_pages self-test PASS (pooled-DI + standalone + vehicle filter + degrade-safe)")

# END OF FILE
