#!/usr/bin/env python3
"""BUILT 0.65.0: Foundation batch part 2 — shared patterns.py + its test, shared diagram helpers
(_common.py, used by THIS diagram), and the route smoke test wired into verify_all. (dark R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *   # palette + box/t/wrap/panel/svg_open/render  (proving the shared module works)

W, H = 1180, 540
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
P.append(t(40, 46, "BUILT — Foundation batch, part 2: shared code + route smoke test  (v0.65.0)", 19, TXT, 700))
P.append(t(40, 70, "Removing duplication and widening the test net. This diagram itself is rendered by the new shared _common.py — dogfooding the cleanup.", 11, SUB, 400))
P.append('<line x1="40" y1="86" x2="%d" y2="86" stroke="%s"/>' % (W - 40, LINE))
P.append(panel(40, 108, 553, 180, "\U0001F9E9", "patterns.py — one home for the regexes", ACC,
  ["NSN / FIG / labeled part-number patterns + norm_nsn / digits / nsn_fts_phrase, currently copied across search, callouts, and threed_refs.",
   "tests/test_patterns.py pins them: dashed+bare NSN canonicalize the same, FIG ranges, labeled P/N only, FTS phrase form. 9/9 pass.",
   "Modularization (#36) will switch the viewer_app copies to `from patterns import ...`."],
  "Single source of truth for part-token extraction."))
P.append(panel(604, 108, 553, 180, "\U0001F3A8", "_common.py — shared diagram helpers", TEAL,
  ["The palette + box/text/wrap/panel were re-declared in all 78 generators; now they live in one module.",
   "Future _make_*.py do `from _common import *` and call render(svg, base).",
   "This very diagram (79) is built with it — so it's proven, not theoretical."],
  "78x duplication retired going forward."))
P.append(panel(40, 300, 553, 180, "\U0001F50C", "Route smoke test", AMB,
  ["tests/test_routes.py starts the REAL server against the deterministic fixture index and hits every known route.",
   "Asserts NO 5xx (the server never crashes on a normal request) + valid JSON on /api/* and /healthz.",
   "Catches a broken route or handler the unit tests would miss."],
  "Every endpoint exercised end-to-end."))
P.append(panel(604, 300, 553, 180, "✅", "Wired into the one-button check", PUR,
  ["verify_all.py now runs test_patterns + test_routes alongside pillars / features / truncation.",
   "RUN-ALL-TESTS.bat = verify_all + the RPS lint, host-side.",
   "So these additives are now part of the standing gate, not one-off checks."],
  "New tests join the permanent harness."))
P.append(box(40, 496, 1116, 34, PANEL, GRN, 12, 1))
s, _ = wrap(58, 517, "VERIFIED: patterns.py compiles, test_patterns 9/9. _common.py renders this PDF (proof). test_routes + verify_all compile; the route suite runs host-side (imports viewer_app). RPS lint still green. Next: the UI helper/CSS consolidation needs a careful pass (the $ helper differs per page) — folded into the modularization/UI batch.", 198, 9, SUB, 12)
P.append(s)
P.append(t(40, H - 8, "BUILT diagram. Dark (R3). v0.65.0 · 2026-06-03 · patterns.py + test_patterns · diagrams/_common.py · tests/test_routes.py → verify_all. Additive (R1/R6).", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "79-foundation2-built")), "bytes")
