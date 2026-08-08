#!/usr/bin/env python3
"""v0.86.0 — CAD images for the whole representative 3-D library. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 600
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
P.append(t(40, 46, "CAD images for the representative 3-D library  (v0.86.0)", 19, TXT, 700))
P.append(t(40, 70, "Every part rendered to a shaded isometric CAD image — scaled to its FLIS dimensions — cached as a sidecar, served on demand.", 11, SUB, 400))
P.append('<line x1="40" y1="86" x2="%d" y2="86" stroke="%s"/>' % (W - 40, LINE))

P.append(panel(40, 110, 250, 132, "1", "classify + build (Python)", ACC,
    ["cad_render.py mirrors partgeo.js", "22 families + NSN/FSC fallback", "scaled to FLIS L/W/H/dia"],
    "same shapes as the WebGL"))
P.append('<text x="306" y="178" font-size="22" fill="%s">&#8594;</text>' % SUB)
P.append(panel(322, 110, 250, 132, "2", "render (Pillow)", TEAL,
    ["shaded iso + edge lines", "dimension callouts (in.)", "title block: NSN/name/shape"],
    "no GPU, no heavy deps"))
P.append('<text x="588" y="178" font-size="22" fill="%s">&#8594;</text>' % SUB)
P.append(panel(604, 110, 250, 132, "3", "cache (sidecar)", AMB,
    ["index/cadcache/<nsn>.png", "never touches the index (R1)", "render-once, then instant"],
    "resumable batch or on-demand"))
P.append('<text x="870" y="178" font-size="22" fill="%s">&#8594;</text>' % SUB)
P.append(panel(886, 110, 254, 132, "4", "serve + show", GRN,
    ["/cadimg?nsn= (figcrop pattern)", "3-D library thumbnails", "SVG/WebGL stay as fallback/live"],
    "the whole ~20,869 set"))

yb = 268
P.append(box(40, yb, 545, 96, PANEL, ACC, 12, 1))
P.append(t(58, yb + 24, "Two ways to populate", 12, ACC, 700))
s, _ = wrap(58, yb + 44, "MAKE-CAD.bat pre-renders the whole representative set (ref_nsn with FLIS dims + figure-bearing parts) with progress + ETA, resumable. Or skip it: /cadimg renders each part the first time it is viewed and caches it.", 92, 9.5, SUB, 13)
P.append(s)
P.append(box(596, yb, 544, 96, PANEL, PUR, 12, 1))
P.append(t(614, yb + 24, "What a CAD image shows", 12, PUR, 700))
s, _ = wrap(614, yb + 44, "A clean three-quarter shaded view of the part's shape, the overall bounding dimensions called out in inches, and a title block with the NSN, nomenclature and shape family. Labeled REPRESENTATIVE — not a manufacturing drawing.", 98, 9.5, SUB, 13)
P.append(s)

yc = yb + 112
P.append(box(40, yc, 1100, 52, PANEL, GRN, 12, 1))
P.append(t(58, yc + 21, "Verified", 11.5, GRN, 700))
s, _ = wrap(58, yc + 39, "Sample families rendered in isolation (bolt/gear/bearing/canister/bracket/switch) and end-to-end through the live server (/cadimg?nsn= -> valid PNG). Additive + legacy-safe: static PNGs need no WebGL, a real win for old machines.", 210, 9.5, SUB, 12)
P.append(s)

P.append(t(40, H - 8, "Diagram. Dark (R3). v0.86.0 · 2026-06-04 · engine/cad_render.py + /cadimg route + make_cad.py/MAKE-CAD.bat · index/cadcache sidecar. R1.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "95-cad-images")), "bytes")
