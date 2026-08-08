#!/usr/bin/env python3
"""v0.99.12 — Verification map: what the regression suites guard, incl. the new work-order tests. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 700
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "Verification map — what VERIFY-099.bat now guards   v0.99.12", 19, TXT, 700))
P.append(t(40, 70, "The pre-1.0 hardening pass starts by locking in the work-order stack: behaviors verified by hand while building are now permanent regression tests.", 11.5, SUB, 400))
hr(86)

suites = [
 ("test_features / _integration", TEAL, ["restructure kept the 0.90–0.95", "imagery/CAD/schematic stack wired;", "CAD_VERSION 7, routes registered,", "material_for, schemgraph, localmodel."]),
 ("test_features_modules", ACC, ["every features/*.py imports;", "registry populated; new schemgraph", "review routes present; schemreview", "sidecar round-trips."]),
 ("test_jobcard  (NEW)", GRN, ["figureparts dedup + fig meta + urls;", "jobcard intent/order/warning/preview;", "build_pdf valid multi-page;", "procedure materials + refs parse."]),
 ("test_routes / _search / _hardening", AMB, ["route table shape; search quality", "(ranking/dedup); hardening (POST cap,", "same-origin, param validation →", "400 not 500)."]),
]
x0, y0, cw, ch = 40, 118, 268, 150
for i, (ti, col, rows) in enumerate(suites):
    cx = x0 + i*(cw+8)
    P.append(box(cx, y0, cw, ch, PANEL, col, 11, 1))
    P.append(t(cx+14, y0+24, ti, 11.5, col, 700))
    yy = y0+46
    for r in rows: P.append(t(cx+14, yy, r, 8.8, SUB, 400)); yy += 15
hr(290)

P.append(t(40, 318, "WHAT test_jobcard PINS DOWN", 13, GRN, 700))
P.append(box(40, 332, 1100, 116, PANEL, GRN, 12, 1))
rows = ["figureparts.parts_on: a part listed twice on a sheet counts ONCE; figure no./title surfaced; NSN-first; dossier URLs; bad input safe.",
        "jobcard._task_intent: 'replace…'→Replacement, 'adjust…'→Adjustment, a bare NSN→no verb. _order_procs floats the matching kind first.",
        "jobcard._lookalike_warning: fires when same-name parts differ by UOC/CAGEC/SMR/FSC/part-#; SILENT on NSN format-drift; None when absent.",
        "jobcard.build_pdf: still emits a valid multi-page PDF once the Materials section + ⚠ BEFORE-YOU-START box are present.",
        "procedures_feature._parse_procedure: MATERIALS captured, TM/WP/LO/TB/TC refs digit-anchored (no 'LOCKWASHER'), steps-only page still parses."]
yy = 356
for r in rows:
    P.append('<circle cx="56" cy="%d" r="2.4" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(66, yy, r, 232, 9.4, SUB, 13); P.append(s); yy += 13*n + 3
hr(462)

P.append(t(40, 490, "HOW IT RUNS (mount-truncation aware)", 13, ACC, 700))
P.append(box(40, 504, 1100, 96, PANEL, ACC, 12, 1))
s,_ = wrap(58, 528, "figureparts.py is small/un-grown so its checks run in-sandbox now (green). jobcard.py + procedures_feature.py GREW this "
  "session, so the sandbox mount serves truncated reads — their assertions were verified standalone while building and now run "
  "HOST-SIDE via VERIFY-099.bat (python tests\\test_jobcard.py). Same discipline as the rest of the 0.99.x wave: logic in-sandbox, wiring host-side.", 226, 10, SUB, 15)
P.append(s)
hr(614)

P.append(t(40, 642, "R1 · additive: one new test module + one line in the verify batch. Nothing writes the index. Next hardening step: property/fuzz over the pure helpers.", 10, SUB, 400))
P.append(t(40, H-8, "Markup. Dark (R3). v0.99.12 · 2026-07-01 · tests/test_jobcard.py + VERIFY-099.bat. Read-only. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "116-verification-map")), "bytes")
