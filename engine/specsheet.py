#!/usr/bin/env python3
"""THE VIEWER -- PER-VEHICLE SPEC-SHEET PDF (v1.4.0). One printable page of a subject's consolidated 'leading
particulars' straight from the Masterfile: every dimension with its value, dual unit, source (authoritative vs external),
and a wide-variance flag. A bay-ready summary a mechanic can print and tape to the bench. No external links (R11) --
authoritative values come from the manuals, external ones are labelled. reportlab; read-only. Fed by masterfile.for_subject."""
import io
import time

# colours (match the dark job-card / figuresheet palette but print on white here for legibility)
_INK = (0.10, 0.12, 0.16); _SUB = (0.42, 0.47, 0.53); _ACC = (0.12, 0.35, 0.62)
_GRN = (0.11, 0.45, 0.28); _AMB = (0.66, 0.50, 0.16); _LINE = (0.80, 0.83, 0.87)


def available():
    try:
        import reportlab  # noqa: F401
        return True
    except Exception:
        return False


def build(subject_label, filtered_rows):
    """Return PDF bytes for a one-page spec sheet. `filtered_rows` = the masterfile for_subject filtered list
    (each: type, unit, value, low, high, n, authoritative, note, and optional alt/system/spread)."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas as rlc
    buf = io.BytesIO(); c = rlc.Canvas(buf, pagesize=letter); W, H = letter

    c.setFillColorRGB(*_INK); c.setFont("Helvetica-Bold", 22)
    c.drawString(48, H - 64, "Spec Sheet")
    c.setFillColorRGB(*_ACC); c.setFont("Helvetica-Bold", 15)
    c.drawString(48, H - 88, (subject_label or "").strip()[:70])
    c.setFillColorRGB(*_SUB); c.setFont("Helvetica", 9)
    c.drawString(48, H - 104, "Consolidated leading particulars from THE VIEWER Masterfile  -  %s" % time.strftime("%Y-%m-%d"))
    c.setStrokeColorRGB(*_LINE); c.setLineWidth(1); c.line(48, H - 112, W - 48, H - 112)

    # column header
    y = H - 136
    c.setFillColorRGB(*_SUB); c.setFont("Helvetica-Bold", 8.5)
    c.drawString(48, y, "DIMENSION"); c.drawString(210, y, "VALUE"); c.drawString(340, y, "ALT")
    c.drawString(430, y, "SOURCE"); c.drawString(520, y, "N")
    y -= 6; c.line(48, y, W - 48, y); y -= 16

    rows = sorted(filtered_rows or [], key=lambda r: (0 if r.get("authoritative") else 1, r.get("type", "")))
    for r in rows[:44]:
        if y < 90:
            c.setFillColorRGB(*_SUB); c.setFont("Helvetica-Oblique", 8)
            c.drawString(48, y, "more dimensions in the Masterfile (/master)"); break
        span = ""
        if r.get("low") and r.get("high") and r.get("low") != r.get("high"):
            span = "  (%s-%s)" % (r["low"], r["high"])
        auth = bool(r.get("authoritative"))
        c.setFillColorRGB(*_INK); c.setFont("Helvetica-Bold", 9.5)
        c.drawString(48, y, str(r.get("type", ""))[:22])
        c.setFillColorRGB(*(_GRN if auth else _AMB)); c.setFont("Helvetica-Bold", 9.5)
        c.drawString(210, y, ("%s %s%s" % (r.get("value", ""), r.get("unit", ""), span))[:22])
        c.setFillColorRGB(*_SUB); c.setFont("Helvetica", 8.5)
        c.drawString(340, y, str(r.get("alt", "") or "")[:16])
        c.setFillColorRGB(*(_GRN if auth else _AMB)); c.setFont("Helvetica", 8)
        c.drawString(430, y, "manual" if auth else "ext - unconfirmed")
        c.setFillColorRGB(*_SUB); c.setFont("Helvetica", 8.5)
        c.drawString(522, y, str(r.get("n", "")))
        if r.get("spread") == "wide":
            c.setFillColorRGB(*_AMB); c.setFont("Helvetica-Bold", 7.5)
            c.drawString(548, y, "!")
        y -= 15

    c.setFillColorRGB(*_SUB); c.setFont("Helvetica", 8)
    c.drawString(48, 60, "Authoritative values are from the manuals; 'ext' values are external references (unconfirmed) that only")
    c.drawString(48, 49, "fill dimension types the manuals omit. '!' = sources disagree widely -- confirm on the cited page before use.")
    c.showPage(); c.save()
    return buf.getvalue()


def for_subject(master_db, subject):
    """Convenience: read the Masterfile for `subject` and render the sheet. Returns PDF bytes or None."""
    try:
        import masterfile
        res = masterfile.for_subject(master_db, subject)
        rows = res.get("filtered") or []
        if not rows:
            return None
        label = (rows[0].get("subject_label") or subject) if rows else subject
        return build(label, rows)
    except Exception:
        return None


if __name__ == "__main__":
    if not available():
        print("reportlab unavailable; skipping"); raise SystemExit(0)
    sample = [
        {"type": "length", "unit": "in", "value": "180", "low": "180", "high": "180", "n": 3,
         "authoritative": 1, "alt": "4572 mm", "spread": ""},
        {"type": "weight", "unit": "lb", "value": "7700", "low": "7700", "high": "9100", "n": 5,
         "authoritative": 1, "alt": "3492.66 kg", "spread": "wide"},
        {"type": "capacity", "unit": "gal", "value": "25", "low": "25", "high": "25", "n": 1,
         "authoritative": 0, "alt": "94.64 L", "spread": ""},
    ]
    pdf = build("HMMWV M998", sample)
    assert pdf[:5] == b"%PDF-", "not a PDF"
    assert len(pdf) > 800, ("PDF too small", len(pdf))
    print("specsheet self-test OK  (valid %d-byte PDF, %d dimensions, wide-variance + ext labelled)" % (len(pdf), len(sample)))
# END OF FILE
