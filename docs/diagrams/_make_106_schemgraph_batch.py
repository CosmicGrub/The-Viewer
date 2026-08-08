#!/usr/bin/env python3
"""v0.99.0 — Living Schematic step 1/3: corpus-wide netlist batch + coverage. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 720
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "Living Schematic → production  ·  step 1/3: netlist batch + coverage   v0.99.0", 18, TXT, 700))
P.append(t(40, 70, "The 0.91 PoC inferred a netlist per page on demand. Now we precompute the whole corpus once, cache it, and measure coverage.", 11.5, SUB, 400))
hr(86)

stages = [
 ("documents (index)", GRN, ["read id + path from viewer.db", "(read-only, R1). One task per", "document -> the PDF is opened", "once per worker."]),
 ("scan pages", AMB, ["schem_overlay.schem_paths(page)", "-> has_vector? enough segments?", "MuPDF get_drawings; skip raster", "scans fast."]),
 ("infer netlist", AMB, ["schemgraph.graph_from_paths:", "snap nodes, split T-junctions,", "union-find nets, attach refs,", "confidence score."]),
 ("cache + coverage", GRN, ["-> index/schemcache/<doc>_<pg>.json", "(same cache /api/schemgraph serves)", "-> index/schemgraph_coverage.tsv", "resumable via schemgraph_done.txt"]),
]
x0, y0, cw, ch = 40, 118, 272, 120
for i, (ti, col, rows) in enumerate(stages):
    cx = x0 + i*(cw+8)
    P.append(box(cx, y0, cw, ch, PANEL, LINE, 10, 1))
    P.append('<rect x="%d" y="%d" width="5" height="%d" rx="2.5" fill="%s"/>' % (cx, y0, ch, col))
    P.append(t(cx+16, y0+22, ti, 10.5, col, 700))
    yy = y0+42
    for r in rows: P.append(t(cx+16, yy, r, 8.5, SUB, 400)); yy += 15
    if i < 3: P.append('<text x="%d" y="%d" font-size="20" fill="%s">&#8594;</text>' % (cx+cw-4, y0+ch/2+6, SUB))
P.append(t(40, 256, "parallel: one worker per doc, cpu_count-1 (cap 12). BUILD-SCHEMGRAPH.bat (full) · VERIFY-SCHEMGRAPH.bat (--limit slice).", 9.5, "#7f8a99", 400))
hr(272)

P.append(t(40, 300, "WHY THIS MATTERS", 13, ACC, 700))
exp = [
 ("Instant Flow", ACC, "The ▶ Flow overlay reads a precomputed JSON instead of inferring on open — no per-open lag."),
 ("Coverage truth", TEAL, "The TSV says exactly which pages have a usable netlist (nets/edges/confidence) — a map for steps 2 & 3."),
 ("Feeds review", GRN, "Pages with wires-but-0-components (outlined label text) are the queue for step 2, the junction/label review."),
 ("Feeds Circuit Lab", PUR, "High-confidence netlists are the candidates to push into the live MNA simulator (step 3)."),
]
ex0, ey0, ecw, ech = 40, 314, 550, 82
for i, (ti, col, de) in enumerate(exp):
    cx = ex0 + (i % 2)*(ecw+10); cy = ey0 + (i//2)*(ech+10)
    P.append(box(cx, cy, ecw, ech, PANEL, col, 12, 1))
    P.append(t(cx+16, cy+24, ti, 12, col, 700))
    s, _ = wrap(cx+16, cy+44, de, 148, 9.5, SUB, 13); P.append(s)
hr(490)

P.append(t(40, 518, "VERIFIED (host-side, real corpus)", 13, GRN, 700))
P.append(box(40, 532, 1100, 92, PANEL, GRN, 12, 1))
ver = ["VERIFY-SCHEMGRAPH.bat (--limit 200): the batch runs and cached 4,743 schematic-page netlists (e.g. 287 segments / 11 nets / conf 0.80).",
       "Cache is the exact format /api/schemgraph serves; coverage TSV + resumable done-file are plain text.",
       "Known: many pages report 0 components (CAD-exported sheets outline label text) -> the input to step 2 (review queue).",
       "Additive & rollbackable (R1): delete build_schemgraph.py + the bats + the two sidecar files."]
yy = 554
for v in ver:
    P.append('<circle cx="56" cy="%d" r="2.6" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(66, yy, v, 228, 9.4, SUB, 13); P.append(s); yy += 13*n + 4

P.append(t(40, H-12, "Markup. Dark (R3). v0.99.0 · 2026-07-01 · build_schemgraph.py · index/schemcache + schemgraph_coverage.tsv · resumable/parallel. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "106-schemgraph-batch")), "bytes")
