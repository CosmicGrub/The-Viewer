#!/usr/bin/env python3
"""FIX 0.72.2: /api/threed_refs 500 — a helper moved during modularization wasn't re-imported. (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 560
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
P.append(t(40, 46, "FIX — why /api/threed_refs returned 500  (v0.72.2)", 19, TXT, 700))
P.append(t(40, 70, "One red line in VERIFY-ALL. Plain version: a helper function moved to a new file, and one old caller never got the new address.", 11, SUB, 400))
P.append('<line x1="40" y1="86" x2="%d" y2="86" stroke="%s"/>' % (W - 40, LINE))

# The chain of what happened
P.append(t(40, 116, "What actually happened, step by step", 13, TXT, 700))
steps = [
  ("1", "A test asked the 3D viewer: “where does part 5305-01-674-1467 show up in the manuals?”", ACC),
  ("2", "That handler also lists which Smart Collections the part belongs to — so it calls a helper named _collections_defs().", TEAL),
  ("3", "Back in v0.70 we split the big server file up; _collections_defs() MOVED into collections_feature.py.", AMB),
  ("4", "The move re-imported the 5 public collection functions back — but NOT this one internal helper.", AMB),
  ("5", "So at request time the server looked for _collections_defs(), couldn't find the name -> NameError.", RED),
  ("6", "The route wraps everything in “catch any error -> return 500”, so the user/test just saw HTTP 500.", RED),
]
y = 138
for n, txt, col in steps:
    P.append('<circle cx="62" cy="%d" r="11" fill="none" stroke="%s" stroke-width="1.5"/>' % (y + 4, col))
    P.append(t(62, y + 8, n, 11, col, 700, "middle"))
    s, used = wrap(86, y, txt, 168, 10.5, TXT, 13)
    P.append(s); y += 13 * used + 8

# Fix box
P.append(box(40, y + 4, 1100, 70, PANEL, GRN, 12, 1))
P.append(t(58, y + 26, "THE FIX  (one line)", 11.5, GRN, 700))
s, _ = wrap(58, y + 46, "Add the missing name to the import in viewer_app.py:  from collections_feature import (…, _collections_defs). Nothing else changed — no new logic, no database touch. The page-search half of the same handler was always fine because it had its own error guard; that's why only ONE of 86 checks was red.", 200, 9.5, SUB, 13)
P.append(s)

yb = y + 84
P.append(box(40, yb, 540, 58, PANEL, PUR, 12, 1))
s, _ = wrap(58, yb + 22, "Layman's analogy: a department (the helper) moved to a new building. Most callers got the new address; this one caller kept dialing the old room number and got 'no such extension' — which the switchboard reported as a generic 'error 500'.", 96, 9, SUB, 12)
P.append(s)
P.append(box(596, yb, 544, 58, PANEL, ACC, 12, 1))
s, _ = wrap(614, yb + 22, "Verified: reproduced the import + injected-core mechanism in isolation (both resolve); grepped for any OTHER helpers left behind by the split — none. Re-run VERIFY-ALL.bat to see test_routes go 34/34.", 98, 9, SUB, 12)
P.append(s)

P.append(t(40, H - 8, "FIX diagram. Dark (R3). v0.72.2 · 2026-06-03 · viewer_app.py import line · root cause: v0.70 modularization left _collections_defs un-imported. Rollbackable (R1).", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "88-threedrefs-500-fix")), "bytes")
