#!/usr/bin/env python3
"""v1.3.3 — Figure vision: callout-number OCR, symbol detection, VLM interface. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
W, H = 1160, 470
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
P.append(t(40, 46, "Figure vision — callouts · symbols · vision-language interface   v1.3.3", 17, TXT, 700))
hr(72)
P.append(panel(40, 92, 350, 168, "🔢", "callouts.py  §4.5", ACC,
               ["read numeric callout labels (Tesseract)", "with their positions", "link callout → leader line (dimscan)",
                "ties figure number → RPSTL part", "/api/callouts"], "CALLOUT OCR"))
P.append(panel(405, 92, 350, 168, "🔺", "symbols.py  §4.8/4.11", TEAL,
               ["template-match schematic components", "+ safety symbols (⚠ hazard)", "non-max suppression",
                "templates in index/symbols/", "no training, no GPU"], "SYMBOL DETECT"))
P.append(panel(770, 92, 350, 168, "🧠", "vlm.py  §10.1", PUR,
               ["ask a page image a question", "pluggable backend (drop-in)", "GPU model host-side (Qwen-VL/Donut)",
                "degrades cleanly if absent", "/api/vlm"], "VISION-LANGUAGE ◐"))
hr(282)
P.append(t(40, 308, "Catalog essentially complete on the non-GPU span (R12)", 13, TXT, 700))
P.append(box(40, 320, 1080, 116, PANEL, GRN, 12, 1))
s, _ = wrap(58, 344, "✅ done: §1.3/1.8 OCR prep · §2.2/2.3/2.4/2.6 tables+layout+cleanup · §3.2/3.6-3.11 semantic · "
            "§4.5/4.8/4.11 figure vision · §5.1-5.5/5.8 PDF-native · §6.2 IETM · §7.1/7.4/7.5 dedup+graph+cross-val. "
            "◐ (real capability, heavier step host-side): §4.6 dimension geometry, §4.9 barcodes, §9.1 OCR-confidence, "
            "§10.1 vision-language (interface ready — add a GPU model). The remaining ○ are only minor niceties "
            "(§5.6 layers, §5.7 glyph remap, §6.1 publog expand, §9.5 review queue). The repository stands on its own.",
            250, 10.5, SUB, 16); P.append(s)
print("PDF bytes:", render("".join(P) + "</svg>", BASE_DIR + "/146-figure-vision"))
