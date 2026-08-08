#!/usr/bin/env python3
"""BUILT 0.71.0: schematic Highlighter Phase 1 (vector overlay + connected-group + raster fallback) and the
end-to-end demo/test congruence suite. (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 540
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
P.append(t(40, 46, "BUILT — schematic Highlighter (Phase 1) + end-to-end demo suite  (v0.71.0)", 19, TXT, 700))
P.append(t(40, 70, "Click elements on vector schematics to highlight the connected net; prove the whole app hangs together with one host-side command.", 11, SUB, 400))
P.append('<line x1="40" y1="86" x2="%d" y2="86" stroke="%s"/>' % (W - 40, LINE))
P.append(panel(40, 108, 360, 196, "\U0001F58D", "Highlighter — vector overlay", ACC,
  ["schem_overlay.py reads the page's real geometry + text via PyMuPDF on demand (normalized 0..1, no conversion).",
   "schemhl.js renders an interactive SVG (page image + clickable paths); hover outlines, click highlights the CONNECTED net/trace (union-find on shared endpoints).",
   "Toggle: 🖍 Highlight in the schematic viewer. Own zoom."],
  "~45% of sheets clickable now, no conversion."))
P.append(panel(412, 108, 360, 196, "\U0001F9FE", "Raster fallback (honest)", AMB,
  ["Scanned sheets have no geometry — schempaths returns has_vector=false.",
   "The highlighter shows a clear 'this is a scan' note and the existing callout chips (NSN/part/figure -> dossier/Look-Alike) stay available.",
   "Flood-fill tracing for scans = Phase 2 (deferred per your choice)."],
  "No dead ends; scans use callouts."))
P.append(panel(784, 108, 356, 196, "✅", "End-to-end congruence suite", GRN,
  ["test_routes now starts the REAL server on the fixture and hits EVERY major route (search/collections/callouts/3D/schempaths/tags/keywords/dossier/procedure/healthz/static), asserting no 5xx + valid JSON.",
   "RUN-ALL-TESTS.bat = pillars + features + patterns + routes + truncation + RPS lint.",
   "DEMO-SCRIPT.md: green-gate + a 6-min end-to-end demo flow."],
  "One button proves it works together."))
P.append(box(40, 320, 1100, 88, PANEL, PUR, 12, 1))
P.append(t(58, 342, "HOW TO RUN THE DEMO", 11.5, PUR, 700))
s, _ = wrap(58, 362, "On Windows: (1) RUN-ALL-TESTS.bat -> expect ALL TESTS GREEN. (2) run_app.bat -> it serves + opens the page. (3) follow docs/DEMO-SCRIPT.md: slang search -> tag -> page/loupe/callouts -> schematic highlighter -> detailed 3D -> collections -> solve->packet -> PUB LOG dossier. Optional: FINALIZE-OCR.bat + ENRICH-PUBLOG.bat for fullest data; run_safeguard.bat snapshot first.", 200, 9, SUB, 12)
P.append(s)
P.append(box(40, 416, 1100, 64, PANEL, AMB, 12, 1))
s, _ = wrap(58, 437, "VERIFIED: schem_overlay on real corpus schematics (607 paths), schemhl.js syntax + ES5-clean, schematics.html toggle + both routes + expanded test_routes confirmed on host. CAVEAT: the sandbox mount is intermittently corrupting reads of the large viewer_app.py, so the server-dependent suite couldn't be RUN in-sandbox — the authoritative gate is RUN-ALL-TESTS.bat on Windows. Host files are intact (authoritative tools confirm).", 200, 9, SUB, 12)
P.append(s)
P.append(t(40, H - 8, "BUILT diagram. Dark (R3). v0.71.0 · 2026-06-03 · schem_overlay.py · ui/schemhl.js · /api/schempaths · schematics.html 🖍 · test_routes + DEMO-SCRIPT.md. Additive (R1/R6).", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "85-highlighter-demo-built")), "bytes")
