#!/usr/bin/env python3
"""
THE VIEWER -- 104th ECC Parts Request Sheet generator.

Produces a clean, printable PDF replica of the unit's parts request sheet.
The onboarding/modal answers fill the header; the parts cart fills the item blocks.

Usage as a library:
    from parts_request_pdf import build_request_pdf
    build_request_pdf("out.pdf", session, items)

  session = {"mechanic": "...", "bumper": "...", "fault": "...",
             "tm": "...", "uoc": "...", "tech_status": "...",
             "motor_sergeant": "..."}
  items   = [{"item_name","nsn","qty","fig","part","unit_price","aac","arc"}, ...]

CLI (writes a demo sheet):
    python parts_request_pdf.py demo.pdf
"""
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

RED = (0.80, 0.10, 0.10)
BLACK = (0, 0, 0)
GREY = (0.45, 0.45, 0.45)

def _label_value(c, x, y, label, value, label_color=BLACK, label_font=("Helvetica-Bold", 9),
                 line_to=None, value_font=("Helvetica", 9)):
    c.setFont(*label_font); c.setFillColorRGB(*label_color)
    c.drawString(x, y, label)
    lw = c.stringWidth(label, *label_font)
    vx = x + lw + 4
    end = line_to if line_to else vx + 120
    # value
    if value:
        c.setFont(*value_font); c.setFillColorRGB(*BLACK)
        c.drawString(vx + 2, y + 1, str(value))
    # underline for the blank
    c.setStrokeColorRGB(*GREY); c.setLineWidth(0.5)
    c.line(vx, y - 2, end, y - 2)
    return end

def build_request_pdf(out_path, session, items):
    session = session or {}
    items = items or []
    # Paginate into sheets of 6 item blocks each (>6 items -> multiple 104th sheets).
    chunks = [items[i:i + 6] for i in range(0, len(items), 6)] or [[]]
    total = len(chunks)

    c = canvas.Canvas(out_path, pagesize=letter)
    W, H = letter
    M = 0.9 * inch

    for pi, chunk in enumerate(chunks):
        rows = list(chunk) + [{}] * (6 - len(chunk))
        y = H - 0.7 * inch

        # ---- Title ----
        c.setFillColorRGB(*BLACK); c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(W/2, y, "104TH ECC PARTS REQUEST SHEET")
        if total > 1:
            c.setFont("Helvetica-Bold", 9); c.setFillColorRGB(*GREY)
            c.drawRightString(W - M, y, f"Sheet {pi+1} of {total}")
        y -= 16
        c.setFillColorRGB(*RED); c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(W/2, y, "(FILL OUT ALL BLOCKS)")
        y -= 26

        # ---- Header block ----
        right = W - M
        _label_value(c, M, y, "MECHANIC'S NAME (PRINT/SIGN):", session.get("mechanic"), line_to=right)
        y -= 18
        midx = M + 2.7 * inch
        _label_value(c, M, y, "BUMPER#:", session.get("bumper"), line_to=midx - 10)
        _label_value(c, midx, y, "FAULT:", session.get("fault"), line_to=right)
        y -= 18
        col2 = M + 2.7 * inch; col3 = M + 4.4 * inch
        _label_value(c, M, y, "TM:", session.get("tm"), line_to=col2 - 10)
        _label_value(c, col2, y, "UOC:", session.get("uoc"), line_to=col3 - 10)
        _label_value(c, col3, y, "TECH STATUS:", session.get("tech_status"), line_to=right)
        y -= 22

        # ---- Item blocks (6) ----
        block_h = 58
        for it in rows:
            bx, bw = M, right - M
            c.setStrokeColorRGB(*BLACK); c.setLineWidth(1)
            c.rect(bx, y - block_h, bw, block_h, stroke=1, fill=0)
            iy = y - 16
            nsn_x = bx + 3.4 * inch
            _label_value(c, bx + 10, iy, "ITEM NAME:", it.get("item_name"), line_to=nsn_x - 10)
            _label_value(c, nsn_x, iy, "NSN:", it.get("nsn"), line_to=bx + bw - 10)
            iy -= 18
            qx = bx + 10; fx = bx + 1.7 * inch; px = bx + 3.0 * inch
            _label_value(c, qx, iy, "QTY:", it.get("qty"), line_to=fx - 10)
            _label_value(c, fx, iy, "FIG#:", it.get("fig"), line_to=px - 6)
            _label_value(c, px, iy, "PART #:", it.get("part"), line_to=bx + bw - 10)
            iy -= 17
            # FEDLOG row (red labels)
            c.setFont("Helvetica-Bold", 7); c.setFillColorRGB(*RED)
            c.drawString(bx + 10, iy, "(FEDLOG)")
            upx = bx + 0.9 * inch; aacx = bx + 3.4 * inch; arcx = bx + 4.7 * inch
            _label_value(c, upx, iy, "UNIT PRICE:", it.get("unit_price"), label_color=RED, line_to=aacx - 10)
            _label_value(c, aacx, iy, "AAC:", it.get("aac"), label_color=RED, line_to=arcx - 10)
            _label_value(c, arcx, iy, "ARC:", it.get("arc"), label_color=RED, line_to=bx + bw - 10)
            y -= (block_h + 8)

        # ---- Footer ----
        y -= 6
        _label_value(c, M, y, "MOTOR SERGEANT / SENIOR MECHANIC:", session.get("motor_sergeant"), line_to=right)
        c.showPage()

    c.save()
    return out_path

def _demo():
    session = {
        "mechanic": "SPC R. Alvarez", "bumper": "B-14", "tm": "TM 9-2320-280-20-2",
        "fault": "No-start; dual-voltage alternator not charging, coolant seep at water pump",
        "uoc": "", "tech_status": "NMC", "motor_sergeant": "",
    }
    items = [
        {"item_name": "GASKET, WATER PUMP", "nsn": "5330-01-186-9023", "qty": "1",
         "fig": "84", "part": "12342418", "unit_price": "", "aac": "", "arc": ""},
        {"item_name": "ALTERNATOR, DUAL VOLTAGE", "nsn": "2920-01-449-2202", "qty": "1",
         "fig": "12", "part": "12446052", "unit_price": "", "aac": "", "arc": ""},
        {"item_name": "FILTER ELEMENT, FUEL", "nsn": "2910-01-374-9226", "qty": "2",
         "fig": "7", "part": "23512387", "unit_price": "", "aac": "", "arc": ""},
        {"item_name": "BELT, V, ACCESSORY DRIVE", "nsn": "3030-01-356-1234", "qty": "1",
         "fig": "9", "part": "12338456", "unit_price": "", "aac": "", "arc": ""},
    ]
    out = sys.argv[1] if len(sys.argv) > 1 else "demo_parts_request.pdf"
    build_request_pdf(out, session, items)
    print("wrote", out)

if __name__ == "__main__":
    _demo()
