# THE VIEWER — Complete Project Summary (duplication / hand-off kit)

**State: v1.15.0 · 2026-08-19** (rewritten 2026-08-08 from ~130 versions of drift, updated 2026-08-09,
reconciled 2026-08-18 after a 50-finding 4-tier audit + UX pass + CI + doc reconciliation, and reconciled
again 2026-08-24 after a 30-commit Discovery Engine / in-app scanning / reachability-audit session — see the
reconciliation notes below). This document + `docs/PORTING.md` (the copy checklist — reconciled to v1.13.2 on
2026-08-08, now several point releases behind again; not touched in this update, see §9) + `docs/CHANGELOG.md`
(the full version history) + `docs/MASTER-RECONCILIATION.md` (the cross-checked feature inventory this
rewrite is sourced from) + `docs/HANDOFF-NOTE.md` (the living session hand-off) are everything a new machine —
or a new collaborator/AI session — needs to duplicate this project and continue it without losing progress.
Treat all five as canonical; keep them in sync going forward.

> **Reconciliation note (2026-08-08):** this file had gone stale at "v0.98.0 · 2026-07-01" while the rest of the
> project had moved on 130+ versions to **v1.13.2**. `docs/CHANGELOG.md` and `docs/ITERATION-SNAPSHOTS.md` never
> drifted (each change appends to them directly); this hand-authored summary simply stopped being updated after
> the 0.96–0.98 restructure. Rewritten below against `docs/MASTER-RECONCILIATION.md` + `CHANGELOG.md` as source of
> truth. Nothing in the codebase changed as part of this rewrite — docs only. **Follow-up (same day):**
> `docs/PORTING.md` had the identical drift and has since been reconciled too — every cross-reference to it below
> now points at the current version, not the stale one.
>
> **Follow-up (2026-08-09):** bumped v1.13.2 → **v1.13.4** throughout. In between, a full live-driving pass +
> parallel static audit found and fixed 36 real bugs (v1.13.4, following v1.13.3's first-ever confirmed-green
> `VERIFY.bat` host run) — see §4's updated Dev/verify/ops line and §8's largely-cleared outstanding-items list.
>
> **Follow-up (2026-08-18):** this file had drifted again — still claiming "v1.13.4, nothing has shipped since
> 2026-08-08" while `main` had moved on to **v1.14.0** (HEAD `3054dad`). In between: a 12-commit, 50-finding
> 4-tier code audit — Critical (`08bbb81`→`086aed3`), High (`04bd4a5`→`48c7a63`), Medium (`0059dc8`→`3590cb2`),
> Low (`aad1709`→`e4f4bd0`) — a follow-up priority-5 UI/UX pass (`71c9c4c`/`a32aee9`), this repo's first-ever CI
> workflow plus a real bug it caught on day one (`7c4a3ba`), and a Tier-1 doc/dependency/dead-code staleness
> pass (`3054dad`). Every tier was independently xhigh-effort multi-agent code-reviewed, with every real review
> finding fixed before moving on. `engine/tests/verify_all.py` is now **26/26, ALL GREEN** — the first fully
> clean run in the project's history. Full detail in `CHANGELOG.md`'s `[1.14.0]` entry; §4, §6, and §8 below are
> the sections that actually changed in this reconciliation pass.
>
> **Follow-up (2026-08-24):** this file had drifted again — still claiming "v1.14.0" while `main` had moved on
> 30 more commits to **v1.15.0** (2026-08-19, ~25 hours of continuous work, `main` @ `9b0e5b9`). `CHANGELOG.md`
> itself only caught up to it five days later, in a dedicated reconciliation pass on 2026-08-24 (PR #4) —
> this file's update rides the same pass. In between: Discovery Engine phase 1 + in-app scan/OCR (drag-and-drop
> upload, dimensional/schematic detection wired into the live scan), a 6-agent full-codebase reachability audit
> that closed 3 more "built but never wired in" gaps (RPSTL extraction, pagetrim boilerplate stripping,
> automatic keywords refresh) plus a new mechanical checker (`audit_features.py [7]`) for that exact bug class
> going forward, all 5 previously-deferred items closed (tables_plus cross-page stitching, Office-format
> extraction, dedup/editions clustering, symbols crop UI, pagetrim's OCR-page path), a new opt-in RPS `Premium`
> visual tier + 9 real hardware-adaptive-engine gaps closed, OCR confidence finally threaded through to
> `torque.html`/`measures.html`, a 52-fix functions+security pass across all 265+ routes, a barcode-loss bug
> caught live by this repo's own CI, a masterfile/dedup audit, airgap NIIN-decision sync, a weekly full-DB
> backup task, and a UX pass (adjacent-page warning merge, honest failure states, hands-free readaloud
> navigation, touch sizing, inline search answers, confidence-signaling badges). `engine/tests/verify_all.py`
> is now **46/46, ALL GREEN**. Full detail in `CHANGELOG.md`'s `[1.15.0]` entry; §4, §6, and §8 below are the
> sections that actually changed in this reconciliation pass.

> **⚠ Architecture updated at v0.96.0 "THE RESTRUCTURE" (and 0.97/0.98), extended through v1.13.0.** Sections below
> describe the current shape:
> - `engine/viewer_app.py` is a **thin shell** (config, per-thread SQLite, RPS init, Handler, main). All domain
>   logic lives in **`engine/features/`**: `registry` (declarative `{path:handler}` routes + central param
>   validation), `routes` (every endpoint declared once), **`corpus.py`** (the one shared FTS retrieval layer used
>   by every search-adjacent feature, added v1.13.0), plus `search / parts / browse / procedures / render / ingest
>   / sessions` feature modules. DI unchanged (`<module>.core = viewer_app`); the shell re-exports every public
>   name, so `import viewer_app as V` still works for tests/scripts.
> - Dispatch is **one dict lookup inside one error boundary** (150 unique route decorators, 244 GET + 21 POST —
>   **265 routes** registered, audited, no collisions) — malformed input → clean **400**; rotating error log; 8 MB POST cap
>   (413 unread); same-origin POST check (403); ingest paths canonicalized. Shared front-end: `engine/theme.py` +
>   `/base.css` + `/shared.js` (dedup'd across all 29 pages).
> - **0.97** search-quality (NEAR/phrase handling, did-you-mean) + UI dedup. **0.98** nav consolidation
>   (Collections/Tools menus). **1.13.0** "HOLISTIC HARDENING" wove `corpus.py`/`validate.py`/`trust.py` through
>   every consumer and made **root `VERIFY.bat`** the single authoritative test gate (see §6).
> - **Rollbacks:** `backups/pre-v0.96-restructure/` (byte-for-byte monolith), `pre-v0.97-batch/`, `pre-v0.98-nav/`,
>   `pre-v1.13/` (current rollback point).

---

## 1 · Mission

An **OFFLINE search engine with a dynamic GUI** over a library of military Technical Manuals (modeled on
EMS-NG / IADS / Adobe — "the best of all worlds"), for vehicle mechanics. The five founding goals — all shipped:

- **A. Find anything** in the TM/PDF corpus fast — solutions to mechanical problems with minimal digging.
- **B. Many ways to search** — full-text, Ctrl+F in-document, Google-style offline type-ahead, fuzzy/slang keywords.
- **C. Complete instructional rundowns** — disassembly/assembly procedures, tools, and **clear differences between
  look-alike parts** and how to tell them apart.
- **D. Richer-than-the-PDF graphics** — dynamic diagrams and 3-D, simple AND advanced, for young mechanics and SMEs alike.
- **E. Effortless ingestion** of new PDFs/files into the system.

## 2 · The system at a glance

- **Server:** `engine/viewer_app.py` — pure Python **stdlib** `ThreadingHTTPServer`, default `127.0.0.1:8765`.
  Domain logic in `engine/features/` (see the architecture note above), DI via `module.core = viewer_app`.
- **UI:** plain HTML/JS pages in `engine/ui/` (no framework, ES5-safe for legacy hardware). Custom WebGL renderer
  `gl3d.js`; shared widgets (`loupe.js`, `partview.js`, `cadview.js`, `schemflow.js`, `palette.js`, `scanner.js`,
  `readaloud.js`, `shared.js`).
- **Data:** corpus at **`E:\ALL MILITARY TMS`** (READ-ONLY, never written) → indexed into **`index/viewer.db`**
  (~3.65 GB+: documents, pages, OCR text layer, parts, ref_nsn/FLIS). Every feature adds its own **append-only
  sidecar** database under `index/` rather than touching the core schema outside migrations (`index/publog.db` —
  the ~16 GB DLA PUBLOG/FLIS catalog — is the largest of these).
- **Tiers (RPS = Retroactive Post-Support):** `sysprobe.py` probes the host → modern / lite / legacy feature tiers,
  so the same codebase runs on an RTX-class Win11 box or a Win7/Vista shop-floor PC. **As of v1.13.2** the tier
  choice is a persisted Settings decision (Auto / Performance / Retroactive Post-Support), not just an env flag.
- **Two builds, one codebase** (`docs/FORKS.md`): the Advanced/GPU production build (RapidOCR on
  `onnxruntime-gpu`, 10–30× faster OCR) is the priority fork; `make_portable.bat` derives a Lite/portable build
  (finished index only, CPU-safe, one-click `SETUP.bat`/`START.bat`) for weaker machines. Same `viewer.db` schema
  either way.

## 3 · Standing rules governing every change (R1–R13, THE VIEWER-only — do not carry to other projects)

| # | Rule |
|---|---|
| R1 | Backwards-compatible + rollbackable; corpus read-only |
| R2 | Every addition ships with a data-flow diagram |
| R3 | Diagrams: professional dark theme + PDF (`docs/diagrams/_make_NN_*.py` generators → SVG+PDF+preview) |
| R4 | A `docs/CHANGELOG.md` entry with every change |
| R5 | + a graphical changelog explanation (CHANGELOG-VISUAL) |
| R6 | Append-only data — add, never remove |
| R7 | Legacy builds get a dual-track changelog (`docs/CHANGELOG-LEGACY.md`, branched at 0.37.0) with parity notes |
| R8 | Write a full HANDOFF note at session end / on request |
| R9 | Always use no-truncation discipline; verify completeness mechanically |
| R10 | Every iteration ships a **literal screenshot** of the running app — still owed, see §8 |
| R11 | 100% info retrieval incl. dimensions → Wayback-routed external gap-fill → consolidated linkless Masterfile |
| R12 | Implement every method in `EXTRACTION-METHODS-CATALOG.md` until the app is a complete standalone repository |
| R13 | **★ Above military grade** — built for eventual military use; accuracy sacred, extractive+cited, fail loud, verify like lives depend on it |

## 4 · Feature inventory (what's been built, by area)

Reconciled and cross-checked in full in `docs/MASTER-RECONCILIATION.md` §4 — summarized here:

- **Search & discovery** — FTS w/ side filter, offline type-ahead, in-document Ctrl+F, Ctrl+K command palette,
  mechanic-slang fuzzy layer, Smart Collections, hybrid search (acronym/glossary expansion + RRF fusion + fuzzy
  NSN "did you mean," 1.5.0), semantic + visual (photo→figure) search, fielded operators `tm:`/`nsn:`/`vehicle:`/
  `side:` (1.13.0), zero-result gap log (1.13.0), a home search that routes a torque/measurement-shaped query to
  an inline answer card instead of leaving it a click away (1.15.0), synonym/fuzzy-only hits now visibly badged
  "≈ approx" rather than rendering identically to a literal match (1.15.0).
- **In-app ingestion & Discovery Engine** (1.15.0) — Add Documents runs scan+OCR+parts as one in-app job with a
  real 4-stage progress panel, closing the "go run a `.bat` yourself" gap; drag-and-drop single-file upload
  (`ingest_upload()`) with a live "where did my data go" breakdown panel; `crawl()` now actually reads
  images/`.txt`/`.html` (a standalone image gets the same OCR/barcode/dimensional pipeline a scanned PDF page
  does, for free) and — tier-gated to Win10/11 — `.docx`/`.xlsx`/`.pptx`/`.rtf` via new `engine/office.py`;
  `tables.py`/RPSTL parsing/pagetrim boilerplate stripping/`keywords.json` refresh all became live pipeline
  stages instead of separate manual `.bat` tools; the resulting 8 extraction-stage opt-out toggles are now
  centralized in one live registry (`engine/flags.py`).
- **Two sides of the house** — Operator(-10) vs Mechanic(-20) classifier + confidence, side chooser, chapter-level
  routing inside combined manuals, override/review queues.
- **Procedures, workflow & job packages** — procedure view, Solve-it hub, printable job packet, torque/fastener
  reference, Work Order builder `/jobcard`, cross-figure part locator `/locate`, unified **`/part`** page (identity
  + supersession + parts + dims + torque + cautions + procedure + model + conflict banner) + `jobpack.py` PDF
  (1.7.0), `/troubleshoot` fault trees (1.7.0), serviceability go/no-go + torque-sequence diagrams + BOM + pinouts
  (1.9.0), DA-2404/2407 forms, MAC parser (1.12.8), shift-handover digest, one-time-use/torque-to-yield fastener
  flags (1.13.0).
- **Parts intelligence & cross-reference** — unified part dossier, Look-Alike Parts recognizer `/partdiff`, RPSTL
  parsing → PN↔figure correlation, cross-reference engine, PUBLOG/FLIS federal catalog (~16 GB DLA export →
  `index/publog.db`, 1.5.0), hand-scanner + camera routing, `publogdiff.py` interchangeability verdicts + shelf
  scan `/binaudit` (1.6.0), exploded/assembly view, fleet shared-parts commonality (1.11.0), edition/near-duplicate
  clustering (`dedup.py` + `/api/editions`, TM-family-blocked before the O(n²) pass, 1.15.0), a barcode-vs-OCR
  NSN conflict table when a page's decoded barcode and its regex-read NSN disagree (1.15.0), airgap NIIN-review-
  decision sync between air-gapped units — sign/verify, fail-closed on tamper, conflicts surfaced not
  auto-resolved (1.15.0).
- **Imagery, 3-D & CAD** — real cited figure crops, parametric 3-D (`partgeo.js`, custom WebGL), auto-CAD image
  engine `cad_render.py` at **CAD_VERSION 7** (SS4 supersampling, 3-point lighting, silhouette ink-line, contact
  shadow, FLIS color + procedural texture; ~32,622-part cache; STL/OBJ export), interactive Rotate-CAD tab, CAD
  material grafted onto the WebGL model, local authoritative models (`index/models3d/<NSN>.obj|.stl`), approximate
  3-D from PUBLOG dimensions (`dimscad.py`, 1.6.0), AI-generated illustrative tier (Meshy import lane,
  non-authoritative by construction, 1.13.1), touch-orbit + pinch-zoom with an always-visible zoom/reset row on
  the interactive 3-D view and its SVG fallback (ported from the CAD-rotate tab, 1.14.0).
- **Schematics & circuits** — tilt/mirror/blueprint modes, Circuit Lab (MNA simulator in a Web Worker; individual
  wire selection/deletion instead of only wiping the canvas, 1.14.0), schematic Highlighter, Living Schematic
  (`schemgraph.py` netlist inference → animated current-flow overlay), wiring continuity trace
  (`harnesstrace.py`, 1.12.6); page-level schematic detection (vector netlist + raster/keyword signal) now runs
  automatically during ingest, not just via `BUILD-SCHEMGRAPH.bat` (1.15.0); a new template crop-and-save UI
  (`symbols.py`'s missing piece — 3 routes + a modal on Deep Zoom) lets a mechanic teach the app a symbol
  in-app instead of hand-cropping a PNG outside it (1.15.0).
- **R13 trust, verification & safety layer** — `validate.py` (quarantines garbled/impossible values, 1.8.0, woven
  into `/measures` + `conflicts.detect` at 1.13.0), `trust.py` canonical trust badges, `/verify` cockpit,
  `signoff.py` SME approve/reject (append-only), `tmrev.py` superseded-TM flag, `integrity.py` corruption/tamper
  detection, `conflicts.py` cross-manual disagreement flags + precomputed sweep (`build_conflicts.py`, 1.13.0),
  offline cited Q&A `ask.py`, offline read-aloud, air-gap signed update package (HMAC-SHA256, fail-closed, 1.12.0).
- **Decoders & reference tools** — standards/spec designation, NSN-structure, SMR, CAGE/NCAGE — all on `/decode`.
- **Fleet readiness & training** — fluids/service-interval matrix + `/readiness` (1.11.0), bulk folder ingestion +
  `viewer_ingest.py prune` (reconciles documents whose source file was deleted/renamed since the last crawl,
  rename detection via fingerprint match, dry-run by default, 1.14.0), cited multiple-choice learn mode `/learn`,
  append-only field notes w/ SME endorsement.
- **Extraction, enrichment & the Masterfile (R11/R12)** — `measures.py` (13-type dimensional extractor), `tables.py`
  (structured tables), `enrich.py` (Wayback-routed external gap-fill, opt-in crawler only, app stays 100% offline),
  `masterfile.py` (consolidates corpus+external into `index/masterfile.db`, no external links surfaced), `/master`.
  `measures.py`/`tables.py`/pagetrim now run live during ingest, not just as separate `BUILD-*.bat` tools, and
  `part_differences()` gained a live per-variant "dimensions" discriminator (1.15.0). `masterfile.py`'s
  representative value is now the numeric median of a group's real values (previously the most-common exact
  value *string* — almost always an arbitrary first-crawled tiebreak for continuous measurements), and
  corroboration counting is deduped by `(TM edition, page)` before a group can earn the "high — cited &
  corroborated" badge (1.15.0).
- **UI/UX, accessibility & onboarding** — kiosk mode, deep-zoom callouts, palette aria-modal + focus trap,
  `esc()`/`toast()` dedup app-wide, offline QR deep-link (base URL now resolved via a validated allowlist,
  `safe_public_base()`, instead of trusting the raw `Host` header, 1.14.0), Masterfile spec-sheet + `/mastercov`
  coverage dashboard, `index.html` ES5 capability-probe + minimal legacy fallback shell for RPS-Legacy/IE11/
  old-Firefox hardware (1.14.0). The mechanic path no longer re-gates behind the full-screen session modal on
  every cold start (a time-boxed "already chose to browse" preference), touch-sizing generalized app-wide, the
  command-palette pill relabeled from a keyboard-shortcut convention this audience has no reason to recognize
  to "🔍 Jump to anything" and finally sized to the 44px touch floor, `readaloud.js` gained hands-free
  voice-controlled step-by-step navigation for `procedure.html`, `procedure_full()` merges a preceding page's
  WARNING box and stops collapsing three different failure states into one ambiguous "none found," a resolved
  7-glyph icon-collision pass across `palette.js` synced into every affected page, and the guided demo tour got
  its first-ever test coverage (all 1.15.0).
- **Performance, RPS & stability** — gzip+keep-alive, fitz LRU + thread-local conns + ETag, RPS legacy fallback +
  warmup, parallel CAD batch, GPU-tier OCR, preflight/disk-guard/off-disk backup, `corpus.py` unification + pooled
  `doc_path()` + startup auto-optimizer + bounded worker pool (1.13.0 groundwork), persisted RPS run-mode (1.13.2),
  `ocr_supervisor.py` heartbeat-staleness watchdog + per-page OCR timeout (`VIEWER_OCR_PAGE_TIMEOUT`, force-kills
  and recovers a HUNG — not just crashed — OCR pass, 1.14.0). New opt-in **`Premium`** run-mode choice (a visual
  layer that only ever activates on top of an already-`modern`-capable machine) plus 9 real gaps closed where
  RPS's own hardware-tier flags went unread: OCR ingestion workers/DPI/GPU now default to the real `sysprobe.py`
  profile instead of a flat guess, `embed.py` `mmap`s its embeddings array on lite/legacy instead of a full
  ~293MB in-memory copy, the HTTP worker-pool ceiling and the page-render DPI cap both finally branch on the
  real RPS tier (all 1.15.0).
- **Dev / verify / ops tooling** — root **`VERIFY.bat`** (the one gate, see §6) — **confirmed GREEN on an actual
  host for the first time in 1.13.3**, reconfirmed after the larger 1.13.4 hardening pass (563 PASS / 0 FAIL,
  658/658 files intact both times) — `engine/tools/check_crlf.py`, `safeguard.py backupdb` (VACUUM INTO + disk
  guard + keep-2; as of 1.14.0 `viewer_ingest.py migrate()` also calls it automatically before applying any
  pending migration, but the standalone manual invocation is still never actually run) · **resource-leak +
  uncached-endpoint + regex-fabrication hardening** (1.13.3/1.13.4): 13 sites where a query throwing after a
  lazy-validated `sqlite3.connect()` skipped `close()` (all now `con=None`+`finally`), 2 multi-second aggregate
  endpoints TTL-cached, and several classification bugs that could fabricate or mislabel data (`rpstl.py`
  SMR/CAGEC, `standards.py` item-name fabrication via prefix-match) fixed to match the app's own R13 "never
  fabricate" discipline. **v1.14.0** — a 12-commit, 50-finding 4-tier audit (Critical/High/Medium/Low) + a
  priority-5 UI/UX pass + this repo's **first-ever CI workflow** (`.github/workflows/ci.yml`, runs
  `verify_all.py --snapshot` on every push/PR to `main`) took `engine/tests/verify_all.py` to **26/26, ALL
  GREEN** for the first time in the project's history; its test-suite gate is now glob-based auto-discovery
  (23 `test_*.py` files, no hardcoded list) instead of the old hardcoded allowlist, which itself had drifted
  ~40% behind reality. `registry.py` gained `safe_header_token()` plus a SQLite 64-bit bind-range guard on
  `qint()`; `kg.py` and `build_publog.py` now both rebuild into a temp file and atomically swap in rather than
  deleting-then-rebuilding in place. **v1.15.0** (30 commits, ~25 hours) — a dedicated functions+security audit
  across all 265+ routes landed **52 confirmed fixes** (7 security: a `None`-vs-JSON-`null` dispatch confusion
  that 500'd instead of 400'ing, a missing ingest-root fence on `/api/airgap_verify`, a host-path leak on
  `/api/ingest_preview` in exposed mode, non-atomic CAD cache writes, an unbounded schemgraph cache-key param,
  a DPI-cap bypass on any request carrying a `clip` param, a `POST /api/ingest` check-then-act race); new
  `audit_features.py [7]` adds a mechanical AST import-closure reachability checker for the "built but never
  wired in" bug class that had recurred across at least 9 prior commits; a real barcode-loss bug was caught
  live by this repo's own CI on its first run against the barcode pipeline (an OCR text-engine failure was
  silently discarding an already-decoded barcode); the multi-GB `viewer.db` finally has automatic protection
  beyond the source-file snapshot vault (a new weekly scheduled full-DB backup task, `run_backupdb.bat`); the
  8 extraction-pipeline opt-out toggles are now a live, centralized registry (`engine/flags.py`) instead of 8
  independent `os.environ.get()` call sites; `verify_all.py` also now prints full output on a suite failure
  instead of silently discarding everything but the last 3 lines. `engine/tests/verify_all.py` is now
  **46/46, ALL GREEN**.

## 5 · Code & data map

- `engine/viewer_app.py` — thin server shell. `engine/features/` — all domain logic (`registry`, `routes`,
  `corpus.py`, and the per-area feature modules). `engine/ui/*` — pages/widgets.
- Builders & batches: `make_cad.py` (parallel), `extract_figures.py`, `build_rpstl.py`, `build_xref.py`,
  `build_publog.py`, `build_conflicts.py`, `build_masterfile.py`, `classify_sides.py`, `bench_cad_parallel.py`,
  `build_dedup.py` (1.15.0 — editions/near-duplicate clustering).
- Diagnostics/verification: `diag_*.py`, `verifystate.py`, `cad_status.py`, `mutate.py`, `run_timeout.py`,
  `engine/tools/check_crlf.py`, `engine/audit_features.py` (its `[7]` section, 1.15.0, is a mechanical
  reachability checker for the "built but never wired in" bug class — distinct from `verifystate.py`'s
  has-a-self-test check).
- New pipeline-support modules (1.15.0): `engine/flags.py` (the 8 extraction-toggle live registry),
  `engine/office.py` (`.docx`/`.xlsx`/`.pptx`/`.rtf` text extraction, tier-gated to Win10/11).
- Launchers: the root `*.bat` files (RUN-/MAKE-/BUILD-/VERIFY-/DIAG-/RE-RENDER-CAD/DEMO/RESTART-CLEAN…) plus
  root **`VERIFY.bat`** — the single authoritative gate. New in 1.15.0: `DEDUP.bat`, `run_backupdb.bat`,
  `BUILD-AIRGAP-MANIFEST.bat`/`VERIFY-AIRGAP-BUNDLE.bat`.
- `index/` sidecars: see `PORTING.md` §1 for precious-vs-regenerable (largest: `viewer.db` ~3.65 GB+,
  `publog.db` ~9 GB — both git-ignored, host-generated only). New in 1.15.0: `dedup.db` (edition clustering).
- `docs/`: `CHANGELOG.md` (version history, count not re-tallied since v1.13.2 — treat "219 entries" from an
  earlier pass as stale) / `CHANGELOG-LEGACY.md` (143, dual-track parity per R7), `ITERATION-SNAPSHOTS.md` +
  `ITERATION-DASHBOARD.html` (not regenerated for the v1.15.0 reconciliation — see `HANDOFF-NOTE.md`'s
  "Suggested next"), `MASTER-RECONCILIATION.md`, `HANDOFF-NOTE.md`, `diagrams/` (185+ dark-theme PDF/SVG pairs,
  count also not re-tallied), proof images, `LOCAL-MODELS.md`, `IMAGE3D-SETUP.md`, `PORTING.md`, this file.

## 6 · Dev workflow & conventions (how progress is made safely)

1. Build additively (new module + route + UI hook), keep R1 rollback notes in the changelog entry.
2. **Verify host-side** with root **`VERIFY.bat`** — the single authoritative gate since v1.13.0: exit-code truth
   per step, `run_timeout.py` wall-clock guards, unions the audit + GET/POST route sweeps (**265 routes** as
   last counted at v1.14.0, 244 GET + 21 POST — a real batch of new routes landed in v1.15.0
   (`ocr_backlog_start`, `ingest_upload`, `airgap_export_decisions`/`import_decisions`, 3 `symbols_*` routes,
   `editions`) that this count doesn't yet reflect; see `HANDOFF-NOTE.md`'s gotchas) + every regression suite +
   `rps_lint` + `verify_ui` + `check_crlf` + module self-tests + no-truncation completeness.
   `VERIFY-099.bat` forwards to it. Convention exists because dev-sandbox reads of freshly-grown files truncate
   (cached size) — **host files are always fine; never "fix" a file based on a truncated sandbox read.**
   `engine/tests/verify_all.py`'s own regression-suite gate is glob-based auto-discovery (no hardcoded list) and
   is **46/46 ALL GREEN** as of v1.15.0 (`9b0e5b9`) — up from 26/26 at the start of v1.14.0, itself the first
   fully clean run in the project's history; 18 new test files landed in the v1.15.0 range alone.
   **`.github/workflows/ci.yml`** (added in 1.14.0) runs `verify_all.py --snapshot` on every push/PR to
   `main` — complementing rather than replacing the host-side `VERIFY.bat` run. It caught a real bug
   (`test_http.py`) on its first-ever run, a real barcode-loss bug on its first run against the barcode
   pipeline during v1.15.0, and — separately, during the CI-hardening work that landed alongside the v1.15.0/
   CHANGELOG reconciliation on 2026-08-24 — its own environment gaps (no `tesseract` binary on either runner,
   a Windows-only test font with no Linux fallback), both now fixed.
3. Document: changelog entry (+ legacy parity entry) + dark diagram PDF via a `_make_NN_*.py` generator.
4. Long batches are resumable + observable (`CAD-STATUS.bat`, heartbeat/notify watchers); never click inside a
   running batch console (Select mode pauses it — Esc resumes).
5. Schema changes go through migrations, applied atomically per-migration (`viewer_ingest.migrate()`, 1.13.0).
   Never write the big DB through a sandbox mount — sidecars are written by host-run builders only.

## 7 · Hardware profile & tuning (original dev machine)

Acer Nitro 5: **16-core Alder Lake, RTX 4050 Laptop 6 GB, DDR5, Win11.** RPS=modern. OCR 8/12 workers.
CAD batch 12 workers (cap; raise via `--workers` on bigger CPUs). On a NEW machine: delete
`index/hardware_profile.json` → sysprobe re-tunes everything. GPU is used for OCR (onnxruntime) + WebGL;
the CAD PNG renderer is CPU-parallel by design.

## 8 · Current state & in-flight (hand-off)

**True current state: v1.15.0, shipped 2026-08-19 (`main` @ `9b0e5b9`).** 30 commits, ~25 hours, effectively
one continuous session (2026-08-18 20:40 → 2026-08-19 21:41) — the largest single body of undocumented work
this project has ever carried at once (`CHANGELOG.md` itself only caught up to it on 2026-08-24, PR #4).
Headline threads: Discovery Engine phase 1 + in-app scan/OCR (drag-and-drop upload, non-PDF format support,
dimensional/schematic detection wired into the live scan), a 6-agent full-codebase reachability audit that
closed 3 more "built but never wired in" gaps (RPSTL extraction, pagetrim boilerplate stripping, automatic
keywords refresh) plus a new mechanical checker for that bug class going forward, all 5 previously-deferred
items closed (tables_plus cross-page stitching, Office-format extraction, dedup/editions clustering, symbols
crop UI, pagetrim's OCR-page path), a new opt-in RPS `Premium` visual tier + 9 hardware-adaptive-engine gaps
closed, OCR confidence finally threaded through to `torque.html`/`measures.html`, a 52-fix functions+security
pass across all 265+ routes, a barcode-loss bug caught live by this repo's own CI, a masterfile/dedup audit,
airgap NIIN-decision sync, a weekly full-DB backup task, and a UX pass. See `CHANGELOG.md`'s `[1.15.0]` entry
for the complete, itemized list (written from the actual commit diffs, not just messages). Known outstanding
items (host-side, still owed — full detail in `MASTER-RECONCILIATION.md` §6):

1. **R10 literal screenshots have never actually been saved as artifacts** — `docs/screenshots/` still holds
   only a README of intended routes. Every fix across the v1.14.0 and v1.15.0 sessions was verified live
   against the real running app, but none were saved to `docs/screenshots/`. Still the single most
   consistently-deferred action across every session.
2. **`BUILD-CONFLICTS.bat`** — first precomputed conflict-sweep run, still never run; `index/conflicts.db`
   doesn't exist yet. Optional while OCR is paused.
3. **`measures.py`'s bare-number-fused-to-single-letter-unit ambiguity** (e.g. an RPSTL item number "489A"
   reading as "489 Amps") — the **labeled** sub-case ("ITEM 489A", any bare-letter unit preceded by a
   figure/table/item/detail/etc. reference word) is fixed as of `[1.18.0]`. The **unlabeled** sub-case
   (a bare "489A" with no preceding label) stays open on purpose: unlike the labeled fix, a blanket
   no-space-required guard would silently drop real "12V"/"5A"/"60W"-style fused electrical readings,
   a recall regression with no safe way to verify without the real corpus. Documented since `[1.13.4]`.
4. **`safeguard.py backupdb`** — a manual entry point (`run_backupdb.bat`) and an automatic weekly scheduled
   task (`THE_VIEWER_WeeklyDBBackup`, via `register_snapshot_task.bat`) both shipped in v1.15.0, but neither
   has been confirmed to have actually run against the real production index on the host yet.
5. **OCR completion** — confirmed **94.4%** as of the v1.13.4 session; not re-checked during either the
   v1.14.0 or v1.15.0 sessions, both code-quality/feature passes rather than ingestion runs — check current %
   via `/command` or `/status` before assuming fully finished either way.
6. **Tiers 2–6 of the separate staleness Drift Report** (dependency-version-bound hardening, further doc
   reconciliation beyond each pass, and repo-bloat cleanup) — the Tier-1 pass (`3054dad`) is only the first
   tier of that audit; the rest is tracked separately and not yet started. This is a DIFFERENT tracking thread
   from item 7 below and from the v1.14.0 Medium-tier deferred findings — see `HANDOFF-NOTE.md`'s "Suggested
   next" for the full disambiguation.
7. **v1.15.0's own deliberately-deferred items:** `camelot_tables()` (3rd table-extraction engine pilot) stays
   unwired into `/api/tables_plus` — a documented cv2/opencv-python binary-collision risk on version skew;
   `dedup.py` cross-TM-family duplicates aren't caught by design (the TM-family blocking that makes the O(n²)
   pass tractable at real corpus scale — 39,683 docs — trades that away deliberately).
8. **Route count (265, 244 GET + 21 POST) hasn't been recounted since v1.14.0** — v1.15.0 added a real batch
   of new routes (see §6); worth a fresh audit pass.

Resolved since the last update (kept here for continuity, since these were open as of v1.14.0):
`engine/tests/verify_all.py` climbed from 26/26 to **46/46, ALL GREEN**, 18 new test files added · a real
barcode-loss bug (an OCR text-engine failure silently discarding an already-decoded barcode) caught live by
CI and fixed · the multi-GB `viewer.db` finally has automatic backup protection beyond the snapshot vault ·
the 8 extraction-pipeline toggles are now a live centralized registry instead of 8 independent call sites ·
`verify_all.py` prints full output on a suite failure instead of silently discarding everything past the last
3 lines (a real, self-inflicted debugging gap found while chasing this exact reconciliation's own CI failures).

(`docs/PORTING.md`'s matching "v0.98.0" drift — previously listed here — was reconciled on 2026-08-08 to
v1.13.2, and is now several point releases behind again (still v1.13.2 vs. current v1.15.0); see its own
header, and §9 below. Not touched in this reconciliation pass — out of scope, see the note at the top of this
file.)

## 9 · How to duplicate

1. Follow **`docs/PORTING.md`** (copy list, deps, the E:\ path trap, the hardware_profile.json trap, the v1.13.2
   persisted-run-mode trap, first-run checklist) — reconciled to v1.13.2 alongside this file.
2. Give any new collaborator/AI session **this file + `MASTER-RECONCILIATION.md` + `HANDOFF-NOTE.md` + PORTING.md +
   the two changelogs** as context — together they carry the rules (R1–R13), the architecture, the verification
   conventions, and the full feature history.
3. Confirm the duplicate with root `VERIFY.bat` + the spot-checks in PORTING.md §6.

*This summary is the canonical hand-off, reconciled against `MASTER-RECONCILIATION.md` and `CHANGELOG.md`.
Per-feature depth lives in the changelog entries and their diagrams.*
