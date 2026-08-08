# THE VIEWER — Master Reconciliation (all chats, all versions → one record)

**Compiled 2026-08-08.** This document exists because the project's own canonical docs had drifted out of sync
with each other across sessions: `docs/CHANGELOG.md` and `docs/ITERATION-SNAPSHOTS.md` were current (**v1.13.2**),
`docs/HANDOFF-NOTE.md` was two point-releases behind (fixed today — see its own header), and
`docs/PROJECT-SUMMARY.md` was ~130 versions behind (still headed "v0.98.0"). This file is the reconciled,
single-source feature record, cross-checked against the actual files on disk (not just memory). It supplements —
does not replace — `CHANGELOG.md` (the full 215-entry per-change log) and `HANDOFF-NOTE.md` (the living session
hand-off). Treat all three as canonical going forward; keep them in sync.

**True current state: v1.13.2, shipped 2026-07-18.** Nothing has shipped between 2026-07-18 and today (2026-08-08)
— confirmed by CHANGELOG.md's newest entry.

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
(1.13.0) · zero-result **gap log** (`/api/searchgaps`, 1.13.0) surfacing what the corpus could not answer.

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
commonality** (`commonality.py`, 1.11.0).

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
shared signal on pinouts (`harnesstrace.py`, `/api/harnesstrace`, 1.12.6).

### R13 trust, verification & safety layer
`validate.py` — quarantines garbled/impossible extracted values, red banner on `/part` (1.8.0) → **woven into**
`/measures` (per-row quality) and `conflicts.detect` (garble dropped pre-grouping so it can't fabricate a safety
conflict, 1.13.0) · `trust.py` canonical trust level + trust badges on measures/ask/conflicts/publogdiff (1.13.0) ·
`/verify` verification cockpit (last VERIFY result, module roster, DB integrity, 1.8.0) · `signoff.py` — SME
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
· bulk folder ingestion (`ingestpipe.py` + `BULK-INGEST.bat`, 1.11.3) · cited multiple-choice **learn mode**
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
`docs/EXTRACTION-METHODS-CATALOG.md` track R12's march toward every method in the catalog being implemented.

### UI/UX, accessibility & onboarding
Kiosk mode (bigger text, ≥44px targets, 1.4.0) · deep-zoom + callout hotspots (0.99.3/0.99.8) · palette
aria-modal + focus trap, `role=dialog` modals, `esc()`/`toast()` dedup across all 29 pages, `alert()`→`toast()`
app-wide, shared footer nav injector (1.13.0) · offline QR deep-link from `/packet` to a part's dossier, LAN-scannable
(`qrgen.py`, 1.4.0) · Masterfile spec-sheet PDF + `/mastercov` least-covered-first coverage dashboard (1.4.0) ·
Tools "Diagnose & decode" menu group (1.13.0).

### Performance, RPS & stability
gzip+keep-alive (0.46) · fitz LRU + thread-local conns + NOCASE indexes + ETag/304 (0.56–0.58) · RPS legacy mode
w/ Poppler/Tesseract fallback + warmup (0.45/0.26) · parallel CAD batch, 2.9× measured (0.95) · GPU-tier OCR
(RapidOCR/onnxruntime, 8–12 workers) · preflight gate, disk guard, off-disk backup mirror, server/OCR watchdogs
(0.63) · custom mutation-testing harness (0.72.3) · **`corpus.py`** unified FTS retrieval used by every consumer,
pooled `doc_path()`, startup auto-optimizer (WAL + bg indexes), bounded worker pool, `safeguard.atomic_write`
everywhere (1.13.0 groundwork) · **persisted RPS run-mode** — Auto/Performance/Retroactive-Post-Support saved to
Settings, `/api/rps_mode` (1.13.2, the current latest).

### Dev / verify / ops tooling
Route smoke tests, static audits, end-to-end demo/test suite, the VERIFY-*.bat family · root **`VERIFY.bat`** —
now the single authoritative gate: exit-code truth, `run_timeout.py` wall-clock guards (no step can hang for
hours), unions audit + GET/POST route sweeps (**281 routes green**) + all regression suites + `rps_lint` +
`verify_ui` + `check_crlf` + module self-tests + no-truncation completeness (1.13.0, hang-proofed 1.12.7) ·
`engine/tools/check_crlf.py` — repo-wide CRLF gate for `.bat` files (83 verified, 1.13.0) · `safeguard.py backupdb`
— VACUUM INTO + disk guard + keep-2, manual (1.13.0).

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
| **v1.13.2 (current)** | RPS run-mode becomes a persisted Settings choice |

## 6 · Known outstanding items (host-side, still owed as of today)

1. **R10 literal screenshots have never actually been captured** — `docs/screenshots/` holds only a README of
   intended routes to capture. Every single changelog/snapshot entry since R10 was adopted says "pending
   host-side" because the app only runs on the user's machine, not in the build sandbox. This is the single most
   consistently-deferred action across every session. Needs either the Claude-in-Chrome extension connected while
   `RUN-VIEWER.bat` is running, or a manual computer-use screenshot per the route list in that README.
2. **`VERIFY.bat`** (the v1.13.0 unified gate) has not been confirmed green on the actual host yet for the
   v1.13.0–1.13.2 work.
3. **Re-baseline the pre-OCR `safeguard.py` snapshot** — the current baseline predates the OCR text layer.
4. **`BUILD-CONFLICTS.bat`** — first precomputed conflict-sweep run, optional while OCR is paused.
5. **OCR completion** — was ~43.8% at the v1.0.0 cut per `RELEASE-NOTES-1.0.md`; check current % via `/command` or
   `CAD-STATUS.bat`/OCR watchdog before assuming it's finished.
6. **`docs/PROJECT-SUMMARY.md` needs a full rewrite pass** — it's the designated "canonical hand-off for
   duplication" doc but its header and §4 feature table stop at v0.98.0 and never learned about v0.99.x through
   v1.13.2. This document (`MASTER-RECONCILIATION.md`) is the interim fix; a proper PROJECT-SUMMARY.md rewrite is
   still a good idea when there's a session to spend on it.

## 7 · Downloadable artifacts produced across the project's life

- **`docs/diagrams/`** — 185 dark-theme diagram PDFs (+ matching SVGs, several with PNG previews and `.mmd`
  sources), one pair per addition per R2/R3, numbered roughly 00→113+ plus named ones (`CHANGELOG-VISUAL.pdf`,
  `CHANGELOG-DUALTRACK.pdf`).
- **`docs/CHANGELOG.md`** (215 entries) / **`docs/CHANGELOG-LEGACY.md`** (139 entries, dual-track parity per R7).
- **`docs/ITERATION-SNAPSHOTS.md`** + **`docs/ITERATION-DASHBOARD.html`** — the tagged FEATURE/UPGRADE/POLISH/FIX
  index (213 iterations, 136 legacy-tracked), regenerable via `engine/build_iteration_snapshot.py`.
- **`docs/HANDOFF-NOTE.md`** — the living session hand-off (reconciled to v1.13.2 today).
- **`docs/ocr_example_before_after.pdf`** — OCR quality proof.
- **`docs/RELEASE-NOTES-1.0.md`** — the v1.0.0 release notes.
- This file, **`docs/MASTER-RECONCILIATION.md`**.
- Data deliverables (not "downloads" in the document sense, but produced artifacts): `index/viewer.db`,
  `index/publog.db`, `index/masterfile.db`, `index/cadcache/` (~32,622-part CAD render cache), `index/conflicts.db`.

<!-- END OF FILE -->
