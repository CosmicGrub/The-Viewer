# THE VIEWER — Complete Project Summary (duplication / hand-off kit)

**State: v1.14.0 · 2026-08-18** (rewritten 2026-08-08 from ~130 versions of drift, updated 2026-08-09, and
reconciled again 2026-08-18 after a 50-finding 4-tier audit + UX pass + CI + doc reconciliation — see the
reconciliation notes below). This document + `docs/PORTING.md` (the copy checklist — reconciled to v1.13.2 on
2026-08-08, now several point releases behind again; not touched in this update, see §9) + `docs/CHANGELOG.md`
(the full 219-entry version history) + `docs/MASTER-RECONCILIATION.md` (the cross-checked feature inventory this
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
  `side:` (1.13.0), zero-result gap log (1.13.0).
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
  scan `/binaudit` (1.6.0), exploded/assembly view, fleet shared-parts commonality (1.11.0).
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
  (`harnesstrace.py`, 1.12.6).
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
- **UI/UX, accessibility & onboarding** — kiosk mode, deep-zoom callouts, palette aria-modal + focus trap,
  `esc()`/`toast()` dedup app-wide, offline QR deep-link (base URL now resolved via a validated allowlist,
  `safe_public_base()`, instead of trusting the raw `Host` header, 1.14.0), Masterfile spec-sheet + `/mastercov`
  coverage dashboard, `index.html` ES5 capability-probe + minimal legacy fallback shell for RPS-Legacy/IE11/
  old-Firefox hardware (1.14.0).
- **Performance, RPS & stability** — gzip+keep-alive, fitz LRU + thread-local conns + ETag, RPS legacy fallback +
  warmup, parallel CAD batch, GPU-tier OCR, preflight/disk-guard/off-disk backup, `corpus.py` unification + pooled
  `doc_path()` + startup auto-optimizer + bounded worker pool (1.13.0 groundwork), persisted RPS run-mode (1.13.2),
  `ocr_supervisor.py` heartbeat-staleness watchdog + per-page OCR timeout (`VIEWER_OCR_PAGE_TIMEOUT`, force-kills
  and recovers a HUNG — not just crashed — OCR pass, 1.14.0).
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
  deleting-then-rebuilding in place.

## 5 · Code & data map

- `engine/viewer_app.py` — thin server shell. `engine/features/` — all domain logic (`registry`, `routes`,
  `corpus.py`, and the per-area feature modules). `engine/ui/*` — pages/widgets.
- Builders & batches: `make_cad.py` (parallel), `extract_figures.py`, `build_rpstl.py`, `build_xref.py`,
  `build_publog.py`, `build_conflicts.py`, `build_masterfile.py`, `classify_sides.py`, `bench_cad_parallel.py`.
- Diagnostics/verification: `diag_*.py`, `verifystate.py`, `cad_status.py`, `mutate.py`, `run_timeout.py`,
  `engine/tools/check_crlf.py`.
- Launchers: the root `*.bat` files (RUN-/MAKE-/BUILD-/VERIFY-/DIAG-/RE-RENDER-CAD/DEMO/RESTART-CLEAN…) plus
  root **`VERIFY.bat`** — the single authoritative gate.
- `index/` sidecars: see `PORTING.md` §1 for precious-vs-regenerable (largest: `viewer.db` ~3.65 GB+,
  `publog.db` ~9 GB — both git-ignored, host-generated only).
- `docs/`: `CHANGELOG.md` (219 entries) / `CHANGELOG-LEGACY.md` (143, dual-track parity per R7),
  `ITERATION-SNAPSHOTS.md` + `ITERATION-DASHBOARD.html`, `MASTER-RECONCILIATION.md`, `HANDOFF-NOTE.md`,
  `diagrams/` (185+ dark-theme PDF/SVG pairs), proof images, `LOCAL-MODELS.md`, `IMAGE3D-SETUP.md`, `PORTING.md`,
  this file.

## 6 · Dev workflow & conventions (how progress is made safely)

1. Build additively (new module + route + UI hook), keep R1 rollback notes in the changelog entry.
2. **Verify host-side** with root **`VERIFY.bat`** — the single authoritative gate since v1.13.0: exit-code truth
   per step, `run_timeout.py` wall-clock guards, unions the audit + GET/POST route sweeps (**265 routes**, 244
   GET + 21 POST — supersedes the older "281 routes" figure this section used to carry) + every
   regression suite + `rps_lint` + `verify_ui` + `check_crlf` + module self-tests + no-truncation completeness.
   `VERIFY-099.bat` forwards to it. Convention exists because dev-sandbox reads of freshly-grown files truncate
   (cached size) — **host files are always fine; never "fix" a file based on a truncated sandbox read.**
   `engine/tests/verify_all.py`'s own regression-suite gate is glob-based auto-discovery (23 `test_*.py` files,
   no hardcoded list) and is **26/26 ALL GREEN** — first fully clean run in the project's history, as of the
   v1.14.0 audit. **`.github/workflows/ci.yml`** (new in 1.14.0) runs `verify_all.py --snapshot` on every
   push/PR to `main` — this repo's first CI, complementing rather than replacing the host-side `VERIFY.bat` run.
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

**True current state: v1.14.0, shipped 2026-08-18 (`main` @ `3054dad`).** This is the largest single effort in
the project's history by commit count: a 12-commit, 50-finding 4-tier code audit — Critical (`08bbb81`→`086aed3`,
8 findings), High (`04bd4a5`→`48c7a63`, 12 findings), Medium (`0059dc8`→`3590cb2`, 19 of 24 findings), Low
(`aad1709`→`e4f4bd0`, 6 findings) — a follow-up priority-5 UI/UX pass (`71c9c4c`/`a32aee9`, 10 findings), this
repo's first-ever CI workflow plus a real bug it caught on day one (`7c4a3ba`), and a Tier-1 doc/dependency/
dead-code staleness pass (`3054dad`). Every tier was independently xhigh-effort multi-agent code-reviewed, with
every real review finding fixed in its own follow-up commit before moving to the next tier. See `CHANGELOG.md`'s
`[1.14.0]` entry for the complete, itemized list. Known outstanding items (host-side, still owed — full detail
in `MASTER-RECONCILIATION.md` §6):

1. **R10 literal screenshots have never actually been saved as artifacts** — `docs/screenshots/` still holds
   only a README of intended routes. Every fix across the v1.14.0 audit and UX pass was verified live against
   the real running app (screenshots viewed inline during the session), but none were saved to
   `docs/screenshots/`. Still the single most consistently-deferred action across every session.
2. **`BUILD-CONFLICTS.bat`** — first precomputed conflict-sweep run, still never run; `index/conflicts.db`
   doesn't exist yet. Optional while OCR is paused.
3. **`measures.py`'s bare-number-fused-to-single-letter-unit ambiguity** (e.g. an RPSTL item number "489A"
   reading as "489 Amps") — the same bug class fixed elsewhere (most recently the Medium-tier `xref.py`
   fake-NSN fix and the priority-5 UX pass's NIIN-fabrication fix in `/binaudit`), but broader; needs
   corpus-wide regression testing before a safe fix. Documented, not yet patched.
4. **`safeguard.py backupdb`** — the manual, standalone CLI invocation is still never actually run. As of
   1.14.0, `viewer_ingest.py migrate()` calls it automatically before applying any pending migration, so the
   snapshot-before-migration case is now covered; the general on-demand/manual backup path is not.
5. **OCR completion** — confirmed **94.4%** as of the v1.13.4 session (live `/status` check: 1,745,197 of
   1,848,465 pages searchable); not re-checked during the v1.14.0 audit, which was a code-quality/UX pass, not
   an ingestion run — check current % via `/command` or `/status` before assuming fully finished either way.
6. **Tiers 2–6 of the separate staleness Drift Report** (dependency-version-bound hardening, further doc
   reconciliation beyond this pass, and repo-bloat cleanup) — the Tier-1 pass above is only the first tier of
   that audit; the rest is tracked separately and not yet started.

Resolved since the last update (kept here for continuity, since these were open as of v1.13.4/v1.13.2):
`engine/tests/verify_all.py` is fully clean for the first time in the project's history (**26/26, ALL GREEN**;
its test-suite gate is now glob-based auto-discovery instead of a hardcoded, drifted allowlist) · this repo has
CI for the first time (`.github/workflows/ci.yml`, runs on every push/PR to `main`) · the deprecated `fitz`
import-alias warning is gone from every in-engine call site (22 sites migrated to `import pymupdf as fitz`; 7
launch-script probes deliberately left, since they already self-heal) · `kg.py`/`build_publog.py` rebuilds are
now crash-safe (build-to-temp-then-swap, matching the pattern each already partly had) · the QR job-packet
deep-link base URL now comes from a validated allowlist (`safe_public_base()`) instead of the raw `Host` header.

(`docs/PORTING.md`'s matching "v0.98.0" drift — previously listed here — was reconciled on 2026-08-08 to
v1.13.2, and is now several point releases behind again (still v1.13.2 vs. current v1.14.0); see its own
header, and §9 below.)

## 9 · How to duplicate

1. Follow **`docs/PORTING.md`** (copy list, deps, the E:\ path trap, the hardware_profile.json trap, the v1.13.2
   persisted-run-mode trap, first-run checklist) — reconciled to v1.13.2 alongside this file.
2. Give any new collaborator/AI session **this file + `MASTER-RECONCILIATION.md` + `HANDOFF-NOTE.md` + PORTING.md +
   the two changelogs** as context — together they carry the rules (R1–R13), the architecture, the verification
   conventions, and the full feature history.
3. Confirm the duplicate with root `VERIFY.bat` + the spot-checks in PORTING.md §6.

*This summary is the canonical hand-off, reconciled against `MASTER-RECONCILIATION.md` and `CHANGELOG.md`.
Per-feature depth lives in the changelog entries and their diagrams.*
