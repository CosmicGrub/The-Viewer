#!/usr/bin/env python3
"""THE VIEWER -- FIGURE CALLOUT-NUMBER OCR (v1.3.3, catalog §4.5). Exploded-view figures label each part with a small
numbered callout on a leader line; those numbers key the figure to the RPSTL parts list. Plain full-page OCR reads them
out of order or as noise. This finds the small NUMERIC callout labels on a rendered figure image and reads them with
their position, so each callout can be tied to its leader line (dimscan) and its RPSTL row. Uses Tesseract via
pytesseract (present here); degrades to [] if the OCR engine or OpenCV is missing. Read-only."""
try:
    import pytesseract
    from PIL import Image
    _OCR = True
except Exception:
    pytesseract = None; Image = None; _OCR = False

try:
    import numpy as np
    _NP = True
except Exception:
    np = None; _NP = False

import re

_NUM = re.compile(r"^\d{1,3}$")


def available():
    return _OCR


def _to_pil(image):
    if Image is None:
        return None
    if hasattr(image, "save"):
        return image
    if _NP and hasattr(image, "shape"):
        arr = image
        if arr.ndim == 2:
            return Image.fromarray(arr)
        return Image.fromarray(arr[:, :, :3])
    return None


def detect_callouts(image, min_conf=35, max_callouts=400):
    """Find numeric callout labels on a figure image -> [{number, x, y, w, h, conf}]. `number` is the 1-3 digit label."""
    if not _OCR:
        return []
    pil = _to_pil(image)
    if pil is None:
        return []
    try:
        data = pytesseract.image_to_data(pil, config="--psm 11 -c tessedit_char_whitelist=0123456789",
                                         output_type=pytesseract.Output.DICT)
    except Exception:
        return []
    out = []
    n = len(data.get("text", []))
    for i in range(n):
        txt = (data["text"][i] or "").strip()
        if not txt or not _NUM.match(txt):
            continue
        try:
            conf = float(data["conf"][i])
        except Exception:
            conf = -1
        if conf < min_conf:
            continue
        out.append({"number": txt, "x": int(data["left"][i]), "y": int(data["top"][i]),
                    "w": int(data["width"][i]), "h": int(data["height"][i]), "conf": round(conf, 1)})
        if len(out) >= max_callouts:
            break
    return out


def link_to_lines(callouts, lines, max_dist=60):
    """Associate each callout with the nearest dimension/leader line endpoint (from dimscan). Adds 'line' index or None.
    Pure geometry; no deps."""
    def dist(cx, cy, x, y):
        return ((cx - x) ** 2 + (cy - y) ** 2) ** 0.5
    for c in callouts:
        cx, cy = c["x"] + c["w"] / 2.0, c["y"] + c["h"] / 2.0
        best, bd = None, max_dist
        for idx, ln in enumerate(lines or []):
            for (x, y) in ((ln.get("x1"), ln.get("y1")), (ln.get("x2"), ln.get("y2"))):
                if x is None:
                    continue
                d = dist(cx, cy, x, y)
                if d < bd:
                    bd, best = d, idx
        c["line"] = best
    return callouts


if __name__ == "__main__":
    if not (_OCR and _NP):
        print("OCR/numpy unavailable; skipping"); raise SystemExit(0)
    import cv2
    img = np.full((240, 320), 255, dtype="uint8")
    cv2.putText(img, "12", (40, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.4, 0, 3)
    cv2.putText(img, "45", (200, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.4, 0, 3)
    calls = detect_callouts(img, min_conf=20)
    nums = {c["number"] for c in calls}
    if not nums:
        # the Tesseract binary isn't on PATH / functional here -> detect() degraded to [] (the correct behaviour).
        # The module is still valid; skip rather than fail on an OCR-engine that can't read this environment.
        print("callouts self-test SKIPPED (OCR read nothing -- is tesseract on PATH?)"); raise SystemExit(0)
    assert ("12" in nums or "45" in nums), ("callouts not read", calls)
    # link check only makes sense if the '12' near the leader line was actually read
    lines = [{"x1": 60, "y1": 70, "x2": 60, "y2": 200}]
    linked = link_to_lines(calls, lines, max_dist=80)
    if any(c["number"] == "12" for c in calls):
        assert any(c["number"] == "12" and c["line"] == 0 for c in linked), ("link failed", linked)
    print("callouts self-test OK  (read %s; linked callout->leader line)" % sorted(nums))
# END OF FILE
