# THE VIEWER — Complete Project Summary (duplication / hand-off kit)

**State: v1.70.0 · 2026-09-05** (rewritten 2026-08-08 from ~130 versions of drift, updated 2026-08-09,
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
result (`[1.47.0]`); then two more `transformers`/`torch`-never-installed env-assumption self-test
failures — the same bug class this session already fixed twice — found by `VERIFY.bat`'s per-module
self-test loop (a check `verify_all.py --snapshot` doesn't cover) in `engine/vlm.py` and
`engine/pageqa.py`, fixed the same way as `test_pageqa.py` (`[1.48.0]`); then a real hang bug found in
the project's own `tests/mutate.py` mutation-testing tool — a mutant-induced infinite loop survived its
own `--timeout` for 5+ hours on Windows because killing the intermediary shell process left the actual
hung test process running as an orphaned grandchild, fixed by killing the whole process tree on timeout
instead (`[1.49.0]`); then, found by the final release-cut `verify_all.py --snapshot` pass, a worse bug
in the same tool — restoring a mutated file's *text* left its *compiled bytecode cache* stale, so a
mutant's logic could silently outlive its own SHA-256-verified restore and leak into whatever imported
the module next, including the real application; fixed by purging the target's `__pycache__` entry after
every restore (`[1.50.0]`); then the first four implementation PRs of the multi-window/multi-tab
initiative — `VW.channel`, a real cross-window publish/subscribe layer in `shared.js` (`[1.51.0]`),
`VW.workspace`, the saved-set-of-pages data model riding it (`[1.52.0]`), `VW.windows`, the
one shared window-opening path with named reuse and an instant toast (`[1.53.0]`), A1, the home
nav's ↗ pop-out links — the first real UI consumer of any of it (`[1.55.0]`) — `VW.bench`, which
promotes the twice-duplicated "My Bench" accessor into `shared.js` and makes the pinned list
live-sync across tabs — the first change in that initiative a technician can actually see repaint on
its own (`[1.56.0]`) — a responsive breakpoint baseline for `base.css`, this app's first
width-based CSS rules, CSS only with no page yet checked against them (`[1.57.0]`, reserved as
`1.54.0` at authoring time then renumbered on merge) — then all four of the per-page verification
batches that baseline exists for. Batch 1: 13 pages resized in a real browser at 960px/720px against
the real corpus, turning up two genuine defects (`procedure.html`'s reference rail wrapping but
keeping its two-column width across a 35px band, and `measures.html`'s non-wrapping measurement rows
scrolling the page sideways from 490px down), both fixed page-locally with `base.css` untouched
(`[1.58.0]`). Batch 2: 12 more pages resized the same way, finding control labels splitting mid-word
in `index.html`'s in-app viewer and a card silently clipping a too-wide table on `handover.html`,
both also fixed page-locally (`[1.59.0]`). Batch 3: 11 pages
(`learn`/`binaudit`/`coverage`/`ingest`/`ops`/`status`/`verify`/`command`/`collections`/`review`/
`demo`), finding 3 more genuine defects — NSNs split mid-identifier on the look-alike audit table, a
NIIN variant split mid-string on the queue built to compare NSN strings, and the demo tour's tooltip
landing behind a control bar that is 119px tall at 720px rather than the 56px its code hard-coded —
and confirming the other 8 pages clean, `base.css` again untouched (`[1.60.0]`). Batch 4, the last:
the 12 specialized-visualization pages, fixing three more real defects, all in the pages' own inline
styles and none in `base.css` (`[1.61.0]`). Then, unrelated to the multi-window initiative — found
while reading `/api/coverage` output during that initiative's own responsive-verification batches —
a real `cad.pct` bug fixed at both layers: `coverage.html`'s three percent meters now clamp their
bar width to 0-100 while (per R13) keeping the numeric label honest above 100%, and
`coverage.py`/`make_cad.py`'s denominator/numerator mismatch that let `cad.pct` read `156.3%` in the
first place is fixed at the source, verified back to a clean `100.0%` (`[1.62.0]`). Then, back on the
multi-window plan, stage 4 PR 14 — **A2, per-page pop-out control**: a new `VW.popoutControl()` in
`shared.js` gives every adopting page (`part`/`procedure`/`torque`/`jobcard`/`bench`) its own real
`<button>` to pop *itself* out into a second window, using the byte-for-byte same window-naming
transform as A1's `popoutName()` so a page popped out from the home nav and the same page popped out
from its own new control land on one window, not two; the same action also registers as a Ctrl+K
palette entry through a new, order-independent `window.__paletteQueue` handoff `palette.js` drains at
two points, since `popoutControl()` cannot reach `palette.js`'s `COMMANDS` array directly on the
normal shared.js-then-page-script-then-palette.js load order (`[1.63.0]`). Then stage 5, PR 15 —
**B, curated workspace launcher**: "Launch Work Order" (`jobcard.html`) and "Launch Solve It"
(`solve.html`) each call `VW.workspace.create()` once, THEN `VW.windows.open()` per page, threading
the page's current `#q` value onto every launched URL at click time; a new `VW.popoutWindowName`
export reuses A1/A2's own window-naming transform byte-for-byte rather than a third copy, so a page
already open is reused, not duplicated; the design doc's `VW.capabilities.tier` guard is written
feature-detected against a capability that does not exist until Stage 6, a genuine no-op today; and a
real popup-blocker test found and reported an honest limitation — this session's own Browser-pane
preview tool cannot demonstrate true multi-window fan-out at all (confirmed with a code-independent
page), so that remains a manual, real-desktop-browser check (`[1.64.0]` — see the reconciliation notes
below and §8 items 25–46). Then, out of the plan doc's own stage order (it belongs right after PR 2
but was skipped over during this session's earlier parallel-dispatch of other PRs, and is inserted
now because PR 16/F, next in the queue, depends on it) — stage 2, PR 3, **`VW.workspace`
export/import**: `exportUrl(id)`/`exportFile(id)` hand a workspace's `{name, items}` (deliberately
never its id or timestamps) to a different technician's browser as a `"ws=<json>"` query string or a
downloadable `.json` `Blob`; `importUrl(qs)`/`importFile(blob)` share one parse-validate-create
helper that shape-validates BEFORE any write (reusing PR 2's own `_wsItems()` as the arbiter of a
well-formed item, rather than re-checking item shape a second time), throws/rejects with a specific
message on any mismatch, and always mints a brand-new id — never trusting one that might arrive in
the payload, even a deliberately spoofed one, proven directly rather than argued (`[1.65.0]` — see
§8 item 47). This document +
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
31. **`[1.48.0]` — two more `transformers`/`torch`-never-installed self-test failures, same bug class
    already fixed twice this session.** `VERIFY.bat`'s per-module self-test loop (~68 modules) — a check
    `verify_all.py --snapshot` never runs — surfaced `engine/vlm.py`'s and `engine/pageqa.py`'s own
    `__main__` self-tests hardcoding the assumption that `transformers`/`torch` are never installed.
    `vlm.py`'s self-test called `ask()`/`ground()` with no explicit backend, expecting `_load_backend()`
    to find nothing; once `vlm_backend.py`'s default Florence-2 backend became importable, `available`
    flipped from the expected `False` to `True`. `pageqa.py`'s failure was a subtler cascade:
    `pageqa.available()` is `vlm.available() and _gpu_tier()`, so once `vlm.available()` flipped, that
    gate silently passed on this real GPU-equipped machine and fell through to a real page-render
    attempt instead of the intended "no backend" short-circuit. Both fixed by forcing `VIEWER_VLM` to a
    genuinely-nonexistent module name before the "no backend" assertions — the identical fix already
    applied to `test_pageqa.py`. Verified: both self-tests pass cleanly post-fix; the full 68-module
    self-test loop is clean; `verify_all.py --snapshot` clean per the now-3 documented pre-existing
    flakes. See `CHANGELOG.md` `[1.48.0]`.
32. **`[1.49.0]` — `tests/mutate.py` could hang for hours past its own `--timeout`, on Windows.** Running
    `RUN-MUTATION.bat`'s 7-step sequence as direct commands (pre-release verification) hit a mutant in
    `procedure_feature.py` (`i += 1` → `i -= 1` in a blank-line-skip loop) that puts the parser into a
    genuine infinite loop — and `run_test()`'s `subprocess.run(cmd, shell=True, timeout=...)` only killed
    the intermediary `cmd.exe` on Windows timeout, leaving the actual hung test process running as an
    orphaned grandchild holding the stdout pipe open, so `communicate()` never saw EOF and the timeout
    never actually returned. Hung silently for 5+ hours before being caught. A second run (`rps.py`) was
    killed pre-emptively before repeating it. Fixed by killing the whole process tree on timeout
    (`taskkill /F /T` on Windows) instead of the single intermediary process. Verified: a deliberately
    hanging grandchild now times out in ~3s under a 3s cap; normal pass/fail exit codes unaffected; a
    full real run against `patterns.py` still restores source and passes SHA-256 verification. Both
    source files left mutated on disk by the hang were restored from their `.orig` backups first. See
    `CHANGELOG.md` `[1.49.0]`.
33. **`[1.50.0]` — `tests/mutate.py` could poison the real Python bytecode cache, silently, for days.**
    Found by the final, fresh `verify_all.py --snapshot` pass at the actual release-cut point:
    `test_patterns.py` failed 3 real-looking checks against `tm_side("TM 9-2320-280-10")` on a file `git
    diff` showed byte-identical to its committed source. Recompiling the function's own source text fresh
    gave the correct answer while the already-loaded module gave the wrong one — the discrepancy lived in
    compiled bytecode, not source. `mutate.py`'s restore step only ever rewrote and SHA-verified the
    target's *text*; it never touched the *derived `.pyc`* a subprocess `import` during a mutant's test
    window leaves in `__pycache__/`, keyed by mtime+size, and the rapid mutate/restore cycle can alias a
    mutant's cached bytecode onto the restored original — so the cache silently outlives the source it no
    longer matches, and every later importer (another test run, or the real application) inherits the
    mutant's logic invisibly. Undetected for two real days. Fixed: purge the target's cached `.pyc`/`.pyo`
    after every restore, both per-mutant (the one that matters — a hard-killed run, like `[1.49.0]`'s own
    incident, skips final cleanup entirely) and in the final cleanup. Verified: re-ran mutation testing
    against `patterns.py` with the fix, confirmed no `.pyc` survived and `tm_side()` was immediately
    correct with no manual intervention; every `__pycache__/` under `engine/` was purged as emergency
    remediation and every mutation-target test file re-run clean. A second, unrelated issue in the same
    pass: `test_ingest_routes.py`'s real e2e upload check exceeded its hardcoded 15s HTTP timeout because
    `_launch()`'s real, by-design synchronous `safeguard.snapshot()` cost (hundreds of tracked
    source/doc/diagram files by now) has grown past that budget — reproduced the underlying pipeline by
    hand (works correctly, ~1-2s once running) and widened just that check's timeout to 60s. See
    `CHANGELOG.md` `[1.50.0]`.
34. **`[1.51.0]` — `VW.channel`: cross-window/cross-tab publish/subscribe (multi-window support,
    PR 1/18).** First implementation PR of `docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md`.
    A real, reusable cross-window sync layer in `shared.js` — `BroadcastChannel` primary transport,
    automatic `storage`-event fallback for RPS/legacy browsers, per-(channel,tab) sequence numbers
    for gap detection (deliberately not a global cross-tab sequence — no single source of truth
    exists for that without real coordination overkill), schema versioning (a mismatched `v` is
    silently ignored, never crashes a subscriber on older/newer code), and an explicit size guard on
    the fallback path (`localStorage` shares one ~5-10MB origin quota; the guard throws a clear
    error before a raw `QuotaExceededError` or a partially-written shared key could surface
    downstream). Verified with a genuinely real test: `engine/tests/js/test_channel_node.js` uses two
    independent `vm.createContext()` sandboxes standing in for two browser tabs — each with its own
    window/document/localStorage (so requiring `shared.js` into each gives fully independent closure
    state), sharing Node's real global `BroadcastChannel` constructor — production code exercising a
    real `BroadcastChannel`, not a reimplementation of the logic under test. 16 checks: cross-tab
    delivery/ordering/no-self-echo, the storage-event fallback path (captured directly from whatever
    listener `shared.js` itself registers, since Node has no real cross-context storage-event IPC),
    gap detection on a simulated coalesced write, silent version-mismatch handling, the
    oversized-payload guard, malformed-JSON safety. Caught and fixed two `rps_lint` false positives
    along the way (backticks/ellipses in doc comments, which the linter's text scan doesn't
    distinguish from real code). No UI changes yet — nothing calls `VW.channel` outside its own
    tests. See `CHANGELOG.md` `[1.51.0]`.
35. **`[1.52.0]` — `VW.workspace`: saved, named sets of pages, CRUD (multi-window support,
    PR 2/18).** Stage 2 of the same plan, riding `[1.51.0]`'s `VW.channel`. A workspace is the data
    behind "reopen everything I had open for this job": `create/list/get/touch` over a record of
    `{id, name, items: [{page, params}], created, lastOpened, source}`. CRUD only — export/import
    (PR 3) and the built-in templates (PR 4) build on this exact record shape and storage key and
    are deliberately not here. Stored as one JSON **array** under a new `viewer_workspaces`
    localStorage key rather than an id-keyed object, a decision documented in the code itself:
    `list()` is by far the dominant read (the saved-workspaces UI repaints the whole set whenever
    anything changes) and an array preserves a stable creation order for free, where an id-keyed
    object would need a sort on every `list()` for the same guarantee; `get(id)`'s linear scan is
    the right trade for a handful of human-named entries; and an array is already the shape PR 3
    will serialize. Every mutation publishes on `VW.channel` with a deliberately thin
    `{action, id, name, at}` payload — `localStorage` is already shared across every tab on this
    origin for free, so a second tab does not need the data pushed to it, it needs to be *told*
    something changed so it can re-read and repaint (the same philosophy the design spec describes
    for D, Bench sync); the write happens first and the notification second, so a reacting tab
    always reads an already-committed value, and read-only calls publish nothing. Defensive
    throughout: wrapped storage access (private browsing and full quotas both throw), a corrupt
    stored value degrading to a filtered view instead of an exception, a read never rewriting
    storage, and ids checked against what is actually stored and regenerated on a hit so a
    duplicate is impossible rather than merely unlikely. Verified with a genuinely real test —
    `engine/tests/js/test_workspace_node.js`, 73 checks all passing — where two
    `vm.createContext()` sandboxes stand in for two tabs **sharing one `localStorage` object**,
    exactly what two tabs on one origin have: tab A creates, tab B is notified over Node's real
    global `BroadcastChannel`, and tab B then genuinely finds the workspace through its own
    `list()`. A controllable clock makes "touch moves `lastOpened`" a real observable change
    instead of a check that passes vacuously in the same millisecond, and every persisted-state
    check parses the raw storage value directly rather than trusting the API to describe itself.
    Adversarially checked by injecting 6 real mutations into `shared.js`: 5 caught; the 6th
    (dropping the id generator's random suffix) survives because the collision-regeneration guard
    independently preserves uniqueness — confirmed directly and reported as the equivalent mutant
    it is. No UI changes yet — nothing calls `VW.workspace` outside its own tests. See
    `CHANGELOG.md` `[1.52.0]`.
36. **`[1.53.0]` — `VW.windows`: one window-opening path, named reuse, instant toast (multi-window
    support, PR 5/18).** Stage 2 of the same plan, built on `[1.51.0]`'s `VW.channel`; layout
    capture/restore is explicitly PR 6, not this one. (`1.52.0` was reserved up front by the sibling
    stage-2 PR in item 35, `VW.workspace` CRUD, built in parallel off the same `main`; that
    sibling has since merged and this work was rebased onto it, the real `shared.js` conflict —
    both PRs add a block just above the `VW` export object — resolved by keeping both,
    `VW.workspace` then `VW.windows`, with both suites re-run green afterward.) `VW.windows.open(url, opts)` makes
    the *named* form of `window.open` the ergonomic default — passing the same name twice is how a
    browser natively reuses a window instead of stacking a fresh one up per click, and it is the
    thing every call site forgets, because nothing about writing `window.open(url)` suggests you
    were supposed to name anything. Three things are layered on top that a bare call site could not
    sensibly do for itself: an in-tab **registry** (`VW.windows.registry()` reports
    `[{name, url}, ...]`, the hook PR 6 extends with real `screenX`/`screenY`/`outerWidth`/
    `outerHeight` bounds); a **broadcast** of every successful open (`{event, name, url, count}`) on
    `VW.channel`'s `"windows"` channel, plumbing for a future cross-tab "N windows open" that
    nothing renders yet; and an instant **toast** on open *and* on refocus, reusing `shared.js`'s
    existing `toast()` — the design spec's priority 2 ("snappy UI"), aimed squarely at the reuse
    case, where on some window managers the reused window comes forward *behind* the current one and
    the click otherwise looks like it did nothing at all. Limits are documented in the code rather
    than left to be discovered: the registry is per tab and in memory (it lists what *this* tab
    opened during *this* page load — which is exactly why each open is broadcast, since a cross-tab
    view must be assembled from the messages, never read off one tab's registry), and it is a
    best-effort mirror of the browser's own named-window table rather than the truth (handles
    reporting `closed === true` are pruned on every read and before every reuse decision); an
    unnamed open cannot be tracked at all (an anonymous window can never be looked up again) so it
    opens and toasts but never enters the registry; no window-features argument is ever passed, since
    supplying one turns what the browser would open as an ordinary tab into a stripped chrome-less
    popup over the user's own preference; a blocked (`null`) or throwing `window.open` returns `null`
    and skips the toast, the registry write *and* the broadcast alike. **Verified with 48 real
    checks** in `engine/tests/js/test_windows_node.js`: the real `shared.js` loaded into a
    `vm.createContext()` sandbox with a **mocked `window.open`** that records every call (url, name,
    argument count) and returns a fake handle, asserting on what the production code actually did —
    same name twice produces ONE registry entry while still really calling `window.open` a second
    time (the browser does the reuse; skipping the call would leave the existing window sitting
    behind whatever is in front of it), different names produce separate entries, a new url on an
    existing name updates the tracked url, an unnamed open neither throws nor pollutes the registry
    but still toasts, the blocked and throwing paths return `null` with no toast/entry/broadcast, a
    closed window is pruned and re-opening that name is a fresh open rather than a reuse, and the
    returned registry is a copy that cannot be mutated back into the real one. The broadcast half is
    **not** mocked: a second independent sandbox subscribes over Node's real global
    `BroadcastChannel` and the full 6-event sequence is asserted end to end. The test was itself
    checked for vacuousness by deliberately breaking `shared.js` three times (registry keyed by
    `name + Math.random()` → 10 FAIL; `toast()` moved above the popup-blocked guard → 6 FAIL;
    `channelPublish` disabled → 2 FAIL) — the second of which caught a real weakness in an earlier
    draft of the test, which compared toast *text* and so missed a wrongly-repeated identical
    message; the fake DOM now logs every `textContent` **write** and the test counts writes.
    **Explicitly not proven and not provable here: that a real browser reuses a named window** —
    that is browser behavior, not this codebase's, and the mock agreeing with the code it was written
    to exercise proves nothing about Chrome or Firefox; a human opening a pop-out twice in a real
    browser is the only check for it, called out as manual in the PR in the same framing the design
    spec uses for every other real-hardware-only behavior. `rps_lint` caught one ES5 false positive
    on the way through (the plain-English word "let" followed by a space, inside a new doc comment —
    the same class `[1.51.0]` hit twice), reworded rather than suppressed. No UI changes — nothing
    calls `VW.windows` outside its own tests; A1 (PR 12), A2 (PR 14) and B (PR 15) are the first real
    consumers. See `CHANGELOG.md` `[1.53.0]`.
37. **`[1.55.0]` — A1: home nav pop-out links (multi-window support, PR 12/25).** Stage 4 of the
    same plan, and the **first real UI consumer** of item 36's `VW.windows` — which until now had
    nothing calling it outside its own tests. (`1.54.0` and `1.56.0` are claimed by sibling PRs built
    in parallel off the same `main`, so this branch reserved `1.55.0` up front rather than race for a
    number.) Each of the 30 entries in `index.html`'s Tools nav is now a `.mrow` carrying its
    **original `<a>`, byte-for-byte unchanged** — same href, title and label, still navigating in
    place on a normal click and still ctrl/middle-clickable into a tab exactly as before — plus an
    adjacent ↗ `<button>` that opens that same section in its own reusable window through
    `VW.windows.open(url, {name})`. The ↗ is an *additional, explicit* affordance beside the link,
    never a replacement for it: the design spec's whole framing is that this app has always been able
    to open things in new tabs, and what is missing is **discoverability**, not capability. Each
    pop-out is a real `<button type="button">` — in the tab order by default, picking up `base.css`'s
    shared `:focus-visible` outline — carrying its own `aria-label` naming its own destination
    ("Open Torque quick-ref in a new window"), not a bare glyph; confirmed live in a real browser
    (all 30 report `tabIndex 0`, each exposed by full name in the accessibility tree), because an
    unlabeled icon-only control is exactly what the `[1.46.0]`/`[1.47.0]` accessibility passes went
    through this app to remove. **Two load-bearing decisions:** the url is read off the sibling link
    *at click time* rather than baked into the button, so the menu's existing `threadQuery()` (which
    rewrites every href on every open so the mechanic's current search carries into the tool being
    opened) is not silently defeated — the pop-out inherits the query for free; and the window name
    is derived from the base path with the query stripped (`/torque?q=bolt` → `vw-torque`), because
    the name is the *entire* mechanism by which `VW.windows.open` reuses a window instead of stacking
    a new one up per click, so it has to be identical across clicks while the href is not. Deriving
    it in one small function rather than hand-writing 30 `data-` attributes makes a copy-paste
    collision (two rows sharing a name, one silently stealing the other's window) impossible rather
    than merely unlikely, and it is keyed to the **destination page** rather than to this menu on
    purpose, so A2's `popoutControl()` (PR 14) can name its window the same way and land on the same
    window. One existing behavior deliberately changed: the Tools popup's "any button in here closes
    the menu" rule (written for `#pnReviewBtn`) now exempts `.popout`, since popping several sections
    out in a row is the whole point of multi-window support and closing after each one would force a
    re-open per pop-out and discard the keyboard focus just placed; `#pnReviewBtn` still closes it,
    and deliberately gets no pop-out of its own, being a modal opener rather than a link.
    **Deliberately untouched:** the three top-level header pills (Collections / My Bench / Help — a
    `flex` row that already wraps at narrow widths, and all three still ctrl/middle-clickable), and
    the `#legacyHome` ES5 fallback's own link list, since the spec's capability ladder puts the
    legacy tier at "no advanced capability affordances shown in the UI at all"; the gate protecting
    that fallback (`check_es5_fallback.py`) is asserted still green by the new test, so this change
    cannot have leaked into it. `index.html` is `MODERN_BY_DESIGN` in `rps_lint.py` — confirmed by
    reading that gate's own output before any JS was written, not assumed — but the wiring is ES5
    `var`/`function` regardless, because it lives in the same IIFE as the Tools-menu toggle, which
    *is* ES5 and does run on legacy hardware, and a control that renders there and then does nothing
    would be worse than not shipping it there. **Verified with 36 checks** in the new
    `engine/tests/test_home_nav_popout.py`, all against the real shipped markup: every nav link in a
    row beside exactly one pop-out, and no link missed (proved by stripping the rows and confirming
    nothing is left behind); every pop-out a real focusable `<button>` with a non-empty `aria-label`
    naming its *own* row; every href still a real, currently-registered route (cross-checked against
    `features/routes/*.py`, the same technique `test_uiux_fixes.py` already uses); window names
    unique per row and unchanged by any appended `?q=…`; the wiring really calling `VW.windows.open`
    with a name; `/shared.js` really loaded and really loading first; `#pnReviewBtn` with no pop-out;
    `node --check` clean on the inline scripts; the ES5 fallback span still present and clean.
    Checked for vacuousness with **7 injected mutations**, every one caught — and that run **found a
    real bug in the test itself**, not the feature: its mismatch diagnostic crashed with
    `UnicodeEncodeError` on a cp1252 Windows console (the nav labels are emoji-heavy), converting a
    clean FAIL into a swallowed exception *and* skipping every assertion after it; fixed with an
    ASCII-safe helper matching `check_onboarding_menu.py`'s stated convention, and re-run to confirm
    3 clean FAILs with a readable diagnostic. **What is live-verified vs. still manual:** the real
    server was started and the real page driven — the menu renders correctly, and at a 375px viewport
    with a coarse pointer each pop-out measures exactly 44×44 through the existing
    `@media (pointer:coarse)` rule, with no row overflow and no horizontal page overflow. **Not**
    provable there, and stated as manual rather than implied automated: that clicking ↗ opens a real
    separate window and that a second click *refocuses* it instead of opening a third. The embedded
    preview browser refuses popups outright (`window.open()` returned `null` and navigated the
    current tab in place), so reuse is genuinely unobservable in it — though that did usefully
    exercise `VW.windows`'s documented blocked-popup path for real, returning `null` and correctly
    skipping the toast, the registry write and the broadcast with no error. The owed manual check is
    the same real-browser-only one `[1.53.0]` recorded for the layer underneath, unchanged and still
    open. No `shared.js` change: this PR only *calls* the already-merged `VW.windows.open` and needed
    nothing new exported. **One real, previously-undocumented test-infrastructure hazard was found
    and run to ground on the way through:** a later confirmatory `verify_all.py --snapshot` failed
    hard on `test_ingest_routes.py`, reproduced deterministically, and proved to be a **cross-process
    port collision** — that suite uses a fixed port (8894) and `ThreadingHTTPServer`'s stdlib default
    `allow_reuse_address = 1`, so on Windows a second bind of a port another process already holds
    succeeds *silently* and the requests are answered by the first listener (sibling agents running
    the same suite concurrently, confirmed by `netstat`; mechanism reproduced in isolation). A copy
    of the suite differing only by `PORT = 8897` ran `175 passed, 0 failed` on this exact tree.
    Pre-existing, unrelated to A1, deliberately left alone rather than fixed in an unrelated PR, and
    written down rather than left as folklore. See `CHANGELOG.md` `[1.55.0]`.
38. **`[1.56.0]` — `VW.bench`: My Bench promoted into `shared.js` and live-synced across tabs
    (multi-window support, PR 13/25, feature D).** Stage 4 of the same plan. Items 34/35/36 built
    plumbing nothing rendered; item 37 (A1) was the first real UI consumer of `[1.53.0]`'s
    `VW.windows`, and D is the first real UI consumer of `[1.51.0]`'s `VW.channel` — the first change
    in this initiative where a technician sees one window's edit repaint another's, live.
    (`1.54.0` is reserved by a sibling responsive-baseline PR built in parallel off the same `main`,
    not yet merged.) The same
    two-line bench read/write pair had been written out twice, independently: inline in `bench.html`,
    the page that renders the list, and again in `palette.js`, the ☆ pin pill on every page — both
    parsing the same `viewer_bench` key, both re-applying the same 100-entry cap, neither knowing the
    other existed. Promoted to **`VW.bench.get()`/`VW.bench.put(list)`** with the stored record shape
    and the cap carried over unchanged. `get()` now returns an array unconditionally — a stored JSON
    *object* used to make `palette.js`'s pin fail silently, since its pin path called `.filter` on
    whatever came back, **a real live bug rather than a hypothetical** — with non-object entries
    dropped from the returned view only and a read never rewriting storage, so a corrupt value stays
    inspectable in devtools. `put()` now returns a real `true`/`false`, for the same reason
    `VW.workspace.create()` reports a refused write: a caller that cannot tell a stored bench from an
    unstored one can only ever lie to the user. Every write publishes a deliberately thin
    `{action, count, at}` on `VW.channel` — storage is already shared across tabs on this origin for
    free, so the message is only "re-read and repaint", never a second copy of the truth; the write
    happens first and the notification second; reads publish nothing. **Conflicts are last-write-wins
    with no merge**, per the design spec and unchanged since scoping. `bench.html`'s local copy is
    **deleted**, not kept as a fallback; it subscribes to the `"bench"` channel to re-render, matches
    a removal by the row's `url` rather than by the index it was painted at (another window can now
    change the list between paint and click), and raises a short toast on a cross-tab repaint,
    because a row appearing on its own otherwise reads as a glitch. `palette.js` routes through
    `VW.bench` too — that is what makes D real rather than scope creep, since the pin pill performs
    nearly every actual bench write in the app — keeping its direct `localStorage` path only for
    `circuitlab.html` and `scan.html`, the two pages that load it without `shared.js` and would
    otherwise lose pinning entirely. Verified with **77 real checks** across two `vm.createContext()`
    sandboxes sharing one `localStorage` object with a real `BroadcastChannel` between them, plus the
    storage-event fallback transport; **adversarially checked with 7 injected mutations, all 7
    caught**, two of which improved the test rather than confirming it (a dropped publish originally
    crashed the run instead of reporting failures; the non-array guard originally survived until an
    array-*like* stored object was added as the one fixture only that guard rejects). A third
    mutation attempt was itself wrong and is recorded rather than dropped: it silently hit
    `_wsRead`'s byte-identical line higher up the file and "survived" for that reason alone. **Owed
    manual check, stated rather than implied:** two real browser windows — pin in one, confirm the
    row appears in the other with no reload, then remove a row and confirm the first repaints. Two
    `verify_all` failures were chased rather than re-run until green: `safeguard verify`'s was
    self-inflicted (a line-ending normalization ran after that pass's own snapshot, converting two
    files from CRLF to LF — byte deltas matching their line counts exactly, and `git diff` never
    moved, since `core.autocrlf=true` normalizes both to the same committed content), and
    `test_ingest_routes.py`'s is a pre-existing concurrency flake now understood rather than guessed
    at — 20/20 standalone including on genuinely pristine pre-`1.56.0` code, then reproduced
    deliberately at 6/6 by running two instances at once, because that file binds a machine-wide
    fixed port (8894) and mutates process-global state. See `CHANGELOG.md` `[1.56.0]`.

39. **`[1.57.0]` — responsive baseline: the app's first shared width breakpoints in `base.css`
    (multi-window support, PR 7/25).** Stage 3 of the same plan — the design spec's priority 3, "a
    real, verified responsive baseline." **CSS only, and only the shared rules**: no
    `engine/ui/*.html` file is touched and no real page has been checked in a resized window yet;
    that is PRs 8-11, batched by the home nav's own 6 section groupings. (`1.54.0` was reserved up
    front when this branch was built in parallel with two sibling PRs that went on to claim
    `1.55.0`/`1.56.0` (items 37/38); both merged first while this PR was still under review, so on
    merge it takes the next free number instead.) The spec's claim
    was checked rather than trusted: before this change `base.css` held exactly three media queries
    and not one was width-based (`pointer:coarse`, `print`, `prefers-reduced-motion`), so the one
    sheet all 48 pages link contributed literally nothing to a narrow window, while eight pages had
    grown their own ad-hoc breakpoints at seven different numbers (1280/920/820/780/760/720/620) and
    the other forty had none. Two anchors, neither invented: **960px** is exactly half a 1080p
    monitor — the scenario `[1.53.0]`'s `VW.windows` makes ordinary rather than hypothetical — and
    **720px** is the number four of this app's own pages already picked for themselves. Seven rules:
    a self-limiting `#vw-toast{max-width:calc(100vw - 24px)}` outside any breakpoint (`[1.53.0]`
    made toasts routine and the longest of them is wider than a narrow pop-out); at ≤960px,
    `flex-wrap:wrap` on the row-shaped classes (**not a new convention — the app's own, finished**:
    `.search` already declares it in 18 of 18 flex definitions, `.toolbar` 2/2, `.chips` 2/2,
    `.cols` 1/1, `.tools` 1/1, `.row` 7/8, `.bar` 8/14, `header` 5/9, `.tabs` 0/1), `min-width:0` on
    layout-container children (generalising the lesson `index.html` already learned locally twice —
    its `minmax(0,1fr)` comment and its own `.vside{min-width:0}`), `body{overflow-wrap:break-word}`
    so an unbreakable NSN/CAGE/part number wraps instead of scrolling the page sideways,
    `max-width:100%` on `img`/`video`/`iframe`, and a collapse of `.grid2` (this app's only class
    actually *named* for being a two-column split); at ≤720px, `.side` stacks full-width. **The
    thing that would have made the whole PR inert:** `base.css` is linked *before* every page's
    inline `<style>` and a media query adds no specificity, so a plain `.grid2{...}` here loses to
    `part.html`'s later equal-specificity rule — every rule therefore picks its weight deliberately
    (`:where()` at specificity 0 for safety nets any page must be free to override, a bare selector
    where no page declares that property at all, `body .x` only where it genuinely must win).
    Deliberately **not** done: collapsing `.grid`, which means an explicit `1fr 1fr` split on 5 pages
    (all of which already collapse themselves at 720-820px) *and* an `auto-fill` card grid on 6
    others that already reflows — a blanket rule fixes nothing on the first and turns the second into
    a column of 900px-wide cards. Verified with no CSS linter available: brace/comment audit
    (`{`57 = `}`57, depth never negative, `/*`31 = `*/`31); a real browser made to parse the whole
    file and read back `cssRules` (43 top-level rules, all five media rules intact with every inner
    rule — `(max-width: 960px)`:5, `(max-width: 720px)`:1, nothing silently dropped, `:where()`
    included); and a cascade harness reproducing the real load order, served over HTTP and measured
    with `getComputedStyle` at 1200/960/720/400px — proving at 1200px every value is byte-identical
    to before the change (inert above the breakpoint, R1), at 960px that the `:where()` choice really
    does let `procedure.html` keep its intentional `.steps{min-width:340px}` and the `auto-fill`
    `.grid` keep 3 columns, and at 400px that `scrollWidth` equals `clientWidth` (400 = 400) where
    the same page with `base.css` disabled overflows to 534. **Not proven:** anything about how the
    44 other real pages actually look at 960px — only a human resizing each does that, which is
    PRs 8-11. See `CHANGELOG.md` `[1.57.0]`.
40. **`[1.58.0]` — responsive verification batch 1: 13 pages resized in a real browser, 2 real
    defects found and fixed (multi-window support, PR 8/25).** Stage 3, the first of the four
    per-page passes item 39 deliberately left undone. Covers `part` · `procedure` · `torque` ·
    `jobcard` · `bench` · `dossier` · `partdiff` · `locate` · `decode` · `fastener` · `pmcs` ·
    `measures` · `readiness`; the first five land here because **PR 14 (A2, the per-page pop-out
    control) is blocked on exactly those**. Three sibling batches are in flight in parallel holding
    `1.59.0`/`1.60.0`/`1.61.0`, so this took the lowest free number rather than racing for one, and
    **`engine/ui/base.css` is not touched** — neither defect was a shared-layer problem, and a
    shared-file edit is precisely what would collide with those three. Method, because "verified" is
    the word most likely to be doing no work in a pass like this: the real server against the real
    227,908-row corpus, each page loaded with a query that actually returns data (`alternator` /
    NSN `3040-01-521-7377` / `brake` / `5 TON` / `5310-01-359-2198`) rather than an empty shell, then
    measured at 960px and 720px and swept to 360px with a probe walking every non-fixed element in
    `body` for a right edge past the viewport and for internal `scrollWidth > clientWidth`;
    `readiness`'s fluids/intervals and `measures`'s external references return nothing on this
    machine, so those two were exercised with stubbed responses of the documented shape rather than
    counted as passing on a blank page. **Fixed (1):** `procedure.html`'s `.side` rail —
    **756px is the last side-by-side width** (348/348); at **755px** the `.cols` row wraps, which
    makes the page taller, which brings in a 15px scrollbar, which drops the usable width to 740px
    and holds it wrapped (a stable, reproducible equilibrium, not a flicker) — and the rail then
    keeps its declared `420px`/`46vw`, landing **332-347px wide inside a 677-696px row**, so the
    scanned page a technician checks the steps against renders at under half the width sitting empty
    beside it. That held 755→721px, where `base.css`'s shared 720px rule took over. Closed with one
    page-local `@media(max-width:755px){ .side{width:100%;max-width:none} }`; after, 756px is
    unchanged and 755-721px gives a **677-711px** rail. **Item 39 predicted this band at ~20px; it
    is 35px** — that estimate came from the layout arithmetic alone and missed the scrollbar the
    wrap itself brings in. **Fixed (2):** `measures.html`'s `.m`/`.em`, row-shaped flex containers
    that never declared `flex-wrap`; neither name is in `base.css`'s shared wrap list, correctly, so
    the fix went in the page (adding a single-page class to the shared sheet is the exact mistake
    item 39's own entry warned about for `.grid`). Content floor ~411px, so the page overflowed at
    **490px** (1px), **480px** (11px), **375px** (116px), pushing the `p.N ↗` citation link — the
    one control on the row — off the right edge. **Openly below this batch's own 960/720 anchors**,
    fixed anyway because 480px is a quarter of the same 1080p monitor the 960px anchor is half of,
    and because it provably changes nothing above 491px. The other **11 pages needed nothing**, per
    page rather than as a blanket claim. Also measured: all 13 at 720px with device emulation on
    (`pointer:coarse` matching, 44×44 minimums live) and at 960px with a coarse pointer forced —
    the case that matters, since `jobcard`'s and `dossier`'s two-column grids are still live at
    960px while collapsed at 720px — zero overflow in every combination. **Measured and deliberately
    not fixed:** the bottom-right fixed chrome overlaps itself (18×44 / 156×4 / 66×4 / 21×29 px),
    but the four rectangles are **byte-identical at 1400/960/720px on a desktop pointer** (a coarse
    pointer still shows them, touch sizing only growing the last pair 21×29 → 21×44),
    so it is pre-existing, width-independent, shared by all 48 pages, and belongs in its own PR;
    plus two 360px-only overflows (`procedure`'s own deliberate `.steps{min-width:340px}` floor,
    `fastener`'s 5-column table), both below any named scenario. **One trap worth carrying:** the
    server holds UI files in memory after first read, so the first post-edit measurement showed the
    fix doing nothing — the browser was being served the pre-edit file. Every "after" number comes
    from a server restarted on the edited tree, confirmed by `curl`-ing the page for the new rule
    first. Tests: `test_uiux_fixes.py` 273 → **285**, negative-tested (reverting both fixes gives
    `280 passed, 5 failed`; restoring gives 285/0) — source-text assertions, **not** layout
    measurements. See `CHANGELOG.md` `[1.58.0]`.
41. **`[1.59.0]` — per-page responsive verification, batch 2 of 4: 12 pages resized for real
    (multi-window support, PR 9/25).** Stage 3 of the same plan, and the answer to the thing item 39
    explicitly could not prove. `[1.57.0]` shipped the shared breakpoints and stated that not one
    real page had been opened in a resized window; this is that work for one of the four batches.
    (Numbered 41 here, and `1.59.0`, because three sibling batches are in flight in parallel and
    claimed `1.58.0`/`1.60.0`/`1.61.0`; if merge order differs, renumber — `[1.57.0]` did exactly
    that with its own version.) **The 12:** `solve`, `troubleshoot`, `ask`, `handover`, `circuitlab`,
    `scan`, `semantic`, `visual`, `kg`, `related`, `index`, `help` — each loaded against the running
    server at **960** and **720 CSS px** with real content, not an empty shell (`solve` driven
    through both stages, `troubleshoot` onto a fault tree that really has checks, `ask` left to
    finish its ~25-second round trip, `circuitlab` with the RLC sample simulating, `index` past its
    side-gate with 30 results and the in-app document viewer open). Two instrumented passes each: an
    **overflow probe** (anything past the viewport, any `scrollWidth > clientWidth` under
    `overflow-x:visible`, anything clipped by >20px under `overflow-x:hidden` — the silent
    content-loss case an ordinary overflow check misses — plus document-level scroll width) and a
    **mid-word-break detector** (record every leaf element's height, set
    `body.style.overflowWrap='normal'`, re-measure, report anything *taller* with the shared rule
    than without). **Two pages needed a fix, both in that page's own inline `<style>`; `base.css` is
    untouched.** (1) **`index.html`**: `.vbar`'s densest `.pgctl` row (Clean, four sliders,
    Mirror/HD/Loupe/Callouts/Reset) is a flex row with no wrap, so below ~960px every control is
    shrunk narrower than its own label — and `[1.57.0]`'s shared `body{overflow-wrap:break-word}`
    then split four of them **inside the word**. Measured at 720px: `contrast` 16→32px, `zoom`
    16→32px, Mirror/Loupe/Callouts/Reset 52→71px each, rendering as `Mirr / or`, `Loup / e`,
    `Callou / ts`, `Rese / t`. **No overflow check would ever have found this** — the row's
    `scrollWidth` and `clientWidth` were both 688px with and without the rule.
    `@media(max-width:960px){.pgctl{flex-wrap:wrap}}` returns every button to its natural width at a
    uniform 33px with its label whole on one line, costing 18px of toolbar height (`.vbar` 249→267px)
    and buying back six readable controls; the detector then reports zero breaks. This is the first
    page where `[1.57.0]`'s own honestly-declared `break-word` trade came due, and the answer turned
    out to be better than the per-page override that entry anticipated. Scoped at 960 *beside* — not
    merged into — this file's own long-standing 920px block, which keeps its separate job (collapsing
    `main` and the `.vside` rail, both re-verified working at 720px). Not put in `base.css` because
    `.pgctl` is an `index.html`-only class name that `base.css`'s own `pointer:coarse` rule already
    describes as "index.html's in-viewer zoom/contrast/tilt row". (2) **`handover.html`**: `.card` is
    `overflow:hidden` for its rounded corners, so a table wider than the card is cut off with **no
    scrollbar and nothing on screen to say a column is missing** — measured at 720px, a 1299px table
    inside a 670px card, 629px simply gone. `@media(max-width:960px){.card{overflow-x:auto}}` makes
    it reachable while keeping `overflow-y:hidden` and the corners. **Honest scope:** latent, not
    observed — both *wired* tables fit at 720px with realistic rows (hyphenated NSNs, a superseded
    `MS51922-17`); the two that would hit it first render raw `JSON.stringify` output, which
    `overflow-wrap` cannot break because it does not affect a table column's min-content width, and
    are not wired server-side yet, as the page's own notes already say. **The other ten needed
    nothing**, confirmed rather than assumed — notably **`circuitlab.html`**, flagged up front for
    its real-time simulator stage: the `194px 1fr 236px` shell still fits at 720px (stage 290px) and
    960px (530px), and the SVG stage is **not** distorted or mis-tiled, its background grid `<rect>`
    measuring exactly the stage width at both. A stale 530px grid rect seen after resizing was chased
    to ground and was the *harness*, not the page — CDP device-metrics emulation changes the viewport
    without firing `resize`, and this page redraws on `window.addEventListener("resize", draw)`;
    dispatching it manually snapped the grid to 970px, and a fresh load at each width is correct.
    A1's `↗` pop-out buttons from `[1.55.0]` are fully on screen in the Tools dropdown at 720px.
    **One real collision found and deliberately NOT fixed here:** the bottom-right pill cluster
    overlaps itself (`#vw-read-btn` 458→524, `#bench-pill` 503→570, `#cmdk-pill` 552→708). It is not
    a responsive bug — the identical overlap is present at **1500px** — so it is width-independent,
    pre-existing, and lives in shared `palette.js`/`readaloud.js` chrome affecting all 48 pages,
    exactly the shared-file change most likely to conflict with the three sibling batches in flight.
    Recorded rather than lost; it belongs in its own PR. New `engine/tests/test_responsive_batch2.py`
    (**49 checks, 49 passed**) parses each page's inline `<style>` with CSS comments stripped first —
    not cosmetic, since both fixes carry doc comments naming the very properties they set — and
    asserts each fix exists, is scoped to its measured breakpoint and not global, that the
    pre-existing 920px and `.card{overflow:hidden}` rules survive, that all 12 pages still link
    `/base.css` and declare a `width=device-width` viewport meta (without which a narrow browser lays
    out at ~980px and scales, and every rule verified here would silently never fire), and that the
    eight no-fix pages still carry no page-local width breakpoint. Negative-controlled: with the
    fixes removed it returns `45 passed, 4 failed`, exit 1. `rps_lint` was checked before touching
    anything — of these 12 only `solve.html`/`help.html` are `ES5_REQUIRED`, and no inline `<script>`
    was touched on any page, both fixes being CSS. See `CHANGELOG.md` `[1.59.0]`.

42. **`[1.60.0]` — responsive per-page pass, batch 3 of 4: 11 pages resized for real, 3 genuine
    narrow-window defects fixed (multi-window support, PR 10/25).** Stage 3, the first instalment of
    the debt item 39 recorded against itself. `learn`, `binaudit`, `coverage`, `ingest`, `ops`,
    `status`, `verify`, `command`, `collections`, `review` and `demo` were each loaded from the real
    server in a real browser **with their real data** and measured at **960 CSS px** (half a 1080p
    monitor) and **720 CSS px** (a docked or quarter-width window). Three defects found.
    **(1) `binaudit.html`** — its audit table's NSN column is 127px and holds one NSN per line at
    1440px, but 123px at 960px and 94px at 720px, where the hyphens inside an NSN become ordinary
    break opportunities and every identifier splits across two lines (`6115-01-` / `036-6374`) — on
    the one page whose stated job is telling apart look-alike NSNs. Not `base.css`'s
    `overflow-wrap`, checked by suppressing that rule and re-measuring: the NSNs still broke. Fixed
    with `white-space:nowrap` on the column **plus** `overflow-x:auto` on `#out`, since the nowrap
    alone pushed `scrollWidth` to 435 against a 400px client; with both, 400px measures 400 = 400
    with `#out` scrolling internally at 419/368. **(2) `status.html`** — the NIIN format-drift queue
    ("same NIIN written as different NSN strings") split a variant mid-NSN at 720px; measured
    character-by-character with a `Range`, the live first row read `5305-00-292-4587 · 5306-00-292-`
    / `4587 · 5605-00-292-4587`. Fixed with nowrap on the NIIN/variants columns at ≤720px inside a
    real `.tscroll` wrapper — required, because nowrap alone with a 5-variant row pushed the page to
    1023 against 720, and `overflow-x` on a `<table>` element does nothing (Chrome computes it
    `visible`). After: 40 live rows, 0 broken variant cells, page 720 = 720; at 960px the column
    widths are byte-identical to the pre-change measurement. **(3) `demo.html`** — `place()` clamped
    the guided-tour tooltip against a hard-coded `barH = 56`, true only while the control bar fits
    one row; at 720px it is 119px (86px from its own dots strip wrapping, then 119px once item 39
    added `flex-wrap:wrap` to the shared `.bar` selector), so at 720x620 steps 3/14/15 of the
    19-step Mechanic tour put the tooltip 44px/3px/59px **behind** the bar. Fixed by reading the
    bar's real `offsetHeight`; after, every step clears it (worst −5px) and at 1440px the measured
    height is exactly 56, so the change is inert at desktop width. ES5 only — and `rps_lint`'s
    recurring false positive struck again, matching the words "class at 960px" in a comment as a
    class declaration. The other **8 pages needed nothing**, each reported as a measurement rather
    than a shrug (see `CHANGELOG.md` for what was loaded and checked on each), including two
    pre-existing oddities deliberately left alone because they measure identical at 1440px:
    `coverage.html`'s 156.3% meter and `command.html`'s `.cards` grid shrink-wrapping to one column
    inside a `.row` flex. **`base.css` deliberately untouched** — every defect was page-specific and
    three sibling batches were in flight against the same shared sheet. New
    `engine/tests/test_responsive_batch3.py`, **25 checks all passing**, proven non-vacuous rather
    than claimed: with all three fixes deliberately reverted it reported 18 passed / 7 failed, exit
    1, naming exactly the reverted ones, after which the files were restored `diff`-identical. See
    `CHANGELOG.md` `[1.60.0]`.

43. **`[1.61.0]` — responsive verification, batch 4 of 4: the 12 specialized-visualization pages
    resized for real (multi-window support, PR 11/25).** The **last** of the four per-page batches
    that turn item 39's shared CSS from "written" into "verified" — `master`, `mastercov`, `packet`,
    `exploded`, `schematics`, `threed`, `deepzoom`, `stepflow`, `keywords`, `publog`, `audit`,
    `cadtex_test`. (Item number 43 and version `1.61.0` were both reserved up front: three sibling
    batches of this same pass were being built in parallel, claiming `1.58.0`/`1.59.0`/`1.60.0` and
    items 40–42; if one does not land, this renumbers on merge exactly as item 39 did.) Each page
    was served by a real `viewer_app.py`, opened in a real browser and measured at **960px and
    720px** with `getComputedStyle`/`getBoundingClientRect`. Several of these pages render a
    WebGL/canvas/SVG stage that sizes itself by script — the reason `base.css` excludes
    `svg`/`canvas` from its image clamp — and **those stages were out of scope and untouched**; what
    was checked is the chrome around them. **Three real defects, each fixed in that page's own
    inline `<style>`, none in `base.css`:** `cadtex_test.html`'s three *fixed* `310px` grid tracks
    (`3*310 + 2*14` gap `+ 2*20` body margin = **998px**) overflowed by **210px at 768px** and 18px
    at 960px, clipping whole test cards and their canvases — fixed with an `auto-fit` fallback to as
    many *whole* 310px tracks as fit, deliberately chosen so the `290x220` canvases stay untouched;
    `deepzoom.html`'s `.top` bar of up to 11 controls declared no `flex-wrap` and pushed the page
    **77px sideways at 720px** (`scrollWidth` 797 vs 720) whenever the Editions/Ask-this-page buttons
    are live — `.top` is declared on exactly two pages app-wide and the other already wraps, so it
    was a genuine one-page gap rather than a hole in the shared sheet; and `schematics.html`'s sheet
    title, `flex:1 1 0%` in a 15-control bar, shrank to **3px at 720px** (needing 182px), fixed by
    giving it a row of its own below 960px. All three are scoped inside `@media (max-width:960px)`
    so wide-desktop layout is byte-identical to before (R1), verified by re-measuring at 1400px.
    **Nine pages needed no change and that was measured, not assumed** — zero escaping elements at
    both widths, with each page's *own* render output injected verbatim where this host has no data
    built, so the real tables and card lists were exercised rather than measured empty.
    `packet.html` got the print check it was owed: the new breakpoints **do** bind during print
    (the real page box is 710px/688px after its own `@page{margin:14mm}`), but exactly one of the
    seven rules reaches it (`overflow-wrap:break-word`, which helps), so nothing screen-only leaks
    into the printed sheet. Two honest negatives recorded rather than dropped: `publog.html` showed
    **no** measurable benefit from `overflow-wrap` (its long string breaks at its own commas), and a
    pre-existing, **width-independent** overlap in the shared bottom-right chrome (`#vw-footer` vs
    the `palette.js` pills, 4px; the read-aloud button vs the bench pill, 21px) was found, confirmed
    identical at 1400px, and deliberately left alone as app-wide chrome outside a 12-page batch. New
    `engine/tests/test_responsive_batch4.py`, **58 checks**, proven load-bearing by mutation (all 5
    injected regressions caught); two of its checks are real arithmetic over the page's own parsed
    CSS rather than string matching. See `CHANGELOG.md` `[1.61.0]`.

44. **`[1.62.0]` — a real `cad.pct` bug, unrelated to the multi-window initiative: found while
    reading `/api/coverage` output during that initiative's own responsive-verification batches,
    fixed at both layers.** `coverage.html`'s three percent meters built their bars via string
    concatenation with no width clamp, while the page's own `pctBar()` helper already did it right
    but was dead code — routed all three through it. Per R13 (fail loud, never silently
    misrepresent), the bar clamps to 0-100 but the number does not — an out-of-range ratio still
    reads true, now with a visible "over 100%" flag. Root cause: `coverage.py`'s
    `representative_parts` only counted `ref_nsn` rows with FLIS dimensional characteristics,
    undercounting by roughly a third against `make_cad.py`'s real render pool (which unions that
    with every NSN against a figure in `parts`) — 20,869 counted vs 32,622 actually eligible — plus
    a smaller numerator bug double-counting turntable sprite-sheet renders as separate parts. Both
    fixed at the source, with sync comments tying the two files' copies of the query logic
    together. Verified live: `cad.pct` 156.3% → 100.0%. See `CHANGELOG.md` `[1.62.0]`.

45. **`[1.63.0]` — A2: per-page pop-out control (multi-window support, PR 14/25, stage 4).** The
    mirror image of item 37's A1: a page a technician is *already on* now gets its own control to
    pop itself out into a second window, instead of navigating back to the home nav first. New
    `VW.popoutControl()` in `shared.js`, called once, zero-config, by a page's own inline script,
    injects a real, keyboard-focusable `<button id="vw-popout-pill">` — never a `div`+click handler,
    the same `[1.46.0]`/`[1.47.0]` accessibility convention item 37 followed — labeled with A1's own
    `"Open X in a new window"` phrasing, with one shared `doPopout()` inner function backing both the
    button and a new Ctrl+K palette entry so the open call is never duplicated between them.
    **The window-naming logic is a byte-for-byte copy of A1's `popoutName()`** (`index.html`, ~line
    592) — the entire reason A1's own comment named this PR in advance: popping `/torque` out from
    the home nav, then clicking `/torque`'s own new control, lands on the SAME window, not a second
    one; the new `engine/tests/test_a2_popout.py` extracts and compares the two files' actual
    regex/string-transform source text to prove that, not just eyeballs it. **The palette entry
    needed a new, order-independent registration hook that did not exist before this PR:**
    `popoutControl()` cannot reach into `palette.js`'s `COMMANDS` array directly — on the normal load
    order (`shared.js` in `<head>`, then the page's own inline script, then `palette.js` last)
    `COMMANDS` does not exist yet at that moment — so it pushes a plain descriptor onto a new
    `window.__paletteQueue` instead, and `palette.js` drains that queue into `COMMANDS` at **two**
    points (right after `COMMANDS` is built, and again as the first statement inside `open()`) so a
    descriptor lands correctly regardless of which of the two real script orders a future page ends
    up using. Placement (`base.css`, `#vw-popout-pill{right:288px;bottom:12px}`) was measured in a
    real browser rather than guessed — `#bench-pill`'s own rendered left edge sits around
    `right:217px` at every width tested (1400/960/720 CSS px, and in kiosk mode), leaving this pill a
    genuine ~70px clear gap; it does **not** touch item 43's already-known, separately-filed
    `#vw-footer`/`#cmdk-pill`/`#bench-pill` overlap. Adopted on the 5 pages the plan names —
    `part`/`procedure`/`torque`/`jobcard`/`bench` — each already carrying its item 40/`[1.58.0]`
    responsive pass. New `engine/tests/test_a2_popout.py`, **62 assertions**, proven load-bearing by
    reverting 5 representative fixes one at a time (the helper's own existence, the naming-transform
    identity with A1, both palette drain call sites, one page's adoption call, the pill's placement
    offset) and confirming the relevant assertion(s) genuinely failed, then restoring and
    re-confirming a clean 62/0. `rps_lint` caught the same false-positive class this initiative has
    hit before (item 34's backticks/ellipses, item 42's "class"): backticks used as plain
    code-reference punctuation in a doc comment read as ES6 template literals by the blunt text
    scan — reworded without backticks, not suppressed. **Owed manual check, not automatable here,
    same as item 37's own PR:** pop out
    `/torque` from its own new control, then pop out `/torque` again from the home nav's ↗ — confirm
    one window, not two. See `CHANGELOG.md` `[1.63.0]`.

46. **`[1.64.0]` — B: curated workspace launcher (multi-window support, PR 15/25, stage 5).** Two
    real, one-click launch sets, each a real `<button>`: "Launch Work Order" on `jobcard.html` opens
    `procedure.html` + `torque.html` + `part.html`; "Launch Solve It" on `solve.html` opens
    `troubleshoot.html` + `procedure.html` + `locate.html`. Both follow the plan's own required
    order — one `VW.workspace.create(name, items, "template")` call persists a real workspace record
    *before* anything opens, then each page opens via `VW.windows.open()` — and both read `#q`'s
    CURRENT value inside the click handler (never a page-load-time value) and thread it onto every
    launched URL as `?q=...`, the same convention item 37/`index.html`'s `threadQuery()` (A1)
    established for every Tools-menu link. **`shared.js` gained one new export, not a new naming
    rule:** item 45's `_popoutWindowName()` was private to its closure, sufficient for
    `popoutControl()` (which only ever names the CURRENT page), but B opens pages other than
    whichever one it's running on and needed the same transform reachable directly — exported as
    `VW.popoutWindowName`, the exact same function, so a page already open via A1's home-nav ↗, A2's
    own pop-out control, or a previous B launch is REUSED, never duplicated; neither `jobcard.html`
    nor `solve.html` re-implements any fragment of the naming regex, both call
    `VW.windows.open(url, {name: VW.popoutWindowName(url)})`, byte-for-byte identical text in both
    files. **The design doc's item-8 "Addition this revision" — a `VW.capabilities.tier` guard
    before opening several windows at once — is written forward-compatible, not built out:**
    `VW.capabilities` is Stage 6 (PR 19-25) and does not exist on `main`, and PR 15's own "Depends
    on" list names no Stage 6 PR, so both launch functions feature-detect it end to end
    (`window.VW && VW.capabilities`, then `caps && typeof caps.tier==='string'`) — reads as "no tier
    info" today and does nothing, starts warning on `lite`/`legacy` the day a real
    `VW.capabilities.tier` ships, with zero further code change needed here. New
    `engine/tests/test_b_workspace_launcher.py`, **52 assertions**, proven load-bearing by reverting
    6 representative fixes one at a time (the `shared.js` export, one page's item order,
    `workspace.create()`'s ordering relative to the open loop, the capabilities guard's
    short-circuiting, one page's button id, a simulated re-implemented naming regex) and confirming
    the relevant assertion(s) genuinely failed, then restoring and re-confirming a clean 52/0.
    `rps_lint` clean (`solve.html`/`shared.js` are ES5-required; `jobcard.html` modern-by-design).
    **Popup-blocker behavior tested for real, with an honest limitation found and reported rather
    than assumed away:** this session's automated Browser-pane preview tool cannot demonstrate
    genuine multi-window fan-out — every `window.open()` call there returns `null` (the
    already-tested blocked-popup path in `VW.windows.open()` handles that cleanly, no crash), and the
    pane's one visible tab is separately redirected to only the LAST attempted URL by the harness
    itself, confirmed identical with a code-independent page containing nothing but 3 raw
    `window.open()` calls — i.e. a property of that sandboxed preview tool, not a finding about real
    desktop Chrome/Firefox. What WAS confirmed live against a running server: both buttons correctly
    thread the live `#q` value onto the final URL (`/part?q=alternator`, `/locate?q=brake pad`).
    Whether a real desktop browser opens all 3 as separate windows within one synchronous click, and
    whether a second click reuses them, is called out as a genuine unverified manual check — same
    honest treatment item 45/A1/A2 already give their own window-reuse behavior. **Deliberately out
    of scope, matching the plan's own PR 15 scope, not a shortfall:** these workspaces launch fresh
    every time and are never saved/listed/reopened — that's PR 16/F's job, which depends on B
    existing first. See `CHANGELOG.md` `[1.64.0]`.

47. **`[1.65.0]` — `VW.workspace` export/import (multi-window support, PR 3/25, stage 2 — landed out
    of order).** The plan doc placed this right after PR 2 (CRUD); it was skipped over during this
    session's earlier parallel-dispatch of other PRs and is inserted now, after PR 15/B, because PR
    16 (F — save & reopen named workspaces, next in the queue) explicitly depends on it existing
    first. Four new `shared.js` exports alongside PR 2's `create`/`list`/`get`/`touch`:
    `exportUrl(id)` returns a `"ws=<json>"` query-string encoding for handing one workspace to a
    DIFFERENT technician's browser; `exportFile(id)` wraps the identical payload as a downloadable
    `application/json` `Blob`; both return `null` (never throw) for an unknown id, matching `get()`'s
    own not-found convention. **The exported payload deliberately carries only `{name, items}`** —
    never this browser's internal id or `created`/`lastOpened` timestamps, meaningless (the id) or
    actively misleading (the timestamps) once recreated on a different machine.
    `importUrl(qs)` (a bare query string or a full `"?ws=..."` fragment, either accepted) and
    `importFile(blob)` (Blob→text via a plain `.then()` chain — never an arrow function or
    async/await, matching `palette.js`'s existing `fetch().then()` convention) share one internal
    parse-validate-create helper: shape-validated BEFORE anything touches storage, throwing/rejecting
    with a specific `Error` message on any mismatch, matching the design spec's edge case verbatim
    ("validated before being written, rejected with a clear message on any mismatch") — deliberately
    stricter than `create()`'s own lenient item coercion, since an import is trusting a file that
    could have been hand-edited, corrupted, or tampered with, not a payload this same page built for
    itself. **Item shape checking is not reimplemented a second time:** validation reuses PR 2's own
    `_wsItems()` as the arbiter — if `_wsItems()` would drop an entry (no usable `page`, not an
    object), that entry was invalid, and unlike `create()` the entire import is refused rather than
    silently keeping only the entries that happened to survive. **A fresh id is always minted**, via
    the same `workspaceCreate()`/`_wsNewId()` path every other workspace goes through; neither import
    function ever reads an `id` field off the incoming payload — not even a deliberately spoofed one,
    proven directly in the new test rather than merely argued.
    **New `engine/tests/test_workspace_export_import.py`** (`node --check` syntax coverage) **+
    `tests/js/test_workspace_export_import_node.js`, 53 real round-trip assertions** — not
    source-text matching, actual calls through the real exported functions. The exportUrl→importUrl
    and exportFile→importFile round trips each run across TWO SEPARATE `localStorage` stores (one per
    simulated browser, unlike PR 2's own node test which deliberately shares one store between two
    tabs) so the round trip proves the exported payload is genuinely portable rather than two
    contexts quietly sharing one store. Proven load-bearing by two targeted, restored-afterward
    breaks: temporarily making import trust an incoming `id` field (3 "never reuse a spoofed id"
    assertions genuinely failed), and temporarily skipping shape validation before the write (9
    assertions genuinely failed, covering both the "throws" and the "storage left untouched" halves
    of the malformed-import cases) — each confirmed failing, then reverted and re-confirmed a clean
    53/0. `rps_lint.py` clean (`shared.js` is ES5-required; the only close call was a doc comment's
    own `"..."` ellipsis reading as a false-positive spread/rest hit, reworded rather than
    suppressed). Design doc's own `VW.workspace` API-block header comment updated from "CRUD in
    progress; export/import/templates next" to "CRUD + export/import landed; built-in templates
    next". **Deliberately out of scope, matching PR 3's own plan-doc scope, not a shortfall:**
    `schemaVersion`/migration-on-read (Stage 6), the File System Access API path for `exportFile`
    (the design doc's own deferred note), and any UI over these four functions — that UI is PR 16/F's
    job, which depends on this PR existing first. See `CHANGELOG.md` `[1.65.0]`.

48. **`[1.66.0]` — F: save & reopen named workspaces + the auto-checkpoint (multi-window support, PR
    16/25, stage 5).** The UI over everything item 46 (B)/47 (export-import) built. New
    `engine/ui/workspaces.html` (`/workspaces`): lists every saved workspace, most-recently-opened
    first; **save** turns THIS TAB's own `VW.windows.registry()` — the `{name, url}` pairs it opened
    via a pop-out or a launch button — into `{page, params}` items by hand-parsing each open
    window's url apart (the reverse transform of the query-building approach item 46's own launch
    buttons use for their single `q` param, generalized here to an arbitrary params object), names
    it via a plain `window.prompt()` (the same lightweight pattern item 37/`index.html` already uses
    for "name this collection"), then calls `VW.workspace.create(name, items, "manual")`, disabling
    the save with a clear message rather than silently creating an empty workspace when nothing is
    open. **Reopen** calls `VW.workspace.touch(id)` first (so "last opened" means what it says), then
    opens every item via the exact same `VW.windows.open(url, {name: VW.popoutWindowName(url)})`
    pairing item 45/46's own A1/A2/B already use — never a re-implemented naming copy. **Export**
    offers a real share-link copy (`origin + '/workspaces?' + exportUrl(id)`, via
    `navigator.clipboard` where available, a visible selectable field as fallback where it isn't) and
    a real `.json` download (the exact `Blob` + `URL.createObjectURL` + `<a download>` pattern
    `circuitlab.html` already established, not a new mechanism). **Import** accepts a pasted share
    link (a full URL, a bare `?ws=...` fragment, or the raw `ws=...` string `exportUrl()` itself
    returns — all three normalized to what `VW.workspace.importUrl()` already parses) or an uploaded
    `.json` via `importFile()`, both catching item 47's real thrown/rejected `Error` and surfacing it
    via `toast()`/an inline message rather than letting it propagate unhandled.

    **Gap filled: `VW.workspace.delete(id)`** — the one CRUD operation item 39's original PR shipped
    without (only `create`/`list`/`get`/`touch`). A list UI that only ever grows is a real usability
    problem for a page a technician returns to across a whole career, not a hypothetical one; same
    read-all/mutate/write-back shape and notify-only-after-the-write-commits ordering as `touch()`,
    wired behind a real `confirm()` on the page matching this app's established care around
    irreversible actions.

    **The auto-checkpoint — design doc item 9's "Addition this revision," built for real, not
    flavor text.** A single well-known slot, `viewer_last_session`, genuinely distinct from the
    named-workspaces key `viewer_workspaces` (proven both structurally — the two source literals
    compared — and functionally — a real save/read round trip against both keys in the same store),
    silently holding a tab's own `VW.windows.registry()` snapshot, overwritten every time, never a
    growing list, and structurally invisible to `VW.workspace.list()` since it lives under its own
    key entirely. Written on `pagehide` (chosen over `beforeunload`/`unload`, both already used
    elsewhere in this codebase — `readaloud.js`/`scan.html` respectively — with no single established
    preference; `pagehide` fires reliably on bfcache eviction where `beforeunload` is increasingly
    throttled by modern browsers) **and** a 2-minute `setInterval` safety net against the design
    doc's own explicitly named risk — a browser/OS crash mid-shift fires no unload event at all.
    **Wired at the `shared.js` top level, not only from `workspaces.html`**, so the checkpoint
    reflects windows opened from ANY feature (A1/A2/B) — made safe by skipping the write whenever the
    writing tab's own registry is empty, so an idle tab with nothing open can never clobber a real
    checkpoint a different tab just wrote (two tabs that BOTH genuinely have windows open remain
    last-write-wins with no merge, the same conflict resolution item 39's own `VW.bench` already
    accepts). `workspaces.html` is the ONE place that ever offers to act on it — "a checkpoint
    exists" is the whole restore heuristic, the design doc's own explicitly-sanctioned baseline over
    a more elaborate staleness rule — and restoring is strictly a real button click, never automatic
    on load, mirroring this app's established stance (already written into the design doc's general
    multi-window philosophy) that a web page cannot run code "on launch" unprompted.

    **Handover integration**, the plan's own "using PR 3's export/import for the `/handover`
    hand-off": a new, real, findable section on `handover.html` ("Hand off your open workspace")
    linking to `/workspaces`, showing LIVE data (`VW.workspace.list().length`, read the same way
    `workspaces.html` itself reads it) rather than a static blurb.

    **New `engine/tests/test_f_workspace_reopen.py` + `tests/js/test_f_workspace_reopen_node.js`,
    40 checks.** Source-level: every required `VW.workspace`/`VW.checkpoint` call is real call-site
    text in `workspaces.html`, the reopen path reuses `VW.popoutWindowName` (not a re-implemented
    naming regex, checked the same way item 46's own test checks jobcard/solve), delete sits behind a
    real `confirm()`, both import paths handle the thrown/rejected `Error`, and `handover.html`
    genuinely carries the new section. Real round trips (Node `vm.createContext`, same convention as
    items 39/47's own node tests): `workspaceDelete()` create→delete→confirm-gone-from-list/get, a
    refused-write case, and the cross-tab "delete" notification over a real `BroadcastChannel`; the
    checkpoint tests build a sandbox with a REAL `addEventListener` (captures handlers instead of a
    no-op stub) and a REAL `setInterval` (captures the callback instead of scheduling one), then fire
    `shared.js`'s OWN module-load-time-registered `pagehide`/interval handlers directly — proving the
    wiring actually exists and actually works, including the "an empty-registry tab's pagehide must
    never clobber a real checkpoint" guard against a second tab sharing the same store. **Proven
    load-bearing**: 5 representative guarantees broken one at a time (removing the delete call site,
    re-implementing the naming regex, making `workspaceDelete()` a no-op, colliding the checkpoint
    key with the workspaces key, removing the handover section) and confirming the right assertions
    genuinely failed (2, 3, 3, 6, 1 respectively), then restored and re-confirmed a clean 40/0.

    **A real regression caught and fixed before this shipped, not glossed over:** the checkpoint
    block was originally inserted between `popoutControl()` and the final `var VW = {...}` assembly —
    harmless in isolation, but item 45's own `test_a2_popout.py` slices `popoutControl()`'s body by
    scanning from its declaration to the NEXT `"\n  var VW = {"` marker, an assumption that broke the
    moment another function's block sat between them: that slice then also swallowed this PR's own
    comment prose mentioning `VW.windows.open(w.url, ...)` as an example, pushing item 45's "exactly
    one `VW.windows.open(` call" assertion to 2. Caught by actually running the FULL `verify_all.py`
    before calling this done, not assumed clean from the new suite alone; fixed by reordering
    `shared.js` so the checkpoint block sits BEFORE `popoutControl()` again, restoring it as the last
    function immediately preceding the `VW` assembly — confirmed `test_a2_popout.py` back to a clean
    62/0 afterward. `rps_lint.py` clean — `workspaces.html` classified `MODERN_BY_DESIGN` (same class
    as item 39/`bench.html`: a localStorage-driven admin tool, not a core ES5-required page);
    `shared.js`/`handover.html` stay ES5-required, unaffected. **Deliberately out of scope, matching
    PR 16's own plan-doc scope, not a shortfall:** screen-aware placement (C, PR 17), the
    kiosk/second-screen view (G, PR 18), and any `VW.capabilities`-gated behavior (Stage 6, not yet
    built). See `CHANGELOG.md` `[1.66.0]`.

49. **`[1.67.0]` — `VW.windows` layout capture + user-triggered restore (multi-window support, PR
    6/25, stage 2 — landed out of order).** The plan doc placed this right after PR 5 (open/reuse/
    toast core); it was skipped over during this session's earlier parallel-dispatch of other PRs and
    is inserted now, out of order, because PR 17 (C — screen-aware placement, next in the queue)
    explicitly depends on it existing first — the same "inserted early because a later PR needs it"
    shape item 47/PR 3 already established. **`registry()` now returns LIVE `screenX`/`screenY`/
    `outerWidth`/`outerHeight`** per tracked window, read directly off the same window handle
    `_winReg` already holds, at CALL time rather than captured once at open-time and cached — a
    technician can move or resize a window after opening it. Every property read is guarded
    independently: a handle that throws or returns something non-numeric on ONE field degrades ONLY
    that field to `null`, never the other three, and never any OTHER tracked window's entry in the
    same `registry()` call. **`windowsOpen(url, opts)` now optionally accepts a position/size hint**
    (`opts.left`/`opts.top`/`opts.width`/`opts.height`, matching `window.open()`'s own
    features-string vocabulary), threaded into the standard third `window.open()` argument only when
    a genuinely NEW window is being opened — never on a reuse, even when the reusing call itself
    offers hints, since browsers generally only honor position/size features on a window's very first
    open. Every hint is sanity-checked against this screen's own `window.screen.availWidth`/
    `availHeight` before use — a generous 4x ceiling, wide enough to admit a plausible
    second-or-third-monitor position, tight enough to still catch the design doc's own named "monitor
    unplugged since the position was saved" case — and a hint that fails is dropped ENTIRELY, never
    partially applied; a bad hint, or an unreadable/non-positive `window.screen`, never throws.
    **New `VW.windows.restoreLayout(entries)`** takes an array shaped like what `registry()` returns
    and, for each entry with a usable `name` AND `url`, calls `windowsOpen()` — the SAME
    open/reuse/toast/broadcast path, not a second, parallel copy of it — translating
    `screenX`/`screenY`/`outerWidth`/`outerHeight` into `windowsOpen()`'s own
    `left`/`top`/`width`/`height` opts; a malformed entry (missing name or url) is skipped, never
    thrown over, never aborting the rest of the batch; returns one `{name, url, ok, reused}` result
    per INPUT entry, in order. **Must never be called from a load/init/`DOMContentLoaded`-style
    handler anywhere in this codebase** — restoring a technician's windows unprompted is exactly the
    design doc's own "a web page cannot run code 'on app launch' unprompted" case; nothing in this
    diff wires one, matching PR 2/PR 3/PR 5's own precedent of shipping API-only, without a dedicated
    UI page.
    **New `engine/tests/test_windows_layout.py` + `tests/js/test_windows_layout_node.js`, 51 real
    assertions** (41 behavioral, through the real production code in a `vm.createContext()` sandbox
    extending item 36's own dual-sandbox convention, + 10 static source-level checks) — a real
    handle's bounds mutated between two `registry()` calls proving the read is genuinely live; a
    throwing property on one tracked window proven to degrade only that field, only that window,
    leaving a second tracked window's entry untouched in the same call; a sane hint proven to thread a
    real features string on a new open and NEVER on a reuse even when the reusing call offers one; an
    implausible hint, a missing `window.screen`, a zero `availWidth`, and a throwing `window.screen`
    accessor all proven to degrade gracefully; `restoreLayout` proven to call through the real
    `windowsOpen()` path via the SAME broadcast-channel envelope shape landing on a genuinely separate
    listener tab, skipping 3 deliberately malformed entries mixed into a 5-entry batch without
    aborting the 2 well-formed ones. The static half proves `restoreLayout` is never invoked anywhere
    in this diff, two independent ways: a comment-stripped full-source scan of `shared.js` for any
    real call-site syntax (zero found beyond the function's own declaration), cross-referenced against
    a `git diff`-scoped scan of this PR's own added lines, plus a check that no
    `addEventListener("DOMContentLoaded"/"load"/"pagehide", …)` handler body anywhere in `shared.js`
    mentions `restoreLayout` at all, even in a comment. **Proven load-bearing** by breaking 6
    representative guarantees one at a time (the live-not-cached read, the per-field throw
    independence, the implausible-hint drop, the reuse-never-threads-bounds rule, the malformed-entry
    skip, and the load-handler-never-calls-it check) and confirming the right assertions genuinely
    failed each time (5, 1, 5, 2, 7, 1 respectively), then reverting and re-confirming a clean 51/0.
    Item 36's own `test_windows_node.js` updated, not broken around: its "no layout fields yet — that
    is PR 6" assertion is now the assertion that those fields exist (`null` in that test's own
    mock-handle harness, which sets no bounds of its own). `rps_lint.py` clean (`shared.js` is
    ES5-required; two prose word choices read as false-positive ES6 `let`/spread-rest hits and were
    reworded, not suppressed, the same near-miss category item 47's own entry already named). Design
    doc's `VW.windows` item-4 header updated from "PR 5 — in progress ...; layout capture/restore is
    PR 6" to "PR 5 + PR 6 landed" — nothing else in that spec file touched. **Deliberately out of
    scope, matching this PR's own plan-doc scope:** any dedicated UI page/button calling
    `restoreLayout()` (PR 17 and/or a later PR's job); the feature-detected, permission-gated
    `getScreenDetails()` multi-monitor placement API (PR 17's own job, explicitly named as depending
    on this PR); and the actual on-screen placement behavior on real, possibly multi-monitor,
    hardware — stated plainly as a manual, real-browser-only check in the PR body, not glossed over.
    See `CHANGELOG.md` `[1.67.0]`.

50. **`[1.68.0]` — C: screen-aware placement (multi-window support, PR 17/25, stage 5).** Depends on
    item 49/PR 6. Extends `windowsOpen(url, opts)` with an opt-in `opts.screen` hint (truthy = "prefer
    a different screen than this tab's own, if one exists and is available"), feature-detected via
    the Window Management API's `getScreenDetails()`, gated "modern tier only" per the design doc's
    own item 10. **The doc/code gap, resolved the same way item 46/PR 15 resolved an identical one:**
    the design doc names `VW.capabilities.windowPlacement` as the gate, but `VW.capabilities` is
    Stage 6 (PR 19–25) and does not exist yet. PR 15 had nothing real to fall back to and shipped
    inert; this PR does have something real — `rps.js`'s already-live `window.RPS.mode`
    (`"modern"`/`"lite"`/`"legacy"`) IS the capability ladder item 10 asks for, so this gates for real
    on an exact `=== "modern"` match (never truthy — `"premium"` is a flag layered on `"modern"`, not
    a mode of its own). `window.RPS` is genuinely `undefined` on 32 of this app's 49 pages (confirmed
    by grep) — treated exactly like "not modern," never a throw. A future Stage 6 PR may swap this for
    `VW.capabilities.windowPlacement`, mirroring item 46's own forward-pointing comment.
    **The permission-timing crux:** `getScreenDetails()` returns a Promise (how the permission prompt
    surfaces), but `window.open()` must run synchronously in the click-handler call stack or a popup
    blocker can treat it as not user-gesture-initiated. `windowsOpen()`'s existing synchronous
    open/reuse/toast/broadcast path runs FIRST, unchanged, and returns its real handle before any of
    this PR's code runs; only then, if the gate passes, does `getScreenDetails()` fire —
    fire-and-forget, never awaited. The resolved target screen (picked from `.screens` by reference
    identity against `.currentScreen`, a comparable `left`/`top` key as fallback; fewer than 2 screens
    or every entry matching current is a no-op) is moved to via `win.moveTo()`. Every failure — API
    absent, denied/rejected promise, a synchronous throw, one screen, a since-closed window — is
    caught silently, never an unhandled rejection.
    **New `test_windows_screen_placement.py` + `test_windows_screen_placement_node.js`, 32 real
    assertions** through the real production code in a `vm.createContext()` sandbox extending item
    36's own dual-sandbox convention (the same one item 49 itself extended): `opts.screen` absent
    NEVER calls `getScreenDetails()` (the single
    most important guarantee given this feature's own stated permission philosophy); the API absent
    and `lite`/`legacy`/undefined `RPS.mode` all skip cleanly; a resolved 2-screen result moves to the
    OTHER screen's bounds, never current's; 1 screen attempts no move; a rejected promise AND a
    synchronously-throwing `getScreenDetails()` both caught with zero unhandled rejections (a real
    `process.on("unhandledRejection", …)` listener backs this); the call ORDER proven via a shared log
    — `window.open()` always before `getScreenDetails()`. **Proven load-bearing** by breaking 6
    representative guarantees one at a time and confirming the right assertions genuinely failed each
    time (3, 2, 2, 3, 1, 4 respectively), then reverting to a clean 32/0. Full `verify_all.py` run
    specifically to confirm item 45's own named `test_a2_popout.py` cross-PR coupling hazard stayed
    avoided (new code landed before `popoutControl()`, same as item 49) — clean 62/0.
    **One pre-existing, not-this-PR's-regression issue found and confirmed, not glossed over:**
    `test_windows_layout.py`'s own `the_diff_genuinely_adds_the_restore_layout_declaration` sanity
    check fails on a clean `origin/main` checkout with zero changes (confirmed via `git stash`) — a
    self-referential git-diff check that can never pass again now that item 49/PR 6 is merged and its
    declaration lives in `origin/main` itself; flagged as a separate follow-up, not touched here (out
    of this PR's scope). `rps_lint.py` clean. Design doc's own `C's extension to VW.windows` section
    updated to name the real `window.RPS.mode` gate instead of the not-yet-existing
    `VW.capabilities.windowPlacement`. **Deliberately out of scope:** any UI page/button passing
    `opts.screen` (PR 18/G, next in the plan, is the first real consumer); `win.resizeTo()`; and the
    actual on-screen placement behavior on real, possibly multi-monitor, Chromium hardware — Node has
    no `getScreenDetails` and no real screens to be right or wrong about it, stated plainly as a
    manual, real-hardware-only check in the PR body. See `CHANGELOG.md` `[1.68.0]`.

51. **`[1.69.0]` — `test_windows_layout.py`'s own item 49/PR 6 sanity check became a permanent
    false-failure once PR 6 merged.** `the_diff_genuinely_adds_the_restore_layout_declaration`
    asserted the diff against `origin/main` genuinely adds `windowsRestoreLayout`'s declaration — true
    only while PR 6 was still unmerged; once merged, `origin/main` already contains it, so that diff
    is naturally, permanently empty from here on and the assertion could never pass again on any
    branch cut from current `main`. Not a regression indicator, a check that quietly assumed its own
    branch was always mid-flight. **Fix**: new `declaration_already_merged()` helper reads
    `origin/main`'s own tree directly via `git show` and checks the declaration against it — the
    sanity check now passes on EITHER "the diff adds it" (live-PR case) OR "already merged into
    `origin/main`" (post-merge case), renamed accordingly. Confirmed it still catches a real
    regression (all three states manually simulated: genuinely missing from both places fails; either
    real condition passes). **Second bug found while writing the fix**: `git show`'s output triggered
    a real `UnicodeDecodeError` crash under this Windows box's default `cp1252` `subprocess.run`
    decoding, tripping on a UTF-8 "←" already inside a `shared.js` comment — fixed by passing
    `encoding="utf-8"` explicitly on both the new `git show` call and the pre-existing `git diff` call
    in `git_added_lines()`, which reads the same UTF-8 content and was equally exposed, just never
    triggered before by coincidence of an empty diff. Verified: `test_windows_layout.py` standalone
    11 passed, 0 failed (was 10/1); clean within a full `verify_all.py --snapshot` run too. Two
    unrelated, pre-existing flakes (`test_hardening.py`'s J68 check, `test_routes.py` route timeouts)
    reproduced independently and confirmed clean in isolation, neither touching this fix's files.
    **Landed as PR 59**, opened directly against `main` from a branch cut before item 50/PR 17 merged
    — both claimed `[1.68.0]` in `CHANGELOG.md`; resolved on merge by retitling this fix to `[1.69.0]`,
    the genuinely next-free version, the same renumbering-on-late-merge pattern this project has used
    since `[1.54.0]`'s own PR 47. See `CHANGELOG.md` `[1.69.0]`.

52. **`[1.70.0]` — Root cause, finally: `test_routes.py`'s "known pre-existing `/api/ask` timeout
    flake" was a live network call, not slow compute.** Named across a dozen-plus prior `CHANGELOG.md`
    entries with the same shrug — reproduced on unmodified `main`, not this change's fault, moving on.
    **What it is not:** expensive local computation outgrowing a fixed timeout, the
    `test_ingest_routes.py`/`[1.50.0]` shape this flake was always filed alongside. **What it actually
    is:** `/api/ask` (`ask.answer()`) and `/api/search_hybrid` (`hybrid_search()`) both lazily
    `import embed`, and `embed.py`'s `SentenceTransformer(...)` call reaches the LIVE Hugging Face Hub
    on every fresh process — measured directly at 15.97s with a real "unauthenticated requests to the
    HF Hub" warning on the wire, vs. a consistent 8.4-8.7s across 3 runs once forced fully offline
    against an already-warm local cache. An unbounded network round trip is exactly why widening the
    timeout never once fixed it in over a dozen attempts (45s wasn't enough either, reproduced live
    while diagnosing this) — and it directly contradicted `.github/workflows/ci.yml`'s own header
    claim that this suite has "no network egress." **Fix**: `HF_HUB_OFFLINE`/`TRANSFORMERS_OFFLINE`
    set via `os.environ.setdefault(...)` near the top of `engine/tests/test_routes.py` (never an
    overwrite — an explicit ambient override still wins), verified safe both warm-cache (real semantic
    path, purely from disk, 8.4-8.7s) and cold-cache (offline mode fails immediately, ~5s, caught by
    `ask.answer()`'s own pre-existing fallback to FTS-only passages — never a hang, never a 5xx);
    `_get()` gained an optional `timeout=`, with a new `SLOW_ROUTE_TIMEOUT` dict giving just these two
    routes 25s (~3x the observed warm-cache worst case) while every other route keeps the tight 10s
    default. **Trade-off stated plainly:** CI, having no Hugging-Face-model cache step, no longer
    exercises the real semantic path for these two routes at all — only FTS fallback — same risk that
    was always silently there on any run whose download stalled past its timeout, just deterministic
    now instead of a coin flip; a follow-up CI model-cache step would restore full coverage, left out
    to keep this fix scoped. Verified: `test_routes.py` standalone, 3 consecutive runs, 298/0 every
    time (was 297/1); full `verify_all.py --snapshot` 75/75 ALL GREEN. **Landed as PR 60.** This entry
    itself is a doc-sync completion: PR 60 shipped with only `CHANGELOG.md` updated (VERSION bumped,
    no matching item here or in `MASTER-RECONCILIATION.md`/`HANDOFF-NOTE.md`), and PR 60 had already
    merged by the time the gap was noticed — completed here in its own follow-up PR, the same way item
    51/PR 59's own incomplete doc-sync was completed before it merged. See `CHANGELOG.md` `[1.70.0]`.

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
