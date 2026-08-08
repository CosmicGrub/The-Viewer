#!/usr/bin/env python3
"""v1.1.4 — The Masterfile: consolidate corpus + external into one congruent dataset (no links). Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
W, H = 1200, 600
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
P.append(t(40, 46, "The Masterfile — one congruent consolidation of every dimension (no links surfaced)   v1.1.4", 17, TXT, 700))
P.append(t(40, 64, "Corpus authoritative · external only fills gaps · external web provenance kept internal (audit only)", 11, AMB, 400))
hr(80)
P.append('<defs><marker id="a" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">'
         '<path d="M0 0 L6 3 L0 6 z" fill="%s"/></marker></defs>' % SUB)
# inputs
P.append(panel(40, 100, 300, 130, "📚", "measures.db (corpus)", ACC,
               ["Authoritative measurements", "Cited to the real TM page", "The source of truth"], "AUTHORITATIVE"))
P.append(panel(40, 250, 300, 130, "🌐", "enrich.db (external)", AMB,
               ["Gap-fills from the internet", "Routed via Wayback", "web links stay INSIDE here"], "SUPPLEMENTAL"))
# consolidation
P.append(t(400, 126, "masterfile.build()", 13, TEAL, 700))
P.append(box(400, 138, 320, 250, PANEL, TEAL, 12, 1))
yy = 166
for line in ["Key everything to the authoritative subject",
             "Corpus wins: external kept ONLY for dimension types the corpus lacks",
             "RAW layer: every value (corpus + external)",
             "FILTERED layer: canonical value + range + count per dimension",
             "Strip external URLs — none enter the Masterfile"]:
    P.append('<circle cx="418" cy="%d" r="3" fill="%s"/>' % (yy-3, TEAL))
    s, n = wrap(430, yy, line, 46, 10.3, SUB, 13); P.append(s); yy += n*13 + 9
P.append('<path d="M340 165 L400 220" stroke="%s" stroke-width="2" marker-end="url(#a)"/>' % SUB)
P.append('<path d="M340 315 L400 300" stroke="%s" stroke-width="2" marker-end="url(#a)"/>' % SUB)
# outputs
P.append(panel(760, 100, 400, 130, "🗄", "index/masterfile.db  +  docs/MASTERFILE.md", PUR,
               ["master_raw + master_filtered", "one congruent, rebuildable sidecar (R1/R6)"], "THE MASTERFILE"))
P.append(panel(760, 250, 400, 130, "🖥", "/master  (no links)", GRN,
               ["Filtered: authoritative vs external", "Raw: corpus rows cite the manual page", "external rows: no link"],
               "CONSOLIDATED VIEW"))
P.append('<path d="M720 200 L760 165" stroke="%s" stroke-width="2" marker-end="url(#a)"/>' % SUB)
P.append('<path d="M960 230 L960 250" stroke="%s" stroke-width="2" marker-end="url(#a)"/>' % SUB)
hr(404)
P.append(t(40, 430, "What the reader sees", 13, TXT, 700))
P.append(box(40, 442, 1120, 130, PANEL, LINE, 12, 1))
P.append(t(58, 466, "HMMWV  —  filtered (canonical per dimension)", 11.5, TXT, 700))
rows = [("length", "180 in", "authoritative", GRN), ("weight", "7700 lb", "authoritative", GRN),
        ("capacity", "25 gal", "external · unconfirmed", AMB), ("electrical", "24 V", "external · unconfirmed", AMB)]
yy = 490
for typ, val, tag, col in rows:
    P.append(t(66, yy, typ, 10.5, SUB, 400)); P.append(t(190, yy, val, 11, "#7fd6a0" if col == GRN else "#e8c07a", 700))
    P.append(box(300, yy-13, 150, 18, P2, col, 5, 1)); P.append(t(308, yy-1, tag, 8.2, col, 700)); yy += 20
P.append(t(560, 490, "No web links. Corpus values point to the manual page;", 10.2, SUB, 400))
P.append(t(560, 506, "external values are labelled and unlinked. One file,", 10.2, SUB, 400))
P.append(t(560, 522, "congruent with the corpus and the rest of the project —", 10.2, SUB, 400))
P.append(t(560, 538, "raw + filtered, correlated to the authoritative files.", 10.2, SUB, 400))
print("PDF bytes:", render("".join(P) + "</svg>", BASE_DIR + "/136-masterfile"))
