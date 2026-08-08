#!/usr/bin/env python3
"""v1.5.0 data-flow: PUBLOG/FLIS catalog · hand-scanner & camera · hybrid search · exploded/assembly. Dark (R2/R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1240, 940
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
def arrow(x1, y1, x2, y2, col=SUB):
    P.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1.6" marker-end="url(#ah)"/>' % (x1, y1, x2, y2, col))
P.append('<defs><marker id="ah" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto">'
         '<path d="M0,0 L7,3 L0,6 Z" fill="%s"/></marker></defs>' % SUB)

P.append(t(40, 50, "THE VIEWER v1.5.0 — PUBLOG catalog · scanner · hybrid search · exploded view  (data flow)", 19, TXT, 700))
P.append(t(40, 76, "Five lanes: the official DLA federal catalog, hand-scanner + camera scan-in, smarter retrieval, and an interactive assembly walkthrough. "
                   "Additive & rollbackable (R1); corpus + PUBLOG CSVs read-only (R6).", 11.5, SUB, 400))
hr(92)

# ---- LANE 1: PUBLOG ----
P.append(t(40, 120, "1  PUBLOG / FLIS  —  ~16 GB official CSV export  ->  authoritative offline part identity", 13, ACC, 700))
P.append(box(40, 132, 250, 78, PANEL, LINE, 10, 1)); P.append(t(56, 156, "DLA PUBLOG export", 11, TXT, 700))
P.append(t(56, 176, "P_FLIS_NSN · V_FLIS_PART", 9, SUB)); P.append(t(56, 190, "V_CHARACTERISTICS · P_CAGE …", 9, SUB))
arrow(290, 171, 340, 171, ACC)
P.append(box(340, 132, 250, 78, PANEL, ACC, 10, 1)); P.append(t(356, 156, "build_publog.py (HOST)", 11, ACC, 700))
P.append(t(356, 176, "row-stream -> index/publog.db", 9, SUB)); P.append(t(356, 190, "NIIN-keyed · indexes after load", 9, SUB))
arrow(590, 171, 640, 171, ACC)
P.append(box(640, 132, 250, 78, PANEL, TEAL, 10, 1)); P.append(t(656, 156, "publog.py  /api/publog", 11, TEAL, 700))
P.append(t(656, 176, "NSN/NIIN lookup + reverse", 9, SUB)); P.append(t(656, 190, "by part number (?pn=)", 9, SUB))
arrow(890, 171, 940, 171, TEAL)
P.append(box(940, 132, 260, 78, PANEL, GRN, 10, 1)); P.append(t(956, 156, "/publog + dossier card", 11, GRN, 700))
P.append(t(956, 176, "item · part#s + CAGE · charx", 9, SUB)); P.append(t(956, 190, "weight/cube · replaced-by", 9, SUB))
hr(226)

# ---- LANE 2: scanner ----
P.append(t(40, 254, "2  SCAN A PART  —  hand scanner (any page) or camera  ->  the catalog", 13, PUR, 700))
P.append(box(40, 266, 360, 74, PANEL, PUR, 10, 1)); P.append(t(56, 290, "Hand scanner — scanner.js", 11, PUR, 700))
s,_=wrap(56, 310, "keyboard-wedge burst+Enter detected on EVERY page (injected by palette.js) -> routes NSN or part# to lookup", 74, 9.3, SUB, 12); P.append(s)
P.append(box(420, 266, 360, 74, PANEL, ACC, 10, 1)); P.append(t(436, 290, "Camera — /scan", 11, ACC, 700))
s,_=wrap(436, 310, "native BarcodeDetector (offline): QR/Code128/39/EAN/DataMatrix -> same lookup; graceful fallback + manual entry", 74, 9.3, SUB, 12); P.append(s)
arrow(780, 303, 830, 303, GRN)
P.append(box(830, 266, 370, 74, PANEL, GRN, 10, 1)); P.append(t(846, 290, "-> /publog?nsn= or ?pn=", 11, GRN, 700))
s,_=wrap(846, 310, "NSN -> catalog record; otherwise reverse part-number lookup. Scan a bin label, land on the part.", 76, 9.3, SUB, 12); P.append(s)
hr(356)

# ---- LANE 3: hybrid ----
P.append(t(40, 384, "3  HYBRID + GLOSSARY SEARCH  —  smarter retrieval, each signal degrades on its own", 13, AMB, 700))
P.append(box(40, 396, 300, 92, PANEL, AMB, 10, 1)); P.append(t(56, 418, "hybrid.py", 11, AMB, 700))
for i,txt in enumerate(["1) glossary/acronym query expand", "2) RRF fuse keyword + semantic", "3) fuzzy NSN 'did you mean'", "   (grounded in PUBLOG)"]):
    P.append(t(56, 438+i*15, txt, 9, SUB))
arrow(340, 442, 390, 442, AMB)
P.append(box(390, 396, 300, 92, PANEL, LINE, 10, 1)); P.append(t(406, 418, "signals", 11, TXT, 700))
P.append(t(406, 440, "keyword (FTS) — always", 9, GRN)); P.append(t(406, 456, "semantic — if embeddings built", 9, SUB))
P.append(t(406, 472, "NSN suggest — if PUBLOG built", 9, SUB))
arrow(690, 442, 740, 442, GRN)
P.append(box(740, 396, 460, 92, PANEL, GRN, 10, 1)); P.append(t(756, 418, "/api/search_hybrid  +  home hints bar", 11, GRN, 700))
s,_=wrap(756, 440, "fused results; the main /api/search now also annotates acronym expansions + NSN did-you-mean WITHOUT changing ranking (safe, additive).", 96, 9.3, SUB, 13); P.append(s)
hr(504)

# ---- LANE 4: exploded ----
P.append(t(40, 532, "4  EXPLODED / ASSEMBLY VIEW  (/exploded)  —  a figure becomes a step-through walkthrough", 13, TEAL, 700))
P.append(box(40, 544, 1160, 96, PANEL, TEAL, 12, 1))
comp = [("figure image", "/page"), ("hotspots", "/api/callout_numbers (+iw/ih)"),
        ("assembly order", "/api/figureparts"), ("dimensions", "/api/dimscan"), ("find a figure", "/api/locate")]
x=58
for lab, ep in comp:
    P.append(box(x, 560, 210, 34, P2, TEAL, 8, 1)); P.append(t(x+12, 581, lab, 10, TXT, 700)); x+=224
s,_=wrap(58, 616, "One page composes them: numbered callout hotspots over the figure + an ordered parts panel you step through; "
                  "toggle DISASSEMBLY to reverse the order and overlay dimension lines. Each step deep-links to the part's dossier / how-to / catalog.", 224, 9.4, SUB, 13); P.append(s)
hr(658)

# ---- graceful degrade + rollback ----
P.append(t(40, 686, "GRACEFUL DEGRADE & ROLLBACK (unchanged doctrine)", 13, GRN, 700))
notes = [
 ("PUBLOG", ACC, "Not built? /api/publog + the dossier card say so and the app is unchanged. BUILD-PUBLOG.bat builds index/publog.db."),
 ("Scanner", PUR, "Pure ES5 + native BarcodeDetector. No camera / old browser? Hand scanner + manual entry still work."),
 ("Hybrid", AMB, "No embeddings -> keyword+glossary+NSN only. Never worse than the base keyword search; ranking untouched on /api/search."),
 ("Exploded", TEAL, "No callout OCR on the host? Shows the ordered parts panel without hotspots. Rollback = delete the page + module; zero impact."),
]
ny, nx0, ncw, nch = 700, 40, 575, 74
for i,(ti,col,de) in enumerate(notes):
    cx = nx0 + (i%2)*(ncw+10); cy = ny + (i//2)*(nch+10)
    P.append(box(cx, cy, ncw, nch, PANEL, col, 12, 1)); P.append(t(cx+16, cy+24, ti, 12, col, 700))
    s,_=wrap(cx+16, cy+44, de, 150, 9.3, SUB, 12); P.append(s)

P.append(box(40, 862, 1160, 40, PANEL, GRN, 12, 1))
P.append(t(58, 887, "R1 additive/rollbackable · R2 this diagram · R3 dark+PDF · R4 CHANGELOG [1.5.0] · R5 changelog-visual · R6 read-only corpus+CSVs · "
                    "R7 legacy [1.5.0-legacy] · R9 tail sentinel + VERIFY-099 (publog/build_publog/hybrid) · VERSION=1.5.0.", 9.0, SUB, 400))
P.append(t(40, H-8, "Dark (R3). 2026-07-02 · build_publog.py · publog.py · scanner.js · /scan · hybrid.py · /exploded · /api/{publog,search_hybrid,callout_numbers iw/ih}.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "150-publog-scanner-search")), "bytes")
