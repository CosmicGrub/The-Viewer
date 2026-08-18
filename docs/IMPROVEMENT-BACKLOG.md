# THE VIEWER — Improvement Backlog (holistic review)

A grounded, categorized list of **90 candidate tasks** — tweaks, cleanups, and design tightening — from a
whole-program pass. Each line is one actionable item with a tag:

- **[RPS]** built/verified to keep modern·lite·legacy parity (stdlib / ES5-safe / no modern-only API).
- **[care]** touches a large file or shared path — do behind a snapshot, verify host-side.
- **[quick]** small, low-risk, high-clarity win.

Nothing here changes the corpus (read-only, R1) or removes data (append-only, R6). The **Testing plan** at
the end defines how every additive *and* the retroactive (RPS) compatibility get verified.

---

## A. Structure & modularization
1. Split `viewer_app.py` (~2,090 lines) into feature modules (`search`, `render`, `collections`, `callouts`, `threed`, `schematics`, `dossier`, `ingest`) imported by a thin app shell. **[care]** *(ties task #36; also the durable truncation fix.)*
2. Extract a shared `ui/shared.js` with `esc()`, `$()`, XHR/fetch helpers, `toast()` — remove the duplicated copies from ~14 HTML files. **[quick]**
3. Move the repeated `:root{...}` theme variables and common CSS into one `ui/base.css` loaded by every page. **[quick]**
4. Single source of truth for theme tokens: one CSS file + one Python `theme.py` the diagram generators import (they re-declare the palette in every `_make_*.py`). **[quick]**
5. Replace the long `if/elif` route chains in `do_GET`/`do_POST` with a declarative `{path: handler}` registry. **[care]**
6. Consolidate the NSN / FIG / part-number regexes into one `patterns.py` used by search, callouts, threed_refs, dossier. **[RPS]**
7. Create an `engine/features/` package; each feature registers its own routes via a small registry. **[care]**
8. De-duplicate the diagram generators with a shared `diagrams/_common.py` (box/text/wrap/panel helpers repeat in every script). **[quick]**

## B. Server robustness & correctness
9. Wrap every handler in one error boundary that logs the traceback and returns a clean JSON 500 (never drop the socket). **[care]**
10. Add a rotating error log (`logging`, size-capped) and surface "recent errors" in `/ops`. **[RPS]**
11. Central param parsing/clamping (ints, ranges, enums) so a bad `?limit=abc` returns **400**, not 500. **[quick]**
12. Path-traversal guard on `/page`: only render documents whose path is in the `documents` table; reject anything else. **[care]**
13. Max POST body size + read timeout to avoid a hung/oversized request. **[quick]**
14. `/healthz` endpoint returning `preflight --json` for the watchdog and the ops badge. **[RPS]**
15. Confirm the server only binds `127.0.0.1` by default and document how to expose it deliberately. **[quick]**
16. Graceful shutdown (handle SIGINT) that checkpoints WAL and closes connections cleanly. **[quick]**

## C. Search quality & relevance
17. Tune FTS5 ranking with `bm25()` column weights (title/NSN/tm > body). **[RPS]**
18. Boost exact NSN / part-number matches above body-text hits. **[RPS]**
19. Multi-term highlight in the page render `hl` (today only the first term burns in). **[care]**
20. "Did you mean / zero-result" suggestions from the vocab when a search returns nothing. **[quick]**
21. Expand `synonyms.json` (military abbreviations) + a small editor UI for it. **[RPS]**
22. Expose proximity/`NEAR` and phrase operators in the search hints + parser. **[quick]**
23. Small LRU cache of recent identical query+filter result sets. **[RPS]**
24. Optional stemming/tokenizer tuning (`unicode61`/porter) measured against recall. **[care]**

## D. Performance & efficiency
25. Pre-bake per-document grid thumbnails (dpi 24/70) so galleries paint instantly. **[care]**
26. `Cache-Control: immutable` + versioned URLs for static JS/CSS/handlers. **[quick]**
27. Gzip + cache the static UI files in memory once at startup. **[quick]**
28. Lazy-load 3D/schematic grid thumbnails with `IntersectionObserver` (modern) / fallback. **[RPS]**
29. Debounce `/api/suggest` type-ahead (~120 ms) and cancel in-flight requests. **[quick]**
30. Batch the dossier's 6+ queries into fewer round-trips. **[care]**
31. Consistent pagination on every list endpoint (some return all rows). **[quick]**
32. Cap the fitz LRU and connection reuse per RPS mode with explicit ceilings. **[RPS]**

## E. UI / UX tightening
33. One shared header/nav component instead of the per-page copy. **[quick]**
34. Consistent keyboard shortcuts across pages (`/`, `Ctrl-K`, `Esc`) + a shortcuts overlay. **[RPS]**
35. Loading **skeletons** instead of "loading…" text. **[quick]**
36. Consistent empty-state copy with a helpful next action. **[quick]**
37. Unify notifications: everything uses `toast()` (some pages use `alert`). **[quick]**
38. Dark/light theme toggle (once tokens are centralized, #4). **[RPS]**
39. Responsive/touch pass for tablet use in the bay (hit targets, viewport). **[care]**
40. Consistent deep-link/back behavior when a page is opened directly. **[quick]**
41. Persist all viewer prefs (match mode, thumbs, hl, mode) in one place. **[RPS]**

## F. Accessibility & input
42. ARIA roles/labels across interactive controls (extend the search combobox pattern). **[quick]**
43. Focus trap + restore in modals (3D gate, schematics gate, palette). **[quick]**
44. Color-contrast audit of the dark theme to WCAG AA. **[quick]**
45. Keyboard fallback for the loupe / 3D orbit / Circuit Lab (non-mouse). **[care]**
46. Honor `prefers-reduced-motion` in CSS (tie to the RPS lite "animations off"). **[RPS]**

## G. RPS / legacy parity
47. **Automated RPS lint**: scan ES5-tier `ui/*.html` for arrow/`const`/`let`/template syntax; fail the build. **[RPS]**
48. A per-page RPS manifest (modern-by-design vs ES5-safe) checked by the lint. **[RPS]**
49. CI fixture exercising the legacy **Poppler** render path. **[care]**
50. Legacy smoke test asserting the polyfills cover every used API (fetch/Promise/Set/Array.from). **[RPS]**
51. A `?mode=legacy` force flag so modern machines can test the legacy path. **[RPS]**

## H. Data integrity, safety & stability
52. Add `safeguard.py mirror` (off-disk) to the daily scheduled task when a backup dir is configured. **[RPS]**
53. Weekly consistent `viewer.db` backup (`snapshot --withdb`) + WAL checkpoint. **[care]**
54. Quarantine a damaged file (keep a forensic copy) before `recover` overwrites it. **[quick]**
55. Integrity tiles in `/ops`: last snapshot, verify status, free disk, OCR heartbeat age. **[RPS]**
56. Write an alert flag/log line when the disk guard trips or `verify` finds damage. **[RPS]**
57. Confirm atomic writes for `collections.db` / `reviews.db` user data. **[quick]**
58. Make every migration idempotent (`IF NOT EXISTS` / guarded `ADD COLUMN`) to kill the version-drift class. **[care]**

## I. OCR & ingestion pipeline
59. Per-page OCR **timeout** so one hung page can't stall a pass (pairs with the heartbeat watchdog). **[care]**
60. Capture OCR **confidence**; flag low-confidence pages for re-review. **[care]**
61. Auto-detect rotation/orientation for sideways scans before OCR. **[care]**
62. Incremental re-OCR of low-character pages at a higher DPI. **[RPS]**
63. Crawl-time dedup of identical PDFs across the corpus. **[quick]**
64. "Stuck page" report (pages repeatedly failing) surfaced in status. **[quick]**
65. Pages/sec + ETA refinement on the status page. **[quick]**

## J. Security & input validation (offline, defense-in-depth)
66. Audit every user-supplied `LIKE`/`GLOB` (scope filters) for parameterization. **[quick]**
67. Hard server-side caps on `limit`/`offset` regardless of client. **[quick]**
68. Same-origin check on POST endpoints. **[quick]**
69. Stop echoing raw exception strings to the client; log server-side, return generic. **[care]**
70. Canonicalize `/ingest` paths — only allow adding docs under configured roots. **[care]**

## K. Testing & QA
71. Add the new features to the regression suites: collections, callouts, threed_refs, preflight, `disk_ok`, mirror. **[RPS]**
72. Route smoke test: hit every GET/POST against a fixture DB; assert status + valid JSON shape. **[care]**
73. Wire the **ES5/RPS lint** (#47) into the test runner. **[RPS]**
74. Node JS-unit harness for UI helpers (`esc`, `hlTerm`, `circuitsim`, callout extract). **[RPS]**
75. Extend mutation testing to the new modules. **[care]**
76. Golden-file test for diagram generators (SVG output stable). **[quick]**
77. One `RUN-ALL-TESTS.bat` = `verify_all` + lints + mutation subset, host-side. **[RPS]**

## L. Documentation & onboarding
78. Refresh `ARCHITECTURE.md` for the new modules/features. **[quick]**
79. `USER-GUIDE.md` for mechanics (search → solve → packet → print) with screenshots. **[quick]**
80. `API.md` documenting every `/api/*` endpoint, params, and response shape. **[quick]**
81. Regenerate the stalled `CHANGELOG-VISUAL` host-side (it's frozen at 0.46 in-sandbox). **[care]**
82. A short "first 10 minutes" quickstart on the home page / help. **[quick]**

## M. Observability & ops
83. `/ops` live tiles: OCR heartbeat age, disk free, last snapshot/verify, current RPS mode. **[RPS]**
84. Optional structured JSON logs for ingestion + server. **[quick]**
85. A system-status badge (green/amber/red from `/healthz`) in the main header. **[RPS]**

## N. Packaging, config & deploy
86. One `engine/config.json` for port, paths, thresholds, backup dir (replace scattered env/consts). **[care]**
87. First-run setup wizard `.bat`: probe → install → snapshot → open. **[quick]**
88. Portable/Lite build parity check after modularization (`make_portable`). **[care]**
89. Single `VERSION` constant surfaced in the UI footer and `/healthz`. **[quick]**

## O. Small features / polish
90. Recent-searches history + copy-NSN/citation buttons + viewer keyboard paging (PgUp/PgDn). **[quick]**

---

## Testing plan — every additive AND the retroactive (RPS)

Every batch of the above ships only when **all** of the following pass, run **host-side** (coherent files):

1. **Snapshot first** — `run_safeguard.bat snapshot --label pre-<batch>` (rollback point; R1).
2. **Regression suites** — `VERIFY-ALL.bat` runs `test_pillars` + `test_features` + `test_truncation` + `safeguard verify`. Add new cases per #71 so each additive has a test.
3. **Route smoke test** (#72) — every endpoint returns a sane status + shape against the fixture DB.
4. **Retroactive (RPS) checks** — the **ES5/RPS lint** (#47–#50, #73): no ES6 syntax in ES5-tier pages; polyfill-coverage smoke test; and a `?mode=legacy` pass that exercises the lite/legacy render + UI paths. This is the "retroactive" gate — a change is not done until legacy still works.
5. **Isolation tests** for any logic touching the big, truncation-prone files (replicate the function on a temp fixture), per the anti-truncation protocol in `DEVELOPMENT.md`.
6. **Post-change verify + snapshot** — `VERIFY-ALL.bat`; if green and it's a milestone, snapshot again; if `verify` flags TRUNCATED/SHRUNK, `recover /all`.

Each item also keeps the standing rules: a data-flow **diagram** (R2/R3 dark + PDF), a **changelog** entry (R4) with its visual (R5), and a **legacy** changelog note (R7) recording parity.

## Suggested execution order
1. **Foundation (low risk, unblocks the rest):** A2–A4, A6, A8, G47–G48, K73, K77, B11, B14.
2. **Structure:** A1, A5, A7 (the modularization — task #36) behind a snapshot.
3. **Robustness & security:** B9–B16, J66–J70.
4. **Quality & perf:** C17–C24, D25–D32.
5. **UX & a11y:** E33–E41, F42–F46.
6. **Integrity/OCR/ops/docs/polish:** H, I, M, L, N, O.

---

## Completion log (append-only)

### 2026-06-10 — v0.96.0 "THE RESTRUCTURE" (phases 1–3 executed)
**DONE (in full):**
- **A1, A5, A7** — viewer_app.py → ~330-line shell + `engine/features/` (9 modules, verbatim moves,
  same DI pattern); declarative route registry (108 GET + 10 POST). Monolith preserved in
  `backups/pre-v0.96-restructure/` (md5-verified).
- **A4** — `engine/theme.py` single token source; `ui/base.css` mirrors it; `_common.py` imports it.
- **A6** — `patterns.py` adopted by search/render/parts/browse features (regex copies gone with the monolith).
- **A8** — `_common.py` already existed; now palette-sourced from theme.py (its old `RED #c4585a`
  normalized to the canonical `#e0564f` for future regenerations).
- **B9, B10, B11, B13, B15, B16** — one error boundary; rotating `engine/logs/server-errors.log`
  (tail in `/api/ops`); central param validation → 400; 8 MB POST cap (413, body unread, conn closed) +
  60 s handler timeout; 127.0.0.1-default documented; graceful Ctrl+C w/ WAL checkpoint.
- **B12** — verified: `/page` (and all render routes) address documents by id only; path comes from the
  `documents` table — traversal-safe by construction.
- **B14** — `/healthz` existed; now also carries `version`.
- **J66** (audited: all LIKE/GLOB parameterized), **J67** (hard row ceilings), **J68** (same-origin POST),
  **J69** (generic 500s, tracebacks to log), **J70** (ingest paths canonicalized + optional
  `VIEWER_INGEST_ROOTS` fence).
- **G47/G48** — rps_lint existed; all 31 UI files now classified (6 tiered overlays locked ES5;
  tagger.js comment false-positive fixed); **K73/K77** — lint + new `test_hardening.py` (K71, 12 checks)
  wired into `verify_all.py` / VERIFY-ALL.bat.
- **F46** — `prefers-reduced-motion` honored in base.css.
- **N88** — verified `make_portable.py` copytree picks up `features/` (Lite parity).
- **N89** — `VERSION` constant surfaced in `/healthz`, `/api/status`, `/api/ops`.
- **L78** — ARCHITECTURE.md §11 appended (current engine layout + hardened request lifecycle).

**PARTIAL (groundwork laid, finish in a later session):**
- **A2/A3** — `ui/shared.js` + `ui/base.css` created, served, lint-locked; pages still carry their inline
  copies (identical behavior). Strip page-by-page WITH browser verification; new pages must use the shared files.
- **#81** — v0.96.0 entry appended to `_make_changelog_visual.py`; 0.28→0.95 backfill + host-side
  regeneration still pending.

**Verified:** 75 regression + 59 route-smoke + 12 hardening tests green in the isolation tree; RPS GATE PASS.
Run `VERIFY-ALL.bat` host-side (coherent files) to confirm + snapshot.

**Still open:** C17–C24 (search quality), D25–D32 (perf), E33–E45 (UX/a11y), H52–H58, I59–I65 (OCR),
K72 exists / K74–K76, L79/L80/L82, M83–M85, N86/N87, O90.

### 2026-06-10 — v0.97.0 (same day, second batch: search quality + dedup finish + layout)
**DONE (in full):**
- **C18** exact-match boost (verbatim hit + exact part-number → `exact` flag, sorts first, stable).
- **C20** did-you-mean: offline edit-distance-1 suggestions from the FTS vocab + index-verified
  strongest-token fallback; clickable links in the home page empty state.
- **C22** `"phrase"` and `a NEAR b` operators pass through to FTS5; plain queries unchanged.
- **C23** 60 s / 200-entry LRU of identical query+filter result sets at the route layer.
- **C17** resolved **N/A by design**: `pages_fts` is single-column (body text only), so per-column
  bm25 weights don't apply; rank already uses bm25 and C18 covers the exact-first intent.
- **A2/A3 FINISHED**: 12 ES5 pages adopt `/base.css` + `/shared.js`; 11 inline `esc()` copies and
  12 inline `:root` palettes stripped (packet keeps paper-preview CSS; procedure/status keep their
  brighter green as a one-token override). Verified: lint green, `node --check` clean on every
  inline script, all pages 200 from the live fixture server.
- **E39 (the reported offset bug)**: header nav wraps at every width; labels never wrap internally;
  `main` grid `minmax(0,1fr)` + 1280 px breakpoint — sideways overflow is now impossible from the
  header/results layout.
- **#81 ROOT-CAUSE FIX**: `_make_changelog_visual_full.py` auto-generates the complete visual
  changelog (127 releases) from CHANGELOG.md at runtime — the strip can never stall again.
- **K71 extension**: new `test_search_quality.py` (15 checks) wired into verify_all/VERIFY-ALL.

**Verified:** all 8 suites green in the isolation tree. Rollback: `backups/pre-v0.97-batch/` (R1).

**Still open after v0.97.0:** C19/C21/C24, D25–D32, E33–E38/E40–E41, F42–F45, H52–H58, I60–I65,
K72/K74–K76, L79/L80/L82, M83–M85, N86/N87, O90.

### 2026-06-10 — v0.98.0 (third batch: nav consolidation, by direct request)
- Schematics + 3D Library moved INSIDE Collections (LIBRARIES cards); standalone header buttons
  removed; `/schematics` + `/3d` routes untouched (R1).
- ONE accessible 🧰 Tools menu (Solve it · Part dossier · How to do it · Look-Alike Parts ·
  Circuit Lab │ Add documents · Ops · OCR status · Part# review). Header: **16 items → 7**.
- Touches **E33** (shared header concept — partially: home page nav now structured) and finishes
  the practical goal of **E39**. Verified 10/10 acceptance + 7 suites + RPS gate.
  Rollback: `backups/pre-v0.98-nav/`.

### 2026-08-18 — v1.14.0 (50-finding 4-tier audit + UX pass + CI + doc reconciliation)
**DONE:**
- **I59** — per-page OCR timeout shipped: `VIEWER_OCR_PAGE_TIMEOUT` in `viewer_ingest.py`, paired
  with new `ocr_supervisor.py`'s heartbeat-staleness watchdog so a HUNG (not just crashed) pass is
  force-killed and recovered too. High-tier audit fixes, commit `04bd4a5` (range `04bd4a5`→`48c7a63`).
  See `docs/CHANGELOG.md` `[1.14.0]` for the full audit.
