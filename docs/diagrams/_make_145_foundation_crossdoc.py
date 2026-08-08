#!/usr/bin/env python3
"""v1.3.2 — OCR pre-processing, layout analysis, edition dedup, cross-validation. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
W, H = 1180, 470
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
P.append(t(40, 46, "Sharper foundation + connected methods   v1.3.2", 17, TXT, 700))
hr(72)
P.append(panel(40, 92, 265, 168, "🧼", "ocrprep.py  §1.3/1.8", ACC,
               ["deskew (8° → 0)", "denoise · Otsu binarize", "orientation (OSD)", "better OCR input"], "PRE-OCR"))
P.append(panel(320, 92, 265, 168, "🗺", "layout.py  §2.4", TEAL,
               ["title/heading/para/caption", "header/footer/figure", "from PyMuPDF blocks (no ML)",
                "reading order · /api/layout"], "LAYOUT"))
P.append(panel(600, 92, 265, 168, "🧬", "dedup.py  §7.1", AMB,
               ["word-shingle fingerprints", "Jaccard clustering", "same TM diff change# → cluster",
                "prefer latest · de-dupe hits"], "EDITIONS"))
P.append(panel(880, 92, 265, 168, "🤝", "crossval.py  §7.5", PUR,
               ["measures + tables + IETM agree", "→ confidence up (3-way=1.0)", "disagreements → conflict flag",
                "feeds Masterfile confidence"], "AGREEMENT"))
hr(282)
P.append(t(40, 308, "R12 progress — foundation & cross-document lanes done", 13, TXT, 700))
P.append(box(40, 320, 1100, 112, PANEL, GRN, 12, 1))
s, _ = wrap(58, 344, "✅ now spans §1.3/1.8 (OCR prep), §2.2/2.3/2.4/2.6 (tables + layout + cleanup), §3.2/3.6-3.11 "
            "(semantic), §5.1-5.5/5.8 (PDF-native), §6.2 (IETM), §7.1/7.4/7.5 (dedup, graph, cross-validation). ◐: §4.6 "
            "dimension geometry, §4.9 QR, §9.1 OCR-confidence. Remaining ○ are the last vision pieces: §4.5 "
            "callout-number OCR + §4.8 symbol detection (next wave), and §10.1 vision-language QA (GPU/host model). "
            "The self-standing repository is nearly feature-complete on the non-VLM span (R12).", 252, 10.5, SUB, 16)
P.append(s)
print("PDF bytes:", render("".join(P) + "</svg>", BASE_DIR + "/145-foundation-crossdoc"))
