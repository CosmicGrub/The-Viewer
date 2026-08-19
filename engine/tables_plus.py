#!/usr/bin/env python3
"""THE VIEWER -- BORDERLESS + CROSS-PAGE TABLE RECOVERY (v1.3.0, catalog §2.2 + §2.3). PyMuPDF find_tables (tables.py)
only catches RULED tables; many TM spec/RPSTL tables have no grid lines, and long ones run across pages. This adds:
  §2.2 borderless extraction via pdfplumber's text-alignment strategy (cleans pdfplumber's empty-row artifacts), and
  §2.3 cross-page stitching (merge a table that continues onto the next page when column counts match and the
       continuation has no repeated header).
Read-only; degrades to [] if pdfplumber is absent. Feeds the tables sidecar / Masterfile spec detection. Corpus
authoritative.

NOT WIRED IN YET: stitch() (the §2.3 merge logic itself) has no caller in the served app either -- /api/tables_plus
(features/routes/doc_extractors.py) resolves and returns exactly one page's tables via borderless_tables() and
never builds the ordered (page, table) list stitch() expects, and no ingest-pipeline step calls it. Its only
caller today is its own __main__ self-test below. A spec/RPSTL table that legitimately continues onto a
following page is therefore always returned to callers of /api/tables_plus as separate, unmerged per-page
fragments -- the merge logic itself is implemented and passes its own unit test, but nothing in the served app
invokes it yet, until a route or pipeline step is deliberately added to assemble that page list and call
stitch() on it.

PILOT (optional, off by default -- see requirements.txt): camelot_tables() is a THIRD, independent extraction
engine (camelot-py 2.0) for cross-validating tables.py (PyMuPDF, ruled) and this module's own borderless_tables()
(pdfplumber) against the same page. camelot-py 2.0 dropped the hard Ghostscript requirement -- its default
image-conversion backend is 'pdfium' (bundled pypdfium2, pure pip-installable, no external binary) -- so
_camelot_backend() only forces the legacy-toolchain 'poppler' backend explicitly on the legacy tier (same
modern_os signal sysprobe.py's own render_backend fallback uses); the modern tier leaves camelot's 'pdfium'
default alone. camelot hard-requires opencv-python-headless, which installs into the SAME cv2/ package path as
opencv-python (already in requirements.txt) -- confirmed via a real install: pip lets both co-exist, but they
ship different cv2.pyd binaries under that identical path, so whichever installs/upgrades second silently
overwrites the other's binary on disk. Verified harmless *today* only because both currently resolve to the same
opencv release (byte-identical files) and nothing in this codebase calls the GUI-only cv2 functions the headless
build lacks; a future version skew between the two separately-pinned specs would not be caught by `pip check`
and could break real cv2 users (vectorize/symbols/barcodes) at import time -- which is exactly why camelot-py
stays an opt-in pip-install-it-yourself extra rather than a hard requirements.txt dependency.
NOT WIRED IN YET: camelot_tables() has no caller in the served app -- /api/tables_plus (features/routes/
doc_extractors.py) calls only this module's borderless_tables(), and no ingest-pipeline step calls it either.
Its only callers today are its own __main__ self-test below and tests/test_camelot_tables.py. The actual
page-for-page cross-validation described above is exercised only by those two, not against real corpus pages,
until a route or pipeline step is deliberately added to call it."""
import os, sys

try:
    import pdfplumber
    _OK = True
except Exception:
    pdfplumber = None; _OK = False

try:
    import camelot
    _CAMELOT_OK = True
except Exception:
    camelot = None; _CAMELOT_OK = False


def available():
    return _OK


def camelot_available():
    return _CAMELOT_OK


def _clean(rows):
    """Drop pdfplumber's all-empty artifact rows and trailing empty cells; keep real rows."""
    out = []
    for r in rows or []:
        cells = [(c or "").strip() for c in r]
        if any(cells):
            out.append(cells)
    return out


def borderless_tables(pdf_path, page, max_tables=8):
    """Extract borderless (text-aligned) tables from one page (1-based) -> [{rows, n_rows, n_cols}]."""
    if not _OK or not pdf_path or not os.path.exists(pdf_path):
        return []
    out = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if page < 1 or page > len(pdf.pages):
                return []
            pg = pdf.pages[page - 1]
            settings = {"vertical_strategy": "text", "horizontal_strategy": "text", "snap_tolerance": 8}
            # extract_table (singular) aligns borderless columns far more cleanly than extract_tables here
            t = pg.extract_table(table_settings=settings)
            if t:
                rows = _clean(t)
                if len(rows) >= 2 and max(len(r) for r in rows) >= 2:
                    out.append({"rows": rows[:80], "n_rows": len(rows), "n_cols": max(len(r) for r in rows)})
    except Exception:
        return out
    return out


def _is_data_row(row):
    """A row that carries data (has at least one purely-numeric cell) -- the reliable 'this continues a table' signal."""
    return any((c or "").replace(",", "").replace(".", "").isdigit() for c in row if c)


def stitch(page_tables):
    """Merge tables that continue across pages. `page_tables` = ordered list of (page, table_dict). Two consecutive
    tables stitch when they have the SAME column count AND the later one either starts with a data row (no header) or
    repeats the previous header (which is then de-duplicated). Returns a list of {rows, n_rows, n_cols, pages} dicts
    where pages is the list of source page numbers merged into that table."""
    stitched = []
    for page, t in page_tables:
        if not t or not t.get("rows"):
            continue
        rows = t["rows"]; ncol = t.get("n_cols", max((len(r) for r in rows), default=0))
        if stitched:
            prev = stitched[-1]
            repeats_header = rows[0] == prev["rows"][0]
            if prev["n_cols"] == ncol and (_is_data_row(rows[0]) or repeats_header):
                add = rows[1:] if repeats_header else rows   # drop a duplicated header
                prev["rows"].extend(add)
                prev["n_rows"] = len(prev["rows"])
                prev["pages"].append(page)
                continue
        stitched.append({"rows": list(rows), "n_rows": len(rows), "n_cols": ncol, "pages": [page]})
    return stitched


def _camelot_backend():
    """Pick camelot's PDF->image conversion backend from the SAME legacy/modern signal sysprobe.py computes
    for the page-render engine (build_profile()'s modern_os = os_rank >= 100, i.e. Win10/11): the legacy tier
    forces Poppler explicitly (Poppler is the toolchain sysprobe already falls back to for page rendering
    there -- see render_backend in sysprobe.py), the modern tier leaves camelot's own 'pdfium' default alone
    (bundled pypdfium2 -- no external binary, no Ghostscript). Fail-open to 'pdfium' if the probe can't run
    for any reason -- a probe glitch must never break extraction (R1)."""
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        import sysprobe
        modern = sysprobe.load_or_build().get("modern_os", True)
    except Exception:
        modern = True
    return "pdfium" if modern else "poppler"


def camelot_tables(pdf_path, page, flavor="lattice", max_tables=8, backend=None):
    """Cross-validation extraction via camelot-py (pilot) -- a THIRD, independent table engine alongside
    tables.py (PyMuPDF find_tables, ruled) and this module's own borderless_tables() (pdfplumber). `page` is
    1-based, like borderless_tables(). `backend` overrides the tier-picked backend from _camelot_backend()
    when the caller wants a specific one; camelot's own use_fallback=True means even a forced 'poppler' still
    degrades to pdfium if poppler-utils isn't actually on PATH, so this never hard-fails on a legacy box that
    lacks it. Same {rows, n_rows, n_cols} shape as borderless_tables() so a caller can diff the two page-for-
    page. Read-only; degrades to [] if camelot-py is absent, the page has no table, or extraction fails for
    any reason."""
    if not _CAMELOT_OK or not pdf_path or not os.path.exists(pdf_path):
        return []
    out = []
    try:
        be = backend or _camelot_backend()
        result = camelot.read_pdf(pdf_path, pages=str(page), flavor=flavor, backend=be, use_fallback=True)
        tables_found = list(result)[:max_tables]
    except Exception:
        return out
    for t in tables_found:
        # per-table try: one malformed table (e.g. an unexpected t.df dtype) must not discard tables
        # already found on this page, nor skip tables still to come in the loop -- R1 degrades a single
        # bad table to "not found", not the whole page.
        try:
            raw = [[("" if c is None else str(c)) for c in row] for row in t.df.values.tolist()]
            rows = _clean(raw)
            if len(rows) >= 2 and max((len(r) for r in rows), default=0) >= 2:
                out.append({"rows": rows[:80], "n_rows": len(rows), "n_cols": max(len(r) for r in rows)})
        except Exception:
            continue
    return out


if __name__ == "__main__":
    import tempfile

    if not _OK:
        print("pdfplumber unavailable; borderless/stitch self-test skipped")
    else:
        import pymupdf as fitz
        # borderless spec table (no ruling lines)
        d = fitz.open(); pg = d.new_page(width=400, height=260)
        for r, row in enumerate([["ITEM", "DIMENSION", "UNIT"], ["Overall length", "180", "in"],
                                 ["Curb weight", "5200", "lb"], ["Fording depth", "30", "in"]]):
            for c, val in enumerate(row):
                pg.insert_text((40 + c * 130, 60 + r * 30), val, fontsize=10)
        p = os.path.join(tempfile.mkdtemp(), "b.pdf"); d.save(p); d.close()
        tabs = borderless_tables(p, 1)
        assert tabs and tabs[0]["n_cols"] >= 3, ("borderless", tabs)
        flat = [c for row in tabs[0]["rows"] for c in row]
        assert "180" in flat and "5200" in flat and "Curb weight" in flat, ("data recovered", tabs[0]["rows"])
        assert all(any(c.strip() for c in r) for r in tabs[0]["rows"]), ("no empty rows", tabs[0]["rows"])

        # cross-page stitch: page 1 has header+2 rows, page 2 continues with 2 more rows (no header) -> one 5-row table
        t1 = {"rows": [["ITEM", "DIM", "UNIT"], ["a", "1", "in"], ["b", "2", "in"]], "n_rows": 3, "n_cols": 3}
        t2 = {"rows": [["c", "3", "in"], ["d", "4", "in"]], "n_rows": 2, "n_cols": 3}
        st = stitch([(1, t1), (2, t2)])
        assert len(st) == 1 and st[0]["n_rows"] == 5 and st[0]["pages"] == [1, 2], ("stitch", st)
        # a table with its own header must NOT stitch
        t3 = {"rows": [["NAME", "QTY"], ["x", "9"]], "n_rows": 2, "n_cols": 2}
        st2 = stitch([(1, t1), (3, t3)])
        assert len(st2) == 2, ("no-stitch on header/col mismatch", st2)
        print("tables_plus self-test OK  (borderless extract + clean + cross-page stitch)")

    # camelot pilot regression now lives entirely in tests/test_camelot_tables.py (real ruled-table
    # extraction, empty-cell/no-table/missing-file/out-of-range-page degradation, explicit backend
    # override, disabled-dependency degradation, tier-gating incl. the probe-glitch case, and cross-
    # validation vs tables.py) -- strictly more coverage than duplicating a subset of it here would give.
# END OF FILE
