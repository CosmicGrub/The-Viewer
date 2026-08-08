#!/usr/bin/env python3
"""v0.99.20 — Torque quick-reference page + ft-lb/in-lb/N·m converter. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 650
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "Torque quick-reference   v0.99.20", 19, TXT, 700))
P.append(t(40, 70, "Torque is safety-critical and looked up constantly — but it had no page (only buried in procedures/Work Order). New /torque surfaces it, with a unit converter.", 11.5, SUB, 400))
hr(86)

# mock of the page
bx, by, bw, bh = 40, 110, 1100, 250
P.append(box(bx, by, bw, bh, PANEL, "#7fbfff", 12, 1.2))
P.append(t(bx+18, by+28, "🔩 Torque quick-reference", 14, "#7fbfff", 700))
# converter
P.append(box(bx+18, by+42, 520, 78, "#10151c", "#223", 10, 1))
P.append(t(bx+30, by+62, "Converter — ft-lb · in-lb · N·m", 10.5, "#7fbfff", 600))
for i,(v,u) in enumerate([("30","ft-lb"),("360","in-lb"),("40.67","N·m")]):
    cx=bx+30+i*165
    P.append(box(cx, by+72, 150, 34, "#16202b", "#26333f", 8, 1))
    P.append(t(cx+12, by+90, v, 15, "#cfe", 700)); P.append(t(cx+12, by+102, u, 8.5, SUB, 400))
# a cited spec
P.append(box(bx+18, by+130, bw-36, 96, "#10151c", "#223", 10, 1))
P.append(t(bx+32, by+152, "30–35 ft-lb", 15, GRN, 700))
P.append(t(bx+150, by+152, "= 360…420 in-lb · 40.67…47.45 N·m", 10.5, SUB, 400))
s,_ = wrap(bx+32, by+172, "“Tighten the alternator mounting bolts to 30-35 ft-lb in the sequence shown.”", 224, 10, "#cdd8e4", 14); P.append(s)
P.append(t(bx+32, by+206, "HMMWV M998 · TM 9-2320-280-24P · p.215", 9.5, SUB, 400))
P.append(box(bx+330, by+196, 82, 16, "#16202b", "#2f4858", 6, 1)); P.append(t(bx+340, by+208, "view page ↗", 8.4, "#4f9dff", 400))
hr(376)

P.append(t(40, 404, "WHAT IT DOES", 13, ACC, 700))
P.append(box(40, 418, 545, 118, PANEL, ACC, 12, 1))
rows = ["Search a part / NSN / fastener → every cited torque value",
        "(from /api/torque), each with context + page citation that",
        "opens the real page in Deep-Zoom.",
        "Live converter + per-result conversion to the other two units.",
        "Parses '30–35 ft-lb', '18 in-lb', '45 N·m' (ranges handled)."]
yy = 442
for r in rows: P.append(t(58, yy, r, 9.8, SUB, 400)); yy += 18

P.append(t(604, 404, "VERIFIED / R1", 13, GRN, 700))
P.append(box(604, 418, 536, 118, PANEL, GRN, 12, 1))
ver = ["inline JS passes node --check; math verified (30 ft-lb = 40.67 N·m = 360 in-lb).",
       "FOUND & FIXED a parse bug: unit normalizer didn't strip the '·' in N·m → 45 N·m returned null.",
       "Wired: /torque in _PAGES · 🔩 in palette + Tools menu · in verify_ui.py. Citations → /deepzoom.",
       "Additive & rollbackable: one page + one route + two menu entries. No index writes (R1/R6)."]
yy = 440
for v in ver:
    P.append('<circle cx="620" cy="%d" r="2.4" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(632, yy, v, 226, 9.2, SUB, 13); P.append(s); yy += 13*n + 3

P.append(t(40, H-8, "Markup. Dark (R3). v0.99.20 · 2026-07-01 · ui/torque.html + /torque + converter. Read-only. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "124-torque")), "bytes")
