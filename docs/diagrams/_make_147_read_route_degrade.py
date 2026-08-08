#!/usr/bin/env python3
"""v1.3.4 — Read routes degrade gracefully when an optional sidecar isn't built. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
W, H = 1140, 430
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
P.append(t(40, 46, "Read routes degrade gracefully on un-built sidecars   v1.3.4", 17, TXT, 700))
P.append(t(40, 64, "One error boundary, now classifying DB errors instead of blanket-500", 11, SUB, 400))
hr(80)
P.append(t(40, 106, "GET /api/* raises ...", 12.5, TXT, 700))
rows = [
    ("registry.ParamError  (bad ?limit=abc)", "-> 400", ACC),
    ("FileNotFoundError  (missing doc/page/crop)", "-> 404", ACC),
    ("OperationalError \"no such table\"  (sidecar NOT built)", "-> 200  {ok:false, unavailable:true}", GRN),
    ("OperationalError \"no such column\" / locked / corrupt", "-> 500 + log ref  (real DB issue)", AMB),
    ("KeyError / TypeError / any logic bug", "-> 500 + log ref  (stays visible)", RED),
]
y = 128
for left, right, col in rows:
    P.append(box(40, y, 560, 34, PANEL, LINE, 8, 1)); P.append(t(56, y+22, left, 10.5, SUB, 400))
    P.append('<path d="M604 %d L648 %d" stroke="%s" stroke-width="2" marker-end="url(#a)"/>' % (y+17, y+17, SUB))
    P.append(box(652, y, 448, 34, P2, col, 8, 1)); P.append(t(668, y+22, right, 10.5, col, 700))
    y += 44
P.append('<defs><marker id="a" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">'
         '<path d="M0 0 L6 3 L0 6 z" fill="%s"/></marker></defs>' % SUB)
hr(y+8)
P.append(t(40, y+34, "Why", 13, TXT, 700))
P.append(box(40, y+46, 1060, 60, PANEL, GRN, 12, 1))
s, _ = wrap(58, y+68, "THE VIEWER now has many OPTIONAL sidecars (measures/tables/enrich/masterfile/kg/sides/chapters). "
            "A route hitting one that hasn't been built should say 'not built yet', not crash with a 500. This fixes "
            "the read-route 5xx class the HTTP fuzz flags, WITHOUT hiding genuine bugs (those still 500 with a log ref). "
            "The originally-reported 500 list was from stale 0.99.34 code -- re-run RUN-HTTP-FUZZ.bat for a current signal.",
            244, 10.3, SUB, 15); P.append(s)
print("PDF bytes:", render("".join(P) + "</svg>", BASE_DIR + "/147-read-route-degrade"))
