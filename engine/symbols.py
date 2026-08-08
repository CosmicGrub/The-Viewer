#!/usr/bin/env python3
"""THE VIEWER -- SYMBOL DETECTION (v1.3.3, catalog §4.8 + §4.11). Finds repeated graphical symbols on a page image by
template matching: schematic components (resistor, relay, connector, ground) and safety symbols (the warning triangle,
electrical-hazard, radiation marks). Given a small template image per symbol, it locates every occurrence with a score,
so schematics can be inventoried and safety marks surfaced. Pure OpenCV (no GPU, no training); the templates are just
cropped example images the user supplies (index/symbols/<name>.png). Read-only; degrades to [] without OpenCV."""
try:
    import cv2
    import numpy as np
    _OK = True
except Exception:
    cv2 = None; np = None; _OK = False

import os


def available():
    return _OK


def _gray(image):
    arr = image if hasattr(image, "shape") else np.array(image.convert("L"))
    if arr.ndim == 3:
        arr = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    return arr


def _nms(points, min_dist=12):
    """Greedy suppression of matches closer than min_dist (keep highest score first)."""
    kept = []
    for p in sorted(points, key=lambda z: -z[2]):
        if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 >= min_dist ** 2 for q in kept):
            kept.append(p)
    return kept


def detect(image, templates, threshold=0.72):
    """`templates` = {name: template_image}. Returns [{name, x, y, w, h, score}] for every match >= threshold."""
    if not _OK or not templates:
        return []
    g = _gray(image); out = []
    for name, tmpl in templates.items():
        t = _gray(tmpl)
        th, tw = t.shape[:2]
        if th >= g.shape[0] or tw >= g.shape[1]:
            continue
        res = cv2.matchTemplate(g, t, cv2.TM_CCOEFF_NORMED)
        ys, xs = np.where(res >= threshold)
        pts = [(int(x), int(y), float(res[y, x])) for x, y in zip(xs, ys)]
        for x, y, sc in _nms(pts, min_dist=max(tw, th) // 2 or 8):
            out.append({"name": name, "x": x, "y": y, "w": tw, "h": th, "score": round(sc, 3)})
    out.sort(key=lambda r: -r["score"])
    return out


def load_templates(folder):
    """Load index/symbols/*.png as {basename: image}. Returns {} if folder/opencv missing."""
    if not _OK or not folder or not os.path.isdir(folder):
        return {}
    tt = {}
    for fn in os.listdir(folder):
        if fn.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
            img = cv2.imread(os.path.join(folder, fn), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                tt[os.path.splitext(fn)[0]] = img
    return tt


if __name__ == "__main__":
    if not _OK:
        print("OpenCV unavailable; skipping"); raise SystemExit(0)
    # page with two identical warning triangles at known spots
    img = np.full((240, 320), 255, dtype="uint8")
    def triangle(cx, cy):
        pts = np.array([[cx, cy - 14], [cx - 14, cy + 12], [cx + 14, cy + 12]], np.int32)
        cv2.fillPoly(img, [pts], 0)
    triangle(60, 60); triangle(240, 170)
    template = img[44:76, 44:76].copy()          # crop around the first triangle
    hits = detect(img, {"warning": template}, threshold=0.7)
    assert len(hits) >= 2, ("expected 2 warning symbols", len(hits), hits[:3])
    xs = sorted(h["x"] for h in hits[:2])
    assert xs[0] < 80 and xs[1] > 200, ("locations wrong", xs)
    assert all(h["name"] == "warning" for h in hits), hits
    print("symbols self-test OK  (%d 'warning' symbols located by template match)" % len(hits))
# END OF FILE
