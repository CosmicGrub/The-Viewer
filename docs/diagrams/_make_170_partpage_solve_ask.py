#!/usr/bin/env python3
"""v1.7.0 data-flow: unified part page + job PDF, guided troubleshooting + conflict checker, offline Q&A + read-aloud, command center. Dark (R2/R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1240, 960
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 50, "THE VIEWER v1.7.0 — Part page + job PDF · guided troubleshooting · offline Q&A · command center", 18, TXT, 700))
P.append(t(40, 76, "App-wide, high-leverage: one pane per part, a printable job package, symptom-to-fix trees, a safety conflict check, cited offline answers, and hands-free help. R1 rollbackable · R6 read-only · no new deps.", 11, SUB, 400))
hr(92)

def card(x, y, w, hh, col, ti, rows, tisz=12):
    P.append(box(x, y, w, hh, PANEL, LINE, 11, 1))
    P.append('<rect x="%d" y="%d" width="5" height="%d" rx="2.5" fill="%s"/>' % (x, y, hh, col))
    P.append(t(x+16, y+22, ti, tisz, col, 700)); yy = y+42
    for r in rows: P.append(t(x+16, yy, r, 9, SUB, 400)); yy += 15

# ---- 1 unified part page + job pdf ----
P.append(t(40, 120, "1  ONE AUTHORITATIVE PART PAGE  (/part)  +  COMPLETE JOB-PACKAGE PDF", 13, GRN, 700))
card(40, 132, 366, 118, GRN, "/part  ->  /api/partsummary", [
 "ONE call fuses: identity + supersession", "alert · parts-to-order · key dims ·", "torque · cautions · procedure ·",
 "approx 3-D model · CONFLICT banner", "(a fast bay-floor single pane)"])
P.append(t(423, 190, "->", 20, SUB, 700))
card(452, 132, 366, 118, ACC, "jobpack.py  ->  /api/jobpack", [
 "the COMPLETE printable package:", "identity + PUBLOG + alerts + parts +", "dims + torque + cautions + full",
 "procedure, all cited -> one PDF.", "buttons on /part and /dossier"])
P.append(t(835, 190, "->", 20, SUB, 700))
card(864, 132, 336, 118, TEAL, "the mechanic", [
 "opens /part, scans the alerts,", "prints the package, walks to", "the bay with everything cited —",
 "no hunting across pages."])
hr(266)

# ---- 2 troubleshooting + conflicts ----
P.append(t(40, 294, "2  GUIDED TROUBLESHOOTING  +  CROSS-MANUAL CONFLICT CHECK", 13, AMB, 700))
card(40, 306, 575, 112, AMB, "faulttree.py  ->  /troubleshoot", [
 "parses MALFUNCTION -> (STEP n) TEST OR INSPECTION -> CORRECTIVE ACTION",
 "out of the OCR text into interactive DECISION TREES: pick a symptom,",
 "step the checks, land on the fix -> procedure / part. Cited to the page.",
 "Self-tested on the real Army TM troubleshooting format."])
card(625, 306, 575, 112, RED, "conflicts.py  ->  /api/conflicts  (SAFETY)", [
 "gathers a part's measured values across the corpus and flags where two",
 "MANUALS DISAGREE on a torque / pressure / dimension — each value cited,",
 "severity-ranked. Shown as a red banner on /part.",
 "Verified: 35 vs 50 ft-lb across 2 docs -> flagged HIGH."])
hr(434)

# ---- 3 offline Q&A + read-aloud ----
P.append(t(40, 462, "3  OFFLINE CITED Q&A  +  HANDS-FREE", 13, PUR, 700))
card(40, 474, 575, 112, PUR, "ask.py  ->  /ask   (extractive, no LLM, no network)", [
 "retrieve pages (semantic embeddings + keyword FTS) -> return the exact",
 "ANSWERING SENTENCES verbatim, each with its manual + page. Nothing is",
 "invented; it surfaces the lines a mechanic would read.",
 "Verified: 'bleed the CTIS lines' -> TM-B p.44."])
card(625, 474, 575, 112, ACC, "readaloud.js   (auto-injected app-wide)", [
 "native SpeechSynthesis reads any page ALOUD (greasy-hands friendly) +",
 "voice input on the search box (SpeechRecognition, best-effort).",
 "Fully offline; both degrade silently if the browser lacks the API.",
 "A '🔊 read' pill + a '🎤' mic appear where supported."])
hr(602)

# ---- 4 command center + hardening ----
P.append(t(40, 630, "4  COMMAND CENTER  +  HARDENING", 13, TEAL, 700))
card(40, 642, 575, 108, TEAL, "/command  ->  /api/command_status", [
 "one 'are we complete?' cockpit: OCR % · corpus coverage ·",
 "PUBLOG build state · Masterfile dimensional gaps.",
 "Best-effort aggregate — one missing sidecar can't break it.",
 "Points you at RESUME-OCR / BUILD-PUBLOG when incomplete."])
card(625, 642, 575, 108, GRN, "tests/test_newmodules.py  (property/fuzz)", [
 "hammers publogdiff · dimscad · conflicts · faulttree · ask ·",
 "hybrid · jobpack with random & hostile inputs; asserts NO crash",
 "+ invariants. Verified 0 crashes over 3,000+ cases/target;",
 "wired into VERIFY-099 (4,000/target host-side)."])
hr(766)

# ---- degrade + rollback ----
P.append(t(40, 794, "GRACEFUL DEGRADE & ROLLBACK", 13, GRN, 700))
notes = [
 ("Everything cites the page", ACC, "Part page, job PDF, troubleshooting, and Q&A all deep-link the cited TM page. The manual stays the source of truth."),
 ("Nothing invented", PUR, "The assistant is EXTRACTIVE — verbatim sentences from the corpus, never generated. Empty when the corpus has no answer."),
 ("Coverage-aware", AMB, "Sections fill in as OCR completes; the command center shows how far along everything is and what to build next."),
 ("Rollback (R1)", TEAL, "Each new page/module + its route removes cleanly. No schema changes; read-only over the existing indexes."),
]
ny, nx0, ncw, nch = 808, 40, 575, 66
for i,(ti,col,de) in enumerate(notes):
    cx = nx0 + (i%2)*(ncw+10); cy = ny + (i//2)*(nch+10)
    P.append(box(cx, cy, ncw, nch, PANEL, col, 12, 1)); P.append(t(cx+16, cy+22, ti, 11.5, col, 700))
    s,_=wrap(cx+16, cy+40, de, 156, 9.0, SUB, 11); P.append(s)

P.append(box(40, 924, 1160, 30, PANEL, GRN, 10, 1))
P.append(t(58, 943, "R1 rollbackable · R2 this diagram · R3 dark+PDF · R4 CHANGELOG [1.7.0] · R5 changelog-visual · R6 read-only · R7 legacy · R9 VERIFY-099 (jobpack/conflicts/faulttree/ask + fuzz) · VERSION=1.7.0.", 8.8, SUB, 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "170-partpage-solve-ask")), "bytes")
