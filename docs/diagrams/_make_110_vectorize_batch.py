#!/usr/bin/env python3
"""v0.99.5 — Corpus-wide vectorization batch. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1120, 560
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "Corpus-wide vectorization batch   v0.99.5", 19, TXT, 700))
P.append(t(40, 70, "Pre-render every figure page to crisp SVG once, so the ⛭ Vector view opens instantly instead of vectorizing on demand.", 11.5, SUB, 400))
hr(86)

stages = [
 ("figure pages", GRN, ["parts.fig_no -> distinct", "(document_id, page) + path.", "read-only on the index."]),
 ("vectorize.ensure", AMB, ["render page (fitz) -> OpenCV", "potrace-style -> SVG. cached", "index/veccache/<doc>_<pg>_<dpi>.svg.", "skip if already cached (resumable)."]),
 ("coverage", GRN, ["index/vectorize_coverage.tsv:", "doc, page, svg_bytes, contours.", "parallel: cpu_count-1 (cap 10)."]),
]
x0, y0, cw, ch = 40, 118, 346, 116
for i, (ti, col, rows) in enumerate(stages):
    cx = x0 + i*(cw+6)
    P.append(box(cx, y0, cw, ch, PANEL, col, 11, 1))
    P.append(t(cx+16, y0+24, ti, 12, col, 700))
    yy = y0+46
    for r in rows: P.append(t(cx+16, yy, r, 9, SUB, 400)); yy += 15
    if i < 2: P.append('<text x="%d" y="%d" font-size="22" fill="%s">&#8594;</text>' % (cx+cw-2, y0+ch/2+7, SUB))
hr(250)

P.append(t(40, 278, "VERIFIED / NOTES", 13, GRN, 700))
P.append(box(40, 292, 1040, 96, PANEL, GRN, 12, 1))
ver = ["build_vectorize.py parses; reuses the proven 0.99.4 vectorizer (docs/vectorize_proof.png).",
       "BUILD-VECTORIZE.bat runs the full set (resumable, parallel); --limit for a quick slice.",
       "Same shape as build_schemgraph / make_cad (host batch, sidecar-only, R1/R6). Degrades cleanly without OpenCV.",
       "Deepens 0.99.4: on-demand vectorization -> corpus-wide precompute, so figures are instantly crisp."]
yy = 314
for v in ver:
    P.append('<circle cx="56" cy="%d" r="2.6" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(66, yy, v, 212, 9.4, SUB, 13); P.append(s); yy += 13*n + 4

P.append(t(40, H-10, "Markup. Dark (R3). v0.99.5 · 2026-07-01 · build_vectorize.py · index/veccache + vectorize_coverage.tsv · parallel/resumable. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "110-vectorize-batch")), "bytes")
