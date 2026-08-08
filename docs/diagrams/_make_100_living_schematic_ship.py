#!/usr/bin/env python3
"""v0.91.0 — "Living Schematic" SHIPPED (PoC): netlist inference + tiered animated flow overlay. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1200, 880
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "“Living Schematic” — SHIPPED (PoC)   v0.91.0", 19, TXT, 700))
P.append(t(40, 70, "A flat vector schematic → an inferred netlist → an interactive overlay whose wires animate in the direction of flow.", 11.5, SUB, 400))
hr(86)

# pipeline
P.append(t(40, 114, "THE PIPELINE (per page, cached)", 13, TEAL, 700))
stages = [
 ("schem_overlay.py", GRN, ["EXISTING. Pure read of the", "PDF vectors → lines / polylines /", "rects + text words, normalized", "0..1.  /api/schempaths"]),
 ("schemgraph.py", AMB, ["NEW. segments → snap endpoints", "to NODES → split T-junctions →", "union-find NETS → attach R/C/K", "labels → CONFIDENCE score"]),
 ("/api/schemgraph", AMB, ["NEW route. Serves the graph,", "cached to index/schemcache/", "<doc>_<page>.json.  &fresh=1", "rebuilds. R1 sidecar-only."]),
 ("schemflow.js", GRN, ["NEW overlay. Draws the graph", "over the page image; wires", "ANIMATE power→load; click a", "wire=isolate net; click part."]),
]
x0, y0, cw, ch = 40, 128, 280, 120
for i, (ti, col, rows) in enumerate(stages):
    cx = x0 + i*(cw+8)
    P.append(box(cx, y0, cw, ch, PANEL, LINE, 10, 1))
    P.append('<rect x="%d" y="%d" width="5" height="%d" rx="2.5" fill="%s"/>' % (cx, y0, ch, col))
    P.append(t(cx+16, y0+22, ti, 11.5, col, 700))
    yy = y0+42
    for r in rows: P.append(t(cx+16, yy, r, 8.6, SUB, 400)); yy += 15
    if i < 3: P.append('<text x="%d" y="%d" font-size="20" fill="%s">&#8594;</text>' % (cx+cw-4, y0+ch/2+6, SUB))
P.append(t(40, 268, "green = built on what already existed · amber = the new pieces.", 9.5, "#7f8a99", 400))
hr(282)

# tiers
P.append(t(40, 310, "THE OVERLAY SCALES WITH THE BUILD (RPS)", 13, ACC, 700))
tiers = [("MODERN", GRN, "requestAnimationFrame dash flow — smooth traveling dashes along every wire, in the current's direction."),
         ("LITE", AMB, "Browser-driven SMIL <animate> on stroke-dashoffset — same direction + speed, no JS loop."),
         ("LEGACY", RED, "No loop at all: static highlight + a ▸ STEP button that advances the flow one hop at a time.")]
for i, (ti, col, de) in enumerate(tiers):
    cx = 40 + i*(386+6); cy = 324
    P.append(box(cx, cy, 386, 84, PANEL, col, 12, 1))
    P.append(t(cx+16, cy+24, ti, 12, col, 700))
    s, _ = wrap(cx+16, cy+44, de, 100, 9.4, SUB, 13); P.append(s)
hr(424)

# interactions
P.append(t(40, 452, "WHAT THE MECHANIC DOES", 13, AMB, 700))
exp = [
 ("Watch the flow", ACC, "Wires animate power → load (direction inferred by BFS from power/ground labels). The page reads as a system, not a static picture."),
 ("Isolate a net", TEAL, "Click any wire: its whole net lights amber end-to-end, everything else dims. Click empty space to clear."),
 ("Break down a part", GRN, "Click a component marker (R12, K3…): a panel opens with the reference and a one-click ‘find every mention in this manual’."),
 ("Confidence read-out", PUR, "The toolbar shows nets · parts · confidence% so you know how much to trust the inference on this particular sheet."),
]
ex0, ey0, ecw, ech = 40, 466, 575, 86
for i, (ti, col, de) in enumerate(exp):
    cx = ex0 + (i % 2)*(ecw+10); cy = ey0 + (i//2)*(ech+10)
    P.append(box(cx, cy, ecw, ech, PANEL, col, 12, 1))
    P.append(t(cx+16, cy+25, ti, 12.5, col, 700))
    s, _ = wrap(cx+16, cy+46, de, 150, 9.5, SUB, 13); P.append(s)
hr(656)

# verification
P.append(t(40, 684, "VERIFIED ON THE REAL CORPUS", 13, GRN, 700))
P.append(box(40, 698, 1120, 92, PANEL, GRN, 12, 1))
ver = ["Self-test: a synthetic loop + a mid-wire tap collapses to ONE connected net — the T-junction split works.",
       "Engine Wiring Harness p1 → 77 components · 1,652 wire-segments · 65 nets · confidence 0.97. Many wiring pages score ≥0.94.",
       "Visual proof (docs/schemflow_proof.png): the inferred netlist traces the actual Caterpillar C7 engine schematic.",
       "Known PoC limit: CAD-exported sheets with OUTLINED label text yield wires/nets but no components — breakdown needs an OCR text layer."]
yy = 720
for v in ver:
    P.append('<circle cx="56" cy="%d" r="2.6" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(66, yy, v, 232, 9.6, SUB, 13); P.append(s); yy += 13*n + 4

P.append(t(40, H-12, "Markup. Dark (R3). v0.91.0 · 2026-06-04 · schemgraph.py · /api/schemgraph · schemflow.js · schematics.html ▶ Flow · builds on schem_overlay/circuitsim/cadimg. R1.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "100-living-schematic-shipped")), "bytes")
