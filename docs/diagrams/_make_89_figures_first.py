#!/usr/bin/env python3
"""v0.82.0 — Figures-first 3-D library: lead with parts that have a real cited manual image. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1180, 600
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
P.append(t(40, 46, "Figures-first 3-D library  (v0.82.0)", 19, TXT, 700))
P.append(t(40, 70, "Interim measure: while the broader approximation work continues, the page leads with the parts that ALREADY have a real manual image.", 11, SUB, 400))
P.append('<line x1="40" y1="86" x2="%d" y2="86" stroke="%s"/>' % (W - 40, LINE))

# Data-flow row of panels
P.append(panel(40, 110, 250, 150, "DB", "parts table",  ACC,
    ["each row = a part cited on a manual page", "has fig_no + page + document_id", "WHERE fig_no IS NOT NULL and NSN<>''"],
    "source of truth for 'has a figure'"))
P.append('<text x="306" y="190" font-size="22" fill="%s">&#8594;</text>' % SUB)

P.append(panel(322, 110, 250, 150, "JOIN", "LEFT JOIN ref_nsn", TEAL,
    ["pull name / part# / CAGEC / chars", "name backfills the shape classifier", "GROUP BY nsn, ORDER BY name"],
    "one card per distinct NSN"))
P.append('<text x="588" y="190" font-size="22" fill="%s">&#8594;</text>' % SUB)

P.append(panel(604, 110, 250, 150, "IMG", "/figcrop image_url", AMB,
    ["every card carries a real crop URL", "renders the cited figure region", "cached PNG in index/figcache"],
    "no blank/blocky cards up top"))
P.append('<text x="870" y="190" font-size="22" fill="%s">&#8594;</text>' % SUB)

P.append(panel(886, 110, 254, 150, "UI", "3-D library page", GRN,
    ["leads with working examples", "card preview uses image_url first", "per-card lookup only as fallback"],
    "you see the manual breakdown image"))

# the toggle
yb = 295
P.append(box(40, yb, 1100, 64, PANEL, PUR, 12, 1))
P.append(t(58, yb + 26, "TOGGLE — “include parts without a manual figure”", 12, PUR, 700))
s, _ = wrap(58, yb + 46, "Default (off) = figures-first set described above. Checked = /api/threed?all=1 falls back to the full FLIS-dimension set (representative parametric shapes, some without a figure). The hint line states which mode you're in.", 200, 9.5, SUB, 13)
P.append(s)

# what changed / compat
yc = yb + 80
P.append(box(40, yc, 540, 110, PANEL, ACC, 12, 1))
P.append(t(58, yc + 24, "What changed", 11.5, ACC, 700))
s, _ = wrap(58, yc + 44, "threed_list() defaults to figures_only=True and is sourced from parts (not ref_nsn), so membership is driven by 'a figure actually exists.' /api/threed honors ?all=1 for the old full set. threed.html: checkbox + mode hint + card uses server image_url.", 96, 9.5, SUB, 13)
P.append(s)

P.append(box(596, yc, 544, 110, PANEL, GRN, 12, 1))
P.append(t(614, yc + 24, "Compatibility (R1) + rollback", 11.5, GRN, 700))
s, _ = wrap(614, yc + 44, "Purely additive: the all=1 path preserves prior behavior; no schema change; corpus untouched. Front-end is no-cache so a normal reload picks it up; the server was restarted to load the Python change. Rollback = set threed_list default figures_only=False.", 98, 9.5, SUB, 13)
P.append(s)

P.append(t(40, H - 8, "Data-flow diagram. Dark (R3). v0.82.0 · 2026-06-03 · engine/viewer_app.py threed_list + /api/threed · engine/ui/threed.html. Backwards-compatible & rollbackable (R1).", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "89-figures-first")), "bytes")
