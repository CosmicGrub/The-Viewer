#!/usr/bin/env python3
"""v1.9.0: serviceability/go-no-go, torque-sequence diagrams, kit/BOM, connector pinouts, learn/quiz, field notes. Dark (R2/R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1240, 800
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
def card(x, y, w, hh, col, ti, rows):
    P.append(box(x, y, w, hh, PANEL, LINE, 11, 1)); P.append('<rect x="%d" y="%d" width="5" height="%d" rx="2.5" fill="%s"/>' % (x, y, hh, col))
    P.append(t(x+16, y+22, ti, 11.5, col, 700)); yy = y+42
    for r in rows: P.append(t(x+16, yy, r, 9, SUB, 400)); yy += 15

P.append(t(40, 48, "THE VIEWER v1.9.0 — serviceability & safety graphics · kit/BOM · wiring pinouts · training · field notes", 16.5, TXT, 700))
P.append(t(40, 74, "Built under R13. Additive/rollbackable (R1); read-only except the append-only notes sidecar; no new deps. Every new pure module self-tested.", 11, SUB, 400))
hr(90)

P.append(t(40, 116, "SERVICEABILITY & SAFETY GRAPHICS", 12.5, RED, 700))
card(40, 128, 575, 108, RED, "serviceability.py -> /api/serviceability", [
 "extracts SERVICEABLE / WEAR limits (min/max, 'replace if',", "not-to-exceed) distinct from nominal + a GO/NO-GO checker:",
 "measured value -> serviceable / marginal / REPLACE.",
 "verified: 0.475 vs 0.480 min => replace. On /part."])
card(625, 128, 575, 108, AMB, "torqueseq.py -> /api/torqueseq", [
 "detects star / criss-cross / sequential pattern + staged torque",
 "values; renders a NUMBERED bolt-pattern diagram (number =",
 "tightening order). The 'what order do I torque' safety graphic.",
 "star_order(8) = 1,5,2,6,3,7,4,8. On /part."])
hr(250)

P.append(t(40, 278, "LOGISTICS  ·  WIRING", 12.5, GRN, 700))
card(40, 290, 575, 100, GRN, "bom.py -> /api/bom  (complete kit)", [
 "one deduped, categorized KIT: parts (+qty) + consumables",
 "(gaskets/seals/O-rings/cotter pins/lube, flagged from the",
 "procedure) + tools. Folded into the job-package PDF. On /part."])
card(625, 290, 575, 100, ACC, "pinouts.py -> /api/pinouts  (wiring)", [
 "extracts CONNECTOR PINOUTS + WIRE COLORS ('J5 pin B = ground,",
 "white/black') so continuity is checked at the right pins.",
 "(symptom->circuit fault isolation = noted follow-up)"])
hr(404)

P.append(t(40, 432, "PEOPLE  (young + seasoned mechanics)", 12.5, PUR, 700))
card(40, 444, 575, 100, PUR, "training.py -> /learn  (cited quiz)", [
 "multiple-choice questions from real corpus values with plausible",
 "distractors; every answer links to the page to LEARN from.",
 "reproducible with a seed. Builds knowledge against the TMs."])
card(625, 444, 575, 100, TEAL, "fieldnotes.py -> /api/notes  (audit trail)", [
 "cited field-note TIPS on a part/procedure, on the SAME append-only",
 "audit store; an SME ENDORSES a tip so young mechanics see which",
 "are vouched for. institutional knowledge that compounds. On /part."])
hr(558)

P.append(t(40, 586, "R13 POSTURE", 12.5, GRN, 700))
notes = [
 ("Know when to replace", RED, "Nominal size isn't safety — the serviceable limit is. Go/no-go answers 'is this part still good?' with the cited limit."),
 ("Right order, right kit", AMB, "Torque-sequence diagrams + a complete kit list mean the job is done in the right order with everything on hand."),
 ("Learn from the source", PUR, "The quiz is built from cited values and links back to the page — a young mechanic learns the manual, not a guess."),
 ("Knowledge, vouched for", TEAL, "Field tips are captured with an append-only trail and SME endorsement — nothing anonymous is presented as truth."),
]
ny, nx0, ncw, nch = 600, 40, 575, 66
for i,(ti,col,de) in enumerate(notes):
    cx = nx0 + (i%2)*(ncw+10); cy = ny + (i//2)*(nch+10)
    P.append(box(cx, cy, ncw, nch, PANEL, col, 12, 1)); P.append(t(cx+16, cy+22, ti, 11.5, col, 700))
    s,_=wrap(cx+16, cy+40, de, 156, 9.0, SUB, 11); P.append(s)

P.append(box(40, 770, 1160, 22, PANEL, GRN, 8, 1))
P.append(t(58, 785, "R13 above-military-grade · R1 rollbackable · R4 CHANGELOG [1.9.0] · R9 VERIFY-099 (6 modules) · append-only notes · VERSION=1.9.0.", 8.6, SUB, 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "190-serviceability-kit-training")), "bytes")
