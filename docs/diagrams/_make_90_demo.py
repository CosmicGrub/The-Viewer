#!/usr/bin/env python3
"""v0.83.0 — Interactive demo / onboarding tour (both sides), launched from a bat. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 640
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
P.append(t(40, 46, "Interactive demo / onboarding tour  (v0.83.0)", 19, TXT, 700))
P.append(t(40, 70, "Double-click DEMO.bat -> a self-contained guided walkthrough of every core feature, for both sides of the house. No server needed.", 11, SUB, 400))
P.append('<line x1="40" y1="86" x2="%d" y2="86" stroke="%s"/>' % (W - 40, LINE))

# launch chain
P.append(panel(40, 108, 250, 120, "BAT", "DEMO.bat", ACC,
    ["double-click in the project root", "start \"\" demo.html", "opens in the default browser"],
    "no server, no install"))
P.append('<text x="306" y="172" font-size="22" fill="%s">&#8594;</text>' % SUB)
P.append(panel(322, 108, 250, 120, "HTML", "demo.html (ES5)", TEAL,
    ["pure ES5 + inline CSS/SVG", "zero external dependencies", "RPS-safe: runs on old browsers"],
    "deterministic, always renders"))
P.append('<text x="588" y="172" font-size="22" fill="%s">&#8594;</text>' % SUB)
P.append(panel(604, 108, 250, 120, "GATE", "Choose your side", AMB,
    ["Operator (-10)  /  Mechanic (-20)", "filters steps by op / mech / both", "switch sides any time"],
    "right depth for the viewer"))
P.append('<text x="870" y="172" font-size="22" fill="%s">&#8594;</text>' % SUB)
P.append(panel(886, 108, 254, 120, "TOUR", "coach-mark engine", GRN,
    ["scrim + spotlight cutout", "SVG arrows + callout tooltips", "Back/Next/Skip/Autoplay + dots"],
    "step-by-step, highlighted"))

# the two scripted paths
yb = 250
P.append(box(40, yb, 545, 150, PANEL, TEAL, 12, 1))
P.append(t(58, yb + 24, "OPERATOR (-10) path", 12.5, TEAL, 700))
ops = ["1  Search a fault (offline, instant) + predictive suggestions",
       "2  Results tagged by side — operator hits first",
       "3  Open the exact manual page",
       "4  Find-in-manual (Ctrl+F) with highlighted hits",
       "5  Operator checks (safety-first; escalate when needed)",
       "6  Solve-it hub"]
yy = yb + 44
for s in ops:
    P.append(t(58, yy, s, 10, SUB, 400)); yy += 17

P.append(box(596, yb, 544, 150, PANEL, AMB, 12, 1))
P.append(t(614, yb + 24, "MECHANIC (-20) path  (adds, on top of the above)", 12.5, AMB, 700))
mech = ["4  Procedure / how-to: ordered steps + tools + warnings",
        "5  Torque & fastener reference (dry vs. lubed)",
        "6  3-D parts: real manual figure + live parametric model",
        "7  Look-alike part-diff: flags thread/length/source",
        "8  Circuit Lab: trace + simulate the schematic",
        "9  Smart Collections   +   10  Add documents (ingest)"]
yy = yb + 44
for s in mech:
    P.append(t(614, yy, s, 10, SUB, 400)); yy += 17

# robustness note
yc = yb + 168
P.append(box(40, yc, 1100, 64, PANEL, PUR, 12, 1))
P.append(t(58, yc + 24, "Why this one always works", 11.5, PUR, 700))
s, _ = wrap(58, yc + 44, "The demo is decoupled from the live server and live data (faithful in-HTML mock screens), so it is immune to the port / stale-process issue that was masking earlier changes. Also exposed in-app at /demo. Purely additive (R1): two files + one route; rollback = delete them.", 210, 9.5, SUB, 13)
P.append(s)

P.append(t(40, H - 8, "Data-flow diagram. Dark (R3). v0.83.0 · 2026-06-04 · DEMO.bat + engine/ui/demo.html + /demo route. ES5/RPS-safe, backwards-compatible & rollbackable (R1).", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "90-demo-onboarding")), "bytes")
