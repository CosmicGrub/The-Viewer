#!/usr/bin/env python3
"""v1.13.0 HOLISTIC HARDENING — 4 review lanes -> 4 work packages -> audit/harden gates. Dark (R2/R3/R5)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1240, 860
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]


def hr(y):
    P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W - 40, y, LINE))


def card(x, y, w, hh, col, ti, rows):
    P.append(box(x, y, w, hh, PANEL, LINE, 11, 1))
    P.append('<rect x="%d" y="%d" width="5" height="%d" rx="2.5" fill="%s"/>' % (x, y, hh, col))
    P.append(t(x + 16, y + 22, ti, 11.5, col, 700))
    yy = y + 42
    for r in rows:
        P.append(t(x + 16, yy, r, 9, SUB, 400)); yy += 15


def arrow(x1, y1, x2, y2, col):
    P.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1.6"/>' % (x1, y1, x2, y2, col))
    P.append('<polygon points="%d,%d %d,%d %d,%d" fill="%s"/>' % (x2, y2, x2 - 5, y2 - 8, x2 + 5, y2 - 8, col))


P.append(t(40, 46, "THE VIEWER v1.13.0 — HOLISTIC HARDENING: dev-team review implemented, audited, shipped", 16.5, TXT, 700))
P.append(t(40, 70, "4 parallel review lanes -> 4 work packages -> independent audit + adversarial hardening + polish. Additive/rollbackable (R1); backup at backups/pre-v1.13.", 10.5, SUB, 400))
hr(84)

# ---- row 1: the four review lanes ---------------------------------------------------------------
P.append(t(40, 108, "DEV-TEAM REVIEW (4 lanes)", 12, ACC, 700))
lane_w = 283
for i, (ti, sub) in enumerate([
        ("server / data access", "leaks · dup SQL · trust gaps"),
        ("verify / operations", "gate sprawl · coverage holes"),
        ("UI coherence / a11y", "dup helpers · alert() · nav"),
        ("features / safety", "missed roadmap safety items")]):
    x = 40 + i * (lane_w + 10)
    P.append(box(x, 118, lane_w, 46, P2, LINE, 9, 1))
    P.append(t(x + 12, 137, ti, 10.5, TXT, 700))
    P.append(t(x + 12, 153, sub, 8.6, SUB, 400))
    arrow(x + lane_w // 2, 164, x + lane_w // 2, 186, LINE)

# ---- row 2: the four work packages --------------------------------------------------------------
P.append(t(40, 182, "", 1, SUB))
card(40, 190, 283, 168, TEAL, "ACCURACY (R13 everywhere)", [
    "features/corpus.py = ONE shared FTS",
    "retrieval (pooled in-app, leak-proof",
    "standalone); measures/ask/faulttree/",
    "cautions/pmcs/oneuse ride it.",
    "validate.py: quarantine withheld;",
    "conflicts drop garble pre-grouping.",
    "trust badges; niin_of canonical;",
    "qfloat; atomic migrations."])
card(333, 190, 283, 168, AMB, "VERIFY / OPS (one gate)", [
    "root VERIFY.bat = THE union gate",
    "(exit-code truth, run_timeout);",
    "VERIFY-099 forwards to it.",
    "test_routes + blanket POST sweep",
    "(281 green). rps_lint: unclassified",
    "page = FAIL. check_crlf.py gate",
    "(83 bats). safeguard backupdb",
    "(VACUUM INTO, keep-2) + gc fix."])
card(626, 190, 283, 168, PUR, "UI COHERENCE + A11Y", [
    "Tools menu 'Diagnose & decode'",
    "group; shared.js footer injector;",
    "esc()/toast() dedup on 29 pages;",
    "base.css onto 5 stray pages;",
    "all alert() -> toast();",
    "palette aria-modal + focus trap;",
    "modals role=dialog; dossier->/part",
    "banner; packet<->jobcard links."])
card(919, 190, 281, 168, RED, "FEATURES (safety + search)", [
    "operators tm:/nsn:/vehicle:/side:",
    "(parse_operators, param filters);",
    "oneuse.py /api/oneuse one-time-use",
    "TTY flags, cited, red /part card,",
    "into the /api/bom kit warnings;",
    "gap log /api/searchgaps + card;",
    "build_conflicts.py precomputed",
    "sweep sidecar (append-only, R6)."])

for cx in (181, 474, 767, 1059):
    arrow(cx, 358, cx, 384, LINE)

# ---- row 3: audit gate --------------------------------------------------------------------------
P.append(t(40, 404, "INDEPENDENT AUDIT (isolated /tmp copy — never the live 8.4 GB index)", 12, GRN, 700))
card(40, 414, 575, 150, GRN, "compile + integration gates", [
    "188/188 .py compile · 0 NUL/truncated files · CRLF PASS",
    "no route collisions (244 GET + 20 POST, overwrite detector)",
    "corpus.fts_pages callers signature-checked (6 modules)",
    "search LRU key = raw q + side -> operator variants can",
    "NEVER hit a stale cache entry (verified live)",
    "bom warnings shape matches /part + job-package consumers",
    "precomputed conflicts never rereads its own output"])
card(625, 414, 575, 150, GRN, "suites (all green)", [
    "test_routes 281/281 (GET+POST sweeps) · search_quality 23",
    "hardening 12 · patterns 20 · features 21 · pillars 23",
    "rps_lint PASS · verify_ui PASS · check_crlf PASS",
    "12 module self-tests: corpus measures conflicts oneuse",
    "bom analytics publog publogdiff signoff hybrid ask",
    "build_conflicts --selftest"])
arrow(327, 564, 327, 590, LINE)
arrow(912, 564, 912, 590, LINE)

# ---- row 4: harden + polish ---------------------------------------------------------------------
P.append(t(40, 610, "ADVERSARIAL HARDENING + POLISH", 12, RED, 700))
card(40, 620, 575, 118, RED, "hostile pass on the new endpoints (live fixture server)", [
    "/api/search · /api/oneuse · /api/searchgaps: 63 cases —",
    "missing/empty/10KB params, unicode, quotes, SQL-ish,",
    'vehicle:"unclosed · side:\'; DROP · repeated operators,',
    "FTS metacharacters, absurd limits",
    "RESULT: 0 x 5xx · 0 tracebacks · 0 fixes needed"])
card(625, 620, 575, 118, ACC, "polish", [
    "dead sqlite3/os imports removed (measures, faulttree —",
    "corpus owns retrieval now); v1.13.0 tags + shebangs on",
    "new modules; no stray debug prints / console.log;",
    "palette page-map: N/A (no new pages this wave)"])
arrow(620, 738, 620, 764, LINE)

# ---- footer: ship line --------------------------------------------------------------------------
P.append(box(40, 772, W - 80, 56, P2, GRN, 9, 1.4))
P.append(t(60, 795, "SHIPPED: VERSION 1.13.0 · CHANGELOG [1.13.0] + legacy parity · HANDOFF rewritten · snapshot row (UPGRADE)", 10.5, GRN, 700))
P.append(t(60, 813, "HOST-PENDING: run root VERIFY.bat (green gate) · R10 literal screenshot · optional BUILD-CONFLICTS.bat while OCR paused · safeguard backupdb manual", 9.2, SUB, 400))

print(render("".join(P) + "</svg>", os.path.join(BASE_DIR, "113-holistic-hardening")))
# END OF FILE
