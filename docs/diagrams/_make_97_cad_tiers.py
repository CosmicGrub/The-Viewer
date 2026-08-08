#!/usr/bin/env python3
"""v0.89.0 — CAD detail level scales with the program build / RPS tier. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 560
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
P.append(t(40, 46, "CAD detail level = the program build (RPS tier)  (v0.89.0)", 19, TXT, 700))
P.append(t(40, 70, "The auto-CAD engine renders the look each build can afford: richer on capable hardware, lightweight (and numpy-free) on legacy.", 11, SUB, 400))
P.append('<line x1="40" y1="86" x2="%d" y2="86" stroke="%s"/>' % (W - 40, LINE))

tiers = [
 ("LEGACY build", RED, "→ v1", ["flat diffuse shading", "head-down (original projection)", "no colour parse, NO TEXTURE",
   "no numpy / no GPU needed", "runs on Win 7 / Vista, low-RAM"]),
 ("LITE build", AMB, "→ v2", ["right-side-up orientation", "Blinn-Phong specular + metallic", "no surface texture (lighter)",
   "good on mid machines", "numpy optional"]),
 ("MODERN build", GRN, "→ v3", ["+ FLIS colour (olive drab, CARC…)", "+ per-material surface texture", "(brushed / grain / rubber / paint)",
   "the full 'product render'", "the default"]),
]
x0, y0, cw, ch = 40, 110, 360, 210
for i, (ti, col, vv, rows) in enumerate(tiers):
    cx = x0 + i*(cw+10)
    P.append(box(cx, y0, cw, ch, PANEL, col, 12, 1))
    P.append(t(cx+18, y0+30, ti, 14, col, 700))
    P.append(t(cx+cw-70, y0+30, vv, 16, col, 700))
    yy = y0+58
    for r in rows:
        P.append('<circle cx="%d" cy="%d" r="2.6" fill="%s"/>' % (cx+22, yy-3, col))
        P.append(t(cx+32, yy, r, 10, SUB, 400)); yy += 23
    P.append(box(cx+16, y0+ch-34, cw-32, 24, P2, col, 6, 1))
    P.append(t(cx+26, y0+ch-18, "cache: <nsn>_%s.png  (per-tier, separate)" % vv.split()[-1], 9, col, 700))

# the resolver
yb = 344
P.append(box(40, yb, 1100, 70, PANEL, ACC, 12, 1))
P.append(t(58, yb+24, "How /cadimg picks the level", 12, ACC, 700))
s, _ = wrap(58, yb+44, "Explicit ?style=v1|v2|v3 wins; else ?tier=modern|lite|legacy; else the server's own RPS_MODE (set from the machine profile at startup). cad_render.TIER_STYLE maps tier→style. Response carries X-CAD-Style. So a build serves — and only renders/ships — the detail it can afford; nothing wasted.", 210, 9.5, SUB, 13)
P.append(s)

yc = yb + 86
P.append(box(40, yc, 1100, 54, PANEL, PUR, 12, 1))
P.append(t(58, yc+22, "Populate a tier", 11.5, PUR, 700))
s, _ = wrap(58, yc+40, "MAKE-CAD.bat (or make_cad.py --style v1|v2|v3) pre-renders a chosen tier into the per-tier cache; the legacy build renders v1 on-demand with zero extra dependencies. Backwards-compatible: default stays v3 (R1).", 205, 9.5, SUB, 12)
P.append(s)

P.append(t(40, H-8, "Diagram. Dark (R3). v0.89.0 · 2026-06-04 · cad_render.TIER_STYLE + ensure(style=) · /cadimg ?style/?tier/RPS_MODE · make_cad --style. R1.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "97-cad-tiers")), "bytes")
