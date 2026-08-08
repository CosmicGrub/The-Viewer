#!/usr/bin/env python3
"""v0.85.0 — streamlined image search: number -> results -> figure/3-D/pages + loupe + page highlight. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 600
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
P.append(t(40, 46, "Streamlined image search  (v0.85.0)", 19, TXT, 700))
P.append(t(40, 70, "Navigate to a TM page -> click an NIIN/NSN/part# -> pick the matching result -> see figure / schematic / 3-D, in a side drawer.", 11, SUB, 400))
P.append('<line x1="40" y1="86" x2="%d" y2="86" stroke="%s"/>' % (W - 40, LINE))

P.append(panel(40, 110, 250, 120, "1", "TM page + Callouts", ACC,
    ["open a part's manual page", "toggle the callout markers", "NSN / part# / figure are clickable"],
    "/api/callouts (OCR text layer)"))
P.append('<text x="306" y="174" font-size="22" fill="%s">&#8594;</text>' % SUB)
P.append(panel(322, 110, 250, 120, "2", "click a number", AMB,
    ["highlights it ON the page", "opens the side drawer", "fetches matching results"],
    "part_record / part_by_number"))
P.append('<text x="588" y="174" font-size="22" fill="%s">&#8594;</text>' % SUB)
P.append(panel(604, 110, 250, 120, "3", "pick a result", TEAL,
    ["one row per catalogued match", "name + NSN + part#", "click to load its assets"],
    "the respective match"))
P.append('<text x="870" y="174" font-size="22" fill="%s">&#8594;</text>' % SUB)
P.append(panel(886, 110, 254, 120, "4", "assets, in place", GRN,
    ["figure crop (+ loupe magnifier)", "live 3-D model (orbit/zoom)", "pages/schematics that hold it"],
    "no leaving the page"))

# the assets row
yb = 256
P.append(box(40, yb, 360, 104, PANEL, ACC, 12, 1))
P.append(t(58, yb + 22, "📄 Figure + 🔎 Loupe", 12, ACC, 700))
s, _ = wrap(58, yb + 42, "The cited figure crop, with the reusable magnifier lens (loupe.js) on it — also wired onto the schematics viewer. Hover to magnify, scroll to zoom. Works on any image (barring 3-D).", 100, 9.5, SUB, 13)
P.append(s)
P.append(box(420, yb, 360, 104, PANEL, TEAL, 12, 1))
P.append(t(438, yb + 22, "🧊 Live 3-D (partview.js)", 12, TEAL, 700))
s, _ = wrap(438, yb + 42, "The detailed parametric model embedded in the drawer — PartGeo + GL3D (WebGL), SVG fallback on legacy. Same shape engine as the 3-D library.", 100, 9.5, SUB, 13)
P.append(s)
P.append(box(800, yb, 340, 104, PANEL, AMB, 12, 1))
P.append(t(818, yb + 22, "📃 Pages that hold it", 12, AMB, 700))
s, _ = wrap(818, yb + 42, "Schematics + manual pages referencing the part (threed_refs). Click one -> the viewer jumps there AND highlights the matching callout on that page.", 94, 9.5, SUB, 13)
P.append(s)

yc = yb + 122
P.append(box(40, yc, 1100, 52, PANEL, PUR, 12, 1))
P.append(t(58, yc + 21, "Page highlighting (both ends)", 11.5, PUR, 700))
s, _ = wrap(58, yc + 39, "The searched number is boxed on the current page when you click it; the resulting part is boxed on the figure/schematic page when you open it — so you always see where the information lives.", 210, 9.5, SUB, 12)
P.append(s)

P.append(t(40, H - 8, "Diagram. Dark (R3). v0.85.0 · 2026-06-04 · index.html drawer + partview.js + loupe.js · /partview.js /loupe.js. Additive, legacy-safe (R1).", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "94-image-search")), "bytes")
