#!/usr/bin/env python3
"""v0.99.8 — Figure -> Parts: the inverse of the locator; closes the navigation loop. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 700
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "Figure → Parts: closing the navigation loop   v0.99.8", 19, TXT, 700))
P.append(t(40, 70, "The locator sends you from a part to its figures. figureparts sends you from a figure back to ALL its parts — so you can walk the sheet both ways.", 11.5, SUB, 400))
hr(86)

# the loop, as four linked nodes
nodes = [
 ("\U0001f9ed  Locate a part", AMB, "/locate?q=NSN", ["Enter NSN / P-N / name.", "partlocate.py -> every figure", "& page that calls it out."]),
 ("\U0001f50e  Deep-zoom a figure", TEAL, "/deepzoom?doc&page", ["Open the page, pan/zoom,", "progressive DPI + callout", "hotspots on the drawing."]),
 ("\U0001f9e9  Parts on this page", GRN, "/api/figureparts", ["NEW. figureparts.py lists", "EVERY part on the sheet from", "the parts index (deduped)."]),
 ("\U0001f4c7  Any part's dossier", ACC, "/dossier · /partdiff", ["Each row links back to its", "dossier / look-alike diff /", "CAD — and back to /locate."]),
]
x0, y0, cw, ch = 40, 118, 272, 150
cx_list = []
for i, (ti, col, route, rows) in enumerate(nodes):
    cx = x0 + i*(cw+6); cx_list.append(cx)
    P.append(box(cx, y0, cw, ch, PANEL, col, 11, 1))
    P.append(t(cx+16, y0+24, ti, 12.5, col, 700))
    P.append(t(cx+16, y0+42, route, 9.5, SUB, 400))
    yy = y0+64
    for r in rows: P.append(t(cx+16, yy, r, 9.2, SUB, 400)); yy += 15
# arrows between the four, and a wrap-around loop arrow back
for i in range(3):
    ax = cx_list[i]+cw; bx = cx_list[i+1]
    P.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="2" marker-end="url(#ah)"/>' % (ax-2, y0+ch/2, bx+2, y0+ch/2, TEAL))
P.append('<defs><marker id="ah" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="%s"/></marker></defs>' % TEAL)
# loop-back arrow (last -> first) under the row
P.append('<path d="M%d,%d C%d,%d %d,%d %d,%d" stroke="%s" stroke-width="2" fill="none" stroke-dasharray="5 4" marker-end="url(#ah)"/>' % (
    cx_list[3]+cw/2, y0+ch, cx_list[3]+cw/2, y0+ch+34, cx_list[0]+cw/2, y0+ch+34, cx_list[0]+cw/2, y0+ch+4, AMB))
P.append(t(cx_list[1]+40, y0+ch+30, "loop: any part → relocate → next figure", 9.5, AMB, 400))
hr(322)

P.append(t(40, 350, "WHAT IT RETURNS", 13, ACC, 700))
P.append(box(40, 364, 1100, 92, PANEL, ACC, 12, 1))
s,_ = wrap(58, 388, "GET /api/figureparts?doc=ID&page=N -> { doc, page, fig_no, fig_title, count, parts:[ {nsn, part_number, name, "
  "nomenclature, cagec, smr, uoc, dossier_url, locate_url, cad_url} ] }. Deduped by (nsn, part-no, name); NSN-first ordering. "
  "Read-only on parts; db_path passed explicitly. The /deepzoom drawer consumes it directly and refreshes on page-turn.", 224, 10, SUB, 15)
P.append(s)
hr(472)

P.append(t(40, 500, "VERIFIED / R1", 13, GRN, 700))
P.append(box(40, 514, 1100, 74, PANEL, GRN, 12, 1))
ver = ["figureparts.py logic-tested in-sandbox on a synthetic index: dup part counted once, fig metadata extracted (fig FIG 5, count 2).",
       "deepzoom.html inline JS passes node --check; the \U0001f9e9 drawer is pure ES5, no new deps. Route is one declarative @get (host-verify in VERIFY-099.bat).",
       "Additive & rollbackable: one module + one read-only route + one UI drawer. Nothing writes the index (R1/R6)."]
yy = 536
for v in ver:
    P.append('<circle cx="56" cy="%d" r="2.6" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(66, yy, v, 224, 9.4, SUB, 13); P.append(s); yy += 13*n + 3

P.append(t(40, H-10, "Markup. Dark (R3). v0.99.8 · 2026-07-01 · figureparts.py //api/figureparts · /deepzoom drawer. Read-only. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "112-figureparts")), "bytes")
