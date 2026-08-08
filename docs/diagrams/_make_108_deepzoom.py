#!/usr/bin/env python3
"""v0.99.3 — Offline deep-zoom + callout hotspots. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 720
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "Offline deep-zoom + callout hotspots   v0.99.3", 19, TXT, 700))
P.append(t(40, 70, "Zoom deep into any TM page or schematic — crisp at every level, no internet, no CDN — and click the OCR callouts to jump to the part.", 11.5, SUB, 400))
hr(86)

P.append(t(40, 114, "HOW IT WORKS", 13, TEAL, 700))
stages = [
 ("canvas viewer", GRN, ["deepzoom.js: a <canvas> draws", "the page; drag-pan, wheel-zoom,", "pinch, dbl-click fit. Same proven", "pattern as cadview.js."]),
 ("progressive DPI", AMB, ["as you zoom in, it re-requests", "/page?dpi=N at 150→300→600→1000", "so pixels stay CRISP — tiles", "generated on demand, offline."]),
 ("callout hotspots", TEAL, ["/api/callouts -> numbered markers", "at each NSN/PN/FIG box; click a", "number to jump to the part", "(/dossier, /partdiff). ⌖ toggles."]),
 ("entry points", PUR, ["/deepzoom?doc=ID&page=N page", "(page nav + doc title) +", "🔎 Deep Zoom button on the", "schematics viewer toolbar."]),
]
x0, y0, cw, ch = 40, 128, 272, 120
for i, (ti, col, rows) in enumerate(stages):
    cx = x0 + i*(cw+8)
    P.append(box(cx, y0, cw, ch, PANEL, LINE, 10, 1))
    P.append('<rect x="%d" y="%d" width="5" height="%d" rx="2.5" fill="%s"/>' % (cx, y0, ch, col))
    P.append(t(cx+16, y0+22, ti, 11, col, 700))
    yy = y0+42
    for r in rows: P.append(t(cx+16, yy, r, 8.6, SUB, 400)); yy += 15
    if i < 3: P.append('<text x="%d" y="%d" font-size="20" fill="%s">&#8594;</text>' % (cx+cw-4, y0+ch/2+6, SUB))
hr(264)

P.append(t(40, 292, "WHY OFFLINE-NATIVE", 13, ACC, 700))
exp = [
 ("No CDN / no tiles on disk", ACC, "OpenSeadragon needs pre-generated tile pyramids; here the server renders the exact DPI you need, when you need it. Nothing to pre-bake, nothing to sync."),
 ("Crisp, not blurry", TEAL, "Zooming past a threshold swaps in a higher-DPI render instead of upscaling — so a dense parts diagram stays legible at deep zoom."),
 ("Callouts are already there", GRN, "The OCR callout boxes (NSN/PN/FIG) that the page already computes become clickable hotspots — read the figure, tap a number, land on the part."),
 ("Every tier", PUR, "Plain canvas + <img>, ES5-safe — works on legacy too (just a lower DPI ceiling). No WebGL required."),
]
ex0, ey0, ecw, ech = 40, 306, 550, 90
for i, (ti, col, de) in enumerate(exp):
    cx = ex0 + (i % 2)*(ecw+10); cy = ey0 + (i//2)*(ech+10)
    P.append(box(cx, cy, ecw, ech, PANEL, col, 12, 1))
    P.append(t(cx+16, cy+24, ti, 11.5, col, 700))
    s, _ = wrap(cx+16, cy+44, de, 150, 9.4, SUB, 13); P.append(s)
hr(506)

P.append(t(40, 534, "STATUS", 13, GRN, 700))
P.append(box(40, 548, 1100, 92, PANEL, GRN, 12, 1))
ver = ["deepzoom.js + deepzoom.html inline JS pass node --check; deepzoom.html added to verify_ui.py.",
       "Route table + schematics 🔎 button pending the host suite -> run VERIFY-099.bat.",
       "DEFERRED (documented): line-art vectorization (raster->vector) — a separate heavy task; schem_overlay already extracts existing PDF vectors.",
       "Additive & rollbackable (R1): 2 new UI files + 2 route lines + 1 toolbar button. This closes the 4th 'all of the above' thread."]
yy = 570
for v in ver:
    P.append('<circle cx="56" cy="%d" r="2.6" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(66, yy, v, 224, 9.4, SUB, 13); P.append(s); yy += 13*n + 4

P.append(t(40, H-10, "Markup. Dark (R3). v0.99.3 · 2026-07-01 · deepzoom.js · /deepzoom · /api/callouts hotspots · progressive /page?dpi. Offline, ES5. R1.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "108-deepzoom")), "bytes")
