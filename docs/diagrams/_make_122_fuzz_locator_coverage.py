#!/usr/bin/env python3
"""v0.99.18 — Hardening wider: fuzz partlocate + coverage.pct/overview. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 660
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "Hardening, wider — fuzz the locator + coverage math   v0.99.18", 19, TXT, 700))
P.append(t(40, 70, "Extended the property/fuzz harness to the last untested read helpers. 206,300 cases, 0 violations — these modules are solid.", 11.5, SUB, 400))
hr(86)

rows = [
 ("coverage.pct(a,b)", GRN, "pct ∈ [0,100] for 0≤a≤b; exactly 0.0 when b==0; never raises. High-volume (per-iteration loop)."),
 ("partlocate.locate", TEAL, "count == len(appearances) ≤ limit; every URL (deepzoom/vectorize/page) absolute; deduped by (doc,page,fig); never raises."),
 ("coverage.overview", ACC, "never raises; every percentage-named value stays within [0,100]. DB-backed, sampled."),
]
y = 116
for name, col, inv in rows:
    P.append(box(40, y, 1100, 52, PANEL, col, 10, 1))
    P.append(t(56, y+22, name, 12.5, col, 700))
    s,_ = wrap(56, y+40, inv, 224, 9.8, SUB, 13); P.append(s)
    y += 60
hr(y+4)

yb = y + 28
P.append(t(40, yb, "RESULT", 13, GRN, 700))
P.append(box(40, yb+14, 545, 118, PANEL, GRN, 12, 1))
P.append(t(60, yb+52, "206,300", 32, "#7fd8b6", 700))
P.append(t(60, yb+74, "cases executed against the REAL modules · 0 violations", 10.5, SUB, 400))
s,_ = wrap(60, yb+98, "No new bugs — unlike 0.99.15, where fuzzing vectorize caught a real cv2.resize crash. These read helpers hold.", 108, 9.6, SUB, 13)
P.append(s)

P.append(t(604, yb, "WHERE IT RUNS", 13, ACC, 700))
P.append(box(604, yb+14, 536, 118, PANEL, ACC, 12, 1))
run = ["Guarded checks: skip cleanly if a module is absent.",
       "coverage.pct in the per-iteration loop (cheap, high-N).",
       "partlocate + coverage.overview sampled (DB-backed).",
       "VERIFY-099.bat runs a 3k fuzz smoke; RUN-HARDENING.bat",
       "runs the full N (--max = 1e6/property → millions)."]
yy = yb+38
for r in run:
    P.append('<circle cx="620" cy="%d" r="2.4" fill="%s"/>' % (yy-3, ACC)); P.append(t(632, yy, r, 9.6, SUB, 400)); yy += 17
hr(yb+150)

P.append(t(40, yb+178, "R1 · test-only change; no product code touched. R9 tail sentinel intact; runs host-side (mount truncates the grown harness in-sandbox).", 10, SUB, 400))
P.append(t(40, H-8, "Markup. Dark (R3). v0.99.18 · 2026-07-01 · test_property_fuzz.py +partlocate/coverage/pct. Read-only. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "122-fuzz-locator-coverage")), "bytes")
