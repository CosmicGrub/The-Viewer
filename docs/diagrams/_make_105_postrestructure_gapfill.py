#!/usr/bin/env python3
"""v0.98.1 — Post-restructure gap-fill: integration coverage for the imagery/CAD/schematic stack + doc refresh. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1200, 780
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "Post-restructure gap-fill   v0.98.1", 19, TXT, 700))
P.append(t(40, 70, "A paused 0.95 session re-synced to the real v0.98.0 tree, confirmed THE RESTRUCTURE kept the 0.90–0.95 stack intact, and closed two overlooked gaps.", 11.5, SUB, 400))
hr(86)

# what was verified
P.append(t(40, 114, "1 · RE-SYNC & AUDIT (read-only) — did the monolith→features/ split drop anything?", 13, TEAL, 700))
P.append(box(40, 128, 1120, 92, PANEL, GRN, 12, 1))
au = ["Routes: /cadimg /cadspin /cadstl /cadobj /api/cadmaterial /api/schempaths /api/schemgraph /api/localmodel(_mesh) — ALL registered in the new registry.",
      "Modules: schemgraph · localmodel · cad_render · schem_overlay — present + referenced by features/.",
      "cad_render CAD_VERSION 7 · render()/material_for/render_spin/ensure_spin intact · make_cad parallel (multiprocessing/--force) intact.",
      "UI: threed/schematics + cadview/schemflow/schemhl/gl3d served. → Nothing dropped by the split."]
yy = 150
for a in au:
    P.append('<circle cx="56" cy="%d" r="2.6" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(66, yy, a, 232, 9.5, SUB, 13); P.append(s); yy += 13*n + 4
hr(232)

# the two gaps filled
P.append(t(40, 260, "2 · GAPS FILLED (additive — no engine code touched)", 13, AMB, 700))
cards = [
 ("tests/test_features_integration.py", GRN, ["16 checks spanning the imagery/CAD/", "schematic features THROUGH the new", "registry: routes registered, CAD v7,", "material_for, render_spin, a v1 render,", "schemgraph one-net, localmodel OBJ.", "A permanent regression guard."]),
 ("VERIFY-V098.bat", ACC, ["one host-side button: parse shell +", "features/*.py, then run the core", "suites + the new test to a log.", "", "RESULT: 21+16+59+15+12 =", "123 checks · 0 failures."]),
 ("Refreshed hand-off docs", AMB, ["PROJECT-SUMMARY.md + PORTING.md", "were stale (0.95 monolith).", "Now describe the v0.98 thin shell", "+ engine/features/ package,", "registry/routes, new backups,", "nav consolidation."]),
]
x0, y0, cw, ch = 40, 274, 372, 150
for i, (ti, col, rows) in enumerate(cards):
    cx = x0 + i*(cw+2)
    P.append(box(cx, y0, cw-8, ch, PANEL, LINE, 10, 1))
    P.append('<rect x="%d" y="%d" width="5" height="%d" rx="2.5" fill="%s"/>' % (cx, y0, ch, col))
    P.append(t(cx+16, y0+22, ti, 10.5, col, 700))
    yy = y0+44
    for r in rows: P.append(t(cx+16, yy, r, 8.7, SUB, 400)); yy += 15
hr(444)

# safety note
P.append(t(40, 472, "3 · SAFETY — why this couldn't collide with the restructure session", 13, ACC, 700))
P.append(box(40, 486, 1120, 96, PANEL, ACC, 12, 1))
sf = ["The restructure (0.96→0.98, 2026-06-10) was already complete on disk — this session DISREGARDED redoing it (per instruction).",
      "This pass is purely ADDITIVE: two NEW files + doc/changelog edits. No feature module, route, or shell code was modified (R1).",
      "Rollback = delete the 2 new files + revert the doc/changelog entries. Everything verified green host-side (coherent files).",
      "R1 backwards-compatible · R4 changelog · R7 legacy parity entry · this diagram (R2/R3)."]
yy = 508
for a in sf:
    P.append('<circle cx="56" cy="%d" r="2.6" fill="%s"/>' % (yy-3, ACC)); s, n = wrap(66, yy, a, 232, 9.5, SUB, 13); P.append(s); yy += 13*n + 4

P.append(t(40, H-12, "Markup. Dark (R3). v0.98.1 · 2026-07-01 · tests/test_features_integration.py · VERIFY-V098.bat · PROJECT-SUMMARY/PORTING refresh. Additive, R1.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "105-postrestructure-gapfill")), "bytes")
