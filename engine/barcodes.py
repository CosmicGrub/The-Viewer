#!/usr/bin/env python3
"""THE VIEWER -- BARCODE / QR / DATA-MATRIX DETECTOR (v1.2.0, catalog §4.9). Some TMs print NSNs, part numbers, and
serials as 1-D barcodes or QR/Data-Matrix on the page. This reads them off a rendered page image. Backends, best first:
pyzbar (1-D + QR + Data-Matrix) if installed, else OpenCV QRCodeDetector (QR only, always available). Degrades to [] if
neither can read anything. Read-only; feeds the parts index / Masterfile with machine-read identifiers (higher trust
than OCR). Pure detection -- pass it a PIL image or a numpy array."""
import re

try:
    import pyzbar.pyzbar as _pyzbar
    _HAVE_ZBAR = True
except Exception:
    _pyzbar = None; _HAVE_ZBAR = False

try:
    import cv2
    import numpy as _np
    _HAVE_CV = True
except Exception:
    cv2 = None; _np = None; _HAVE_CV = False

_NSN = re.compile(r"\b\d{4}-?\d{2}-?\d{3}-?\d{4}\b")


def available():
    return _HAVE_ZBAR or _HAVE_CV


def backend():
    return "pyzbar" if _HAVE_ZBAR else ("opencv-qr" if _HAVE_CV else "none")


def _to_cv(image):
    if _np is None:
        return None
    try:
        arr = image if hasattr(image, "shape") else _np.array(image.convert("RGB"))
        if arr.ndim == 3:
            arr = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        return arr
    except Exception:
        return None


def detect(image):
    """Return [{type, data, nsn?}] for every barcode/QR found in `image` (PIL image or numpy array). Fail-soft -> []."""
    out = []
    # 1) pyzbar handles 1-D + QR + Data-Matrix
    if _HAVE_ZBAR:
        try:
            for s in _pyzbar.decode(image):
                data = s.data.decode("utf-8", "replace") if isinstance(s.data, bytes) else str(s.data)
                rec = {"type": str(getattr(s, "type", "barcode")), "data": data}
                m = _NSN.search(data)
                if m:
                    rec["nsn"] = m.group(0)
                out.append(rec)
            if out:
                return out
        except Exception:
            pass
    # 2) OpenCV QR fallback (QR only)
    if _HAVE_CV:
        arr = _to_cv(image)
        if arr is not None:
            try:
                det = cv2.QRCodeDetector()
                ok, infos, pts, _ = det.detectAndDecodeMulti(arr)
                if ok and infos:
                    for data in infos:
                        if not data:
                            continue
                        rec = {"type": "QRCODE", "data": data}
                        m = _NSN.search(data)
                        if m:
                            rec["nsn"] = m.group(0)
                        out.append(rec)
            except Exception:
                pass
    return out


if __name__ == "__main__":
    # plumbing self-test: backends resolve, empty/garbage input never raises
    print("backend:", backend())
    assert detect(None) == [], "None input must return []"
    if _HAVE_CV:
        import numpy as np
        blank = np.zeros((80, 80), dtype="uint8") + 255
        assert detect(blank) == [], "blank image must return []"
    # NSN scrape from decoded payload works
    rec = {"data": "NSN 2920-01-371-9577 ALTERNATOR"}
    assert _NSN.search(rec["data"]).group(0) == "2920-01-371-9577"
    print("barcodes self-test OK  (backend=%s; graceful degrade + NSN scrape verified)" % backend())
# END OF FILE
