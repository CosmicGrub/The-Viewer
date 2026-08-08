#!/usr/bin/env python3
"""v0.84.1/0.84.2 — full 3-D geometry wiring: classify (+NSN fallback) -> builder -> BOTH render paths. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 640
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
P.append(t(40, 46, "3-D geometry wiring — every shape resolves to a real mesh, in both views", 18, TXT, 700))
P.append(t(40, 70, "Audited host-side: 22 families, every classifier output + every NSN/FSC value has a builder, every builder makes a valid mesh.", 11, SUB, 400))
P.append('<line x1="40" y1="86" x2="%d" y2="86" stroke="%s"/>' % (W - 40, LINE))

# classify chain
P.append(panel(40, 110, 250, 132, "1", "classify(name,chars,nsn)", ACC,
    ["name -> family() (24 keywords)", "if box -> NSN Federal Supply Class", "FSC/FSG table -> shape"],
    "98.5% get a real family"))
P.append('<text x="306" y="178" font-size="22" fill="%s">&#8594;</text>' % SUB)
P.append(panel(322, 110, 250, 132, "2", "PartGeo.build(fam, dims)", TEAL,
    ["22 builders (bolt..canister)", "driven by FLIS L/W/H/dia/bore", "unknown -> f_box (safety net)"],
    "returns {V, F, smooth}"))
P.append('<text x="588" y="178" font-size="22" fill="%s">&#8594;</text>' % SUB)
P.append(panel(604, 110, 254, 132, "3", "one detailed mesh", AMB,
    ["hex-head bolt · races+balls bearing", "toothed gear · holed gasket · helix", "same mesh for every view"],
    "{V,F} shared, not re-derived"))

# the two views fed by the same mesh
P.append('<text x="731" y="262" font-size="20" fill="%s">&#8595;</text>' % SUB)
P.append(box(40, 274, 360, 96, PANEL, GRN, 12, 1))
P.append(t(58, 298, "Artist approximation (drawn SVG)", 12, GRN, 700))
s, _ = wrap(58, 318, "The grid card thumbnail AND the no-WebGL modal fallback render the SAME detailed mesh (renderSVG projects {V,F}, depth-shaded). Runs on legacy browsers.", 100, 9.5, SUB, 13)
P.append(s)
P.append(box(420, 274, 360, 96, PANEL, ACC, 12, 1))
P.append(t(438, 298, "Representative rendering (WebGL)", 12, ACC, 700))
s, _ = wrap(438, 318, "The opened modal renders the SAME mesh live in 3D (GL3D.load) — orbit + zoom — with the material uniform. Parameter panel rebuilds it live.", 100, 9.5, SUB, 13)
P.append(s)
P.append(box(800, 274, 340, 96, PANEL, PUR, 12, 1))
P.append(t(818, 298, "Layered on top", 12, PUR, 700))
s, _ = wrap(818, 318, "Colour/material from appearance() (FLIS scan). Real cited figure from /figcrop as the 'Manual illustration' tab. NSN cross-ref + refs.", 94, 9.5, SUB, 13)
P.append(s)

# audit result strip
yb = 392
P.append(box(40, yb, 1100, 92, PANEL, LINE, 12, 1))
P.append(t(58, yb + 24, "Wiring audit (host-side, authoritative)", 12, TXT, 700))
rows = ["name classifier  -> 22 distinct families ............ all 22 have a builder      OK",
        "NSN FSC + FSG    -> 95 mappings / 20 values ......... all are builders            OK",
        "22 builders      -> real f_* functions .............. all build a valid mesh       OK",
        "unknown family   -> f_box fallback .................. nothing renders empty         OK"]
yy = yb + 44
for r in rows:
    P.append(t(58, yy, r, 9.6, SUB, 400)); yy += 15

P.append(t(40, H - 8, "Diagram. Dark (R3). v0.84.1-0.84.2 · 2026-06-04 · engine/ui/partgeo.js (classify/build/22 families) + threed.html (buildModel/renderSVG/open3D). R1.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "93-geometry-wiring")), "bytes")
