#!/usr/bin/env python3
"""BUILT 0.66.0: OCR scan COMPLETE -> finalize the whole scan into the program (FINALIZE-OCR.bat):
refresh parts, optimize index (full type-ahead vocab + WAL), milestone backup, report, nomenclature. (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 560
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
P.append(t(40, 46, "BUILT — OCR scan COMPLETE: the full corpus wired in  (v0.66.0)", 19, TXT, 700))
P.append(t(40, 70, "The text layer has been live in search/find/collections/callouts/3D as it filled. FINALIZE-OCR.bat (host-side) locks in the now-COMPLETE scan.", 11, SUB, 400))
P.append('<line x1="40" y1="86" x2="%d" y2="86" stroke="%s"/>' % (W - 40, LINE))

# already-live row
P.append(box(40, 100, 1100, 56, PANEL, GRN, 12, 1))
P.append(t(58, 122, "ALREADY LIVE (auto-wired by the FTS trigger as OCR filled each page):", 11.5, GRN, 700))
s, _ = wrap(58, 140, "Search · Find-in-manual · Smart Collections (auto-fill + 'new' badges) · page/schematic callouts · 3D part references. Every page became searchable the moment it was OCR'd — no rebuild.", 200, 9.2, SUB, 12)
P.append(s)

def panel6(x, y, w, ic, title, color, body, metric):
    out = [box(x, y, w, 132, PANEL, LINE, 12), '<rect x="%s" y="%s" width="6" height="132" rx="3" fill="%s"/>' % (x, y, color)]
    out.append(t(x + 18, y + 23, ic + "  " + title, 12, TXT, 700))
    s, _ = wrap(x + 18, y + 44, body, int((w - 34) / 5.2), 8.7, SUB, 11); out.append(s)
    out.append(box(x + 14, y + 132 - 28, w - 28, 20, P2, color, 6, 1)); out.append(t(x + 22, y + 132 - 14, metric, 8.5, color, 700))
    return "".join(out)

y1 = 172
P.append(panel6(40, y1, 360, "1⃣", "Refresh structured parts", ACC,
    "viewer_ingest.py parts re-extracts NSN/figure/nomenclature from every now-readable RPSTL page.", "Parts index reflects the WHOLE scan."))
P.append(panel6(412, y1, 360, "2⃣", "Optimize the index", TEAL,
    "optimize_index.py rebuilds suggest_terms from the COMPLETE vocab + ANALYZE + WAL + indexes.", "Predictive type-ahead now covers everything."))
P.append(panel6(784, y1, 356, "3⃣", "Milestone backup", AMB,
    "safeguard snapshot --with-db takes a consistent copy of the finished index (+ off-disk mirror).", "The finished corpus is protected."))
y2 = 318
P.append(panel6(40, y2, 360, "4⃣", "Completion report", PUR,
    "ocr_report.py --full writes the OCR completion report (pages, coverage, engine).", "A record of the finished run."))
P.append(panel6(412, y2, 360, "5⃣", "Top nomenclatures", GRN,
    "top_nomenclature.py answers 'which part comes up most' (battery / a specific bolt / gasket ...).", "Answers the standing question #37."))
P.append(panel6(784, y2, 356, "6⃣", "Health check", RED,
    "verify_all + RPS lint confirm the additives pass and legacy parity holds after finalizing.", "Green before and after."))

P.append(box(40, 472, 1100, 56, PANEL, GRN, 12, 1))
P.append(t(58, 493, "ONE BUTTON, HOST-SIDE:  FINALIZE-OCR.bat", 11.5, GRN, 700))
s, _ = wrap(58, 511, "Runs the six steps in order on Windows (the multi-GB index can't be written from a sandbox). top_nomenclature.py verified against the fixture; FINALIZE-OCR.bat + the scripts confirmed on host. After it, the complete scan is fully leveraged across the whole program.", 200, 9, SUB, 12)
P.append(s)
P.append(t(40, H - 8, "BUILT diagram. Dark (R3). v0.66.0 · 2026-06-03 · FINALIZE-OCR.bat · top_nomenclature.py · optimize_index/viewer_ingest parts · safeguard --with-db. Additive (R1/R6).", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "80-ocr-finalize-built")), "bytes")
