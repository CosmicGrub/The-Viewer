#!/usr/bin/env python3
"""v0.99.16 — OCR status + one-click resume + daily monitor. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 700
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "OCR — status & resume   v0.99.16", 19, TXT, 700))
P.append(t(40, 70, "The scan stalled at 43.8% on June 3. ~96% of the whole library is already searchable; the gap is the remaining scanned pages.", 11.5, SUB, 400))
hr(86)

# status bar (43.8%)
P.append(t(40, 116, "SCANNED PAGES NEEDING OCR — 121,135 total", 12, ACC, 700))
bx, by, bw, bh = 40, 130, 1100, 34
P.append(box(bx, by, bw, bh, PANEL, LINE, 8, 1))
done_w = int(bw * 0.438)
P.append('<rect x="%d" y="%d" width="%d" height="%d" rx="8" fill="%s"/>' % (bx, by, done_w, bh, GRN))
P.append(t(bx+12, by+22, "53,016 done · 43.8%", 12, "#08120b", 700))
P.append(t(bx+done_w+12, by+22, "67,919 pending + 200 stale = 68,119 to go", 11, SUB, 400))

# the whole library
P.append(t(40, 196, "THE WHOLE LIBRARY — ~1.85 M pages across 39,683 documents", 12, ACC, 700))
segs = [("native text (no OCR needed)", 1727330, TEAL), ("OCR done", 53016, GRN), ("still pending", 68119, AMB)]
total = sum(s[1] for s in segs); x = 40; y2 = 210
for label, n, col in segs:
    ww = int(1100 * n / total)
    P.append(box(x, y2, max(ww, 2), 30, col, col, 4, 0))
    x += ww
P.append(t(40, 258, "1,727,330 native-text + 53,016 OCR'd = 1,780,346 searchable now (96.3%).  Remaining 68,119 scanned pages → OCR.", 10, SUB, 400))
hr(280)

# resume flow
P.append(t(40, 308, "RESUME-OCR.bat  →  run to 100% (self-restarting)", 13, GRN, 700))
steps = [("probe GPU + install", TEAL, ["RapidOCR PP-OCRv5 +", "onnxruntime-gpu; 12 workers,", "240 dpi (Acer Nitro RTX 4050)."]),
         ("requeue stale", AMB, ["cleanup resets the 200 stuck", "'running' locks back to", "'pending' so none orphan."]),
         (":ocrloop until 0", GRN, ["OCR pass; if it stops early or", "crashes, auto-restart in 8s —", "the watchdog behavior."]),
         ("report + snapshot", ACC, ["writes docs/OCR-COMPLETION-", "REPORT.md, post-run snapshot,", "opens the report."])]
x0, y0, cw, ch = 40, 322, 272, 118
cxs = []
for i, (ti, col, rows) in enumerate(steps):
    cx = x0 + i*(cw+6); cxs.append(cx)
    P.append(box(cx, y0, cw, ch, PANEL, col, 11, 1))
    P.append(t(cx+13, y0+22, ti, 11.5, col, 700))
    yy = y0+42
    for r in rows: P.append(t(cx+13, yy, r, 8.8, SUB, 400)); yy += 15
for i in range(3):
    P.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="2" marker-end="url(#a)"/>' % (cxs[i]+cw-2, y0+ch/2, cxs[i+1]+2, y0+ch/2, GRN))
P.append('<defs><marker id="a" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="%s"/></marker></defs>' % GRN)
hr(460)

P.append(t(40, 488, "MONITOR — daily task 'viewer-ocr-daily-progress' (09:08)", 13, ACC, 700))
P.append(box(40, 502, 1100, 74, PANEL, ACC, 12, 1))
s,_ = wrap(58, 526, "Reads ocr_progress_history.tsv (the runner appends to it live) + the heartbeat freshness — NOT a slow full-table scan — "
  "and pings Chris each morning with % done, pages remaining, running-vs-stalled, and a reminder to launch RESUME-OCR.bat if it stopped. "
  "At 100% it says the library is fully OCR'd and the check can be turned off.", 232, 10, SUB, 15)
P.append(s)
hr(592)

P.append(t(40, 620, "TO START: double-click RESUME-OCR.bat (plug in AC, fans high; ~15-20h GPU time, resumable). Desktop automation can't start the long run for you.", 10, AMB, 700))
P.append(t(40, H-8, "Markup. Dark (R3). v0.99.16 · 2026-07-01 · RESUME-OCR.bat + daily OCR task. Read-only on the index. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "120-ocr-resume")), "bytes")
