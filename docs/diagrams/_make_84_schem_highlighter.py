#!/usr/bin/env python3
"""PLAN 0.x: schematic highlighter mode — per-page strategy (vector overlay / callout hotspots / raster
flood-fill), grounded in a corpus probe (45% vector / 38% raster / 18% hybrid). (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 560
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
P.append(t(40, 46, "PLAN — schematic highlighter mode (clickable schematics)", 19, TXT, 700))
P.append(t(40, 70, "A schematic is only clickable if it carries structure. Probed 40 schematics: ~45% vector · ~38% raster scan · ~18% hybrid. So the mode is chosen PER PAGE.", 11, SUB, 400))
P.append('<line x1="40" y1="86" x2="%d" y2="86" stroke="%s"/>' % (W - 40, LINE))
P.append(panel(40, 108, 360, 198, "\U0001F58A", "Vector overlay  (Phase 1, ~45%)", GRN,
  ["Read the page's drawing ops (get_drawings) + word boxes on demand — NO conversion.",
   "Draw a transparent clickable SVG overlay over the page image; hover outlines, click highlights, connected segments group into a net/element.",
   "Crisp, scalable, RPS-safe. Con: vector pages only; geometric not semantic."],
  "Clickable now on ~half the corpus."))
P.append(panel(412, 108, 360, 198, "\U0001F3F7", "Callout hotspots  (Phase 1b, any text)", TEAL,
  ["Reuse the callout extractor + OCR word boxes: make reference designators / item #s / part #s / FIG refs clickable.",
   "Click -> highlight the label AND cross-link to the legend / parts list / dossier (with PUB LOG mfr + interchangeable).",
   "Works on raster scans too — now that OCR is 100%."],
  "Adds the meaning a shape can't."))
P.append(panel(784, 108, 356, 198, "\U0001F525", "Raster flood-fill  (Phase 2, ~38%)", AMB,
  ["Pure scans have no geometry: click a line, flood-fill the connected dark pixels to 'follow this wire'.",
   "Client-side on the canvas; heuristic but useful for tracing a circuit.",
   "Optional. Con: can over/under-select at crossings; no semantics."],
  "Tracing for the scans, later."))
P.append(box(40, 326, 1100, 70, PANEL, ACC, 12, 1))
P.append(t(58, 348, "NO CONVERSION REQUIRED", 11.5, ACC, 700))
s, _ = wrap(58, 366, "#1 reads vector geometry on demand, #2 reuses OCR, #3 processes pixels on the fly. The only optional optimisation is caching extracted paths in a small sidecar for instant re-open — additive, never touches the corpus (R1).", 200, 9.2, SUB, 12)
P.append(s)
P.append(box(40, 410, 1100, 70, PANEL, PUR, 12, 1))
P.append(t(58, 432, "RECOMMENDATION", 11.5, PUR, 700))
s, _ = wrap(58, 450, "Build Phase 1 (highlighter toggle + vector overlay + callout hotspots) — medium effort, makes 60%+ of pages interactive, RPS-safe, grounded in the real geometry/text. Add raster flood-fill (Phase 2) and a path cache (Phase 3) only if wanted. Two choices to confirm: highlight a single path vs connected-group; include flood-fill from the start or later.", 200, 9.2, SUB, 12)
P.append(s)
P.append(t(40, H - 8, "PLAN diagram. Dark (R3). 2026-06-03 · docs/SCHEMATIC-HIGHLIGHTER-PLAN.md · probe via PyMuPDF get_drawings/get_text/get_images. Read-only (R1).", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "84-schematic-highlighter-plan")), "bytes")
