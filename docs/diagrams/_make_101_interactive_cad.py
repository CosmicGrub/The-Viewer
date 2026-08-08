#!/usr/bin/env python3
"""v0.92.0 — Interactive CAD: the CAD image rotates / zooms / scales like the 3-D model. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1200, 840
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "Interactive CAD — the CAD image now rotates, zooms & scales   v0.92.0", 19, TXT, 700))
P.append(t(40, 70, "Same renderer, now a turntable: grab the CAD image and spin it. It stays the real CAD render — shaded, coloured, textured, dimensioned.", 11.5, SUB, 400))
hr(86)

# pipeline
P.append(t(40, 114, "HOW IT WORKS", 13, TEAL, 700))
stages = [
 ("render(yaw=…)", GRN, ["EXISTING renderer + 3 new args:", "yaw = spin about vertical axis,", "pitch = tilt, title = drop the", "footer for clean frames. (R1)"]),
 ("render_spin / ensure_spin", AMB, ["render N viewpoints around 360°", "→ one TURNTABLE SPRITE SHEET,", "cached <nsn>_spin<n>_<style>.png.", "Tier frames: 12 / 16 / 24."]),
 ("/cadspin route", AMB, ["serves the sheet + X-CAD-Frames /", "X-CAD-FrameW headers. Mirrors", "/cadimg (nsn/chars/style/tier).", "cached in index/cadcache/."]),
 ("cadview.js", GRN, ["canvas + 1 PNG, NO WebGL, ES5.", "drag=rotate · scroll/pinch=zoom", "· pan when zoomed · auto-spin.", "its own 🔄 Rotate CAD tab."]),
]
x0, y0, cw, ch = 40, 128, 280, 118
for i, (ti, col, rows) in enumerate(stages):
    cx = x0 + i*(cw+8)
    P.append(box(cx, y0, cw, ch, PANEL, LINE, 10, 1))
    P.append('<rect x="%d" y="%d" width="5" height="%d" rx="2.5" fill="%s"/>' % (cx, y0, ch, col))
    P.append(t(cx+16, y0+22, ti, 11, col, 700))
    yy = y0+42
    for r in rows: P.append(t(cx+16, yy, r, 8.5, SUB, 400)); yy += 15
    if i < 3: P.append('<text x="%d" y="%d" font-size="20" fill="%s">&#8594;</text>' % (cx+cw-4, y0+ch/2+6, SUB))
P.append(t(40, 266, "green = built on what already existed · amber = the new pieces. BOTH stay: 🖼 CAD image (static, default) + 🔄 Rotate CAD (interactive) — separate tabs, like the 3-D / schematic viewers.", 9.5, "#7f8a99", 400))
hr(282)

# the controls
P.append(t(40, 310, "WHAT THE MECHANIC CAN DO (same feel as the 3-D model)", 13, AMB, 700))
exp = [
 ("Rotate", ACC, "Drag left/right to spin the part through a full turn — see the back, the far side, how it seats."),
 ("Zoom / scale", TEAL, "Scroll or pinch to zoom into a feature; drag to pan when zoomed. Reset (⌂) returns to the framed view."),
 ("Auto-rotate", GRN, "⟳ toggles a slow continuous spin — hands-free presentation while you read the procedure."),
 ("Still the CAD", PUR, "Every frame is the real CAD render: material colour + texture, facet shading, and the H/L dimension callouts."),
]
ex0, ey0, ecw, ech = 40, 324, 575, 84
for i, (ti, col, de) in enumerate(exp):
    cx = ex0 + (i % 2)*(ecw+10); cy = ey0 + (i//2)*(ech+10)
    P.append(box(cx, cy, ecw, ech, PANEL, col, 12, 1))
    P.append(t(cx+16, cy+25, ti, 12.5, col, 700))
    s, _ = wrap(cx+16, cy+46, de, 150, 9.5, SUB, 13); P.append(s)
hr(508)

# tiers
P.append(t(40, 536, "SCALES WITH THE BUILD (RPS) — GPU-FREE ON EVERY TIER", 13, ACC, 700))
tiers = [("MODERN", GRN, "24 frames (v3, textured + colour) — smoothest spin."),
         ("LITE", AMB, "16 frames (v2, specular/metallic) — lighter sheet."),
         ("LEGACY", RED, "12 frames (v1, flat) — same drag/zoom, no WebGL, runs on Win7/Vista.")]
for i, (ti, col, de) in enumerate(tiers):
    cx = 40 + i*(386+6); cy = 550
    P.append(box(cx, cy, 386, 78, PANEL, col, 12, 1))
    P.append(t(cx+16, cy+24, ti, 12, col, 700))
    s, _ = wrap(cx+16, cy+44, de, 100, 9.4, SUB, 13); P.append(s)
hr(644)

# verification
P.append(t(40, 672, "VERIFIED (host-side)", 13, GRN, 700))
P.append(box(40, 686, 1120, 96, PANEL, GRN, 12, 1))
ver = ["VERIFY-CADSPIN.bat → verify_cadspin.py rendered turntables for a bearing, a bolt and a gear.",
       "Proof montage docs/cadspin_proof.png shows the hex head, gear teeth and bore VISIBLY rotating frame-to-frame.",
       "Shading + the H/L dimension callouts are preserved on every frame — it's still a CAD drawing, just rotatable.",
       "cad_render.py + viewer_app.py parse host-side; cadview.js passes node --check. Additive & rollbackable (R1)."]
yy = 708
for v in ver:
    P.append('<circle cx="56" cy="%d" r="2.6" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(66, yy, v, 232, 9.6, SUB, 13); P.append(s); yy += 13*n + 4

P.append(t(40, H-12, "Markup. Dark (R3). v0.92.0 · 2026-06-04 · cad_render.render_spin/ensure_spin · /cadspin · cadview.js · threed.html CAD tab · cadcache. Complements the WebGL 3-D tab. R1.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "101-interactive-cad")), "bytes")
