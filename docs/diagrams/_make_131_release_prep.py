#!/usr/bin/env python3
"""v0.99.34 — Release prep: one-click verify orchestrator + v1.0 cut. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
W, H = 1120, 520
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
P.append(t(40, 46, "Release prep — one button to green-light, one to cut 1.0   v0.99.34", 19, TXT, 700))
hr(70)
P.append(t(40, 100, "RUN-ALL-VERIFY.bat  →  docs\\run-all.log", 13, GRN, 700))
P.append(box(40, 114, 1040, 96, PANEL, GRN, 12, 1))
steps = "1. VERIFY-099 (syntax·audit·completeness·snapshot·UI-JS·regression·fuzz smoke)   →   2. HTTP fuzz (no 5xx)   →   3. Mutation (test-quality)   →   4. Build visual index"
s,_ = wrap(58, 140, steps, 232, 10.5, SUB, 16); P.append(s)
P.append(t(58, 190, "Long jobs stay SEPARATE (run when ready): RESUME-OCR · BUILD-EMBEDDINGS · BUILD-INSTALLER.", 9.6, AMB, 400))
hr(228)
P.append(t(40, 256, "CUT-V1.0.bat  →  engine\\cut_v1.py", 13, "#7fbfff", 700))
P.append(box(40, 270, 1040, 110, PANEL, "#7fbfff", 12, 1))
r = ["Run ONLY after RUN-ALL-VERIFY is clean. Takes a safeguard snapshot (rollback point), stamps VERSION=1.0.0,",
     "banners both changelogs with a [1.0.0] entry, and regenerates the iteration snapshot so it still MATCHES (R10).",
     "Refuses to re-cut if already 1.x; prompts before it commits. Human notes: docs/RELEASE-NOTES-1.0.md."]
yy = 294
for x in r:
    P.append('<circle cx="56" cy="%d" r="2.5" fill="%s"/>' % (yy-3, "#7fbfff")); s, n = wrap(66, yy, x, 234, 9.6, SUB, 14); P.append(s); yy += 14*n + 5
hr(396)
P.append(t(40, 424, "R1 · additive tooling; cut_v1.py verified (parses + completeness-clean). The feature set is well past 1.0 scope; this makes the cut a single command.", 10, SUB, 400))
P.append(t(40, H-8, "Markup. Dark (R3). v0.99.34 · 2026-07-01 · RUN-ALL-VERIFY.bat · CUT-V1.0.bat · cut_v1.py. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "131-release-prep")), "bytes")
