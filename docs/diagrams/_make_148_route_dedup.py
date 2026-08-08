#!/usr/bin/env python3
"""v1.3.5 — Fix duplicate route collisions + audit guard. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
W, H = 1140, 440
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
P.append(t(40, 46, "Duplicate route collisions fixed + audit guard   v1.3.5", 17, TXT, 700))
P.append(t(40, 64, "A {path:handler} registry silently drops one of two same-path handlers", 11, SUB, 400))
hr(80)
P.append(t(40, 106, "Before — collision (one handler DEAD)", 12.5, RED, 700))
P.append(box(40, 118, 520, 130, PANEL, RED, 12, 1))
P.append(t(58, 142, "@get /figcrop  (doc/page crop)   <- deepzoom/rpstl/xref", 9.6, SUB, 400))
P.append(t(58, 160, "@get /figcrop  (name crop)       <- visual search   ⟵ wins", 9.6, "#f2c3ad", 700))
P.append(t(58, 182, "=> doc/page figure crops 404 all over the app", 9.6, RED, 700))
P.append(t(58, 210, "@get /api/coverage  overview     <- /coverage,/ops", 9.6, SUB, 400))
P.append(t(58, 228, "@get /api/coverage  per-vehicle  <- home  ⟵ wins", 9.6, "#f2c3ad", 700))
P.append(t(600, 106, "After — merged, branch on param", 12.5, GRN, 700))
P.append(box(600, 118, 500, 130, PANEL, GRN, 12, 1))
P.append(t(618, 142, "/figcrop:  ?name= -> figcache file", 9.8, "#8fd6ab", 400))
P.append(t(618, 160, "           else  -> doc/page crop", 9.8, "#8fd6ab", 400))
P.append(t(618, 190, "/api/coverage:  ?vehicle= -> per-vehicle", 9.8, "#8fd6ab", 400))
P.append(t(618, 208, "                else      -> overview", 9.8, "#8fd6ab", 400))
P.append(t(618, 236, "both callers work; no dead handler", 9.6, GRN, 700))
hr(266)
P.append(t(40, 292, "Guard so it can't recur", 13, TXT, 700))
P.append(box(40, 304, 1060, 96, PANEL, ACC, 12, 1))
s, _ = wrap(58, 328, "audit_features.py [0] now scans the routes source for repeated @get/@post on the same "
            "(method, path) and FAILs on any duplicate -- the runtime dict hid these. GET+POST on one path (legit "
            "read/write) is not flagged. Verified: 101 decorators, 0 same-method duplicates. Runs in VERIFY-099. "
            "Pairs with v1.3.4 (read routes degrade instead of 500 when a sidecar isn't built).", 246, 10.4, SUB, 15)
P.append(s)
print("PDF bytes:", render("".join(P) + "</svg>", BASE_DIR + "/148-route-dedup"))
