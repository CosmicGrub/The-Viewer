# THE VIEWER — Master Reconciliation (all chats, all versions → one record)

**Compiled 2026-08-08, updated 2026-08-09, reconciled again 2026-08-18, again 2026-08-24, again 2026-08-29
(6 PRs merged, `[1.18.0]`–`[1.23.0]`, plus a route-count re-audit, `[1.24.0]`), and seven more times on
2026-08-30 (a critical real-host fix: 4 missing schema migrations, `[1.25.0]`; `conflicts.py`'s
cross-vehicle false-positive fix, itself needing a second pass after adversarial review caught a safety
regression in the first, `[1.26.0]`; wiring that fix's new fields into `engine/ui/part.html`, `[1.27.0]`;
then, following a production-readiness/EMS-VIEWER-parity audit, 3 field-reliability quick wins,
`[1.28.0]`; then a second scoping audit's Build Roadmap "Now" tier — a missing-CSS-token bug worse than
first scoped, a doubled fuzzy-search scan, 5 modals with no real focus trap, 3 unlabeled viewer images,
3 real WCAG contrast failures, 10 unlabeled controls, `[1.29.0]`; then the same roadmap's "Next" tier —
5 orphaned modules wired in, a related-parts card, search-result OCR/conflict signals, symptom query
routing, `index.html` finally loading `/base.css`, `[1.30.0]`; then a Gap Sweep audit's 5 priority items
— RapidOCR installed, `/api/search_hybrid` made parameter-complete and switched on as primary search,
one dead column filled, 3 more orphans wired, a real `"search"` analytics event, `[1.31.0]`; then a
same-day CRITICAL fix — installing sentence-transformers silently made a stale, pre-existing embeddings
index look "fresh" to the new primary search endpoint, caught and fixed before reaching any real user,
`[1.32.0]`; then 2 more orphaned routes wired — blank DA-2404/2407 print-on-demand forms, `[1.33.0]`; then
the full-corpus-rebuild prerequisite `[1.32.0]`'s own research flagged — `embed.build_index()`'s
hardcoded 200,000-row cap made configurable, unbatched per-row encoding replaced with real chunked
batching (~1.3x measured), and checkpointed/resumable so a killed mid-run process loses at most one
chunk, code + tests only, `[1.36.0]`; then `[1.33.0]`'s one deliberately-open item closed —
`/api/ingest_scan` wired into `ingest.html` as a separate, honestly-captioned panel, `[1.37.0]`; then
`parts.cagec`/`parts.smr` cross-database correlation — the design `[1.33.0]` scoped but deliberately
didn't start, implemented and verified against this repo's own real corpus at 48.0% yield, catching and
fixing a real production-breaking `executemany()`-inside-an-open-cursor "database is locked" bug before
it shipped, `[1.38.0]`; then a same-day CRITICAL follow-up, found during adversarial verification of
`[1.36.0]` before the rebuild it gates was launched — a mid-build `model.encode()` failure on one chunk
could silently blend hash-fallback vectors into an index still stamped as pure `sentence-transformers`,
the `[1.32.0]` failure mode again at row/chunk granularity; fixed by tracking per-chunk fallback events
(surviving interrupt+resume) and withholding the meta stamp whenever any are present, code + tests
only, `[1.39.0]`; then a readiness audit's completeness pass on `part.html` — its shared `gj()` fetch
helper collapsed a real transport/server failure and a genuine empty result into the exact same falsy
shape across all 15 fetch call sites, so the two safety-relevant panels (cross-manual conflicts,
one-time-use/TTY fasteners) failed completely silently; fixed to resolve an honest `{ok,status,body}`
and show a distinct message for each outcome, catching and fixing two real bugs live during
verification (an always-truthy `s.title` empty-test, a shared-card overwrite race) before shipping,
`[1.41.0]`; then version-staleness detection — nothing recorded when the process started or whether
its code still matched disk, so a server left running across a `git pull` looked completely healthy
while quietly running stale code; fixed with `STARTUP_VERSION`/`STARTUP_TIME` captured once at
import, a TTL-cached on-disk `VERSION=` re-read (never a re-import, never `git`), new
`started_with_version`/`started_at`/`code_changed_since_start` fields on `/healthz`/`/api/ops`, and a
non-dismissible whole-site banner in `shared.js` that clears itself once the process is actually
restarted, `[1.42.0]`).** This document
exists because the project's own canonical docs had drifted out of sync with each other across sessions —
including, at the 2026-08-09 update, this file itself: it named **v1.13.4** as the state all canonical docs
agreed on the same day `CHANGELOG.md`'s newest entry had already moved on to **v1.13.5**. The exact same drift
class recurred at the 2026-08-24 update: `CHANGELOG.md` itself only caught up to v1.15.0 five days after that
version shipped (PR #4) — this file is a downstream reconciliation of that same reconciliation, not an
independent re-derivation. This file is the reconciled, single-source feature record, cross-checked against
the actual files on disk (not just memory) where practical. It supplements — does not replace —
`CHANGELOG.md` (a per-change log whose entry count is no longer re-tallied here after v1.13.2, see §7) and
`HANDOFF-NOTE.md` (the living session hand-off). Treat all four as canonical going forward; keep them in sync.

**True current state: v1.42.0, shipped 2026-08-31** (version-staleness detection — a server left
running across a `git pull` looked completely healthy while quietly running stale code, since nothing
recorded when it started or whether its code still matched disk; fixed with `STARTUP_VERSION`/
`STARTUP_TIME` captured once at import, a TTL-cached on-disk `VERSION=` re-read, new
`started_with_version`/`started_at`/`code_changed_since_start` fields on `/healthz`/`/api/ops`, and a
non-dismissible whole-site banner in `shared.js` — see §6 item 26). Immediately prior: v1.41.0, shipped
2026-08-31 (`part.html` no longer conflates a failed request with "part not found" — `gj()`, the
shared fetch helper behind all 15 of the page's fetch call sites, now resolves an honest
`{ok,status,body}` instead of collapsing a real transport/server failure and a genuine empty result
into the same falsy shape; two real bugs (an always-truthy `s.title` empty-test, a shared-card
overwrite race between the conflicts/validate panels) caught live during verification and fixed
before shipping — see §6 item 25). Immediately prior: v1.39.0, shipped 2026-09-01 (CRITICAL
fix — `build_index()` could stamp an index as pure `sentence-transformers` even when a mid-build
`model.encode()` failure had silently blended hash-fallback vectors into one chunk; found during
adversarial verification of `[1.36.0]` before its gated full-corpus rebuild was launched — see §6 item
24). Immediately prior: v1.38.0,
shipped 2026-09-01 (`parts.cagec`/`parts.smr` cross-database correlation — `correlate_parts_cagec()`
joins `index/rpstl.db` into `parts` on `(document_id, page, nsn)`, filtered through `index/cage.json`;
48.0% yield measured against a real 4,000-row sample of this repo's own corpus; a real bug caught
during verification and fixed before shipping, not after; independently adversarially verified before
merge, 0 incorrect writes found across ~5,300 audited real writes — see §6 item 23). Immediately
prior: v1.37.0, shipped 2026-08-31 (`[1.33.0]`'s one deliberately-open item closed — `/api/ingest_scan`
wired into `ingest.html` as a separate "Broader file scan" panel, never merged into the existing
Preview panel; shipped copy briefly and incorrectly overclaimed Office-format coverage, caught by
adversarial verification before merge and corrected — see §6 item 22). Immediately prior to that:
v1.36.0, shipped 2026-08-31 (`embed.py`'s full-rebuild prep — configurable row cap, batched encoding,
resumable checkpointing, no full-corpus rebuild run yet — see §6 item 21). Immediately prior to that:
v1.33.0, shipped 2026-08-30 (2 more orphaned routes wired — blank DA-2404/2407 print-on-demand forms,
one click away on `pmcs.html`/`jobcard.html`, plus confirmation that
`/api/chapter_jump` genuinely isn't worth wiring — see §6 item 20). Immediately prior to that, all the
same day (2026-08-30):
v1.32.0 (CRITICAL, same-day fix — installing sentence-transformers to research semantic search's
feasibility silently reclassified this repo's real, stale, pre-existing embeddings index as "fresh,"
feeding near-noise cosine scores into `/api/search_hybrid`'s RRF fusion — the primary search endpoint as
of `[1.31.0]` — until caught and fixed; see §6 item 19); v1.31.0 (a Gap Sweep audit's 5 priority
items — RapidOCR installed, `/api/search_hybrid` made parameter-complete and switched on as the primary
search endpoint, one genuinely-fixable dead column filled, 3 more orphaned routes wired (including a
brand-new `/handover` page), a real `"search"` analytics event — see §6 item 18); v1.30.0 (the Build
Roadmap's full "Next" tier — 5 orphaned modules wired into the UI, a
related-parts card, OCR-confidence/conflict signals in search results, symptom/"how do I" query
routing, `index.html` finally loading `/base.css` + a new control-border token — see §6 item 17); v1.29.0
(the Roadmap's "Now" tier — restored
missing/undefined CSS color tokens on the home page, 3 real WCAG contrast fixes, a doubled fuzzy-search
scan fixed, focus traps on all 5 real modals, alt text on the 3 primary viewer images, ARIA labels on the
10 highest-traffic controls — see §6 item 16); v1.28.0 (3
field-reliability quick wins from a production-readiness/EMS-VIEWER-parity audit — cart persistence,
stepflow voice-nav wiring, PORTING.md currency — see §6 item 15); v1.27.0 (`engine/ui/part.html` now shows
`[1.26.0]`'s `cross_vehicle`/`vehicles` fields to a technician, see §6 item 14); v1.26.0 (`conflicts.py`'s
cross-vehicle false-positive fix); v1.25.0 (critical fix: 4 missing schema migrations applied to the real
production DB, see §6 item 13); before that v1.24.0, shipped 2026-08-29 (route-count re-audit, docs-only,
see §6 item 9); before that v1.15.0, shipped 2026-08-19, `main` @ `9b0e5b9`. 30
commits, ~25 hours, effectively one
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
agreement scoring (`crossmethod.py`, 1.10.0) · **`parts.cagec`/`parts.smr` cross-database correlation**
(`correlate_parts_cagec()`, 1.34.0) — joins `rpstl.db`'s parts_rows into `parts` on
`(document_id, page, nsn)`, filtered through the real `cage.json` CAGE registry, feeding
`jobcard.py`'s printed CAGE/SMR lines and the look-alike-parts CAGEC/SMR discriminator, both
previously always-empty · **PUBLOG/FLIS federal catalog** — ~16 GB DLA export → NIIN-keyed
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
   reading as "489 Amps") — the **labeled** sub-case ("ITEM 489A", any bare-letter unit preceded by a
   figure/table/item/detail/etc. reference word) is fixed as of `[1.18.0]`, generalizing the existing
   degF/degC `_CALLOUT` guard. The **unlabeled** sub-case (a bare "489A" with no preceding label) stays
   open — a blanket no-space-required guard would silently drop real "12V"/"5A"/"60W"-style fused
   electrical readings (standard, common notation in this corpus), a recall regression with no safe way
   to verify without the real corpus. Documented in `CHANGELOG.md` `[1.13.4]`.
4. ~~**`safeguard.py backupdb`**~~ — **DONE, `[1.25.0]`:** run for real (3.64 GB `VACUUM INTO`, verified via
   `PRAGMA quick_check`, 147.5s); `THE_VIEWER_WeeklyDBBackup` scheduled task registered and test-fired via
   `schtasks /Run` — confirmed it actually executes end-to-end (produced a second real backup file).
5. ~~**OCR completion**~~ — **RE-CHECKED, `[1.25.0]`:** **94.62%** (1,749,089 of 1,848,465 pages have
   `char_count > 0`), up slightly from 94.4% at v1.13.4. No OCR process currently running (confirmed via
   process inspection).
6. **A live analytics record still carries an old bad NSN** (dated 2026-06-01, traced during v1.13.4's
   live-driving pass to a since-fixed bad example-data bug) — real historical data, R6 append-only, left for the
   user to decide whether to touch.
7. ~~**Staleness-audit Tiers 2, 5, 6**~~ — **CORRECTED, `[1.24.0]`:** `[1.23.0]`'s "only 2/5/6 remain
   genuinely unstarted" claim was itself wrong. `git log --all --grep="Drift Report\|Tier"` shows the Viewer
   Drift Report staleness audit only ever had **4 tiers total, not 6**: Tier 1 (`3054dad`), Tier 2 (`132132f`
   — the [1.14.0] documentation-reconciliation commit itself, missed by `[1.23.0]`'s check same as Tiers 3/4
   initially were), Tier 3 (`8f795bc`, dependency/CI hardening), Tier 4 (`1b3c6d8`, repo bloat/env
   vars/Windows CI) — whose commit message states outright: "This closes out all 4 tiers of the Viewer Drift
   Report staleness audit run across this session." **All 4 tiers are complete; there is no Tier 5 or 6 and
   never was.**
8. **v1.15.0's own deliberately-deferred items:** `camelot_tables()` (3rd table-extraction engine pilot) stays
   unwired into `/api/tables_plus` — a documented cv2/opencv-python binary-collision risk on version skew, not
   just unmeasured benefit; `dedup.py` cross-TM-family duplicates aren't caught by design (the TM-family
   blocking that makes the O(n²) pass tractable at real corpus scale trades that away deliberately).
9. ~~**Route count (265, 244 GET + 21 POST) hasn't been recounted since v1.14.0**~~ — **DONE, `[1.24.0]`:**
   mechanically re-counted live against `engine/features/registry.py` — **276 routes (250 GET + 26 POST),
   zero collisions**, verified at the source level (135 decorator-declared GET paths across
   `features/routes/*.py` + 115 `static.py`-programmatic GET paths = 250 exactly, no overlap between the two
   registration sources; 26 decorator POST paths, no internal duplicates). New since v1.14.0: `/api/pageqa`,
   `/api/vlm`, `/api/layout`, `/api/editions`, `/api/symbols`, `/api/symbols_page_image` (GET);
   `/api/airgap_export_decisions`, `/api/airgap_import_decisions`, `/api/analytics_log`,
   `/api/ingest_upload`, `/api/ocr_backlog_start`, `/api/symbols_template` (POST). See `CHANGELOG.md` `[1.24.0]`.
10. **~~Real semantic embeddings + hybrid ranking~~** — stale, corrected in `[1.23.0]`'s reconciliation:
    `hybrid.py` already does real RRF fusion of keyword (FTS) + `embed.py` semantic search, confirmed
    directly. The v1.14.0-Medium-tier `_box()` CAD-mesh-builder duplication (previously listed as still open
    in `HANDOFF-NOTE.md`) was also found already fixed (`37d909b`, 2026-08-18) and reconciled — not repeated
    here since it was never listed in this file to begin with.
11. **Tier-2 "learned search re-ranker" — Phase 1 (click instrumentation + heuristic re-rank) shipped in
    `[1.20.0]`; the actual learned model is still open**, now that a real click-through log exists to train it
    on (see `CHANGELOG.md` `[1.20.0]` / `HANDOFF-NOTE.md` item 8).
12. **`[1.18.0]`–`[1.23.0]`, 6 PRs from the same session as this reconciliation, all now merged.** Beyond
    item 11 above: `[1.18.0]` measures.py unlabeled-bare-unit case stays genuinely open (needs real corpus
    data); `[1.19.0]` home-page nav regroup (nothing left open); `[1.21.0]` per-line OCR confidence capture
    (per-word stays open, GPU-gated); `[1.22.0]` multi-column reading-order reconstruction (3+ column layouts
    not specifically detected; the row-alignment threshold is tuned against synthetic fixtures only, worth
    real-corpus validation if mis-detections surface). `[1.23.0]` (this entry) is documentation-only.
13. **`[1.25.0]` — critical fix: the real `viewer.db` was missing 4 schema migrations (0009–0012)**,
    silently breaking `measures`/`ask`/`cautions`/`pmcs`/`oneuse` since v1.13.5 (~3 weeks) — the test
    suite never caught it because it runs against a synthetic fixture DB with the correct schema. Fixed
    via `python viewer_ingest.py migrate` (auto-backs up first, applies atomically); confirmed live
    (`find_for_query('torque')`: 0 → 26 real cited results); `verify_all.py` re-run clean (48/49, only the
    known pre-existing flake) after. ~~**New follow-up surfaced while fixing this**: `BUILD-CONFLICTS.bat`'s
    real first-ever sweep found data..., but its 1548-of-2000-subjects "conflict" rate is inflated by
    generic, corpus-wide subject phrases pooling unrelated values from different vehicles/manuals under
    one subject string~~ — **FIXED, `[1.26.0]`, see item 14 below.**
14. **`[1.26.0]` — fixed `conflicts.py`'s cross-vehicle false positives, in two passes.** Pass 1 tried
    grouping by `(type, unit, vehicle)`; adversarial review caught it silently DROPPING a genuine
    cross-manual disagreement whenever the same real vehicle was filed under two different ingest-folder
    spellings (confirmed live: a real 35-vs-50-ft-lb torque conflict returned `[]`) — reverted before
    merge. Pass 2 (shipped) restores byte-identical recall to the pre-bug code and instead annotates each
    conflict with `vehicle`/`vehicles`/`cross_vehicle`, never filtering by it. Re-swept for real: 1548
    conflicts unchanged (recall confirmed unregressed), 5,071 now marked `cross_vehicle: true` (ambiguous)
    vs 1,466 `cross_vehicle: false` (confirmed single-vehicle). ~~**Genuinely still open**:
    `engine/ui/part.html` doesn't yet read any of the new fields~~ — **DONE, `[1.27.0]`:** the conflict
    card now shows each value's vehicle inline plus a "⚠ Spans N different vehicle labels..." caveat on
    `cross_vehicle: true` conflicts; verified live against the real WINCH INSTALLATION example. Still
    open, lower priority: a pre-existing citation-completeness quirk (citations dedup
    by distinct value not by doc, so a vehicle named in `vehicles` can have zero backing citation in
    `values`) and the fact that `vehicle` is a raw ingest-folder name, not a curated identity, so
    `cross_vehicle: false` can still in principle mean two different real vehicles sharing one broad
    folder (e.g. "WORK", ~65% of the corpus). Both disclosed in `conflicts.py`'s own docstring, neither
    fixed. See `CHANGELOG.md` `[1.26.0]` for the full two-pass story.
15. **`[1.28.0]` — 3 field-reliability quick wins from a production-readiness/EMS-VIEWER-parity audit.**
    The audit itself: a source-cited comparison of THE VIEWER against fielded military IETM viewers
    (EMS-VIEWER/EMS-NG, IADS) plus an honest search-accuracy scorecard, published as a standalone dossier.
    Fixes shipped from its "do now" tier: the parts-request cart now persists to `localStorage` from
    every mutation path (previously the app's other core workflow had zero autosave); `stepflow.html`
    now actually triggers `readaloud.js`'s hands-free voice step-nav (additive class aliases, zero style
    impact, confirmed); `docs/PORTING.md` updated from a 14-version-stale v1.13.2 to current, now
    explicitly warning about the real `[1.25.0]` schema-migration trap. All three verified live in a
    real browser. ~~**Still open from the same audit**: ARIA/`<label>`s exist on only 2 of 45 UI pages;
    the home page's 6 modals lack real focus traps~~ — see item 16.
16. **`[1.29.0]` — the Build Roadmap's full "Now" tier** (a second scoping audit, companion to `[1.28.0]`'s
    dossier, with real benchmarks + a real programmatic WCAG contrast audit run on this host). The
    `--acc` CSS bug turned out worse than first scoped: confirmed live via `getComputedStyle()`,
    `index.html`'s own `:root` duplicate never defined `--acc`/`--grn`/`--amb`/`--red`/`--teal`/`--pur` at
    all, so keyboard focus was silently invisible and the operator/mechanic side badges, "Saved"
    confirmations, and chapter-count status text were rendering in plain white instead of their intended
    colors — all restored. Restoring them exposed 3 real WCAG AA text-contrast failures (2.98:1 / 3.36:1 /
    4.02:1, all below the 4.5:1 floor); fixed with new lightened text-only token siblings
    (`--grn-tx`/`--red-tx`), locked in by a new automated contrast guard in `engine/verify_ui.py`. A
    fuzzy-search vocabulary scan that ran 2-3x per query on identical tokens now runs once per token per
    request via a request-scoped cache (`search_feature.py`), proven by a new call-counting regression
    test, not just "search() doesn't crash". A shared `VW.trapFocus()` (`shared.js`, modeled on
    `palette.js`'s own correct Tab-trap) is now wired into all 5 real modals — Tab-cycle containment,
    Escape-to-close, focus-restore, each verified live. The 3 primary viewer images have `alt` text; the
    10 highest-traffic controls (home + 8 tool search boxes + `collections.html`'s form) have
    `aria-label`s. ~~**Still open from the same roadmap**: 5 built-but-orphaned modules...~~ — see
    item 17.
17. **`[1.30.0]` — the Build Roadmap's full "Next" tier**, grounded in 4 parallel research passes
    reading the real modules/routes/UI patterns before any code was written (not the roadmap's own
    summary text). The 5 orphaned modules (`commonality.py`/`tmrev.py`/`harnesstrace.py`+
    `pinouts.py`/`macchart.py`/`crossmethod.py`) are wired in on `part.html`/`procedure.html`, each
    verified live or via synthetic data where this corpus has no organic example. `commonality.py`'s
    placement was corrected from the roadmap's own suggestion: confirmed live that `readiness.html` is
    vehicle-scoped end to end while `commonality.py` does an exact NSN/name/part-number lookup — a
    genuine shape mismatch, shipped on `part.html` instead. A "Related parts" card (`xref.py`) landed
    on `part.html` and `dossier.html`. `p.ocr_confidence` now reaches every search result (a one-column
    SELECT fix in `search_feature.py`'s `search()`) — though a real corpus check found this deployment
    has zero populated `ocr_confidence` values across 53,391 OCR'd pages, disclosed honestly rather than
    glossed over. The conflict-flag and symptom/"how do I" query-routing items both shipped in a form
    measurement changed from the roadmap's own sketch: `conflicts.py`'s `check_query()` measured
    200-227ms and `/api/ask` measured 900-1855ms on common queries (both confirmed directly on this
    host) — too slow to bake into `/api/search`'s own response or fire automatically on every keystroke,
    so both now run independently/on-demand instead. `index.html` finally loads `/base.css` — a real
    visual-diff pass, not a blind strip-and-link: the fully-redundant `:root`/`[hidden]` duplication is
    gone, the kiosk-mode/touch-target rules stay (this page's `a.ghost` class isn't covered by
    base.css's shared `a.btn` selector — confirmed `.ghost` is 69× local-only), and a real latent
    checkbox-distortion bug in this page's duplicate (already fixed once in base.css) got fixed in the
    same pass. Paired with a new `--line-ctl` interactive-control border token (`--line` itself measured
    1.05-1.45:1, far under the 3:1 UI floor), locked in by a new guard in `engine/verify_ui.py`.
    **Still open from the same roadmap** (Later tier, calendar/data-gated by design): semantic search is
    real but non-functional in production today (no embedding model installed, stale index) — needs a
    decision, fix or hide; ~~RRF hybrid fusion has zero UI callers~~ — see item 18; a learned re-ranker
    is gated on click volume that doesn't exist yet (`index/analytics.jsonl` logs zero `search`/`click`
    events); the other 35 of 45 UI pages still carry no ARIA of their own; no accounts/RBAC, TLS,
    offsite backup automation, or accreditation artifacts exist for multi-site fielding.
18. **`[1.31.0]` — Gap Sweep: the 5 priority items**, from a 5-agent parallel research audit answering
    "what's going on with OCR confidence, and what other gaps exist." RapidOCR installed
    (`rapidocr-onnxruntime` 1.2.3) and independently re-verified live in this session's own process, not
    just the installing agent's self-report — `viewer_ingest.py`'s confidence write path was already
    correct; this machine's OCR engine (Tesseract fallback, zero confidence captured) was the real gap.
    `/api/search_hybrid` — item 17's own still-open finding — is now the home search box's primary
    endpoint, closing that gap for real: a second research pass first found the route silently dropped
    side/match_any/fuzzy/mode/tm:/vehicle:/nsn: operators entirely (would have broken the SIDE toggle
    and offline did-you-mean outright if switched naively), so `hybrid.hybrid_search()` and
    `r_search_hybrid` gained full parameter parity with `/api/search` first, then the switch was verified
    extensively — 100% result-count parity across ~20 diverse test queries, plus a genuine glossary-aware
    ranking improvement for acronym queries confirmed live (a "CTIS" query now also ranks pages
    mentioning "Central Tire Inflation System"). Of the 5 dead columns Gap Sweep found (same "read but
    never written" shape as `ocr_confidence`), only `ref_nsn.superseded` at the FLIS site was genuinely
    trivial — its value was already parsed, just never bound to the column; the other 4
    (`parts.cagec`/`smr`/`uoc`, `ref_nsn.data_date`) need real cross-database integration or brand-new
    extraction logic, correctly left open rather than rushed. 3 more orphaned routes wired in: `rpstl.py`
    (a new card on `part.html`), `partspdf.py` (a new button on `jobcard.html`), and `handover.py` — a
    genuinely new page, `/handover`, since none of the 3 candidate existing pages (`status.html`,
    `ops.html`, `jobcard.html`) fit its shop-wide "since last shift" scope. A real `"search"` analytics
    event kind added — declared-valid in `analytics.py`'s `_VALID` set since it was first written, but
    nothing had ever logged one; `top_searches` had always been silently empty. **Still open**: 4 of the
    5 dead columns; 19 more orphaned routes beyond the 8 now wired across `[1.30.0]`/`[1.31.0]`
    (standouts: `/api/chapter_jump`, `/api/tables_plus`, `/api/ingest_scan`, the DA-2404/2407 forms,
    `/api/schemgraph_review`); ~~semantic search still non-functional~~ — see item 19; everything else
    from item 17's still-open list. See the Gap Sweep artifact and `CHANGELOG.md` `[1.28.0]`–`[1.31.0]`.
19. **`[1.32.0]` — CRITICAL, same-day fix: a stale embeddings index was silently reclassified as
    fresh.** While researching semantic search's real feasibility (a genuine `pip install
    sentence-transformers`, not a simulation — item 18's still-open list flagged this as the sole
    remaining blocker), `embed.backend()` started returning `"sentence-transformers"` instead of
    `"hash-fallback"`. `embed._index_is_stale()`'s no-meta-stamp check only ever compared the
    *current* backend against itself (`return backend() == "hash-fallback"`) — never against what the
    index was actually built with — so this repo's real, pre-existing, unstamped
    `index/embeddings.npy` (built under the old hash-bucket math, since sentence-transformers had
    never been installed here before) was silently reclassified from stale to fresh. It then started
    feeding through `/api/search_hybrid`'s RRF fusion — the primary search endpoint as of `[1.31.0]`
    — as near-noise cosine scores (0.18–0.19, confirmed live against real corpus queries, nowhere near
    the 0.7+ a genuine semantic match produces) blended into real search results as if they were a
    legitimate corroborating signal. Fixed the same day, before reaching any real user:
    `_index_is_stale()` now requires a meta stamp proving an index was built by the backend that is
    *currently* active, in both directions of mismatch. `embed.py`'s own self-test had also silently
    stopped exercising this exact check once a real model backend became available (gated behind
    `if backend()=="hash-fallback"`) — now runs unconditionally. Two more tests
    (`test_routes.py`'s `/api/pageqa` content check, `test_pageqa.py`'s "no backend" subprocess test)
    had the same "transformers/torch never installed" assumption baked in — fixed to compute the
    expected value live / force a genuinely nonexistent `VIEWER_VLM` module, making both deterministic
    regardless of what's installed. **Separately confirmed via the same research pass** (not yet
    acted on): a true full-corpus embeddings rebuild would cost ~9-12 hours of continuous CPU wall
    time and ~2.6GB disk on this host, and needs a source-code change first (the 200,000-row cap is
    hardcoded, covering only ~12% of the corpus) — a real go/no-go decision for a human, not something
    to launch unattended. See `CHANGELOG.md` `[1.32.0]`.
20. **`[1.33.0]` — 2 more orphaned routes wired**, picked up from item 18's still-open list. `GET
    /api/form_2404`/`/api/form_2407` (blank DA-2404 PMCS worksheet / DA-2407 maintenance-request
    worksheet) were real, tested routes with zero UI entry point — each already had a working `POST`
    sibling to fill a worksheet from logged data, but the blank print-on-demand form had no button
    anywhere. Now an always-enabled print link on `pmcs.html`/`jobcard.html` respectively, deliberately
    ungated (unlike `[1.31.0]`'s `partspdf.py` button) since a blank form needs no prior search; both
    verified live via `curl` returning genuine single-page PDFs before shipping. `/api/chapter_jump` —
    one of item 18's named standouts — was investigated and confirmed genuinely NOT worth wiring:
    `index.html`'s `openViewer()` already calls the richer `/api/chapters`, which `chapter_jump` is a
    strict subset of, and `renderChapterBanner()` needs the fuller response regardless, so wiring it in
    would only add a second round-trip for data already in hand. `/api/ingest_scan` — another named
    standout — stays open on purpose, pending a product decision: its own supported-extension list
    (`ingestpipe.SUPPORTED`) undercounts what the real ingest job actually processes (missing
    `.docx`/`.xlsx`/`.pptx`/`.rtf`/`.bmp`/`.gif`), and a UI addition next to the existing Preview button
    risks showing two legitimately-disagreeing "how many new files" counts with no explanation. Also
    scoped this session but explicitly NOT started: a design for `parts.cagec`/`smr` cross-database
    correlation (join `rpstl.db`'s `parts_rows` into the main `parts` table via the confirmed-reliable
    `(document_id, page, nsn)` key, filtering garbage CAGEC values via the existing `index/cage.json`
    registry — sized at ~1 focused day of implementation + verification, not a same-day fix, given real
    data-quality landmines already investigated); and a full semantic-search corpus rebuild (the one-time
    `sentence-transformers` package install is done and verified working end-to-end — real
    `embed_text()`/`encode()` calls, cosine 0.725 for related text vs. 0.070 for unrelated — but a true
    full rebuild is an explicit ~9–12 hour unattended commitment plus ~2.6GB disk, an explicit NO-GO for
    autonomous execution per the research agent's own recommendation, adopted rather than overridden).
    **Still open**: 4 of the 5 dead columns; ~17 more orphaned routes beyond the 10 now wired across
    `[1.30.0]`/`[1.31.0]`/`[1.33.0]` (standouts: `/api/tables_plus`, `/api/ingest_scan`,
    `/api/schemgraph_review`); semantic search still non-functional pending the rebuild decision above;
    everything else from item 18's still-open list. See `CHANGELOG.md` `[1.33.0]`.
21. **`[1.36.0]` — `embed.py` full-rebuild prep: configurable cap, batched encoding, resumable
    checkpointing.** The one remaining prerequisite item 19 left open — `build_index()`'s
    `limit=200000` was hardcoded, covering only ~11.9% of this deployment's real 1,682,054 eligible
    pages — implemented and tested. Three changes: (1) `limit=None` now resolves to
    `VIEWER_EMBED_LIMIT` (env var, default 200000, same convention as `VIEWER_DB`/
    `VIEWER_OCR_PAGE_TIMEOUT`), byte-identical behavior for the sole existing caller
    (`BUILD-EMBEDDINGS.bat`, which sets no override); (2) rows are processed in chunks and each
    chunk's texts go to `model.encode()` as one batched call instead of one `embed_text()` call per
    row — measured ~40 pages/sec unbatched vs. ~53–54 pages/sec batched on this host, real corpus
    text, real model (~1.3x, re-confirming item 19's own research-pass benchmark); (3) each completed
    chunk is checkpointed to shard files (`index/_embed_build/`) plus a progress marker
    (`index/embeddings.progress.json`) keyed on the query's real `ORDER BY id` cursor, so a killed
    mid-run process resumes from its last completed chunk instead of restarting from zero — verified
    directly via a real fault injected mid-loop (not a mock), confirming the resumed run's final
    output is byte-identical (ids + vectors) to an uninterrupted run over the same sample. **The
    safety invariant `[1.32.0]` depends on is preserved structurally, not by new logic in
    `_index_is_stale()`**: `embeddings.meta.json` is written exactly once, after the shard merge
    succeeds, nowhere else — a process killed at any earlier point never touches it, so the existing
    no-meta-stamp-means-stale branch keeps refusing an incomplete build with zero changes to that
    function. **No full-corpus rebuild was run** — that ~9–12 hour, ~2.6GB commitment stays a
    separate, human-supervised action per item 19/20's own NO-GO-for-autonomous-execution finding;
    this item is code + `engine/tests/test_embed_checkpoint.py` (34 new checks) only, validated
    against small synthetic samples plus one 300-row pass against the real `index/viewer.db`
    (read-only). See `CHANGELOG.md` `[1.36.0]`.
22. **`[1.37.0]` — `/api/ingest_scan` wired into the UI**, closing the one item `[1.33.0]` deliberately
    left open. Shipped as a SEPARATE "Broader file scan" link + `#broaderOut` panel on `ingest.html`,
    never merged into the existing Preview panel (`#out`) — exactly to avoid `[1.33.0]`'s named risk of
    two silently-disagreeing "how many new files" counts. The panel's copy states, in plain language:
    what it adds over Preview (`.txt`/`.html`/`.htm`/`.xml`/`.csv`/`.md`/`.tiff`/`.tif`/`.png`/`.jpg`/
    `.jpeg` — the real `ingestpipe.SUPPORTED` set, vs. Preview's PDF-only coverage; **not**
    `.docx`/`.xlsx`/`.pptx`/`.rtf`/`.bmp`/`.gif`, which an earlier draft of the shipped copy briefly and
    incorrectly claimed — caught by adversarial verification before merge, confirmed live against a
    running server, and corrected); what's still not covered (legacy `.doc`/`.xls`/`.ppt` and `.svg` —
    discovered, a `documents` row is created, but never content-extracted by the real ingest job); that
    `.xml`/`.csv`/`.md` are themselves only a partial win — `ingestpipe.SUPPORTED` counts and dedupes
    them, but `viewer_ingest.py`'s `crawl()`/`classify_ext()`/`index_other()` has no extraction path for
    them at all, so they land in the exact same "discovered, zero content" state as `.doc`/`.xls`/`.ppt`/
    `.svg`; and that this scan's dedup method (content hash OR filename, via `ingestpipe.plan()`) differs
    from Preview's (`os.path.realpath()` exact-string-match only), so a legitimate count mismatch between
    the two panels is explained instead of left as an unexplained discrepancy. Separately traced whether
    `/api/ingest_scan` needed the `_exposed_read_guard()` gate its `GET` siblings
    (`/api/ingest_preview`/`/api/ingest_status`) carry — a gap an earlier research pass flagged as
    "worth flagging separately" — and confirmed it does NOT: it's a `POST` route, and `viewer_app.py`'s
    `do_POST` already requires the shared `X-Viewer-Token` for every `POST` when the server is
    network-exposed, before any route handler runs at all. Left as a code comment on `r_ingest_scan`
    (`engine/features/routes/ingest.py`) rather than adding a redundant guard call, so a future pass
    doesn't re-flag and "fix" a non-bug. Verified live, twice: at initial ship
    (`engine/tests/test_ingest_routes.py`'s real e2e `POST /api/ingest_scan` coverage, plus a direct
    `ingestpipe.scan_folder()` call confirming the extension gap), and again after the copy correction
    above (a real server, a temp folder with one file per extension across both the true-supported and
    true-unsupported sets, a real POST to `/api/ingest_scan` — exactly the 12 real `SUPPORTED`
    extensions came back, all 6 previously-misclaimed extensions correctly absent). **Still open**:
    everything else from item 21's still-open list (4 of 5 dead columns, ~17 more orphaned routes beyond
    the ones now wired, semantic search's full-corpus rebuild decision). See `CHANGELOG.md` `[1.37.0]`.
23. **`[1.38.0]` — `parts.cagec`/`parts.smr` cross-database correlation**, the design item 20 scoped but
    deliberately didn't start. `correlate_parts_cagec()` joins `index/rpstl.db`'s `parts_rows` into the
    main `parts` table on the confirmed-reliable `(document_id, page, nsn)` key (both DBs share the same
    `documents.id` numbering), filtered through `index/cage.json` (the real ~12k-entry CAGE registry)
    before anything is written — confirmed directly against this repo's own real `rpstl.db` that the
    filter is load-bearing: raw `CAGEC_RE` matches include real garbage (vehicle model numbers like
    `M35A3`, nomenclature words like `WINCH`/`SCREW`/`LIGHT`, RPSTL boilerplate like `WHERE`/`EXCEPT`)
    that happens to fit the "5 alphanumeric characters" shape. SMR is trusted only when that SAME
    candidate row's cagec passed validation; a key with 2+ distinct valid cagec candidates is genuinely
    ambiguous and is skipped, never guessed at (49 of 4,768 real multi-candidate keys). Wired as the new
    8th/final ingest stage, deliberately full-corpus every run (NOT `_TOUCHED_DOC_IDS`-scoped like its
    neighbors, since `extract_parts()` rebuilds the whole `parts` table every time) plus a standalone
    `python viewer_ingest.py cagec [--db PATH]` backfill for an already-ingested corpus. **A real,
    production-breaking bug was caught during verification, never shipped**: the first draft batched
    `UPDATE`s via `executemany()` INSIDE the same `SELECT` cursor loop it was reading from — invisible at
    small synthetic scale, reproduced immediately as `sqlite3.OperationalError: database is locked`
    against this repo's real 227,908-row `parts` table (which has never been under the 1,000-row
    batch-flush threshold that triggers it — this would have crashed the stage on every real ingest run).
    Fixed via `.fetchall()` before writing, matching `extract_parts()`'s own existing convention. **Real
    yield, measured against this repo's own corpus** (a random 4,000-row sample of the real 227,908, not
    the full corpus — see below): **48.0%**, closely matching item 20's ~48.2% full-corpus estimate;
    every written cagec round-tripped as genuinely present in the real `cage.json`, no known-garbage
    token ever reached a written column. New test file `engine/tests/test_cagec_smr_correlation.py`
    (38 checks): synthetic-fixture isolation tests plus real-data checks against this repo's actual
    `index/` DBs (read-only throughout, located via a worktree-aware path resolver since the real,
    gitignored `index/` doesn't exist inside a `.claude/worktrees/<id>` checkout). Sampled rather than
    full-corpus in the test suite for a measured reason, not convenience: per-row `UPDATE` cost on this
    dev host is dominated by real-time antivirus scanning of SQLite's small writes (confirmed via
    `Get-MpComputerStatus` — real-time protection on, zero exclusions configured), making a full
    227,908-row write pass take 15+ minutes of pure AV overhead. One caveat flagged, not fixed:
    `index/rpstl.db`'s mtime is ~7 weeks older than `index/viewer.db`'s on this deployment — worth a
    fresh `python build_rpstl.py` before trusting the first real backfill's yield as current. Real,
    previously-inert downstream consumers now live: `figureparts.py`→`jobcard.py`'s printed "CAGE"/"SMR"
    lines on the mechanic-facing job-card PDF, `partlocate.py`, `parts_feature.py`'s look-alike-parts
    CAGEC/SMR discriminator, `jobpack.py`'s JSON export — none needed code changes, only real data.
    **Independently adversarially verified before merge** (own scripts, disposable read-only-sourced DB
    copies, not the implementer's own test harness): 0 incorrect writes found across ~5,300 independently
    audited real writes, two full samples, exhaustively checked; a targeted attack rebuilding the
    candidate index from the FULL unsampled `rpstl.db` found all 49 genuinely-ambiguous real keys
    correctly refused (0 written); idempotency confirmed via two full runs (0 drift) plus a deliberately
    hand-corrupted row correctly recomputed back to the right value on a third run — clarifying the real
    contract is "recompute and correct when a candidate exists," not "never touch a populated row." One
    non-blocking note: the write loop has no try/except, matching `extract_parts()`'s own existing
    precedent in the same file, not a new regression. **Still open**: 2 of the original 5 Gap Sweep dead
    columns (`parts.uoc`, `ref_nsn.data_date`); semantic search's full-corpus rebuild (NO-GO without a
    human go-ahead, per item 20); ~17 more orphaned routes; everything else from item 22's still-open
    list. See `CHANGELOG.md` `[1.38.0]`.
24. **`[1.39.0]` — CRITICAL: `build_index()` could stamp a mixed real/hash-fallback index as pure
    `sentence-transformers`.** Found during adversarial verification of item 21, before the
    full-corpus rebuild it gates was launched. `cur_backend = backend()` was snapshotted once, before
    the chunk loop, and stamped into `embeddings.meta.json` unconditionally at the end — but if a
    chunk's `model.encode()` call threw (bad input, transient OOM), the bare per-row
    `except Exception: hash-fallback` pattern silently substituted hash vectors for THAT CHUNK ONLY
    while the meta stamp still claimed a pure `sentence-transformers` index. **Confirmed
    pre-existing, not introduced by item 21** — the original unbatched `embed_text()` had the
    identical bare fallback and the old `build_index()` also stamped the backend after the fact with
    no per-row correlation; item 21's batching just enlarged one failure event's blast radius from 1
    row to up to `chunk_size` (5,000) rows. This is `[1.32.0]`'s failure mode again (real vectors
    compared against incompatible vectors → near-noise cosine scores silently trusted), now possible
    at row/chunk granularity inside an otherwise-valid build. **Fixed**: every chunk whose
    `model.encode()` call actually raised is tracked in `fallback_events`, persisted through
    `embeddings.progress.json` so the record survives an interrupt+resume exactly like every other
    piece of item 21's build state; if any remain once the shard merge succeeds,
    `embeddings.meta.json` is deliberately withheld (any stale one from a prior clean build is
    removed) — reusing `_index_is_stale()`'s existing no-meta-stamp-means-stale branch, zero new
    per-row staleness logic — and `embeddings.fallback.json` records exactly which rows are suspect.
    `BUILD-EMBEDDINGS.bat` now prints an explicit warning instead of a bare success line when this
    happens. Verified directly: a real `model.encode()` failure was injected mid-build (a stub model,
    not a mock of `build_index()` itself), confirming the meta stamp is withheld,
    `_index_is_stale()`/`search()` both refuse the index end-to-end, the on-disk array genuinely
    mixes real and hash vectors only in the affected rows, the record survives a genuine
    interrupt+resume, and a clean rebuild clears the stale fallback report. **No full-corpus rebuild
    was run** — this item is code + `engine/tests/test_embed_partial_fallback.py` (32 new checks)
    only. See `CHANGELOG.md` `[1.39.0]`.
25. **`[1.41.0]` — `part.html` no longer conflates a failed request with "part not found."** Found
    during a readiness audit's completeness pass. `gj()`, the shared fetch helper behind all 15 of
    `part.html`'s fetch call sites (the primary `/api/partsummary` card + 14 lazy-loaded panels),
    collapsed a real transport/server failure and a genuine "nothing here" result into the exact same
    falsy shape — the primary card showed a flat "Nothing found." on any network hiccup, and the two
    safety-relevant panels (cross-manual conflicts, one-time-use/TTY fasteners) failed completely
    silently, with no visible sign a check had even been attempted. **Fixed**: `gj()` now resolves
    `{ok,status,body}` — `ok` true only for a 2xx response whose body actually parsed as JSON — instead
    of a bare `null`-or-parsed-body; it still never rejects, so no call site's `.then()` shape changed.
    Every one of the 15 sites now branches on `res.ok` first, rendering a distinct `⚠ Couldn't load
    <thing> — try again.` on failure (a small `failCard()` helper reusing the `.alert.verd` amber style
    already defined in the file but never referenced before this). 7 panels (model, torque-sequence,
    serviceability, MAC, RPSTL, wiring, job-kit) had no honest-empty message at all before this pass
    and got one added at the same time, so failure and empty stayed distinguishable from both
    directions. The two safety-relevant panels get explicitly-worded `⚠ ... Do not treat this as
    "no conflicts."` / `"none flagged."` copy, matching the "do not treat this as..." pattern
    `dossier.html`'s own cautions/publog panels already established. **Two real bugs caught live while
    verifying, not shipped**: (1) the primary card's new empty-test initially included `s.title`, which
    `jobcards.py`'s `_jobpack_data()` always sets to the raw query string as a bare fallback
    (`pkg={"title":q,...}`) even when nothing matched — making the empty-test always true regardless of
    query, caught by hand-testing a real no-match query against the real corpus and dropped from the
    test before merge; (2) `#conflictcard` is shared by two lazy functions (`lazyValidate`,
    `lazyConflicts`) and one of them used to overwrite via `box.innerHTML=h`, which would silently wipe
    out whatever the other had already appended, including a new failure marker — both now exclusively
    append via `insertAdjacentHTML('beforeend', …)`, verified live that a validate-failure message and
    a real conflicts result render together without either erasing the other. **Verified live**, not
    just read: real server, real corpus (`index/viewer.db`, ~39,700 documents) — a real part (`POWER
    UNIT DIESEL`) renders unchanged; a genuinely no-match query now shows "Nothing found." (correctly,
    for the first time on the right basis); a forced fetch failure (both a true `fetch()` rejection and
    a real HTTP 404 from the live server) was injected at all 15 call sites in-browser and each showed
    its own distinct failure message, never the old empty-state text. **No real browser/JS test harness
    exists for any UI page in this repo** (confirmed, not assumed) — new coverage follows this repo's
    existing static-source-text-assertion convention (`test_uiux_fixes.py`, 22 new checks, 272/272
    total) instead of inventing a new test style out of scope. See `CHANGELOG.md` `[1.41.0]`.
26. **`[1.42.0]` — version-staleness detection: a stale running server is now visible, not silent.**
    Nothing anywhere recorded when the running process started, or whether the code it launched with
    still matched what was on disk — a server left running across a `git pull` (or any on-disk edit
    that never got a restart) answered every request fine while quietly running stale code, with no
    signal anywhere for an operator to notice. Fixed with `STARTUP_VERSION`/`STARTUP_TIME`
    (`engine/viewer_app.py`, next to `VERSION`) captured once at import and never changed for the life
    of the process, plus `current_disk_version()` — a plain `open()`+regex re-read of just the
    `VERSION = "..."` line, TTL-cached at 30s so polling costs at most one file read per window, never
    a re-import (`sys.modules`/the running feature-module DI graph untouched) and never `git` (this app
    is stdlib-only by design on fielded/legacy machines), fails open on any read error. New
    `started_with_version`/`started_at`/`code_changed_since_start` fields on `/healthz` and `/api/ops`
    (the existing `version` field is unchanged — still the in-memory version actually running; the new
    fields are what make it possible to notice it no longer matches disk). A non-dismissible banner
    self-injects from `shared.js` (`#vw-stalebanner`, the existing `_footerNav` self-injecting/
    id-guarded pattern) on every page, not just `/ops`, polling `/healthz` on load and every 5 minutes,
    deliberately carrying no dismiss control or `localStorage` suppression — a dismissible banner is
    exactly the "silent for weeks" failure this closes — clearing itself automatically once the process
    is actually restarted. `ops.html` gets a dedicated "Code freshness" stat card. New test
    `test_version_staleness.py`: real `ThreadingHTTPServer` + `viewer_app.Handler`, confirms no
    mismatch on a fresh process against its own on-disk file, safely rewrites the real on-disk
    `VERSION =` line (saved/restored in `try`/`finally` so a mid-test crash can't leave the repo file
    mutated) and confirms the mismatch **is** now reported on both endpoints, confirms a second,
    genuinely fresh subprocess started against that same now-changed file reports **no** mismatch (the
    detector tracks what a process actually started with, not a fixed constant), and confirms 20
    back-to-back `/healthz` calls stay fast (TTL cache, not a per-request file read). Verified:
    `verify_all.py --snapshot` clean except `test_routes.py`'s pre-existing `/api/ask` timeout,
    confirmed identical on unmodified `origin/main` via `git stash` before this work began, unrelated
    to this change. See `CHANGELOG.md` `[1.42.0]`.

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
