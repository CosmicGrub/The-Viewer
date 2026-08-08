#!/usr/bin/env python3
"""108: v0.97.0 — search quality + UI dedup + the header-wrap layout fix (R2/R3 dark + PDF).

Top: the upgraded query pipeline (operators -> match builder -> exact-boost ranking -> LRU,
with the did-you-mean branch on zero results). Middle: the UI dedup (12 pages now pull
/base.css + /shared.js; inline copies stripped). Bottom: the E39 layout fix.
Run:  python _make_108_search_dedup.py
"""
from _common import *

W, H = 1180, 720
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0),
     '<defs><marker id="a" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto">'
     '<path d="M0,0 L7,3 L0,6 z" fill="%s"/></marker></defs>' % SUB]

P.append(t(40, 44, "v0.97.0 — SEARCH QUALITY + UI DEDUP + LAYOUT FIX", 19, TXT, 700))
P.append(t(40, 66, "backlog C18/C20/C22/C23 · A2/A3 finished across 12 pages · E39 header-wrap fix · visual changelog now auto-generated (#81)", 11.5, SUB))

# lane 1: query pipeline
P.append(t(40, 102, "QUERY PIPELINE (additions in green)", 12, ACC, 700))
lane = [("Query", P2, LINE, ""),
        ('Operators (C22)\n"exact phrase" · a NEAR b', PANEL, GRN, "pass through to FTS5"),
        ("build_match\nsynonyms · fuzzy · phrases", PANEL, LINE, "unchanged core"),
        ("FTS5 rank (bm25)", PANEL, LINE, "single-column body text"),
        ("Exact-boost (C18)\nverbatim hit · exact part#", PANEL, GRN, "sorts above keyword hits"),
        ("60s LRU (C23)\nrepeat query = no SQLite", PANEL, GRN, "200 entries, TTL-safe")]
x = 40
for i, (label, fill, stroke, sub) in enumerate(lane):
    bw = 172
    P.append(box(x, 118, bw, 74, fill, stroke, 10))
    lines = label.split("\n")
    yy = 140 if len(lines) > 1 else 152
    for li, ln in enumerate(lines):
        P.append(t(x + bw / 2, yy + li * 14, ln, 9.6 if li else 10.6, SUB if li else TXT, 400 if li else 700, "middle"))
    if sub:
        P.append(t(x + bw / 2, 184, sub, 8.4, SUB, 400, "middle"))
    if i < len(lane) - 1:
        P.append('<path d="M%d,155 L%d,155" stroke="%s" stroke-width="1.6" fill="none" marker-end="url(#a)"/>' % (x + bw, x + bw + 16, SUB))
    x += bw + 18

# zero-result branch
P.append('<path d="M610,192 L610,228" stroke="%s" stroke-width="1.6" fill="none" marker-end="url(#a)"/>' % AMB)
P.append(box(440, 232, 360, 50, PANEL, AMB, 10))
P.append(t(620, 252, "0 results → did_you_mean (C20)", 11, TXT, 700, "middle"))
P.append(t(620, 268, "closest indexed terms (edit-distance 1, offline) + strongest-token fallback — clickable in the UI", 8.6, SUB, 400, "middle"))

# lane 2: UI dedup
y2 = 320
P.append(t(40, y2, "UI DEDUP FINISHED (A2/A3) — 12 pages now share ONE helper + ONE token sheet", 12, GRN, 700))
P.append(box(40, y2 + 14, 360, 96, PANEL, GRN, 10))
P.append(t(56, y2 + 36, "/base.css  +  /shared.js", 11.5, TXT, 700))
s, _ = wrap(56, y2 + 54, "tokens (theme.py mirror) + esc/$/getJSON/postJSON/toast/debounce — ES5, lint-locked", 64, 9, SUB, 11)
P.append(s)
P.append(t(56, y2 + 98, "inline copies STRIPPED (11×esc, 12×:root)", 9.3, GRN, 700))
P.append('<path d="M400,%d L436,%d" stroke="%s" stroke-width="1.6" fill="none" marker-end="url(#a)"/>' % (y2 + 62, y2 + 62, SUB))
pages = ["collections", "partdiff", "procedure", "solve", "dossier", "packet*", "stepflow", "ingest", "ops", "status", "help", "keywords"]
px, py = 440, y2 + 14
for i, pg in enumerate(pages):
    cx = px + (i % 4) * 178; cy = py + (i // 4) * 34
    P.append(box(cx, cy, 166, 26, P2, LINE, 7))
    P.append(t(cx + 83, cy + 17, pg + ".html", 9.5, TXT, 400, "middle"))
P.append(t(440, y2 + 124, "*packet keeps its paper-preview styling — shared.js only · procedure/status keep their deliberate brighter green as a 1-token override", 8.6, SUB))

# lane 3: layout fix
y3 = 478
P.append(t(40, y3, "LAYOUT FIX (E39) — the home page no longer overflows sideways", 12, AMB, 700))
P.append(box(40, y3 + 14, 545, 150, PANEL, RED, 10))
P.append(t(56, y3 + 36, "BEFORE", 11, RED, 700))
s, _ = wrap(56, y3 + 54, "header nav = 16 buttons in ONE non-wrapping flex row -> ~2000px minimum width. Any narrower window: the whole page scrolls sideways, the left edge (logo, search label) is cut off, buttons wrap into 3-line towers.", 96, 9.4, SUB, 12)
P.append(s)
P.append(box(56, y3 + 116, 510, 30, P2, RED, 7))
P.append(t(311, y3 + 135, "…E VIEWER | 16 buttons →→→ (off-screen) | scrollbar", 9.2, SUB, 400, "middle"))
P.append(box(595, y3 + 14, 545, 150, PANEL, GRN, 10))
P.append(t(611, y3 + 36, "AFTER (v0.97.0)", 11, GRN, 700))
s, _ = wrap(611, y3 + 54, "header{flex-wrap:wrap} at EVERY width · .tg nav wraps BETWEEN buttons (white-space:nowrap inside labels) · main grid minmax(0,1fr) so results can never force overflow · right column narrows at 1280px.", 96, 9.4, SUB, 12)
P.append(s)
P.append(box(611, y3 + 110, 510, 18, P2, GRN, 6))
P.append(t(866, y3 + 123, "THE VIEWER   [row 1: 9 buttons]", 8.8, SUB, 400, "middle"))
P.append(box(611, y3 + 132, 510, 18, P2, GRN, 6))
P.append(t(866, y3 + 145, "[row 2: remaining buttons — everything visible, no sideways scroll]", 8.8, SUB, 400, "middle"))

P.append(t(40, H - 38, "Also shipped: CHANGELOG-VISUAL-FULL — the complete 127-release visual changelog, auto-generated from CHANGELOG.md (backlog #81 root-cause fix; can never stall again).", 9.6, SUB))
P.append(t(40, H - 14, "Verified: 8 suites green incl. new test_search_quality (15 checks) · every modified page fetched 200 + node-syntax-clean · RPS GATE PASS · rollback: backups/pre-v0.97-batch (R1)", 9.3, "#6b7280"))

if __name__ == "__main__":
    print(render("\n".join(P) + "</svg>", BASE_DIR + "/108-search-dedup-layout"))
