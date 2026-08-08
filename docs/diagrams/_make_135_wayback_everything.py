#!/usr/bin/env python3
"""v1.1.3 — Route every link through the Wayback Machine; harvest from many sources. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
W, H = 1200, 620
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
P.append(t(40, 46, "Route every link through the Wayback Machine — harvest missing dimensions from many sources   v1.1.3", 17, TXT, 700))
P.append(t(40, 64, "Corpus stays authoritative · app stays offline (network only in the opt-in ENRICH.bat crawler)", 11, AMB, 400))
hr(80)
P.append('<defs><marker id="a" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">'
         '<path d="M0 0 L6 3 L0 6 z" fill="%s"/></marker></defs>' % SUB)
# link sources (left column)
P.append(t(40, 106, "① Many link sources (per gap subject)", 12.5, "#7fbfff", 700))
P.append(panel(40, 116, 330, 96, "🗄", "Internet Archive full-text", TEAL,
               ["ia_search → item text (djvu)", "high-yield, text pulled directly"], "SOURCE A"))
P.append(panel(40, 220, 330, 96, "🔎", "Web search (optional plugin)", PUR,
               ["enrich_search.py: search()→[urls]", "DuckDuckGo/Bing/… host-supplied"], "SOURCE B"))
P.append(panel(40, 324, 330, 96, "📌", "Your seed list", AMB,
               ["index/enrich_seeds.txt", "'subject | url' scoped, or global"], "SOURCE C"))
# wayback gate (center)
P.append(t(430, 106, "② The Wayback gate", 12.5, GRN, 700))
P.append(box(430, 116, 300, 304, PANEL, GRN, 12, 1))
P.append(t(450, 142, "EVERY link (B + C) is routed", 11.5, TXT, 700))
P.append(t(450, 160, "through the Wayback Machine:", 11.5, TXT, 700))
yy = 186
for line in ["availability API → closest snapshot", "if none & --save → Save Page Now",
             "fetch archived copy → strip_html", "→ pinned, permanent archived text"]:
    P.append('<circle cx="452" cy="%d" r="3" fill="%s"/>' % (yy-3, GRN))
    s, n = wrap(464, yy, line, 44, 10.2, SUB, 13); P.append(s); yy += n*13 + 8
P.append(box(446, 350, 268, 56, P2, GRN, 8, 1))
s, _ = wrap(458, 372, "Result is tied to an archived URL + snapshot timestamp — reproducible offline forever.",
            52, 9.6, "#8fd6ab", 13); P.append(s)
# extract + record (right)
P.append(t(770, 106, "③ Extract & record (gap-only)", 12.5, ACC, 700))
P.append(panel(770, 116, 390, 96, "📐", "measures.extract", ACC,
               ["Same engine as the corpus path", "value · range · tolerance · unit · type"], "EXTRACT"))
P.append(panel(770, 220, 390, 96, "🗂", "enrich.db (append-only)", PUR,
               ["Keeps ONLY missing dimension types", "Provenance: archived URL + orig URL + ts"], "RECORD"))
P.append(panel(770, 324, 390, 96, "🖥", "/measures — badged", AMB,
               ["'External — unconfirmed' block", "archived-date link + source domain"], "OFFLINE READ"))
for y in (164, 268, 372):
    P.append('<path d="M370 %d L430 %d" stroke="%s" stroke-width="2" marker-end="url(#a)"/>' % (y, 250, SUB))
P.append('<path d="M730 250 L770 164" stroke="%s" stroke-width="2" marker-end="url(#a)"/>' % SUB)
P.append('<path d="M965 212 L965 220" stroke="%s" stroke-width="2" marker-end="url(#a)"/>' % SUB)
P.append('<path d="M965 316 L965 324" stroke="%s" stroke-width="2" marker-end="url(#a)"/>' % SUB)
hr(444)
# proof band
P.append(t(40, 470, "Live-verified", 13, TXT, 700))
P.append(box(40, 482, 1120, 96, PANEL, GRN, 12, 1))
s, _ = wrap(58, 508, "Real searches (HMMWV M998, M35A2) returned spec links; the Wayback availability API confirmed an "
            "archived snapshot for every one. Pulling one archived HMMWV spec page, the measurement engine recovered "
            "34 measurements — 12 length, 11 weight, 4 capacity, plus rpm, volts/amps, speed, angle, power — each "
            "pinned to its archived source. This is exactly the missing dimensional data the corpus lacks, filled "
            "without ever modifying it.", 250, 10.5, SUB, 15); P.append(s)
print("PDF bytes:", render("".join(P) + "</svg>", BASE_DIR + "/135-wayback-everything"))
