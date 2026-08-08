#!/usr/bin/env python3
"""BUILT 0.69.0: inline background part tagging — a pencil on each part; tags feed offline search. (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 470
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
P.append(t(40, 46, "BUILT — inline part tagging (background pencil)  (v0.69.0)", 19, TXT, 700))
P.append(t(40, 70, "Tagging lives in the background while you browse, not as a foreground feature page — a small pencil on every part, click to add your words.", 11, SUB, 400))
P.append('<line x1="40" y1="86" x2="%d" y2="86" stroke="%s"/>' % (W - 40, LINE))
P.append(panel(40, 108, 360, 188, "✎", "A quiet pencil on every part", ACC,
  ["tagger.js drops a small, low-key pencil on each part — NSN-bearing search results and every 3D library card (dossier / Look-Alike next).",
   "Click it: a tiny popover to add/remove your own words (slang, common names, tags) for THAT part.",
   "ES5-safe, dependency-free, served at /tagger.js."],
  "Tag the part in front of you, in place."))
P.append(panel(412, 108, 360, 188, "\U0001F50E", "Tags teach search", TEAL,
  ["A tag is stored against the part (by NSN, else name) in keywords_user.json and folded into the offline search expansion, live.",
   "So a word you tag onto a part also FINDS that part — and tags on the same part find each other.",
   "Directly teaches; indirectly improves every later search."],
  "Your word now finds the part."))
P.append(panel(784, 108, 356, 188, "\U0001F4A4", "Background, not foreground", AMB,
  ["Removed the prominent Keywords nav button; the manager page stays only as a quiet 'manage all' link inside the popover.",
   "The system stays out of the way until you reach for the pencil.",
   "All parts taggable, no dedicated feature field."],
  "Out of the way until you want it."))
P.append(box(40, 312, 1100, 80, PANEL, GRN, 12, 1))
P.append(t(58, 334, "VERIFIED", 11.5, GRN, 700))
s, _ = wrap(58, 354, "tagger.js syntax-clean + ES5-clean (RPS gate covers it). Tag logic isolation-tested: tagging NSN 6140-01-485-1472 ('battery, storage') with 'juice box' makes 'juice box' find the NSN AND the name; tags become mutually findable. Server functions + /api/tags + /tagger.js routes confirmed on host. Tags live-reload into search with no restart.", 200, 9, SUB, 12)
P.append(s)
P.append(t(40, H - 8, "BUILT diagram. Dark (R3). v0.69.0 · 2026-06-03 · ui/tagger.js · /api/tags + user_tags_* · keywords_user.json tags · index.html + threed.html pencils. Additive (R1/R6).", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "83-inline-tags-built")), "bytes")
