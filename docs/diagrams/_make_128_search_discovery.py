#!/usr/bin/env python3
"""v0.99.25/28/29 — Search & discovery trio: semantic search · visual match · related parts. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
W, H = 1180, 560
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
P.append(t(40, 46, "Search & discovery — three new ways to find a part   v0.99.25/28/29", 19, TXT, 700))
P.append(t(40, 70, "Beyond keyword search: by MEANING, by PHOTO, and by RELATIONSHIP. All offline.", 11.5, SUB, 400))
hr(86)
cards = [
 ("🧠 Semantic search  /semantic", "#7fbfff", ["embed.py + /api/semantic. Search by meaning:", "'coolant leak at the water pump' finds the", "right pages w/o those exact words.", "Local sentence-transformers model when", "installed; deterministic hash fallback else.", "Build: BUILD-EMBEDDINGS.bat. Verified:", "self-cos=1.0, related 0.73 > unrelated 0.0."]),
 ("📷 Visual match  /visual", GRN, ["phash.py + POST /api/visualmatch. Drop a", "photo of a part → closest figure crops by", "64-bit DCT perceptual hash + Hamming.", "Pure numpy/PIL, offline, no model.", "Build: BUILD-VISUAL-INDEX.bat -> phash.tsv.", "Verified: identical/resized = 0, unrelated = 31.", "/figcrop serves the matched crop."]),
 ("🧩 Related  /related", AMB, ["xref.py + /api/xref. For a part: the", "assemblies/figures it belongs to, its", "SIBLINGS (same figure), and SEE-ALSO", "(same assembly elsewhere) — each links to", "dossier / deep-zoom.", "Verified: siblings BOLT/NUT, see-also", "VOLTAGE REGULATOR (self-inclusion bug fixed)."]),
]
x0, y0, cw, ch = 40, 116, 366, 210
for i, (ti, col, rows) in enumerate(cards):
    cx = x0 + i*(cw+6)
    P.append(box(cx, y0, cw, ch, PANEL, col, 11, 1))
    P.append(t(cx+14, y0+24, ti, 12, col, 700))
    yy = y0+46
    for r in rows: P.append(t(cx+14, yy, r, 9, SUB, 400)); yy += 15.5
hr(342)
P.append(t(40, 370, "VERIFIED / R1", 13, GRN, 700))
P.append(box(40, 384, 1100, 96, PANEL, GRN, 12, 1))
ver = ["All three cores verified in-sandbox against real logic (cosine / Hamming / xref on synthetic DBs); pages pass node --check.",
       "Model/index BUILD steps run host-side (BUILD-EMBEDDINGS / BUILD-VISUAL-INDEX) — the app degrades gracefully with a clear 'not built' state.",
       "Wired: /semantic /visual /related in _PAGES + palette + Tools menu + verify_ui; /api/semantic /api/visualmatch /api/xref /figcrop.",
       "Additive & read-only: new modules + routes + pages. Nothing writes the index (R1/R6)."]
yy = 406
for v in ver:
    P.append('<circle cx="56" cy="%d" r="2.6" fill="%s"/>' % (yy-3, GRN)); s, n = wrap(66, yy, v, 224, 9.3, SUB, 13); P.append(s); yy += 13*n + 4
P.append(t(40, H-8, "Markup. Dark (R3). v0.99.25/28/29 · 2026-07-01 · embed.py · phash.py · xref.py. Read-only. R1/R6.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "128-search-discovery")), "bytes")
