#!/usr/bin/env python3
"""v0.99.23 — PMCS finder: jump to the maintenance-check tables by vehicle. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
W, H = 1100, 540
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
P.append(t(40, 46, "PMCS finder — the maintenance-check tables, fast   v0.99.23", 19, TXT, 700))
P.append(t(40, 70, "Find Preventive Maintenance Checks & Services tables by vehicle, with the interval each page covers, each cited to its real page.", 11, SUB, 400))
hr(86)
# result mock
P.append(box(40, 110, 1020, 128, PANEL, "#7fbfff", 12, 1))
P.append(t(56, 132, "HMMWV M998 · TM 9-2320-280-10 · p.40", 12, "#cfe", 700))
P.append(box(500, 120, 90, 16, "#16202b", "#2f4858", 6, 1)); P.append(t(510, 132, "view page ↗", 8.4, "#4f9dff", 400))
for i, iv in enumerate(["Before operation", "During operation", "After operation", "Weekly"]):
    cx = 56 + i*135
    P.append(box(cx, 144, 128, 18, "#123a2c", "#1d9e75", 999, 1)); P.append(t(cx+8, 157, iv, 8.6, "#7fd8b6", 400))
s,_ = wrap(56, 182, "“TABLE 2-1. PREVENTIVE MAINTENANCE CHECKS AND SERVICES. Interval: BEFORE, DURING, AFTER, WEEKLY. Item: engine oil level…”", 210, 10, "#cdd8e4", 15); P.append(s)
P.append(t(56, 226, "+ intervals inferred: Monthly / Annually on continuation pages.", 9.5, SUB, 400))
hr(258)
P.append(t(40, 286, "HOW / VERIFIED / R1", 13, GRN, 700))
P.append(box(40, 300, 1020, 168, PANEL, GRN, 12, 1))
ver = ["pmcs.find(): FTS-match ('preventive maintenance checks' OR PMCS OR 'checks and services'); dedup by doc+page; infer interval from text.",
       "Vehicle filters on documents.vehicle LIKE — NOT the page body. A self-test caught the original body-FTS bug (vehicle isn't in the body) and it was fixed.",
       "Verified in-sandbox on a synthetic FTS index: HMMWV → 2 PMCS pages w/ correct intervals; wrong vehicle → 0; no-vehicle → all.",
       "/api/pmcs + /pmcs page + 🗓 in palette + Tools menu; pmcs.py in audit + VERIFY-099 + verify_ui. Read-only on the index (R1/R6)."]
yy = 324
for v in ver:
    P.append('<circle cx="56" cy="%d" r="2.6" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(66, yy, v, 210, 9.6, SUB, 14); P.append(s); yy += 14*n + 5
P.append(t(40, H-8, "Markup. Dark (R3). v0.99.23 · 2026-07-01 · pmcs.py + /api/pmcs + /pmcs. Read-only. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "127-pmcs")), "bytes")
