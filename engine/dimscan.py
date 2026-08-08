#!/usr/bin/env python3
"""THE VIEWER -- DIMENSION-LINE / GD&T SCANNER (v1.3.1, catalog §4.6). The marquee 'spatial data' capability: on an
engineering drawing the dimensions live on leader/extension lines (often ROTATED or vertical), which plain text OCR
reads out of order or misses. This detects the dimension-line geometry on a rendered page image (long straight segments
at any angle, via OpenCV Hough) so the number sitting on each line can then be OCR'd IN CONTEXT and tied to the feature
it measures. Geometry detection is done here (cv2, no GPU); the per-line number OCR is the host-side step (needs the OCR
engine). Read-only; degrades to [] without OpenCV. Corpus authoritative."""
import math

try:
    import cv2
    import numpy as np
    _OK = True
except Exception:
    cv2 = None; np = None; _OK = False


def available():
    return _OK


def _angle(x1, y1, x2, y2):
    a = math.degrees(math.atan2(y2 - y1, x2 - x1))
    if a < 0:
        a += 180.0
    return round(a, 1)


def detect_dimension_lines(image, min_len=40, max_lines=400):
    """Detect candidate dimension/leader lines in `image` (PIL image or numpy array). Returns
    [{x1,y1,x2,y2,length,angle,orient}] where orient in {horizontal,vertical,diagonal}. Angle is 0..180 so rotated
    dimensions are caught. Fail-soft -> []."""
    if not _OK or image is None:
        return []
    try:
        arr = image if hasattr(image, "shape") else np.array(image.convert("L"))
        if arr.ndim == 3:
            arr = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(arr, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, math.pi / 180, threshold=50,
                                minLineLength=min_len, maxLineGap=6)
        out = []
        if lines is None:
            return out
        for ln in lines[:max_lines]:
            x1, y1, x2, y2 = (int(v) for v in ln[0])
            length = round(math.hypot(x2 - x1, y2 - y1), 1)
            if length < min_len:
                continue
            ang = _angle(x1, y1, x2, y2)
            orient = "horizontal" if (ang < 15 or ang > 165) else ("vertical" if 75 < ang < 105 else "diagonal")
            out.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2, "length": length, "angle": ang, "orient": orient})
        # longest first (dimension lines tend to be the long clean strokes)
        out.sort(key=lambda r: -r["length"])
        return out
    except Exception:
        return []


def summarize(lines):
    """Roll up detected lines by orientation -> {n, horizontal, vertical, diagonal, has_rotated}."""
    o = {"horizontal": 0, "vertical": 0, "diagonal": 0}
    for l in lines:
        o[l["orient"]] = o.get(l["orient"], 0) + 1
    return {"n": len(lines), **o, "has_rotated": o["diagonal"] > 0}


if __name__ == "__main__":
    if not _OK:
        print("OpenCV unavailable; skipping"); raise SystemExit(0)
    img = np.full((240, 240), 255, dtype="uint8")
    cv2.line(img, (20, 40), (200, 40), 0, 2)          # horizontal dimension line
    cv2.line(img, (30, 60), (30, 210), 0, 2)          # vertical dimension line
    cv2.line(img, (40, 200), (200, 60), 0, 2)         # ~45deg rotated dimension line
    lines = detect_dimension_lines(img, min_len=60)
    s = summarize(lines)
    assert s["n"] >= 3, ("expected >=3 lines", s, len(lines))
    assert s["horizontal"] >= 1 and s["vertical"] >= 1, s
    assert s["has_rotated"], ("rotated dimension line not detected", s)
    # angles present should include ~0/180 (horiz), ~90 (vert), ~45/135 (diag)
    angs = [l["angle"] for l in lines]
    assert any(a < 15 or a > 165 for a in angs) and any(75 < a < 105 for a in angs), angs
    print("dimscan self-test OK  (%d lines; H=%d V=%d D=%d, rotated detected)"
          % (s["n"], s["horizontal"], s["vertical"], s["diagonal"]))
# END OF FILE
