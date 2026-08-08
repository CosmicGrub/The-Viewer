#!/usr/bin/env python3
"""v0.90.0 — CAD-first library + a rundown of every CAD/3-D bat. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 760
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
P.append(t(40, 46, "CAD-first 3-D library + bat rundown  (v0.90.0)", 19, TXT, 700))
P.append(t(40, 70, "The CAD image is now the face of every part. The interactive 3-D model and the cited manual figure are one click away.", 11, SUB, 400))
P.append('<line x1="40" y1="86" x2="%d" y2="86" stroke="%s"/>' % (W - 40, LINE))

# representation hierarchy
P.append(t(40, 116, "WHAT YOU SEE NOW", 13, ACC, 700))
P.append(panel(40, 130, 360, 132, "GRID", "every card", ACC,
    ["leads with the CAD image (/cadimg)", "textured + coloured + dimensioned", "detail follows the build tier (&tier=)",
     "parametric SVG = loading placeholder only"],
    "uniform CAD face across the library"))
P.append('<text x="416" y="200" font-size="22" fill="%s">&#8594;</text>' % SUB)
P.append(panel(432, 130, 708, 132, "MODAL", "click a part → tabs (CAD opens first)", GRN,
    ["🖼 CAD image (default) — the rendered representative CAD, scaled to FLIS dims",
     "◳ Interactive 3-D — the live WebGL parametric model (spin / zoom)",
     "📄 Manual illustration — the real cited TM scan, when one exists",
     "⚠ Approximation — opt-in experimental image→3-D"],
    "CAD at the forefront; figure + live 3-D secondary"))

# bat rundown
P.append(t(40, 300, "RUN THESE — every CAD/3-D bat (all compile-verified)", 13, AMB, 700))
rows = [
 ("RUN-CAD-TIERS.bat", GRN, "Render ALL THREE tiers (v1/v2/v3) for the whole ~32,622-part set — the complete collection.", "★ run this for a complete CAD set (resumable)"),
 ("MAKE-CAD.bat", ACC, "Render only the modern v3 (textured) set into index/cadcache.", "modern set only"),
 ("RUN-CAD-BATCH.bat", ACC, "Stop any running batch, clear orphaned older renders, render v3 fresh.", "clean restart of v3"),
 ("CAD-STATUS.bat", TEAL, "Live progress: per-tier counts (legacy/lite/modern), %, rate, ETA, or COMPLETE.", "check progress anytime"),
 ("RENDER-CONTACT.bat", PUR, "A 10-part textured contact sheet -> docs/cad_contact_sheet.png.", "see the textures"),
 ("RENDER-COMPARE.bat", PUR, "A 50-part v1-vs-v2 comparison sheet -> docs/cad_v1_vs_v2.png.", "see the v1→v2 jump"),
 ("RUN-CADCHECK.bat", AMB, "Start a throwaway server on 8766 and HTTP-probe /cadimg -> a real PNG.", "smoke-test the route"),
]
y = 320
P.append(box(40, y, 1100, 26, P2, LINE, 6, 1))
P.append(t(54, y+18, "BAT", 9.5, SUB, 700)); P.append(t(280, y+18, "WHAT IT DOES", 9.5, SUB, 700)); P.append(t(900, y+18, "WHEN", 9.5, SUB, 700))
y += 30
for name, col, what, when in rows:
    P.append(box(40, y, 1100, 40, PANEL, LINE, 7, 1))
    P.append('<rect x="40" y="%d" width="5" height="40" rx="2.5" fill="%s"/>' % (y, col))
    P.append(t(54, y+25, name, 10.5, col, 700))
    s, _ = wrap(280, y+17, what, 118, 9.3, TXT, 12); P.append(s)
    s, _ = wrap(900, y+17, when, 44, 9.0, SUB, 12); P.append(s)
    y += 45

P.append(box(40, y+4, 1100, 44, PANEL, ACC, 12, 1))
s, _ = wrap(58, y+24, "Don't have a cached image? The server renders it on demand: GET /cadimg?nsn=… (or ?style=v1|v2|v3 / ?tier=modern|lite|legacy). STL/OBJ at /cadstl /cadobj. Tip: never click inside a running batch console — that pauses it (press Esc to resume).", 210, 9.5, SUB, 13)
P.append(s)

P.append(t(40, H-8, "Markup. Dark (R3). v0.90.0 · 2026-06-04 · threed.html CAD-first card+modal · /cadimg tiered · cadcache. All bats compile-audited. R1.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "98-cad-first")), "bytes")
