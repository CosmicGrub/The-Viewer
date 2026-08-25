#!/usr/bin/env python3
"""Route-level coverage for `/api/layout` (catalog §2.4) and its column-aware reading order (catalog §2.5,
`layout.py`'s `_reading_order()` / `_column_order()`). A repo-wide grep found /api/layout had NO test
coverage at all before this file (not even the blanket bare-GET crash-sweep would prove anything beyond
"no 5xx") -- `test_routes.py` now hits it with real params in its curated list, and THIS file goes further:
it exercises the REAL route function (`doc_extractors.r_layout`) directly, the same lightweight h/qs/core-
fake pattern `test_tables_plus_stitch.py` already established for a sibling per-page extractor route, against
a REAL 2-column PDF built with PyMuPDF, asserting the actual JSON response comes back in column-aware
order -- not just calling `layout.analyze()` in isolation the way layout.py's own __main__ self-test does.
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
        print("SKIP test_layout_route.py (PyMuPDF not installed)")
        return [], []

    import layout
    if not layout.available():
        print("SKIP test_layout_route.py (layout.py unavailable -- unexpected, PyMuPDF is a hard requirement)")
        return [], []

    import features.routes.doc_extractors as DE

    d = tempfile.mkdtemp(prefix="layout_route_test_")

    # --- a genuine 2-column page: full-width header + title, 3 left-column paragraphs and 3 right-
    # column paragraphs with pairwise-overlapping y-ranges (the exact shape a flat (y, x) sort
    # interleaves), full-width footer. Same fixture shape as layout.py's own __main__ self-test.
    pdf_path = os.path.join(d, "twocol.pdf")
    doc = fitz.open(); pg = doc.new_page(width=640, height=700)
    pg.insert_text((40, 30), "TM 9-2320-280-24  RUNNING HEADER FOR THE COOLING SYSTEM CHAPTER", fontsize=8)
    pg.insert_text((40, 90), "CHAPTER 3  COOLING SYSTEM MAINTENANCE PROCEDURES", fontsize=24)
    pg.insert_text((40, 150), "Radiator inspection steps go here", fontsize=10)     # left 1
    pg.insert_text((320, 160), "Hose clamp torque specification", fontsize=10)      # right 1 (overlaps left 1's y)
    pg.insert_text((40, 220), "Thermostat replacement procedure", fontsize=10)      # left 2
    pg.insert_text((320, 230), "Fan clutch inspection procedure", fontsize=10)      # right 2 (overlaps left 2's y)
    pg.insert_text((40, 290), "Water pump removal steps follow", fontsize=10)       # left 3
    pg.insert_text((320, 300), "Coolant reservoir pressure test", fontsize=10)      # right 3 (overlaps left 3's y)
    pg.insert_text((40, 660), "Change 3                                                              3-1", fontsize=8)
    doc.save(pdf_path); doc.close()

    db_path = os.path.join(d, "viewer.db")
    con = sqlite3.connect(db_path)
    con.execute("CREATE TABLE documents(id INTEGER PRIMARY KEY, path TEXT, page_count INTEGER)")
    doc_id = _mkdoc(con, pdf_path, 1)
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
        h = _FakeHandler()
        DE.r_layout(h, {"doc": [str(doc_id)], "page": ["1"]})
        code, body = h.sent
        check("/api/layout: 200 + JSON", code == 200)
        check("/api/layout: available=True (PyMuPDF is a hard requirement)", body.get("available") is True)
        regions = body.get("regions") or []
        texts = [r["text"][:8] for r in regions]
        check("/api/layout: real route returns column-aware order (header, title, LEFT col x3, RIGHT col x3, footer)",
              texts == ["TM 9-232", "CHAPTER ", "Radiator", "Thermost", "Water pu",
                        "Hose cla", "Fan clut", "Coolant ", "Change 3"])
        check("/api/layout: summary n matches region count", body.get("summary", {}).get("n") == len(regions))

        # --- a single-column page through the same real route: must be flat (y, x) order, unaffected ---
        single_pdf = os.path.join(d, "single.pdf")
        sd = fitz.open(); spg = sd.new_page(width=400, height=300)
        spg.insert_text((40, 30), "Header text here", fontsize=8)
        spg.insert_text((40, 90), "Body paragraph one describing the procedure in normal text.", fontsize=10)
        spg.insert_text((40, 150), "Body paragraph two continues describing the procedure here too.", fontsize=10)
        sd.save(single_pdf); sd.close()
        single_id = _mkdoc(con, single_pdf, 1); con.commit()
        h2 = _FakeHandler()
        DE.r_layout(h2, {"doc": [str(single_id)], "page": ["1"]})
        code2, body2 = h2.sent
        regions2 = body2.get("regions") or []
        ys2 = [r["bbox"][1] for r in regions2]
        check("/api/layout: single-column page stays flat top-to-bottom order (no false-positive column split)",
              code2 == 200 and ys2 == sorted(ys2))

        # --- a nonexistent doc id degrades cleanly, no crash ---
        h3 = _FakeHandler()
        DE.r_layout(h3, {"doc": ["999999"], "page": ["1"]})
        code3, body3 = h3.sent
        check("/api/layout: unknown doc id -> 200 + empty regions, no crash",
              code3 == 200 and body3.get("regions") == [])
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
