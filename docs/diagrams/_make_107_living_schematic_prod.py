#!/usr/bin/env python3
"""v0.99.1 — Living Schematic productionization: steps 2 (review) & 3 (Circuit Lab bridge) + observability. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 760
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "Living Schematic → production: review + Circuit Lab bridge   v0.99.1", 18, TXT, 700))
P.append(t(40, 70, "Three steps, now complete: (1) precompute netlists corpus-wide, (2) human review/override, (3) hand off to Circuit Lab.", 11.5, SUB, 400))
hr(86)

steps = [
 ("STEP 1  ·  precompute", GRN, ["build_schemgraph.py (0.99.0)", "-> index/schemcache + coverage TSV.", "4,743 pages cached (verified)."]),
 ("STEP 2  ·  review / override", AMB, ["schemreview.py: append-only sidecar.", "/api/schemgraph_review (queue) +", "_decision (POST). schemflow ⚑ Correct:", "drop missed refs, mark good/bad.", "r_schemgraph MERGES overrides."]),
 ("STEP 3  ·  Circuit Lab bridge", TEAL, ["⚡ Circuit Lab shows the inferred", "netlist (nets/comps/conf) + JSON", "download; build the live circuit", "over the page. (values not inferred)"]),
]
x0, y0, cw, ch = 40, 118, 366, 130
for i, (ti, col, rows) in enumerate(steps):
    cx = x0 + i*(cw+6)
    P.append(box(cx, y0, cw, ch, PANEL, col, 11, 1))
    P.append(t(cx+16, y0+24, ti, 12, col, 700))
    yy = y0+46
    for r in rows: P.append(t(cx+16, yy, r, 9, SUB, 400)); yy += 15
    if i < 2: P.append('<text x="%d" y="%d" font-size="22" fill="%s">&#8594;</text>' % (cx+cw-2, y0+ch/2+7, SUB))
hr(262)

P.append(t(40, 290, "THE REVIEW LOOP (closes the 0-components gap)", 13, AMB, 700))
P.append(box(40, 304, 1100, 78, PANEL, AMB, 12, 1))
s,_ = wrap(58, 328, "CAD-exported sheets outline their label text, so schemgraph finds wires but 0 components. The coverage TSV flags those pages; "
  "the review queue surfaces them; a reviewer drops the missing ref-designators (R12, K3…) which are stored append-only and merged back into "
  "the served graph — so the Flow overlay and Circuit Lab bridge get the human-corrected netlist next time. (R1/R6: index never written.)", 224, 10, SUB, 15)
P.append(s)
hr(398)

P.append(t(40, 426, "OBSERVABILITY + TESTS", 13, ACC, 700))
exp = [
 ("/api/schemgraph_coverage", ACC, "schematic pages · pages-with-components · avg confidence · nets total · pages reviewed."),
 ("test_features_modules.py", GRN, "every features/ module imports; registry populated; new routes registered; schemreview round-trip."),
 ("test_features_integration.py", TEAL, "the 0.90-0.95 imagery/CAD/schematic stack still wired through the v0.98 registry (16 checks)."),
 ("VERIFY-099.bat", PUR, "one host-side button: syntax + UI JS + all suites -> docs/verify_099.log. (run after the USB copy)"),
]
ex0, ey0, ecw, ech = 40, 440, 550, 78
for i, (ti, col, de) in enumerate(exp):
    cx = ex0 + (i % 2)*(ecw+10); cy = ey0 + (i//2)*(ech+8)
    P.append(box(cx, cy, ecw, ech, PANEL, col, 12, 1))
    P.append(t(cx+16, cy+23, ti, 11.5, col, 700))
    s,_ = wrap(cx+16, cy+42, de, 150, 9.3, SUB, 12); P.append(s)
hr(612)

P.append(t(40, 640, "STATUS", 13, GRN, 700))
P.append(box(40, 654, 1100, 66, PANEL, GRN, 12, 1))
s,_ = wrap(58, 676, "Built + logic-verified in-sandbox (schemreview queue/record/override/coverage; schemflow node --check; 4,743 pages cached). "
  "Full host suite pending VERIFY-099.bat (deferred: USB copy in progress). Additive & rollbackable (R1). Remaining backlog item: deep-zoom + callout hotspots (step 4).", 224, 10, SUB, 15)
P.append(s)

P.append(t(40, H-10, "Markup. Dark (R3). v0.99.1 · 2026-07-01 · schemreview.py · /api/schemgraph_review(_decision)/_coverage · schemflow ⚑ · circuitlab bridge. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "107-living-schematic-prod")), "bytes")
