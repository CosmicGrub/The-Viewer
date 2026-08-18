#!/usr/bin/env python3
"""THE VIEWER -- BORDERLESS + CROSS-PAGE TABLE RECOVERY (v1.2.3, catalog §2.2 + §2.3). PyMuPDF find_tables (tables.py)
only catches RULED tables; many TM spec/RPSTL tables have no grid lines, and long ones run across pages. This adds:
  §2.2 borderless extraction via pdfplumber's text-alignment strategy (cleans pdfplumber's empty-row artifacts), and
  §2.3 cross-page stitching (merge a table that continues onto the next page when column counts match and the
       continuation has no repeated header).
Read-only; degrades to [] if pdfplumber is absent. Feeds the tables sidecar / Masterfile spec detection. Corpus
authoritative."""
import os

try:
    import pdfplumber
    _OK = True
except Exception:
    pdfplumber = None; _OK = False


def available():
    return _OK


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


if __name__ == "__main__":
    if not _OK:
        print("pdfplumber unavailable; skipping"); raise SystemExit(0)
    import pymupdf as fitz, tempfile
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
# END OF FILE
