#!/usr/bin/env python3
"""PROPOSAL: 'Living Schematic' — the schematic equivalent of the CAD engine: animated signal/flow + breakdowns. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1240, 1280
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 50, "“Living Schematic” — a CAD-engine equivalent for schematics & diagrams  (proposal)", 20, TXT, 700))
P.append(t(40, 76, "Turn a flat scanned schematic into an interactive diagram with animated flow IN THE DIRECTION of the current/fluid, and click-through component breakdowns.", 11.5, SUB, 400))
hr(92)

# ---- the analogy ----
P.append(t(40, 120, "THE ANALOGY", 13, ACC, 700))
P.append(box(40, 132, 1160, 70, PANEL, ACC, 12, 1))
s, _ = wrap(58, 156, "CAD engine:  a PART  ->  classify shape  ->  build procedural geometry  ->  rendered image (tiered, cached).      "
    "Living Schematic:  a SCHEMATIC PAGE  ->  extract its vectors+labels  ->  infer the connectivity graph (netlist)  ->  ANIMATED, interactive diagram (tiered, cached).  "
    "Same idea: reconstruct structured meaning from the source, then render something richer than the flat scan.", 232, 10.5, TXT, 15)
P.append(s)
hr(214)

# ---- how it works: pipeline ----
P.append(t(40, 242, "HOW IT WORKS — the pipeline", 13, TEAL, 700))
stages = [
 ("1  VECTORIZE", GRN, ["already have it:", "schem_overlay.py / /api/schempaths", "-> lines, curves + text boxes", "(R1/R2/C1, net names, pin #s)"]),
 ("2  INFER GRAPH", AMB, ["NEW: snap line endpoints at", "junctions -> nodes/nets; attach", "labelled symbols to nodes", "-> a netlist (graph) sidecar"]),
 ("3  SIMULATE", GRN, ["already have it:", "Circuit Lab MNA solver", "(circuitsim.js) -> node V,", "branch currents + direction"]),
 ("4  ANIMATE", AMB, ["NEW: schemflow.js overlay —", "dashes/particles travel each", "wire in the CURRENT'S direction,", "speed ∝ |current|"]),
 ("5  BREAK DOWN", AMB, ["NEW: click a component ->", "its CAD image + part record", "(NSN/part#), connected nets,", "'trace this signal' walkthrough"]),
]
x0, y0, cw, ch = 40, 256, 226, 118
for i, (ti, col, rows) in enumerate(stages):
    cx = x0 + i*(cw+8)
    P.append(box(cx, y0, cw, ch, PANEL, LINE, 10, 1))
    P.append('<rect x="%d" y="%d" width="5" height="%d" rx="2.5" fill="%s"/>' % (cx, y0, ch, col))
    P.append(t(cx+16, y0+22, ti, 11, col, 700))
    yy = y0+42
    for r in rows: P.append(t(cx+16, yy, r, 8.5, SUB, 400)); yy += 15
P.append(t(40, 392, "green = building blocks that ALREADY EXIST · amber = the new pieces. Per-page graph cached like figcrop/cadcache (schemgraph.db sidecar, R1).", 9.5, "#7f8a99", 400))
hr(408)

# ---- the experience ----
P.append(t(40, 436, "THE EXPERIENCE (what the mechanic sees)", 13, AMB, 700))
exp = [
 ("Animated flow", ACC, "Current/signal — or hydraulic/pneumatic fluid — flows along the wires/lines in its real direction. Play / pause / speed. Colour = hot/active."),
 ("Trace-a-net", TEAL, "Click a wire or a net name: the whole net lights up and the animation isolates to just that path, end to end, across the page."),
 ("Component breakdown", GRN, "Click a symbol (R12, valve, relay): a panel shows its CAD image, NSN/part #, value/rating, the nets it touches, and where it appears in the TM."),
 ("Guided walkthrough", PUR, "Step the signal source -> load in order (like the onboarding tour, on the schematic) — the 'directions of the directions' as a narrated path."),
]
ex0, ey0, ecw, ech = 40, 450, 575, 92
for i, (ti, col, de) in enumerate(exp):
    cx = ex0 + (i % 2)*(ecw+10); cy = ey0 + (i//2)*(ech+10)
    P.append(box(cx, cy, ecw, ech, PANEL, col, 12, 1))
    P.append(t(cx+16, cy+26, ti, 12.5, col, 700))
    s, _ = wrap(cx+16, cy+48, de, 150, 9.6, SUB, 13); P.append(s)
hr(666)

# ---- RPS tiers ----
P.append(t(40, 694, "SCALES WITH THE BUILD (RPS), like CAD", 13, ACC, 700))
tiers = [("MODERN", GRN, "WebGL particle flow along traces + live re-simulation; smooth, many particles."),
         ("LITE", AMB, "Lightweight animated SVG dashes (stroke-dashoffset); the same direction + speed, cheaper."),
         ("LEGACY", RED, "No continuous animation: static highlight + a STEP button that advances the flow one hop at a time (RPS-safe, no rAF loop).")]
for i, (ti, col, de) in enumerate(tiers):
    cx = 40 + i*(386+6); cy = 708
    P.append(box(cx, cy, 386, 80, PANEL, col, 12, 1))
    P.append(t(cx+16, cy+24, ti, 12, col, 700))
    s, _ = wrap(cx+16, cy+44, de, 100, 9.4, SUB, 13); P.append(s)
hr(806)

# ---- pros / cons ----
P.append(t(40, 834, "PROS", 13, GRN, 700)); P.append(t(630, 834, "CONS / RISKS", 13, RED, 700))
pros = ["Reuses what's built: schempaths + Circuit Lab + CAD images + RPS + the part records.",
        "Turns a static scan into a teaching tool — flow + direction is how techs actually reason.",
        "Generalises beyond circuits: hydraulic/pneumatic/fuel/coolant diagrams animate the same way (fluid flow).",
        "Ties every symbol to its real part (NSN) and its CAD image — one unified object model.",
        "Offline, deterministic, cached per page; degrades gracefully on legacy."]
cons = ["Graph inference from a SCANNED schematic is the hard part — OCR noise, dense/overlapping lines, hand drawing.",
        "Needs a human-in-the-loop review/override for wrong junctions (an append-only fix queue, like the NIIN review).",
        "Simulation needs component VALUES; many TM schematics omit them — animate topology/direction even without a full solve.",
        "Animation cost on big pages; cap particle counts + tier it; cache the graph, not the frames.",
        "Not every 'schematic' is a graph (block diagrams, exploded views) — detect type, fall back to the highlighter."]
yy = 856
for pr in pros:
    P.append('<circle cx="52" cy="%d" r="2.6" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(62, yy, pr, 118, 9.6, SUB, 13); P.append(s); yy += 13*n + 7
yy = 856
for cn in cons:
    P.append('<circle cx="632" cy="%d" r="2.6" fill="%s"/>' % (yy-3, RED)); s, n = wrap(642, yy, cn, 118, 9.6, SUB, 13); P.append(s); yy += 13*n + 7

# ---- rollout ----
yb = 1116
P.append(box(40, yb, 1160, 96, PANEL, PUR, 12, 1))
P.append(t(58, yb+24, "Suggested rollout (each step shippable on its own)", 12, PUR, 700))
s, _ = wrap(58, yb+44, "1) schemgraph.py + BUILD-SCHEMGRAPH.bat: host batch infers the netlist per schematic page -> schemgraph.db sidecar (with a confidence score).   "
    "2) /api/schemgraph route serves it.   3) schemflow.js: the animated overlay (tiered).   4) Component breakdown panel reusing /api/part_record + /cadimg.   "
    "5) Review/override queue for bad junctions.   6) Wire it into Circuit Lab + the schematics viewer. Proof-of-concept first on ONE clean wiring page to prove the graph inference, then scale.", 232, 9.5, SUB, 13)
P.append(s)

P.append(t(40, H-10, "Proposal markup. Dark (R3). 2026-06-04 · builds on schem_overlay.py · /api/schempaths · circuitsim.js (MNA) · /api/part_record · /cadimg · RPS tiers.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "99-living-schematic")), "bytes")
