#!/usr/bin/env python3
"""v0.99.19 — Hardening the front door: fuzz the request param validator (registry.qstr/qint/qflag). Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 640
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "Hardening the front door — fuzz the param validator   v0.99.19", 19, TXT, 700))
P.append(t(40, 70, "Every route parses user query params through registry.qstr/qint/qflag. Contract: bad input → 400, NEVER a 500. Proved it holds under 878k adversarial cases.", 11.5, SUB, 400))
hr(86)

# flow: bad input -> ParamError -> 400
P.append(t(40, 114, "THE GUARANTEE", 13, ACC, 700))
boxes = [("adversarial query", AMB, ["?n=abc  ?limit=9…40 digits", "?doc=- 5  ?page=٣ (unicode)", "?x=1_000  ?q=1;DROP TABLE", "empty / [None] / multi-value"]),
         ("qstr / qint / qflag", TEAL, ["central param parsing +", "clamping (lo/hi, ABS_MAX).", "int() guarded; type coerced."]),
         ("ParamError → 400", GRN, ["malformed input becomes a", "clean 400 — the server never", "throws an uncontrolled 500."])]
x0, y0, cw, ch = 40, 128, 340, 118
cxs = []
for i, (ti, col, rows) in enumerate(boxes):
    cx = x0 + i*(cw+30); cxs.append(cx)
    P.append(box(cx, y0, cw, ch, PANEL, col, 11, 1))
    P.append(t(cx+15, y0+24, ti, 12.5, col, 700))
    yy = y0+46
    for r in rows: P.append(t(cx+15, yy, r, 9.2, SUB, 400)); yy += 15
for i in range(2):
    P.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="2" marker-end="url(#a)"/>' % (cxs[i]+cw+2, y0+ch/2, cxs[i+1]-2, y0+ch/2, TEAL))
P.append('<defs><marker id="a" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="%s"/></marker></defs>' % TEAL)
hr(272)

yb = 300
P.append(t(40, yb, "RESULT", 13, GRN, 700))
P.append(box(40, yb+14, 545, 108, PANEL, GRN, 12, 1))
P.append(t(60, yb+52, "878,583", 32, "#7fd8b6", 700))
P.append(t(60, yb+74, "adversarial cases · 0 leaks (nothing but ParamError escaped)", 10, SUB, 400))
s,_ = wrap(60, yb+96, "qint always returns a bounded int · qstr str-or-None · qflag bool. No user input can 500 the server.", 108, 9.6, SUB, 13)
P.append(s)

P.append(t(604, yb, "WHY IT MATTERS", 13, ACC, 700))
P.append(box(604, yb+14, 536, 108, PANEL, ACC, 12, 1))
s,_ = wrap(622, yb+44, "This is an OFFLINE search engine that takes arbitrary NSNs, part numbers and free text from mechanics. The param "
  "front door being crash-proof means a fat-fingered query, a copy-paste with junk, or a malformed link degrades to a "
  "clean 400 message — never a stack-trace / 500. That's the 'above military grade' robustness bar applied to the input layer.", 232, 9.8, SUB, 14)
P.append(s)
hr(yb+138)

P.append(t(40, yb+166, "R1 · test-only; no product code touched. Guarded (skips if module absent). Runs host-side (VERIFY-099 smoke + RUN-HARDENING full). R9 sentinel intact.", 10, SUB, 400))
P.append(t(40, H-8, "Markup. Dark (R3). v0.99.19 · 2026-07-01 · test_property_fuzz.py + registry qstr/qint/qflag. Read-only. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "123-fuzz-params")), "bytes")
