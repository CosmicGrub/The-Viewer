#!/usr/bin/env python3
"""v0.99.14 — Property/fuzz hardening harness over the pure helpers. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 710
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "Hardening pass — property + fuzz over the pure helpers   v0.99.14", 19, TXT, 700))
P.append(t(40, 70, "Above-military-grade rigor: assert each pure helper's invariants hold across adversarial seeds + a million random inputs. Hypothesis if present; stdlib fuzz always.", 11.5, SUB, 400))
hr(86)

P.append(t(40, 114, "HELPER → INVARIANT THAT MUST NEVER BREAK", 13, ACC, 700))
rows = [
 ("jobcard._task_intent", "always {kind ∈ VALID | None, verb, focus:str}; never raises"),
 ("jobcard._order_procs", "length-preserving; matching-kind items STRICTLY precede non-matching; stable"),
 ("jobcard._lookalike_warning", "returns None or str; never raises"),
 ("procedures_feature._parse_procedure", "None or dict w/ all keys; EVERY reference is digit-anchored; never raises"),
 ("figureparts.parts_on", "dedup: count == len(parts) == distinct (nsn,pn,name) keys; never raises"),
 ("patterns.norm_nsn", "idempotent: norm(norm(x)) == norm(x)"),
]
y = 132
for name, inv in rows:
    P.append(box(40, y, 1100, 34, PANEL, TEAL, 8, 1))
    P.append(t(54, y+22, name, 11, "#7fbfff", 700))
    P.append(t(360, y+22, inv, 10, SUB, 400))
    y += 40
hr(y+2)

yb = y + 26
P.append(t(40, yb, "HOW IT RUNS", 13, GRN, 700))
P.append(box(40, yb+14, 545, 128, PANEL, GRN, 12, 1))
run = ["1. adversarial SEED corpus (empty, control chars, TM/WP,",
       "   'LOCKWASHER'/'LOOSEN', huge repeats) — deterministic.",
       "2. Hypothesis @given (if installed) — smart shrinking to the",
       "   minimal falsifying example.",
       "3. large-N stdlib fuzz — the bulk of the tally; --max = 1e6",
       "   iters/property → millions of cases.",
       "RUN-HARDENING.bat → docs/hardening_report.txt; 3k smoke in VERIFY-099."]
yy = yb+36
for r in run:
    P.append(t(58, yy, r, 9.4, GRN if r.startswith(("1.","2.","3.")) else SUB, 400)); yy += 16

P.append(t(604, yb, "IN-SANDBOX PROOF", 13, ACC, 700))
P.append(box(604, yb+14, 536, 128, PANEL, ACC, 12, 1))
P.append(t(622, yb+44, "80,040", 30, "#7fbfff", 700))
P.append(t(622, yb+66, "cases executed · 0 invariant violations", 10.5, SUB, 400))
P.append(t(622, yb+92, "figureparts run against the REAL module; the grown", 9.2, SUB, 400))
P.append(t(622, yb+106, "jobcard/parser helpers verified via verbatim standalone", 9.2, SUB, 400))
P.append(t(622, yb+120, "copies. Host run scales to the full million+ per property.", 9.2, SUB, 400))
hr(yb+156)

P.append(t(40, yb+184, "R1 · additive: two new test/bat files, zero product-code change. Read-only, no corpus, no network. The pre-1.0 rigor gate.", 10, SUB, 400))
P.append(t(40, H-8, "Markup. Dark (R3). v0.99.14 · 2026-07-01 · tests/test_property_fuzz.py + RUN-HARDENING.bat. Read-only. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "118-hardening")), "bytes")
