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
restarted, `[1.42.0]`; then TLS support for LAN-exposed deployments — the existing
`VIEWER_ALLOWED_HOSTS`/`VIEWER_AUTH_TOKEN` hardening protected authentication over plain HTTP, but a
LAN-exposed VIEWER still crossed the network unencrypted; fixed with new off-by-default
`--tls`/`--cert`/`--key` flags wrapping the listening socket in stdlib `ssl` (TLS 1.2+, zero change
to `Handler`/the worker semaphore), a new one-time self-signed-cert CLI (`engine/gen_cert.py`, gated
behind an optional `cryptography` import rather than an `openssl` shell-out or a vendored X.509
encoder), `safe_public_base()` made scheme-aware for `/api/qr`, and a real-TLS-handshake test suite
confirming both the TLS-on and TLS-off paths, `[1.43.0]`; then the first real backup restore drill ever
performed — the weekly `backupdb` automation had run for real and passed `PRAGMA quick_check`, but nobody
had ever pointed a live app instance at a restored copy and confirmed it actually served correct data;
one was performed for real (copy to an isolated scratch location, a genuinely separate `viewer_app.py`
instance, real queries against real endpoints, original backup + live `viewer.db` confirmed untouched
before and after), and it found a real, previously-unknown gap: `/api/search`/`/api/pmcs` silently return
empty against a backup whose `schema_version` predates the `pages.ocr_confidence` column current code
requires in those paths — closing the "is this actually restorable" question while opening a real,
documented follow-up decision, `[1.44.0]`).** This document
exists because the project's own canonical docs had drifted out of sync with each other across sessions —
including, at the 2026-08-09 update, this file itself: it named **v1.13.4** as the state all canonical docs
agreed on the same day `CHANGELOG.md`'s newest entry had already moved on to **v1.13.5**. The exact same drift
class recurred at the 2026-08-24 update: `CHANGELOG.md` itself only caught up to v1.15.0 five days after that
version shipped (PR #4) — this file is a downstream reconciliation of that same reconciliation, not an
independent re-derivation. This file is the reconciled, single-source feature record, cross-checked against
the actual files on disk (not just memory) where practical. It supplements — does not replace —
`CHANGELOG.md` (a per-change log whose entry count is no longer re-tallied here after v1.13.2, see §7) and
`HANDOFF-NOTE.md` (the living session hand-off). Treat all four as canonical going forward; keep them in sync.

**True current state: v1.54.0, shipped 2026-09-03** (the responsive baseline — this app's first
width-based breakpoints in `base.css`, stage 3 / PR 7 of the multi-window/multi-tab initiative and
the design spec's priority 3. Two anchors: **960px**, exactly half a 1080p monitor, which is the
scenario `[1.53.0]`'s `VW.windows` makes ordinary rather than hypothetical; and **720px**, the number
four of this app's own pages had already picked for themselves. Seven rules — `flex-wrap:wrap` on the
row-shaped classes (finishing a convention the app had already adopted in 18 of 18 `.search`
definitions but only 8 of 14 `.bar` and 5 of 9 `header`), `min-width:0` on layout-container children,
`overflow-wrap:break-word` so an unbreakable NSN cannot scroll the page sideways, `max-width:100%` on
`img`/`video`/`iframe`, a `.grid2` collapse, a full-width `.side`, and a self-limiting `#vw-toast`
width cap. **CSS only** — no `engine/ui/*.html` is touched and **no real page has been verified in a
resized window yet**; that is PRs 8-11, batched by the home nav's own 6 section groupings, and this
entry must not be read as having done it. The rule that would have made the whole thing inert —
`base.css` loads before every page's inline `<style>`, and a media query adds no specificity — is
handled by weighting each selector deliberately (`:where()` at 0 for the safety nets, `body .x` only
where it must beat a page). `.grid` is deliberately left alone: it means an explicit two-column split
on 5 pages and an `auto-fill` card grid on 6 others, so one blanket rule cannot be right for both.
Verified with a brace/comment audit, a real browser parse of the file (43 top-level rules, both new
media rules intact), and a `getComputedStyle` cascade harness at 1200/960/720/400px showing the block
is byte-for-byte inert above 960px and that 400px has no horizontal overflow where the same markup
without `base.css` overflows to 534px. See §6 item 38).
Immediately prior: v1.53.0, shipped 2026-09-03 (`VW.windows` — the one shared window-opening
path in `shared.js`, stage 2 / PR 5 of the multi-window/multi-tab initiative, built on `[1.51.0]`'s
`VW.channel`: `open(url, opts)` makes the *named* form of `window.open` the ergonomic default, since
passing the same name twice is how a browser natively reuses a window and is the thing every call
site forgets, plus a per-tab registry, a broadcast of every open on the `"windows"` channel, and an
instant toast on open *and* refocus. Verified with 48 checks against the real `shared.js` in a `vm`
sandbox with a mocked `window.open` that records every call — and the test itself checked for
vacuousness by deliberately breaking `shared.js` three ways, which caught a real weakness in an
earlier draft of it. Explicitly **not** proven there: that a real browser reuses a named window,
which only a human in a real browser can confirm. Layout capture/restore is PR 6, not this. `1.52.0` was
reserved up front by a sibling stage-2 PR built in parallel off the same `main`, since merged and
rebased onto here. See §6 item 37).
Immediately prior: v1.52.0, shipped 2026-09-03 (`VW.workspace` — saved, named sets of pages,
`create/list/get/touch` over `{id, name, items: [{page, params}], created, lastOpened, source}`,
stored as one JSON array under a new `viewer_workspaces` localStorage key, every mutation
publishing a deliberately thin notification on `VW.channel` so a second tab re-reads rather than
being pushed a second copy of the truth; verified with 73 real checks across two
`vm.createContext()` sandboxes sharing one `localStorage`, adversarially checked with 6 injected
mutations — item 36). Before that: `VW.channel` — a real, reusable cross-window
publish/subscribe layer in `shared.js`, the first implementation PR of the multi-window/multi-tab
initiative: `BroadcastChannel` primary transport with a `storage`-event fallback for RPS/legacy
browsers, per-(channel,tab) sequence numbers for gap detection, schema versioning, an explicit
oversized-payload guard on the fallback path. Verified with two independent `vm.createContext()`
sandboxes standing in for two real browser tabs, sharing Node's real global `BroadcastChannel`
constructor — production code exercising a real implementation, not a reimplementation of the logic
under test (`[1.51.0]`, item 35). Before that: found by the final, fresh `verify_all.py --snapshot`
pass at the actual release-cut point: `tests/mutate.py`'s restore step rewrote and SHA-verified a mutated
target's *text* but never touched its *derived bytecode cache* — a mutant's `.pyc` could silently outlive
its own verified-clean source restore and leak into whatever imported the module next, including the real
application; `patterns.tm_side()` was provably returning wrong results for two real days before this pass
caught it. Fixed by purging the target's cached `.pyc`/`.pyo` after every restore. A second, unrelated
issue in the same pass — `test_ingest_routes.py`'s real e2e upload check exceeding its hardcoded 15s HTTP
timeout as `_launch()`'s real, by-design synchronous safeguard-snapshot cost has grown with the project's
size — fixed by widening just that check's timeout (`[1.50.0]`, item 34). Before that: a real hang bug
found in the project's own `tests/mutate.py` mutation-testing tool while running `RUN-MUTATION.bat`'s
sequence as part of pre-release verification: a mutant-induced infinite loop survived its own `--timeout`
for 5+ hours on Windows because killing the intermediary `cmd.exe` left the actual hung test process
running as an orphaned grandchild; fixed by killing the whole process tree on timeout instead (`[1.49.0]`,
item 33). Before that: two more `transformers`/`torch`-never-installed self-test failures — the same
env-assumption bug class this session already fixed twice — caught by `VERIFY.bat`'s per-module
self-test loop (a check `verify_all.py --snapshot` doesn't cover) in `engine/vlm.py` and
`engine/pageqa.py`, fixed the same way as `test_pageqa.py` (`[1.48.0]`, item 32). Before that, all
shipped 2026-08-31 → 2026-09-01 as part of a real-world-readiness push following an independent
6-dimension audit: the first real backup restore drill (`[1.44.0]`, item 28); TLS support
for LAN-exposed deployments (`[1.43.0]`, item 27); a stale-running-server visibility fix
(`[1.42.0]`, item 26); a `part.html` failed-request/not-found conflation fix (`[1.41.0]`, item 25); a
degraded-search-signal UI addition (`[1.45.0]`, item 29); accessibility work extended beyond `index.html`
— real contrast fixes, modal focus traps, a generalized (then adversarially-caught-and-fixed) contrast
guard (`[1.46.0]`/`[1.47.0]`, item 30). See each item below and their `CHANGELOG.md` entries for full
detail — the previous version of this very paragraph was itself caught stale (still describing only
`[1.43.0]`) while reconciling `[1.48.0]`, the exact documentation-drift pattern this file's own opening
section describes recurring.

Full detail on the TLS work specifically: a LAN-exposed VIEWER (`--host 0.0.0.0`) had
`VIEWER_ALLOWED_HOSTS`/`VIEWER_AUTH_TOKEN` authentication hardening but crossed the network in plaintext;
fixed with new off-by-default `--tls`/`--cert`/`--key` flags (`engine/viewer_app.py`) wrapping the
server's listening socket in stdlib `ssl.SSLContext` (TLS 1.2+) once at startup, with zero changes to
`Handler` or the bounded-worker semaphore, and a fail-fast (never-falls-back-to-plaintext) refusal when
`--tls` is passed with no cert/key resolvable. New one-time cert CLI `engine/gen_cert.py` (RSA-2048,
10-year self-signed, SAN auto-detects LAN IPs), gated behind an optional `cryptography` import —
matching the existing `sentence-transformers`/`rapidocr-onnxruntime`/`pyzbar` pattern rather than an
`openssl` shell-out (no guaranteed `openssl.exe` on this app's documented Win7/Vista floor) or a
vendored ASN.1/X.509 encoder. `safe_public_base()`
(feeds `/api/qr`) now emits `https://` when TLS is active; the scheme-check reading its output was
made scheme-agnostic to match. New test `test_tls.py`: a real cert, a real TLS handshake (not
mocked) confirming `https://` succeeds, plain `http://` on the same port is rejected, an untrusting
client is rejected, the plain-HTTP path is unaffected when `--tls` is never passed, and `main()`
fails fast on a missing cert. New doc `docs/TLS-LAN-SETUP.md`. Immediately prior: v1.42.0, shipped
2026-08-31 (version-staleness detection — a server left running across a `git pull` looked completely
healthy while quietly running stale code, since nothing recorded when it started or whether its code
still matched disk; fixed with `STARTUP_VERSION`/`STARTUP_TIME` captured once at import, a TTL-cached
on-disk `VERSION=` re-read, new `started_with_version`/`started_at`/`code_changed_since_start` fields
on `/healthz`/`/api/ops`, and a non-dismissible whole-site banner in `shared.js` — see §6 item 26).
Immediately prior: v1.41.0, shipped
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
   **Restore side closed, `[1.44.0]`:** `quick_check` only ever proved the backup file's own internal
   consistency, never that the app layer could actually read it — a real restore drill (copy to
   isolated scratch, start a genuinely separate `viewer_app.py` instance against only the copy, hit
   real endpoints with real queries; see `docs/RESTORE-DRILL-LOG.md`) found that `/api/search` and
   `/api/pmcs` silently return empty results against `viewer-20260830-1348.db` because its
   `schema_version=8` predates the `pages.ocr_confidence` column current app code requires in those
   query paths — a real, previously-unverified gap between "backup passes `quick_check`" and "backup
   is actually restorable into a working app." `part_record`/`part_by_number` were unaffected. Left
   open for a human decision (schema-version gate on restore, or run `fix_schema_version.py` against
   future backups first); no code changed. Original backup + `index/viewer.db` confirmed untouched.
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
27. **`[1.43.0]` — TLS support for LAN-exposed deployments.** Every existing safeguard for a
    LAN-exposed VIEWER (`VIEWER_ALLOWED_HOSTS`/`VIEWER_AUTH_TOKEN` gating `X-Viewer-Token`) protected
    *authentication* over plain HTTP — the token itself, and the search/TM/parts/NSN content it
    protects, still crossed the network unencrypted, readable to anyone else on the same LAN segment.
    Fixed with new, off-by-default `--tls`/`--cert`/`--key` flags (`engine/viewer_app.py`): an
    `ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)` (minimum TLS 1.2) wraps the server's listening socket
    once, in `main()`, right after `_BoundedThreadingHTTPServer` is constructed and before
    `serve_forever()` — `Handler`/`BaseHTTPRequestHandler` and the bounded-worker semaphore are
    completely unmodified. An existing `--host 0.0.0.0` invocation is byte-for-byte unchanged unless
    `--tls` is passed explicitly, and the server fails fast (never binds, never falls back to
    plaintext) if `--tls` is passed with no cert/key resolvable. New one-time cert-minting CLI
    `engine/gen_cert.py` (RSA-2048, 10-year self-signed, SAN auto-detects LAN IPs), gated behind an
    optional `cryptography` import — matching the existing `sentence-transformers`/
    `rapidocr-onnxruntime`/`pyzbar` OPTIONAL-tier pattern rather than an `openssl` shell-out (this
    app's documented Win7/Vista floor has no guaranteed `openssl.exe` on PATH) or a vendored
    ASN.1/X.509 encoder (hand-rolled crypto is riskier to maintain than the field-standard library);
    `cryptography` is needed for this one offline, one-time step only, never by the running server,
    which serves TLS entirely via stdlib `ssl`. `safe_public_base()` (feeds `/api/qr`) now emits
    `https://` when TLS is active; the loopback-detection check reading its output
    (`doc_extractors.py`) was made scheme-agnostic to match. New test `engine/tests/test_tls.py`: a
    real cert, a real `ThreadingHTTPServer` wrapped exactly as `main()` wraps it, a genuine TLS
    handshake (not mocked) confirming `https://` succeeds, plain `http://` on the same port is
    rejected, an untrusting client is rejected, the plain-HTTP path is unaffected when `--tls` is never
    passed, and `main()` fails fast on a missing cert — skips gracefully if `cryptography` isn't
    installed. New doc `docs/TLS-LAN-SETUP.md`: cert generation, per-platform browser-trust steps, and
    an explicit "what this does/doesn't protect against" section. Verified: `verify_all.py --snapshot`
    clean except the two now-documented pre-existing flakes. See `CHANGELOG.md` `[1.43.0]`.
28. **`[1.44.0]` — the first real backup restore drill, performed and documented.** `safeguard.py
    backupdb()`'s `PRAGMA quick_check` (`[1.25.0]`) proves a backup file's SQLite B-tree structure is
    internally consistent — it never opens a connection against the app's own tables, runs a real
    query, or feeds a result through the app layer. This had never actually been tested end-to-end. A
    real drill was performed: `backups\db\viewer-20260830-1348.db` (3.64 GB, SHA-256-verified identical
    after copy) copied — never moved — to an isolated scratch location outside the repo, a genuinely
    separate `viewer_app.py` instance started against only that copy on an unused port, real queries
    hit against `/healthz`, `/api/part_record`, `/api/part_by_number`, `/api/search`, and `/api/pmcs`.
    **Found a real gap**: `/api/search` and `/api/pmcs` both return `200` with silently empty results
    against this backup. Root cause confirmed directly against the restored file: the backup's `pages`
    table predates the `ocr_confidence` column (`schema_version=8`, `healthz`'s own `schema` check
    already said `WARN: schema_version=8 < migrations=12`), and current app code
    (`search_feature.py:_meta_rows()`, its LIKE fallback, and `corpus.py:fts_pages()`, used by
    `pmcs.find()`) unconditionally selects that column, throws, and swallows the error into an empty
    `200` with no error surfaced anywhere. The identical FTS query run directly against the restored
    file (no app layer) returns correct real hits immediately — a pure app/schema-version mismatch, not
    a corpus or FTS problem. `part_record`/`part_by_number` unaffected, served correct real data. **No
    code changed to work around this** — left for a human decision (schema-version gate on restore, or
    run `fix_schema_version.py` against future backups first); see `docs/RESTORE-DRILL-LOG.md` for the
    full request/response record. Drill instance cleanly shut down (Windows required a forceful
    `taskkill /F` — non-forceful didn't stop a console-less Python server within 2s, a platform
    limitation, not a drill defect); original backup and `index/viewer.db` confirmed byte-for-byte
    (size + mtime + SHA-256) untouched throughout. A live free-disk check at drill time found `E:` at
    6.3 GB free, an order of magnitude below an earlier planning pass's ~63 GB estimate — flagged, not
    silently corrected; the drill used `C:` instead (8.69 GB free at the time). See `CHANGELOG.md`
    `[1.44.0]`.
29. **`[1.45.0]` — search UI now shows an honest signal when semantic search is degraded or
    rebuilding.** `hybrid.hybrid_search()` (behind `/api/search_hybrid`, the primary search endpoint
    since `[1.31.0]`) called `embed.search()` but kept only `.get("results")` — it discarded
    `ready`/`stale` entirely, so the only trace of semantic-index health reaching the UI was
    `signals.semantic === 0`, identical whether the index was never built, stale, mid-rebuild, or the
    query just had zero semantic matches. There was also no way at query time to tell "never built"
    apart from "actively rebuilding" — `build_index()` writes `embeddings.progress.json` while a
    rebuild runs, but nothing read it before. **Fixed**: new `embed._build_progress()` /
    `embed.semantic_status(index_dir)` (`engine/embed.py`) read `embeddings.progress.json` for a live
    percent-complete and return one honest, query-independent state —
    `ready`/`never_built`/`rebuilding`/`stale`; `hybrid_search()` (`engine/hybrid.py`) forwards it as a
    new top-level `semantic_status` field, alongside the unchanged `signals` block. New
    `renderSemanticStatus(d, q)` in `engine/ui/index.html`, called from `runSearch()` next to the
    existing `renderSearchHints()` and styled identically to its quiet `.searchhints` card
    (`afterbegin` into `#results`, `var(--panel)`/`var(--line)`/`var(--sub)`, no `role="alert"`) —
    deliberately **not** `shared.js`'s `_staleBanner()` treatment (fixed-position, red,
    non-dismissible), which stays reserved for the unrelated code-version-mismatch emergency. Shown
    only when `semantic_status.state !== "ready"` and the search actually returned keyword results, so
    it never displaces the "No matches" empty state. Dismissible per-state via
    `sessionStorage['vw-semstatus-dismissed-<state>']` so dismissing one state doesn't suppress a later
    different one. Four distinct copy strings, one per real state (nothing renders when `ready`):
    `never_built` ("🧩 Semantic (meaning-based) search hasn't been set up on this install yet — results
    below are keyword matches only."), `rebuilding` ("⏳ Semantic search is building its index (N%
    complete) — results may improve once it finishes."), `stale` ("🔄 Semantic search's index is out of
    date and needs a rebuild — results below are keyword matches only."). **Verified live, not just
    static HTML**: this session's own background embeddings rebuild (`embed_rebuild_v2.py`, already
    running per house rules, confirmed via `tasklist`/`embeddings.progress.json` before touching
    anything) put the real repo in a genuine `rebuilding` state throughout — `embed.semantic_status()`
    called directly against the real `index/` dir returned `{"state": "rebuilding", "progress":
    {"percent": 25, "rows_done": 505000, "limit": 2000000}}`; a real second `viewer_app.py` instance
    (`--db index/viewer.db --port 18901`, read-only) hit live `/api/search_hybrid?q=brake` and the
    response's top-level `semantic_status` field matched, progressing to `26%` moments later.
    `never_built`/`stale` verified the same way against isolated scratch index directories outside the
    repo (one empty; one with `embeddings.npy`/`embeddings_ids.tsv` copied over but no
    `embeddings.meta.json`/`embeddings.progress.json`) — real function calls against real files, not
    simulated. Test server killed by PID matched via `netstat` to its own port only; the pre-existing
    background rebuild was never touched. Verified: `verify_all.py --snapshot` clean except the three
    now-documented pre-existing flakes. See `CHANGELOG.md` `[1.45.0]`.
30. **`[1.46.0]` — accessibility work extended beyond `index.html`: real contrast fixes, modal focus
    traps, a generalized contrast guard.** A research pass re-verified `[1.29.0]`'s own accessibility
    disclosure against the real files and found a correction to its numbers: `status.html`'s `.tag.ok`
    was carried on prior lists as a 3.10:1 WCAG failure, but that figure is base.css's un-overridden
    `--grn` — this page's own local `--grn:#2f9d63` override actually measures 4.56:1, a genuine pass,
    left untouched here. `demo.html`'s full local `:root` token override (shadowing all 12 of
    base.css's tokens, plus `--grn2`, which base.css lacked) is gone — every value matched base.css
    exactly except `--red` (`#c4585a` vs. base's `#e0564f`), the direct cause of a real
    `.warn .n` contrast failure (3.94:1 → 6.13:1 fixed via the existing `--red-tx` token). Two more
    confirmed real failures fixed the same way: `status.html` `.tag.bad` (4.18:1 → 5.65:1) and
    `index.html`'s 2 remaining inline `color:var(--red)` stragglers (4.53:1, a narrow existing pass,
    swapped to `--red-tx` anyway for consistency, now 6.13:1). `schematics.html`/`threed.html`'s gate
    modals now carry `role="dialog" aria-modal="true"` + `VW.trapFocus()`, which required generalizing
    `shared.js`'s `trapFocus()` itself: both pages toggle their gate via `classList.add/remove('on')`
    against a CSS rule, never touching the inline `style` attribute `trapFocus()` originally watched —
    attaching it as-is would have silently never trapped focus. `isVisible()` now reads
    `getComputedStyle()`, the `MutationObserver` now watches both `style` and `class`, and Escape
    detects which convention is live before closing — verified live in a real browser for both pages,
    `index.html`'s 5 existing modals confirmed unaffected. `verify_ui.py`'s WCAG guard rewritten from a
    3-pair hardcoded list (that only ever opened `base.css`/`index.html`) to a real per-page scan
    across all 48 `ui/*.html` pages with cascade-aware token resolution (each page's own `:root{}`
    override layered on `base.css`'s) — exactly the gap that let `status.html`'s real failure ship
    invisibly. The new scan itself caught 2 more previously-unknown real failures while being built
    (`index.html`'s `.sheetprev .e`, `measures.html`'s `.em .tagx`, both fixed) and one bug in the
    scanner's own logic (a descendant selector's self-declared background was being ignored in favor
    of its ancestor's, caught and fixed before landing). Baseline ARIA (`role="main"`, `aria-label`s,
    `aria-live` result regions, dialog semantics) landed on 10 pages this pass — `collections`,
    `threed`, `status`, `schematics`, `verify`, `jobcard`, `part`, `visual`, `procedure`, `demo` —
    scoped from real (thin) click-analytics traffic plus the pages already open for the contrast/modal
    work. **Honestly left open, same disclosure convention as `[1.29.0]`**: 31 pages still carry zero
    ARIA (named in full in `CHANGELOG.md` `[1.46.0]`, including `review.html` — omitted from every
    one of the 5 canonical docs' lists in the original pass and restored by a follow-up adversarial
    fix); `cadtex_test.html` confirmed unreachable through any route and excluded on that basis.
    See `CHANGELOG.md` `[1.46.0]`.
31. **`[1.47.0]` — adversarial verification of `[1.46.0]` found 3 real, confirmed, blocking issues;
    all fixed.** (1) `verify_ui.py`'s "generalized" contrast guard's `_is_pure_class_selector()` regex
    had no `.` in its character class, so it could never match a compound-class token like `.tag.bad`
    — `_parse_css_rules()` gated both the single- and compound-selector branches behind that one
    check, so every compound-selector rule on every page was silently discarded before parsing,
    directly contradicting `[1.46.0]`'s claim of closing the gap that let `status.html`'s real
    `.tag.bad` failure ship invisibly. Confirmed via a real adversarial test (injecting
    `.injectedbad.contrast{color:#333333;background:#222222}` into `status.html` — not caught before
    the fix); fixed (regex now matches one-or-more `.class` segments) and re-verified the same way
    (pair count 146→147, correctly flagged `FAIL -- 1.26:1`, injection then fully reverted). Real
    corrected scan state: 146 pairs, 117 OK, 0 FAIL, 29 SKIP. (2) The zero-ARIA disclosure list said
    "27 pages" while enumerating 30 names, and omitted `review.html` (genuinely zero-ARIA, untouched
    by `[1.46.0]`) from every one of the 5 canonical docs' lists — recounted directly from
    `ui/*.html`; the real count is 31, list corrected everywhere. (3) `[1.46.0]`'s "61/61 GREEN, 0
    failures... no flakes needed this run" claim was false — three re-runs this pass never once
    reproduced 0 flakes: the authoritative run (no concurrent edits) got 60/61 (`test_routes.py`'s
    pre-existing `/api/ask` timeout, reproduced standalone), an earlier run flagged `test_http.py`'s
    equally pre-existing `/api/pageqa` timeout instead — corrected to report the real results
    honestly. See `CHANGELOG.md` `[1.47.0]`.
32. **`[1.48.0]` — two more `transformers`/`torch`-never-installed self-test failures, the exact env-
    assumption bug class this session already fixed twice.** `VERIFY.bat`'s per-module self-test loop
    (~68 modules, `python -B <module>.py`) — a check `verify_all.py --snapshot` never runs — surfaced
    `engine/vlm.py`'s and `engine/pageqa.py`'s own `__main__` self-tests hardcoding the same stale
    assumption `test_routes.py`/`test_pageqa.py` already hardcoded and had fixed earlier this session.
    `vlm.py`'s self-test called `ask()`/`ground()` with no explicit backend, expecting `_load_backend()`
    to find nothing; once `vlm_backend.py`'s default Florence-2 backend became importable (a side effect
    of `sentence-transformers` pulling in `transformers`/`torch`), `available` flipped from the expected
    `False` to `True`, breaking the hardcoded `assert ... is False` calls. `pageqa.py`'s failure was a
    subtler cascade: `pageqa.available()` is `vlm.available() and _gpu_tier()`, so once `vlm.available()`
    flipped, that gate silently passed on this real GPU-equipped dev machine and fell through to a real
    page-render attempt for a doc/page that doesn't exist in the self-test's fixture-free context,
    surfacing as a confusing "could not render doc 1 page 1" note instead of the intended "no backend"
    one. Both fixed by forcing `VIEWER_VLM` to a genuinely-nonexistent module name before the "no
    backend" assertions, making `_load_backend()`'s `__import__()` fail deterministically regardless of
    what happens to be installed — the identical fix already applied to `test_pageqa.py`. **Not found by
    any test suite until now** — `verify_all.py --snapshot` (run dozens of times across this session)
    never exercises these two modules' own `__main__` self-test blocks, only `VERIFY.bat`'s dedicated
    per-module self-test loop does — a concrete argument for keeping that gate in the pre-release
    checklist rather than treating `verify_all.py --snapshot` alone as sufficient. Verified: both
    self-tests pass cleanly post-fix, the full 68-module self-test loop is clean, `verify_all.py
    --snapshot` clean per the now-3 documented pre-existing flakes. See `CHANGELOG.md` `[1.48.0]`.
33. **`[1.49.0]` — `tests/mutate.py` could hang for hours past its own `--timeout`, on Windows.** Running
    `RUN-MUTATION.bat`'s 7-step sequence as direct commands (pre-release verification) hit a mutant in
    `procedure_feature.py`'s blank-line-skip branch (`i += 1` → `i -= 1`) that puts `parse_procedure()`
    into a genuine infinite loop — Python's negative-index wraparound means it never raises, it just
    walks `i` backward forever. `run_test()`'s `subprocess.run(cmd, shell=True, timeout=timeout)` is
    supposed to kill anything that takes longer than `--timeout`; on Windows, `shell=True` spawns an
    intermediary `cmd.exe`, and `TimeoutExpired`'s kill only reaches that intermediary — the real hung
    test process survives as an orphaned grandchild holding the inherited stdout pipe open, so
    `communicate()`'s wait for pipe-EOF never returns and the timeout mechanism never actually fires.
    Hung silently for 5+ hours (zero output, zero crash) before being caught purely because the wall-clock
    made no sense. A second run (`rps.py`, step 4/7) was killed pre-emptively before it could repeat the
    same failure, once the pattern was recognized. **Fixed**: `run_test()` now launches via `Popen`
    directly and, on timeout, kills the whole process tree (`taskkill /F /T /PID <pid>` on Windows,
    `Popen.kill()` elsewhere) instead of the single intermediary process. Verified directly: a
    deliberately-hanging grandchild (`python -c "time.sleep(30)"` run through a shell wrapper) now times
    out in ~3s under a 3s cap — previously this exact shape of command hung indefinitely; normal pass/fail
    exit codes unaffected (checked against both `sys.exit(0)` and `sys.exit(1)`); a full real run against
    `patterns.py` still restores the source and passes SHA-256 verification afterward. Both source files
    left mutated on disk mid-run by the hang (`procedure_feature.py`, `rps.py`) were restored from their
    `.orig` backups before anything else touched them. This is a defect in test tooling
    `VERIFY.bat`/`RUN-ALL-VERIFY.bat` depend on, not in the application — filed as its own fix rather than
    folded into the mutation-testing pass it was found during. See `CHANGELOG.md` `[1.49.0]`.
34. **`[1.50.0]` — `tests/mutate.py` could poison the real Python bytecode cache, silently, for days.**
    Found by the final, fresh `verify_all.py --snapshot` pass at the actual release-cut point — worse than
    item 33's hang, since nothing crashed or timed out to flag it: `test_patterns.py` failed 3 real-
    looking checks against `patterns.tm_side("TM 9-2320-280-10")` (expected `operator=True,
    confidence="high"`; got `operator=False, mechanic=True, confidence="low"`) on a file `git diff` showed
    byte-identical to its own committed source. Recompiling `tm_side()`'s own source text fresh
    (`exec(compile(inspect.getsource(...)))`) gave the correct answer while the already-loaded module gave
    the wrong one, in the same process, back to back — proving the discrepancy lived in compiled
    bytecode, not source. **Root cause**: `mutate.py`'s restore step only ever rewrote and SHA-256-verified
    the target's *source text*; it never touched the *derived bytecode cache* a subprocess `import` during
    a mutant's test window leaves behind in `__pycache__/`, keyed by the source file's mtime+size. The
    mutate/restore cycle rewrites the same file, often at the same size, fast enough for Windows' mtime
    resolution to alias a mutant's cached `.pyc` onto the restored original — so the cache silently
    outlives the "restored, verified" source it no longer matches, and every later process that imports
    the module (another test run, `VERIFY.bat`, or **the actual running application**) inherits the
    mutant's logic instead of the real one, invisibly, for as long as that stale `.pyc` sits there. This
    one specifically dated back to item 33's own `[1.49.0]` mutation-testing investigation on
    2026-09-01 — undetected for two real days. **Fixed**: `mutate.py` now purges the target's cached
    `.pyc`/`.pyo` immediately after every restore — both after each individual mutant (the one that
    actually matters: a hard-killed run, like item 33's own incident, skips the final cleanup entirely, so
    only the per-mutant purge is reliable against exactly the failure mode that caused this) and again in
    the final cleanup. Verified: re-ran mutation testing against `patterns.py` (15 mutants) with the fix
    in place, confirmed no `.pyc` was left in `__pycache__/` afterward, and `tm_side()` — checked directly
    and via a full `test_patterns.py` run — returned the correct result immediately, with no manual cache
    purge needed. Remediation for the poisoning already in place: every `__pycache__/` under `engine/` was
    purged as an emergency measure before the fix landed, confirmed by re-running every test file whose
    module was a mutation-testing target this session (`test_patterns.py`, `test_procedure.py`,
    `test_features.py`, `test_jobcard.py`, `test_property_fuzz.py`) — all clean. A second, unrelated
    failure surfaced in the same verification pass: `test_ingest_routes.py`'s real, unmocked end-to-end
    upload check (`_launch()` takes a genuine synchronous `safeguard.snapshot()` of every critical
    engine/docs/diagram file before it spawns the ingest subprocess and returns) now measures ~24.5s
    standalone — this project has accumulated hundreds of tracked source/doc/diagram files over its life,
    and that real, by-design cost has grown past the test's hardcoded 15s HTTP client timeout. Reproduced
    the underlying upload pipeline by hand (real subprocess, real migration, real crawl) and confirmed it
    works correctly and completes in ~1-2s once actually running — the test's timeout was simply too
    tight for a call that legitimately includes a scanning-cost-scales-with-project-size safety snapshot.
    Fixed by giving `_req()` an explicit `timeout=` parameter (default unchanged at 15s for every other
    call) and passing a wider one (60s) for the two checks that go through `_launch()`. Verified: both
    checks now pass cleanly, twice in a row. See `CHANGELOG.md` `[1.50.0]`.
35. **`[1.51.0]` — `VW.channel`: cross-window/cross-tab publish/subscribe (multi-window support,
    PR 1/18).** First implementation PR of the multi-window/multi-tab initiative scoped in
    `docs/superpowers/specs/2026-09-03-multi-window-tabs-design.md` /
    `...-plan.md`. A real, reusable cross-window sync layer in `shared.js`, built deep from the start
    per the design spec's expanded scope: `BroadcastChannel` primary transport, automatic
    `storage`-event fallback for the older/RPS-mode browsers this codebase still supports where
    `BroadcastChannel` is undefined — a subscriber never needs to know or care which transport
    delivered a message. Ordering via a `seq` counter scoped to (channel name, publishing tab)
    — deliberately not a global cross-tab sequence, since no single source of truth exists for that
    without real coordination overkill — lets a subscriber detect it missed a message from a
    specific other tab (`meta.gap === true`), which matters most on the fallback path: two rapid
    writes from one tab can coalesce into a single `storage` event elsewhere, since the event only
    ever reflects the current value at dispatch time. Schema versioning via a `v` field: a mismatch
    is silently ignored, never crashes a subscriber running older/newer code. An explicit size guard
    on the fallback path (`localStorage` shares one ~5-10MB origin-wide quota with everything else
    already stored there) throws a clear, immediate error on an oversized payload rather than
    letting a raw `QuotaExceededError` or a partially-written shared key surface downstream —
    `BroadcastChannel` has no such limit. **Verified with a genuinely real test, not a
    reimplementation of the logic under test**: `engine/tests/js/test_channel_node.js` uses two
    independent `vm.createContext()` sandboxes standing in for two real browser tabs — each gets its
    own window/document/localStorage, so requiring `shared.js` into each gives fully independent
    closure state (`_channelTabId`, `_channelSeq`, `_channelLastSeen`, `_channelSubs`), exactly like
    two real tabs share nothing but the browser's `BroadcastChannel` registry, while both sandboxes
    are handed the SAME `BroadcastChannel` constructor reference (Node has a real global
    implementation) — this is production code exercising a real `BroadcastChannel`, not a mock
    standing in for one. 16 checks: cross-tab delivery/ordering/no-self-echo over `BroadcastChannel`;
    the `storage`-event fallback path (Node has no real cross-context `storage`-event IPC to rely on,
    so the test captures whatever listener `shared.js` itself registers via
    `window.addEventListener("storage", ...)` and invokes it directly with the same envelope shape a
    real event would carry — everything the listener actually does with that envelope is the real
    code, unmocked, only the OS-level delivery mechanism is stood in for); gap detection on a
    simulated coalesced write; silent version-mismatch handling; the oversized-payload guard;
    malformed-JSON safety. Along the way, caught and fixed two real `rps_lint` false positives:
    backticks and an ellipsis used as plain-English punctuation inside the new doc comments, which
    the linter's blunt text-level regex scan doesn't distinguish from actual template-literal/
    spread-rest syntax — fixed by rewording the comments, matching every other comment in this file's
    existing plain-text style. No UI changes yet — nothing calls `VW.channel` outside its own tests.
    `VW.workspace`/`VW.windows` and the features that actually consume this (D, then B/F/C/G) follow
    in subsequent PRs per the plan. See `CHANGELOG.md` `[1.51.0]`.
36. **`[1.52.0]` — `VW.workspace`: saved, named sets of pages — CRUD (multi-window support,
    PR 2/18).** Stage 2 of the same plan, the first consumer of `[1.51.0]`'s `VW.channel`. A
    workspace is the data behind "reopen everything I had open for this job":
    `VW.workspace.create(name, items) -> id` (or `null` when storage refused the write — a caller
    must not treat that as "probably fine"; it is the difference between a UI that can say
    "couldn't save that" and one that lies), `.list()` in creation order, `.get(id)`, and
    `.touch(id)` moving only `lastOpened`. The record is exactly what the design spec names:
    `{id, name, items: [{page, params}], created, lastOpened, source}`, with `lastOpened` equal to
    `created` on a fresh workspace on purpose — a never-reopened workspace then sorts sanely by
    `lastOpened` alone with no null handling in every consumer, and "never reopened since it was
    made" stays detectable as `lastOpened === created`. CRUD **only**: export/import (PR 3) and the
    built-in templates (PR 4) build on this exact record shape and storage key and are deliberately
    not here. The optional third `source` argument (defaulting to `"manual"`, accepting only
    `"template"`) is present now rather than bolted on in PR 4, because the spec's record carries
    `source` from the start and without it the field would be a constant with a misleading name.
    **Storage shape, a real decision documented in the code rather than left implicit**: the whole
    set is one JSON *array* under a new `viewer_workspaces` key, not an id-keyed object — `list()`
    is by far the dominant read (the saved-workspaces UI this exists to feed repaints the entire
    set whenever anything changes) and an array preserves a stable creation order for free, where
    an id-keyed object would need a sort on every `list()` for the same guarantee; `get(id)`'s
    linear scan is the right trade for a handful of entries a person typed names for, not thousands
    of machine-generated rows; and an array is already the exact shape PR 3 will serialize.
    **Every mutation publishes on `VW.channel`, with a deliberately thin payload**: `localStorage`
    is already shared across every tab on this origin for free, so a second tab does not need the
    data pushed to it — it needs to be *told* something changed so it can re-read and repaint,
    which is the same philosophy the design spec describes for D (Bench sync): the channel is a
    notification layer over storage that is already shared, never a second copy of the truth. The
    payload is only `{action, id, name, at}` — enough to repaint or highlight one row, small enough
    that the channel's storage-fallback size guard can never fire on it, incapable of going stale
    against the real stored value. The write happens first and the notification second, so a tab
    reacting to a notification always reads an already-committed value; read-only calls publish
    nothing, since there is nothing to react to and a broadcasting read would be a live-lock
    waiting to happen the moment a subscriber repaints by calling `list()`. Defensive throughout:
    private-browsing profiles and full quotas both throw on plain `localStorage` access so every
    read and write is wrapped; a corrupt or hand-edited stored value degrades to an empty/filtered
    view instead of throwing; a read never rewrites storage, so a corrupt value stays inspectable
    in devtools rather than being destroyed by the act of looking at it; and ids (a base-36
    timestamp plus 6 random base-36 characters) are checked against the ids actually stored and
    regenerated on a hit, so a duplicate is impossible rather than merely unlikely, with a bounded
    loop and a deterministic final fallback so a pathological environment can neither spin forever
    nor return a taken id. **Verified with a genuinely real test, not a reimplementation of the
    logic under test**: `engine/tests/js/test_workspace_node.js`, 73 checks, all passing. Every
    assertion goes through the real exported functions loaded from the real `shared.js`, and every
    persisted-state check parses the raw `viewer_workspaces` value out of the store directly rather
    than trusting the API to describe itself. Two `vm.createContext()` sandboxes stand in for two
    browser tabs **sharing one `localStorage` object** — which is exactly what two tabs on one
    origin have — so the design's central claim is exercised end to end rather than asserted: tab A
    creates a workspace, tab B receives the notification over Node's real global
    `BroadcastChannel`, and tab B then really does find the workspace through its own `list()`. The
    sandbox's `Date` is a controllable clock (`shared.js` only ever calls `Date.now()`), which is
    what makes "touch updates `lastOpened`" a real observable change rather than a check that
    passes vacuously when both timestamps land in the same millisecond. Also covered: the exact
    stored field set with no extras, item/param normalization, name/source fallbacks, id uniqueness
    under a frozen clock *and* a constant `Math.random`, four shapes of corrupt stored value,
    storage that refuses reads and storage that refuses writes, and the same notification over the
    storage-event fallback transport with `BroadcastChannel` hidden. **Adversarially checked** by
    injecting 6 real mutations into `shared.js` and re-running: 5 caught (touch not moving
    `lastOpened`, create not publishing, the read filter dropped, param values not coerced, a
    refused write reported as success); the 6th — dropping the id generator's random suffix —
    survives because the collision-regeneration guard independently preserves the only property
    under contract (uniqueness), producing `wsmf29czk0` / `wsmf29czk0-1` instead of colliding.
    Confirmed directly rather than assumed, and reported as the equivalent mutant it is rather than
    papered over. No UI changes yet — nothing calls `VW.workspace` outside its own tests. See
    `CHANGELOG.md` `[1.52.0]`.
37. **`[1.53.0]` — `VW.windows`: one window-opening path, named reuse, instant toast (multi-window
    support, PR 5/18).** Stage 2 of the same plan, built on item 35's `VW.channel`; layout
    capture/restore is explicitly PR 6, deliberately not this one. (`1.52.0` was reserved up front by the
    sibling stage-2 PR in item 36 — `VW.workspace` CRUD — built in parallel off the same `main`,
    so this branch took the next number rather than race for one; that sibling has since merged and
    this work was rebased onto it, the real `shared.js` conflict — both PRs add a block just above
    the `VW` export object — resolved by keeping both, `VW.workspace` then `VW.windows`, with both
    suites re-run green afterward.) **Why it exists when `window.open()` is already one
    line:** passing the same *second* argument (the window name) twice is how a browser natively
    reuses a window instead of stacking up a fresh one per click — that behavior is free, and it is
    also the thing every call site forgets, because nothing about writing `window.open(url)`
    suggests you were supposed to name anything. A technician tapping the same "pop out the torque
    table" affordance four times across one job ends up with four identical windows fighting over
    the second monitor. `VW.windows.open(url, opts)` makes the named form the ergonomic default (a
    caller passes `opts.name` once and stops thinking about reuse) and layers on three things a bare
    call site could not sensibly do for itself: a per-tab **registry** (`VW.windows.registry()`
    reports `[{name, url}, ...]` — the hook PR 6 extends with real `screenX`/`screenY`/`outerWidth`/
    `outerHeight` bounds); a **broadcast** of every successful open (`{event, name, url, count}`) on
    `VW.channel`'s `"windows"` channel, plumbing for a future cross-tab "N windows open" that
    nothing renders yet; and an instant **toast** on open *and* on refocus, reusing `shared.js`'s
    existing `toast()` rather than inventing another one — the design spec's priority 2 ("snappy
    UI: one window-opening path, named-window reuse, instant toast feedback"), aimed squarely at the
    reuse case, where on some window managers the reused window comes forward *behind* the current
    one and the click otherwise looks like it did nothing at all. Distinct messages for the two
    outcomes ("Opened in a new window" vs. "Already open — switched to that window") make which one
    happened visible. **Limits documented in the code rather than left to be discovered later:** the
    registry is per tab and in memory — it lists what *this* tab opened during *this* page load, not
    every VIEWER window on the machine, which is exactly why each open is broadcast (a cross-tab view
    has to be assembled from the messages, never read off one tab's registry); it is a best-effort
    mirror of the browser's own named-window table rather than the truth, since the browser reuses a
    named window whether or not this registry knows about it (so after a reload a reuse can be
    reported as a fresh open), with handles reporting `closed === true` pruned on every `registry()`
    call and before every reuse decision, which covers the common case — the user closed the pop-out
    — exactly; without `opts.name` there is no reuse and no tracking at all, because an unnamed
    `window.open()` returns a fresh anonymous window every call and nothing can ever look it up
    again, so such a call opens and toasts (a click must always visibly register) but never enters
    the registry; no window-features argument is ever passed on this path, since supplying one turns
    what the browser would have opened as an ordinary tab into a stripped chrome-less popup,
    overriding the user's own new-window preference (PR 6's `restoreLayout()` is the one place that
    will legitimately pass explicit bounds, because there the user asked for exactly that); and a
    blocked (`null`) or outright-throwing `window.open` returns `null` and skips the toast, the
    registry write *and* the broadcast alike, since none of them may claim a window opened when none
    did. **Verified with 48 real checks**: `engine/tests/js/test_windows_node.js` loads the real
    `shared.js` into a `vm.createContext()` sandbox (the same document/localStorage shimming approach
    `test_channel_node.js` uses) with a **mocked `window.open`** that records every call it receives
    — url, name, argument count — and hands back a fake window handle, then asserts on what the
    production `VW.windows.open()`/`registry()` code actually did with it: same name twice produces
    ONE registry entry while still really calling `window.open` a second time (the browser does the
    reuse; skipping the call would leave the existing window untouched and still sitting behind
    whatever is in front of it), different names produce separate entries, a new url on an existing
    name updates the tracked url, an unnamed open neither throws nor pollutes the registry but still
    toasts, the popup-blocked and `window.open`-throws paths return `null` with no toast, no entry
    and no broadcast, a closed window is pruned and re-opening that name is a fresh open rather than
    a reuse, and the returned registry is a copy that cannot be mutated back into the real one. The
    broadcast half is **not** mocked at all: a second, independent sandbox subscribes over Node's
    real global `BroadcastChannel` and the full 6-event sequence is asserted end to end. The test was
    itself checked for vacuousness by deliberately breaking `shared.js` three times and confirming
    the right checks flipped to FAIL — keying the registry by `name + Math.random()` (10 FAIL,
    including "same name twice produces ONE registry entry, not two"), moving the `toast()` above the
    popup-blocked guard (6 FAIL), and disabling the `channelPublish` call (2 FAIL). The second of
    those **caught a real weakness in an earlier draft of the test**: it asserted "a blocked open
    does not toast" by comparing the toast text before and after, and the deliberately-broken code
    passed anyway, because the text it wrongly wrote happened to equal the text already there. The
    fake DOM now exposes `textContent` as an accessor that logs every *write*, so the test counts
    real DOM writes instead of comparing values — and the same mutation then failed correctly.
    **What this cannot prove, stated plainly rather than glossed over** (the same framing the design
    spec uses for every other real-hardware-only behavior): whether a real browser genuinely reuses a
    window when the same name is passed twice. That is browser behavior, not this codebase's —
    `shared.js`'s entire reuse strategy is to hand the name to `window.open` and let the browser's own
    named-window table do the work, and Node has no `window.open` to be right or wrong about it. The
    mock mirrors that table because it is the semantic the production code is written against, but a
    mock agreeing with the code it was written to exercise proves nothing about Chrome or Firefox.
    The owed manual check: open a pop-out twice in a real browser, confirm ONE window results. Real
    popup-blocker behavior and real raise-to-front/focus behavior are equally out of reach here.
    `rps_lint` caught one ES5 false positive on the way through — the plain-English word "let"
    followed by a space inside a new doc comment, which the linter's blunt text-level regex scan
    cannot distinguish from a real `let` declaration, the same class item 35 hit twice — reworded
    rather than suppressed. No UI changes: nothing calls `VW.windows` outside its own tests yet;
    A1 (home-nav pop-out links, PR 12), A2 (`popoutControl()`, PR 14) and B (curated launcher, PR 15)
    are the first real consumers. See `CHANGELOG.md` `[1.53.0]`.

38. **`[1.54.0]` — responsive baseline: this app's first shared width breakpoints in `base.css`
    (multi-window support, PR 7 of 25).** Stage 3 of
    `docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md`, and the design spec's priority 3
    ("a real, verified responsive baseline"). **Scope, stated first because it is the thing most
    likely to be misread: CSS only.** No `engine/ui/*.html` file is touched, and **not one real page
    has been opened in a resized window and checked** — that is PRs 8-11, batched by the home nav's
    own 6 section groupings, where actual overflow and collision get found and fixed page by page.
    This item is the shared foundation those four inherit and nothing more. (`1.55.0` and `1.56.0`
    are reserved by two sibling PRs built in parallel off the same `main`, so this branch took
    `1.54.0` up front rather than race for a number — the convention items 36/37 already used.)
    **The premise was verified, not taken from the spec:** before this change `base.css` contained
    exactly three media queries and not one of them was width-based (`pointer:coarse`, `print`,
    `prefers-reduced-motion`), so the single sheet all 48 pages `<link>` contributed literally
    nothing to a narrow window; meanwhile eight pages had grown their own ad-hoc width breakpoints
    at seven different numbers (1280/920/820/780/760/720/620) and the other forty had none at all.
    **Two anchors, neither invented.** 960px is exactly half of a 1080p monitor — the concrete
    scenario the spec names, and the one item 37's `VW.windows` turns from hypothetical into
    ordinary, since the entire point of a pop-out is reading `torque.html` at ~960 CSS px instead of
    ~1900. 720px — a docked or quarter-width window — is the number four of this app's own pages
    already chose for themselves (`help`/`jobcard`/`solve` at 720-760, `part` at 760), so the shared
    sheet agrees with the pages instead of fighting them. **Seven rules.** One outside any
    breakpoint: `#vw-toast{max-width:calc(100vw - 24px)}`, deliberately unbreakpointed because it is
    `base.css`'s own chrome (no page defines it) and the constraint is self-limiting — and because
    item 37 made toasts routine on exactly this path ("Already open — switched to that window" fires
    on every pop-out reuse) with the longest of those strings wider than a narrow popped-out window.
    At ≤960px: `flex-wrap:wrap` on `header,.bar,.row,.cols,.search,.chips,.toolbar,.tools,.tabs`,
    which is **not a new convention but this app's own, finished** — counted across the page family,
    `.search` already declares it in 18 of its 18 flex definitions, `.toolbar` 2/2, `.chips` 2/2,
    `.cols` 1/1, `.tools` 1/1, `.row` 7/8, `.bar` 8/14, `header` 5/9, `.tabs` 0/1, and the pages that
    forgot are precisely the ones that break when squeezed (`flex-wrap` is inert on a non-flex
    element, and several pages reuse `.bar` as a progress meter, so this only acts where a row would
    otherwise push the page sideways; `.wrap` is excluded because `circuitlab.html`/`deepzoom.html`
    use it as a full-height column app shell where wrapping means something);
    `:where(.grid,.grid2,.cards,.tiles,.cols,.bar,.row,.search)>*{min-width:0}`, generalising a
    lesson `index.html` had already learned locally *twice* (its
    `grid-template-columns:minmax(0,1fr) 420px` carries the comment "the results column can never
    force sideways overflow", and its own 920px block sets `.vside{min-width:0}`);
    `body{overflow-wrap:break-word}`, so a long unbreakable NSN/CAGE/part number/file path — what
    this app is made of — wraps instead of forcing a horizontal scrollbar, an honest trade in which
    a mid-string break is worse to read than an unbroken number and better than a sideways-scrolling
    page; `:where(img,video,iframe){max-width:100%}` (`svg`/`canvas` deliberately excluded, since the
    3-D/deep-zoom/circuit stages size theirs by script); and `body .grid2{grid-template-columns:1fr}`,
    the one class in this app actually *named* for being a two-column split. At ≤720px:
    `body .side{width:100%;max-width:none}` — `procedure.html`'s `.side{width:420px;max-width:46vw}`
    beside `.steps{min-width:340px}` is the app's only `.side`-named split, and below roughly 740px
    the two stop fitting, the wrapping `.cols` row drops the rail underneath, and it lands there
    still only ~330px wide, worse than either layout on its own. **The thing that would have made
    this entire PR inert, and how it was avoided:** `base.css` is `<link>`ed in `<head>` *before*
    every page's inline `<style>`, and a media query adds no specificity, so a plain
    `@media(max-width:960px){.grid2{...}}` written here **loses** to `part.html`'s later,
    equal-specificity `.grid2{grid-template-columns:1fr 1fr}` — the rule would parse, match, and be
    overridden, leaving a sheet that looks correct and does nothing. Each rule therefore picks its
    weight on purpose: `:where(...)` (specificity 0) for the safety nets any page must stay free to
    override, a bare element/class selector where no page declares that property at all, and
    `body .x` only where the rule genuinely has to beat a page's own declaration. **Deliberately not
    done, and worth recording because it is the obvious move and it would have been wrong:** `.grid`
    is not collapsed to a single column. It means two different things across this app — an explicit
    two-column `1fr 1fr` split on 5 pages (`dossier`/`help`/`jobcard`/`solve`/`exploded`, every one
    of which already collapses itself at 720-820px) and a `repeat(auto-fill,minmax(150-320px,1fr))`
    card grid on 6 others (`collections`/`coverage`/`schematics`/`threed`/`partdiff`/`demo`) that
    already reflows correctly — so a blanket collapse fixes nothing on the first group and turns the
    second into a column of 900px-wide cards. Also considered and dropped: tightening `.wrap`'s
    horizontal padding, since 2 of the 44 pages using `.wrap` use it as a full-viewport app shell
    with no padding at all, and a blanket override would silently change those two to buy ~12px on
    the other 42. **Verified three ways, there being no CSS linter in this repo.** (1) A brace and
    comment audit with comments stripped: `{` 57 = `}` 57, nesting depth never negative, final depth
    0, `/*` 31 = `*/` 31. (2) A real browser made to *parse* the file — all of `base.css` inlined into
    a `<style>` and read back through `document.styleSheets[…].cssRules`, which silently drops
    anything it cannot parse: 43 top-level rules, and all five media rules present with every inner
    rule intact (`(pointer: coarse)` 4, `print` 1, `(prefers-reduced-motion: reduce)` 1,
    `(max-width: 960px)` 5, `(max-width: 720px)` 1) — nothing dropped, `:where()` included. (3) A
    cascade harness reproducing the real load order (this `base.css` in one `<style>`, then a second
    holding verbatim copies of `part.html`'s `.grid2`, `procedure.html`'s `.cols`/`.steps`/`.side`,
    `solve.html`'s `header`/`.bar` and `collections.html`'s `.grid`), served over HTTP and measured
    with `getComputedStyle` at 1200/960/720/400px. It proves three things: at 1200px **every value is
    byte-identical to what it was before this change** (the block is completely inert above 960px —
    R1); at 960px the `auto-fill` `.grid` is still 3 columns and `.steps` still holds its intentional
    `min-width:340px`, i.e. the specificity-0 `:where()` choice really does let pages win where they
    should, while `.grid2` and `.side` show the `body .` selectors really do beat a page's later
    declaration where they must; and at 400px `documentElement.scrollWidth` (400) equals
    `clientWidth` (400) with no horizontal overflow, where toggling that same live page's `base.css`
    `<style>` to `disabled=true` makes the identical markup immediately overflow to 534px against a
    400px client — the rules are doing the work, not the markup. **What this cannot prove, stated
    plainly:** the harness holds copies of four pages' rules. It demonstrates the shared block behaves
    as designed against those patterns and says nothing at all about whether the other 44 real pages
    look right at 960px. Only a human resizing each one does that, and that is PRs 8-11. Final full
    `verify_all.py --snapshot`: **`64 checks | 64 ok | 0 FAILED` · `ALL GREEN -- suites pass and
    every protected file matches the vault.`** All 61 `test_*.py` suites PASS, including
    `test_uiux_fixes.py` at 273/273 — the suite that string-splits `base.css` itself to assert on its
    kiosk-mode and `pointer:coarse` blocks, and therefore the direct check that inserting a new
    section did not disturb them — plus `RPS GATE: PASS`, `test_routes.py` PASS with no sign of the
    known pre-existing `/api/ask` timeout flake, and `safeguard verify: 734 files, 734 OK, 0
    DAMAGED`. **Reaching that took three full runs, and both intermediate failures are written down
    rather than re-run until green; neither was this change's content, and both were chased to root
    cause.** *Run 1*: every suite PASS, `63 ok | 1 FAILED` on `safeguard verify`, which named
    `base.css`, `HANDOFF-NOTE.md` and `MASTER-RECONCILIATION.md` as `MODIFIED (grew / edited)` —
    self-inflicted ordering, since `--snapshot` baselines at the *start* of a ~3.5-minute run and
    those three were still being edited while it was in flight; nothing truncated or shrunk, all
    three grew by exactly the bytes edited. *Run 2*: every suite PASS but `safeguard verify` crashed
    with `FileNotFoundError` on a missing `manifest.json`. Root-caused rather than guessed:
    `verify_all.py` invokes `safeguard.py verify` with **no** snapshot id, so `latest_snapid()`
    returns the lexicographically-last `SNAP_*` directory — which after a full run is one the *test
    suites* created, since `ingest_feature.py` takes a real `safeguard.snapshot("pre-ingest")` before
    every ingest and `test_ingest_routes.py` drives it. That is long-standing behaviour, not new:
    item 37's own entry records `verify vs SNAP_20260903_181820_pre-ingest`. What was new is that one
    such test-created snapshot had a `files/` directory but no manifest, left by an aborted launch —
    all of it inside `backups/`, which is **gitignored and no part of this PR**. Verifying against
    run 2's own baseline (`safeguard.py verify --snap SNAP_20260903_230713_verify_all`) returned
    **734 files, 734 OK, 0 DAMAGED**, and after that garbage directory was removed a plain verify
    returned the same against the next snapshot. *Run 3*: `62 ok | 2 FAILED` — `test_routes.py` (the
    known pre-existing `FAIL GET /api/ask?q=... -> request error: timed out`, 295 passed / 1 failed)
    and `test_ingest_routes.py` with `IndexError: list index out of range` on `_popen_calls[0]`. The
    second was traced, not assumed: that suite stands up its own server on the **hard-coded port
    8894**, and `netstat` showed 8894 already `LISTENING`, held by a `tests/test_ingest_routes.py`
    process whose parent shell was running out of **a different worktree entirely** — one of the
    sibling PRs being built in parallel on this machine, looping that same suite.
    `HTTPServer.allow_reuse_address` lets the second bind succeed on Windows, so the requests reached
    the *other* process, whose `subprocess.Popen` is not the one this run monkeypatched, leaving
    `_popen_calls` empty. That is exactly the false-failure mode item 35 already documented for this
    same file ("checks depend on process-global state and a fixed port"). The sibling's processes
    were **left alone**; once port 8894 was free, `test_ingest_routes.py` standalone gave **175
    passed, 0 failed**, and the final full run came back ALL GREEN with that suite PASS (34.2s). The
    docs edits and the `ITERATION-SNAPSHOTS.md`/`ITERATION-DASHBOARD.html` regeneration recording all
    this necessarily happened *after* the green run — writing a run's result into the repo modifies
    the tree it just verified, which is run 1's trap exactly — so a confirmatory post-edit run on the
    finished tree is reported in the PR body instead.
    See `CHANGELOG.md` `[1.54.0]`.

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
