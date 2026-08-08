#!/usr/bin/env python3
"""v0.94.0 — Wire local 3-D models (OBJ/STL) into the viewer, replacing the placeholder. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1200, 760
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "Local 3-D models — drop your CAD, replace the placeholder   v0.94.0", 19, TXT, 700))
P.append(t(40, 70, "If you have a real model file for a part, the 3-D tab loads IT instead of the representative geometry. Authoritative, not an approximation.", 11.5, SUB, 400))
hr(86)

# pipeline
P.append(t(40, 114, "HOW IT WORKS", 13, TEAL, 700))
stages = [
 ("1  DROP A FILE", GRN, ["index/models3d/<NSN>.obj", "                    or .stl", "named by the part's NSN.", "sidecar — never the index (R1)."]),
 ("2  localmodel.py", AMB, ["find() the file → parse to {V,F}.", "OBJ (n-gon→tris) · ASCII STL ·", "BINARY STL (struct). pure stdlib.", "faces capped 300k."]),
 ("3  /api/localmodel(_mesh)", AMB, ["status: exists / fmt / url.", "mesh: {V,F,local:true} JSON.", "404 JSON when none (no 5xx).", ""]),
 ("4  gl3d.js", GRN, ["auto-centres + auto-fits any", "units; loads in the Interactive", "3-D tab in place of the", "parametric placeholder."]),
]
x0, y0, cw, ch = 40, 128, 280, 116
for i, (ti, col, rows) in enumerate(stages):
    cx = x0 + i*(cw+8)
    P.append(box(cx, y0, cw, ch, PANEL, LINE, 10, 1))
    P.append('<rect x="%d" y="%d" width="5" height="%d" rx="2.5" fill="%s"/>' % (cx, y0, ch, col))
    P.append(t(cx+16, y0+22, ti, 11, col, 700))
    yy = y0+42
    for r in rows: P.append(t(cx+16, yy, r, 8.6, SUB, 400)); yy += 15
    if i < 3: P.append('<text x="%d" y="%d" font-size="20" fill="%s">&#8594;</text>' % (cx+cw-4, y0+ch/2+6, SUB))
hr(262)

# authoritative vs approximation
P.append(t(40, 290, "AUTHORITATIVE vs APPROXIMATION", 13, ACC, 700))
P.append(box(40, 304, 560, 120, PANEL, GRN, 12, 1))
P.append(t(58, 330, "🧩  LOCAL MODEL  (this feature)", 12.5, GRN, 700))
for k, ln in enumerate(["Your real OBJ/STL file — shown as-is, NO watermark.", "Replaces the placeholder in the Interactive 3-D tab.",
                        "Green badge + one-click toggle back to the placeholder.", "index/models3d/<NSN>.obj|.stl"]):
    P.append(t(58, 356+k*17, "· "+ln, 9.6, SUB, 400))
P.append(box(620, 304, 540, 120, PANEL, AMB, 12, 1))
P.append(t(638, 330, "⚠  IMAGE→3D  (Approximation tab)", 12.5, AMB, 700))
for k, ln in enumerate(["AI-generated from the figure crop (TripoSR…).", "Gated — off until you configure a backend.",
                        "ALWAYS watermarked 'NOT TO SCALE'.", "index/mesh3d/ · docs/IMAGE3D-SETUP.md"]):
    P.append(t(638, 356+k*17, "· "+ln, 9.6, SUB, 400))
hr(444)

# verified
P.append(t(40, 472, "VERIFIED (host-side)", 13, GRN, 700))
P.append(box(40, 486, 1120, 96, PANEL, GRN, 12, 1))
ver = ["VERIFY-LOCALMODEL.bat: localmodel.py + viewer_app.py + both UI pages parse.",
       "Round-trip parse of a sample OBJ (8v/12f), ASCII STL and BINARY STL (36v/12f each) → all OK; test files cleaned up.",
       "gl3d auto-centres/auto-fits, so a model in any units displays correctly; materials still come from FLIS/scan.",
       "Additive & rollbackable (R1): drop the module + 2 routes + the loadLocalModel block. How-to: docs/LOCAL-MODELS.md."]
yy = 508
for v in ver:
    P.append('<circle cx="56" cy="%d" r="2.6" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(66, yy, v, 232, 9.6, SUB, 13); P.append(s); yy += 13*n + 4

P.append(t(40, H-12, "Markup. Dark (R3). v0.94.0 · 2026-06-04 · localmodel.py · /api/localmodel(_mesh) · threed.html loadLocalModel · gl3d.js · index/models3d. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "103-local-models")), "bytes")
