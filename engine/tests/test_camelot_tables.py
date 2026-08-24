#!/usr/bin/env python3
"""Regression guard for the camelot-py pilot in engine/tables_plus.py (a THIRD, independent table-extraction
engine for cross-validating tables.py's PyMuPDF find_tables against tables_plus.py's own pdfplumber path).
camelot-py is an OPTIONAL install (see requirements.txt) -- this file SKIPS cleanly (exit 0) when it isn't
present, exactly like tables_plus.py's own self-test, so CI (which installs only requirements.txt's hard/
recommended deps) is unaffected. Where camelot-py IS installed, every check below runs for real against a
synthetic ruled-table PDF built with reportlab (already a hard dependency) -- no corpus needed, no network."""
import os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ENG = os.path.dirname(HERE)
sys.path.insert(0, ENG)

import tables_plus  # noqa: E402
try:
    import tables  # PyMuPDF find_tables -- the ruled-table engine camelot cross-validates against
except Exception:
    tables = None

FAILS = []


def check(name, cond):
    print(("  ok  " if cond else "  FAIL") + "  " + name)
    if not cond:
        FAILS.append(name)


def _ruled_pdf(rows, col_widths=None):
    """Build a real ruled (grid-lined) table PDF via reportlab -- what camelot's default flavor='lattice'
    actually needs (vs. tables_plus.py's own borderless synthetic fixture, which has no ruling lines)."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    path = os.path.join(tempfile.mkdtemp(), "ruled.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter)
    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 1.0, colors.black),
                           ("FONTSIZE", (0, 0), (-1, -1), 10)]))
    doc.build([t])
    return path


def test_real_extraction():
    """The core pilot claim: camelot must genuinely read a ruled table's real cell data, not just return
    SOME non-empty structure."""
    from reportlab.lib.units import inch
    rows = [["ITEM", "NSN", "QTY", "UNIT"],
            ["Filter, oil", "2940-01-123-4567", "2", "EA"],
            ["Gasket, head", "5330-00-987-6543", "1", "EA"],
            ["Bolt, hex", "5306-00-111-2222", "8", "EA"],
            ["Washer, lock", "5310-00-333-4444", "8", "EA"]]
    path = _ruled_pdf(rows, [1.6 * inch, 1.8 * inch, 0.7 * inch, 0.7 * inch])
    tabs = tables_plus.camelot_tables(path, 1)
    check("camelot found a table", bool(tabs))
    if not tabs:
        return
    check("camelot got all 4 columns", tabs[0]["n_cols"] == 4)
    check("camelot got all 5 rows", tabs[0]["n_rows"] == 5)
    flat = [c for r in tabs[0]["rows"] for c in r]
    check("real NSN data recovered", "2940-01-123-4567" in flat and "5306-00-111-2222" in flat)
    check("real item names recovered", "Filter, oil" in flat and "Washer, lock" in flat)
    check("no fully-empty artifact rows", all(any(c.strip() for c in r) for r in tabs[0]["rows"]))


def test_empty_cell_survives():
    """A ruled table with a genuinely blank cell must not crash camelot_tables()'s row cleaning."""
    rows = [["ITEM", "NSN", "QTY"], ["Gasket", "", "1"], ["Bolt", "5306-00-111-2222", "8"]]
    path = _ruled_pdf(rows)
    tabs = tables_plus.camelot_tables(path, 1)
    check("empty-cell table still extracts", bool(tabs) and tabs[0]["n_rows"] == 3)


def test_no_table_page_degrades_empty():
    """A page with no ruled table at all must degrade to [] (not raise)."""
    from reportlab.pdfgen import canvas
    path = os.path.join(tempfile.mkdtemp(), "blank.pdf")
    c = canvas.Canvas(path)
    c.drawString(100, 700, "plain narrative text, no table on this page")
    c.save()
    tabs = tables_plus.camelot_tables(path, 1)
    check("no-table page returns []", tabs == [])


def test_missing_file_degrades_empty():
    tabs = tables_plus.camelot_tables(os.path.join(tempfile.mkdtemp(), "does_not_exist.pdf"), 1)
    check("missing file returns [] (no raise)", tabs == [])


def test_out_of_range_page_degrades_empty():
    rows = [["A", "B"], ["1", "2"]]
    path = _ruled_pdf(rows)
    tabs = tables_plus.camelot_tables(path, 99)
    check("out-of-range page returns [] (no raise)", tabs == [])


def test_backend_tier_gating():
    """_camelot_backend() must force 'poppler' on the legacy tier and leave camelot's own 'pdfium' default
    alone on the modern tier -- the same modern_os signal sysprobe.py's own render_backend fallback uses.
    Monkeypatches sysprobe.load_or_build() directly so this is deterministic regardless of THIS machine's
    real hardware tier."""
    here = ENG
    if here not in sys.path:
        sys.path.insert(0, here)
    import sysprobe
    orig = sysprobe.load_or_build
    try:
        sysprobe.load_or_build = lambda: {"modern_os": False}
        check("legacy tier forces poppler", tables_plus._camelot_backend() == "poppler")
        sysprobe.load_or_build = lambda: {"modern_os": True}
        check("modern tier uses camelot's pdfium default", tables_plus._camelot_backend() == "pdfium")
        sysprobe.load_or_build = lambda: (_ for _ in ()).throw(RuntimeError("probe glitch"))
        check("a probe glitch fails open to pdfium", tables_plus._camelot_backend() == "pdfium")
    finally:
        sysprobe.load_or_build = orig


def test_explicit_backend_override():
    """camelot_tables(..., backend=...) must let a caller override the tier auto-pick outright, and a
    forced 'poppler' with no poppler-utils on PATH must still degrade to a working result (camelot's own
    use_fallback=True), not an exception."""
    from reportlab.lib.units import inch
    rows = [["ITEM", "QTY"], ["Bolt", "8"], ["Nut", "8"]]
    path = _ruled_pdf(rows)
    tabs = tables_plus.camelot_tables(path, 1, backend="poppler")
    check("forced poppler backend still extracts (falls back if poppler-utils absent)", bool(tabs))


def test_disabled_dependency_degrades_empty():
    """With the pilot's own availability gate forced off, camelot_tables() must degrade to [] cleanly --
    exactly the pattern borderless_tables() already uses for a missing pdfplumber."""
    rows = [["ITEM", "QTY"], ["Bolt", "8"]]
    path = _ruled_pdf(rows)
    orig = tables_plus._CAMELOT_OK
    try:
        tables_plus._CAMELOT_OK = False
        check("disabled dependency returns [] (no raise)", tables_plus.camelot_tables(path, 1) == [])
    finally:
        tables_plus._CAMELOT_OK = orig


def test_cross_validates_against_pymupdf_tables():
    """The actual PILOT POINT: on the SAME ruled-table PDF, camelot (independent engine) and tables.py
    (PyMuPDF find_tables, the engine THE VIEWER already ships) must agree on row/column shape -- that
    agreement is what makes camelot useful as a cross-validation source rather than just another opinion."""
    if tables is None or not tables.available():
        print("  skip  cross-validation vs tables.py (PyMuPDF not installed)"); return
    from reportlab.lib.units import inch
    rows = [["ITEM", "DIM", "UNIT"], ["Overall length", "180", "in"], ["Curb weight", "5200", "lb"],
            ["Fording depth", "30", "in"]]
    path = _ruled_pdf(rows, [2.2 * inch, 1.0 * inch, 0.8 * inch])
    pymupdf_tabs = tables.extract_page(path, 1)
    camelot_tabs = tables_plus.camelot_tables(path, 1)
    check("both engines found a table", bool(pymupdf_tabs) and bool(camelot_tabs))
    if pymupdf_tabs and camelot_tabs:
        check("row counts agree", pymupdf_tabs[0]["n_rows"] == camelot_tabs[0]["n_rows"])
        check("column counts agree", pymupdf_tabs[0]["n_cols"] == camelot_tabs[0]["n_cols"])
        cflat = [c for r in camelot_tabs[0]["rows"] for c in r]
        check("camelot independently recovered the same figures", "180" in cflat and "5200" in cflat)


def run():
    if not tables_plus.camelot_available():
        print("camelot-py not installed (optional -- see requirements.txt); pilot regression skipped")
        return
    print("== camelot-py pilot regression (engine/tables_plus.py) ==")
    test_real_extraction()
    test_empty_cell_survives()
    test_no_table_page_degrades_empty()
    test_missing_file_degrades_empty()
    test_out_of_range_page_degrades_empty()
    test_backend_tier_gating()
    test_explicit_backend_override()
    test_disabled_dependency_degrades_empty()
    test_cross_validates_against_pymupdf_tables()


if __name__ == "__main__":
    run()
    print(("FAILED: " + ", ".join(FAILS)) if FAILS else "ALL CAMELOT PILOT TESTS PASS")
    sys.exit(1 if FAILS else 0)
# END OF FILE
