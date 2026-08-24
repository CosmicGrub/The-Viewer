#!/usr/bin/env python3
"""THE VIEWER -- PARTS-REQUEST PDF + NSN BARCODES (v0.99.26). Turn a list of requested parts into a clean printable
parts-request sheet with a scannable Code128 barcode of each NSN (so supply can scan, not retype). Pure reportlab,
offline. Read-only; items are passed in (gathered by the route from the request session or a query)."""
import io, re, time


def _digits(nsn):
    return re.sub(r"\D", "", nsn or "")


def build_pdf(items, meta=None):
    """items = [{nsn, name, part_number, cagec, qty, uoc}]; meta = {title, mechanic, bumper, tm, unit}. -> PDF bytes."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas as rlc
    from reportlab.graphics.barcode import code128
    meta = meta or {}
    buf = io.BytesIO(); c = rlc.Canvas(buf, pagesize=letter); W, H = letter
    def header(page):
        c.setFillColorRGB(0.07, 0.09, 0.12); c.rect(0, H - 96, W, 96, fill=1, stroke=0)
        c.setFillColorRGB(0.90, 0.93, 0.96); c.setFont("Helvetica-Bold", 18); c.drawString(42, H - 46, "Parts Request")
        c.setFillColorRGB(0.55, 0.60, 0.68); c.setFont("Helvetica", 9)
        sub = "  ·  ".join([x for x in [meta.get("unit"), ("Mechanic: " + meta["mechanic"]) if meta.get("mechanic") else "",
                     ("Bumper: " + meta["bumper"]) if meta.get("bumper") else "", ("TM: " + meta["tm"]) if meta.get("tm") else "",
                     time.strftime("%Y-%m-%d")] if x])
        c.drawString(42, H - 64, sub[:150])
        c.setFillColorRGB(0.50, 0.66, 0.90); c.setFont("Helvetica-Bold", 8)
        c.drawString(42, H - 82, "%-24s %-30s %-8s %-6s  BARCODE (NSN, Code128)" % ("NSN", "NOMENCLATURE", "P/N", "QTY"))
        c.setFillColorRGB(0.40, 0.44, 0.50); c.setFont("Helvetica-Oblique", 7)
        c.drawString(42, 30, "Scan the NSN barcode at supply. Verify NSN/qty against the TM before ordering. THE VIEWER · page %d" % page)
    header(1); y = H - 116; page = 1
    for it in items:
        if y < 90:
            c.showPage(); page += 1; header(page); y = H - 116
        nsn = (it.get("nsn") or "").strip(); dig = _digits(nsn)
        c.setFillColorRGB(0.90, 0.93, 0.96); c.setFont("Helvetica", 9)
        c.drawString(42, y, (nsn or "—")[:22])
        c.drawString(190, y, (it.get("name") or it.get("nomenclature") or "")[:34])
        c.drawString(400, y, (it.get("part_number") or "")[:12])
        c.drawString(470, y, str(it.get("qty") or 1)[:4])
        if len(dig) >= 13:
            try:
                bc = code128.Code128(dig, barHeight=15, barWidth=0.62)
                bc.drawOn(c, 505, y - 4)
            except Exception:
                pass
        c.setStrokeColorRGB(0.16, 0.19, 0.24); c.setLineWidth(0.4); c.line(42, y - 8, W - 42, y - 8)
        y -= 30
    if not items:
        c.setFillColorRGB(0.55, 0.60, 0.68); c.setFont("Helvetica-Oblique", 11); c.drawString(42, H - 140, "No parts in this request.")
    c.showPage(); c.save(); return buf.getvalue()


if __name__ == "__main__":
    items = [
        {"nsn": "2920-01-333-3333", "name": "ALTERNATOR", "part_number": "A1", "qty": 1},
        {"nsn": "5305-01-111-1111", "name": "BOLT, MACHINE", "part_number": "B1", "qty": 8},
        {"nsn": "", "name": "GASKET (local purchase)", "part_number": "G-77", "qty": 2},
    ]
    pdf = build_pdf(items, {"unit": "B CO 3-7 CAV", "mechanic": "SPC Solomon", "bumper": "C-12", "tm": "TM 9-2320-280-24P"})
    open("/tmp/partspdf_test.pdf", "wb").write(pdf)
    try:
        import pymupdf as fitz
        d = fitz.open("/tmp/partspdf_test.pdf"); pages = d.page_count; txt = d[0].get_text(); d.close()
    except Exception:
        pages = "?"; txt = ""
    print("pdf bytes:", len(pdf), "| valid:", pdf[:5] == b"%PDF-", "| pages:", pages, "| has ALTERNATOR:", "ALTERNATOR" in txt)
    assert pdf[:5] == b"%PDF-", "not a PDF"
    print("partspdf self-test OK")
# END OF FILE
