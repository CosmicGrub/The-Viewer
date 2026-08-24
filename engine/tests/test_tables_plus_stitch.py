#!/usr/bin/env python3
"""Regression coverage for the tables_plus.py audit finding: stitch() (cross-page borderless-table
merging, catalog §2.3) was implemented and unit-tested from day one but had no caller anywhere in
the served app -- /api/tables_plus (features/routes/doc_extractors.py) never built the ordered
(page, table) list it expects. Fixed by adding an explicit stitch=1 mode to that route; single-page
mode (the default) is unchanged.

Exercises the REAL route function directly (h/qs/core are lightweight fakes -- no need for a full
HTTP server to prove the routing logic + real tables_plus calls are wired correctly) against a REAL
multi-page PDF with genuine borderless (unruled) tables built via PyMuPDF, run through the REAL
pdfplumber-backed borderless_tables() + stitch(). Skips cleanly if pdfplumber isn't installed (same
convention tables_plus.py's own self-test uses) -- but pdfplumber is a hard requirements.txt
dependency, so this should never actually skip in a normal environment.
RUN ON WINDOWS / a coherent env (imports features.routes.doc_extractors). Pure stdlib + PyMuPDF."""
import os
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE)


class _FakeHandler:
    def __init__(self):
        self.sent = None
    def _send(self, code, body):
        self.sent = (code, body)


def _mkdoc(con, path, page_count):
    cur = con.execute("INSERT INTO documents(path, page_count) VALUES(?,?)", (path, page_count))
    return cur.lastrowid


def run():
    passed, failed = [], []
    def check(name, cond):
        (passed if cond else failed).append(name)

    try:
        import pymupdf as fitz
    except Exception:
        print("SKIP test_tables_plus_stitch.py (PyMuPDF not installed)")
        return [], []
    try:
        import tables_plus
    except Exception:
        print("SKIP test_tables_plus_stitch.py (tables_plus import failed)")
        return [], []
    if not tables_plus.available():
        print("SKIP test_tables_plus_stitch.py (pdfplumber not installed -- unexpected, it's a hard requirement)")
        return [], []

    import features.routes.doc_extractors as DE

    d = tempfile.mkdtemp(prefix="tables_plus_stitch_test_")
    pdf_path = os.path.join(d, "spec.pdf")
    doc = fitz.open()
    p1 = doc.new_page(width=400, height=260)
    for r, row in enumerate([["ITEM", "DIMENSION", "UNIT"], ["Overall length", "180", "in"],
                             ["Curb weight", "5200", "lb"], ["Height", "84", "in"]]):
        for c, val in enumerate(row):
            p1.insert_text((40 + c * 130, 60 + r * 30), val, fontsize=10)
    # page 2 repeats the header (a realistic continuation banner) then new rows -- stitch() must
    # detect + drop the repeated header, not double-count it.
    p2 = doc.new_page(width=400, height=260)
    for r, row in enumerate([["ITEM", "DIMENSION", "UNIT"], ["Fording depth", "30", "in"],
                             ["Ground clearance", "16", "in"], ["Wheelbase", "131", "in"]]):
        for c, val in enumerate(row):
            p2.insert_text((40 + c * 130, 60 + r * 30), val, fontsize=10)
    doc.save(pdf_path); doc.close()

    db_path = os.path.join(d, "viewer.db")
    con = sqlite3.connect(db_path)
    con.execute("CREATE TABLE documents(id INTEGER PRIMARY KEY, path TEXT, page_count INTEGER)")
    doc_id = _mkdoc(con, pdf_path, 2)
    con.commit()

    class _FakeCore:
        DB_PATH = db_path
        @staticmethod
        def db():
            c = sqlite3.connect(db_path); c.row_factory = sqlite3.Row
            return c
        @staticmethod
        def doc_path(did):
            r = con.execute("SELECT path FROM documents WHERE id=?", (did,)).fetchone()
            return r[0] if r else None

    orig_core = DE.core
    DE.core = _FakeCore
    try:
        # --- default (single-page) mode is UNCHANGED -- no stitch param ---
        h1 = _FakeHandler()
        DE.r_tables_plus(h1, {"doc": [str(doc_id)], "page": ["1"]})
        code1, body1 = h1.sent
        r1 = body1   # h._send(code, body) hands the real handler a dict, not JSON bytes, to serialize
        check("single-page mode: 200 + JSON", code1 == 200)
        check("single-page mode: returns exactly page 1's table, unstitched", r1.get("page") == 1
              and len(r1.get("tables") or []) == 1 and r1["tables"][0]["n_rows"] == 4)
        check("single-page mode: no 'stitched' key (unchanged response shape)", "stitched" not in r1)

        # --- stitch=1 mode: the whole document, cross-page continuation merged ---
        h2 = _FakeHandler()
        DE.r_tables_plus(h2, {"doc": [str(doc_id)], "stitch": ["1"]})
        code2, body2 = h2.sent
        r2 = body2
        check("stitch=1 mode: 200 + JSON", code2 == 200)
        check("stitch=1 mode: marks the response as stitched", r2.get("stitched") is True)
        tbls2 = r2.get("tables") or []
        check("stitch=1 mode: merged into exactly ONE table (not two per-page fragments)", len(tbls2) == 1)
        if tbls2:
            check("stitch=1 mode: spans both source pages", tbls2[0].get("pages") == [1, 2])
            check("stitch=1 mode: 7 total rows (4 + 3, repeated header on page 2 correctly dropped)",
                  tbls2[0].get("n_rows") == 7)
            flat = [c for row in tbls2[0]["rows"] for c in row]
            check("stitch=1 mode: data from BOTH pages present in the merged table",
                  "Overall length" in flat and "Wheelbase" in flat)
            check("stitch=1 mode: the repeated header appears only ONCE",
                  sum(1 for row in tbls2[0]["rows"] if row == ["ITEM", "DIMENSION", "UNIT"]) == 1)

        # --- a document with no borderless tables at all -> stitch=1 degrades to an empty list, not a crash ---
        blank_pdf = os.path.join(d, "blank.pdf")
        bd = fitz.open(); bd.new_page(); bd.save(blank_pdf); bd.close()
        blank_id = _mkdoc(con, blank_pdf, 1); con.commit()
        h3 = _FakeHandler()
        DE.r_tables_plus(h3, {"doc": [str(blank_id)], "stitch": ["1"]})
        code3, body3 = h3.sent
        r3 = body3
        check("stitch=1 on a blank document: 200 + empty tables, no crash", code3 == 200 and r3.get("tables") == [])

        # --- a nonexistent doc id -> degrades cleanly, no crash, no path resolved ---
        h4 = _FakeHandler()
        DE.r_tables_plus(h4, {"doc": ["999999"], "stitch": ["1"]})
        code4, body4 = h4.sent
        r4 = body4
        check("stitch=1 on an unknown doc id: 200 + empty tables, no crash", code4 == 200 and r4.get("tables") == [])
    finally:
        DE.core = orig_core

    return passed, failed


if __name__ == "__main__":
    p, f = run()
    for n in p: print("PASS", n)
    for n in f: print("FAIL", n)
    print("\n%d passed, %d failed" % (len(p), len(f)))
    sys.exit(1 if f else 0)

# END OF FILE
