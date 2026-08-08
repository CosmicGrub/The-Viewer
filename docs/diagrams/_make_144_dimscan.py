#!/usr/bin/env python3
"""v1.3.1 — Rotation-aware dimension-line scanner. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
W, H = 1160, 440
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
P.append(t(40, 46, "Rotation-aware dimension-line scanner — the spatial-data marquee   v1.3.1", 17, TXT, 700))
hr(72)
P.append(panel(40, 92, 340, 150, "📐", "dimscan.py  §4.6", ACC,
               ["OpenCV Canny + probabilistic Hough", "finds leader/dimension lines at ANY angle",
                "classify H / V / diagonal (rotated)"], "GEOMETRY (no GPU)"))
P.append(panel(400, 92, 340, 150, "🔎", "locate numbers in context", TEAL,
               ["each line → where its dimension text sits", "even rotated/vertical callouts",
                "host-side OCR reads the number"], "§4.6 host step"))
P.append(panel(760, 92, 360, 150, "🧩", "→ Masterfile dimension", PUR,
               ["value tied to the feature it measures", "dual-unit + confidence flagged",
                "/api/dimscan?doc=&page="], "SPATIAL DATA"))
P.append('<defs><marker id="a" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">'
         '<path d="M0 0 L6 3 L0 6 z" fill="%s"/></marker></defs>' % SUB)
for x1, x2 in [(380, 400), (740, 760)]:
    P.append('<path d="M%d 167 L%d 167" stroke="%s" stroke-width="2" marker-end="url(#a)"/>' % (x1, x2, SUB))
hr(264)
P.append(t(40, 290, "Where the catalog stands after this autonomous push", 13, TXT, 700))
P.append(box(40, 302, 1080, 110, PANEL, GRN, 12, 1))
s, _ = wrap(58, 326, "✅ done: §2.2/2.3/2.6 tables+cleanup · §3.2/3.6-3.11 semantic extractors · §5.1-5.5/5.8 PDF-native · "
            "§6.2 IETM/S1000D · §7.4 knowledge graph.  ◐ partial: §4.9 barcodes (QR now), §9.1 OCR-confidence, §4.6 "
            "dimension geometry (number-OCR host-side).  ○ remaining (need GPU/heavy models, host-side): §4.5 "
            "callout-number OCR (easyocr), §2.4 full layout analysis (LayoutParser), §10.1 vision-language page QA. "
            "The repository now answers on its own across the whole cheap+structural span (R12).", 250, 10.5, SUB, 16)
P.append(s)
print("PDF bytes:", render("".join(P) + "</svg>", BASE_DIR + "/144-dimscan"))
