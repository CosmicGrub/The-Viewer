"""forms.py -- generate DA Form 2404 / 5988-E style PMCS worksheets (roadmap Vol.2 #71) and DA Form 2407 /
5990-E style maintenance requests (roadmap Vol.2 #72). After a PMCS a mechanic must record equipment
deficiencies and shortcomings, the corrective action, and a status symbol; when a fault exceeds crew level a
maintenance request goes to support. build_2404() mirrors the 2404's columns (TM item no. | deficiencies &
shortcomings | corrective action | status) with the standard status legend; build_2407() composes the
equipment identity + fault + work-requested request. Both are labelled a WORKSHEET AID -- transcribe onto the
official form / GCSS-Army as your unit requires.

build_2404(data) and build_2407(data) are pure (return PDF bytes) and unit-testable. No corpus writes."""

from __future__ import annotations
import io

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    _OK = True
except Exception:                                   # pragma: no cover
    _OK = False

# DA PMCS status symbols (the ones a mechanic writes in the status column)
STATUS_LEGEND = [
    ("X", "Inoperative / DEADLINED — do not operate"),
    ("-  (horizontal dash)", "A deficiency, but the item is operable"),
    ("/  (diagonal)", "Fault found; parts on order or corrected — needs follow-up"),
    ("Circle-X", "Deadlined for a missing/overdue safety item"),
    ("Blank / OK", "Serviceable, no fault"),
]


def available() -> bool:
    return _OK


def _esc(s):
    return ("" if s is None else str(s)).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_2404(data: dict) -> bytes:
    """data: {equipment:{admin_no,nomenclature,model,miles,hours}, faults:[{item,deficiency,corrective,status}],
    inspector, supervisor, date, organization}. Returns PDF bytes."""
    if not _OK:
        raise RuntimeError("reportlab not installed")
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("cell", parent=ss["BodyText"], fontSize=8.5, leading=10.5))
    ss.add(ParagraphStyle("small", parent=ss["BodyText"], fontSize=7.5, textColor=colors.HexColor("#555"), leading=9))
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch,
                            leftMargin=0.6 * inch, rightMargin=0.6 * inch, title="PMCS worksheet")
    eq = data.get("equipment") or {}
    E = [Paragraph("PMCS Worksheet <font size=8 color='#666'>(DA Form 2404 / 5988-E style — worksheet aid)</font>",
                   ParagraphStyle("T", parent=ss["Title"], fontSize=15, textColor=colors.HexColor("#12325a")))]
    hdr = [["Admin/Bumper No.:", _esc(eq.get("admin_no")), "Nomenclature:", _esc(eq.get("nomenclature"))],
           ["Model:", _esc(eq.get("model")), "Miles / Hours:", _esc("%s / %s" % (eq.get("miles", ""), eq.get("hours", "")))],
           ["Organization:", _esc(data.get("organization")), "Date:", _esc(data.get("date"))]]
    th = Table(hdr, colWidths=[1.2 * inch, 2.6 * inch, 1.2 * inch, 2.4 * inch])
    th.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 8.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#12325a")),
                            ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#12325a")),
                            ("LINEBELOW", (1, 0), (1, -1), 0.4, colors.grey), ("LINEBELOW", (3, 0), (3, -1), 0.4, colors.grey)]))
    E.append(th)
    E.append(HRFlowable(width="100%", color=colors.HexColor("#12325a"), spaceBefore=6, spaceAfter=6))

    rows = [["TM ITEM\nNO.", "DEFICIENCIES AND SHORTCOMINGS", "CORRECTIVE ACTION", "STATUS"]]
    faults = data.get("faults") or []
    for f in faults[:60]:
        rows.append([_esc(f.get("item")), Paragraph(_esc(f.get("deficiency")), ss["cell"]),
                     Paragraph(_esc(f.get("corrective")), ss["cell"]), _esc(f.get("status"))])
    # pad with blank lines to a usable worksheet even when few/no faults
    for _ in range(max(0, 12 - len(faults))):
        rows.append(["", "", "", ""])
    tb = Table(rows, colWidths=[0.7 * inch, 3.2 * inch, 2.6 * inch, 0.7 * inch], repeatRows=1)
    tb.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, 0), 7.5), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef6")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b8c2ce")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ROWHEIGHT", (0, 1), (-1, -1), 20) if False else ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
    ]))
    E.append(tb)
    E.append(Spacer(1, 8))
    leg = [["Status symbols:"]] + [["%s — %s" % (s, d)] for s, d in STATUS_LEGEND]
    lt = Table(leg, colWidths=[6.2 * inch])
    lt.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 7.5), ("TEXTCOLOR", (0, 1), (0, -1), colors.HexColor("#333"))]))
    E.append(lt)
    E.append(Spacer(1, 8))
    sig = Table([["Inspector: %s" % _esc(data.get("inspector")), "Supervisor: %s" % _esc(data.get("supervisor"))]],
                colWidths=[3.1 * inch, 3.1 * inch])
    sig.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.grey), ("TOPPADDING", (0, 0), (-1, 0), 14)]))
    E.append(sig)
    E.append(Paragraph("Worksheet aid generated by THE VIEWER. Transcribe onto the authoritative DA Form 2404 / "
                       "5988-E (or GCSS-Army) per your unit SOP. Verify each corrective action against the TM.", ss["small"]))
    doc.build(E)
    return buf.getvalue()


def build_2407(data: dict) -> bytes:
    """DA Form 2407 / 5990-E style MAINTENANCE REQUEST (roadmap Vol.2 #72). When a fault is beyond the
    operator/crew level, a work request goes to support maintenance. This composes a clean printable request:
    requesting unit + equipment identity + the fault/deficiency + the work requested + priority.
    data: {organization, wo_no, jon, priority, date, equipment:{admin_no,nomenclature,model,serial,nsn,miles,hours},
    fault, work_requested, requested_by, approved_by, remarks}. WORKSHEET AID -- transcribe onto the official
    DA 2407 / GCSS-Army work order. Pure (returns PDF bytes)."""
    if not _OK:
        raise RuntimeError("reportlab not installed")
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("cell7", parent=ss["BodyText"], fontSize=9, leading=11.5))
    ss.add(ParagraphStyle("tiny", parent=ss["BodyText"], fontSize=7.5, textColor=colors.HexColor("#555"), leading=9))
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch,
                            leftMargin=0.6 * inch, rightMargin=0.6 * inch, title="Maintenance request")
    eq = data.get("equipment") or {}
    E = [Paragraph("Maintenance Request <font size=8 color='#666'>(DA Form 2407 / 5990-E style — worksheet aid)</font>",
                   ParagraphStyle("T2", parent=ss["Title"], fontSize=15, textColor=colors.HexColor("#12325a")))]
    top = [["Requesting Org.:", _esc(data.get("organization")), "Work Order No.:", _esc(data.get("wo_no"))],
           ["Job Order No. (JON):", _esc(data.get("jon")), "Priority:", _esc(data.get("priority"))],
           ["Date:", _esc(data.get("date")), "", ""]]
    tt = Table(top, colWidths=[1.5 * inch, 2.3 * inch, 1.3 * inch, 2.3 * inch])
    tt.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#12325a")),
                            ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#12325a")),
                            ("LINEBELOW", (1, 0), (1, -1), 0.4, colors.grey), ("LINEBELOW", (3, 0), (3, 1), 0.4, colors.grey)]))
    E.append(tt)
    E.append(HRFlowable(width="100%", color=colors.HexColor("#12325a"), spaceBefore=6, spaceAfter=6))

    idrows = [["EQUIPMENT IDENTIFICATION", ""],
              ["Admin/Bumper No.", _esc(eq.get("admin_no"))],
              ["Nomenclature", _esc(eq.get("nomenclature"))],
              ["Model", _esc(eq.get("model"))],
              ["Serial No.", _esc(eq.get("serial"))],
              ["NSN", _esc(eq.get("nsn"))],
              ["Miles / Hours", _esc("%s / %s" % (eq.get("miles", ""), eq.get("hours", "")))]]
    idt = Table(idrows, colWidths=[2.0 * inch, 4.2 * inch])
    idt.setStyle(TableStyle([
        ("SPAN", (0, 0), (1, 0)), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef6")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b8c2ce")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TEXTCOLOR", (0, 1), (0, -1), colors.HexColor("#12325a")),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    E.append(idt)
    E.append(Spacer(1, 8))

    def _block(title, body, minlines=3):
        txt = _esc(body) or ("<br/>" * minlines)
        b = Table([[Paragraph("<b>%s</b>" % title, ss["cell7"])], [Paragraph(txt, ss["cell7"])]], colWidths=[6.2 * inch])
        b.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b8c2ce")),
                               ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#e8eef6")),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 1), (0, 1), 10),
                               ("BOTTOMPADDING", (0, 1), (0, 1), 22)]))
        return b

    E.append(_block("FAULT / DEFICIENCY (describe the malfunction)", data.get("fault")))
    E.append(Spacer(1, 6))
    E.append(_block("WORK REQUESTED", data.get("work_requested")))
    E.append(Spacer(1, 6))
    if data.get("remarks"):
        E.append(_block("REMARKS", data.get("remarks"), minlines=2))
        E.append(Spacer(1, 6))
    sig = Table([["Requested by: %s" % _esc(data.get("requested_by")), "Approved by: %s" % _esc(data.get("approved_by"))]],
                colWidths=[3.1 * inch, 3.1 * inch])
    sig.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.grey), ("TOPPADDING", (0, 0), (-1, 0), 16)]))
    E.append(sig)
    E.append(Paragraph("Worksheet aid generated by THE VIEWER. Transcribe onto the authoritative DA Form 2407 / "
                       "5990-E (or GCSS-Army work order) per your unit SOP. Verify the requested work against the TM.", ss["tiny"]))
    doc.build(E)
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# self-test: `python forms.py`                                                #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import sys
    if not available():
        print("forms self-test SKIPPED (reportlab not installed)"); sys.exit(0)
    data = {
        "equipment": {"admin_no": "HQ-21", "nomenclature": "TRUCK, UTILITY", "model": "M1151", "miles": 42311, "hours": 1875},
        "organization": "B CO 1-2 IN", "date": "2026-07-02", "inspector": "SPC Rivera", "supervisor": "SSG Cole",
        "faults": [
            {"item": "18", "deficiency": "Left front tire below serviceable tread", "corrective": "Replace tire; on order", "status": "/"},
            {"item": "31", "deficiency": "Service brake soft, low pedal", "corrective": "Bleed brakes; deadlined", "status": "X"},
            {"item": "9", "deficiency": "Headlight blackout marker dim", "corrective": "Cleaned contacts, operable", "status": "-"},
        ],
    }
    pdf = build_2404(data)
    assert pdf[:5] == b"%PDF-", "not a PDF"
    assert len(pdf) > 2500, "PDF too small"
    print("forms.build_2404 OK  (valid %d-byte worksheet, %d faults + blank lines + status legend)"
          % (len(pdf), len(data["faults"])))
    # empty worksheet still builds (blank form)
    blank = build_2404({"equipment": {"admin_no": "____"}})
    assert blank[:5] == b"%PDF-"
    print("blank worksheet OK")

    # DA 2407 maintenance request
    req = build_2407({
        "organization": "B CO 1-2 IN", "wo_no": "WO-0042", "jon": "J7-118", "priority": "02", "date": "2026-07-03",
        "equipment": {"admin_no": "HQ-21", "nomenclature": "TRUCK, UTILITY", "model": "M1151",
                      "serial": "NM12345", "nsn": "2320-01-565-4055", "miles": 42311, "hours": 1875},
        "fault": "Service brake soft, low pedal; does not hold on grade.",
        "work_requested": "Diagnose and repair service brake system; bleed and road-test.",
        "requested_by": "SSG Cole", "approved_by": "CW2 Diaz", "remarks": "Deadlined — Circle-X.",
    })
    assert req[:5] == b"%PDF-" and len(req) > 2500, "2407 PDF bad"
    print("forms.build_2407 OK  (valid %d-byte maintenance request)" % len(req))
    blank2 = build_2407({"equipment": {"admin_no": "____"}})
    assert blank2[:5] == b"%PDF-"
    print("blank maintenance request OK")
    print("forms self-test PASS")

# END OF FILE
