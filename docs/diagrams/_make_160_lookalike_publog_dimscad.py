#!/usr/bin/env python3
"""v1.6.0 data-flow: authoritative look-alike intelligence from PUBLOG + approximate 3-D from dimensions. Dark (R2/R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1240, 950
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
def arrow(x1, y1, x2, y2, col=SUB):
    P.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1.6" marker-end="url(#ah)"/>' % (x1, y1, x2, y2, col))
P.append('<defs><marker id="ah" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto">'
         '<path d="M0,0 L7,3 L0,6 Z" fill="%s"/></marker></defs>' % SUB)

P.append(t(40, 50, "THE VIEWER v1.6.0 — Look-alike intelligence from PUBLOG + approximate 3-D  (data flow)", 19, TXT, 700))
P.append(t(40, 76, "Two same-name parts become a decisive answer; every part gets a dimensional 3-D sketch. Additive & rollbackable (R1); read-only (R6).", 11.5, SUB, 400))
hr(92)

# ---- foundation ----
P.append(t(40, 118, "FOUNDATION — extended build_publog.py loads five more FLIS tables", 13, ACC, 700))
tbl = [("V_FLIS_STANDARDIZATION", "ISC + related NSN (I&S)"), ("V_MOE_RULE", "AAC (obsolescence)"),
       ("V_FLIS_PHRASE", "TECH_DOC_NBR (→ manual)"), ("V_H6_RELATED", "related item names"), ("P_CAGE.status", "vendor active?")]
x = 40
for nm, de in tbl:
    P.append(box(x, 130, 228, 52, PANEL, LINE, 9, 1)); P.append(t(x+12, 150, nm, 9.5, ACC, 700)); P.append(t(x+12, 168, de, 9, SUB)); x += 232
hr(196)

# ---- publogdiff bundles ----
P.append(t(40, 224, "publogdiff.py  —  /api/publogdiff (two parts)  ·  /api/publog_intel (one part)", 13, TEAL, 700))
cards = [
 ("1 · DIFF + FINGERPRINT", GRN, ["align characteristics by MRC,", "highlight only differing rows,", "score % identical (fit-fingerprint)"]),
 ("2 · INTERCHANGE VERDICT", AMB, ["GREEN interchangeable (I&S family)", "AMBER one-way substitute (supersede)", "RED not interchangeable + reason;", "substitutes + AAC obsolescence"]),
 ("3 · REF# + VENDOR", ACC, ["decode RNCC/RNVC: exact vs", "'similar, may differ';", "flag inactive-vendor variants", "via CAGE status"]),
 ("4 · CROSSLINK + NICKNAME", PUR, ["TECH_DOC_NBR → the manual;", "colloquial + related names;", "WARN on nickname clashes;", "/binaudit shelf scan"]),
]
x0, y0, cw, ch = 40, 238, 285, 116
for i, (ti, col, rows) in enumerate(cards):
    cx = x0 + i*(cw+8)
    P.append(box(cx, y0, cw, ch, PANEL, LINE, 10, 1))
    P.append('<rect x="%d" y="%d" width="5" height="%d" rx="2.5" fill="%s"/>' % (cx, y0, ch, col))
    P.append(t(cx+16, y0+22, ti, 10.5, col, 700))
    yy = y0+42
    for r in rows: P.append(t(cx+16, yy, r, 8.7, SUB, 400)); yy += 15
hr(372)

# ---- surfaces ----
P.append(t(40, 400, "WHERE IT SHOWS", 13, GRN, 700))
surf = [("/publog", ACC, "supersession · substitutes · vendors · tech-docs · nicknames cards + a '⇄ Compare' box (two-part diff + verdict)."),
        ("/binaudit", PUR, "scan a shelf of NSNs (hand scanner drops them in) → flags look-alike GROUPS + superseded/obsolete items."),
        ("/dossier", TEAL, "authoritative Federal-catalog card + the approximate-model card (below).")]
sy = 414
for ti, col, de in surf:
    P.append(box(40, sy, 1160, 40, PANEL, col, 10, 1)); P.append(t(56, sy+25, ti, 11, col, 700))
    s, _ = wrap(180, sy+25, de, 210, 9.6, SUB, 12); P.append(s); sy += 48
hr(566)

# ---- dimscad ----
P.append(t(40, 594, "5 · APPROXIMATE 3-D / CAD FROM DIMENSIONS  —  dimscad.py  ·  /api/dimscad", 13, AMB, 700))
P.append(box(40, 606, 260, 92, PANEL, LINE, 10, 1)); P.append(t(56, 630, "PUBLOG characteristics", 11, TXT, 700))
P.append(t(56, 650, "'OVERALL LENGTH' → 3.00 IN", 9, SUB)); P.append(t(56, 665, "'DIAMETER' → .50 IN", 9, SUB)); P.append(t(56, 680, "(named dimensions parsed)", 9, SUB))
arrow(300, 652, 350, 652, AMB)
P.append(box(350, 606, 260, 92, PANEL, AMB, 10, 1)); P.append(t(366, 630, "pick primitive", 11, AMB, 700))
P.append(t(366, 650, "cylinder / box / washer / hex", 9, SUB)); P.append(t(366, 665, "from item name + which dims", 9, SUB)); P.append(t(366, 680, "are present", 9, SUB))
arrow(610, 652, 660, 652, GRN)
P.append(box(660, 606, 260, 92, PANEL, GRN, 10, 1)); P.append(t(676, 630, "dimensioned iso SVG", 11, GRN, 700)); P.append(t(676, 650, "+ parametric OBJ mesh", 9, SUB)); P.append(t(676, 665, "(?obj=1) → 3-D library", 9, SUB)); P.append(t(676, 680, "(localmodel.py)", 9, SUB))
arrow(920, 652, 970, 652, GRN)
P.append(box(970, 606, 230, 92, PANEL, LINE, 10, 1)); P.append(t(986, 630, "dossier card", 11, TXT, 700)); P.append(t(986, 650, "'Approximate model", 9, SUB)); P.append(t(986, 665, "(from dimensions)'", 9, SUB)); P.append(t(986, 680, "— a sketch, not the figure", 9, "#6b7280"))
hr(712)

# ---- degrade + rollback ----
P.append(t(40, 740, "GRACEFUL DEGRADE & ROLLBACK", 13, GRN, 700))
notes = [
 ("PUBLOG not built", ACC, "Every /api/publog* + the cards say so and the app is unchanged. BUILD-PUBLOG.bat (now 5 more tables) builds it."),
 ("Sparse data", AMB, "Missing ISC → verdict falls back to a characteristics-closeness estimate; missing dims → 'not enough' note. Never fabricates."),
 ("Authoritative, no links", TEAL, "PUBLOG is the official part-identity source; corpus stays authoritative for procedures. Offline, no links (R11)."),
 ("Rollback (R1)", PUR, "Delete publogdiff.py / dimscad.py + their routes/cards — each removes cleanly with zero impact on the rest."),
]
ny, nx0, ncw, nch = 754, 40, 575, 72
for i,(ti,col,de) in enumerate(notes):
    cx = nx0 + (i%2)*(ncw+10); cy = ny + (i//2)*(nch+10)
    P.append(box(cx, cy, ncw, nch, PANEL, col, 12, 1)); P.append(t(cx+16, cy+23, ti, 12, col, 700))
    s,_=wrap(cx+16, cy+42, de, 152, 9.2, SUB, 12); P.append(s)

P.append(box(40, 906, 1160, 34, PANEL, GRN, 12, 1))
P.append(t(58, 928, "R1 rollbackable · R2 this diagram · R3 dark+PDF · R4 CHANGELOG [1.6.0] · R5 changelog-visual · R6 read-only · R7 legacy [1.6.0-legacy] · R9 VERIFY-099 (publogdiff/dimscad) · VERSION=1.6.0.", 9.0, SUB, 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "160-lookalike-publog-dimscad")), "bytes")
