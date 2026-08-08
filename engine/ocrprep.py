#!/usr/bin/env python3
"""THE VIEWER -- OCR PRE-PROCESSING (v1.3.2, catalog §1.3 + §1.8). Old TM scans are skewed, speckled, and sometimes
rotated 90/180 deg -- all of which wreck OCR accuracy and therefore every downstream extractor. This cleans a page
image BEFORE OCR: estimate + correct skew, denoise, binarize (Otsu), and detect page orientation. Pure OpenCV/numpy (no
GPU); orientation uses pytesseract OSD when the tesseract binary is present, else a safe no-op. Read-only helper used by
the host OCR pass; the running app never needs it. Degrades to identity if OpenCV is absent."""
import math

try:
    import cv2
    import numpy as np
    _OK = True
except Exception:
    cv2 = None; np = None; _OK = False


def available():
    return _OK


def _gray(image):
    arr = image if hasattr(image, "shape") else np.array(image.convert("L"))
    if arr.ndim == 3:
        arr = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    return arr


def skew_angle(image):
    """Estimate the page skew in degrees (positive = counter-clockwise). 0 if it can't be measured."""
    if not _OK:
        return 0.0
    g = _gray(image)
    thr = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thr > 0))
    if len(coords) < 20:
        return 0.0
    angle = cv2.minAreaRect(coords.astype(np.float32))[-1]
    # OpenCV returns angle in (-90, 0]; normalise to a small correction around 0
    if angle < -45:
        angle = 90 + angle
    return round(float(-angle), 2)


def deskew(image):
    """Return the image rotated to remove its skew (and the angle applied). Small-angle only (|a|<=20)."""
    if not _OK:
        return image, 0.0
    g = _gray(image)
    a = skew_angle(g)
    if abs(a) < 0.3 or abs(a) > 20:
        return g, 0.0
    h, w = g.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), a, 1.0)
    rot = cv2.warpAffine(g, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rot, a


def binarize(image):
    """Otsu binarisation -> clean black-on-white for OCR."""
    if not _OK:
        return image
    g = _gray(image)
    return cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]


def denoise(image):
    """Light speckle removal that preserves thin strokes."""
    if not _OK:
        return image
    g = _gray(image)
    return cv2.medianBlur(g, 3)


def detect_orientation(image):
    """Page rotation in {0,90,180,270} via pytesseract OSD if available, else 0 (no-op)."""
    try:
        import pytesseract, re
        osd = pytesseract.image_to_osd(image)
        m = re.search(r"Rotate:\s*(\d+)", osd)
        return int(m.group(1)) % 360 if m else 0
    except Exception:
        return 0


def preprocess(image):
    """Full clean pipeline for OCR: deskew -> denoise -> binarize. Returns (image, {skew, applied})."""
    if not _OK:
        return image, {"skew": 0.0, "applied": []}
    applied = []
    img, a = deskew(image)
    if a:
        applied.append("deskew")
    img = denoise(img); applied.append("denoise")
    img = binarize(img); applied.append("binarize")
    return img, {"skew": a, "applied": applied}


if __name__ == "__main__":
    if not _OK:
        print("OpenCV unavailable; skipping"); raise SystemExit(0)
    # build a clean page with horizontal text bars, then rotate it by a known angle and check deskew recovers it
    base = np.full((300, 400), 255, dtype="uint8")
    for y in range(60, 260, 30):
        cv2.rectangle(base, (60, y), (340, y + 10), 0, -1)
    ang = 8.0
    m = cv2.getRotationMatrix2D((200, 150), ang, 1.0)
    skewed = cv2.warpAffine(base, m, (400, 300), borderValue=255)

    det = skew_angle(skewed)
    assert abs(abs(det) - ang) < 3.5, ("skew estimate off", det)          # detected within a few degrees
    fixed, applied_a = deskew(skewed)
    assert abs(skew_angle(fixed)) < abs(det), ("deskew did not reduce skew", det, skew_angle(fixed))
    b = binarize(skewed)
    assert set(np.unique(b)).issubset({0, 255}), "binarize not black/white"
    out, meta = preprocess(skewed)
    assert "binarize" in meta["applied"] and "denoise" in meta["applied"]
    assert detect_orientation(base) in (0, 90, 180, 270)
    print("ocrprep self-test OK  (skew detected %.1f deg, corrected; binarize+denoise+orientation pipeline)" % det)
# END OF FILE
