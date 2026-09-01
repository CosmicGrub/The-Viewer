# THE VIEWER — Complete Project Summary (duplication / hand-off kit)

**State: v1.47.0 · 2026-09-01** (rewritten 2026-08-08 from ~130 versions of drift, updated 2026-08-09,
reconciled 2026-08-18 after a 50-finding 4-tier audit + UX pass + CI + doc reconciliation, reconciled
again 2026-08-24 after a 30-commit Discovery Engine / in-app scanning / reachability-audit session,
reconciled again 2026-08-29 after 6 PRs (`[1.18.0]`–`[1.23.0]`) merged in sequence plus a route-count
re-audit (`[1.24.0]`), and reconciled eight more times the same day, 2026-08-30 — a critical real-host
fix (4 pending schema migrations were never applied to production, silently breaking measures/ask/
cautions/pmcs/oneuse, `[1.25.0]`); `conflicts.py`'s cross-vehicle false-positive fix, which itself needed
two implementation passes after adversarial review caught a safety regression in the first (`[1.26.0]`);
wiring that fix's new fields into `engine/ui/part.html` (`[1.27.0]`); then, following a production-
readiness/EMS-VIEWER-parity audit, three field-reliability quick wins — parts-request cart persistence,
`stepflow.html`'s voice step-nav wiring, and `PORTING.md`'s currency (`[1.28.0]`); then the Build
Roadmap's full "Now" tier — a missing-CSS-token bug worse than first scoped, a doubled fuzzy-search scan,
5 modals with no real focus trap, 3 unlabeled viewer images, 3 real WCAG contrast failures, and the 10
highest-traffic unlabeled controls (`[1.29.0]`); then the Roadmap's full "Next" tier — 5 previously-
orphaned modules wired into the UI, a related-parts card, OCR-confidence/conflict signals in search
results, symptom/"how do I" query routing, and `index.html` finally loading `/base.css` (`[1.30.0]`);
then a Gap Sweep audit's 5 priority items — RapidOCR installed, `/api/search_hybrid` made parameter-
complete and switched on as the primary search endpoint, one genuinely-fixable dead column filled, 3
more orphans wired (including a brand-new `/handover` page), and a real `"search"` analytics event
(`[1.31.0]`); then a same-day CRITICAL fix — installing sentence-transformers had silently made a
stale, pre-existing embeddings index look "fresh" to the new primary search endpoint, feeding
near-noise semantic scores into live search results; caught and fixed before reaching any real user
(`[1.32.0]`); then 2 more orphaned routes wired in — blank DA-2404/2407 print-on-demand forms, one click
away on `pmcs.html`/`jobcard.html` (`[1.33.0]`); then `embed.py`'s full-rebuild prep — the hardcoded
200,000-row cap made configurable, unbatched encoding replaced with real chunked batching (~1.3x measured),
and resumable checkpointing so a killed mid-run process loses at most one chunk, code + tests only, no
full-corpus rebuild run (`[1.36.0]`); then `[1.33.0]`'s one deliberately-open item closed — `/api/ingest_scan`
wired into `ingest.html` as a separate, honestly-captioned "Broader file scan" panel next to the existing
Preview button, not merged into it (`[1.37.0]`); then the `parts.cagec`/`smr` cross-database correlation
`[1.33.0]` had scoped but not started — 2 more of the 5 Gap Sweep dead columns now genuinely live,
verified against this repo's own real corpus at 48.0% yield, with a real production-breaking bug (an
`executemany()`-inside-an-open-SELECT-cursor "database is locked" crash) caught before it shipped
(`[1.38.0]`); then a same-day CRITICAL follow-up found during adversarial verification of `[1.36.0]`,
before the rebuild it gates was launched — a mid-build `model.encode()` failure on one chunk could
silently blend hash-fallback vectors into an index still stamped as pure `sentence-transformers`, the
`[1.32.0]` failure mode again at row/chunk granularity; fixed by tracking per-chunk fallback events and
withholding the meta stamp whenever any are present, code + tests only (`[1.39.0]`); then a readiness
audit's completeness pass on `part.html` — its shared `gj()` fetch helper collapsed a real transport/
server failure and a genuine "nothing here" result into the exact same falsy shape across all 15 of
its `fetch()` call sites, so a technician had no visible sign that a failed conflicts/one-time-use-
fastener check had happened at all, not merely found nothing; `gj()` now resolves an honest
`{ok,status,body}`, every site shows a distinct "couldn't load" vs. honest-empty message, and two real
bugs (an always-truthy `s.title` empty-test, and a shared-card overwrite race) were caught live while
verifying and fixed before shipping (`[1.41.0]`); then version-staleness detection — a server left
running across a `git pull` looked completely healthy while quietly running stale code, with nothing
recording when it started or whether its code still matched disk; fixed with `STARTUP_VERSION`/
`STARTUP_TIME` captured once at import, a TTL-cached on-disk `VERSION=` re-read (never a re-import,
never `git`), new fields on `/healthz`/`/api/ops`, and a non-dismissible whole-site banner in
`shared.js` that clears itself once the process is actually restarted (`[1.42.0]`); then TLS support
for LAN-exposed deployments — `VIEWER_ALLOWED_HOSTS`/`VIEWER_AUTH_TOKEN` hardened authentication over
plain HTTP, but a LAN-exposed VIEWER still crossed the network unencrypted; fixed with new
off-by-default `--tls`/`--cert`/`--key` flags wrapping the listening socket in stdlib `ssl` (TLS 1.2+,
zero change to `Handler` or the worker semaphore), a new one-time self-signed-cert CLI
(`engine/gen_cert.py`, gated behind an optional `cryptography` import — matching the
`sentence-transformers`/`rapidocr-onnxruntime` pattern rather than an `openssl` shell-out or a
vendored X.509 encoder), `safe_public_base()` now scheme-aware for `/api/qr`, and a real-handshake
test suite (`test_tls.py`) confirming both the TLS-on and TLS-off paths genuinely work (`[1.43.0]`);
then the first real backup **restore** drill — `backupdb()`'s `PRAGMA quick_check` had only ever
proven a backup file's internal consistency, never that the app layer could actually read it; a real
copy of `viewer-20260830-1348.db` was restored into an isolated `viewer_app.py` instance and queried
live, finding that `/api/search`/`/api/pmcs` silently return empty results against this specific
backup because its schema (`schema_version=8`) predates the `pages.ocr_confidence` column current app
code requires, while `/api/part_record`/`/api/part_by_number` were unaffected; the original backup and
`index/viewer.db` were confirmed byte-for-byte untouched throughout (`[1.44.0]`); then a
search-UI honesty fix — `/api/search_hybrid` silently collapsed "semantic index never built",
"stale", "actively rebuilding", and "healthy but zero matches" into the identical
`signals.semantic === 0`, now distinguished via a new `semantic_status` field and a quiet,
per-state-dismissible UI bar, verified live against a real running server during this session's own
in-progress embeddings rebuild (`[1.45.0]`); then accessibility
work extended beyond `index.html` — a research pass re-verified `[1.29.0]`'s own accessibility
disclosure and found a correction (`status.html`'s `.tag.ok` was carried as a 3.10:1 failure but
actually passes at 4.56:1 via this page's own token override, left untouched); 3 real WCAG contrast
failures fixed with the existing `--red-tx` token (`status.html` `.tag.bad` 4.18:1→5.65:1, `demo.html`
`.warn .n` 3.94:1→6.13:1 after removing that page's stale local token override, `index.html`'s 2
remaining inline stragglers 4.53:1→6.13:1); `schematics.html`/`threed.html`'s gate modals gained real
`role="dialog"`/`aria-modal`/focus traps, which required generalizing `shared.js`'s `trapFocus()`
itself since both gates toggle via CSS class rather than inline style; `verify_ui.py`'s WCAG guard
rewritten from a 3-pair hardcoded list to a real per-page scan across all 48 UI pages with
cascade-aware token resolution, catching 2 more previously-unknown real failures in the process; and
baseline ARIA landed on 10 more pages with the remaining zero-ARIA pages honestly named as still
open, matching `[1.29.0]`'s own disclosure convention (`[1.46.0]`); then an adversarial-verification
pass on that work found 3 real, confirmed, blocking issues and fixed all three — the WCAG scanner's
compound-selector regex that could never actually match a token like `.tag.bad`, so the "generalized"
guard's own headline claim was never true (fixed, adversarially re-verified by injection/revert, real
corrected state 146 pairs/117 OK/0 FAIL/29 SKIP); the zero-ARIA disclosure list's "27 vs. 30 names"
mismatch and `review.html`'s omission, corrected to the real 31-page list everywhere; and the false
"0 flakes / 61/61 GREEN" claim, corrected to the real, honestly-reported `verify_all.py --snapshot`
result (`[1.47.0]`) — see the reconciliation notes below and §8 items 25–30). This document +
`docs/PORTING.md` (the copy checklist — reconciled to v1.13.2 on
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
4. ~~**`safeguard.py backupdb`**~~ — **DONE, `[1.25.0]`:** run for real (3.64 GB `VACUUM INTO`, verified via
   `PRAGMA quick_check`, 147.5s) and the `THE_VIEWER_WeeklyDBBackup` scheduled task registered + test-fired
   via `schtasks /Run` — confirmed it actually executes end-to-end (produced a second real backup file), not
   just that the underlying function works standalone. `backups/db/` now holds real, verified copies.
5. ~~**OCR completion**~~ — **RE-CHECKED, `[1.25.0]`:** **94.62%** (1,749,089 of 1,848,465 pages), up
   slightly from 94.4% at v1.13.4. No OCR process currently running (confirmed via process inspection, not
   assumed — some `ocr_status='running'` rows are stale leftover state from a past interrupted run).
6. ~~**Tiers 2, 5, 6 of the separate staleness Drift Report**~~ — **CORRECTED, `[1.24.0]`:** `[1.23.0]`'s
   "only 2/5/6 remain genuinely unstarted" claim was itself wrong. Direct git-history check
   (`git log --all --grep="Drift Report\|Tier"`) shows the Viewer Drift Report staleness audit only ever
   had **4 tiers total, not 6** — Tier 1 (`3054dad`, deprecated imports/test isolation/misc drift), Tier 2
   (`132132f` — the [1.14.0] documentation-reconciliation commit itself, missed by `[1.23.0]`'s check same as
   Tiers 3/4 initially were), Tier 3 (`8f795bc`, dependency/CI hardening), Tier 4 (`1b3c6d8`, repo
   bloat/env vars/Windows CI) — whose own commit message states outright: "This closes out all 4 tiers of
   the Viewer Drift Report staleness audit run across this session." **All 4 tiers are complete; there is no
   Tier 5 or 6 and never was.** This is a DIFFERENT tracking thread from item 7 below and from the v1.14.0
   Medium-tier deferred findings — see `HANDOFF-NOTE.md`'s "Suggested next" for the full disambiguation.
7. **v1.15.0's own deliberately-deferred items:** `camelot_tables()` (3rd table-extraction engine pilot) stays
   unwired into `/api/tables_plus` — a documented cv2/opencv-python binary-collision risk on version skew;
   `dedup.py` cross-TM-family duplicates aren't caught by design (the TM-family blocking that makes the O(n²)
   pass tractable at real corpus scale — 39,683 docs — trades that away deliberately).
8. ~~**Route count (265, 244 GET + 21 POST) hasn't been recounted since v1.14.0**~~ — **DONE, `[1.24.0]`:**
   mechanically re-counted live against `engine/features/registry.py` — **276 routes (250 GET + 26 POST),
   zero collisions**, verified at the source level (135 `@get`/`@post`-decorator GET paths + 115 `static.py`
   programmatic GET paths = 250 exactly, no overlap between the two sources — not just trusting the final
   live-dict size, which can't tell a real registration from a silent same-path overwrite). New since
   v1.14.0: `/api/pageqa`/`/api/vlm`/`/api/layout`/`/api/editions`/`/api/symbols`/`/api/symbols_page_image`
   (GET) and `/api/airgap_export_decisions`/`/api/airgap_import_decisions`/`/api/analytics_log`/
   `/api/ingest_upload`/`/api/ocr_backlog_start`/`/api/symbols_template` (POST). See `CHANGELOG.md` `[1.24.0]`.
9. **Tier-2 "learned search re-ranker" — Phase 1 (click instrumentation + heuristic re-rank) shipped in
   `[1.20.0]`; the actual learned model is still open**, now that a real click-through log exists to train it
   on (see `CHANGELOG.md` `[1.20.0]` / `HANDOFF-NOTE.md` item 8).
10. **`[1.18.0]`–`[1.23.0]`, 6 PRs from the same session as this reconciliation, all now merged.** Beyond
    item 9 above: `[1.18.0]` measures.py unlabeled-bare-unit case stays genuinely open (needs real corpus
    data); `[1.19.0]` home-page nav regroup (nothing left open); `[1.21.0]` per-line OCR confidence capture
    (per-word stays open, GPU-gated); `[1.22.0]` multi-column reading-order reconstruction (3+ column layouts
    not specifically detected; the row-alignment threshold is tuned against synthetic fixtures only, worth
    real-corpus validation if mis-detections surface). `[1.23.0]` (this entry) is documentation-only.
11. ~~**Route count / Staleness Tiers 2,5,6**~~ — **DONE, `[1.24.0]`:** see items 8 and 6 above.
12. **`[1.25.0]` — critical fix: the real `viewer.db` was missing 4 schema migrations (0009–0012)**,
    silently breaking `measures`/`ask`/`cautions`/`pmcs`/`oneuse` since v1.13.5 (~3 weeks) — nothing else
    caught it because the test suite runs against a synthetic fixture DB with the correct schema. Fixed via
    `python viewer_ingest.py migrate` (auto-backs up first, applies atomically); confirmed live
    (`find_for_query('torque')`: 0 → 26 real cited results). ~~**New follow-up surfaced while fixing
    this**: `BUILD-CONFLICTS.bat`'s real first-ever sweep found data..., but its 1548-of-2000-subjects
    "conflict" rate is inflated by generic, corpus-wide subject phrases pooling unrelated values from
    different vehicles/manuals under one subject string~~ — **FIXED, `[1.26.0]`, see item 13 below.**
13. **`[1.26.0]` — fixed `conflicts.py`'s cross-vehicle false positives, in two passes** (Pass 1's own
    design was caught introducing a safety regression by adversarial review before it shipped, and
    reverted in favor of Pass 2 — see `CHANGELOG.md` `[1.26.0]` for the full story). Pass 2 restores
    byte-identical recall to the pre-bug code and annotates each conflict with `vehicle`/`vehicles`/
    `cross_vehicle` instead of filtering by it, so nothing is ever silently dropped. Re-swept for real
    against production: 1548 conflicts unchanged (confirms recall didn't regress), **5,071 now correctly
    marked `cross_vehicle: true`** (ambiguous, needs human confirmation) vs **1,466 marked
    `cross_vehicle: false`** (confirmed single-vehicle). ~~**Genuinely still open**: `engine/ui/part.html`
    does not yet read any of the new fields~~ — **DONE, `[1.27.0]`:** `lazyConflicts()` now shows each
    value's vehicle inline and a "⚠ Spans N different vehicle labels..." caveat on `cross_vehicle: true`
    conflicts; verified live against the real WINCH INSTALLATION example. Still genuinely open, lower
    priority: a pre-existing citation-completeness quirk (conflicts.py's citation
    list dedups by distinct value, not by doc, so a vehicle named in a conflict's `vehicles` list can
    have zero backing citation in `values`) and the underlying fact that `vehicle` is a raw ingest-folder
    name, not a curated identity, so `cross_vehicle: false` can still in principle mean "two different
    real vehicles filed under the same broad folder" (e.g. "WORK", ~65% of the corpus) — both disclosed
    in `conflicts.py`'s own docstring, neither fixed.
14. **`[1.28.0]` — 3 field-reliability quick wins from a production-readiness/EMS-VIEWER-parity audit**
    (the audit itself: a source-cited comparison against fielded military IETM viewers, published as a
    standalone dossier the same session). The parts-request cart (`engine/ui/index.html`) now persists
    to `localStorage` from every mutation path, restoring on load with a visible confirmation toast —
    previously the app's other core workflow had zero autosave while the procedure checklist and ingest
    job both already had it. `stepflow.html` — the page built for hands-free at-the-vehicle use — now
    actually triggers `readaloud.js`'s voice step-nav bar (additive `class="node step"`/`class="num n"`
    aliases; confirmed neither class has any CSS rule anywhere, so this changes zero styling). Both
    verified live in a real browser, not just read. `docs/PORTING.md` — the document a new site would
    use to stand itself up cold — updated from a 14-version-stale v1.13.2 to current, with an explicit
    new call-out of the real `[1.25.0]` schema-migration trap so a fresh copy doesn't walk into it blind.
15. **`[1.29.0]` — the Build Roadmap's full "Now" tier** (a second scoping audit, companion to `[1.28.0]`'s
    dossier, with real benchmarks + a real programmatic WCAG contrast audit run on this host). The home
    page's `--acc` CSS var wasn't just missing a fallback — confirmed live, `index.html`'s own `:root`
    duplicate never defined `--acc`/`--grn`/`--amb`/`--red`/`--teal`/`--pur` at all, so keyboard focus was
    silently invisible and the operator/mechanic side badges, "Saved" confirmations, and chapter-count
    status text were rendering in plain white instead of their intended colors — all restored, plus 3 real
    WCAG AA text-contrast failures the restoration exposed (2.98:1/3.36:1/4.02:1, all below the 4.5:1
    floor) fixed with new lightened text-only token siblings, locked in by a new automated guard in
    `engine/verify_ui.py`. A fuzzy-search vocabulary scan that ran 2-3x per query (same tokens, zero
    behavior difference) now runs once per token per request via a request-scoped cache. A shared
    `VW.trapFocus()` (modeled on `palette.js`'s own correct Tab-trap) is now wired into all 5 real modals
    — Tab-cycle containment, Escape-to-close, focus-restore, verified live. The 3 primary viewer images
    have `alt` text; the 10 highest-traffic controls (home + 8 tool search boxes + `collections.html`'s
    form) have `aria-label`s.
16. **`[1.30.0]` — the Build Roadmap's full "Next" tier**, grounded in 4 parallel research passes
    reading the real modules/routes/UI patterns before any code was written. The 5 orphaned modules
    (`commonality.py`/`tmrev.py`/`harnesstrace.py`+`pinouts.py`/`macchart.py`/`crossmethod.py`) are wired
    in on `part.html`/`procedure.html`; `commonality.py`'s placement was corrected from the roadmap's own
    suggestion after confirming live that `readiness.html` is vehicle-scoped while the module does an
    exact NSN/part lookup — a genuine shape mismatch. A "Related parts" card (`xref.py`) landed on both
    `part.html` and `dossier.html`. `ocr_confidence` now reaches search results (a one-column SELECT
    fix in `search_feature.py`) — though a real corpus check found this deployment has zero populated
    values today, disclosed rather than glossed over. Cross-manual-conflict flags and symptom/"how do
    I" query routing both shipped in a form measurement changed from the roadmap's own sketch:
    `conflicts.py`'s `check_query()` measured 200+ms and `/api/ask` measured 900-1855ms on common
    queries (both confirmed directly), too slow to bake into an automatic per-search fetch — both now
    fire independently/on-demand instead of blocking or auto-running. `index.html` finally loads
    `/base.css` (root cause of `[1.29.0]`'s token bug) via a real visual-diff pass, paired with a new
    `--line-ctl` interactive-control border token (`--line` itself measured 1.05-1.45:1, far under the
    3:1 UI floor). **Still open from the same roadmap** (Later tier, calendar/data-gated by design):
    semantic search is real but currently non-functional in production (no embedding model installed,
    stale index) and needs a decision — fix it for real or hide its UI entry point; the RRF hybrid-fusion
    route has zero UI callers (sequenced after the semantic-search fix); a real learned re-ranker is
    gated on click volume that doesn't exist yet (`index/analytics.jsonl` logs zero `search`/`click`
    events today); the other 35 of 45 UI pages still carry no ARIA of their own; no user accounts/RBAC,
    no TLS, no offsite backup automation, no accreditation artifacts exist for multi-site fielding. See
    the published Build Roadmap and Readiness Dossier artifacts, plus `CHANGELOG.md`
    `[1.28.0]`–`[1.30.0]`, for the complete, prioritized list.
17. **`[1.31.0]` — Gap Sweep: the 5 priority items**, from a 5-agent parallel research audit that
    directly answered "what's going on with OCR confidence, and what other gaps exist." RapidOCR
    installed and independently re-verified live — the confidence write path in `viewer_ingest.py` was
    already correct; this machine's OCR engine (Tesseract fallback, which captures no confidence at all)
    was the real gap. `/api/search_hybrid` — the item 16 above left open — is now the search box's
    primary endpoint, but only after a second research pass found the route was silently dropping
    side/match_any/fuzzy/mode/tm:/vehicle:/nsn: operators entirely; fixed first (`hybrid.hybrid_search()`
    + `r_search_hybrid` gained full parity with `/api/search`), then verified extensively (100%
    result-count parity across ~20 diverse queries, a genuine glossary-aware ranking improvement for
    acronym queries confirmed live) before switching. Of the 5 dead columns Gap Sweep found, only
    `ref_nsn.superseded` was genuinely trivial (its value was already parsed, just never bound to the
    column) — the other 4 need real cross-database integration or brand-new extraction logic, correctly
    left open. 3 more orphaned routes wired in: `rpstl.py` (part.html card), `partspdf.py` (jobcard.html
    button), and `handover.py` — a genuinely new page (`/handover`), since none of the 3 candidate
    existing pages fit its "shop-wide, since last shift" scope. A real `"search"` analytics event kind
    added — declared-valid since `analytics.py`'s `_VALID` set was first written, but never actually
    logged; `top_searches` had always been silently empty. **Still open**: 4 of the 5 dead columns; 19
    more orphaned routes the Sweep found beyond the 8 now wired (standouts: `/api/handover`-class
    features like `/api/chapter_jump`, the DA-2404/2407 forms, `/api/ingest_scan`); semantic search still
    non-functional (now the clear, sole remaining prerequisite for hybrid fusion's full value — the route
    itself is ready); everything else from item 16's still-open list. See the Gap Sweep artifact and
    `CHANGELOG.md` `[1.31.0]` for the complete, prioritized list.
18. **`[1.32.0]` — CRITICAL, same-day fix: a stale embeddings index was silently reclassified as
    fresh.** While researching semantic search's real feasibility (installing `sentence-transformers`
    as a genuine test, not a simulation), `embed.backend()` started returning `"sentence-transformers"`
    instead of `"hash-fallback"` — and `_index_is_stale()`'s no-meta-stamp check, which only ever
    compared the *current* backend against itself, silently flipped from stale to not-stale for the
    real, pre-existing, unstamped `index/embeddings.npy` (built under the old hash-bucket math, since
    sentence-transformers had never been installed here before). That index then started feeding
    through `/api/search_hybrid`'s RRF fusion — the primary search endpoint as of `[1.31.0]` — as
    near-noise cosine scores (0.18–0.19, confirmed live) blended into real search results as if they
    were a legitimate semantic signal. Fixed the same day, before reaching any real user:
    `_index_is_stale()` now requires a meta stamp proving an index was built by the backend that's
    *currently* active. Also fixed: `embed.py`'s own self-test had silently stopped exercising this
    exact check once a real model backend became available; two other tests
    (`test_routes.py`/`test_pageqa.py`) had the same "transformers/torch never installed" assumption
    baked in. **Lesson for future work**: installing any optional heavy dependency can change more
    than the one thing being tested — re-run the full suite and think through every `backend()`-style
    environment probe before trusting a "looks fine" result.
19. **`[1.33.0]` — 2 more orphaned routes wired**: `GET /api/form_2404`/`/api/form_2407` (blank DA-2404
    PMCS worksheet / DA-2407 maintenance-request worksheet) were real, tested routes with zero UI entry
    point — each now has an always-enabled print link on `pmcs.html`/`jobcard.html`, deliberately ungated
    since a blank form needs no prior search; both verified live via `curl` returning genuine single-page
    PDFs before shipping. `/api/chapter_jump` — one of the remaining candidates — was investigated and
    confirmed genuinely not worth wiring: `index.html`'s `openViewer()` already calls the richer
    `/api/chapters`, which `chapter_jump` is a strict subset of. `/api/ingest_scan` stays open on purpose,
    pending a product decision (its own supported-extension list undercounts what the real ingest job
    processes; a naive UI addition risks two disagreeing "how many new files" counts next to the existing
    Preview button). **Still open**: 4 of the 5 dead columns (`parts.cagec`/`smr` scoped this session as a
    real cross-database correlation design, ~1 focused day of implementation, not started); semantic
    search (the one-time model install is done and verified working end-to-end, but a true full-corpus
    rebuild is an explicit ~9–12 hour unattended commitment, NO-GO without a human go-ahead); ~17 more
    orphaned routes; everything else from item 18's still-open list. See `CHANGELOG.md` `[1.33.0]`.
20. **`[1.36.0]` — `embed.py` full-rebuild prep**: the one remaining prerequisite item 19 flagged —
    `build_index()`'s `limit=200000` was hardcoded, covering only ~11.9% of the real 1,682,054 eligible
    pages — now configurable via `VIEWER_EMBED_LIMIT` (byte-identical default behavior for the sole
    existing caller). Unbatched per-row `embed_text()` calls replaced with real chunked
    `model.encode(list, batch_size=...)` calls — measured ~40 pages/sec unbatched vs. ~53–54 pages/sec
    batched on this host (~1.3x, re-confirming item 19's own benchmark). Checkpointed/resumable: each
    completed chunk lands in shard files plus a progress marker keyed on the query's real `ORDER BY id`
    cursor, so a killed mid-run process resumes from its last completed chunk — verified directly via a
    real fault injected mid-loop, confirming the resumed run's final output is byte-identical to an
    uninterrupted run over the same sample. The `[1.32.0]` safety invariant (an incomplete build can
    never look "fresh") is preserved structurally: `embeddings.meta.json` is still written exactly once,
    after the shard merge succeeds, nowhere else — zero changes needed to `_index_is_stale()` itself.
    **No full-corpus rebuild was run** — stays a separate, human-supervised ~9–12 hour action per item
    19's own NO-GO finding; this item is code + `engine/tests/test_embed_checkpoint.py` (34 new checks)
    only. See `CHANGELOG.md` `[1.36.0]`.
21. **`[1.37.0]` — `/api/ingest_scan` wired into the UI**, closing item 19's one deliberately-open item.
    Shipped as a SEPARATE "Broader file scan" link/panel on `ingest.html` — its own `#broaderOut` div,
    never merged into the existing Preview panel — precisely to avoid the two-disagreeing-counts risk
    item 19 flagged. Copy states plainly what it adds over Preview (`.txt`/`.html`/`.htm`/`.xml`/`.csv`/
    `.md`/`.tiff`/`.tif`/`.png`/`.jpg`/`.jpeg` — the real `ingestpipe.SUPPORTED` set, **not**
    `.docx`/`.xlsx`/`.pptx`/`.rtf`/`.bmp`/`.gif`, which an earlier draft of the shipped copy briefly and
    incorrectly claimed until adversarial verification caught it before merge), what's still not covered
    (legacy `.doc`/`.xls`/`.ppt`, `.svg` — discovered, never content-extracted), that `.xml`/`.csv`/`.md`
    are only a partial win (counted here, but the real ingest job extracts zero content from them either
    way), and that this scan's dedup method (hash-or-filename) differs from Preview's (exact path only) —
    so a legitimate count mismatch is explained rather than left as a mystery. Traced whether the route
    needed the same `_exposed_read_guard()` gate its GET siblings carry — confirmed it does not
    (`do_POST` already requires the shared token for every POST when exposed) — and left that finding as
    a code comment so a future pass doesn't "fix" a non-bug. Verified live twice: at initial ship
    (`test_ingest_routes.py`'s real e2e coverage plus a direct `ingestpipe.scan_folder()` call), and again
    after the copy correction (a real server, a temp folder with one file per extension across both sets,
    a real POST — exactly the 12 real `SUPPORTED` extensions came back, all 6 misclaimed ones correctly
    absent). **Still open**: everything else from item 19's still-open list (4 of 5 dead columns, ~17 more
    orphaned routes, semantic search's full-corpus rebuild decision). See `CHANGELOG.md` `[1.37.0]`.
22. **`[1.38.0]` — `parts.cagec`/`parts.smr` cross-database correlation, the design item 19 scoped but
    deliberately didn't start.** `correlate_parts_cagec()` (`engine/viewer_ingest.py`) joins
    `index/rpstl.db`'s `parts_rows` sidecar into the main `parts` table on the confirmed-reliable
    `(document_id, page, nsn)` key, filtering every candidate CAGEC through `index/cage.json` (the real
    ~12k-entry CAGE registry) before writing anything — confirmed directly against this repo's own real
    `rpstl.db` that the filter is load-bearing: raw `CAGEC_RE` matches include real garbage (vehicle model
    numbers like `M35A3`, nomenclature words like `WINCH`/`SCREW`/`LIGHT`, RPSTL boilerplate like
    `WHERE`/`EXCEPT`) that happens to fit the "5 alphanumeric characters" shape. SMR is trusted only when
    that SAME candidate row's cagec passed validation; a key with more than one distinct valid cagec is
    genuinely ambiguous and is skipped, never guessed at. Wired as the new 8th/final ingest stage —
    deliberately full-corpus every single run, NOT scoped to `_TOUCHED_DOC_IDS` like the schematics/
    tables/rpstl stages beside it, since `extract_parts()` unconditionally rebuilds the entire `parts`
    table on every ingest run — plus a standalone `python viewer_ingest.py cagec [--db PATH]` backfill
    command for a corpus ingested before this feature existed. **A real, production-breaking bug was
    caught during verification, never shipped**: the first draft batched `UPDATE`s via `executemany()`
    INSIDE the same `SELECT` cursor loop it was reading from — invisible at small synthetic test scale,
    but reproduced immediately as `sqlite3.OperationalError: database is locked` against this repo's real
    227,908-row `parts` table (which has never been under the 1,000-row batch-flush threshold, so this
    would have crashed the new stage on every real ingest run past ship). Fixed by materializing the
    `SELECT` via `.fetchall()` before writing, the same convention `extract_parts()` itself already uses.
    **Real yield, measured against this repo's own corpus** (a random 4,000-row sample, not the full
    227,908 — see below for why): **48.0%**, matching the `[1.33.0]` scoping research's ~48.2%
    full-corpus estimate closely; every written cagec round-tripped as genuinely present in the real
    `cage.json`, and no known-garbage token ever reached a written column. New test file
    `engine/tests/test_cagec_smr_correlation.py` (38 checks): synthetic-fixture unit tests for the
    filtering/ambiguity/idempotence logic in full isolation, plus real-data checks that read (never
    write) this repo's actual `index/` DBs via a worktree-aware path resolver (the real, gitignored
    `index/` doesn't exist inside a `.claude/worktrees/<id>` checkout — only under the main repo root).
    The real-data run samples 4,000 of the real 227,908 `parts` rows rather than the full corpus: measured
    directly during this work that per-row `UPDATE` cost on this dev host is dominated by real-time
    antivirus scanning of SQLite's small writes (confirmed via `Get-MpComputerStatus`), making a
    full-corpus write pass take 15+ minutes of pure AV overhead — dwarfing the rest of
    `verify_all.py --snapshot`; the candidate-index side is still read in full regardless, only the write
    side is sampled. One caveat flagged, not fixed: `index/rpstl.db`'s mtime is ~7 weeks older than
    `index/viewer.db`'s on this deployment — worth a fresh `python build_rpstl.py` before trusting the
    first real backfill's yield as current rather than a July snapshot. Real, previously-inert downstream
    consumers now live: `figureparts.py`→`jobcard.py`'s printed "CAGE"/"SMR" lines on the mechanic-facing
    job-card PDF, `partlocate.py`, `parts_feature.py`'s look-alike-parts CAGEC/SMR discriminator, and
    `jobpack.py`'s JSON export — none needed code changes, only real data to select. **Independently
    adversarially verified before merge** (own scripts, disposable read-only-sourced DB copies, not the
    implementer's own test harness): 0 incorrect writes found across ~5,300 independently audited real
    writes (two full samples, exhaustively checked); a targeted attack rebuilding the candidate index
    from the FULL unsampled `rpstl.db` found all 49 genuinely-ambiguous real keys correctly refused (0
    written); idempotency confirmed via two full runs (0 drift) plus a deliberately hand-corrupted row
    correctly recomputed back to the right value on a third run. **Still open**: 2 of the original 5 Gap
    Sweep dead columns (`parts.uoc`, `ref_nsn.data_date`); semantic search's full-corpus rebuild (NO-GO
    without a human go-ahead, per item 19); ~17 more orphaned routes; everything else from item 19's
    still-open list. See `CHANGELOG.md` `[1.38.0]`.
23. **`[1.39.0]` — CRITICAL: `build_index()` could stamp a mixed real/hash-fallback index as pure
    `sentence-transformers`**: found during adversarial verification of item 20, before the rebuild it
    gates was launched. Confirmed pre-existing (not introduced by item 20) — `cur_backend` was always
    snapshotted once and stamped unconditionally; batching just raised the blast radius of one bad
    chunk from 1 row to up to `chunk_size` (5,000). Fixed by tracking which chunks' `model.encode()`
    calls actually raised (`fallback_events`, persisted through `embeddings.progress.json` so the
    record survives an interrupt+resume) and withholding `embeddings.meta.json` whenever any are
    present — reusing `_index_is_stale()`'s existing no-meta-stamp-means-stale branch rather than new
    per-row logic — with `embeddings.fallback.json` naming exactly which rows are suspect. Verified
    with a real injected mid-build encode() failure (not a mock): meta stamp withheld,
    staleness/`search()` both refuse the index end-to-end, the on-disk array genuinely mixes real and
    hash vectors only where expected, the record survives a genuine interrupt+resume, and a clean
    rebuild clears the stale fallback report. **No full-corpus rebuild was run** — code +
    `engine/tests/test_embed_partial_fallback.py` (32 new checks) only. See `CHANGELOG.md` `[1.39.0]`.
24. **`[1.41.0]` — `part.html` no longer conflates a failed request with "part not found"**: found
    during a readiness audit's completeness pass. `gj()`, the shared fetch helper backing all 15 of
    `part.html`'s fetch call sites (primary `/api/partsummary` card + 14 lazy panels), collapsed a real
    transport/server failure and a genuine empty result into the exact same falsy shape — the primary
    card showed "Nothing found." on any network hiccup, and the two safety-relevant panels
    (cross-manual conflicts, one-time-use/TTY fasteners) failed completely silently. Fixed by having
    `gj()` resolve `{ok,status,body}` (never rejects, so no call-site shape changed) and updating every
    site to branch on `res.ok` before its existing logic, each showing a distinct `⚠ Couldn't load
    <thing> — try again.` (7 panels that had no empty-state message at all also got one, so failure and
    empty stayed distinguishable from both directions); the two safety panels get explicitly-worded
    "do not treat this as..." copy matching `dossier.html`'s existing precedent. **Two real bugs caught
    live while verifying, not shipped**: the primary card's new empty-test initially included `s.title`,
    which the backend always sets to the raw query string as a bare fallback even on a genuine
    no-match, making the test always true until dropped; and `#conflictcard`'s two writer functions
    (validate, conflicts) — one used to overwrite via `box.innerHTML=h`, silently erasing whatever the
    other had appended, fixed to append-only for both. Verified live against the real corpus
    (`index/viewer.db`, ~39,700 documents): a real part renders unchanged, a genuine no-match query
    shows "Nothing found.", and a forced failure (`fetch()` rejection + real HTTP 404) was injected at
    all 15 call sites in-browser, each showing its own distinct failure message. No real browser/JS
    test harness exists for any UI page in this repo (confirmed) — new coverage follows the existing
    static-source-text-assertion convention instead. See `CHANGELOG.md` `[1.41.0]`.
25. **`[1.42.0]` — version-staleness detection: a stale running server is now visible, not silent**:
    nothing anywhere recorded when the process started or whether its code still matched disk, so a
    server left running across a `git pull` (or any on-disk edit that never got a restart) answered
    every request fine while quietly running stale code. Fixed by capturing `STARTUP_VERSION`/
    `STARTUP_TIME` once, at import (`engine/viewer_app.py`), and adding `current_disk_version()` — a
    TTL-cached (30s) plain `open()`+regex re-read of just the `VERSION =` line, never a re-import
    (`sys.modules`/the running DI graph are untouched) and never `git` (stdlib-only by design). New
    `started_with_version`/`started_at`/`code_changed_since_start` fields on `/healthz` and `/api/ops`
    (the existing `version` field is unchanged — still the in-memory version actually running). A
    non-dismissible banner self-injects from `shared.js` (`#vw-stalebanner`, the `_footerNav`
    self-injecting/id-guarded pattern) on every page, polling `/healthz` on load and every 5 minutes,
    with deliberately no dismiss/`localStorage` suppression — the exact "silent for weeks" failure mode
    this closes — clearing itself automatically once the process is actually restarted. `ops.html` gets
    a dedicated "Code freshness" stat card. New test `test_version_staleness.py`: real
    `ThreadingHTTPServer`, confirms no mismatch on a fresh process, safely rewrites the real on-disk
    `VERSION =` line (saved/restored in `try`/`finally`), confirms the mismatch **is** reported on both
    endpoints, confirms a second genuinely-fresh subprocess against that same changed file reports
    **no** mismatch, and confirms the TTL cache keeps 20 back-to-back `/healthz` calls fast. See
    `CHANGELOG.md` `[1.42.0]`.
26. **`[1.43.0]` — TLS support for LAN-exposed deployments**: `VIEWER_ALLOWED_HOSTS`/`VIEWER_AUTH_TOKEN`
    hardened authentication over plain HTTP, but a LAN-exposed VIEWER (`--host 0.0.0.0`) still crossed
    the network unencrypted — the shared token and all real TM/parts/NSN content readable to anyone
    else on the same segment. Fixed with new off-by-default `--tls`/`--cert`/`--key` flags
    (`engine/viewer_app.py`) wrapping the listening socket in stdlib `ssl.SSLContext` (TLS 1.2+) once
    at startup — zero change to `Handler` or the bounded-worker semaphore, byte-for-byte unchanged
    behavior when `--tls` isn't passed, fails fast (never binds, never falls back to plaintext) if
    `--tls` is passed with no cert/key resolvable. New one-time cert CLI `engine/gen_cert.py`
    (RSA-2048, 10-year self-signed, SAN auto-detects LAN IPs), gated behind an optional `cryptography`
    import — matching the `sentence-transformers`/`rapidocr-onnxruntime`/`pyzbar` pattern rather than
    an `openssl` shell-out (no guaranteed `openssl.exe` on this app's documented Win7/Vista floor) or a
    vendored X.509 encoder. `safe_public_base()` (feeds `/api/qr`) now scheme-aware. New test
    `test_tls.py`: a real cert, a real handshake (not mocked), confirms `https://` succeeds, plain
    `http://` on the same port is rejected, an untrusting client is rejected, and the plain-HTTP path
    is completely unaffected when `--tls` is never passed. New doc `docs/TLS-LAN-SETUP.md`. See
    `CHANGELOG.md` `[1.43.0]`.
27. **`[1.44.0]` — the first real backup restore drill, performed and documented**: `backupdb()`'s
    `PRAGMA quick_check` (`[1.25.0]`) only ever proved a backup file's own internal consistency, never
    that the app layer could actually read it. A real drill was performed: `backups\db\
    viewer-20260830-1348.db` (3.64 GB, SHA-256-verified) copied to an isolated scratch location, a
    genuinely separate `viewer_app.py` instance started against only that copy, real queries hit
    against `/healthz`/`/api/part_record`/`/api/part_by_number`/`/api/search`/`/api/pmcs`. **Found a
    real gap**: `/api/search`/`/api/pmcs` silently return `200` with empty results against this backup
    — its `pages` table predates the `ocr_confidence` column (`schema_version=8` vs. migrations
    through `12`) current app code unconditionally selects in those query paths, throwing and
    swallowing the error into an empty response with no signal anywhere. `part_record`/`part_by_number`
    unaffected. No code changed to work around it — left for a human decision (schema-version gate on
    restore, or run `fix_schema_version.py` against future backups first). Original backup and
    `index/viewer.db` confirmed byte-for-byte untouched (size/mtime/SHA-256) before and after. Full
    record: `docs/RESTORE-DRILL-LOG.md`. See `CHANGELOG.md` `[1.44.0]`.
28. **`[1.45.0]` — search UI now shows an honest signal when semantic search is degraded or
    rebuilding**: `hybrid.hybrid_search()` (behind `/api/search_hybrid`, the primary search endpoint)
    called `embed.search()` but discarded `ready`/`stale` entirely — the only trace of semantic-index
    health reaching the UI was `signals.semantic === 0`, identical whether the index was never built,
    stale, mid-rebuild, or the query simply had zero semantic matches, and nothing at query time could
    tell "never built" apart from "actively rebuilding". **Fixed**: new `embed.semantic_status()`
    reads `embeddings.progress.json` for a live percent-complete and returns one honest state
    (`ready`/`never_built`/`rebuilding`/`stale`); `hybrid_search()` forwards it as a new top-level
    `semantic_status` field. New `renderSemanticStatus()` in `engine/ui/index.html`, styled like the
    existing quiet `renderSearchHints()` card — not `shared.js`'s non-dismissible `_staleBanner()`,
    which stays reserved for the code-version-mismatch emergency — shown only when semantic search
    isn't `ready` and the search actually returned keyword results, dismissible per-state via
    `sessionStorage`. **Verified live against the real running app**: this session's own background
    embeddings rebuild (`embed_rebuild_v2.py`) put the real repo in a genuine `rebuilding` state
    throughout; `embed.semantic_status()` against the real `index/` dir and a real second
    `viewer_app.py` instance's live `/api/search_hybrid?q=brake` both returned matching
    `{"state": "rebuilding", "progress": {"percent": 25-26, ...}}`. `never_built`/`stale` verified the
    same way against isolated scratch index directories outside the repo. See `CHANGELOG.md` `[1.45.0]`.
29. **`[1.46.0]` — accessibility work extended beyond `index.html`: real contrast fixes, modal focus
    traps, a generalized contrast guard.** Re-verified `[1.29.0]`'s own accessibility disclosure and
    found a correction: `status.html`'s `.tag.ok` was carried as a 3.10:1 failure but actually passes
    at 4.56:1 via this page's own `--grn` token override, left untouched. `demo.html`'s full local
    `:root` token override (all 12 base.css tokens shadowed, plus `--grn2`, which base.css lacked) is
    gone — every value matched base.css exactly except `--red`, the direct cause of a real `.warn .n`
    contrast failure (3.94:1 → 6.13:1, fixed via the existing `--red-tx` token). Two more real
    failures fixed the same way: `status.html` `.tag.bad` (4.18:1 → 5.65:1) and `index.html`'s 2
    remaining inline `color:var(--red)` stragglers (4.53:1, a narrow existing pass, swapped anyway for
    consistency, now 6.13:1). `schematics.html`/`threed.html`'s gate modals now carry
    `role="dialog" aria-modal="true"` + `VW.trapFocus()`, which required generalizing `shared.js`'s
    `trapFocus()` itself — both gates toggle via `classList`, never inline `style`, which the original
    implementation only ever watched; verified live in a real browser, `index.html`'s 5 existing
    modals confirmed unaffected. `verify_ui.py`'s WCAG guard rewritten from a 3-pair hardcoded list
    (that only ever opened `base.css`/`index.html`) to a real per-page scan across all 48 UI pages with
    cascade-aware token resolution — exactly the gap that let `status.html`'s real failure ship
    invisibly to CI. The new scan caught 2 more previously-unknown real failures while being built
    (`index.html`'s `.sheetprev .e`, `measures.html`'s `.em .tagx`, both fixed) plus one bug in the
    scanner's own logic (caught and fixed before landing). Baseline ARIA landed on 10 pages —
    `collections`, `threed`, `status`, `schematics`, `verify`, `jobcard`, `part`, `visual`,
    `procedure`, `demo` — with the remaining zero-ARIA pages honestly named as still open in
    `CHANGELOG.md` `[1.46.0]`, matching `[1.29.0]`'s own disclosure convention rather than implying
    full coverage. See `CHANGELOG.md` `[1.46.0]`.
30. **`[1.47.0]` — adversarial verification of `[1.46.0]` found 3 real, confirmed, blocking issues;
    all fixed.** The WCAG contrast guard's compound-selector regex could never actually match a token
    like `.tag.bad`, so its own headline claim (closing the gap that let `status.html`'s real
    `.tag.bad` failure ship invisibly) was never true — confirmed by adversarial injection, fixed, and
    re-verified the same way (real corrected scan state: 146 pairs, 117 OK, 0 FAIL, 29 SKIP). The
    zero-ARIA disclosure list's "27 vs. 30 names" mismatch and `review.html`'s omission from every one
    of the 5 canonical docs, corrected to the real 31-page list everywhere. The "0 flakes / 61/61
    GREEN" claim was false — three re-runs this pass never reproduced it: the authoritative
    no-concurrent-edits run got 60/61 (`test_routes.py`'s pre-existing `/api/ask` timeout, reproduced
    standalone), another run flagged `test_http.py`'s equally pre-existing `/api/pageqa` timeout
    instead — corrected to report reality. See `CHANGELOG.md` `[1.47.0]`.

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
