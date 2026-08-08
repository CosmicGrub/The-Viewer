#!/usr/bin/env python3
"""v0.99.6 — Mission control: coverage dashboard + part locator + doctor. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 700
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "Mission control: coverage · locator · doctor   v0.99.6", 19, TXT, 700))
P.append(t(40, 70, "Turn the enrichment batches into things you can SEE and USE — measure the corpus, jump to any part's figures, and health-check the whole system.", 11.5, SUB, 400))
hr(86)

cards = [
 ("📊 /coverage", GRN, ["coverage.py + /api/coverage.", "One roll-up: OCR% · CAD% ·", "vectorized% · schematic netlists ·", "models · figure crops · sidecar", "health. KPI bars + cards.", "Verified vs a synthetic index."]),
 ("🧭 /locate", AMB, ["partlocate.py + /api/partlocate.", "'Where does this part show up?'", "NSN/PN/name -> every figure &", "page that calls it out, deduped,", "with Deep-Zoom / Vector / open", "links. Verified: 3 hits / 2 docs."]),
 ("🩺 DOCTOR.bat", TEAL, ["doctor.py: deps, CORPUS-PATH", "reachability (the #1 migration", "trap), coverage, cache counts,", "disk free, recent errors ->", "docs/doctor_report.txt.", "Great before/after a move."]),
]
x0, y0, cw, ch = 40, 118, 366, 150
for i, (ti, col, rows) in enumerate(cards):
    cx = x0 + i*(cw+6)
    P.append(box(cx, y0, cw, ch, PANEL, col, 11, 1))
    P.append(t(cx+16, y0+24, ti, 13, col, 700))
    yy = y0+48
    for r in rows: P.append(t(cx+16, yy, r, 8.9, SUB, 400)); yy += 15
hr(288)

P.append(t(40, 316, "HOW IT TIES TOGETHER", 13, ACC, 700))
P.append(box(40, 330, 1100, 96, PANEL, ACC, 12, 1))
s,_ = wrap(58, 354, "The batches (OCR, CAD, schemgraph, vectorize) each write a sidecar + coverage file. /coverage reads them all into "
  "one picture. /locate reads the parts index to send you straight to a part's figures — which you then Deep-Zoom or Vectorize. "
  "DOCTOR checks the whole thing is healthy AND that the corpus is still reachable after a move. All read-only, sidecar-only (R1/R6).", 224, 10, SUB, 15)
P.append(s)
hr(442)

P.append(t(40, 470, "VERIFIED / R1", 13, GRN, 700))
P.append(box(40, 484, 1100, 96, PANEL, GRN, 12, 1))
ver = ["coverage.py / partlocate.py logic-tested in-sandbox on synthetic indexes (percentages + dedup correct).",
       "coverage.html + locate.html pass node --check (added to verify_ui.py); new modules added to VERIFY-099.bat.",
       "doctor.py parses; dep + corpus-path helpers verified. Route registrations pending the host suite (mount truncation).",
       "Additive & rollbackable: 3 modules + 3 pages + 4 read-only routes + DOCTOR.bat. Nothing writes the index."]
yy = 506
for v in ver:
    P.append('<circle cx="56" cy="%d" r="2.6" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(66, yy, v, 224, 9.4, SUB, 13); P.append(s); yy += 13*n + 4

P.append(t(40, H-10, "Markup. Dark (R3). v0.99.6 · 2026-07-01 · coverage.py //coverage · partlocate.py //locate · doctor.py/DOCTOR.bat. Read-only. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "111-mission-control")), "bytes")
