#!/usr/bin/env python3
"""v0.99.11 — Discoverability: revive the command palette + Tools menu + ?q deep-link. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 700
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "Discoverability — the palette was dead; now it opens everywhere   v0.99.11", 19, TXT, 700))
P.append(t(40, 70, "Everything built this session was reachable only by typing the URL. Fix: revive Ctrl+K (it loaded on NO page), and surface the tools in the menu.", 11.5, SUB, 400))
hr(86)

# before / after
P.append(t(40, 112, "THE BUG", 13, "#e06b5a", 700))
P.append(box(40, 126, 545, 150, PANEL, "#e06b5a", 12, 1))
bug = ["palette.js existed + /palette.js was served — but NO html page included it.",
       "So 'press Ctrl+K anywhere' (in the Help link) did literally nothing.",
       "Its 'Search' action went to /?ex= — a param the home page never reads,",
       "so even when opened, searching from the palette silently did nothing.",
       "Net effect: a whole command palette shipped dark for weeks."]
yy = 150
for b in bug:
    P.append('<circle cx="56" cy="%d" r="2.4" fill="%s"/>' % (yy-3, "#e06b5a")); s, n = wrap(66, yy, b, 108, 9.6, SUB, 13); P.append(s); yy += 13*n + 6

P.append(t(604, 112, "THE FIX", 13, GRN, 700))
P.append(box(604, 126, 536, 150, PANEL, GRN, 12, 1))
fix = ["Added <script src=\"/palette.js\"> to home + 8 tool pages (solve, procedure,",
       "  dossier, partdiff, locate, coverage, jobcard, deepzoom). Ctrl+K now opens.",
       "Search action → /?q=, plus a home ?q= deep-link handler in palette.js that",
       "  prefills #q and calls runSearch — /?q=<query> actually runs now.",
       "verify_ui.py now node --checks palette.js + deepzoom.js host-side too."]
yy = 150
for f in fix:
    ind = f.startswith("  ")
    if not ind: P.append('<circle cx="620" cy="%d" r="2.4" fill="%s"/>' % (yy-3, GRN))
    s, n = wrap(634 if ind else 630, yy, f.strip(), 108, 9.6, SUB if ind else TXT, 13); P.append(s); yy += 13*n + 6
hr(292)

# what's now discoverable
P.append(t(40, 320, "NOW REACHABLE IN ONE KEYSTROKE (Ctrl+K) OR THE 🧰 TOOLS MENU", 13, ACC, 700))
tools = [("🔎 Search", AMB), ("🧭 Find a part", TEAL), ("📋 Dossier", ACC), ("🧾 Work Order", GRN),
         ("🔧 How-to", AMB), ("🔍 Look-Alike", TEAL), ("🛠 Solve it", ACC), ("📈 Coverage", GRN),
         ("⚡ Circuit Lab", AMB), ("🧊 3-D", TEAL), ("📐 Schematics", ACC), ("➕ Add docs", GRN),
         ("📊 Ops", AMB), ("🔤 OCR status", TEAL), ("❔ Help", ACC)]
x = 40; y = 340; cw = 176
for i, (lb, col) in enumerate(tools):
    cx = 40 + (i % 5) * (cw + 4); cy = 340 + (i // 5) * 40
    P.append(box(cx, cy, cw, 32, PANEL, col, 8, 1)); P.append(t(cx+12, cy+21, lb, 11, col, 600))
hr(470)

P.append(t(40, 498, "VERIFIED / R1", 13, GRN, 700))
P.append(box(40, 512, 1100, 150, PANEL, GRN, 12, 1))
ver = ["Root cause found by grepping every ui/*.html: palette.js referenced by 0 pages (only mentioned in help.html text).",
       "palette.js read host-authoritatively: 129 lines, IIFE balanced/closed; new commands + /?q= + deep-link handler present.",
       "Script includes confirmed on host via the Read tool (jobcard L95, solve L152, …). Sandbox grep lagged (mount cache) — host is truth.",
       "verify_ui.py extended: node --check of palette.js + deepzoom.js added to VERIFY-099.bat (host-side, since the mount truncates grown files).",
       "Additive & rollbackable: pure <script> includes + palette rows + one Tools-menu group + one ?q handler. Nothing writes the index (R1/R6)."]
yy = 534
for v in ver:
    P.append('<circle cx="56" cy="%d" r="2.6" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(66, yy, v, 224, 9.2, SUB, 13); P.append(s); yy += 13*n + 4

P.append(t(40, H-8, "Markup. Dark (R3). v0.99.11 · 2026-07-01 · palette.js revived + wired · Tools menu · /?q= deep-link. Read-only. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "115-discoverability")), "bytes")
