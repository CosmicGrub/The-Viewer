#!/usr/bin/env python3
"""v0.99.26/27 — Parts-request PDF + barcodes · structured PMCS items. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
W, H = 1120, 500
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
P.append(t(40, 46, "Parts-request PDF + barcodes · structured PMCS   v0.99.26/27", 19, TXT, 700))
hr(70)
P.append(t(40, 100, "🏷 Parts-request PDF  (partspdf.py + /api/partspdf)", 13, GRN, 700))
P.append(box(40, 114, 1040, 120, PANEL, GRN, 12, 1))
r1 = ["Printable Parts Request sheet: unit / mechanic / bumper / TM header + item table, with a scannable",
      "Code128 barcode of each NSN so supply SCANS instead of retyping. Local-purchase items (no NSN) get no barcode.",
      "Pure reportlab, offline. Verified in-sandbox: valid PDF, barcodes rendered (docs/partspdf_proof.png)."]
yy = 138
for r in r1:
    P.append('<circle cx="56" cy="%d" r="2.5" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(66, yy, r, 232, 9.6, SUB, 14); P.append(s); yy += 14*n + 5
hr(250)
P.append(t(40, 278, "🗓 Structured PMCS items  (pmcs.py + /pmcs)", 13, ACC, 700))
P.append(box(40, 292, 1040, 120, PANEL, ACC, 12, 1))
r2 = ["pmcs.find now extracts the individual CHECK ITEMS (numbered rows + CHECK/INSPECT/CLEAN/… lines),",
      "not just a page snippet — the finder lists the actual checks per page, with the interval chips it already had.",
      "Verified in-sandbox: pulls 'check engine oil', 'inspect belts', 'ensure parking brake holds', 'drain separator'; ignores prose."]
yy = 316
for r in r2:
    P.append('<circle cx="56" cy="%d" r="2.5" fill="%s"/>' % (yy-3, ACC)); s, n = wrap(66, yy, r, 232, 9.6, SUB, 14); P.append(s); yy += 14*n + 5
hr(428)
P.append(t(40, 452, "R1 · additive & read-only. reportlab barcode = existing dep; PMCS parse is pure regex over the OCR text.", 10, SUB, 400))
P.append(t(40, H-8, "Markup. Dark (R3). v0.99.26/27 · 2026-07-01 · partspdf.py · pmcs.py. Read-only. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "129-bench-parts")), "bytes")
