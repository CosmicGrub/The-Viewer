#!/usr/bin/env python3
"""v0.99.10 — Job Card deeper: task intent + materials/refs + look-alike warning + preview/builder. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 720
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "Job Card, deeper — understands the task, warns on look-alikes   v0.99.10", 19, TXT, 700))
P.append(t(40, 70, "From 'a part' to 'a job': free-text intent, materials & referenced manuals, a look-alike safety warning, and a preview-first builder page.", 11.5, SUB, 400))
hr(86)

# pipeline row
steps = [
 ("free-text task", AMB, ["'replace the alternator'", "→ _task_intent →", "kind=Replacement,", "focus='alternator'"]),
 ("gather (live)", TEAL, ["procedure_for + torque_specs", "+ part_differences", "(look-alike) + partlocate", "/ figureparts (parts+figs)"]),
 ("order + warn", GRN, ["_order_procs floats the", "matching kind to the top;", "_lookalike_warning fires", "only on real differences"]),
 ("preview / PDF", ACC, ["/api/jobcard_preview → counts", "for the /jobcard builder;", "/api/jobcard → the full", "Work Order PDF"]),
]
x0, y0, cw, ch = 40, 116, 268, 132
cxs = []
for i, (ti, col, rows) in enumerate(steps):
    cx = x0 + i*(cw+8); cxs.append(cx)
    P.append(box(cx, y0, cw, ch, PANEL, col, 11, 1))
    P.append(t(cx+14, y0+22, ti, 12, col, 700))
    yy = y0+44
    for r in rows: P.append(t(cx+14, yy, r, 8.9, SUB, 400)); yy += 15
for i in range(3):
    P.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="2" marker-end="url(#a)"/>' % (cxs[i]+cw-2, y0+ch/2, cxs[i+1]+2, y0+ch/2, TEAL))
P.append('<defs><marker id="a" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="%s"/></marker></defs>' % TEAL)
hr(268)

# what got richer
P.append(t(40, 296, "WHAT GOT RICHER", 13, ACC, 700))
P.append(box(40, 310, 545, 168, PANEL, ACC, 12, 1))
rows = ["procedures_feature._parse_procedure now also pulls MATERIALS / CONSUMABLES and referenced manuals (TM/WP/LO/TB/TC) —",
        "  additive keys, so /procedure benefits too. Digit-anchored regex: 'LOCKWASHER'/'LOOSEN' no longer false-match as refs.",
        "jobcard.build_pdf renders a Materials section + a 'Referenced manuals' line per procedure.",
        "Cover gets a ⚠ BEFORE YOU START box when same-name parts differ by UOC/CAGEC/SMR/FSC/part-# (not mere format drift).",
        "Free-text task intent biases the right procedure kind to the top of the order."]
yy = 334
for r in rows:
    indented = r.startswith("  ")
    if not indented:
        P.append('<circle cx="56" cy="%d" r="2.4" fill="%s"/>' % (yy-3, ACC))
    s, n = wrap(70 if indented else 66, yy, r.strip(), 108, 9.2, SUB if indented else TXT, 13)
    P.append(s); yy += 13*n + 5

# builder page mock
bx, by, bw, bh = 604, 310, 536, 168
P.append(box(bx, by, bw, bh, PANEL, "#7fbfff", 12, 1.4))
P.append(t(bx+16, by+26, "/jobcard  —  preview-first builder", 12.5, "#7fbfff", 700))
P.append(box(bx+16, by+40, bw-32, 26, "#10151c", "#2f4858", 6, 1)); P.append(t(bx+26, by+57, "replace the alternator", 10, SUB, 400))
P.append(box(bx+16, by+74, 150, 20, "#16202b", "#26333f", 999, 1)); P.append(t(bx+26, by+88, "Task  Replacement", 8.6, "#bcd", 400))
P.append(box(bx+172, by+74, 120, 20, "#16202b", "#26333f", 999, 1)); P.append(t(bx+182, by+88, "NSN 2920-01-…", 8.6, "#bcd", 400))
P.append(box(bx+16, by+100, bw-32, 22, "#2a130c", "#d1633a", 6, 1)); P.append(t(bx+26, by+115, "⚠ LOOK-ALIKE: 2 parts share this name — confirm UOC/NSN", 8.6, "#f2c3ad", 400))
P.append(t(bx+16, by+140, "Procedures 2 · Torque 3 · Parts 11 · Figures 6", 9.5, TXT, 400))
P.append(box(bx+bw-176, by+bh-30, 160, 22, "#1a7f4b", "#1a7f4b", 6, 1)); P.append(t(bx+bw-160, by+bh-15, "🧾 Generate Work Order", 9, "#fff", 700))
hr(494)

P.append(t(40, 522, "VERIFIED / R1", 13, GRN, 700))
P.append(box(40, 536, 1100, 150, PANEL, GRN, 12, 1))
ver = ["_parse_procedure tested standalone: materials + tools + cautions + steps captured; refs digit-anchored (no 'LOCKWASHER'); steps-only pages still parse.",
       "jobcard intent/order/warning tested standalone: replace→Replacement, adjust→Adjustment, matching kind floated first, warning only on real look-alikes.",
       "build_pdf smoke-rendered a 2-page PDF with the Materials section + the ⚠ BEFORE YOU START box present (verified via fitz text extraction).",
       "jobcard.html inline JS passes node --check; added to verify_ui.py + VERIFY-099.bat. /jobcard registered in _PAGES; route signature fixed for lookalike.",
       "All read-only; additive keys + one module + two routes + one page + one parser enrichment. Nothing writes the index (R1/R6). Host-verify pending in VERIFY-099.bat."]
yy = 558
for v in ver:
    P.append('<circle cx="56" cy="%d" r="2.6" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(66, yy, v, 224, 9.2, SUB, 13); P.append(s); yy += 13*n + 4

P.append(t(40, H-8, "Markup. Dark (R3). v0.99.10 · 2026-07-01 · jobcard.py + procedures_feature parse · /api/jobcard_preview · /jobcard. Read-only. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "114-jobcard-deep")), "bytes")
