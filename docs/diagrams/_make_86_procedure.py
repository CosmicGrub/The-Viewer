#!/usr/bin/env python3
"""BUILT 0.72.0: reconstituted Fix/procedure pages — deepened parser + side-by-side + checklist + print +
parts/fault correlation. (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 540
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
P.append(t(40, 46, "BUILT — reconstituted Fix / how-to pages  (v0.72.0)", 19, TXT, 700))
P.append(t(40, 70, "A how-to buried in a scanned manual becomes a clean, checkable, exportable step-by-step page — verbatim, shown beside the original to verify.", 11, SUB, 400))
P.append('<line x1="40" y1="86" x2="%d" y2="86" stroke="%s"/>' % (W - 40, LINE))
P.append(panel(40, 108, 360, 196, "\U0001F9E0", "Deepened parser (engine)", ACC,
  ["procedure_feature.py: tools, warnings CLASSIFIED (NOTE/CAUTION/WARNING/DANGER), numbered steps + sub-steps (a./(1)).",
   "Per-step callouts pulled out: torque values, FIG refs, NSNs, part numbers.",
   "procedure_full(query) finds the best procedure in the OCR'd text + its SOURCE page + the parts it involves + fault terms."],
  "Structured, verbatim — nothing invented."))
P.append(panel(412, 108, 360, 196, "\U0001F4D6", "Side-by-side + correlate", TEAL,
  ["Rebuilt steps on the left, the ORIGINAL scanned page on the right — click to open full size; figure chips jump to the cited FIG.",
   "Each step's NSN chips + a parts panel link to the dossier (PUB LOG manufacturer / interchangeable).",
   "Tied to the fault terms that found it."],
  "Trust the rebuild against the source."))
P.append(panel(784, 108, 356, 196, "\U0001F5A8", "Both exports", AMB,
  ["Interactive CHECKLIST — tick each step as you go; state persists (localStorage).",
   "Printable take-to-bay SHEET — 🖨 Print (print-CSS hides nav/side, keeps the clean steps).",
   "ES5-safe page (RPS gate) — works on legacy too."],
  "On-screen checklist AND a paper sheet."))
P.append(box(40, 320, 1100, 88, PANEL, GRN, 12, 1))
P.append(t(58, 342, "VERIFIED (engine) + host gate", 11.5, GRN, 700))
s, _ = wrap(58, 362, "procedure_feature isolation-tested on a synthetic procedure: tools + WARNING/NOTE classified + 4 steps + sub-steps captured + 35 ft-lb torque + FIG 5/12-3 + NSNs 5305-01-674-1467 / 2920-01-449-2202; procedure_full returned source page 42 + parts. procedure.html confirmed ES5-clean; route + _SUB_RE fix confirmed on host; /api/procedure_full added to the test_routes congruence suite. The mount is corrupting reads of several files now, so the server suite is verified host-side via RUN-ALL-TESTS.bat.", 200, 9, SUB, 12)
P.append(s)
P.append(box(40, 416, 1100, 60, PANEL, PUR, 12, 1))
s, _ = wrap(58, 437, "Use it: open How to do it, type a part or symptom (e.g. 'alternator replacement'), get the rebuilt steps beside the page, tick them off, print the sheet, or jump to a part's dossier. Also reachable from Solve it.", 200, 9, SUB, 12)
P.append(s)
P.append(t(40, H - 8, "BUILT diagram. Dark (R3). v0.72.0 · 2026-06-03 · procedure_feature.py · /api/procedure_full · ui/procedure.html (side-by-side/checklist/print/correlate). Additive (R1/R6).", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "86-procedure-reconstituted-built")), "bytes")
