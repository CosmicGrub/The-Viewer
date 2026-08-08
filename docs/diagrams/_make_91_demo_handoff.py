#!/usr/bin/env python3
"""v0.83.1 — demo becomes the onboarding intro; Finish hands off to the REAL side chooser. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 560
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
P.append(t(40, 46, "Onboarding hand-off: guided tour -> the real chooser  (v0.83.1)", 19, TXT, 700))
P.append(t(40, 70, "First run plays the tour inside the app, then drops the user into the genuine “Choose your side” modal — with no coach-marks.", 11, SUB, 400))
P.append('<line x1="40" y1="86" x2="%d" y2="86" stroke="%s"/>' % (W - 40, LINE))

# flow
P.append(panel(40, 112, 250, 132, "LOAD", "app loads (index.html)", ACC,
    ["?side= deep link wins", "else saved side -> straight in", "else first-run -> show the tour"],
    "viewer_demo_seen gates it"))
P.append('<text x="306" y="180" font-size="22" fill="%s">&#8594;</text>' % SUB)
P.append(panel(322, 112, 250, 132, "TOUR", "demo in an iframe", TEAL,
    ["src = /demo?embed=1", "self-contained ES5 walkthrough", "Back/Next/Skip/Autoplay + dots"],
    "embed mode detected"))
P.append('<text x="588" y="180" font-size="22" fill="%s">&#8594;</text>' % SUB)
P.append(panel(604, 112, 250, 132, "FINISH", "Finish / Skip", AMB,
    ["postMessage {viewerDemo:'finish'}", "parent closes the iframe", "sets viewer_demo_seen"],
    "hand-off signal"))
P.append('<text x="870" y="180" font-size="22" fill="%s">&#8594;</text>' % SUB)
P.append(panel(886, 112, 254, 132, "CHOOSER", "real #sidegate modal", GRN,
    ["openSideChooser() — no guides", "Operator (-10) / Mechanic (-20)", "choice saved -> into the app"],
    "the genuine onboarding"))

# standalone path
yb = 270
P.append(box(40, yb, 545, 96, PANEL, PUR, 12, 1))
P.append(t(58, yb + 24, "Standalone (DEMO.bat / file://)", 12, PUR, 700))
s, _ = wrap(58, yb + 44, "Same tour, but Finish has no parent app to message. It navigates to  http://127.0.0.1:8765/?onboard=1 , and the app honors ?onboard=1 by forcing the real chooser. So either way you end in the genuine modal.", 92, 9.5, SUB, 13)
P.append(s)

P.append(box(596, yb, 544, 96, PANEL, ACC, 12, 1))
P.append(t(614, yb + 24, "Replay & escape hatches", 12, ACC, 700))
s, _ = wrap(614, yb + 44, "“▶ Watch the guided tour” button in the chooser footer replays it anytime. A “Skip tour → choose side” button is pinned on the tour overlay. Returning users with a saved side never see the tour.", 96, 9.5, SUB, 13)
P.append(s)

# compat
yc = yb + 112
P.append(box(40, yc, 1100, 56, PANEL, GRN, 12, 1))
P.append(t(58, yc + 22, "Compatibility (R1)", 11.5, GRN, 700))
s, _ = wrap(58, yc + 40, "Additive and behavior-preserving: a saved side still bypasses everything; only the first-run path changed. iframe + postMessage + localStorage are all ES5/legacy-safe. Rollback = revert the index.html load block + the demo embed branch.", 205, 9.5, SUB, 12)
P.append(s)

P.append(t(40, H - 8, "Data-flow diagram. Dark (R3). v0.83.1 · 2026-06-04 · index.html load + #demogate iframe · demo.html finishTour() · /demo?embed=1. Backwards-compatible (R1).", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "91-demo-handoff")), "bytes")
