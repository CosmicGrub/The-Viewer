#!/usr/bin/env python3
"""v0.99.13 — Feature audit + palette QoL (Recent + discoverability pill). Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 700
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "Feature audit + palette QoL   v0.99.13", 19, TXT, 700))
P.append(t(40, 70, "A self-check that catches the palette-was-dead class of bug forever, plus two quality-of-life wins that reach all 19 pages from one file.", 11.5, SUB, 400))
hr(86)

P.append(t(40, 114, "audit_features.py  —  what it cross-checks (host-side)", 13, ACC, 700))
P.append(box(40, 128, 545, 200, PANEL, ACC, 12, 1))
checks = ["[1] every registered page + served script has a FILE (no 404 routes).",
          "[2] every served script is REFERENCED by some page/asset — the exact",
          "     check that would have caught palette.js (served, included nowhere).",
          "[3] orphan pages: ui/*.html with no route (unreachable / oversight).",
          "[4] broken internal links: href/fetch → a route that doesn't exist.",
          "[5] every features/*.py + top-level module still imports.",
          "",
          "RESULT on the real tree: 0 FAIL — 0 dead scripts, 0 orphans,",
          "0 broken links, all modules import. Wired into VERIFY-099.bat +",
          "AUDIT.bat -> docs/feature_audit.txt."]
yy = 152
for c in checks:
    if c:
        col = GRN if c.startswith("RESULT") else SUB
        P.append(t(58, yy, c, 9.4, col, 700 if c.startswith("RESULT") else 400))
    yy += 16

# QoL: palette mock with Recent + pill
bx, by, bw, bh = 604, 128, 536, 200
P.append(box(bx, by, bw, bh, PANEL, "#7fbfff", 12, 1.3))
P.append(t(bx+16, by+24, "palette.js QoL  (Ctrl+K, all 19 pages)", 12.5, "#7fbfff", 700))
P.append(box(bx+16, by+38, bw-32, 24, "#0c1116", "#2b333f", 6, 1)); P.append(t(bx+26, by+54, "type a part / task…", 9.5, SUB, 400))
P.append(t(bx+22, by+78, "RECENT", 8.5, "#9aa6b6", 700))
for i, r in enumerate(["🕘  Work Order — “alternator”", "🕘  Look-Alike Parts — “valve”", "🕘  Deep Zoom — p.214"]):
    P.append(t(bx+26, by+95+i*17, r, 9.6, TXT, 400))
P.append(t(bx+22, by+150, "GO TO", 8.5, "#9aa6b6", 700))
P.append(t(bx+26, by+166, "🔎 Search   🧭 Find a part   🧾 Work Order   📈 Coverage …", 9.4, SUB, 400))
# pill
P.append(box(bx+bw-104, by+bh-30, 88, 20, "#171d26", "#2b333f", 20, 1)); P.append(t(bx+bw-94, by+bh-16, "⌘K jump", 8.6, "#9aa6b6", 400))
hr(346)

P.append(t(40, 374, "THE TWO QoL WINS", 13, GRN, 700))
P.append(box(40, 388, 1100, 92, PANEL, GRN, 12, 1))
s,_ = wrap(58, 412, "RECENT — every tool page you open is recorded (path + ?q + title) to localStorage; the palette shows your last few "
  "at the top when the box is empty, so you jump straight back to the part/figure you were on. ES5-safe with a URLSearchParams "
  "regex fallback. PILL — a subtle '⌘K jump' pill on every page finally makes the command palette discoverable, not just documented.", 224, 10, SUB, 15)
P.append(s)
hr(496)

P.append(t(40, 524, "VERIFIED / R1", 13, GRN, 700))
P.append(box(40, 538, 1100, 124, PANEL, GRN, 12, 1))
ver = ["audit logic run in-sandbox against the real ui/ folder: 0 dead scripts (handles ?v= cache-busters), 0 orphans, 0 broken links.",
       "audit_features.py parses (166 lines, tail sys.exit(main())); imports the live registry host-side to be authoritative.",
       "palette.js read host-authoritatively (161 lines, IIFE balanced/closed); the Recent + pill blocks pass node --check in isolation.",
       "One file (palette.js) delivers both QoL wins to all 19 pages — no per-page edits. Nothing writes the index (R1/R6)."]
yy = 560
for v in ver:
    P.append('<circle cx="56" cy="%d" r="2.6" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(66, yy, v, 224, 9.3, SUB, 13); P.append(s); yy += 13*n + 4

P.append(t(40, H-8, "Markup. Dark (R3). v0.99.13 · 2026-07-01 · audit_features.py/AUDIT.bat · palette.js Recent+pill. Read-only. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "117-audit-qol")), "bytes")
