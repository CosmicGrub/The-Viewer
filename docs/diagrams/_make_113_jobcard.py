#!/usr/bin/env python3
"""v0.99.9 — Job Card / Work Order: compose procedures + torque + parts + figures into one bay-ready PDF. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 720
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "Job Card / Work Order — one bay-ready PDF for a TASK   v0.99.9", 19, TXT, 700))
P.append(t(40, 70, "Requirement C of the brief: a complete instructional rundown — how to remove/install, what tools, what torque — assembled from what's already in the index.", 11.5, SUB, 400))
hr(86)

# left: the four live sources feeding the composer
src = [
 ("procedure_for()", AMB, ["kind (Removal/Install/…),", "numbered steps, tools", "required, WARNING/CAUTION/", "NOTE callouts — cited."]),
 ("torque_specs()", GRN, ["stated torque values near", "'torque'/'tighten' + unit", "(ft-lb / in-lb / N·m),", "each cited to its page."]),
 ("partlocate + figureparts", TEAL, ["every part on the task's", "figures (NSN/P-N/CAGE/SMR),", "deduped across the pages."]),
 ("fitz page render", ACC, ["the actual TM figure pages", "rasterized (source of truth)", "appended after the text."]),
]
x0, y0, cw, ch = 40, 118, 300, 132
for i, (ti, col, rows) in enumerate(src):
    cx = x0 + (i % 2)*(cw+8); cy = y0 + (i//2)*(ch+10)
    P.append(box(cx, cy, cw, ch, PANEL, col, 11, 1))
    P.append(t(cx+14, cy+22, ti, 12, col, 700))
    yy = cy+44
    for r in rows: P.append(t(cx+14, yy, r, 9, SUB, 400)); yy += 15
# composer box on the right
bx, by, bw, bh = 664, 118, 476, 274
P.append(box(bx, by, bw, bh, PANEL, "#7fbfff", 12, 1.5))
P.append(t(bx+18, by+28, "jobcard.build_pdf()  →  Work Order .pdf", 13, "#7fbfff", 700))
P.append(t(bx+18, by+50, "GET /api/jobcard?q=<task | part | NSN>", 10, SUB, 400))
sec = ["Cover — task, part label, NSN, counts, SAFETY line",
       "1 · Procedures — steps + tools + WARNING/CAUTION",
       "2 · Torque values — value + context + citation",
       "3 · Parts on the figures — NSN / P-N / CAGE / SMR",
       "4 · Figure pages — rendered from the source TMs"]
yy = by+78
for s in sec:
    P.append('<circle cx="%d" cy="%d" r="2.6" fill="%s"/>' % (bx+24, yy-3, GRN)); P.append(t(bx+36, yy, s, 10, TXT, 400)); yy += 22
P.append(t(bx+18, by+bh-16, "Pure reportlab + PyMuPDF + Pillow · offline · read-only · dark theme (R3)", 8.6, SUB, 400))
# arrows from sources to composer
for i in range(4):
    cy = y0 + (i//2)*(ch+10) + ch/2
    P.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1.6" marker-end="url(#a)"/>' % (348+(i%2)*(cw+8), cy, bx-4, by+bh/2, "#4a6a8a"))
P.append('<defs><marker id="a" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#4a6a8a"/></marker></defs>')
hr(410)

P.append(t(40, 438, "WHY IT MATTERS", 13, ACC, 700))
P.append(box(40, 452, 1100, 84, PANEL, ACC, 12, 1))
s,_ = wrap(58, 476, "Everything the app had — search, procedures, torque, the locator, figure rendering — was separate. The Job Card fuses them "
  "into the one artifact a mechanic actually carries into the bay: a single work order for 'replace the alternator' with the steps, the "
  "tools, the safety callouts, the torque, the parts and the figures, every line cited to the real TM page. This is the brief's requirement C.", 224, 10, SUB, 15)
P.append(s)
hr(552)

P.append(t(40, 580, "VERIFIED / R1", 13, GRN, 700))
P.append(box(40, 594, 1100, 96, PANEL, GRN, 12, 1))
ver = ["build_pdf() self-test produced a valid 4-page PDF from synthetic content (cover + text page + 2 figure pages); rendered & eyeballed (docs/jobcard_proof*.png).",
       "Auto page-break, WARNING/CAUTION in orange, torque in green, parts with NSN/P-N/CAGE/SMR — all correct. locate.html JS passes node --check.",
       "Route /api/jobcard gathers procedures+torque from the LIVE features (core.db injected) then calls the pure assembler. 🧾 Work Order button on /locate.",
       "Additive & rollbackable: one module + one read-only route + one button. Nothing writes the index (R1/R6). Host-verify in VERIFY-099.bat."]
yy = 616
for v in ver:
    P.append('<circle cx="56" cy="%d" r="2.6" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(66, yy, v, 224, 9.2, SUB, 13); P.append(s); yy += 13*n + 3

P.append(t(40, H-8, "Markup. Dark (R3). v0.99.9 · 2026-07-01 · jobcard.py //api/jobcard · 🧾 on /locate. Read-only. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "113-jobcard")), "bytes")
