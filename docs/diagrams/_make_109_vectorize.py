#!/usr/bin/env python3
"""v0.99.4 — Offline line-art vectorization (potrace-style, OpenCV). Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 700
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "Offline line-art vectorization   v0.99.4", 19, TXT, 700))
P.append(t(40, 70, "Turn a scanned figure/schematic into crisp SVG — razor-sharp at ANY deep-zoom, clean to reprint or recolour. No CDN, no external binary.", 11.5, SUB, 400))
hr(86)

P.append(t(40, 114, "THE PIPELINE (engine/vectorize.py)", 13, TEAL, 700))
stages = [
 ("render page", GRN, ["fitz renders the page to a", "raster at the requested DPI", "(reuses the page renderer)."]),
 ("binarize (Otsu)", AMB, ["cv2 threshold (Otsu, inverted)", "-> ink = foreground. No blur by", "default, so thin lines survive."]),
 ("trace contours", AMB, ["cv2.findContours(RETR_CCOMP) +", "approxPolyDP simplify. Keeps", "hatching, thin lines, text.", "min_area 1.5, simplify 0.9."]),
 ("emit SVG", GRN, ["one even-odd-filled <path>", "(holes handled) -> cached", "index/veccache/<doc>_<pg>.svg,", "served image/svg+xml."]),
]
x0, y0, cw, ch = 40, 128, 272, 116
for i, (ti, col, rows) in enumerate(stages):
    cx = x0 + i*(cw+8)
    P.append(box(cx, y0, cw, ch, PANEL, LINE, 10, 1))
    P.append('<rect x="%d" y="%d" width="5" height="%d" rx="2.5" fill="%s"/>' % (cx, y0, ch, col))
    P.append(t(cx+16, y0+22, ti, 11, col, 700))
    yy = y0+42
    for r in rows: P.append(t(cx+16, yy, r, 8.6, SUB, 400)); yy += 15
    if i < 3: P.append('<text x="%d" y="%d" font-size="20" fill="%s">&#8594;</text>' % (cx+cw-4, y0+ch/2+6, SUB))
hr(260)

P.append(t(40, 288, "WHY IT PAIRS WITH DEEP-ZOOM", 13, ACC, 700))
exp = [
 ("Infinitely crisp", ACC, "A raster blurs when you zoom past its DPI; an SVG is resolution-free — the browser renders the ⛭ Vectorize output razor-sharp at any zoom."),
 ("Offline, uses cv2 already present", TEAL, "OpenCV ships with the OCR stack, so no new dependency. Cached per page; if cv2 is missing the route returns a clean 503."),
 ("Reprint / recolour clean", GRN, "Vector line-art prints crisp and can be recoloured (it's a filled path) — useful for take-to-the-bay packets."),
 ("Keeps the fine detail", PUR, "Tuned so hatching, thin leader lines and callout text survive (no median-blur, low min-area)."),
]
ex0, ey0, ecw, ech = 40, 302, 550, 86
for i, (ti, col, de) in enumerate(exp):
    cx = ex0 + (i % 2)*(ecw+10); cy = ey0 + (i//2)*(ech+10)
    P.append(box(cx, cy, ecw, ech, PANEL, col, 12, 1))
    P.append(t(cx+16, cy+24, ti, 11.5, col, 700))
    s, _ = wrap(cx+16, cy+44, de, 150, 9.4, SUB, 13); P.append(s)
hr(486)

P.append(t(40, 514, "VERIFIED", 13, GRN, 700))
P.append(box(40, 528, 1100, 92, PANEL, GRN, 12, 1))
ver = ["Core logic run in-sandbox on synthetic line-art: 18 contours, faithful reproduction incl. hatching + text.",
       "Proof docs/vectorize_proof.png (raster -> vector, side by side). OpenCV 4.13 + numpy + Pillow.",
       "Route (/vectorize) + ⛭ button pending the host suite (VERIFY-099.bat) — the mount truncated the grown files.",
       "Additive & rollbackable (R1): one module + one route + one button; veccache sidecar only. Closes thread #4 fully."]
yy = 550
for v in ver:
    P.append('<circle cx="56" cy="%d" r="2.6" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(66, yy, v, 224, 9.4, SUB, 13); P.append(s); yy += 13*n + 4

P.append(t(40, H-10, "Markup. Dark (R3). v0.99.4 · 2026-07-01 · vectorize.py (cv2 potrace-style) · /vectorize · deepzoom ⛭ · index/veccache. Offline. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "109-vectorize")), "bytes")
