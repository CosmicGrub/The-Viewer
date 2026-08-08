#!/usr/bin/env python3
"""v0.84.0 — parametric shape pass: box-rate 24.7% -> 9.3% on the real corpus. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 640
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
P.append(t(40, 46, "3-D parametric shape pass  (v0.84.0)", 19, TXT, 700))
P.append(t(40, 70, "Measured the classifier against the live index, then targeted the real offenders. No guessing — every change is data-driven.", 11, SUB, 400))
P.append('<line x1="40" y1="86" x2="%d" y2="86" stroke="%s"/>' % (W - 40, LINE))

# before/after bars
def bar(x, y, w, pct, col, lab):
    P.append(box(x, y, w, 26, P2, LINE, 6, 1))
    P.append(box(x, y, int(w * pct / 100.0), 26, col, col, 6, 0))
    P.append(t(x + w + 12, y + 18, lab, 11, TXT, 700))
P.append(t(40, 118, "Recognizable shape (vs. box fallback), 24,312 figure-bearing parts", 12.5, TXT, 700))
bar(40, 132, 360, 75.3, AMB, "BEFORE  75.3%  (box 24.7%)")
bar(40, 168, 360, 90.7, GRN, "AFTER   90.7%  (box 9.3%)")
P.append(t(40, 214, "= 3,736 more parts now render as a recognizable shape instead of a blank box.", 10.5, SUB, 400))

# the 9 new families
P.append(t(40, 252, "Added 9 geometry families (22 total; all verified to build valid meshes)", 12.5, TXT, 700))
fams = [("plate", "flat slab + bolt-holes", "markers · decals · labels · armor"),
        ("cover", "open panel / pan", "covers · doors · panels · guards"),
        ("pad", "cushion slab", "insulation · pads · straps"),
        ("link", "bar + two end eyes", "connecting links"),
        ("lever", "arm + pivot + grip", "levers · handles · cranks"),
        ("rivet", "shank + button head", "solid / blind rivets"),
        ("switch", "body + toggle + pins", "switches · relays"),
        ("cylinder", "body + rims + port", "motors · pumps · actuators · valves"),
        ("canister", "domed cylinder", "air cleaners · filters · tanks")]
cols = [ACC, TEAL, AMB, PUR, GRN, RED, ACC, TEAL, AMB]
x0, y0, cw, ch, gap = 40, 276, 360, 60, 12
for i, (nm, geo, ex) in enumerate(fams):
    cx = x0 + (i % 3) * (cw + gap); cy = y0 + (i // 3) * (ch + gap)
    P.append(box(cx, cy, cw, ch, PANEL, LINE, 10, 1))
    P.append('<rect x="%d" y="%d" width="5" height="%d" rx="2.5" fill="%s"/>' % (cx, cy, ch, cols[i]))
    P.append(t(cx + 16, cy + 21, nm, 12.5, cols[i], 700))
    P.append(t(cx + 16, cy + 38, geo, 9.5, TXT, 400))
    P.append(t(cx + 16, cy + 52, ex, 8.6, SUB, 400))

yb = 276 + 3 * (ch + gap) + 6
P.append(box(40, yb, 1100, 56, PANEL, GRN, 12, 1))
P.append(t(58, yb + 22, "Also fixed", 11.5, GRN, 700))
s, _ = wrap(58, yb + 40, "A real bug: CLAMP was read as a shaft because the pattern 'LAMP' had no word boundary (matched cLAMP). Bounded LAMP/BULB/CAP/STUD/COIL. Residual box is large assemblies (engine, van, frame) that carry the real manual figure anyway. partgeo.js ?v= bumped so browsers reload.", 208, 9.5, SUB, 12)
P.append(s)

P.append(t(40, H - 8, "Diagram. Dark (R3). v0.84.0 · 2026-06-04 · engine/ui/partgeo.js (family + 9 builders) · measured by ANALYZE-SHAPES.bat. Additive & rollbackable (R1).", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "92-shapes-pass")), "bytes")
