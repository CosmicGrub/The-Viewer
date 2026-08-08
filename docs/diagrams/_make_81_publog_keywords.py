#!/usr/bin/env python3
"""BUILT 0.67.0: PUB LOG cross-reference + repository/browse mode + keyword/tag layer (curated + user). (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 560
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
P.append(t(40, 46, "BUILT — PUB LOG cross-reference · repository mode · keyword layer  (v0.67.0)", 19, TXT, 700))
P.append(t(40, 70, "Tap the full FLIS reference set for correlative data, browse without a parts sheet, and teach search the words mechanics actually use.", 11, SUB, 400))
P.append('<line x1="40" y1="86" x2="%d" y2="86" stroke="%s"/>' % (W - 40, LINE))
P.append(panel(40, 108, 360, 200, "\U0001F517", "PUB LOG cross-reference", ACC,
  ["enrich_flis now matches every index NSN against the FLIS tables and adds: MANUFACTURER + location (P_CAGE via CAGE), colloquial/common name (V_COLLOQUIAL_NAME), interchangeable NSNs (V_FLIS_STANDARDIZATION -> alt_parts).",
   "Append-only (ref_nsn_log, R6), cited to PUB LOG, no schema change.",
   "ENRICH-PUBLOG.bat runs the full folder host-side."],
  "Who makes it, what it's called, what swaps for it."))
P.append(panel(412, 108, 360, 200, "\U0001F50E", "Repository / browse mode", AMB,
  ["Onboarding now has a 'Browse the repository' button -> skip the parts-request sheet and just search/browse (a Browse-mode chip shows it).",
   "An always-visible 'Parts session' button reopens the onboarding window to start/edit a 104th session anytime.",
   "It IS a dedicated repository now, not only a request tool."],
  "Use it as a pure repository, or a request tool."))
P.append(panel(784, 108, 356, 200, "\U0001F3F7", "Keyword / fuzzy layer", TEAL,
  ["keywords.json maps slang/functional words to nomenclature (zerk->grease fitting, turbo->turbocharger, charger->alternator). 47 groups, 309 terms.",
   "build_keywords.py folds in PUB LOG colloquial names.",
   "Loads beside synonyms.json into the offline search expansion."],
  "Mechanics' words find the right part."))
P.append(box(40, 324, 1100, 96, PANEL, PUR, 12, 1))
P.append(t(58, 346, "\U0001F465  YOU CAN TEACH IT: the user keyword/tag manager (/keywords)", 12.5, PUR, 700))
s, _ = wrap(58, 366, "Add your own groups of equivalent words (slang, common names, abbreviations, part numbers). They save to a keywords_user.json sidecar — kept separate from the curated sets — and LIVE-RELOAD into search immediately, no restart. Directly teaches the system your shop's words; indirectly improves every later search and the type-ahead. ES5-safe page (RPS gate covers it).", 200, 9.2, SUB, 12.5)
P.append(s)
P.append(box(40, 432, 1100, 96, PANEL, GRN, 12, 1))
P.append(t(58, 454, "VERIFIED", 11.5, GRN, 700))
s, _ = wrap(58, 474, "Enrichment isolation-tested on synthetic FLIS CSVs (real headers): item name, part/CAGE, manufacturer+location, colloquial, interchangeable->alt_parts, cited description — PASS. Keyword expansion PASS (zerk->grease fitting, turbo->turbocharger, lug->terminal, +8). User keyword save/dedup/delete + live SYN reload PASS. keywords.html ES5-clean. All server functions + routes confirmed on host. Running app stays offline; enrichment reads local PUB LOG only.", 200, 9.2, SUB, 12.5)
P.append(s)
P.append(t(40, H - 8, "BUILT diagram. Dark (R3). v0.67.0 · 2026-06-03 · viewer_ingest.enrich_flis · ENRICH-PUBLOG.bat · keywords.json/build_keywords.py · keywords.html + /api/keywords · index.html buttons. Additive (R1/R6).", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "81-publog-keywords-built")), "bytes")
