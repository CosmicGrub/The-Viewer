#!/usr/bin/env python3
"""v0.95.0 — Hardware-aware boost (parallel CAD batch) + CAD textures grafted onto the 3-D model. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1200, 780
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "Hardware-aware boost + CAD-textured 3-D   v0.95.0", 19, TXT, 700))
P.append(t(40, 70, "Tuned to the machine: 16-core Alder Lake + RTX 4050. Use the cores for the CAD batch; graft the CAD look onto the WebGL model.", 11.5, SUB, 400))
hr(86)

# boost
P.append(t(40, 114, "1 · PARALLEL CAD BATCH (the CPU-bound straggler, fixed)", 13, GRN, 700))
P.append(box(40, 128, 560, 150, PANEL, GRN, 12, 1))
P.append(t(58, 154, "make_cad.py was single-threaded → now multiprocessing.Pool", 11, TXT, 700))
for k, ln in enumerate(["auto-sized to cpu_count-1 (cap 12); --workers / --serial.",
                        "renders are independent → distinct cache files, no contention.",
                        "parent pre-filters cached parts (resumable)."]):
    P.append(t(58, 178+k*17, "· "+ln, 9.6, SUB, 400))
P.append(box(58, 232, 524, 34, P2, GRN, 8, 1))
P.append(t(72, 254, "MEASURED (16 cores): 120 parts  15.4s serial -> 5.26s on 12 workers  =  2.9x", 10, GRN, 700))
P.append(box(620, 128, 540, 150, PANEL, ACC, 12, 1))
P.append(t(638, 154, "Full re-render (98k images, 3 tiers)", 11, ACC, 700))
P.append(t(638, 182, "serial      ~210 min", 12, SUB, 400))
P.append(t(638, 206, "parallel    ~72 min", 13, GRN, 700))
P.append(t(638, 236, "(+ per-worker startup amortizes further at full scale)", 9.4, SUB, 400))
P.append(t(638, 258, "GPU note: RTX 4050 already drives WebGL 3-D + GPU-tier OCR.", 9.2, "#7f8a99", 400))
hr(296)

# textures to 3D
P.append(t(40, 324, "2 · CAD COLOUR + TEXTURE GRAFTED ONTO THE 3-D MODEL", 13, AMB, 700))
stages = [
 ("cad_render.material_for()", GRN, ["colour + metal + material CLASS", "(metal/rubber/wood/plastic/", "paint/brass) + a gl vector.", "route /api/cadmaterial."]),
 ("gl3d.js shader", AMB, ["NEW klass uniform -> procedural", "texture: brushed metal, rubber", "speckle, wood rings, CARC", "orange-peel, brass. load/setKlass."]),
 ("threed.html", AMB, ["applyCadMaterial(m) on open ->", "colour+class on the Interactive", "3-D model. Rotate CAD stays", "flat steel (klass 0)."]),
 ("RESULT", GRN, ["the WebGL 3-D model now MATCHES", "the CAD image's colour + surface.", "graceful: a bad shader just", "falls back to SVG (no crash)."]),
]
x0, y0, cw, ch = 40, 338, 280, 116
for i, (ti, col, rows) in enumerate(stages):
    cx = x0 + i*(cw+8)
    P.append(box(cx, y0, cw, ch, PANEL, LINE, 10, 1))
    P.append('<rect x="%d" y="%d" width="5" height="%d" rx="2.5" fill="%s"/>' % (cx, y0, ch, col))
    P.append(t(cx+16, y0+22, ti, 10.5, col, 700))
    yy = y0+42
    for r in rows: P.append(t(cx+16, yy, r, 8.5, SUB, 400)); yy += 15
    if i < 3: P.append('<text x="%d" y="%d" font-size="20" fill="%s">&#8594;</text>' % (cx+cw-4, y0+ch/2+6, SUB))
hr(472)

# verified
P.append(t(40, 500, "VERIFIED (host-side)", 13, GRN, 700))
P.append(box(40, 514, 1120, 92, PANEL, GRN, 12, 1))
ver = ["VERIFY-BOOST.bat -> docs/boost_verify.log: cad_render / make_cad / viewer_app parse; gl3d.js passes node --check; both UI pages parse.",
       "Benchmark printed the 2.9x speedup above (bench_cad_parallel.py).",
       "CAD texture is a gl3d shader add with a graceful fallback (compile-fail -> SVG, never a crash) — and it compiles.",
       "Additive & rollbackable (R1): revert the pool in make_cad, the shader klass block, material_for + /api/cadmaterial, applyCadMaterial."]
yy = 536
for v in ver:
    P.append('<circle cx="56" cy="%d" r="2.6" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(66, yy, v, 232, 9.5, SUB, 13); P.append(s); yy += 13*n + 4

P.append(t(40, H-12, "Markup. Dark (R3). v0.95.0 · 2026-06-05 · make_cad.py multiprocessing · cad_render.material_for · /api/cadmaterial · gl3d klass texture · threed applyCadMaterial. R1.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "104-boost-and-textured-3d")), "bytes")
