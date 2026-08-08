#!/usr/bin/env python3
"""BUILT 0.68.0: 3D viewer detailed parametric geometry (partgeo.js) — recognisable part meshes from FLIS
dims, no more blocks. (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 520
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
P.append(t(40, 46, "BUILT — 3D viewer: detailed parametric models  (v0.68.0)", 19, TXT, 700))
P.append(t(40, 70, "The WebGL renderer was already glossy; the geometry was blocky. partgeo.js builds the real part shape from the measured dimensions + FLIS characteristics.", 11, SUB, 400))
P.append('<line x1="40" y1="86" x2="%d" y2="86" stroke="%s"/>' % (W - 40, LINE))
P.append(panel(40, 108, 360, 196, "\U0001F529", "Family-specific meshes", ACC,
  ["bolt = hex head + threaded shank · nut = chamfered hex + bore · washer/gasket = ring (gasket with bolt-holes).",
   "bearing = outer/inner races + a ring of balls · gear = teeth + bore · spring = helix.",
   "tube = hollow cylinder · o-ring/seal = torus · pin/shaft = chamfered ends · bracket = L + holes · battery = body + posts."],
  "12 families, classified from the item name."))
P.append(panel(412, 108, 360, 196, "\U0001F4D0", "Driven by real measurements", TEAL,
  ["Pulls overall length / width / height / diameter / bore from the FLIS characteristics already shown in the panel.",
   "So sizes and proportions match the catalogued part, not a generic block.",
   "Still honest: a representative parametric model (no CAD geometry exists in a TM), but it looks like the part."],
  "Proportions from the catalogue."))
P.append(panel(784, 108, 356, 196, "\U0001F5A5", "Both renderers, gallery stays fast", AMB,
  ["partgeo.js returns a plain {V,F} mesh used by BOTH the WebGL shader (smooth normals, glossy) and the SVG fallback (legacy).",
   "Gallery thumbnails keep the light primitive (fast grid); opening a part upgrades to the detailed mesh.",
   "Served at /partgeo.js. No new dependency, offline."],
  "Detail where it counts; speed in the grid."))
P.append(box(40, 320, 1100, 84, PANEL, GRN, 12, 1))
P.append(t(58, 342, "VERIFIED", 11.5, GRN, 700))
s, _ = wrap(58, 362, "partgeo.js node-validated: all 13 families produce finite, non-degenerate meshes (no NaN, valid indices) — bolt 399 verts (hex head + thread grooves), bearing 1342 (races + balls), spring 2120 (helix), gear with teeth. Family classifier 12/12 on real nomenclatures. threed.html wiring + the /partgeo.js route confirmed on host. The same {V,F} reaches the SVG legacy path, so legacy gets the detailed shapes too (flat-shaded).", 198, 9, SUB, 12)
P.append(s)
P.append(t(40, H - 8, "BUILT diagram. Dark (R3). v0.68.0 · 2026-06-03 · ui/partgeo.js · threed.html (buildModel/open3D) · /partgeo.js route. Additive (R1/R6).", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "82-partgeo-3d-built")), "bytes")
