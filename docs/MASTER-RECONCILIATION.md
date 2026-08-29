# THE VIEWER — Master Reconciliation (all chats, all versions → one record)

**Compiled 2026-08-08, updated 2026-08-09, reconciled again 2026-08-18, and again 2026-08-24.** This document
exists because the project's own canonical docs had drifted out of sync with each other across sessions —
including, at the 2026-08-09 update, this file itself: it named **v1.13.4** as the state all canonical docs
agreed on the same day `CHANGELOG.md`'s newest entry had already moved on to **v1.13.5**. The exact same drift
class recurred at the 2026-08-24 update: `CHANGELOG.md` itself only caught up to v1.15.0 five days after that
version shipped (PR #4) — this file is a downstream reconciliation of that same reconciliation, not an
independent re-derivation. This file is the reconciled, single-source feature record, cross-checked against
the actual files on disk (not just memory) where practical. It supplements — does not replace —
`CHANGELOG.md` (a per-change log whose entry count is no longer re-tallied here after v1.13.2, see §7) and
`HANDOFF-NOTE.md` (the living session hand-off). Treat all four as canonical going forward; keep them in sync.

**True current state: v1.15.0, shipped 2026-08-19, `main` @ `9b0e5b9`.** 30 commits, ~25 hours, effectively one
continuous session (2026-08-18 20:40 → 2026-08-19 21:41) — the largest single body of undocumented work this
project has ever carried at once. See `CHANGELOG.md`'s `[1.15.0]` entry for the authoritative commit-by-commit
summary (written from the actual diffs, not just commit messages); §4 below reconciles this file's feature
inventory against it, and §5's version-timeline entry summarizes it. Headline threads, in commit order:
**Discovery Engine phase 1 + in-app scan/OCR** (`05ff17f`→`85df23c`) — drag-and-drop upload, non-PDF format
support, dimensional/schematic detection wired into the live scan; a **6-agent full-codebase reachability
audit** (`099737f`, `e9eee88`) closing 3 more "built but never wired in" gaps (RPSTL extraction, pagetrim
boilerplate stripping, automatic keywords refresh) plus a new live toggle registry (`engine/flags.py`); **all 5
previously-deferred items closed** (`ee3714d`→`d5fb9f8`: tables_plus stitching, Office formats, dedup/editions,
symbols crop UI, pagetrim's OCR-page path); a **52-fix functions+security pass** across all 265+ routes
(`c147614`) + a 32-fix icon/emblem quality pass (`4b3224c`); a real **barcode-loss bug caught live by this
repo's own CI** on its first run against the barcode pipeline (`54d2546`); the **RPS `Premium` tier** +
9-gap hardware-adaptive deepening (`bdc17cd`, `735455f`); **airgap NIIN-decision sync**, a weekly full-DB
backup task, and a mechanical reachability checker (`875ffd5`, `822d830`, `72e1797`); a **masterfile/dedup
audit** (`40a811b`, `299629b`, `ddbc302`); and a closing **UX pass** (adjacent-page warnings, honest failure
states, hands-free readaloud, touch sizing, inline search answers, confidence-signaling badges, `da0c996`→
`9b0e5b9`). `engine/tests/verify_all.py` is now **46/46, ALL GREEN** — up from 26/26 at the start of v1.14.0.

---

## 1 · Mission (unchanged since inception)

An **offline search engine with a dynamic GUI** over a library of military Technical Manuals — modeled on
EMS-NG / IADS / Adobe, "the best of all worlds" — for vehicle mechanics. Five founding goals, all shipped:

- **A. Find anything** in the TM/PDF corpus fast.
- **B. Many ways to search** — full-text, in-document Ctrl+F, offline Google-style predictive type-ahead.
- **C. Complete instructional rundowns** — disassembly/assembly, tools, torque, and clear differences between
  look-alike parts.
- **D. Richer-than-the-PDF graphics** — dynamic diagrams and 3-D, simple and advanced, for young mechanics and SMEs.
- **E. Effortless ingestion** of new files.

## 2 · System architecture (current shape, since the v0.96.0 "THE RESTRUCTURE")

- **Server:** `engine/viewer_app.py` — pure-stdlib `ThreadingHTTPServer`, `127.0.0.1:8765`, now a ~330-line thin
  shell. All domain logic lives in `engine/features/`: `registry` (declarative `{path:handler}` routes + central
  param validation), `routes` (every endpoint declared once), `corpus.py` (the one shared FTS retrieval layer,
  added v1.13.0), plus `search/parts/browse/procedures/render/ingest/sessions` feature modules.
- **UI:** plain HTML/JS in `engine/ui/`, no framework, ES5-safe for legacy hardware. Custom WebGL renderer
  (`gl3d.js`); shared widgets (`loupe.js`, `partview.js`, `cadview.js`, `schemflow.js`, `palette.js`, `scanner.js`,
  `readaloud.js`, `shared.js`).
- **Data:** corpus at `E:\ALL MILITARY TMS` — **read-only, never written** (R1/R6) — indexed into `index/viewer.db`
  (~3.65 GB+: documents, pages, OCR text layer, parts, ref_nsn/FLIS). Every feature adds its own **append-only
  sidecar** database under `index/` rather than touching the core schema outside migrations.
- **Tiers (RPS = Retroactive Post-Support):** `sysprobe.py` probes the host → modern / lite / legacy feature tiers,
  so the same codebase runs on an RTX-class Win11 box or a Win7/Vista shop-floor PC. **As of v1.13.2** the tier
  choice is a persisted Settings decision (Auto / Performance / Retroactive Post-Support), not just an env flag.
- **Two builds, one codebase** (`docs/FORKS.md`): the **Advanced/GPU production build** is the priority fork
  (RapidOCR on `onnxruntime-gpu`, 10–30× faster OCR) — `make_portable.bat` derives the **Lite/portable build**
  (finished index only, CPU-safe, one-click `SETUP.bat`/`START.bat`) for weaker machines. Same `viewer.db` schema
  either way; no divergent code.

## 3 · Standing rules governing every change (R1–R13, THE VIEWER-only)

| # | Rule |
|---|---|
| R1 | Backwards-compatible + rollbackable; corpus read-only |
| R2 | Every addition ships with a data-flow diagram |
| R3 | Diagrams: professional dark theme + PDF |
| R4 | A `CHANGELOG.md` entry with every change |
| R5 | + a graphical changelog explanation (CHANGELOG-VISUAL) |
| R6 | Append-only data — add, never remove |
| R7 | Legacy builds get a dual-track changelog (`CHANGELOG-LEGACY.md`) with parity notes |
| R8 | Write a full HANDOFF note at session end / on request |
| R9 | Always use no-truncation discipline; verify completeness mechanically |
| R10 | Every iteration ships a **literal screenshot** of the running app (not a mock/diagram) — see §6, still owed |
| R11 | 100% info retrieval incl. dimensions → Wayback-routed external gap-fill → consolidated linkless Masterfile |
| R12 | Implement every method in `EXTRACTION-METHODS-CATALOG.md` until the app stands alone as a complete repository |
| R13 | **★ Above military grade** — built for eventual military use; accuracy sacred, extractive+cited, fail loud, verify like lives depend on it |

## 4 · Feature inventory — every subsystem, reconciled across all chats/versions

### Search & discovery
FTS search w/ side filter · offline type-ahead (0.49) · in-document find (Ctrl+F, 0.53) · Ctrl+K command palette
w/ Recent + tag search (0.55, extended 0.99.11/0.99.13) · mechanic-slang keyword/fuzzy layer (0.67) · Smart
Collections from OCR (0.59–0.61) · page callout overlays (0.60) · hybrid search — acronym/glossary expansion + RRF
fusion of keyword+semantic + fuzzy NSN "did you mean" (1.5.0) · **semantic search** (by meaning) and **visual
search** (photo → figure crop) (pre-1.0.0 wave) · **fielded search operators** `tm:`/`nsn:`/`vehicle:`/`side:`
(1.13.0) · zero-result **gap log** (`/api/searchgaps`, 1.13.0) surfacing what the corpus could not answer · home
search now routes a torque/measurement-shaped query to an inline answer card instead of leaving it one click
away, and a synonym/fuzzy-only hit is now visibly badged "≈ approx" rather than rendering identically to a
literal match (1.15.0).

### In-app ingestion & Discovery Engine (1.15.0)
Add Documents runs scan+OCR+parts as one in-app job with a real 4-stage progress panel, closing the "go run a
`.bat` yourself" gap · drag-and-drop single-file upload (`ingest_upload()`) w/ a live "where did my data go"
breakdown panel · `crawl()` now actually reads images/`.txt`/`.html` (`index_other()` — a raw image gets the
SAME OCR/barcode/dimensional pipeline a scanned PDF page does, for free) and, tier-gated to Win10/11,
`.docx`/`.xlsx`/`.pptx`/`.rtf` via new `engine/office.py` · `tables.py`'s `find_tables()`, RPSTL parts-row
extraction, pagetrim boilerplate stripping, and an automatic `keywords.json` refresh all became live pipeline
stages instead of separate manual `.bat` tools (found by a 6-agent reachability sweep of ~90 root-level
modules) · the resulting 8 extraction-stage opt-out toggles are now one live registry (`engine/flags.py`,
`python viewer_ingest.py flags` introspects current state) instead of 8 independent `os.environ.get()` sites.

### Two sides of the house
Operator(-10) vs Mechanic(-20) classifier with confidence + cover/MAC corroboration (0.73–0.75), side-chooser
modal, side-filtered browsing, chapter-level routing inside combined manuals, override + review queues.

### Procedures, workflow & job packages
Procedure view (0.47) · Solve-it hub (0.48) · printable job packet (0.51) · dynamic step-flow diagrams (0.55) ·
torque & fastener reference (0.55) · **Work Order builder** `/jobcard` — one cited PDF: steps, tools, materials,
WARNING/CAUTION, torque, figure parts, rendered pages (0.99.9–0.99.10) · cross-figure part **locator** `/locate`
w/ figure sheet + Work Order export (0.99.6) · unified **`/part`** page (identity + supersession + parts + dims +
torque + cautions + procedure + model + cross-manual conflict banner) + `/api/partsummary` + `jobpack.py` complete
job-package PDF (1.7.0) · `/troubleshoot` fault-tree parser (MALFUNCTION→check→corrective-action, 1.7.0) ·
serviceability go/no-go checker (`serviceability.py`, 1.9.0) · numbered bolt-pattern **torque sequence** diagrams
(`torqueseq.py`, 1.9.0) · complete kit/**BOM** — parts+qty+consumables+tools (`bom.py`, 1.9.0) · connector
**pinouts** + wire-color extraction (`pinouts.py`, 1.9.0) · **DA-2404/5988-E** PMCS worksheet (1.11.2) ·
**DA-2407/5990-E** maintenance request (1.12.2) · **Maintenance Allocation Chart (MAC)** parser — function/level/
man-hours, `/api/mac` (1.12.8) · shift-**handover** digest (`handover.py`, 1.11.1) · **one-time-use / torque-to-
yield / discard-after-removal** fastener flags (`oneuse.py`, red `/part` card, merged into BOM warnings, 1.13.0).

### Parts intelligence & cross-reference
Unified part dossier (0.52) · **Look-Alike Parts recognizer** `/partdiff` — NSN/FSC/UOC/CAGEC/SMR differences
(0.43) · RPSTL parts-list parsing → PN↔figure correlation + breakdown images (0.78, structured import 1.10.0) ·
cross-reference engine (PN+CAGEC→NSN, manufacturer, vehicles, interchange/supersession, 0.67/0.79) ·
correlations sidecar + NIIN-drift review queue · most-common-nomenclature answer (0.72.1) · cross-method
agreement scoring (`crossmethod.py`, 1.10.0) · **PUBLOG/FLIS federal catalog** — ~16 GB DLA export → NIIN-keyed
`index/publog.db`, `/publog` page, `/api/publog` (1.5.0) · hand-scanner + camera barcode routing (`scanner.js`,
`/scan`, 1.5.0) · **`publogdiff.py`** — characteristics diff + fit-fingerprint %, GREEN/AMBER/RED interchangeability
verdict, RNCC/RNVC decode, inactive-vendor flag, PUBLOG↔TM crosslink, nickname reconciliation, `/binaudit` shelf
scan (1.6.0) · exploded/assembly view — numbered hotspots + step-through order (1.5.0) · fleet **shared-parts
commonality** (`commonality.py`, 1.11.0) · **edition/near-duplicate clustering** — `dedup.py` persistence layer
+ `build_dedup.py` + `/api/editions`, TM-family-blocked before the O(n²) pass at real corpus scale (39,683 docs,
1.15.0) · **barcode-vs-OCR NSN conflict table** — flags when a page's decoded barcode and its regex-read NSN
disagree, never auto-resolved (1.15.0) · **airgap NIIN-review-decision sync** between air-gapped units —
sign/verify, fail-closed on tamper/wrong-key, conflicts surfaced not auto-resolved (`airgap.py`, 1.15.0).

### Imagery, 3-D & CAD (the deep stack)
Real cited figure crops per part (0.76) → figure-first 3-D library (0.82) · parametric 3-D (`partgeo.js`,
FLIS-dimension-scaled, custom WebGL) w/ live editable panel (0.81) · scan color+material mapped onto models
(0.80/0.81.1) · **auto-CAD image engine** `cad_render.py`, evolved to **CAD_VERSION 7** (SS4 supersampling, 3-point
lighting, silhouette ink-line, contact shadow, FLIS color + procedural material texture); ~32,622-part cache;
STL/OBJ export (0.86→0.93.3) · interactive turntable sprite sheets → real WebGL Rotate-CAD tab (0.92.1) · CAD-first
library w/ 5 tabs: CAD / Rotate CAD / Interactive 3-D / Manual illustration / Approximation (0.90) · CAD material
grafted onto the WebGL model (`/api/cadmaterial`, 0.95) · **local models** — drop `index/models3d/<NSN>.obj|.stl`
to replace the placeholder, authoritative (0.94) · approximate 3-D **from dimensions** — parses PUBLOG
characteristics, emits dimensioned isometric SVG + parametric OBJ (`dimscad.py`, 1.6.0) · **AI-generated
illustrative tier** — Meshy-style import into `models3d/ai/`, red non-authoritative banner, structurally can never
outrank a real model (1.13.1).

### Schematics & circuits
Schematics library w/ tilt/mirror/blueprint modes (0.41) · **Circuit Lab** overlay editor + real MNA simulator in a
Web Worker (0.42/0.44) · schematic **Highlighter** — vector net click (0.71) · **Living Schematic** — infers a
netlist from page vectors (`schemgraph.py`, T-junction split + confidence) → animated current-flow overlay
(tiered rAF/SMIL/STEP), 0.97 confidence verified on a real harness (0.91) · wiring-continuity **trace** — nets by
shared signal on pinouts (`harnesstrace.py`, `/api/harnesstrace`, 1.12.6) · page-level schematic detection
(vector netlist + raster/keyword signal) now runs automatically during ingest, not just via
`BUILD-SCHEMGRAPH.bat` (new `schematics` table, migration `0011`, 1.15.0) · a missing template-sourcing UI for
`symbols.py` closed — 3 new routes + a crop-and-save modal on Deep Zoom, so teaching the app a symbol no longer
requires hand-cropping a PNG outside the app (1.15.0).

### R13 trust, verification & safety layer
`validate.py` — quarantines garbled/impossible extracted values, red banner on `/part` (1.8.0) → **woven into**
`/measures` (per-row quality) and `conflicts.detect` (garble dropped pre-grouping so it can't fabricate a safety
conflict, 1.13.0) · `trust.py` canonical trust level + trust badges on measures/ask/conflicts/publogdiff (1.13.0) ·
`/verify` verification cockpit (last VERIFY result, module roster, DB integrity, 1.8.0; **had a 3-bug chain
meaning it found ZERO logs, ever, since the v0.96.0 restructure — wrong log filename, stale pass-regex, a
false-positive fail-trigger, plus a separate path-depth bug — all fixed 1.13.4, now correctly reads the real
current state**) · `signoff.py` — SME
approve/reject/override, append-only audit trail, `/review` (1.8.0) · `tmrev.py` — flags a superseded TM revision
(1.8.0) · `integrity.py` — SQLite corruption + SHA-256 tamper-evidence + online-safe backup (1.8.0) · `conflicts.py`
— cross-manual disagreement flags on torque/spec, cited + ranked (1.7.0) · **precomputed conflict sweep**
(`build_conflicts.py`, append-only `index/conflicts.db`, instant `/api/conflicts`, 1.13.0) · offline extractive
**cited Q&A** — no LLM/network (`ask.py`, `/ask`, 1.7.0) · offline **read-aloud** + voice input, app-wide
(`readaloud.js`, 1.7.0) · **air-gap signed update package** — HMAC-SHA256, fail-closed (`airgap.py`, 1.12.0).

### Decoders & reference tools
Standards/spec designation decoder — MS/AN/MIL-PRF/SAE/ASTM (`standards.py`, 1.12.1) · NSN-structure decoder —
FSG/FSC group + NCB country (`nsndecode.py`, 1.12.3) · SMR (Source/Maintenance/Recoverability) code decoder
(`smrdecode.py`, 1.12.4) · CAGE/NCAGE validator (`cage.py`, 1.12.5) · all reachable via the **`/decode`** page +
palette command (added 1.12.9 after being found unreachable in audit).

### Fleet readiness & training
Per-system fluids/capacities (`fluidsmatrix.py`) + service intervals (`intervals.py`) + `/readiness` page (1.11.0)
· bulk folder ingestion (`ingestpipe.py` + `BULK-INGEST.bat`, 1.11.3) · new **`viewer_ingest.py prune`**
subcommand — reconciles documents whose source file was deleted/renamed since the last crawl (rename detection
via fingerprint match, cascade-safe cleanup, dry-run by default, missing-fraction abort threshold so an
unmounted drive can't look like a mass deletion, 1.14.0) · cited multiple-choice **learn mode**
(`training.py`, `/learn`, `/api/quiz`, 1.9.0) · append-only **field notes** w/ SME endorsement (`fieldnotes.py`,
`/api/notes`, 1.9.0) · interactive demo/tour doubling as onboarding → hands off to the side chooser (0.83.x).

### Extraction, enrichment & the Masterfile (R11/R12)
**`measures.py`** — 13-type dimensional extractor (length/dia/tolerance/weight/torque/pressure/capacity/electrical/
temp/flow/speed/rotation/angle), live `/measures` (1.1.0) · **`tables.py`** — PyMuPDF spec/dimension table detection
(1.1.1) · **`enrich.py`** — external gap-fill ONLY where the corpus is silent, every link routed through the
Wayback Machine, badged `external-unconfirmed` w/ full provenance, opt-in crawler only (`ENRICH.bat`) — app stays
100% offline (1.1.2, hardened to "Wayback-everything" at 1.1.3) · **`masterfile.py`** — consolidates
corpus+external into one congruent `index/masterfile.db`, RAW+FILTERED layers, no external links surfaced,
`/master` (1.1.4) · **`macchart.py`** MAC parser (1.12.8, see workflow section) · `docs/EXTRACTION-COVERAGE.md` /
`docs/EXTRACTION-METHODS-CATALOG.md` track R12's march toward every method in the catalog being implemented ·
`measures.py`/`tables.py`/pagetrim now run live during ingest, not just as separate `BUILD-*.bat` tools, and
`part_differences()` gained a live per-variant **dimensions discriminator** (1.15.0) · `masterfile.py`'s
representative value is now the **numeric median** of a group's real values (previously the most-common exact
value *string* — almost always an arbitrary first-crawled tiebreak for continuous measurements, confirmed live:
3 real docs at 180/180.5/179.8in produced `value='180'` purely because that doc crawled first), and
corroboration counting is deduped by `(TM edition, page)` before a group can earn the "high — cited &
corroborated" badge (1.15.0) · `masterfile.py` gained a THIRD, optional corroborating source, `index/pageqa.db`
(`build_pageqa.py`/`BUILD-PAGEQA.bat`, host-side batch tool, catalog §10.1 + §3.12) — self-grounded
(`vlm.ground()` re-locating the model's own claimed phrase) AND OCR-cross-checked (fuzzy word-overlap against
the page's own stored `pages.body_text`, both must pass) vision-language page extractions, tagged
`origin='vlm-verified'`, doc/page-cited and deduped by the same cross-doc same-TM-number guard `corpus` rows
already use, never merged into the `corpus` group itself, degrading exactly like `measures_db`/`enrich_db` when
`pageqa.db` is absent (the common case before `BUILD-PAGEQA.bat` has ever been run) (1.17.0).

### UI/UX, accessibility & onboarding
Kiosk mode (bigger text, ≥44px targets, 1.4.0) · deep-zoom + callout hotspots (0.99.3/0.99.8) · palette
aria-modal + focus trap, `role=dialog` modals, `esc()`/`toast()` dedup across all 29 pages, `alert()`→`toast()`
app-wide, shared footer nav injector (1.13.0) · offline QR deep-link from `/packet` to a part's dossier, LAN-scannable
(`qrgen.py`, 1.4.0; base URL now resolved through a validated-allowlist **`safe_public_base()`** instead of
trusting the raw `Host` header, 1.14.0) · Masterfile spec-sheet PDF + `/mastercov` least-covered-first coverage
dashboard (1.4.0) · Tools "Diagnose & decode" menu group (1.13.0) · the mechanic path no longer re-gates behind
the full-screen session modal on every cold start (a time-boxed "already chose to browse" preference), the
command-palette discovery pill relabeled from a keyboard-shortcut convention this audience has no reason to
recognize to "🔍 Jump to anything" and finally touch-sized, touch-sizing generalized app-wide, `readaloud.js`
gained hands-free voice-controlled step-by-step navigation for `procedure.html`, `procedure_full()` merges a
preceding page's WARNING box and stops collapsing three distinct failure states into one ambiguous "none
found," a 7-glyph icon-collision pass across `palette.js` synced into every affected page, and the guided demo
tour got its first-ever test coverage (all 1.15.0).

### Performance, RPS & stability
gzip+keep-alive (0.46) · fitz LRU + thread-local conns + NOCASE indexes + ETag/304 (0.56–0.58) · RPS legacy mode
w/ Poppler/Tesseract fallback + warmup (0.45/0.26) · parallel CAD batch, 2.9× measured (0.95) · GPU-tier OCR
(RapidOCR/onnxruntime, 8–12 workers) · preflight gate, disk guard, off-disk backup mirror, server/OCR watchdogs
(0.63) · **`ocr_supervisor.py`** — heartbeat-staleness watchdog that force-kills and recovers a HUNG (not just
crashed) OCR pass, plus a per-page OCR timeout (`VIEWER_OCR_PAGE_TIMEOUT`), `run_ocr_auto.bat` (1.14.0) · custom
mutation-testing harness (0.72.3) · **`corpus.py`** unified FTS retrieval used by every consumer,
pooled `doc_path()`, startup auto-optimizer (WAL + bg indexes), bounded worker pool, `safeguard.atomic_write`
everywhere (1.13.0 groundwork) · **persisted RPS run-mode** — Auto/Performance/Retroactive-Post-Support saved to
Settings, `/api/rps_mode` (1.13.2) · new opt-in **`Premium`** run-mode choice — a visual layer that only ever
activates on top of an already-`modern`-capable machine, never a silent downgrade elsewhere — plus 9 real gaps
closed where RPS's own hardware-tier flags went unread: OCR ingestion workers/DPI/GPU now default to the real
`sysprobe.py` profile instead of a flat guess, `embed.py` `mmap`s its embeddings array on lite/legacy instead
of a full ~293MB in-memory copy, the HTTP worker-pool ceiling and the page-render DPI cap both finally branch
on the real RPS tier, and `ocr_supervisor.py`'s watchdog floor gained a real safety-margin fix (raising the
per-page OCR timeout without it would have caused an infinite kill/requeue/restart loop) (all 1.15.0).

### Dev / verify / ops tooling
Route smoke tests, static audits, end-to-end demo/test suite, the VERIFY-*.bat family · root **`VERIFY.bat`** —
the single authoritative gate: exit-code truth, `run_timeout.py` wall-clock guards (no step can hang for
hours), unions audit + GET/POST route sweeps + all regression suites + `rps_lint` + `verify_ui` + `check_crlf`
+ module self-tests + no-truncation completeness (1.13.0, hang-proofed 1.12.7) — **confirmed GREEN on an actual
host for the first time in 1.13.3**, again after the 1.13.4 hardening pass (563 PASS / 0 FAIL, 658/658 files
intact both times), and — once the 1.14.0 audit's CI-fix and Tier-1-staleness commits eliminated the two
open failures (`test_http.py`, `safeguard verify`) that had held since — **fully clean for the first time in
the project's history**: `engine/tests/verify_all.py` now runs **26/26, ALL GREEN**. **`verify_all.py`'s test
gate is now glob-based auto-discovery** of every `engine/tests/test_*.py` file (1.14.0 Critical-tier fix)
instead of a hardcoded filename list — the old list had silently never run 8 real suites (~1,200 lines),
including `test_procedure.py` (22 tests), the one suite that would have caught that same tier's own headline
infinite-loop bug. `engine/tests/` now holds **23 `test_*.py` files** total, all auto-discovered, no hardcoded
list — 6 new/extended this run: `test_seven_modules.py` (105 checks), `test_build_pipeline.py` (44),
`test_prune.py` (22), `test_medium_fixes.py` (29), `test_uiux_fixes.py` (174), `test_ocr_supervisor.py` (11) ·
GET/POST route sweep re-verified live against the running registry at **265 routes green** (244 GET + 21 POST,
`engine/features/registry.py`) — supersedes the "281 routes" figure this section previously carried, which no
longer matches the current route set · this repo's **first-ever CI workflow** — `.github/workflows/ci.yml`,
runs `verify_all.py --snapshot` on every push/PR to `main` — caught a real bug on day one: `test_http.py`'s 29
failures across 11 routes, traced to a drifted DB-fixture schema (`7c4a3ba`, 1.14.0) · **build-to-temp-then-swap**
atomicity extended from `safeguard.atomic_write` to full destructive rebuilds — `kg.py` and `build_publog.py`
now build into a temp file and only swap it in (`safeguard.atomic_replace`) once every table/index has
committed, instead of delete-then-rebuild-unprotected (1.14.0) · `registry.safe_header_token()` shared-helper
extraction + `registry.qint()`'s new SQLite 64-bit bind-range guard — closes an `OverflowError` an oversized
numeric query param used to trigger, found stress-testing beyond CI's own config (1.14.0) ·
`engine/tools/check_crlf.py` — repo-wide CRLF gate for `.bat` files (83 verified, 1.13.0) ·
`safeguard.py backupdb` — VACUUM INTO + disk guard + keep-2, manual (1.13.0; still never actually run —
see §6) · **resource-leak hardening** (1.13.3/1.13.4) — 13 sites across 11 modules where a query throwing
after a lazy-validated `sqlite3.connect()` skipped `close()`, leaking a Windows file handle; all now `con=None`
+ `finally` · **two uncached multi-second aggregate endpoints** TTL-cached (`/command`, `/coverage` share one
cache; `/verify`'s integrity check separately, 300s + `?force=1`) (1.13.4) · **a dedicated functions+security
audit across all 265+ routes** landed **52 confirmed fixes** (1.15.0, `c147614`) — 7 security (a `None`-vs-
JSON-`null` dispatch confusion 500ing instead of 400ing, a missing ingest-root fence on `/api/airgap_verify`, a
host-path leak on `/api/ingest_preview` in exposed mode, non-atomic CAD cache writes, an unbounded schemgraph
cache-key param, a DPI-cap bypass via any request carrying a `clip` param, a `POST /api/ingest` check-then-act
race) plus 45 correctness fixes across `dimscan.py`/`hybrid.py`/`tmrev.py`/`measures.py`/`cad_render.py` and
more · new **`audit_features.py [7]`** (1.15.0, `72e1797`) — a mechanical AST import-closure reachability
checker for the "built but never wired in" bug class that had recurred across at least 9 prior commits,
distinct from `verifystate.py`'s has-a-self-test check · the multi-GB `viewer.db` finally has automatic
protection beyond the source-file snapshot vault — a new weekly scheduled full-DB backup task
(`THE_VIEWER_WeeklyDBBackup`) plus a manual `run_backupdb.bat` entry point (1.15.0, `822d830`) · a real
barcode-loss bug caught live by this repo's own CI on its first run against the barcode pipeline — an OCR
text-engine failure was silently discarding an already-decoded barcode instead of persisting it alongside the
"failed" page status (1.15.0, `54d2546`) · `verify_all.py` now prints full output on a suite failure instead of
silently discarding everything past the last 3 lines — a self-inflicted debugging gap found while chasing this
exact reconciliation's own CI failures (2026-08-24) · `engine/tests/verify_all.py` now runs **46/46, ALL
GREEN** (up from 26/26 at the start of v1.14.0), with 18 new test files landing across the v1.15.0 range alone.

## 5 · Version timeline — the major cuts

| Milestone | What changed |
|---|---|
| pre-0.4x | Foundational monolith build: server, corpus indexing, base FTS search (earliest detail not preserved in current docs — superseded by the restructure below) |
| **v0.96.0 "THE RESTRUCTURE"** | Monolith `viewer_app.py` → thin shell + `engine/features/` package; rollback in `backups/pre-v0.96-restructure/` |
| 0.97 / 0.98 | Search-quality (NEAR/phrase, did-you-mean) + UI dedup; nav consolidation (Collections/Tools menus) |
| 0.99.x | Pre-1.0 polish wave: Work Order builder, `/locate`, `/coverage`, deep-zoom callouts, semantic+visual search, ingest drag-drop, palette Recent+tags |
| **v1.0.0** | First cut — all five founding pillars live; two-tier build (GPU/production + RPS legacy); quality bar = fuzz+mutation+no-truncation gates unioned in `RUN-ALL-VERIFY.bat` |
| v1.1.0 → 1.1.4 | Extraction + enrichment + Masterfile wave (measures/tables/enrich/masterfile) |
| v1.4.0 → 1.6.0 | Bay-floor batch (QR/kiosk/spec-sheet) → PUBLOG/FLIS catalog + scanner + hybrid search → look-alike intelligence + approximate 3-D |
| v1.7.0 → 1.9.0 | Unified `/part` + job PDF + troubleshooting + conflicts + offline Q&A → **R13 trust layer** (validate/verify/signoff/integrity/tmrev) → serviceability/kit/pinouts/training/field-notes |
| v1.10.0 → 1.12.9 | RPSTL + cross-method scoring + 200-idea roadmap → fleet readiness (readiness/handover/PMCS/bulk-ingest) → decoder + safety batch (air-gap/standards/2407/NSN/SMR/CAGE/harness-trace/MAC) → deep audit closing route-coverage gaps |
| **v1.13.0** | HOLISTIC HARDENING — four-lane dev-team review: search operators, one-time-use flags, gap log, precomputed conflicts; `corpus.py` unification; trust badges everywhere; `VERIFY.bat` as the one gate; UI coherence pass; independent audit + adversarial hardening (63 hostile cases, 0 fixes needed) |
| v1.13.1 | AI-generated 3-D illustrative tier (Meshy import lane) |
| v1.13.2 | RPS run-mode becomes a persisted Settings choice |
| v1.13.3 | `VERIFY.bat` confirmed GREEN on an actual host for the first time — 2 real bugs found doing it (a resource leak, a duplicate-append bug) |
| v1.13.4 | Full live-driving pass (every core feature exercised live, not just automated suites) + a parallel static audit → **36 real bugs found and fixed**: 12 resource leaks (13 combined with v1.13.3's), 3 dedup/caching issues, 10 regex/classification bugs (incl. two that violated the app's own "never fabricate" R13 discipline), 2 misc, plus the `verifystate.py`/`/verify` chain that had silently found nothing since the v0.96.0 restructure |
| v1.13.5 | OCR quality signal (per-page `ocr_confidence` captured from RapidOCR, no longer discarded) + a bare-F/C temperature-extraction gap fix — `test_accuracy.py` recall 80%→100% |
| v1.14.0 | 50-finding 4-tier code audit (Critical→High→Medium→Low) + a follow-up priority-5 UI/UX pass + this repo's first-ever CI workflow (plus the real bug it caught on day one) + a Tier-1 pass off a separate full-project staleness audit — see `CHANGELOG.md`'s `[1.14.0]` entry for full detail; `verify_all.py` reaches 26/26 ALL GREEN for the first time |
| **v1.15.0 (current)** | 30-commit, ~25-hour session: Discovery Engine phase 1 + in-app scan/OCR, a 6-agent reachability audit closing 3 more orphaned-module gaps, all 5 previously-deferred items closed, an RPS `Premium` tier + hardware-adaptive deepening, OCR confidence threaded end-to-end, a 52-fix functions+security pass, a CI-caught barcode bug, a masterfile/dedup audit, airgap NIIN-decision sync, a weekly DB backup task, and a UX pass — see the "True current state" paragraph above and `CHANGELOG.md`'s `[1.15.0]` entry for full detail; `verify_all.py` reaches 46/46 ALL GREEN |

## 6 · Known outstanding items (host-side, still owed as of today)

**Resolved since the last update** (kept here, struck through in spirit, for continuity — see §5 for detail):
`VERIFY.bat` confirmed GREEN on host (v1.13.3, reconfirmed through every tier of v1.14.0 and every commit of
v1.15.0 — 46/46 as of `9b0e5b9`) · the resource-leak / uncached-endpoint / regex-fabrication classes of bug
that a full audit specifically went looking for are now fixed (v1.13.4) · a MECHANICAL checker now exists for
the "built but never wired in" class specifically (`audit_features.py [7]`, v1.15.0) — the same class that had
recurred at least 9 times across measures/schemgraph/tables/RPSTL/pagetrim/keywords/tables_plus-stitch/
Office-formats/dedup, all now closed · the multi-GB `viewer.db` finally has automatic backup protection beyond
the source-file snapshot vault (item 4 below is now "confirm it's actually fired," not "doesn't exist").

**Still open:**
1. **R10 literal screenshots have never actually been saved as artifacts.** `docs/screenshots/` still holds only
   a README of intended routes. Every session since — v1.13.4, v1.14.0, v1.15.0 — has live-verified extensively
   against the real running app (screenshots viewed inline during each session) but none were saved to
   `docs/screenshots/`. This remains the single most consistently-deferred action across every session. Needs a
   screenshot captured and saved per major page using the `<version>-<page>.png` convention.
2. **`BUILD-CONFLICTS.bat`** — first precomputed conflict-sweep run, still never run; `index/conflicts.db`
   doesn't exist yet. Optional while OCR is paused.
3. **`measures.py`'s bare-number-fused-to-single-letter-unit ambiguity** (e.g. an RPSTL item number "489A"
   reading as "489 Amps") — the same bug class fixed elsewhere (`fluidsmatrix.py`'s "12L", `measures.py`'s own
   oil-grade/newline cases, v1.13.4), but this specific one is broader and needs corpus-wide regression testing
   before a safe fix. Documented in `CHANGELOG.md` `[1.13.4]`, not yet patched by v1.14.0 or v1.15.0.
4. **`safeguard.py backupdb`** — a manual entry point (`run_backupdb.bat`) and an automatic weekly scheduled
   task (`THE_VIEWER_WeeklyDBBackup`) both shipped in v1.15.0, but neither has been confirmed to have actually
   run against the real production index on the host yet.
5. **OCR completion** — was ~43.8% at the v1.0.0 cut; **confirmed 94.4% as of the v1.13.4 session** (live
   `/status` check, 2026-08-08: 1,745,197 of 1,848,465 pages searchable); not re-checked during v1.14.0 or
   v1.15.0, both code-quality/feature passes rather than ingestion runs. Check current % via `/command` or
   `/status` before assuming it's fully finished.
6. **A live analytics record still carries an old bad NSN** (dated 2026-06-01, traced during v1.13.4's
   live-driving pass to a since-fixed bad example-data bug) — real historical data, R6 append-only, left for the
   user to decide whether to touch.
7. **Staleness-audit Tiers 2, 5, 6** — `[1.23.0]`'s reconciliation found Tiers 3 (dependency/CI hardening,
   `8f795bc`) and 4 (repo bloat/env vars/Windows CI, `1b3c6d8`) were actually done on 2026-08-18; the Tier-1
   pass (`3054dad`) plus these two were simply never reconciled here until now. Only 2/5/6 remain genuinely
   unstarted.
8. **v1.15.0's own deliberately-deferred items:** `camelot_tables()` (3rd table-extraction engine pilot) stays
   unwired into `/api/tables_plus` — a documented cv2/opencv-python binary-collision risk on version skew, not
   just unmeasured benefit; `dedup.py` cross-TM-family duplicates aren't caught by design (the TM-family
   blocking that makes the O(n²) pass tractable at real corpus scale trades that away deliberately).
9. **Route count (265, 244 GET + 21 POST) hasn't been recounted since v1.14.0** — v1.15.0 added a real batch of
   new routes (`ocr_backlog_start`, `ingest_upload`, `airgap_export_decisions`/`import_decisions`, 3
   `symbols_*` routes, `editions`); worth a fresh audit pass.
10. **~~Real semantic embeddings + hybrid ranking~~** — stale, corrected in `[1.23.0]`'s reconciliation:
    `hybrid.py` already does real RRF fusion of keyword (FTS) + `embed.py` semantic search, confirmed
    directly. The v1.14.0-Medium-tier `_box()` CAD-mesh-builder duplication (previously listed as still open
    in `HANDOFF-NOTE.md`) was also found already fixed (`37d909b`, 2026-08-18) and reconciled — not repeated
    here since it was never listed in this file to begin with.
11. **5 open PRs as of `[1.23.0]`, none merged yet**, each independently branched off `main`: `[1.18.0]`
    measures.py unlabeled-bare-unit case (genuinely open, needs real corpus data); `[1.19.0]` home-page nav
    regroup; `[1.20.0]` search click instrumentation + heuristic re-rank (the actual learned model is gated
    on this merging and accumulating real click volume); `[1.21.0]` per-line OCR confidence capture (per-word
    stays open, GPU-gated); `[1.22.0]` multi-column reading-order reconstruction.

## 7 · Downloadable artifacts produced across the project's life

- **`docs/diagrams/`** — 185+ dark-theme diagram PDFs (+ matching SVGs, several with PNG previews and `.mmd`
  sources) as last counted, one pair per addition per R2/R3, numbered roughly 00→113+ plus named ones
  (`CHANGELOG-VISUAL.pdf`, `CHANGELOG-DUALTRACK.pdf`) — count not re-tallied since v1.13.2; v1.15.0 shipped
  without new diagrams (a feature/audit session, not a diagram-tracked addition).
- **`docs/CHANGELOG.md`** (entry count not re-tallied since v1.13.2 — treat "219 entries" from an earlier pass
  as stale) / **`docs/CHANGELOG-LEGACY.md`** (143 entries, dual-track parity per R7).
- **`docs/ITERATION-SNAPSHOTS.md`** + **`docs/ITERATION-DASHBOARD.html`** — the tagged FEATURE/UPGRADE/POLISH/FIX
  index, regenerable via `engine/build_iteration_snapshot.py`. **Not regenerated as part of the v1.15.0
  reconciliation** (2026-08-24) — still reflects v1.14.0; see `HANDOFF-NOTE.md`'s "Suggested next".
- **`docs/HANDOFF-NOTE.md`** — the living session hand-off (reconciled to v1.15.0).
- **`docs/ocr_example_before_after.pdf`** — OCR quality proof.
- **`docs/RELEASE-NOTES-1.0.md`** — the v1.0.0 release notes.
- This file, **`docs/MASTER-RECONCILIATION.md`**.
- Data deliverables (not "downloads" in the document sense, but produced artifacts): `index/viewer.db`,
  `index/publog.db`, `index/masterfile.db`, `index/cadcache/` (~32,622-part CAD render cache),
  `index/conflicts.db`, `index/dedup.db` (edition/near-duplicate clustering, 1.15.0).

<!-- END OF FILE -->
