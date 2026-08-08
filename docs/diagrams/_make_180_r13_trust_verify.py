#!/usr/bin/env python3
"""v1.8.0 R13 trust layer: validation/quarantine, integrity/backup, human sign-off + audit, TM currency, verification cockpit + accuracy. Dark (R2/R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1240, 940
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
def card(x, y, w, hh, col, ti, rows, tisz=12):
    P.append(box(x, y, w, hh, PANEL, LINE, 11, 1)); P.append('<rect x="%d" y="%d" width="5" height="%d" rx="2.5" fill="%s"/>' % (x, y, hh, col))
    P.append(t(x+16, y+22, ti, tisz, col, 700)); yy = y+42
    for r in rows: P.append(t(x+16, yy, r, 9, SUB, 400)); yy += 15

P.append(t(40, 48, "THE VIEWER v1.8.0 — R13 trust layer: validate · integrity · sign-off · TM currency · verify cockpit", 17, TXT, 700))
P.append(t(40, 74, "R13 (above military grade): raise the TRUST, VERIFICATION, and RESILIENCE of the whole app. Additive/rollbackable (R1); append-only audit; no new deps.", 11, SUB, 400))
hr(90)

# 1 trust & accuracy
P.append(t(40, 118, "1  TRUST & ACCURACY", 13, GRN, 700))
card(40, 130, 380, 120, RED, "validate.py  ->  /api/validate", [
 "physical-plausibility + OCR-garble checks", "on every extracted value:",
 "  quarantine = impossible/garbled (HELD)", "  suspect   = unusual (flagged)",
 "wired into /part: bad data is WITHHELD"])
card(430, 130, 380, 120, TEAL, "trust.py  (one canonical level)", [
 "high  = authoritative + corroborated", "medium= single cite   review= disagreement",
 "low   = external      quarantined = failed", "        validation",
 "so a trust chip means the same everywhere"])
card(820, 130, 380, 120, AMB, "defense-in-depth accuracy", [
 "conflicts.py  -> cross-MANUAL disagreement", "validate.py   -> physical plausibility",
 "two independent checks; disagreement is", "SURFACED, never silently resolved.",
 "(cross-method agreement = follow-up)"])
hr(266)

# 2 verification measurable
P.append(t(40, 294, "2  VERIFICATION MADE MEASURABLE", 13, ACC, 700))
card(40, 306, 575, 108, ACC, "verifystate.py  ->  /verify  (cockpit)", [
 "reads the last host-side VERIFY-099 log + the 39-module self-test roster",
 "+ which sidecars are built + DB-integrity status -> ONE 'what have we",
 "proven?' view. Verification you can't see is verification you won't keep green."])
card(625, 306, 575, 108, GRN, "tests/test_accuracy.py", [
 "MEASURED extraction accuracy vs a hand-verified ground-truth set:",
 "recall / precision with a regression FLOOR. You cannot claim 'above",
 "military grade' without measuring it. Wired into VERIFY-099."])
hr(430)

# 3 human authority
P.append(t(40, 458, "3  HUMAN AUTHORITY & AUDITABILITY", 13, PUR, 700))
card(40, 470, 575, 112, PUR, "signoff.py  ->  /review  (SME sign-off)", [
 "low-confidence value -> review queue -> an expert APPROVES / REJECTS /",
 "OVERRIDES -> verified & locked. The store is APPEND-ONLY: every action is",
 "a new event, nothing is updated or deleted -> a permanent who/what/when",
 "audit trail. extracted -> HUMAN-VERIFIED."])
card(625, 470, 575, 112, TEAL, "tmrev.py  ->  /api/tmrev  (TM currency)", [
 "parses a manual's CHANGE number + date; flags when a NEWER revision of",
 "the same TM exists in the corpus, so no one works from a superseded book.",
 "'Is this the current manual?' answered authoritatively.",
 "change number dominates; date breaks ties."])
hr(598)

# 4 resilience
P.append(t(40, 626, "4  RESILIENCE", 13, AMB, 700))
card(40, 638, 1160, 92, AMB, "integrity.py  ->  /api/integrity", [
 "SQLite corruption detection (integrity_check) · SHA-256 tamper-evidence · a file manifest that catches change/corruption ·",
 "ONLINE-safe backup (a consistent snapshot even while the DB is in use). The index and sidecars are the app's memory —",
 "they must never be silently corrupted or lost. Surfaced in the verification cockpit; complements the off-disk safeguard mirror."])
hr(746)

# footer notes
P.append(t(40, 774, "THE POSTURE (R13)", 13, GRN, 700))
notes = [
 ("Never shown as fact", RED, "A garbled or impossible value is quarantined and withheld — the mechanic sees an honest 'held for review', not a wrong number."),
 ("Human vouches", PUR, "A machine extracts; only an SME verifies. Approvals are permanent and auditable — the record can always be reconstructed."),
 ("Proven, not assumed", ACC, "Every module self-tested; accuracy measured against ground truth; the cockpit makes the proof state visible and keeps it green."),
 ("Never lose data", AMB, "Corruption is detected, tampering is evident, and a consistent backup is one call away. Read-only over the corpus (R6)."),
]
ny, nx0, ncw, nch = 788, 40, 575, 66
for i,(ti,col,de) in enumerate(notes):
    cx = nx0 + (i%2)*(ncw+10); cy = ny + (i//2)*(nch+10)
    P.append(box(cx, cy, ncw, nch, PANEL, col, 12, 1)); P.append(t(cx+16, cy+22, ti, 11.5, col, 700))
    s,_=wrap(cx+16, cy+40, de, 156, 9.0, SUB, 11); P.append(s)

P.append(box(40, 906, 1160, 28, PANEL, GRN, 10, 1))
P.append(t(58, 924, "R13 above-military-grade (governs all) · R1 rollbackable · R4 CHANGELOG [1.8.0] · R9 VERIFY-099 (6 modules + accuracy) · append-only audit · VERSION=1.8.0.", 8.8, SUB, 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "180-r13-trust-verify")), "bytes")
