#!/usr/bin/env python3
"""BUILT 0.72.1: answering "which part nomenclature comes up THE MOST" — host-side ranking + one-click bat. (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 540
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
P.append(t(40, 46, "BUILT — most-common part nomenclature  (v0.72.1)", 19, TXT, 700))
P.append(t(40, 70, "Now that the whole corpus is OCR'd, rank every cited part and answer: which one comes up THE MOST — by name, by exact NSN, and by official FLIS name.", 11, SUB, 400))
P.append('<line x1="40" y1="86" x2="%d" y2="86" stroke="%s"/>' % (W - 40, LINE))
P.append(panel(40, 108, 360, 196, "\U0001F522", "Three rankings", ACC,
  ["Headline: most-common NOMENCLATURE — the cited RPSTL item / figure name (BOLT, GASKET, ...).",
   "Most-common EXACT NSN — the single physical part that recurs the most, with vehicle spread.",
   "Optional --flis: the official FLIS item name (INC -> H6) for the top NSNs, joined from PUB LOG."],
  "Name, exact part, and official name."))
P.append(panel(412, 108, 360, 196, "\U0001F5B1", "One double-click", TEAL,
  ["ANSWER-MOST-COMMON-PART.bat runs it on the live index, prints the answer, and opens the result.",
   "Saves index/MOST-COMMON-PART.txt — copy the >>> ANSWER line straight back.",
   "Read-only open (mode=ro + query_only; immutable fallback) — safe to run while OCR / the app is live."],
  "No command line needed."))
P.append(panel(784, 108, 356, 196, "\U0001F4BD", "Why on the PC", AMB,
  ["The live index is 3.65 GB (891,556 x 4 KB pages per its own header).",
   "The dev sandbox mount serves it ~14.5 MB short (~3,500 pages) — SQLite reads that as 'malformed'.",
   "So this single number is computed on the machine that holds the whole file; the file itself is fine."],
  "Truncating mount can't, your PC can."))
P.append(box(40, 320, 1100, 86, PANEL, GRN, 12, 1))
P.append(t(58, 342, "VERIFIED (logic) + host run pending", 11.5, GRN, 700))
s, _ = wrap(58, 362, "Ranking SQL fixture-tested in isolation: headline nomenclature ('BOLT, MACHINE'), per-NSN frequency excluding nulls, COALESCE name fallback, and distinct vehicle/NSN counts all correct. The number itself comes from your run — double-click the bat; it reads index\\viewer.db host-side (where it is coherent) and writes index\\MOST-COMMON-PART.txt.", 200, 9, SUB, 12)
P.append(s)
P.append(box(40, 414, 1100, 60, PANEL, PUR, 12, 1))
s, _ = wrap(58, 435, "Additive (R1/R6): a new bat + an enhanced read-only script — no schema/route/corpus changes; the old `python top_nomenclature.py` call still works. Optional FLIS join is name-only and read-only against PUB LOG CSVs.", 200, 9, SUB, 12)
P.append(s)
P.append(t(40, H - 8, "BUILT diagram. Dark (R3). v0.72.1 · 2026-06-03 · engine/top_nomenclature.py (+3 views, save-to-txt, --flis) · ANSWER-MOST-COMMON-PART.bat. Additive (R1).", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "87-most-common-nomenclature-built")), "bytes")
