#!/usr/bin/env python3
"""THE VIEWER -- HEURISTIC LAYOUT ANALYSIS (v1.3.2, catalog §2.4). Segments a page into logical regions -- title,
heading, paragraph, caption, header, footer, figure -- WITHOUT a heavy ML layout model. It reads PyMuPDF's native block
structure (position, font size, block type) and classifies by relative font size + page position. That gives reading
order, header/footer bands, and figure/caption regions that make every other extractor sharper (and can drive
per-region routing). PyMuPDF only; degrades to [] if fitz is absent. Read-only on the corpus."""
import os
import statistics

try:
    import pymupdf as fitz
    _OK = True
except Exception:
    fitz = None; _OK = False


def available():
    return _OK


def analyze(pdf_path, page, header_frac=0.08, footer_frac=0.92):
    """Return [{type, bbox:[x0,y0,x1,y1], text, size}] for one page (1-based). Types: title, heading, paragraph,
    caption, header, footer, figure. Ordered top-to-bottom (reading order)."""
    if not _OK or not pdf_path or not os.path.exists(pdf_path):
        return []
    out = []
    try:
        d = fitz.open(pdf_path)
        pg = d[int(page) - 1]
        ph = pg.rect.height or 1.0
        raw = pg.get_text("dict")
        blocks = raw.get("blocks", [])
        # gather text block sizes to get a page baseline
        sizes = []
        for b in blocks:
            if b.get("type", 0) == 0:
                for ln in b.get("lines", []):
                    for sp in ln.get("spans", []):
                        if sp.get("size"):
                            sizes.append(sp["size"])
        med = statistics.median(sizes) if sizes else 10.0
        for b in blocks:
            x0, y0, x1, y1 = b.get("bbox", (0, 0, 0, 0))
            ymid = (y0 + y1) / 2.0
            if b.get("type", 0) == 1:                       # image block
                out.append({"type": "figure", "bbox": [round(x0), round(y0), round(x1), round(y1)], "text": "", "size": 0})
                continue
            spans = [sp for ln in b.get("lines", []) for sp in ln.get("spans", [])]
            if not spans:
                continue
            text = " ".join(sp.get("text", "") for sp in spans).strip()
            if not text:
                continue
            bsize = max((sp.get("size", med) for sp in spans), default=med)
            frac = ymid / ph
            # Size-based checks run first so a genuinely large title/heading near the top (or bottom) of
            # the page is classified by its font size rather than being swallowed by the position-based
            # header/footer band -- a real running header/footer is small text, not a large one.
            if bsize >= 1.6 * med and frac < 0.30:
                typ = "title"
            elif bsize >= 1.25 * med:
                typ = "heading"
            elif frac <= header_frac:
                typ = "header"
            elif frac >= footer_frac:
                typ = "footer"
            elif bsize <= 0.85 * med:
                typ = "caption"
            else:
                typ = "paragraph"
            out.append({"type": typ, "bbox": [round(x0), round(y0), round(x1), round(y1)],
                        "text": text[:300], "size": round(bsize, 1)})
        d.close()
    except Exception:
        return out
    out.sort(key=lambda r: (r["bbox"][1], r["bbox"][0]))    # reading order: top-to-bottom, left-to-right
    return out


def summarize(regions):
    c = {}
    for r in regions:
        c[r["type"]] = c.get(r["type"], 0) + 1
    return {"n": len(regions), **c}


if __name__ == "__main__":
    if not _OK:
        print("fitz unavailable; skipping"); raise SystemExit(0)
    import tempfile
    d = fitz.open(); pg = d.new_page(width=400, height=520)
    pg.insert_text((40, 30), "TM 9-2320-280-24  Running Header", fontsize=8)          # header (top)
    pg.insert_text((40, 90), "CHAPTER 2  MAINTENANCE", fontsize=24)                    # title (large, upper)
    pg.insert_text((40, 140), "2-1. Scope", fontsize=15)                              # heading
    pg.insert_text((40, 180), "This paragraph describes the maintenance procedure in normal body text at ten point size for the section.", fontsize=10)
    pg.insert_text((40, 300), "Figure 2-1. Alternator assembly", fontsize=8)          # caption (small)
    pg.insert_text((40, 500), "Change 2                          2-1", fontsize=8)    # footer (bottom)
    pm = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 60, 60)); pm.set_rect(pm.irect, (180, 180, 180))
    pg.insert_image(fitz.Rect(60, 330, 160, 430), pixmap=pm)                          # figure (image block)
    p = os.path.join(tempfile.mkdtemp(), "l.pdf"); d.save(p); d.close()

    reg = analyze(p, 1)
    s = summarize(reg)
    types = {r["type"] for r in reg}
    assert "title" in types, ("title not found", [(r["type"], r["text"][:20]) for r in reg])
    assert "header" in types and "footer" in types, ("header/footer", s)
    assert "figure" in types, ("figure block not detected", s)
    assert any(r["type"] == "paragraph" for r in reg), ("paragraph", s)
    # reading order: header (top) comes before footer (bottom)
    ys = [r["bbox"][1] for r in reg]
    assert ys == sorted(ys), "not in reading order"
    print("layout self-test OK  (%s)" % s)
# END OF FILE
