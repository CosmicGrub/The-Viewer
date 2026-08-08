"""qrgen.py -- offline QR codes for parts / NSNs (bay-floor UX, v1.4.0).

WHY: a printed job packet or a part page can carry a QR so a mechanic scans it
from a phone or a second bay-floor tablet and jumps straight back to the same
part's dossier -- no retyping an NSN. Everything stays offline: the QR encodes a
deep-link URL on THIS server (the Host the request came in on), so a device on
the same bench LAN resolves it directly.

DEPENDENCY POSTURE (matches the rest of the program -- graceful degrade, never a
hard crash if an optional package is missing):
  * primary  : segno       -- pure-python, zero further deps, emits SVG (scales
                             cleanly for print, needs no Pillow).
  * fallback : qrcode+PIL   -- if segno is absent but Pillow (a core dep) and
                             qrcode are present, emit a PNG instead.
  * absent   : available()==False and build() returns (None, reason); callers
                             surface a friendly "QR support not installed" note
                             and the app keeps working. Install with:
                                 pip install segno
                             (segno is listed in requirements.txt, optional tier.)

This module has NO effect on the corpus or the index -- it only renders bytes on
demand. R1 (backwards-compatible / rollbackable): deleting this file and its two
routes removes the feature with zero impact on anything else.
"""

from __future__ import annotations

# ---- optional backends, probed once at import (cheap) -----------------------
_SEGNO = None
_QRCODE = None
try:                                # primary: pure-python, no Pillow needed
    import segno as _SEGNO          # type: ignore
except Exception:                   # pragma: no cover - environment dependent
    _SEGNO = None
if _SEGNO is None:
    try:                            # fallback: needs Pillow (a core dependency)
        import qrcode as _QRCODE    # type: ignore
    except Exception:               # pragma: no cover
        _QRCODE = None


def available() -> bool:
    """True when *some* QR backend can render. Callers gate the UI on this."""
    return _SEGNO is not None or _QRCODE is not None


def backend() -> str:
    if _SEGNO is not None:
        return "segno"
    if _QRCODE is not None:
        return "qrcode"
    return "none"


def _clean(data: str) -> str:
    data = ("" if data is None else str(data)).strip()
    if not data:
        raise ValueError("qrgen: nothing to encode")
    # QR byte mode is fine with URLs; guard only against absurd lengths.
    if len(data) > 900:
        data = data[:900]
    return data


def build(data: str, scale: int = 6, border: int = 3):
    """Render ``data`` as a QR. Returns ``(mime, payload_bytes)`` on success, or
    ``(None, reason)`` when no backend is installed. Never raises for the
    missing-backend case -- only for genuinely bad input (empty string).

    * segno  -> ("image/svg+xml", <svg bytes>)   -- preferred, print-crisp.
    * qrcode -> ("image/png",     <png bytes>)    -- fallback.
    """
    data = _clean(data)
    scale = max(2, min(int(scale or 6), 20))
    border = max(0, min(int(border or 3), 8))

    if _SEGNO is not None:
        import io
        q = _SEGNO.make(data, error="m")      # ECC level M ~15% recovery
        buf = io.BytesIO()
        # dark/light tuned for the app's dark UI printouts stay black-on-white
        q.save(buf, kind="svg", scale=scale, border=border,
               dark="#0b0f14", light="#ffffff")
        return ("image/svg+xml", buf.getvalue())

    if _QRCODE is not None:
        import io
        qr = _QRCODE.QRCode(error_correction=getattr(_QRCODE, "constants", None)
                            and _QRCODE.constants.ERROR_CORRECT_M or 0,
                            box_size=scale, border=border)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0b0f14", back_color="#ffffff")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return ("image/png", buf.getvalue())

    return (None, "QR support is not installed. Run: pip install segno")


def deep_link(base_url: str, q: str, page: str = "/dossier") -> str:
    """Build the URL a scan should open: the part's dossier on THIS server.
    ``base_url`` is e.g. 'http://127.0.0.1:8765' (from the request Host header);
    ``q`` is the NSN / part name. Kept tiny and dependency-free so the route can
    call it directly."""
    from urllib.parse import quote
    base = (base_url or "").rstrip("/")
    page = page if page.startswith("/") else ("/" + page)
    return base + page + "?q=" + quote(str(q or "").strip())


def for_part(base_url: str, q: str, page: str = "/dossier", scale: int = 6):
    """Convenience: encode the dossier deep-link for a part/NSN in one call."""
    return build(deep_link(base_url, q, page), scale=scale)


# --------------------------------------------------------------------------- #
# self-test: `python qrgen.py`  (used by VERIFY-099.bat)                       #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import sys

    # deep_link is pure-python and always testable, backend or not.
    link = deep_link("http://127.0.0.1:8765/", "2530-01-234-5678")
    assert link == "http://127.0.0.1:8765/dossier?q=2530-01-234-5678", link
    print("qrgen deep_link OK -> " + link)

    if not available():
        print("qrgen self-test SKIPPED (no QR backend installed; "
              "feature degrades gracefully). backend=" + backend())
        sys.exit(0)

    mime, payload = build("http://127.0.0.1:8765/dossier?q=alternator")
    assert mime in ("image/svg+xml", "image/png"), mime
    assert payload and len(payload) > 80, "QR payload too small"
    if mime == "image/svg+xml":
        head = payload[:400].decode("utf-8", "replace").lower()
        assert "<svg" in head, "not an SVG"
    else:
        assert payload[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    m2, p2 = for_part("http://127.0.0.1:8765", "5305-00-123-4567")
    assert m2 == mime and p2, "for_part failed"
    print("qrgen self-test PASS (backend=" + backend()
          + ", " + mime + ", " + str(len(payload)) + " bytes)")

# END OF FILE
