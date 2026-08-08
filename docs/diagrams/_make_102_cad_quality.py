#!/usr/bin/env python3
"""v0.93.0 — CAD quality pass (all tiers) + CAD-vs-3D differentiation. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1200, 820
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "Higher-quality CAD across all tiers + CAD vs 3-D, made distinct   v0.93.0", 19, TXT, 700))
P.append(t(40, 70, "The CAD renderer got a quality pass on every tier; the rotating CAD and the 3-D model now read as different things.", 11.5, SUB, 400))
hr(86)

# quality pass
P.append(t(40, 114, "THE QUALITY PASS — engine/cad_render.py (CAD_VERSION 4)", 13, TEAL, 700))
qs = [
 ("Anti-aliasing", GRN, ["Supersample 2× → 3×.", "Cleaner edges everywhere."]),
 ("Finer mesh", GRN, ["cyl 28→48 · tube 32→52 ·", "torus 30×16→48×26 · sphere", "16×12→28×20 · helix sv 8→12.", "Round parts look round."]),
 ("CAD ink-line", AMB, ["Crisp silhouette + hole", "outline from the part mask —", "the technical-drawing line."]),
 ("Depth + clean faces", AMB, ["Soft contact shadow under", "the part; facet edges = a", "subtle tint, not a black wire."]),
]
x0, y0, cw, ch = 40, 128, 280, 112
for i, (ti, col, rows) in enumerate(qs):
    cx = x0 + i*(cw+8)
    P.append(box(cx, y0, cw, ch, PANEL, LINE, 10, 1))
    P.append('<rect x="%d" y="%d" width="5" height="%d" rx="2.5" fill="%s"/>' % (cx, y0, ch, col))
    P.append(t(cx+16, y0+22, ti, 11.5, col, 700))
    yy = y0+42
    for r in rows: P.append(t(cx+16, yy, r, 8.6, SUB, 400)); yy += 15
P.append(t(40, 260, "Applies to ALL tiers, ladder preserved: v1 flat (legacy) · v2 +specular/metallic (lite) · v3 +FLIS colour/texture (modern). Proof: docs/cad_quality_v4.png.", 9.5, "#7f8a99", 400))
hr(276)

# the tier ladder
P.append(t(40, 304, "THE TIER LADDER (each now higher quality)", 13, ACC, 700))
tiers = [("LEGACY · v1", RED, "Flat diffuse, head-down, no colour/texture — but now SS3, rounder mesh, silhouette + shadow."),
         ("LITE · v2", AMB, "Everything in v1 + right-side-up + specular / metallic highlights."),
         ("MODERN · v3", GRN, "Everything in v2 + FLIS colour + per-material procedural surface texture.")]
for i, (ti, col, de) in enumerate(tiers):
    cx = 40 + i*(386+6); cy = 318
    P.append(box(cx, cy, 386, 84, PANEL, col, 12, 1))
    P.append(t(cx+16, cy+24, ti, 12, col, 700))
    s, _ = wrap(cx+16, cy+44, de, 100, 9.3, SUB, 13); P.append(s)
hr(418)

# CAD vs 3D
P.append(t(40, 446, "CAD vs 3-D — now visually DISTINCT (same smooth WebGL motion)", 13, AMB, 700))
P.append(box(40, 460, 560, 150, PANEL, TEAL, 12, 1))
P.append(t(58, 486, "\U0001F504  ROTATE CAD  (technical)", 12.5, TEAL, 700))
for k, ln in enumerate(["Flat-faceted, neutral machined STEEL, matte.", "GLV.load(geom, '#9aa6b2', false, [0.18,14,0.30]).",
                        "Cool blueprint-grey stage. Reads as a CAD model.", "Carries shape + FLIS dimensions, not the part colour."]):
    P.append(t(58, 512+k*18, "· "+ln, 9.6, SUB, 400))
P.append(box(620, 460, 540, 150, PANEL, GRN, 12, 1))
P.append(t(638, 486, "◳  INTERACTIVE 3-D  (realistic)", 12.5, GRN, 700))
for k, ln in enumerate(["The part's FLIS colour, smooth shading.", "The scanned MATERIAL finish (metallic/matte/rubber).",
                        "Looks like the real object's surface.", "Unchanged from before."]):
    P.append(t(638, 512+k*18, "· "+ln, 9.6, SUB, 400))
hr(632)

# verified
P.append(t(40, 660, "VERIFIED (host-side)", 13, GRN, 700))
P.append(box(40, 674, 1120, 92, PANEL, GRN, 12, 1))
ver = ["VERIFY-CAD-QUALITY.bat: cad_render.py parses, both UI pages' inline JS parse (exit 0).",
       "All-tiers quality grid renders to docs/cad_quality_v4.png — round parts round, crisp silhouettes, soft shadows.",
       "Re-render the full library with RUN-CAD-TIERS.bat (clears + re-renders v1/v2/v3) to push v4 quality everywhere.",
       "Additive & rollbackable (R1): revert the render edits + the cadspin GLV.load line + CAD_VERSION."]
yy = 696
for v in ver:
    P.append('<circle cx="56" cy="%d" r="2.6" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(66, yy, v, 232, 9.6, SUB, 13); P.append(s); yy += 13*n + 4

P.append(t(40, H-12, "Markup. Dark (R3). v0.93.0 · 2026-06-04 · cad_render.py SS3+mesh+silhouette+shadow · CAD_VERSION 4 · threed.html cadspin flat-steel · RUN-CAD-TIERS to refresh. R1.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "102-cad-quality")), "bytes")
