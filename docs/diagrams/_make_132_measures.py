#!/usr/bin/env python3
"""v1.1.0 — Measurement / dimensional-data extraction. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
W, H = 1180, 560
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
P.append(t(40, 46, "Measurements & dimensions — pull every measured value out of the text   v1.1.0", 19, TXT, 700))
hr(70)
# pipeline row
P.append(panel(40, 92, 250, 150, "📄", "Text layer (already indexed)", ACC,
               ["Native PDF text (born-digital)", "OCR layer (scanned pages)", "No new scan needed — reuse FTS"],
               "SOURCE · read-only (R1)"))
P.append(panel(310, 92, 300, 150, "📐", "measures.extract()", TEAL,
               ["One tolerant regex over the text",
                "Captures value · range X–Y · tol X±Y",
                "Unit ordering: ft-lb>ft, in-lb>in, N-m>N",
                "13 dimension types classified"],
               "PURE · regex · deterministic"))
P.append(panel(630, 92, 250, 150, "🏷", "Per-hit record", AMB,
               ["type · unit (canonical) · value(s)", "tolerance · raw · context sentence", "cited PAGE + doc + vehicle"],
               "STRUCTURED"))
P.append(panel(900, 92, 240, 150, "🖥", "/measures + /api/measures", PUR,
               ["Grouped + filterable by type", "Each links to its cited page", "Live over FTS — no build step"],
               "OFFLINE UI"))
# arrows
for x1, x2 in [(290, 310), (610, 630), (880, 900)]:
    P.append('<path d="M%d 167 L%d 167" stroke="%s" stroke-width="2" marker-end="url(#a)"/>' % (x1, x2, SUB))
P.append('<defs><marker id="a" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">'
         '<path d="M0 0 L6 3 L0 6 z" fill="%s"/></marker></defs>' % SUB)
hr(262)
# dimension types covered
P.append(t(40, 290, "Dimension types covered", 13, TXT, 700))
types = ["length", "area", "angle", "weight", "force", "torque", "pressure",
         "capacity", "electrical", "temperature", "flow", "speed", "rotation"]
x = 40
for ty in types:
    w = 12 + len(ty) * 8
    P.append(box(x, 302, w, 26, P2, TEAL, 6, 1)); P.append(t(x + 8, 319, ty, 10.5, TEAL, 700)); x += w + 8
# sidecar + guarantee
P.append(t(40, 366, "Optional corpus-wide sidecar", 13, TXT, 700))
P.append(box(40, 380, 540, 96, PANEL, GRN, 12, 1))
s, _ = wrap(58, 406, "BUILD-MEASURES.bat → build_measures.py walks every page and writes index/measures.db "
            "(append-only, read-only on viewer.db — R1/R6). Enables fleet-wide browsing/counts, e.g. 'every torque "
            "spec across all vehicles'. Resumable per doc.", 116, 10.5, SUB, 15)
P.append(s)
P.append(t(620, 366, "The guarantee", 13, TXT, 700))
P.append(box(620, 380, 520, 96, PANEL, AMB, 12, 1))
s, _ = wrap(638, 406, "Closes the 'especially measurements/dimensional data' gap: beyond finding the PAGE, the mechanic "
            "gets the NUMBERS themselves — value, range, tolerance, unit — cited and machine-checkable. Full map in "
            "docs/EXTRACTION-COVERAGE.md.", 112, 10.5, SUB, 15)
P.append(s)
P.append(t(40, 512, "Additive & rollbackable (R1). Self-test: 19 measurements across all target types — PASS.", 10, SUB, 400))
print("PDF bytes:", render("".join(P) + "</svg>", BASE_DIR + "/132-measures"))
