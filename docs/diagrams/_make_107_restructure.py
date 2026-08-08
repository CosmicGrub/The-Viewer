#!/usr/bin/env python3
"""107: v0.96.0 'The Restructure' — data-flow of the modularized server (R2/R3 dark + PDF).

Top lane: request lifecycle through the hardened shell. Middle: the features/ package the
monolith split into. Bottom: the foundation layer (theme/shared/base.css/patterns/lint) and
the safety rails. Run:  python _make_107_restructure.py
"""
from _common import *

W, H = 1180, 760
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0),
     '<defs><marker id="a" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto">'
     '<path d="M0,0 L7,3 L0,6 z" fill="%s"/></marker></defs>' % SUB]

P.append(t(40, 44, "v0.96.0 — THE RESTRUCTURE: monolith → thin shell + features/ package", 19, TXT, 700))
P.append(t(40, 66, "viewer_app.py 2,407 lines → ~330-line shell · domain logic moved verbatim into 9 modules · one error boundary · declarative routes", 11.5, SUB))

# ---- lane 1: request lifecycle ----
P.append(t(40, 102, "REQUEST LIFECYCLE (hardened shell)", 12, ACC, 700))
lane1 = [("Browser /\nUI page", P2, LINE),
         ("Handler\nB13 timeout · J68 origin\nB13 8 MB body cap", PANEL, AMB),
         ("Route registry\n{path: handler}\n108 GET · 10 POST", PANEL, ACC),
         ("Param validation\nqint/qstr/qflag\nbad input → 400 (B11)", PANEL, ACC),
         ("Feature handler\n(verbatim domain logic)", PANEL, GRN),
         ("ONE error boundary\n400 / 404 / logged 500\nnever drops the socket (B9)", PANEL, AMB)]
x = 40
for i, (label, fill, stroke) in enumerate(lane1):
    bw = 172
    P.append(box(x, 118, bw, 70, fill, stroke, 10))
    for li, ln in enumerate(label.split("\n")):
        P.append(t(x + bw / 2, 140 + li * 14, ln, 9.6 if li else 10.6, SUB if li else TXT, 400 if li else 700, "middle"))
    if i < len(lane1) - 1:
        P.append('<path d="M%d,153 L%d,153" stroke="%s" stroke-width="1.6" fill="none" marker-end="url(#a)"/>' % (x + bw, x + bw + 16, SUB))
    x += bw + 18

# ---- lane 2: the features package ----
P.append(t(40, 234, "engine/features/ — WHERE THE MONOLITH'S LOGIC LIVES NOW (DI: each module gets `core` = the running viewer_app)", 12, GRN, 700))
mods = [("registry.py", "routes dicts + ParamError + central clamps (B11/J67)"),
        ("routes.py", "every endpoint, declared once; static pages/scripts as tables"),
        ("search_feature", "synonyms · tags · fuzzy · type-ahead · FTS search · find-in-doc"),
        ("parts_feature", "NSN refs · look-alike diff · NIIN review · learning layer"),
        ("browse_feature", "vehicle hub · sides · 3D/schematics lists · status/ops"),
        ("procedures_feature", "work-package parse · torque specs"),
        ("render_feature", "fitz/Poppler render · page cache · words · callouts (B12 by-id only)"),
        ("ingest_feature", "preview/start/status (+ J70 canonical paths)"),
        ("sessions_feature", "104th request sessions")]
cols = 3
bw, bh, gx, gy = 356, 64, 18, 14
for i, (name, desc) in enumerate(mods):
    cx = 40 + (i % cols) * (bw + gx); cy = 250 + (i // cols) * (bh + gy)
    P.append(box(cx, cy, bw, bh, PANEL, GRN, 10))
    P.append(t(cx + 14, cy + 24, name, 11.5, TXT, 700))
    s, _ = wrap(cx + 14, cy + 42, desc, 62, 9.3, SUB, 12)
    P.append(s)

# arrow from lane1 to lane2
P.append('<path d="M590,188 L590,246" stroke="%s" stroke-width="1.6" fill="none" marker-end="url(#a)"/>' % SUB)

# ---- lane 3: earlier extractions + index ----
y3 = 506
P.append(t(40, y3, "EARLIER EXTRACTIONS (unchanged, same DI)", 12, TEAL, 700))
prior = "collections · sides · chapters · figures · rpstl · xref(+online) · material · image3d · localmodel · procedure_full"
P.append(box(40, y3 + 12, 730, 44, P2, TEAL, 10))
P.append(t(54, y3 + 32, prior, 10.2, SUB))
P.append(t(54, y3 + 46, "all keep calling core.db / core.DB_PATH — the shell still owns config + the per-thread SQLite plumbing", 9.2, SUB))
P.append(box(800, y3 + 12, 340, 44, P2, LINE, 10))
P.append(t(816, y3 + 32, "index/viewer.db (READ-ONLY here, R1)", 10.5, TXT, 700))
P.append(t(816, y3 + 46, "+ sidecars: collections · reviews · correlations · rpstl", 9.2, SUB))

# ---- lane 4: foundation + safety rails ----
y4 = 600
P.append(t(40, y4, "FOUNDATION (dedup) + SAFETY RAILS shipped with v0.96.0", 12, AMB, 700))
rails = [("engine/theme.py", "ONE palette — ui/base.css mirrors it; diagram _common.py imports it (A3/A4/A8)"),
         ("ui/shared.js (ES5)", "ONE copy of esc/$/getJSON/postJSON/toast/debounce — served at /shared.js (A2)"),
         ("patterns.py adopted", "NSN/FIG/PN regexes now imported, not copied (A6)"),
         ("rps_lint in VERIFY-ALL", "ES5/legacy gate runs with every verify; all 31 UI files classified (G47/G48/K73)"),
         ("test_hardening.py", "12 acceptance checks: 400s, 413, 403, traversal, version surfacing (K71)"),
         ("logs + rollback", "rotating server-errors.log in /ops (B10) · monolith preserved in backups/pre-v0.96-restructure (R1)")]
bw2, bh2 = 356, 56
for i, (name, desc) in enumerate(rails):
    cx = 40 + (i % cols) * (bw2 + gx); cy = y4 + 12 + (i // cols) * (bh2 + 12)
    P.append(box(cx, cy, bw2, bh2, PANEL, AMB, 10))
    P.append(t(cx + 14, cy + 20, name, 10.8, TXT, 700))
    s, _ = wrap(cx + 14, cy + 36, desc, 64, 8.9, SUB, 11)
    P.append(s)

P.append(t(40, H - 14, "Rules: R1 backwards-compatible/rollbackable · R2 diagram · R3 dark+PDF · R4 changelog · R5 visual changelog · R6 append-only · verified: 75 regression + 59 route-smoke + 12 hardening tests green", 9.3, "#6b7280"))

if __name__ == "__main__":
    print(render("\n".join(P) + "</svg>", BASE_DIR + "/107-restructure"))
