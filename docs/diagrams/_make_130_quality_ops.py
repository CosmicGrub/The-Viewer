#!/usr/bin/env python3
"""v0.99.24/30/31/32 — Quality & ops: usage analytics · HTTP fuzz · mutation · installer. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
W, H = 1180, 540
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
P.append(t(40, 46, "Quality & ops — analytics · HTTP fuzz · mutation · installer   v0.99.24/30/31/32", 19, TXT, 700))
hr(70)
cards = [
 ("📊 Usage analytics", GRN, ["analytics.py — append-only local", "JSONL, OFFLINE, no accounts.", "/api/analytics_top + palette beacon.", "hot_docs() → prioritize OCR on the", "docs people actually use. Self-test green."]),
 ("🌐 HTTP integ/fuzz", TEAL, ["test_http.py + RUN-HTTP-FUZZ.bat.", "Spins the real app on a test port,", "hits EVERY GET route (adversarial", "params), asserts no 5xx + /api JSON.", "Real request-path coverage."]),
 ("🧬 Mutation testing", ACC, ["RUN-MUTATION.bat extended to", "figureparts / jobcard (test_jobcard)", "+ coverage (property fuzz).", "Survivors = test blind-spots — a", "true test-quality metric for v1.0."]),
 ("📦 Installer", AMB, ["viewer.spec + BUILD-INSTALLER.bat", "→ dist\\THE_VIEWER.exe (no Python).", "FIRST-RUN.bat points at corpus,", "re-tunes hardware, runs doctor,", "launches. For shop-floor PCs."]),
]
x0, y0, cw, ch = 40, 100, 272, 160
for i, (ti, col, rows) in enumerate(cards):
    cx = x0 + i*(cw+6)
    P.append(box(cx, y0, cw, ch, PANEL, col, 11, 1))
    P.append(t(cx+13, y0+22, ti, 12, col, 700))
    yy = y0+44
    for r in rows: P.append(t(cx+13, yy, r, 8.9, SUB, 400)); yy += 15
hr(280)
P.append(t(40, 308, "VERIFIED / R1", 13, GRN, 700))
P.append(box(40, 322, 1100, 96, PANEL, GRN, 12, 1))
ver = ["analytics.py self-test green in-sandbox (ranking / counts / hot-docs / kind-coercion / empty-drop).",
       "HTTP fuzz + mutation are host-side runners (need the app / mutmut-style loop); harness logic written + wired into batch files.",
       "Installer + FIRST-RUN are host build/run scripts; spec lists all hidden-imports so the frozen exe finds the feature modules.",
       "All additive: new modules + scripts, no product-code regressions. analytics is append-only sidecar (R1/R6)."]
yy = 344
for v in ver:
    P.append('<circle cx="56" cy="%d" r="2.6" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(66, yy, v, 224, 9.3, SUB, 13); P.append(s); yy += 13*n + 4
P.append(t(40, H-8, "Markup. Dark (R3). v0.99.24/30/31/32 · 2026-07-01 · analytics.py · test_http.py · RUN-MUTATION · viewer.spec. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "130-quality-ops")), "bytes")
