#!/usr/bin/env python3
"""v0.99.21 — My Bench: pin parts/pages you're working. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
W, H = 1100, 520
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
P.append(t(40, 46, "My Bench — pin what you're working on   v0.99.21", 19, TXT, 700))
P.append(t(40, 70, "A localStorage favorites space: pin a dossier / procedure / torque / figure and jump back instantly. Delivered via palette.js → on every page, no per-page edits.", 11, SUB, 400))
hr(86)
P.append(t(40, 118, "HOW IT WORKS", 13, ACC, 700))
P.append(box(40, 132, 1020, 150, PANEL, ACC, 12, 1))
rows = ["On any page, the ☆ pin pill (bottom-right, beside ⌘K jump) saves {url, title, query} to localStorage 'viewer_bench'.",
        "/bench lists your pinned items — open (new tab), remove, or clear the bench.",
        "★ My Bench is a command in the Ctrl+K palette; the whole thing rides palette.js so it reaches all 20+ pages.",
        "ES5-safe + persists across sessions; excluded on home and on /bench itself."]
yy = 158
for r in rows:
    P.append('<circle cx="56" cy="%d" r="2.6" fill="%s"/>' % (yy-3, ACC)); s, n = wrap(66, yy, r, 210, 10, SUB, 15); P.append(s); yy += 15*n + 6
hr(300)
P.append(t(40, 328, "VERIFIED / R1", 13, GRN, 700))
P.append(box(40, 342, 1020, 120, PANEL, GRN, 12, 1))
ver = ["bench.html inline JS passes node --check; pin/list/remove all localStorage, no backend.",
       "☆ pin pill + ★ My Bench command added to palette.js (reaches every page); /bench in _PAGES + verify_ui.py.",
       "Additive & rollbackable: one page + palette additions. Nothing writes the index (R1/R6)."]
yy = 366
for v in ver:
    P.append('<circle cx="56" cy="%d" r="2.6" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(66, yy, v, 210, 9.6, SUB, 14); P.append(s); yy += 14*n + 5
P.append(t(40, H-8, "Markup. Dark (R3). v0.99.21 · 2026-07-01 · ui/bench.html + ☆ pin pill. Read-only. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "125-bench")), "bytes")
