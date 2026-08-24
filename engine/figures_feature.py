#!/usr/bin/env python3
"""THE VIEWER -- authoritative part imagery: crop a part's CITED figure from the manual.

The accurate, legal, offline image of a part is the manual's own exploded-view illustration (US Army TMs are
public domain). Every part already cites a figure + page; this finds the best citation and crops the figure
region from that PDF page (PyMuPDF), caching the PNG to a SIDECAR dir (index/figcache/). The 3D collection's
preview boxes and a "Manual illustration" tab use these instead of a generic shape.

Region heuristic (born-digital and scanned pages both):
  1. If a "FIGURE n" caption is found, the figure is the area ABOVE it -> crop top..caption.
  2. else if the page's graphic regions (embedded images + vector drawings) cover a sensible sub-area, crop
     their union (with a small margin).
  3. else crop the top ~62% (RPSTL figures sit above the parts table); ultimate fallback = whole page.

Read-only on the index (R1/R6). `core` injected by viewer_app. Requires fitz (PyMuPDF); degrades to None.
"""
import os, re
try:
    import pymupdf as fitz
    # Silence cosmetic MuPDF stderr noise (e.g. "cmsOpenProfileFromMem failed" from PDFs with a broken
    # embedded ICC colour profile). MuPDF falls back to a default colour space and still renders the page,
    # so the crop is unaffected -- this just stops the harmless message from flooding the console.
    try: fitz.TOOLS.mupdf_display_errors(False)
    except Exception: pass
except Exception:
    fitz = None

core = None
_FIG_CAP = re.compile(r"\bFIG(?:URE)?\.?\s*\d", re.I)


def _figcache_dir():
    d = os.path.join(os.path.dirname(core.DB_PATH), "figcache")
    try: os.makedirs(d, exist_ok=True)
    except Exception: pass
    return d


def figure_for(nsn):
    """Best citing figure for an NSN: prefer a row that has a figure number; return doc/page/path."""
    if core is None:
        return {"found": False}
    nsn = (nsn or "").strip()
    if not nsn:
        return {"found": False}
    con = core.db()
    try:
        row = con.execute(
            "SELECT p.document_id AS doc_id, p.page AS page, p.fig_no AS fig_no, p.fig_title AS fig_title, "
            "d.path AS path, d.tm_number AS tm FROM parts p JOIN documents d ON d.id=p.document_id "
            "WHERE p.nsn=? ORDER BY (p.fig_no IS NULL), p.page LIMIT 1", (nsn,)).fetchone()
    except Exception:
        row = None
    finally:
        try: con.close()
        except Exception: pass
    if not row or not row["page"]:
        return {"found": False, "nsn": nsn}
    return {"found": True, "nsn": nsn, "doc_id": row["doc_id"], "page": row["page"],
            "fig_no": row["fig_no"], "fig_title": row["fig_title"], "path": row["path"], "tm": row["tm"]}


def _doc_path(doc_id):
    con = core.db()
    try:
        r = con.execute("SELECT path FROM documents WHERE id=?", (int(doc_id),)).fetchone()
        return r["path"] if r else None
    finally:
        try: con.close()
        except Exception: pass


def _ocr_caption_y(page, dpi=150):
    """SCANNED pages (no text layer): OCR the rendered page to find the FIGURE caption's top y (page coords),
    so we can crop the illustration above it. Uses pytesseract if present; returns None if unavailable.
    Gated by env VIEWER_FIGCROP_OCR (default on)."""
    if os.environ.get("VIEWER_FIGCROP_OCR", "1") == "0":
        return None
    try:
        import pytesseract
        from PIL import Image
        import io as _io
    except Exception:
        return None
    try:
        zoom = dpi / 72.0
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        img = Image.open(_io.BytesIO(pix.tobytes("png")))
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    except Exception:
        return None
    n = len(data.get("text", [])); ph = page.rect.height
    best = None
    for i in range(n):
        w = (data["text"][i] or "").strip()
        if not w:
            continue
        # caption token like "Figure" / "FIG" with a number nearby; only in the lower 85%
        if re.match(r"^FIG(?:URE)?\.?$", w, re.I):
            y_px = data["top"][i]; y_pg = y_px / zoom
            nxt = (data["text"][i + 1].strip() if i + 1 < n else "")
            if y_pg > ph * 0.15 and (re.match(r"\d", nxt) or True):
                best = min(best, y_pg) if best is not None else y_pg
    return best


def _density_table_top(page, dpi=60):
    """SCANNED pages: find where the dense parts-table band begins by row ink-density, so we crop the
    illustration above it. Uses numpy if present; returns a page-coords y or None."""
    try:
        import numpy as np
    except Exception:
        return None
    try:
        zoom = dpi / 72.0
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False, colorspace=fitz.csGRAY)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    except Exception:
        return None
    ph = page.rect.height
    dark = (arr < 140).mean(axis=1)              # fraction of dark pixels per row
    if dark.size < 10:
        return None
    # smooth
    k = max(3, pix.height // 60)
    kernel = np.ones(k) / k
    sm = np.convolve(dark, kernel, mode="same")
    thr = max(0.04, float(sm.mean()) * 1.6)
    lo = int(pix.height * 0.30)                   # tables sit in the lower portion
    run = 0; start = None
    for y in range(lo, pix.height):
        if sm[y] > thr:
            if start is None: start = y
            run += 1
            if run >= max(6, pix.height // 30):    # a sustained dense band = the table
                return (start / pix.height) * ph
        else:
            start = None; run = 0
    return None


def _figure_clip(page):
    """Return a fitz.Rect clip for the figure region on this page (heuristic)."""
    pr = page.rect
    # 1) caption-anchored from the PDF text layer (born-digital)
    try:
        blocks = page.get_text("blocks")
        raw = page.get_text("text") or ""
    except Exception:
        blocks = []; raw = ""
    cap_y = None
    for b in blocks:
        x0, y0, x1, y1 = b[:4]; txt = (b[4] or "") if len(b) > 4 else ""
        if _FIG_CAP.search(txt) and len(txt.strip()) < 80 and y0 > pr.height * 0.15:
            cap_y = min(cap_y, y1) if cap_y else y1
    if cap_y and cap_y < pr.height * 0.95:
        return fitz.Rect(pr.x0, pr.y0, pr.x1, min(pr.y1, cap_y + 4))
    # 1b) SCANNED page (little/no text layer): OCR caption -> else density table-top
    if len(raw.strip()) < 12:
        oy = _ocr_caption_y(page)
        if oy and oy < pr.height * 0.95:
            return fitz.Rect(pr.x0, pr.y0, pr.x1, min(pr.y1, oy + pr.height * 0.02))
        ty = _density_table_top(page)
        if ty and pr.height * 0.2 < ty < pr.height * 0.95:
            return fitz.Rect(pr.x0, pr.y0, pr.x1, ty)
    # 2) graphic-union
    rects = []
    try:
        for img in page.get_images(full=True):
            for rc in page.get_image_rects(img[0]):
                rects.append(fitz.Rect(rc))
    except Exception:
        pass
    try:
        for d in page.get_drawings():
            if d.get("rect"): rects.append(fitz.Rect(d["rect"]))
    except Exception:
        pass
    if rects:
        u = rects[0]
        for rc in rects[1:]:
            u = u | rc
        u = u & pr
        area = (u.width * u.height) / max(1.0, pr.width * pr.height)
        if 0.08 <= area <= 0.85:
            m = 6
            return fitz.Rect(max(pr.x0, u.x0 - m), max(pr.y0, u.y0 - m),
                             min(pr.x1, u.x1 + m), min(pr.y1, u.y1 + m))
    # 3) top portion fallback
    return fitz.Rect(pr.x0, pr.y0, pr.x1, pr.y0 + pr.height * 0.62)


def extract(pdf_path, page_number, dpi, out_path):
    """Render the figure region of (pdf_path, page_number) to out_path PNG. Returns (ok, detail)."""
    if fitz is None:
        return False, "PyMuPDF not available"
    if not pdf_path or not os.path.exists(pdf_path):
        return False, "pdf not found"
    try:
        doc = fitz.open(pdf_path)
        idx = int(page_number) - 1
        total = doc.page_count
        if idx < 0 or idx >= total:
            doc.close()
            return False, "page %s out of range (doc has %d pages)" % (page_number, total)
        page = doc[idx]
        clip = _figure_clip(page)
        mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
        pix.save(out_path)
        doc.close()
        return True, "ok %dx%d" % (pix.width, pix.height)
    except Exception as e:
        return False, "extract error: %s" % e


def get_crop(doc_id, page, dpi=150):
    """Path to the cached figure crop for (doc,page); extract+cache on first request. None if unavailable."""
    try:
        doc_id = int(doc_id); page = int(page); dpi = max(72, min(int(dpi), 300))
    except Exception:
        return None
    out = os.path.join(_figcache_dir(), "%d_%d_%d.png" % (doc_id, page, dpi))
    if os.path.exists(out) and os.path.getsize(out) > 0:
        return out
    path = _doc_path(doc_id)
    ok, _ = extract(path, page, dpi, out)
    return out if ok else None


def callout_crop(doc_id, page, item, dpi=150):
    """T3 (gated): crop tight around a figure's ITEM-number balloon. OCR the figure region for the digit(s)
    of `item`; if found in isolation, crop a box around it. Returns a cached path, or None (caller falls back
    to the whole-figure crop). Gated by VIEWER_FIGCROP_OCR; needs pytesseract."""
    if fitz is None or os.environ.get("VIEWER_FIGCROP_OCR", "1") == "0":
        return None
    try:
        import pytesseract
        from PIL import Image
        import io as _io
    except Exception:
        return None
    try:
        doc_id = int(doc_id); page = int(page); item = str(int(item)); dpi = max(72, min(int(dpi), 300))
    except Exception:
        return None
    out = os.path.join(_figcache_dir(), "callout_%d_%d_%s_%d.png" % (doc_id, page, item, dpi))
    if os.path.exists(out) and os.path.getsize(out) > 0:
        return out
    path = _doc_path(doc_id)
    if not path or not os.path.exists(path):
        return None
    try:
        doc = fitz.open(path)
        idx = page - 1
        if idx < 0 or idx >= doc.page_count:
            doc.close()
            return None
        pg = doc[idx]
        fig = _figure_clip(pg)                       # restrict the balloon search to the illustration
        zoom = dpi / 72.0
        pix = pg.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=fig, alpha=False)
        img = Image.open(_io.BytesIO(pix.tobytes("png")))
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        hits = []
        for i in range(len(data.get("text", []))):
            if (data["text"][i] or "").strip() == item:
                hits.append((data["left"][i], data["top"][i], data["width"][i], data["height"][i]))
        if len(hits) != 1:                           # gate: only when the number is found UNAMBIGUOUSLY
            doc.close(); return None
        lx, ty, ww, hh = hits[0]
        cx = lx + ww / 2.0; cy = ty + hh / 2.0
        # crop a box ~45% of the figure around the balloon, in figure-pixel space -> page coords
        bw = pix.width * 0.45; bh = pix.height * 0.45
        x0 = fig.x0 + max(0, cx - bw / 2) / zoom; y0 = fig.y0 + max(0, cy - bh / 2) / zoom
        x1 = fig.x0 + min(pix.width, cx + bw / 2) / zoom; y1 = fig.y0 + min(pix.height, cy + bh / 2) / zoom
        clip = fitz.Rect(x0, y0, x1, y1) & pg.rect
        cp = pg.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip, alpha=False)
        cp.save(out); doc.close()
        return out
    except Exception:
        return None


def part_image(nsn, dpi=150):
    """Resolve an NSN to its cited figure + a crop URL the UI can fetch."""
    info = figure_for(nsn)
    if not info.get("found"):
        return {"found": False, "nsn": (nsn or "").strip()}
    return {"found": True, "nsn": info["nsn"], "doc_id": info["doc_id"], "page": info["page"],
            "fig_no": info.get("fig_no"), "fig_title": info.get("fig_title"), "tm": info.get("tm"),
            "url": "/figcrop?doc=%d&page=%d&dpi=%d" % (info["doc_id"], info["page"], dpi)}
