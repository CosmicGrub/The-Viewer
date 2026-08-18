#!/usr/bin/env python3
"""THE VIEWER -- TABLE EXTRACTOR (v1.1.1). Pulls structured TABLES out of the PDFs (PyMuPDF find_tables) -- the RPSTL,
torque, PMCS, and especially the LEADING PARTICULARS / SPECIFICATION tables where dimensional data lives. Flags
'spec/dimension' tables (those whose cells carry measurement units, via measures) so a mechanic can jump straight to the
numbers. Read-only; build the sidecar host-side (build_tables.py) or extract per-page on the fly. Degrades to [] if fitz
is absent."""
import os, re

try:
    import fitz
    _OK = True
except Exception:
    fitz = None; _OK = False


def available():
    return _OK


def extract_page(pdf_path, page, max_tables=12):
    """Return a list of {rows, n_rows, n_cols, spec:bool, units} dicts for one page (1-based); rows is a grid of
    cell strings and units is the list of dimension types found in the table."""
    if not _OK or not pdf_path or not os.path.exists(pdf_path):
        return []
    out = []
    try:
        doc = fitz.open(pdf_path)
        pg = doc[int(page) - 1]
        finder = pg.find_tables()
        tabs = list(getattr(finder, "tables", finder))
        for t in tabs[:max_tables]:
            try:
                rows = t.extract()
            except Exception:
                continue
            rows = [[("" if c is None else str(c)).strip() for c in r] for r in rows if r]
            if not rows:
                continue
            units = _units_in(rows)
            out.append({"rows": rows[:60], "n_rows": len(rows), "n_cols": max(len(r) for r in rows),
                        "spec": bool(units), "units": sorted(units)[:8]})
        doc.close()
    except Exception:
        return out
    return out


def _units_in(rows):
    """Which measurement dimension types appear in the table cells (marks it a spec/dimension table)."""
    try:
        import measures
    except Exception:
        return set()
    flat = " ".join(c for r in rows for c in r if c)
    return set(m["type"] for m in measures.extract(flat, cap=80))


def counts_for_doc(pdf_path, max_pages=2000):
    """Quick tally: {pages_with_tables, total_tables, spec_tables} -- for coverage reporting.
    Low finding #47 (dead/broken): the extraction call was short-circuited by an `if False` (dead
    code, never executed) and `spec_tables` was never incremented anywhere in the loop -- this
    always returned 0 for spec_tables regardless of actual content. Fixed by extracting each
    table's cells (same as extract_page()) and reusing _units_in() to decide spec-ness, still
    inside the single fitz.open() session this function already had -- calling extract_page()
    itself per-page would reopen the PDF up to `max_pages` times, defeating the point of a "quick"
    tally."""
    if not _OK or not os.path.exists(pdf_path):
        return {"pages_with_tables": 0, "total_tables": 0, "spec_tables": 0}
    pw = tt = st = 0
    try:
        doc = fitz.open(pdf_path)
        for i in range(min(len(doc), max_pages)):
            finder = doc[i].find_tables()
            these = list(getattr(finder, "tables", finder))
            if these:
                pw += 1; tt += len(these)
                for t in these:
                    try:
                        rows = t.extract()
                    except Exception:
                        continue
                    rows = [[("" if c is None else str(c)).strip() for c in r] for r in rows if r]
                    if rows and _units_in(rows):
                        st += 1
        doc.close()
    except Exception:
        pass
    return {"pages_with_tables": pw, "total_tables": tt, "spec_tables": st}


if __name__ == "__main__":
    if not _OK:
        print("fitz unavailable; skipping"); raise SystemExit(0)
    import tempfile
    doc = fitz.open(); pg = doc.new_page(width=400, height=300)
    for i in range(4):
        y = 60 + i * 30; pg.draw_line((40, y), (360, y))
    for j in range(4):
        x = 40 + j * 107; pg.draw_line((x, 60), (x, 150))
    cells = [["ITEM", "DIMENSION", "UNIT"], ["Overall length", "180", "in"], ["Curb weight", "5200", "lb"]]
    for r, row in enumerate(cells):
        for cc, val in enumerate(row):
            pg.insert_text((48 + cc * 107, 78 + r * 30), val, fontsize=9)
    p = os.path.join(tempfile.mkdtemp(), "t.pdf"); doc.save(p); doc.close()
    res = extract_page(p, 1)
    print("tables found:", len(res))
    if res:
        print("  n_rows=%d n_cols=%d spec=%s units=%s" % (res[0]["n_rows"], res[0]["n_cols"], res[0]["spec"], res[0]["units"]))
        print("  rows:", res[0]["rows"])
    assert res and res[0]["n_rows"] == 3 and res[0]["spec"] and "length" in res[0]["units"], "table/spec detection failed"
    # Low finding #47: counts_for_doc() used to always return spec_tables=0 (dead `if False` short
    # circuit, st never incremented) -- the one spec table on this page must now be counted.
    counts = counts_for_doc(p)
    print("counts_for_doc:", counts)
    assert counts == {"pages_with_tables": 1, "total_tables": 1, "spec_tables": 1}, ("counts_for_doc broken", counts)
    print("tables self-test OK")
# END OF FILE
