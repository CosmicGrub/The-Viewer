# THE VIEWER — Handoff Note (reconciled 2026-08-24)

**Purpose:** hand this project to another chat/device without losing context. Read this + the canonical docs
(`docs/EXTRACTION-COVERAGE.md`, `docs/ROADMAP-1.1.md`, `docs/CHANGELOG.md`, `docs/ITERATION-SNAPSHOTS.md`,
`docs/MASTER-RECONCILIATION.md`).

> **Reconciliation note (2026-08-24):** this file had gone stale again — pinned to v1.14.0/2026-08-18 while
> `CHANGELOG.md` had moved on to **v1.15.0** (2026-08-19), a 30-commit, ~25-hour session (2026-08-18 20:40 →
> 2026-08-19 21:41) — the largest single body of undocumented work this project has carried at once, and
> `CHANGELOG.md` itself only caught up to it in a dedicated reconciliation pass on 2026-08-24 (PR #4), five
> days after it shipped. That pass wrote the `[1.15.0]` entry from the actual commit diffs (not just messages)
> via 8 parallel read-and-summarize passes; this file's "## LATEST — v1.15.0" section below is condensed from
> that same source, not re-derived independently. `docs/PROJECT-SUMMARY.md` and `docs/MASTER-RECONCILIATION.md`
> were reconciled to v1.15.0 in the same pass — all four docs now agree. `ITERATION-SNAPSHOTS.md`/
> `ITERATION-DASHBOARD.html` were **not** regenerated as part of this pass (see "Suggested next" below — that's
> `build_iteration_snapshot.py`, a separate host-run step, not touched here).
>
> **Reconciliation note (2026-08-18):** this file had gone stale again — pinned to v1.13.4/2026-08-09 while
> `CHANGELOG.md` and `ITERATION-SNAPSHOTS.md` had moved on to **v1.14.0** (2026-08-18), 9+ days and an entire
> 12-commit audit run behind. That run is the largest single effort in this project's history by commit
> count: a full 4-tier code audit (Critical/High/Medium/Low, 50 findings from the original manifest,
> `08bbb81`→`e4f4bd0`), a follow-up priority-5 UI/UX fix pass (`71c9c4c`/`a32aee9`), this repo's first-ever CI
> workflow plus the real `test_http.py` bug it caught on day one (`7c4a3ba`), and a Tier-1
> documentation/dependency/git-hygiene staleness pass (`3054dad`). The missing v1.13.5 entry (OCR confidence +
> bare-temperature fix, shipped 2026-08-09 — after the prior reconciliation's cutoff) is added below too.
> Every "current version"/"as of" claim in this file is now updated to **v1.14.0 / `3054dad` / 2026-08-18**;
> see "## LATEST — v1.14.0" below for the full breakdown. `docs/PROJECT-SUMMARY.md` and
> `docs/MASTER-RECONCILIATION.md` are due the same reconciliation in this pass — check their own headers
> rather than assuming from here if this note is ever stale relative to them.
>
> **Reconciliation note (2026-08-09):** this file had gone stale at v1.13.2 while `CHANGELOG.md` and
> `ITERATION-SNAPSHOTS.md` had already moved on to **v1.13.4** (both shipped 2026-08-08). No work has landed
> between 2026-08-08 and today — v1.13.4 is confirmed the true current state on disk (matches `VERSION` in
> `engine/viewer_app.py` and the top entry of `CHANGELOG.md`). The two missing entries (v1.13.3, v1.13.4) are
> added below; nothing else changed. `docs/PROJECT-SUMMARY.md` and `docs/MASTER-RECONCILIATION.md` were
> reconciled to v1.13.4 in the same pass — all four docs now agree.

## LATEST — v1.15.0 (2026-08-19) — Discovery Engine + in-app scanning, 5 deferred items closed, RPS Premium, OCR confidence end-to-end, reachability audit
**VERSION → `1.15.0`.** 30 commits, ~25 hours (2026-08-18 20:40 → 2026-08-19 21:41), effectively one
continuous session — see `CHANGELOG.md`'s `[1.15.0]` entry for the full per-commit breakdown; this section
condenses the same source into hand-off form.
- **Discovery Engine phase 1 + in-app scan/OCR** (`05ff17f`→`85df23c`): Add Documents now runs scan+OCR+parts
  as one in-app job with a real 4-stage progress panel (closes the "go run a .bat yourself" gap); new
  drag-and-drop single-file upload (`ingest_upload()`) with a live "where did my data go" breakdown panel;
  `crawl()` finally reads images/`.txt`/`.html` (`index_other()` — a raw image gets the SAME OCR/barcode/
  dimensional pipeline a scanned PDF page does, for free); `tables.py`'s `find_tables()` becomes a live 5th
  pipeline stage; `measures.py`/`schem_overlay.py`/`schemgraph.py` wired into the live scan (new `schematics`
  table, migration `0011`) with a new "dimensions" discriminator on `part_differences()`.
- **Full-codebase reachability audit → 3 more gaps wired in + a live toggle registry** (`099737f`, `e9eee88`):
  a 6-agent sweep of ~90 root-level modules found RPSTL parts-row extraction, pagetrim boilerplate stripping,
  and an automatic `keywords.json` refresh all fully built with zero live callers — all three wired in as new
  pipeline stages. New `engine/flags.py` centralizes the resulting 8 extraction opt-out toggles into one live
  registry (`python viewer_ingest.py flags` introspects current state).
- **5 previously-deferred items closed** (`ee3714d`→`d5fb9f8`): `tables_plus.py`'s cross-page `stitch()`
  wired into `/api/tables_plus`; new `engine/office.py` (`.docx`/`.xlsx`/`.pptx`/`.rtf` extraction, tier-gated
  to Win10/11); `dedup.py` gains a persistence layer + `/api/editions` + an "📚 Editions" button; `symbols.py`'s
  missing template-sourcing UI (3 new routes + a crop-and-save modal); `pagetrim.py`'s OCR-page path (the
  text-layer path already existed — OCR'd pages needed a separate post-pass design).
- **RPS Premium tier + hardware-adaptive deepening** (`bdc17cd`, `735455f`): a new opt-in `Premium`
  Settings choice (visual-effects layer, only ever activates on top of an already-`modern`-capable machine);
  9 real gaps closed where OCR ingestion/embeddings/HTTP-worker-pool/page-DPI/CAD rendering all had RPS tier
  flags available but unread.
- **OCR confidence threaded end-to-end** (`5116324`, `fcd0d75`): the real per-page confidence score (captured
  since v1.13.5 but never read outside its own column) now feeds the caution/procedure quality-flag heuristic
  AND finally renders on `torque.html`/`measures.html` — both pages were silently discarding an
  already-computed trust signal.
- **Functions + security pass: 52 confirmed fixes** (`c147614`) across all 265+ routes, plus a **32-fix
  icon/emblem quality pass** (`4b3224c`) resolving 7 palette-glyph collisions and real kiosk-mode touch-target
  gaps. A real barcode-loss bug (`54d2546`) — caught live by this repo's own CI on its very first run against
  the barcode pipeline — is fixed: an OCR text-engine failure was silently discarding an already-decoded
  barcode instead of persisting it alongside the "failed" page status.
- **Masterfile comparison audit + dedup performance + weekly DB backup + a mechanical reachability checker**
  (`40a811b`→`804bb08`): `masterfile.py`'s representative value is now a numeric median, not a
  most-common-string tiebreak; corroboration counting deduped by `(TM edition, page)`; `dedup.py` blocks
  comparisons by TM family before the O(n²) pass (real corpus scale: 39,683 docs, ~787M unblocked pairs); new
  weekly `viewer.db` backup task (the multi-GB index was never covered by any automatic task before this);
  new `audit_features.py [7]` — an AST import-closure reachability checker for the "built but never wired in"
  bug class that recurred across at least 9 prior commits.
- **Airgap NIIN-decision sync** (`875ffd5`): sign/verify a batch of review decisions for transfer between
  air-gapped units, fail-closed on tamper/wrong-key, never auto-resolving a genuine conflict.
- **UX pass**: `procedure_full()` now merges the preceding page's WARNING box and stops collapsing three
  different failure states into one "none found" message (`da0c996`); `readaloud.js` gets hands-free
  voice-controlled step navigation (`32614b7`); `palette.js`'s discovery pill relabeled and touch-sized
  (`00b1d4a`); `index.html` stops re-gating mechanics behind the session modal on every launch, routes
  torque/measure queries to an inline answer card, and touch-sizes app-wide (`cc02caa`); a final
  "confidence signaling" pass (`9b0e5b9`) surfaces OCR-badge tooltips, fixes an RPSTL exact-match ordering bug,
  adds a fuzzy-match "≈ approx" badge, and a new barcode-vs-OCR NSN conflict table.
- **Verified:** range ends at **46/46, ALL GREEN** (`9b0e5b9`), up from 26/26 at the start of [1.14.0]. 18 new
  test files across the range.
- **Docs:** `CHANGELOG.md` `[1.15.0]`; `VERSION` bump — both landed 2026-08-24 (PR #4), 5 days after the code
  itself shipped. This file, `PROJECT-SUMMARY.md`, `MASTER-RECONCILIATION.md` reconciled in the same
  2026-08-24 pass (see the reconciliation note at the top of this file).
- **Known, deliberately deferred:** `camelot_tables()` (3rd table engine pilot) stays unwired — a documented
  cv2/opencv-python binary-collision risk on version skew; `dedup.py` cross-TM-family duplicates aren't caught
  by design (the TM-family blocking that makes the O(n²) pass tractable trades that away deliberately).

## v1.14.0 (2026-08-18) — 50-finding 4-tier audit + UX pass + CI + doc reconciliation
**VERSION → `1.14.0`.** The largest single effort in this project's history by commit count (12 commits,
2026-08-17 → 2026-08-18): a full 4-tier code audit (Critical/High/Medium/Low, 50 findings from the original
manifest), a follow-up UI/UX audit + priority-5 fix pass, this repo's first-ever CI workflow (plus a real bug
it caught on day one), and the documentation-reconciliation finding the Medium tier itself explicitly
deferred until everything else was done (this file's update is part of that). Every tier: implement →
independent xhigh-effort multi-agent code review → fix every real review finding in its own follow-up commit
→ next tier — the same discipline applied to the review findings themselves in the CI-fix and staleness passes.
- **Critical (8 findings + 13 review findings, `08bbb81`→`086aed3`):** an infinite loop in
  `procedure_feature.py` (wrong loop-index direction on the blank-line branch) hung on virtually any real
  OCR'd page, backing `GET /api/procedure_full` and exhausting the bounded thread pool one request at a
  time — `test_procedure.py` (22 tests, never wired into the verify gate before now) now passes instantly ·
  `airgap.py verify()` fails closed against a file-existence oracle + a path-traversal escape ·
  `/api/airgap_manifest` + `/api/ingest_scan` now fenced by the same `VIEWER_INGEST_ROOTS` their sibling
  ingest routes already enforced · a negative `Content-Length` used to sail past the POST body cap and read
  until EOF, a malformed one desynced keep-alive — both rejected outright now · `GET /api/audit`/`/ops`/
  `/status` + (review pass) `command_status`/`ingest_status`/`provenance`/`integrity` now require the same
  token the POST auth path already enforced · `embed.py`'s hash-fallback semantic search used Python's
  per-process-randomized `hash()` — silently broken across every server restart on the documented
  zero-download default; switched to `zlib.crc32` + a version stamp (`embed.HASH_ALGO_VERSION`) so a stale
  pre-fix index now reports `ready=False` with a rebuild instruction instead of silently serving broken
  results · `build_publog.py`'s destructive rebuild now builds to a temp file and only swaps it in
  (`safeguard.atomic_replace`) once every table/index has committed · non-atomic sidecar-cache writes across
  `vectorize.py`/`schemgraph.py`/`routes.py ?fresh=1` moved to `safeguard.atomic_write`, plus a real race in
  that helper's own PID-only temp filename fixed (verified live: 16 threads, 320 racing writes, zero
  corruption) · `verify_all.py`'s test gate was a hardcoded filename allowlist — replaced with glob-based
  auto-discovery, surfacing **8 previously-never-run test suites** (~1,200 lines) in the same change.
- **High (12 findings + 15 review findings, `04bd4a5`→`48c7a63`):** `kg.py` now rebuilds to a temp file and
  atomically swaps in too, matching `build_publog.py`'s crash-safe pattern · a SQL condition in `xref.py`
  matched NULL-`fig_no` rows regardless of doc filter, leaking a part's loose rows into every other document's
  sibling-parts list · new **`viewer_ingest.py prune`** subcommand reconciles documents whose source file was
  deleted/renamed since the last crawl (fingerprint rename-detection, cascade-safe cleanup, dry-run default,
  missing-fraction abort threshold so an unmounted drive can't look like a mass deletion) · `migrate()` now
  snapshots the DB before applying any pending migration · the NSN regex across
  `patterns.py`/`core_pillars.py`/`partlocate.py` is now word-boundary-anchored (no longer matches inside
  invoice/PO numbers) · OCR preprocessing (deskew/denoise/binarize) existed but was never actually wired into
  the OCR path — now called · new **`ocr_supervisor.py`** + `run_ocr_auto.bat`: a heartbeat-staleness
  watchdog that force-kills and recovers a HUNG (not just crashed) OCR pass, plus a per-page timeout
  (`VIEWER_OCR_PAGE_TIMEOUT`); review pass caught a real bug in the watchdog itself — a leftover heartbeat
  from a *prior* session made it kill a brand-new healthy pass on its first poll, fixed by tracking the
  child's own start time as the baseline · **`safe_public_base()`** replaces trusting the raw `Host` header
  with a validated allowlist for the QR-code deep-link base URL · this repo's first CI workflow,
  **`.github/workflows/ci.yml`**, runs `verify_all.py` on every push/PR to `main` · 171 new regression checks
  across 3 new test files covering 7 previously-zero-coverage feature modules + the Tier-1 corpus-build
  pipeline.
- **Medium (19 of 24 findings + 14 review findings, `0059dc8`→`3590cb2`):** `xref.py` fabricated a fake NSN
  from any 13+-digit run instead of rejecting it — anchored · `dedup.py`'s shingle hashing had the same
  process-randomized-`hash()` bug as the Critical-tier `embed.py` fix — switched to `zlib.crc32` · a large
  foldout page could rasterize uncapped (48×36in @ 200 DPI ≈ 69MP against a 25MP intended ceiling) — fixed,
  extended to the Poppler fallback render path (which had no cap at all); review pass caught the ceiling's
  own 100-DPI floor could itself push a large enough page back *over* the cap — lowered · `masterfile.py
  build()` rewritten to stream into an incremental aggregator instead of materializing every measurement row
  into one Python list first (verified byte-for-byte output-equivalent across 10 rounds of randomized data +
  a dedicated edge case) · `kg.py neighbors()` now tries an indexed exact/prefix lookup before the slow
  substring scan; review pass caught the initial fix silently dropping valid substring matches whenever an
  exact/prefix match also existed — both queries now always run, merged + deduped · 8 batch-script hardening
  fixes (hardcoded personal-machine paths, silent-success anti-patterns, busy-looping retries, missing
  errorlevel checks) across `VERIFY.bat`/`FIRST-RUN.bat`/`RUN-ALL-VERIFY.bat`/`run_indexing.bat`/
  `RE-RENDER-CAD.bat`/`RUN-CAD-TIERS.bat`/`FIX-PORT.bat`/`KILL-ZOMBIE-ADMIN.bat` · 5 findings deliberately
  deferred with recorded reasoning (a genuine FTS5-vs-completeness tradeoff in `kg.py`, two
  duplicated-but-differently-wound CAD mesh builders left unmerged pending visual verification, this doc
  reconciliation itself), 1 N/A (an orphaned mockup with no live surface).
- **Low (6 findings + 2 review findings, `aad1709`→`e4f4bd0`):** removed a stray `.orig` backup file, a dead
  duplicate module (`crossval.py`, zero external callers), and a superseded batch script still carrying a bug
  its own successor's header documents fixing · fixed a `tables.py` short-circuit (`if False`) that always
  returned 0 regardless of actual content · fixed an unescaped SQL `LIKE` wildcard in `ocr_diag.py` that
  double-counted diagnostics into "other" · `verifystate.py`'s self-test module roster had drifted ~40%
  behind `VERIFY.bat`'s actual gate list — fixed, and hardened to cross-check itself against the real gate
  list going forward so this exact class of silent drift can't recur unnoticed.
- **Priority-5 UI/UX pass (10 findings + 20 review findings, `71c9c4c`/`a32aee9`):** a follow-up UI/UX audit
  (rendering, 3D/CAD, schematics, OCR-facing UX, motion/gestures, scanning) surfaced 52 findings; the 10
  highest-priority shipped here, each verified live against a running instance: `index.html`'s front door was
  ES6-only with no fallback — added a genuine **ES5 capability probe + minimal fallback shell**
  (RPS-Legacy/IE11/old-Firefox support, this app's own stated tier) · Interactive 3D + its SVG fallback
  gained **touch-orbit + pinch-zoom** (ported from CAD-rotate) + an always-visible zoom/reset row · the local
  AI-illustrative 3D model gained an on-canvas watermark on its default tab (R13: AI tiers must never
  visually pass as authoritative) · **Circuit Lab wires can now be selected and deleted individually**
  instead of only wiping the canvas · Deep Zoom now falls back to a chip list for OCR-only-page callouts
  instead of discarding them · safety callouts (WARNING/CAUTION/DANGER) now propagate their OCR-quality
  confidence signal to all 4 pages + the printed Job Card that render them · kiosk/glove-mode's touch-target
  minimum now covers `[role=button]` + the app-wide footer nav, with a `min-width` fix so circular badges
  can't distort into ovals · bin/shelf audit no longer fabricates a fake NIIN from a scan that isn't a clean
  9/13-digit NSN · the QR job-packet deep-link now explains itself instead of silently failing under
  loopback-only deployment · Look-Alike Parts gained an inline cited-figure thumbnail per variant. Review
  pass caught two severe regressions re-introducing the exact bugs the fixes above were meant to close (a
  rejected bin-audit scan could still silently discard the whole in-progress scan list; the NIIN-fabrication
  fix used `>=13` instead of `===13`, so 14+-digit codes were still fabricated) plus 18 more real findings (a
  legacy-fallback redraw path wiping the new 3D zoom bar/watermark, a checkbox-sizing regression, an
  unintended button-height change, a missed IPv6 deployment case, a blob URL leak, cleanup). New
  `engine/tests/test_uiux_fixes.py`: 174 checks.
- **CI (`7c4a3ba`; 3 root causes + 6 review findings):** CI's own Autofix flagged `test_http.py` failing on
  the very first PR this workflow ran against. 8 of 11 failing routes shared one root cause (the test's
  synthetic DB fixture had drifted from the real `documents` schema — missing `type`/`nsn`/`page_count`); 3
  more were flagged "non-JSON" but are legitimately binary-PDF endpoints by design; `/api/search` had one
  genuinely unguarded query. Stress-testing beyond CI's own config surfaced 3 more real, unrelated crashes
  fixed in the same pass: `registry.qint()` had no ceiling against SQLite's 64-bit bind range
  (`OverflowError` on an oversized numeric param), two routes passed `page` unvalidated into a bare `int()`,
  and a non-ASCII "digit" surviving a filename filter crashed a PDF response mid-write with a Latin-1
  encoding error. Review pass caught a genuine concurrency race in one of its own new guards (two threads
  could pair a valid cache signature with an empty map, permanently) — serialized under a lock, verified
  with a 64-thread stress test.
- **Staleness pass, Tier 1 (`3054dad`; 6 items + 10 review findings):** a separate full-project staleness
  audit (dependencies, git hygiene, docs-vs-reality, backlog-vs-fixed, dead code, repo bloat — `docs/audit/`
  + the "Viewer Drift Report" artifact from this session) found PyMuPDF's deprecated `fitz` import alias
  printing an unsuppressible warning on every server start — all 19 (+3 more, review pass) call sites
  migrated to `import pymupdf as fitz`. Also fixed: a real test-isolation bug that had already contaminated
  the live, git-tracked `keywords_user.json` sidecar with leftover test data (cleaned); two stale, fully-merged
  git branches deleted; 6 small hygiene fixes (a 14-release-stale version comment, hardcoded
  personal-machine paths, a dead `.gitattributes` rule, a drifting hardcoded test-file count). **This is only
  Tier 1 of 6** — dependency-version hardening, further doc reconciliation, and repo-bloat cleanup are
  tracked separately, not part of this entry (see "Suggested next" below).
- **Verified:** `engine/tests/verify_all.py` **26/26, ALL GREEN**, stable across every run from the CI-fix
  commit onward — the first point in this project's history the suite has been fully clean end to end (a
  2-failure baseline, `test_http.py` + `safeguard verify`, held through most of this run and was eliminated
  by the CI-fix and Tier-1-staleness commits respectively). 23 `test_*.py` files total now, all
  auto-discovered by glob (no hardcoded list) — 6 new this run: `test_seven_modules.py` (105 checks),
  `test_build_pipeline.py` (44), `test_prune.py` (22), `test_medium_fixes.py` (29), `test_uiux_fixes.py`
  (174), `test_ocr_supervisor.py` (11).
- **Docs:** `CHANGELOG.md` `[1.14.0]`; `VERSION` bump; `ITERATION-SNAPSHOTS.md`/`ITERATION-DASHBOARD.html`
  regenerated (`build_iteration_snapshot.py`) to include the new entry (both already current — don't
  regenerate again for this reconciliation); this file and `docs/PROJECT-SUMMARY.md` reconciled to v1.14.0 in
  the same pass (`PROJECT-SUMMARY.md`'s own header confirms it); `docs/MASTER-RECONCILIATION.md` is due the
  same treatment — check its own header rather than assuming from here.

## v1.13.5 (2026-08-09) — OCR quality signal + temperature extraction gap
**VERSION → `1.13.5`.** Prompted by a direct question ("check the current OCR accuracy numbers") that split
into two different answers: the *extraction* layer (`measures.py`'s regex over already-OCR'd text) had a
measured, root-caused 80% recall gap; the *OCR* layer itself (image-to-text transcription) had **no accuracy
signal of any kind** beyond completion percentage. Both addressed.
- **Fixed — temperature extraction missed bare F/C entirely.** `measures.extract()`'s temperature pattern
  required a `°` symbol or the word "deg"/"degrees" before F/C — a bare reading like "-40 F to 120 F" (a
  real, common way TMs write temperature ranges) extracted **nothing at all**. This was the entire gap behind
  `test_accuracy.py`'s 80% recall score. Added a bare-letter F/C alternative, guarded against the two real
  collision classes this corpus is full of: hyphen-suffixed military designators (F-15, F-16, F/A-18, C-5,
  C-17, C-130 — excluded via the same `(?!-\d)` technique already used for the 5W-30 oil-grade guard) and
  no-space battery C-rate notation (0.5C, 1C — excluded via a new whitespace-required check). `degF`/`degC`
  added to `_BARE_LETTER_UNITS` (the OCR-linearized-table newline guard, v1.13.4) since the new bare
  alternative has the identical bridging risk. `test_accuracy.py` now reports **100% recall (10/10)**.
- **Added — OCR confidence is now captured, not discarded.** RapidOCR computes a per-line confidence score
  for every text detection; `ocr_one()` used to reduce its output to text only and throw the score away —
  meaning the *only* OCR-quality signal in the entire app was "OCR ran" vs. "OCR did not run," never "OCR
  probably got this right." `ocr_one()` now returns `(text, confidence)` (page-level average of RapidOCR's
  per-line scores, 4dp; `None` for the Tesseract fallback path). New additive column `pages.ocr_confidence`
  (migration `0009_ocr_confidence.sql`, nullable, R1-clean — old rows read NULL until naturally re-OCR'd; no
  backfill pass was run against the live corpus). `coverage.overview()`'s `ocr` block now reports
  `avg_confidence`, `confidence_scored_pages`, `low_confidence_pages` (< 0.5 — a deliberately conservative
  first-pass bar), feeding `/api/coverage` + `/api/command_status` (both already TTL-cached, v1.13.4).

## v1.13.4 (2026-08-08) — Full live-driving pass + parallel audit: 36 real bugs found and fixed
**VERSION → `1.13.4`.** Drove every core feature end to end in the real running app (search, part/dossier,
procedures/troubleshoot, job packet, 3D/CAD, schematics/Circuit Lab, PUBLOG, decode, master/coverage, command
center/status, review/collections, ask/learn/verify, command palette/kiosk) — not just the automated suites —
then ran a parallel static audit (7 finders → dedup → adversarial verify-by-refutation, every finding
independently re-derived from the real file before being trusted) for the same bug classes elsewhere.
**36 real bugs found and fixed**, every one root-caused with a live repro before patching.
- **Found live-driving (10):** search `?side=operator` filtered *after* the SQL `LIMIT`, silently starving
  common terms of results (fixed: over-fetch before filtering) · did-you-mean suggested OCR garbage (fixed:
  rank by document frequency) · 5 of 6 hardcoded example NSNs across `index.html`/`jobcard.html`/`demo.html`
  didn't match their labelled item in PUBLOG (all 6 replaced, verified round-trip) · `faulttree.py` had no
  dedup across the corpus's confirmed duplicate-document ingestions (fixed: dedup by `(tm, page, symptom)` +
  `dupe_copies` count) · `/api/command_status` + `/api/integrity` had zero caching on 12-53s / 32-49s
  aggregates, reading as `/command` and `/verify` silently hanging (fixed: 60s/300s TTL caches) ·
  `measures.py`'s torque regex missed Unicode dot variants ("854 N•m" silently mislabeled as force — surfaced
  as a generated quiz question asking "what is the force" with Newton-only answers) + a hyphenated "25 N-m"
  never matched at all (both fixed) · **`verifystate.py` + its route had a 3-bug chain meaning `/verify` had
  found ZERO logs, ever, since the v0.96.0 restructure**: wrong log filename (`verify_099.log` vs the real
  `verify.log`), a pass-counting regex blind to the current log format, a false-positive failure trigger on a
  PASS line that happened to quote an "Error:" string, plus a separate off-path-depth bug (2 `dirname()` hops
  instead of 3, since this code moved into the deeper `engine/features/` during the restructure) — all fixed;
  `/verify` now correctly shows "✓ GREEN · 629 PASS markers".
- **Found by the audit (26):** **12 resource leaks** (same `db_integrity()`-shaped connect-succeeds/
  query-throws/close-skipped pattern already fixed in v1.13.3) across `collections_feature.py`,
  `fieldnotes.py`, `features/parts_feature.py` (×3), `features/browse_feature.py`, `specparse.py`,
  `figuresheet.py`, `safeguard.py` (`_sqlite_backup`), `masterfile.py`, `kg.py`, `tmrev.py` · **3
  sidecar/dedup/caching issues**: `sides_feature.save_override()`'s unbounded write-only log (same waste
  class as the v1.13.3 keywords bug), `procedures_feature.procedure_for()`'s wrong dedup key (same
  duplicate-corpus-doc bug as faulttree.py, different file), `/api/coverage`'s missing cache (same problem as
  `/command`, different route — now sharing one `_coverage_overview_cached()`) · **10 regex/classification
  bugs**: `rpstl.py` could mislabel the SMR code AND manufacturer identity (fixed by reusing `smrdecode`'s
  full curated-table decode instead of a first-letter check), `smrdecode.py`'s own character-class typo
  (excluded `L`, so real `ML`/`AL` codes could never be found) and its `scan()`'s 2-letter-prefix-only check
  (flooded false positives, e.g. "PARTS" → "PA"), `standards.py`'s prefix-matching **fabricated item names**
  for uncatalogued series sharing leading digits with a curated one (e.g. "AN9600-5" → the curated AN960
  washer) — directly against its own "never fabricate" docstring — plus a case-insensitive match that read
  the English word "an" as an AN hardware code, `measures.py`'s bare-W pattern misread SAE oil-viscosity
  grades ("5W-30") as negative wattage and its zero-whitespace number-unit gap could bridge across a
  newline in OCR-linearized tables, `fluidsmatrix.py`'s same zero-whitespace ambiguity let an RPSTL item
  suffix ("12L") displace a real capacity spec, and a "seen system" flag that gave up on the FIRST phrase
  occurrence even with no data nearby, silently losing a real spec appearing later in the same document ·
  **2 misc**: `ingestpipe.scan_folder()`'s `cap=` only broke the inner loop, so `os.walk()` kept traversing
  the whole remaining tree regardless (a folder-scan endpoint could hang on a large drive despite the cap
  existing to prevent exactly that), and a literal U+FFFD Unicode replacement character baked into
  `pinouts.py`'s wire-colour table (a save/encoding accident, confirmed via hexdump).
- **Verified:** regression suites 135/135; full `VERIFY.bat` run three times as fixes landed (the one
  mid-session `test_hardening` failure was a transient port-cooldown artifact from a standalone test run
  moments earlier, reproduced and explained, absent on the next clean run); final run: **RESULT ALL GREEN,
  563 PASS / 0 FAIL, 658/658 files intact.**
- **Deliberately deferred (documented, not fixed):** `measures.py`'s broader bare-number-fused-to-single-
  letter-unit ambiguity (e.g. "489A" reading as "489 Amps") needs corpus-wide regression testing first. A
  live analytics record carrying an old bad NSN was traced but left alone (R6 append-only, real historical
  data — flagged for the user, not silently altered).
- **Docs:** `CHANGELOG.md` `[1.13.4]` + legacy parity; `VERSION` bump; `ITERATION-SNAPSHOTS.md`/
  `ITERATION-DASHBOARD.html` regenerated (R10 integrity confirmed, all 217 versions present). No new diagram
  (R2/R3) — this is a bug-fix pass, not a feature addition, same precedent as v1.13.3.

## v1.13.3 (2026-08-08) — VERIFY.bat confirmed GREEN on host: two real bugs found + fixed
**VERSION → `1.13.3`.** `VERIFY.bat` had never been confirmed green on an actual host for the v1.13.0–1.13.2
work. Running it end-to-end surfaced two real bugs, both root-caused with an isolated repro before fixing:
`safeguard.db_integrity()` leaked its SQLite connection on the error path (deterministically breaking the
very next write on Windows — fixed with `try/finally`), and `search_feature.user_keywords_save()` appended
every submitted keyword group with no dedup (29 identical duplicates had silently accumulated in the live
`keywords_user.json` from repeated test/route-sweep traffic — fixed with the same case-insensitive dedup its
sibling `user_tags_add()` already had; the 29 duplicates cleaned to 1). Re-baselined the stale `safeguard.py`
vault snapshot. Final `VERIFY.bat`: **RESULT ALL GREEN, 563 PASS / 0 FAIL, 658/658 files OK.**

## v1.13.2 (2026-07-18) — Retroactive Post-Support: run-mode is now a saved Settings choice
**VERSION → `1.13.2`.** The RPS runtime mode (`modern`/`lite`/`legacy`) is no longer env/CLI-only — it's a durable
user choice. New `engine/settings.py` (stdlib-only, `safeguard.atomic_write` + atomic-rename fallback, fail-open
read / fail-loud write) persists it to `index/viewer_settings.json`. `status.html` gets a **Run mode** card (Auto ·
Performance · Retroactive Post-Support) showing resolved mode + reason, hardware recommendation, page-cache size;
`POST /api/rps_mode` persists + re-applies live, `GET /api/rps` reports saved setting + `recommended_mode`.
`rps.mode_for_setting()` maps the choice to a concrete mode; `sysprobe.py` surfaces `recommended_run_mode`.
Precedence (R1): `VIEWER_MODE` env (back-compat) > `VIEWER_RUN_MODE` env > saved setting > `auto`. Verified: 5
changed files compile, 22 isolation tests + 13 live-wiring tests green, audit 0 FAIL/0 WARN (150 unique route
decorators). Diagram: `docs/diagrams/53-rps-run-mode-setting.{svg,pdf}`. **R10 screenshot still
pending host-side** (`/status` Run-mode card).

## v1.13.1 (2026-07-18) — AI-generated 3-D models: illustrative tier (Meshy import lane)
`localmodel.py` gains an AI illustrative tier: drop an AI-generated `<NSN>.obj|.stl` (e.g. a Meshy image-to-3D
export) into `index/models3d/ai/` and it loads in the Interactive 3-D tab with a red **"AI-GENERATED
APPROXIMATION — not to scale, not for part ID or measurement"** banner. `localmodel.find_any()` returns
`(path, fmt, tier)`. **R13 accuracy boundary enforced structurally:** an authoritative model in `models3d/` always
wins over an `ai/` one — a generated mesh can never shadow a real one; `/partdiff` stays text/DB-only and never
touches these meshes. Back-compatible: `find()` unchanged.

## v1.13.0 (2026-07-18) — HOLISTIC HARDENING: dev-team review implemented — trust everywhere, one verify gate, UI coherence, safety features
**VERSION → `1.13.0`** (shipped; `backups/pre-v1.13` is the rollback point, R1). A four-lane parallel implementation
of the dev-team review (ACCURACY · VERIFY/OPS · UI · FEATURES) on top of the concurrent groundwork (pooled
`viewer_app.doc_path()`, exposure posture), then an independent audit + adversarial hardening + polish pass.
- **FEATURES:** fielded search operators **`tm:` / `nsn:` / `vehicle:` / `side:`** (`search_feature.parse_operators`,
  parameterized filters, quoted values, home-page hint, `test_search_quality` 23 green) · **`oneuse.py` +
  `/api/oneuse`** one-time-use / torque-to-yield / discard-after-removal fastener flags (R13 extractive + cited;
  red card on `/part`; merged into the `/api/bom` kit as cited `warnings`) · **zero-result GAP LOG** (`gap` events →
  **`/api/searchgaps`** + a `/command` card: what the corpus could NOT answer) · **`build_conflicts.py` +
  `BUILD-CONFLICTS.bat`** precomputed conflict sweep into append-only `index/conflicts.db`; `/api/conflicts` serves
  fresh exact-subject sweeps instantly (`precomputed: true`), falls back live otherwise.
- **ACCURACY (R13):** `features/corpus.py` = the ONE shared FTS retrieval (measures/ask/faulttree/cautions/pmcs/
  oneuse all ride it; pooled in-app, leak-proof standalone) · `validate.py` woven into `/measures` (per-row
  `quality`; quarantined garble withheld-but-returned) and `conflicts.detect` (quarantined values dropped
  pre-grouping — garble can't fabricate a safety conflict) · trust badges on measures/ask/conflicts/publogdiff ·
  `patterns.niin_of()` canonical (publog/publogdiff/xref_feature/build_publog delegate) · `hybrid._GLOSS` lock ·
  `sessions_feature` rollback · `signoff.py` DDL-once + RO reads · `registry.qfloat` · `viewer_ingest.migrate()`
  atomic per-migration transactions.
- **VERIFY/OPS:** root **`VERIFY.bat`** = THE authoritative union gate (exit-code truth, `run_timeout`-wrapped;
  `VERIFY-099.bat` forwards) · `test_routes.py` blanket **POST** sweep added to the GET sweep (**281 green**) ·
  `rps_lint.py` unclassified page = FAIL · NEW `engine/tools/check_crlf.py` (repo CRLF gate; 20 engine bats fixed,
  83 verified) · `safeguard.py backupdb` (VACUUM INTO + disk guard + keep-2; **manual — run when wanted**) + fixed
  dead `gc` CLI branch · `run_ocr_auto.bat` post-run gc.
- **UI:** Tools menu "Diagnose & decode" group on `index.html` · `shared.js` footer nav injector (+ `#vw-footer` in
  base.css) · `esc()`/`toast()` dedup across 29 pages (all load `/shared.js`; `verify_ui.py` dedup guard) ·
  base.css linked into schematics/threed/circuitlab/demo/cadtex_test · all `alert()`→`toast()` · `palette.js`
  aria-modal + focus trap · index modals `role=dialog` · dossier→`/part` banner · packet↔jobcard cross-links.
- **AUDIT (this session, isolated /tmp copy — never the real 8.4 GB index):** 188/188 .py compile, 0 NUL/truncation;
  no route collisions (244 GET + 20 POST); search-LRU key verified operator-safe (raw `q` + `side` in the key —
  no stale-cache path); all `corpus.fts_pages` callers signature-checked; bom `warnings` shape matches `/part` +
  job-package consumers. Suites: routes **281** · search_quality 23 · hardening 12 · patterns 20 · features 21 ·
  pillars 23 · rps_lint / verify_ui / check_crlf PASS · 12 module self-tests PASS. **Adversarial:** 63 hostile
  cases on `/api/search` + `/api/oneuse` + `/api/searchgaps` (10KB params, unicode, SQL-ish, `vehicle:"unclosed`,
  `side:'; DROP`, repeated operators) → 0×5xx, 0 tracebacks, **0 fixes needed**. Polish: dead `sqlite3/os` imports
  out of measures/faulttree; v1.13.0 tags + shebangs on the new modules.
- **Docs:** CHANGELOG `[1.13.0]` (2026-07-18 final entry; the 07-03 preliminary draft is retained below it per R6)
  + legacy parity; diagram `docs/diagrams/113-holistic-hardening.{svg,pdf}` (`_make_113_holistic.py`); iteration
  snapshot row appended (R10 **literal screenshot still pending host-side** — server not running in the sandbox).

### RUN THESE ON THE HOST (updated 2026-08-24, was "2026-08-18")
1. **`VERIFY.bat`** (→ `engine/tests/verify_all.py`) — ✅ **DONE, confirmed GREEN**, repeatedly through
   v1.13.4, every tier of the v1.14.0 audit run, and every commit of the v1.15.0 session — the range ends at
   **46/46, ALL GREEN** (`9b0e5b9`), up from 26/26 at the start of v1.14.0. CI (`.github/workflows/ci.yml`)
   runs the same gate on every push/PR to `main`; the CI-fix work landing alongside PR #3's merge into this
   pass (see `CHANGELOG.md`) also fixed a tesseract-binary gap and a Windows-only-font gap in the CI runners
   themselves, plus made `verify_all.py` print full output on a suite failure instead of just its last 3 lines.
   `VERIFY-099.bat` still forwards to it.
2. **R10 screenshot:** capture the running app (e.g. `/part` red one-use card, `/command` gap card, or home with the
   operators hint) at `127.0.0.1:8765` → `docs/screenshots/`. **Still not done as a saved artifact** — unchanged
   by either the v1.14.0 audit run or the v1.15.0 session, both of which verified extensively live-in-browser but,
   per the same established pattern, didn't save screenshots either. **To finish R10:** capture and save at least
   one real screenshot per major page into `docs/screenshots/` using the `<version>-<page>.png` convention.
3. Optional while OCR is paused: **`BUILD-CONFLICTS.bat`** (precompute the conflict sweep; append-only sidecar) —
   still not run; `index/conflicts.db` doesn't exist yet.
4. **`safeguard.py backupdb`** — a manual entry point (`run_backupdb.bat`) has existed since v1.15.0, **and**
   `register_snapshot_task.bat` now also registers a weekly automatic task
   (`THE_VIEWER_WeeklyDBBackup`, Sunday 03:00) so the multi-GB `viewer.db` finally has *some* automatic
   protection beyond the source-file snapshot vault. Neither has been confirmed run against the real
   production index on this host yet — worth checking the scheduled task is actually registered
   (`schtasks /query`) and has fired at least once.
5. **Re-baseline the pre-OCR safeguard snapshot** — ✅ **DONE**, repeatedly, through v1.13.4 (baseline at that
   point: `SNAP_20260808_184421_v1.13.4-changelog`, 658/658 OK). Not confirmed re-baselined again during either
   the v1.14.0 or v1.15.0 sessions — worth a fresh snapshot next time `safeguard.py` runs on the host, now that
   v1.15.0's changes (including two new migrations, `0011`/`0012`) are on disk.

## v1.10 → v1.12.9 (2026-07-02 → 07-03) — compressed (full detail in CHANGELOG.md)
- **1.10.0 Recommendations wave:** `rpstl.py` structured RPSTL import + `crossmethod.py` cross-method agreement
  scoring; the **200-idea roadmap** (`docs/ROADMAP-200.md`, Vol.2).
- **1.11.x Fleet readiness:** `intervals.py` service intervals + `fluidsmatrix.py` per-system fluids/capacities +
  `commonality.py` fleet shared-parts + **`/readiness`** page (1.11.0); shift-handover digest `handover.py`
  (1.11.1); PMCS worksheet DA-2404-style `forms.py` + `/api/form_2404` (1.11.2); **bulk folder ingestion**
  `ingestpipe.py` + `BULK-INGEST.bat` (1.11.3); first host VERIFY-099 fixes — RPS `let`-in-comment, Windows
  atomic-rename retry (`_replace_retry`), no-truncation false positives (1.11.4).
- **1.12.x Decoder + safety batch:** air-gap signed update package `airgap.py` HMAC-SHA256 fail-closed (1.12.0);
  standards designation decoder `standards.py` (1.12.1); DA-2407/5990-E `build_2407` (1.12.2); NSN-structure
  decoder `nsndecode.py` (1.12.3); SMR decoder `smrdecode.py` (1.12.4); CAGE/NCAGE validator `cage.py` (1.12.5);
  harness continuity trace `harnesstrace.py` (1.12.6); VERIFY-099 hang-proofing + `run_timeout.py` (1.12.7); MAC
  parser `macchart.py` + `/api/mac` (1.12.8); **1.12.9 DEEP AUDIT** — the green `test_routes 87/87` was testing
  NONE of the v1.12 work (hardcoded list): curated 87→106 + **blanket GET crash-sweep** (new routes auto-covered
  forever), the decoders got their **`/decode`** page + palette command (they had been unreachable), 24k fuzz over
  the six new modules (0 crashes), `/reference`→`/decode` rename (collision).

## v1.13.0 preliminary groundwork (2026-07-03, concurrent session) — kept for context
Unified data access (`corpus.py`, `doc_path()`), startup auto-optimizer (WAL + bg indexes), error-boundary `_sent`
hard contract, `safeguard.atomic_write` everywhere, bounded worker pool, exposure posture (`VIEWER_AUTH_TOKEN`
off-loopback), `/part` cite fixes (incl. the `cautions`→`results` regression), home-page kiosk/a11y fix, VERIFY.bat
first cut. ⚠ **Process note preserved:** the three review subagents were told read-only but two wrote code; it was
competent and was independently re-verified to green — but treat autonomous subagent edits as UNVERIFIED and audit
them (memory `gotcha-review-agents-wrote-files`).

## v1.9.0 (2026-07-02) — Serviceability & safety graphics · kit/BOM · pinouts · training · field notes
**VERSION → `1.9.0`.** Built under **R13**. Additive/rollbackable (R1); read-only except append-only `notes.db`; no new deps.
- **`serviceability.py` + `/api/serviceability`** — wear/serviceable-limit extraction + a go/no-go "is my measured value
  in spec?" checker (serviceable/marginal/replace). **`torqueseq.py` + `/api/torqueseq`** — pattern + staged torques →
  a numbered bolt-pattern diagram. Both on `/part`.
- **`bom.py` + `/api/bom`** — complete kit (parts+qty + consumables + tools), into the job package. **`pinouts.py` +
  `/api/pinouts`** — connector pinout + wire-color extraction.
- **`training.py` + `/learn` + `/api/quiz`** — cited multiple-choice learn mode. **`fieldnotes.py` + `/api/notes`** —
  append-only cited tips with SME endorsement, on `/part`.

**Docs:** CHANGELOG `[1.9.0]` + legacy; dark diagram `docs/diagrams/190-serviceability-kit-training.{svg,pdf,png}`;
VERIFY-099 self-tests all six. **Deferred:** fleet commonality, service-interval/fluids readiness, wiring fault isolation
(all three since shipped in 1.11.0 / roadmap items).

## v1.8.0 (2026-07-02) — R13 trust layer: validation · integrity · human sign-off · TM currency · verification cockpit
**VERSION → `1.8.0`.** First batch under **R13 (above military grade)**. Additive/rollbackable (R1); read-only except
the append-only signoff sidecar; no new deps. Every new pure module self-tested.
- **`validate.py` + `/api/validate`** — quarantines garbled/impossible extracted values (physical-plausibility + OCR-garble),
  flags suspect ones; **wired into `/part`** (a red banner withholds bad data). **`trust.py`** = one canonical trust level.
- **`verifystate.py` + `/verify`** — the verification cockpit (last VERIFY result, module roster, sidecar state,
  DB integrity). **`tests/test_accuracy.py`** — measured extraction recall/precision vs a ground-truth set.
- **`signoff.py` + `/review` + `/api/signoff`** — SME approve/reject/override → verified & locked, **append-only** audit
  trail. **`tmrev.py` + `/api/tmrev`** — flags when a newer TM revision exists (don't work from a superseded book).
- **`integrity.py` + `/api/integrity`** — SQLite corruption detection + SHA-256 tamper-evidence + online-safe backup.

**Docs:** CHANGELOG `[1.8.0]` + legacy; dark diagram `docs/diagrams/180-r13-trust-verify.{svg,pdf,png}`; governed by
**R13** (`rule-above-military-grade`).

## v1.7.0 (2026-07-02) — Unified part page + job PDF · troubleshooting · conflicts · offline Q&A · read-aloud · command center
**VERSION → `1.7.0`.** App-wide batch; additive/rollbackable (R1), read-only (R6), no new deps. Every new pure module
is self-tested and fuzz-hardened (0 crashes / 3,000+ cases per target).
- **`/part`** — one fast pane per part (identity + supersession + parts + dims + torque + cautions + procedure +
  approximate model + a cross-manual **conflict banner**), via `/api/partsummary`. **`jobpack.py` + `/api/jobpack`** =
  the complete **job-package PDF**. Both linked from `/dossier`.
- **`/troubleshoot`** (`faulttree.py`) — parses MALFUNCTION→check→corrective-action into interactive fault trees.
  **`conflicts.py` + `/api/conflicts`** — flags where manuals disagree on a torque/spec (safety), cited + ranked.
- **`/ask`** (`ask.py`) — offline, extractive, **cited** Q&A (no LLM/network). **`readaloud.js`** — offline read-aloud
  + voice input, auto-injected app-wide by `palette.js`.
- **`/command`** (`/api/command_status`) — OCR % · coverage · PUBLOG state · Masterfile gaps at a glance.
- **`tests/test_newmodules.py`** — property/fuzz across publogdiff/dimscad/conflicts/faulttree/ask/hybrid/jobpack.

**Docs:** CHANGELOG `[1.7.0]` + legacy; dark diagram `docs/diagrams/170-partpage-solve-ask.{svg,pdf,png}`.

## v1.6.0 (2026-07-02) — Look-alike intelligence from PUBLOG + approximate 3-D
**VERSION → `1.6.0`.** Builds on the PUBLOG sidecar; all additive/rollbackable (R1), read-only (R6). `BUILD-PUBLOG.bat`
now loads five more FLIS tables (standardization/ISC, MOE/AAC, phrase/TECH_DOC, related-INC, CAGE status).
- **`publogdiff.py`** + `/api/publogdiff` (two parts) + `/api/publog_intel` (one part): characteristics **diff +
  fit-fingerprint %**, **interchangeability verdict** (GREEN/AMBER/RED) with substitutes + AAC/replaced-chain
  **supersession**, **RNCC/RNVC** exact-vs-similar decode + **inactive-vendor** flag, **PUBLOG↔TM crosslink**
  (TECH_DOC_NBR) and **nickname reconciliation** with clash warnings. Shown on `/publog` (intel cards + "⇄ Compare")
  and the new scanner-powered **`/binaudit`** (scan a shelf → flag look-alikes + obsolete).
- **`dimscad.py`** + `/api/dimscad`: approximate **3-D from dimensions** — parses named dims from PUBLOG
  characteristics, picks a primitive, and emits a dimensioned isometric SVG + a parametric OBJ (`?obj=1`) that drops
  into the 3-D library. "Approximate model" card on `/dossier`.

**Docs:** CHANGELOG `[1.6.0]` + legacy; dark diagram `docs/diagrams/160-lookalike-publog-dimscad.{svg,pdf,png}`.
**Host step:** `BUILD-PUBLOG.bat` (multi-GB; degrades gracefully until run).

## v1.5.0 (2026-07-02) — PUBLOG catalog · scanner · hybrid search · exploded view
**VERSION → `1.5.0`.** Five lanes, all additive/rollbackable (R1); corpus + the PUBLOG CSVs are read-only (R6):
1. **PUBLOG/FLIS federal catalog** — `build_publog.py` + `BUILD-PUBLOG.bat` stream the ~16 GB DLA PUBLOG export
   (`C:\Users\User\Desktop\publog`) into a NIIN-keyed **`index/publog.db`** (nomenclature, manufacturer part numbers +
   CAGE, item characteristics, weight/cube, cancelled/replaced NIIN). `publog.py` + **`/api/publog`** (NSN/NIIN lookup
   and reverse `?pn=`), a **`/publog`** page, and a Federal-catalog card on `/dossier`. Offline, no links (R11).
2. **Hand scanner + camera** — `scanner.js` is a global keyboard-wedge listener (auto-injected app-wide by palette.js):
   scan a bin/part label on ANY page and it routes the NSN/part number to the catalog. `/scan` adds offline camera
   scanning via the native `BarcodeDetector`.
3. **Hybrid + glossary search** — `hybrid.py` + `/api/search_hybrid`: acronym/glossary query expansion, RRF fusion of
   keyword + semantic, and fuzzy NSN "did you mean" (grounded in PUBLOG). The home search now shows acronym + NSN hints
   (ranking unchanged).
4. **Exploded / assembly view** — `/exploded` turns a figure into numbered hotspots + a step-through assembly order
   (disassembly toggle, dimensions overlay); linked from `/dossier` + palette.

**Docs:** CHANGELOG `[1.5.0]` + legacy; dark diagram `docs/diagrams/150-publog-scanner-search.{svg,pdf,png}`.

## v1.4.0 (2026-07-02) — Bay-floor batch
**VERSION → `1.4.0`** (`engine/viewer_app.py`). Four lanes shipped together, all additive/rollbackable (R1), corpus read-only (R6):
1. **Offline QR** — `qrgen.py` + `/api/qr` render a QR encoding a deep-link to the part's dossier on THIS server (URL from the request `Host` header) so a phone / 2nd bay tablet on the same LAN scans straight to it. Backend order: **segno**(SVG) → **qrcode+Pillow**(PNG) → friendly 503. QR appears on the printable `/packet` header (self-hides if no backend). `segno` now installed by `INSTALL.bat` (recommended tier).
2. **Masterfile spec-sheet + coverage** — `specsheet.py` + `/api/specsheet` (1-page leading-particulars PDF from `masterfile.db`); `/mastercov` dashboard (least-covered first, missing-dimension chips, per-subject PDF). Buttons on `/master`.
3. **Confidence** — `masterfile._confidence(f)` → high / medium / review / low, surfaced on `/master` as a colored badge + legend.
4. **Kiosk mode + ops** — `body.kiosk-mode` (base.css: bigger text, ≥44px touch targets) toggled from the command palette, persisted in `localStorage`, applied app-wide. `VIEWER-MENU.bat` launcher. `verify_ui.py` ASCII console guard.

**Docs:** CHANGELOG `[1.4.0]` + CHANGELOG-LEGACY `[1.4.0-legacy]`; dark diagram `docs/diagrams/140-bayfloor-batch.{svg,pdf,png}` (R2/R3/R5). The v1.2–v1.3.8 waves (extractors, IETM/KG, vision scaffolds, Tools-menu fix) sit underneath, unchanged.

## Where the build is (historical — v1.1 wave)
- **VERSION → `1.1.4`** (`engine/viewer_app.py`). v1.0.0 was cut and verify-green; that session added the
  **v1.1 extraction + enrichment + Masterfile wave** on top (1.1.0 → 1.1.4).
- Everything is additive and rollbackable (R1). The corpus at `E:\ALL MILITARY TMS` was **not touched**; all new data
  lives in **append-only sidecars** under `index\` (R6).

## v1.1.3 / v1.1.4 (added after the first extraction wave)
- **1.1.3 — Wayback-everything.** The gap-fill crawler now harvests candidate links from **many sources** per subject
  (Internet Archive items, optional web-search plugin `engine/enrich_search.py`, and a seed list `index/enrich_seeds.txt`)
  and **routes every link through the Wayback Machine** (availability, or Save Page Now via `--save`) before extraction.
  Provenance now stores the archived URL + original URL + snapshot timestamp. **Live-verified**: real searches → all
  links resolved to Wayback snapshots → 34 measurements recovered from one archived HMMWV spec page.
- **1.1.4 — The Masterfile.** `masterfile.py` + `BUILD-MASTERFILE.bat` consolidate corpus (`measures.db`, authoritative)
  + external (`enrich.db`) into ONE congruent `index/masterfile.db` + `docs/MASTERFILE.md`, keyed to the authoritative
  subjects. RAW + FILTERED layers. **No external links surfaced** — corpus rows keep their manual page cite; external
  web provenance stays inside `enrich.db`. Served at `/master`. `/measures` external block updated to drop the link.
- New host builders (run when OCR paused; `ENRICH` needs internet): `BUILD-TABLES.bat`, `ENRICH.bat`, `BUILD-MASTERFILE.bat`.
  Recommended order: `BUILD-MEASURES` → (`ENRICH`) → `BUILD-MASTERFILE`.

## What shipped in the v1.1.0 → v1.1.2 session
1. **`measures.py` — measurement / dimensional-data extractor (1.1.0).** Pulls every measured value (length, dia.,
   clearance/**tolerance**, weight, force, torque, pressure, capacity, electrical, temperature, flow, speed, rotation,
   angle) with value(s), range, tolerance, canonical unit, dimension type, context sentence, and cited page. New
   **`/measures`** page (grouped + filterable by type) works **live over FTS — no build step**. Optional
   `BUILD-MEASURES.bat` → `index\measures.db` for fleet-wide counts. Self-test: 19 measurements, all types — PASS.
2. **`tables.py` — structured-table extraction (1.1.1).** PyMuPDF `find_tables` over every page; flags **spec/dimension
   tables** (cells carrying units, via `measures`). `/api/tables?doc=&page=` live; `BUILD-TABLES.bat` → `index\tables.db`.
3. **`enrich.py` + `build_enrich.py` — external gap-fill (1.1.2).** The **corpus is authoritative**; this cross-references
   the **open internet** (Internet Archive full-text + **Wayback Machine**) **only to fill dimension types the corpus is
   silent on**. External values never override the corpus, are surfaced only where the corpus is blank, and are badged
   `external-unconfirmed` with full **provenance** (source, URL, Wayback ts, fetched ts). `/api/external` + a badged
   section on `/measures`. **App stays 100% offline** — only the opt-in `ENRICH.bat` crawler touches the network; the
   server only reads the append-only `index\enrich.db`. Self-test (mocked network + extractor) — PASS.
4. **Docs:** `docs/EXTRACTION-COVERAGE.md` (full map of every extraction/parse/detection method + the enrichment layer),
   changelog `[1.1.0]/[1.1.1]/[1.1.2]`, legacy `[1.1.x-legacy]`, dark diagrams **132/133/134** (SVG+PDF+PNG, R2/R3/R5).
   `/measures` added to the command palette.

## VERIFY wiring (current)
Root **`VERIFY.bat`** is the single authoritative gate (v1.13.0): exit-code truth per step, `run_timeout.py`
wall-clock guards, concise RESULT summary + `pause >nul` (the QuickEdit console-hang lesson), CRLF-safe.
`VERIFY-099.bat` forwards to it. It unions: audit · test_routes (GET+POST sweeps) · the regression suites ·
rps_lint · verify_ui · check_crlf · module self-tests · no-truncation completeness (R9). **The regression-suite
list is no longer hardcoded** — a v1.14.0 Critical-tier fix (`08bbb81`) replaced `verify_all.py`'s fixed
filename allowlist with glob-based auto-discovery, which is what surfaced 8 previously-never-run test suites
(~1,200 lines, including `test_procedure.py`'s 22 tests catching the live `procedure_feature.py` infinite
loop) in that same change. **`test_*.py` files auto-discovered by glob, 46/46 gates ALL GREEN as of `9b0e5b9`**
(v1.15.0, 2026-08-19) — up from 26/26 at the start of v1.14.0, itself the first point in this project's
history the suite was fully clean end to end; the count keeps climbing (18 new test files landed across the
v1.15.0 range alone). The old subroutine `call :body > log` pattern is retained — do **not** re-wrap the body
in CMD parens (the `( )` paren-block bug silently killed earlier host-verifies). If gate 7's `test_hardening`
step ever fails right after a standalone run of the same test file, it's very likely the same transient
port-8893 TIME_WAIT cooldown hit during the v1.13.4 session — re-run VERIFY.bat clean (no standalone test runs
immediately before it) before treating it as a real regression. **This same gate also runs in CI** —
**`.github/workflows/ci.yml`** (added in v1.14.0) invokes `verify_all.py` on every push/PR to `main`; it
caught a real `test_http.py` bug on its very first run (`7c4a3ba`), and again a real barcode-loss bug on its
first run against the barcode pipeline during v1.15.0 (`54d2546`) — plus, ironically, its own environment gaps
(no `tesseract` binary, a Windows-only test font) during the CI-hardening work that landed alongside the
v1.15.0/CHANGELOG reconciliation on 2026-08-24.

## Known gotchas still in force
- **Mount truncation:** sandbox reads of grown host files are truncated/stale; verify host-side or via the Read tool.
  Snapshot/verify HOST-SIDE (`safeguard.py` / root `VERIFY.bat`).
- **Never** write the big `viewer.db` through the mount; sidecars are written by host-run builders only.
- **LF-only .bat blink-crashes** — now gated mechanically by `engine/tools/check_crlf.py` (in VERIFY).
- Duplicate route paths silently override — audited at 244 GET + 21 POST (265 total, no collisions) as of
  v1.14.0; a real, mechanical check for a DIFFERENT bug class (built but never wired in — dead code, not a
  collision) was added in v1.15.0 (`audit_features.py [7]`, 0 FAIL/0 WARN against the live repo as of that
  session). The route COUNT itself hasn't been recounted since v1.15.0 added a real batch of new routes
  (RPSTL/schematics/tables stages don't add routes, but `ocr_backlog_start`, `ingest_upload`,
  `airgap_export_decisions`/`import_decisions`, and the 3 new `symbols_*` routes all do) — worth a fresh count
  next time the audit runs.
- Standing rules R1–R13 are **THE VIEWER-only**; do not carry them to other projects.

## Suggested next
1. **R10 screenshots** — still the one item from the v1.13.0-era host checklist not done as a saved artifact
   (see "RUN THESE ON THE HOST" above); unchanged by either the v1.14.0 audit run or the v1.15.0 session.
2. **`measures.py`'s deferred bare-unit-fusion ambiguity** (item "489A" reading as "489 Amps") — still open;
   needs corpus-wide regression testing before a safe fix; flagged since `CHANGELOG.md` `[1.13.4]`, not
   touched by v1.14.0 or v1.15.0.
3. **Staleness-audit Tiers 2, 5, 6** — `[1.23.0]`'s reconciliation pass found Tiers 3 (dependency/CI
   hardening) and 4 (repo bloat, env vars, Windows CI) were actually done on 2026-08-18 (`8f795bc`,
   `1b3c6d8`) and simply never reconciled here — corrected. Only Tiers 2/5/6 remain genuinely unstarted (see
   `docs/audit/` + the Viewer Drift Report artifact for what those cover). Note this is a DIFFERENT
   deferred-items list from the "5 deferred items" v1.15.0 closed (item 4 below, and distinct again from
   item 5's audit-reachability findings) — three separate tracking threads with similar names, easy to
   conflate.
4. **5 Medium-tier findings deliberately deferred from the v1.14.0 audit** (see `CHANGELOG.md` `[1.14.0]`,
   Medium-tier entry) — the tier's own duplicated `_box()` CAD mesh-builder cleanup this item used to also
   list was fixed on 2026-08-18 (`37d909b`, which also consolidated two more duplicated helpers and split
   the OCR lock timeout) and reconciled in `[1.23.0]`; removed from this line. (Not the same "5 deferred
   items" as v1.15.0's — those were tables_plus-stitch/Office-formats/dedup/symbols/pagetrim, flagged by a
   later, separate audit, and are now CLOSED.)
5. **v1.15.0's own deliberately-deferred items**: `camelot_tables()` (3rd table-extraction engine pilot)
   stays unwired into `/api/tables_plus` — a documented cv2/opencv-python binary-collision risk on version
   skew, not just unmeasured benefit; `dedup.py` cross-TM-family duplicates aren't caught by design (the
   TM-family blocking that makes the O(n²) pass tractable at real corpus scale trades that away deliberately).
6. Confirm the new weekly DB-backup scheduled task (v1.15.0) is actually registered and has fired on the real
   host (see "RUN THESE ON THE HOST" item 4); complete OCR → re-index; run `BUILD-CONFLICTS.bat` (first sweep,
   still never run) and `BUILD-MEASURES`/`BUILD-MASTERFILE` refreshes on the grown text layer.
7. ~~Real semantic embeddings + hybrid ranking~~ — **stale, corrected in `[1.23.0]`'s reconciliation pass**:
   `hybrid.py` already does real RRF fusion of keyword (FTS) + `embed.py` semantic search, confirmed directly
   (this item predates whenever that actually shipped and was never removed once it did). R12 catalog march
   continues (`docs/EXTRACTION-METHODS-CATALOG.md` — next cheapest uncaptured methods).
8. **5 more open PRs as of `[1.23.0]`, none merged yet** (each independently branched off `main`, each own
   spec+plan under `docs/superpowers/`): `[1.18.0]` measures.py unlabeled-bare-unit case remains genuinely
   open per its own design (needs real corpus data, not a quick fix); `[1.19.0]` home-page nav regroup;
   `[1.20.0]` search click instrumentation + heuristic re-rank (the actual learned re-ranker model is the
   real follow-on, gated on this merging and accumulating real click volume); `[1.21.0]` per-line OCR
   confidence capture (per-word specifically stays open, GPU-gated); `[1.22.0]` multi-column reading-order
   reconstruction. See each PR's own CHANGELOG entry for what's deferred within it.

<!-- END OF FILE -->
