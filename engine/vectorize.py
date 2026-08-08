#!/usr/bin/env python3
"""THE VIEWER -- offline LINE-ART VECTORIZATION (v0.99.4). Turns a raster TM figure / scanned schematic into a
crisp SVG (potrace-style: trace the ink regions' boundaries, fill with even-odd) so it stays razor-sharp at ANY
deep-zoom level, and can be recoloured / printed cleanly. Pure OpenCV + numpy + Pillow (no CDN, no external
binaries). Cached to a sidecar (index/veccache/); the index is never written (R1/R6).

  vectorize_image(pil_img) -> svg string | None
  vectorize_page(pdf_path, page, dpi) -> svg string | None
  ensure(cache_dir, doc_id, page, pdf_path, dpi) -> svg path | None
"""
import os

try:
    import numpy as _np
    import cv2 as _cv2
    from PIL import Image as _Image
    _OK = True
except Exception:
    _OK = False


def available():
    return _OK


def vectorize_image(pil_img, max_dim=1700, simplify=0.9, min_area=1.5, max_contours=60000, denoise=False):
    """Vectorize a PIL image of black-on-white line-art into an SVG string (or None if unavailable/empty)."""
    if not _OK or pil_img is None:
        return None
    g = _np.asarray(pil_img.convert("L"))
    H, W = g.shape[:2]
    scale = 1.0
    if max(H, W) > max_dim:
        scale = max_dim / float(max(H, W))
        # guard: a very thin image can round a dimension to 0, which crashes cv2.resize (inv_scale_x > 0)
        g = _cv2.resize(g, (max(1, int(W * scale)), max(1, int(H * scale))), interpolation=_cv2.INTER_AREA)
        H, W = g.shape[:2]
    # ink -> 255 (foreground) via Otsu; light denoise so speckle doesn't explode the path count
    _thr, bw = _cv2.threshold(g, 0, 255, _cv2.THRESH_BINARY_INV | _cv2.THRESH_OTSU)
    if denoise:
        bw = _cv2.medianBlur(bw, 3)      # optional: only when the scan is speckly (thin detail is lost)
    cnts, hier = _cv2.findContours(bw, _cv2.RETR_CCOMP, _cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    # keep the biggest first, drop speckle, cap count
    idx = sorted(range(len(cnts)), key=lambda i: _cv2.contourArea(cnts[i]), reverse=True)
    d = []; kept = 0
    for i in idx:
        c = cnts[i]
        if _cv2.contourArea(c) < min_area:
            continue
        ap = _cv2.approxPolyDP(c, simplify, True)
        if len(ap) < 3:
            continue
        pts = ap.reshape(-1, 2)
        seg = "M" + " L".join("%d,%d" % (int(p[0]), int(p[1])) for p in pts) + "Z"
        d.append(seg); kept += 1
        if kept >= max_contours:
            break
    if not d:
        return None
    ink = "".join(d)
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">'
           '<rect x="0" y="0" width="%d" height="%d" fill="#ffffff"/>'
           '<path d="%s" fill="#14181d" fill-rule="evenodd" stroke="none"/></svg>'
           % (W, H, W, H, W, H, ink))
    return svg


def vectorize_page(pdf_path, page, dpi=200, **kw):
    if not _OK or not pdf_path or not str(pdf_path).lower().endswith(".pdf") or not os.path.exists(pdf_path):
        return None
    try:
        import fitz
        doc = fitz.open(pdf_path)
        pg = doc[int(page) - 1]
        pix = pg.get_pixmap(dpi=int(dpi))
        img = _Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()
    except Exception:
        return None
    return vectorize_image(img, **kw)


def cache_path(cache_dir, doc_id, page, dpi):
    safe = "".join(ch for ch in str(doc_id) if ch.isalnum() or ch in "-_")
    return os.path.join(cache_dir, "%s_%s_%s.svg" % (safe or "doc", int(page), int(dpi)))


def ensure(cache_dir, doc_id, page, pdf_path, dpi=200):
    if not _OK:
        return None
    try:
        os.makedirs(cache_dir, exist_ok=True)
    except Exception:
        pass
    out = cache_path(cache_dir, doc_id, page, dpi)
    if os.path.exists(out) and os.path.getsize(out) > 0:
        return out
    svg = vectorize_page(pdf_path, page, dpi)
    if not svg:
        return None
    try:
        open(out, "w", encoding="utf-8").write(svg)
        return out
    except Exception:
        return None


if __name__ == "__main__":
    # self-test on a synthetic line drawing
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (400, 300), "white"); dr = ImageDraw.Draw(im)
    dr.rectangle([60, 60, 200, 180], outline="black", width=3)
    dr.ellipse([220, 90, 340, 210], outline="black", width=3)
    dr.line([60, 240, 340, 240], fill="black", width=3)
    dr.text((70, 200), "R12", fill="black")
    svg = vectorize_image(im)
    print("available:", available())
    print("svg len:", len(svg) if svg else 0, "| has path:", ("<path" in (svg or "")))
