#!/usr/bin/env python3
"""v1.2.2 — Cheap-wins bundle: safety callouts · OCR-confidence · PDF form/attachments. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
W, H = 1160, 470
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
P.append(t(40, 46, "Cheap-wins bundle — more R12 methods, no GPU, all feed the mechanic views   v1.2.2", 17, TXT, 700))
hr(72)
P.append(panel(40, 92, 350, 170, "⚠", "cautions.py  §3.9", "#e8a06a",
               ["WARNING / CAUTION / NOTE / DANGER", "pulled as severity-ranked objects", "DANGER sorts first · cited to page",
                "/api/cautions + dossier card"], "SAFETY CALLOUTS"))
P.append(panel(405, 92, 350, 170, "🎚", "textquality.py  §9.1", TEAL,
               ["Post-hoc OCR quality score 0..1", "garbage-char · vowel-less · stray-tok", "clean / suspect / poor flag",
                "flags callouts from bad-OCR pages"], "CONFIDENCE"))
P.append(panel(770, 92, 350, 170, "📑", "pdfmeta  §5.4 / §5.5", PUR,
               ["AcroForm fields (fillable IETMs)", "embedded files (CAD/CSV inside PDF)", "folded into /api/pdfmeta",
                "fitz API verified on synthetic PDF"], "PDF-NATIVE +"))
hr(284)
P.append(t(40, 310, "Progress toward the self-standing repository (R12)", 13, TXT, 700))
P.append(box(40, 322, 1080, 118, PANEL, GRN, 12, 1))
s, _ = wrap(58, 346, "Catalog status now: §3.2 units · §3.6 leading-particulars · §3.7/3.8 thread/MIL-SPEC · §3.9 safety "
            "callouts · §5.1/5.2/5.3/5.8 PDF outline/metadata/links/annotations · §5.4/5.5 form fields/attachments — all "
            "✅; §4.9 barcodes & §9.1 OCR-confidence ◐. Every value lands in the linkless Masterfile, dual-unit and "
            "confidence-flagged, corpus authoritative. Next cheap lanes: acronym expansion (§3.10), header/footer strip "
            "(§2.6); then borderless + cross-page tables (§2.2/2.3) and the heavy ceiling (§2.4/4.6/6.2/10.1).",
            248, 10.5, SUB, 16); P.append(s)
print("PDF bytes:", render("".join(P) + "</svg>", BASE_DIR + "/141-cheap-wins"))
