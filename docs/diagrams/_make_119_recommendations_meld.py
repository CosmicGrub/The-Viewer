#!/usr/bin/env python3
"""v0.99.15 — All five recommendations + feature congruency (the meld) + R9 no-truncation gate. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 720
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))

P.append(t(40, 46, "All recommendations + the meld   v0.99.15", 19, TXT, 700))
P.append(t(40, 70, "Five recommendations shipped, then proven to fit together: every cross-link a feature emits resolves to a real route, and a fuzz-found crash was fixed.", 11.5, SUB, 400))
hr(86)

cards = [
 ("#2 Fuzz render/vectorize", "#e0564f", ["Extended fuzz to vectorize_image.", "FOUND a real crash: thin image +", "small max_dim → cv2.resize(0).", "Fixed max(1,int()); reproved 9,000", "cases incl. max_dim=1. New invariant."]),
 ("#3 Per-part look-alike", GRN, ["jobcard._flag_lookalikes marks", "parts that are look-alike variants;", "⚠ + /partdiff compare link in the", "builder + PDF. Agrees with the cover", "warning (silent on format-drift)."]),
 ("#4 Drag-drop ingest", TEAL, ["/ingest drop-zone + folder detect", "(webkitGetAsEntry) + Recent paths.", "Honest to the server-path model —", "no upload subsystem, corpus stays", "read-only (R1/R6)."]),
 ("#5 Accessibility (WCAG AA)", ACC, [":focus-visible everywhere (base.css).", "Palette: listbox/option ARIA,", "aria-activedescendant, focus return,", "keyboard-operable pill. aria-hidden", "on decorative icons."]),
]
x0, y0, cw, ch = 40, 116, 272, 150
for i, (ti, col, rows) in enumerate(cards):
    cx = x0 + i*(cw+6)
    P.append(box(cx, y0, cw, ch, PANEL, col, 11, 1))
    P.append(t(cx+13, y0+22, ti, 11.5, col, 700))
    yy = y0+44
    for r in rows: P.append(t(cx+13, yy, r, 8.7, SUB, 400)); yy += 15
hr(282)

# congruency center
P.append(t(40, 310, "CONGRUENCY — do the pieces mesh? (test_congruency.py)", 13, "#7fbfff", 700))
P.append(box(40, 324, 1100, 128, PANEL, "#7fbfff", 12, 1.3))
rows = ["Every cross-link a feature emits must resolve to a route the app actually serves — no dangling references as features multiply.",
        "figureparts → /dossier, /locate   ·   jobcard part rows → /partdiff, /dossier   ·   palette's 22 destinations → real routes/pages.",
        "look-alike WARNING (cover) and per-part FLAG use the same 'real difference' gate — verified they agree (and both stay silent on format-drift).",
        "VERIFIED in-sandbox: figureparts links all resolve; all 22 palette destinations resolve; 0 dangling. (full check runs host-side.)"]
yy = 348
for r in rows:
    P.append('<circle cx="56" cy="%d" r="2.5" fill="%s"/>' % (yy-3, "#7fbfff")); s, n = wrap(66, yy, r, 226, 9.6, SUB, 14); P.append(s); yy += 14*n + 5
hr(468)

# R9 gate
P.append(t(40, 496, "R9 — NO-TRUNCATION GATE (new standing rule, this project only)", 13, AMB, 700))
P.append(box(40, 510, 1100, 92, PANEL, AMB, 12, 1))
s,_ = wrap(58, 534, "The sandbox mount truncates / stale-caches / null-pads grown host files, so 'it parsed in the sandbox' is unreliable here. "
  "R9: always verify completeness mechanically — a tail sentinel on every generated file + verify_complete.py, run HOST-side "
  "(bundled into engine/tools/notrunc/ and VERIFY-099.bat) where the files are whole, or via the host-authoritative Read tool. "
  "This session that discipline caught the '# -- END --' false-tail and confirmed the real files are complete.", 232, 10, SUB, 15)
P.append(s)
hr(618)

P.append(t(40, 646, "R1 · all additive: 1 one-line crash fix + 4 feature melds + 1 congruency test + the R9 gate. Nothing writes the index. Read-only, rollbackable.", 10, SUB, 400))
P.append(t(40, H-8, "Markup. Dark (R3). v0.99.15 · 2026-07-01 · vectorize fix · jobcard look-alike · ingest drop · a11y · test_congruency · R9. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "119-recommendations-meld")), "bytes")
