#!/usr/bin/env python3
"""DETAILED visual of the CAD function: what it does, how it works, and a roadmap to improve it. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1240, 1240
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

# ---- header ----
P.append(t(40, 50, "THE auto-CAD function — what it does, how it works, how to make it better", 21, TXT, 700))
P.append(t(40, 76, "Turns every catalogued part into a shaded, dimensioned CAD image from its name + NSN + FLIS dimensions. Offline, pure Python + Pillow.", 12, SUB, 400))
hr(92)

# ---- WHAT IT DOES ----
P.append(t(40, 120, "WHAT IT DOES", 14, ACC, 700))
P.append(box(40, 132, 1160, 78, PANEL, ACC, 12, 1))
s, _ = wrap(58, 156, "Most of the 20,869 representative parts have no manufacturer CAD model and often no manual figure — just a name and FLIS dimensions. "
    "The auto-CAD function manufactures a recognizable engineering picture for each one: it infers the part's shape, scales it to the real dimensions, "
    "and renders a clean three-quarter CAD view with dimension callouts and a title block. The result looks like a drafting-room approximation and is "
    "labeled as such — a fast visual identity for a part that otherwise had none.", 235, 11, TXT, 15)
P.append(s)
hr(228)

# ---- HOW IT WORKS ----
P.append(t(40, 256, "HOW IT WORKS  ·  the pipeline (engine/cad_render.py)", 14, TEAL, 700))
stages = [
 ("1  CLASSIFY", ACC, ["name -> family() (24 keyword rules)", "if unknown -> NSN Federal Supply Class", "22 shape families (bolt..canister)"]),
 ("2  DIMENSION", TEAL, ["parse FLIS characteristics text", "DIAMETER/LENGTH/WIDTH/HEIGHT/THK", "-> L, W, H, dia, bore (inches)"]),
 ("3  BUILD MESH", AMB, ["family builder -> {V, F}", "primitives: cyl/prism/tube/torus/", "sphere/helix/gear/box, scaled"]),
 ("4  PROJECT", PUR, ["rotate (three-quarter iso)", "orthographic to 2-D", "fit + centre to canvas"]),
 ("5  SHADE", GRN, ["painter's sort by depth", "per-face normal . light", "facet colour = material x brightness"]),
 ("6  ANNOTATE", ACC, ["overall-dimension callouts (in.)", "title block: NSN / name / shape", "drafting grid + 'REPRESENTATIVE'"]),
 ("7  OUTPUT", TEAL, ["2x supersample -> LANCZOS down", "PNG to index/cadcache/ sidecar", "cache key = nsn + CAD_VERSION"]),
 ("8  SERVE", AMB, ["/cadimg?nsn= render-on-demand", "MAKE-CAD.bat pre-renders all", "shown as the 3-D card thumbnail"]),
]
x0, y0, cw, ch = 40, 270, 282, 112
for i, (ti, col, rows) in enumerate(stages):
    cx = x0 + (i % 4) * (cw + 8); cy = y0 + (i // 4) * (ch + 10)
    P.append(box(cx, cy, cw, ch, PANEL, LINE, 10, 1))
    P.append('<rect x="%d" y="%d" width="5" height="%d" rx="2.5" fill="%s"/>' % (cx, cy, ch, col))
    P.append(t(cx + 16, cy + 22, ti, 12, col, 700))
    yy = cy + 42
    for r in rows:
        P.append('<circle cx="%d" cy="%d" r="2.4" fill="%s"/>' % (cx + 19, yy - 3, col))
        P.append(t(cx + 28, yy, r, 8.9, SUB, 400)); yy += 16
# flow arrows between the two rows handled implicitly; add a small note
P.append(t(40, 270 + 2*ch + 30, "Faithful to partgeo.js: the same 22 families + the same NSN/FSC fallback, so the CAD image always matches the live WebGL model and the card tag.", 10, "#7f8a99", 400))
hr(520)

# ---- ANATOMY OF A CAD IMAGE ----
P.append(t(40, 548, "ANATOMY OF A CAD IMAGE", 14, AMB, 700))
ax, ay, aw, ah = 40, 562, 560, 360
P.append(box(ax, ay, aw, ah, "#f1f4f7", "#c7d0d8", 10, 1))
# faint grid
for gx in range(ax+20, ax+aw, 26): P.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#e0e6ea"/>' % (gx, ay, gx, ay+ah-66))
for gy in range(ay+20, ay+ah-66, 26): P.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#e0e6ea"/>' % (ax, gy, ax+aw, gy))
# a little shaded iso block (hex-ish prism) to stand in for the part
cxp, cyp = ax+250, ay+150
P.append('<polygon points="%d,%d %d,%d %d,%d %d,%d" fill="#5a6573"/>' % (cxp-70,cyp-30, cxp+70,cyp-30, cxp+90,cyp+10, cxp-50,cyp+10))   # top
P.append('<polygon points="%d,%d %d,%d %d,%d %d,%d" fill="#3a434f"/>' % (cxp-70,cyp-30, cxp-50,cyp+10, cxp-50,cyp+120, cxp-70,cyp+80))   # left
P.append('<polygon points="%d,%d %d,%d %d,%d %d,%d" fill="#2b333d"/>' % (cxp+70,cyp-30, cxp+90,cyp+10, cxp+90,cyp+120, cxp+70,cyp+80))   # right
P.append('<polygon points="%d,%d %d,%d %d,%d %d,%d" fill="#323b46"/>' % (cxp-50,cyp+10, cxp+90,cyp+10, cxp+90,cyp+120, cxp-50,cyp+120)) # front
# dimension line (right)
P.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#2864aa" stroke-width="2"/>' % (ax+aw-40, ay+30, ax+aw-40, ay+ah-96))
P.append(t(ax+aw-34, ay+170, "H 2.0\"", 11, "#2864aa", 700))
# title block
P.append(box(ax, ay+ah-58, aw, 58, "#1c2430", "#2864aa", 0, 1))
P.append(t(ax+14, ay+ah-36, "NUT, HEX   ·   NSN 5310-...   ·   shape: nut", 10.5, "#e6e9ee", 700))
P.append(t(ax+14, ay+ah-18, "REPRESENTATIVE CAD APPROXIMATION — scaled to FLIS dims", 9, "#9aa6b6", 400))
# leader labels on the right column
lx = ax + aw + 26
labels = [("Shaded facets", "per-face flat shading from a key light", GRN, ay+40),
          ("Edge lines", "every face outlined — the 'CAD wireframe' read", AMB, ay+96),
          ("Dimension callout", "the overall size in inches, from FLIS", ACC, ay+152),
          ("Drafting grid", "faint background = engineering-paper feel", TEAL, ay+208),
          ("Title block", "NSN · name · shape family · disclaimer", PUR, ay+264)]
for nm, de, col, yy in labels:
    P.append('<circle cx="%d" cy="%d" r="4" fill="%s"/>' % (lx, yy-4, col))
    P.append(t(lx+14, yy, nm, 11.5, TXT, 700))
    P.append(t(lx+14, yy+15, de, 9, SUB, 400))
hr(940)

# ---- ROADMAP ----
P.append(t(40, 968, "BETTER & MORE — ways to grow this feature", 14, GRN, 700))
cols = [
 ("Higher fidelity", ACC, ["smooth (vertex-normal) shading for round parts",
   "port the WebGL specular/metallic look to Pillow", "soft shadow + ground plane for depth",
   "per-family canonical orientation (bolt head up, …)"]),
 ("More accuracy", TEAL, ["parse thread pitch, head/drive type, # holes",
   "sub-type builders (hex vs socket screw; ball vs roller)", "fit dims from RPSTL/figure when FLIS is silent",
   "'low-confidence' badge when dimensions are defaulted"]),
 ("Real CAD output", AMB, ["export STL / OBJ per part (3-D print / CAD)",
   "glTF/GLB for web + AR viewing", "true multi-view drawing sheet (front/top/side + iso)",
   "full dimensioning + tolerances on the sheet"]),
 ("UX + scale", PUR, ["CAD tab + download button in the part modal",
   "loupe on the CAD image; print into the job packet", "'report wrong shape' override -> append-only feedback",
   "multiprocess the 20,869 batch; pre-warm on idle"]),
]
cx0 = 40; cwd = 287
for i, (ti, col, rows) in enumerate(cols):
    cx = cx0 + i*(cwd+5); cy = 982
    P.append(box(cx, cy, cwd, 210, PANEL, LINE, 10, 1))
    P.append('<rect x="%d" y="%d" width="5" height="210" rx="2.5" fill="%s"/>' % (cx, cy, col))
    P.append(t(cx+16, cy+24, ti, 12.5, col, 700))
    yy = cy + 48
    for r in rows:
        P.append('<circle cx="%d" cy="%d" r="2.6" fill="%s"/>' % (cx+19, yy-3, col))
        sline, n = wrap(cx+28, yy, r, 44, 9.2, SUB, 13)
        P.append(sline); yy += 13*n + 8

P.append(t(40, H-12, "Detailed reference. Dark (R3). v0.86.0 · 2026-06-04 · engine/cad_render.py · /cadimg · make_cad.py / MAKE-CAD.bat · index/cadcache. Representative — not a manufacturing drawing.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "96-cad-detailed")), "bytes")
