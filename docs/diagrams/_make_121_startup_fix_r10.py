#!/usr/bin/env python3
"""v0.99.17 — Offline startup fix + version banner + R10 iteration-snapshot dashboard. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 710
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "Offline startup fix · version banner · R10 snapshot   v0.99.17", 19, TXT, 700))
P.append(t(40, 70, "Fixed the launch hang on the offline machine, corrected the stale version, and built the visual per-iteration snapshot Chris asked for.", 11.5, SUB, 400))
hr(86)

# FIX 1
P.append(t(40, 112, "[FIX] startup hung on pip retries (offline)", 13, "#e0564f", 700))
P.append(box(40, 126, 545, 150, PANEL, "#e0564f", 12, 1))
b = ["run_app.bat ran `pip install --upgrade pip` on EVERY launch →",
     "ConnectionResetError(10054), retry x4 — hangs when offline.",
     "FIX: one `import fitz, reportlab, PIL` gate; touch the network",
     "ONLY if a package is missing (then --timeout 8 --retries 1).",
     "Same guard applied to run_ocr_auto/gpu/ocr/enrich/indexing.",
     "Normal launch now: 'All present -- no network touched'."]
yy = 150
for x in b:
    P.append('<circle cx="56" cy="%d" r="2.4" fill="%s"/>' % (yy-3, "#e0564f")); s, n = wrap(66, yy, x, 110, 9.6, SUB, 13); P.append(s); yy += 13*n + 5

# FIX 2
P.append(t(604, 112, "[FIX] version banner was stale", 13, AMB, 700))
P.append(box(604, 126, 536, 150, PANEL, AMB, 12, 1))
P.append(t(624, 156, "engine/viewer_app.py", 11, SUB, 400))
P.append(t(624, 182, 'VERSION = "0.98.0"', 13, "#e0564f", 700))
P.append(t(624, 204, "→", 13, SUB, 400))
P.append(t(650, 204, 'VERSION = "0.99.17"', 13, GRN, 700))
s,_ = wrap(624, 232, "The running app printed v0.98.0 while the changelog was at 0.99.16 — a snapshot-vs-changelog mismatch. Bumped to match; the app VERSION now tracks the changelog top (per R10).", 108, 9.6, SUB, 14)
P.append(s)
hr(292)

# R10
P.append(t(40, 320, "[FEATURE] R10 — the iteration snapshot (visual, matches the changelog EXACTLY)", 13, "#7fbfff", 700))
P.append(box(40, 334, 545, 170, PANEL, "#7fbfff", 12, 1))
r = ["New rule R10: every iteration ships a comprehensive, VISUAL snapshot",
     "of every change — tagged [FEATURE] [UPGRADE] [POLISH] [FIX] — so Chris",
     "can see & confirm changes iteration-to-iteration.",
     "engine/build_iteration_snapshot.py DERIVES it from CHANGELOG.md, so it",
     "matches by construction (amended: MUST match, no exceptions) — it even",
     "self-asserts every changelog version is present. Wired into VERIFY-099.",
     "Outputs: docs/ITERATION-SNAPSHOTS.md + docs/ITERATION-DASHBOARD.html."]
yy = 358
for x in r:
    P.append('<circle cx="56" cy="%d" r="2.3" fill="%s"/>' % (yy-3, "#7fbfff")); s, n = wrap(66, yy, x, 110, 9.4, SUB, 13); P.append(s); yy += 13*n + 4

# dashboard mock
bx, by, bw, bh = 604, 334, 536, 170
P.append(box(bx, by, bw, bh, PANEL, "#7fbfff", 12, 1.3))
P.append(t(bx+16, by+24, "ITERATION-DASHBOARD.html", 12, "#7fbfff", 700))
P.append(t(bx+16, by+42, "149 iterations · 88 legacy · matches CHANGELOG.md", 9.5, SUB, 400))
# filter chips
chips = [("All", "#e6edf4"), ("Feature", "#4f9dff"), ("Upgrade", "#caa24a"), ("Polish", "#1d9e75"), ("Fix", "#e0564f")]
cx = bx+16
for lab, col in chips:
    wct = 20 + len(lab)*6
    P.append(box(cx, by+52, wct, 18, "#16202b", col, 999, 1)); P.append(t(cx+7, by+65, lab, 8.4, col, 600)); cx += wct+6
# a sample card
P.append(box(bx+16, by+80, bw-32, 74, "#0f151c", LINE, 8, 1))
P.append(t(bx+28, by+98, "0.99.17  2026-07-01  Offline startup fix + R10", 9.6, "#7fbfff", 700))
P.append(box(bx+28, by+106, 54, 15, "#12314f", "#12314f", 4, 0)); P.append(t(bx+34, by+117, "FEATURE", 7.6, "#8fc0ff", 700))
P.append(box(bx+88, by+106, 30, 15, "#3a1512", "#3a1512", 4, 0)); P.append(t(bx+94, by+117, "FIX", 7.6, "#f2a49c", 700))
P.append(t(bx+28, by+138, "search · filter by tag · link to each diagram · legacy parity", 8.6, SUB, 400))
hr(520)

P.append(t(40, 548, "VERIFIED / R1", 13, GRN, 700))
P.append(box(40, 562, 1100, 96, PANEL, GRN, 12, 1))
ver = ["Generator run: 149 iterations, 88 with legacy parity, 11 with diagram links; R10 integrity OK -- all 149 CHANGELOG versions present.",
       "Snapshot MATCHES the changelog by construction (derived from it); verbatim '(...)'/'[...]' in old entries are real text, not truncation.",
       "Outputs structurally complete: ITERATION-SNAPSHOTS.md ends with the tail sentinel, DASHBOARD.html closes cleanly (R9).",
       "Additive & rollbackable: bat guards + one VERSION constant + one generator + two generated docs. Nothing writes the index (R1/R6)."]
yy = 584
for v in ver:
    P.append('<circle cx="56" cy="%d" r="2.6" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(66, yy, v, 224, 9.3, SUB, 13); P.append(s); yy += 13*n + 4

P.append(t(40, H-8, "Markup. Dark (R3). v0.99.17 · 2026-07-01 · run_app.bat offline-safe · VERSION 0.99.17 · R10 dashboard. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "121-startup-fix-r10")), "bytes")
