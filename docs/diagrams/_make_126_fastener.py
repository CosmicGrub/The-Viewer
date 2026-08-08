#!/usr/bin/env python3
"""v0.99.22 — Fastener reference: thread sizes → dimensions → torque/usage. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
W, H = 1100, 520
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
P.append(t(40, 46, "Fastener reference — identify a thread   v0.99.22", 19, TXT, 700))
P.append(t(40, 70, "Major diameter (in+mm) and threads-per-inch / pitch for common UNC / UNF / ISO metric sizes — exact standard geometry — with links to torque and manual usage.", 11, SUB, 400))
hr(86)
# mini table
P.append(box(40, 110, 1020, 150, PANEL, "#7fbfff", 12, 1))
P.append(t(56, 132, "SIZE        MAJOR DIA         THREADS/PITCH     CLASS     FIND", 10.5, "#7fbfff", 700))
demo = [("1/2-13", "0.500 in · 12.70 mm", "13 TPI", "UNC", "Torque · In manuals"),
        ("3/8-16", "0.375 in · 9.53 mm", "16 TPI", "UNC", "Torque · In manuals"),
        ("M10", "0.394 in · 10.00 mm", "1.50 mm", "METRIC", "Torque · In manuals")]
yy = 158
for sz, dia, tp, cl, find in demo:
    P.append(t(56, yy, sz, 10.5, "#cfe", 700)); P.append(t(170, yy, dia, 10, SUB, 400)); P.append(t(400, yy, tp, 10, SUB, 400)); P.append(t(560, yy, cl, 10, SUB, 400)); P.append(t(680, yy, find, 10, "#4f9dff", 400)); yy += 26
P.append(t(56, yy+4, "…30+ sizes · filter by typing or by class tab (All / UNC / UNF / Metric)", 9.5, SUB, 400))
hr(280)
P.append(t(40, 308, "VERIFIED / R1", 13, GRN, 700))
P.append(box(40, 322, 1020, 140, PANEL, GRN, 12, 1))
ver = ["Geometry is exact standard (inch major-dia + TPI; metric pitch) — verifiable engineering reference.",
       "Torque is DELIBERATELY deferred to the TM (bold caveat): each row links to /torque and /?q= — never a generic chart on safety-critical joints.",
       "Client-side (offline, ES5); inline JS passes node --check. Wired: /fastener + 🔧 in palette + Tools menu + verify_ui.py.",
       "Additive & rollbackable: one page + two menu entries. Nothing writes the index (R1/R6)."]
yy = 346
for v in ver:
    P.append('<circle cx="56" cy="%d" r="2.6" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(66, yy, v, 210, 9.6, SUB, 14); P.append(s); yy += 14*n + 5
P.append(t(40, H-8, "Markup. Dark (R3). v0.99.22 · 2026-07-01 · ui/fastener.html + /fastener. Read-only. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "126-fastener")), "bytes")
