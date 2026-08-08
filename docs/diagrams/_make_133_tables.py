#!/usr/bin/env python3
"""v1.1.1 — Structured-table extraction (RPSTL / spec / leading-particulars). Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
W, H = 1180, 520
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
P.append(t(40, 46, "Structured-table extraction — jump straight to the spec numbers   v1.1.1", 19, TXT, 700))
hr(70)
P.append(panel(40, 92, 260, 156, "📄", "PDF page", ACC,
               ["Every page of every manual", "Ruled tables detected by geometry", "Read-only on the corpus (R1)"],
               "SOURCE"))
P.append(panel(320, 92, 300, 156, "🔎", "PyMuPDF find_tables", TEAL,
               ["Recovers cells → rows/cols", "RPSTL · torque · PMCS grids", "Leading-particulars / SPEC tables",
                "Degrades to [] if fitz absent"],
               "tables.extract_page()"))
P.append(panel(640, 92, 250, 156, "📐", "_units_in() via measures", AMB,
               ["Flatten cells → run measures", "If cells carry units → SPEC table", "Records which dimension types"],
               "SPEC FLAG"))
P.append(panel(910, 92, 230, 156, "🗂", "/api/tables + tables.db", PUR,
               ["On-the-fly per doc+page", "BUILD-TABLES.bat → sidecar", "Append-only (R1/R6)"],
               "OUTPUT"))
for x1, x2 in [(300, 320), (620, 640), (890, 910)]:
    P.append('<path d="M%d 170 L%d 170" stroke="%s" stroke-width="2" marker-end="url(#a)"/>' % (x1, x2, SUB))
P.append('<defs><marker id="a" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">'
         '<path d="M0 0 L6 3 L0 6 z" fill="%s"/></marker></defs>' % SUB)
hr(268)
# example
P.append(t(40, 296, "Worked example — a spec table becomes queryable numbers", 13, TXT, 700))
P.append(box(40, 310, 520, 150, PANEL, LINE, 12, 1))
rows = [["ITEM", "DIMENSION", "UNIT"], ["Overall length", "180", "in"], ["Curb weight", "5200", "lb"]]
yy = 336
for i, r in enumerate(rows):
    col = TXT if i == 0 else SUB
    P.append(t(60, yy, r[0], 11, col, 700 if i == 0 else 400))
    P.append(t(320, yy, r[1], 11, col, 700 if i == 0 else 400))
    P.append(t(440, yy, r[2], 11, col, 700 if i == 0 else 400))
    yy += 26
P.append(t(60, 448, "→ flagged SPEC · units {length, weight}", 10.5, TEAL, 700))
P.append(box(600, 310, 540, 150, PANEL, GRN, 12, 1))
s, _ = wrap(618, 336, "Why it matters: dimensional data in TMs lives in leading-particulars / specification tables that OCR "
            "flattens into unstructured text. Recovering the table structure — and flagging the ones that carry units — "
            "lets a mechanic land directly on the numbers instead of reading prose. Pairs with /measures.",
            116, 10.5, SUB, 15)
P.append(s)
P.append(t(40, 496, "Additive & rollbackable (R1). Self-test extracts a 3×3 spec table and flags it (host-side) — PASS.", 10, SUB, 400))
print("PDF bytes:", render("".join(P) + "</svg>", BASE_DIR + "/133-tables"))
