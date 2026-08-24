#!/usr/bin/env python3
"""Regression coverage for symbols.py's missing template-sourcing mechanism (a deferred item from
the flags audit): symbols.detect() was always fully built and self-tested, but nothing in the app
could ever GET a template image into index/symbols/ in the first place -- an operator had to
hand-crop and drop a PNG there manually, outside the app entirely. This adds the crop-and-save
route (/api/symbols_template) and the detection route (/api/symbols) that reads what it saves.

Exercises the REAL route functions directly (h/qs/payload/core are lightweight fakes -- no need for
a full HTTP server to prove the routing + real symbols.py calls are wired correctly) against a REAL
PDF with solid-filled shapes (matching symbols.py's own self-test convention -- a thin-outlined
shape is weak template-matching material and produces noisy results, not a wiring problem).
Skips cleanly if OpenCV isn't installed (symbols.py's own established convention).
RUN ON WINDOWS / a coherent env (imports features.routes.doc_extractors). Pure stdlib + PyMuPDF."""
import os
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


def run():
    passed, failed = [], []
    def check(name, cond):
        (passed if cond else failed).append(name)

    try:
        import pymupdf as fitz
    except Exception:
        print("SKIP test_symbols_routes.py (PyMuPDF not installed)")
        return [], []
    try:
        import symbols
    except Exception:
        print("SKIP test_symbols_routes.py (symbols import failed)")
        return [], []
    if not symbols.available():
        print("SKIP test_symbols_routes.py (OpenCV not installed)")
        return [], []

    import features.routes.doc_extractors as DE

    d = tempfile.mkdtemp(prefix="symbols_routes_test_")
    pdf_path = os.path.join(d, "schem.pdf")
    doc = fitz.open()
    p = doc.new_page(width=400, height=300)
    # two solid-filled squares -- matches symbols.py's own self-test convention (cv2.fillPoly, a
    # solid shape) rather than a thin-outlined one, which is weak template-matching material and
    # produces noisy/unreliable results unrelated to whether the WIRING is correct.
    p.draw_rect((40, 40, 90, 90), color=(0, 0, 0), fill=(0, 0, 0))
    p.draw_rect((260, 180, 310, 230), color=(0, 0, 0), fill=(0, 0, 0))
    doc.save(pdf_path); doc.close()

    db_path = os.path.join(d, "viewer.db")
    open(db_path, "w").close()

    class _FakeCore:
        DB_PATH = db_path
        @staticmethod
        def doc_path(did):
            return pdf_path if did == 5 else None

    orig_core = DE.core
    DE.core = _FakeCore
    try:
        # --- detection with no templates yet: available, but empty, not an error ---
        h1 = _FakeHandler()
        DE.r_symbols_detect(h1, {"doc": ["5"], "page": ["1"]})
        code1, body1 = h1.sent
        check("no templates yet: 200 + available=True", code1 == 200 and body1.get("available") is True)
        check("no templates yet: zero templates, zero matches (not an error)",
              body1.get("templates") == [] and body1.get("n") == 0 and body1.get("symbols") == [])
        check("no templates yet: real page dimensions still reported", body1.get("iw", 0) == 0)  # no render attempted without templates

        # --- saving a template: reject a bad/unsafe name (path-traversal attempt) ---
        h_bad_name = _FakeHandler()
        DE.r_symbols_template(h_bad_name, {}, {"doc": 5, "page": 1, "dpi": 150,
                                                "x": 30, "y": 30, "w": 70, "h": 70, "name": "../../evil"})
        check("save template: rejects a path-traversal-shaped name", h_bad_name.sent[0] == 400)

        # --- saving a template: reject a crop box that extends past the rendered page ---
        h_oob = _FakeHandler()
        DE.r_symbols_template(h_oob, {}, {"doc": 5, "page": 1, "dpi": 150,
                                          "x": 0, "y": 0, "w": 999999, "h": 999999, "name": "toobig"})
        check("save template: rejects an out-of-bounds crop box", h_oob.sent[0] == 400)

        # --- saving a template: reject a non-positive width/height ---
        h_zero = _FakeHandler()
        DE.r_symbols_template(h_zero, {}, {"doc": 5, "page": 1, "dpi": 150,
                                           "x": 30, "y": 30, "w": 0, "h": 70, "name": "zerowidth"})
        check("save template: rejects a zero-width crop box", h_zero.sent[0] == 400)

        # --- saving a template: an unknown document id ---
        h_nodoc = _FakeHandler()
        DE.r_symbols_template(h_nodoc, {}, {"doc": 999999, "page": 1, "dpi": 150,
                                            "x": 30, "y": 30, "w": 70, "h": 70, "name": "nodoc"})
        check("save template: an unknown document id -> 404, not a crash", h_nodoc.sent[0] == 404)

        # --- saving a REAL template: crop around the first square at dpi=150 ---
        # dpi=150 vs PDF's 72 dpi native -> scale factor 150/72 for the (40,40)-(90,90) rect
        scale = 150.0 / 72.0
        rx, ry = int(40 * scale) - 5, int(40 * scale) - 5
        rw = rh = int(50 * scale) + 10
        h_save = _FakeHandler()
        DE.r_symbols_template(h_save, {}, {"doc": 5, "page": 1, "dpi": 150,
                                           "x": rx, "y": ry, "w": rw, "h": rh, "name": "black square"})
        code_save, body_save = h_save.sent
        check("save template: 200 + ok=True for a real, in-bounds crop", code_save == 200 and body_save.get("ok") is True)
        check("save template: the name is sanitized (space -> underscore)", body_save.get("name") == "black_square")
        sym_dir = os.path.join(d, "symbols")
        check("save template: the PNG file actually landed on disk", os.path.exists(os.path.join(sym_dir, "black_square.png")))

        # --- detection now finds the saved template, on BOTH squares (a genuine repeated symbol) ---
        h2 = _FakeHandler()
        DE.r_symbols_detect(h2, {"doc": ["5"], "page": ["1"], "dpi": ["150"]})
        code2, body2 = h2.sent
        check("detect after saving: 200 + the new template is listed", code2 == 200 and body2.get("templates") == ["black_square"])
        hits = body2.get("symbols") or []
        check("detect after saving: at least 2 matches found (both solid squares)", len(hits) >= 2)
        check("detect after saving: every match is correctly named", all(hh["name"] == "black_square" for hh in hits))
        check("detect after saving: real page dimensions reported once a render actually happens",
              body2.get("iw", 0) > 0 and body2.get("ih", 0) > 0)
        # the second square is roughly at PDF (260,180)-(310,230) -> scaled x should land near there
        xs = sorted(hh["x"] for hh in hits[:2])
        check("detect after saving: matches land near BOTH real square locations, not just one",
              xs[0] < int(150 * scale) and xs[-1] > int(200 * scale))
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
