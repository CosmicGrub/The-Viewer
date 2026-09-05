# THE VIEWER — Handoff Note (reconciled 2026-09-05)

**Purpose:** hand this project to another chat/device without losing context. Read this + the canonical docs
(`docs/EXTRACTION-COVERAGE.md`, `docs/ROADMAP-1.1.md`, `docs/CHANGELOG.md`, `docs/ITERATION-SNAPSHOTS.md`,
`docs/MASTER-RECONCILIATION.md`).

> **Reconciliation note (2026-09-05, forty-fourth pass):** G — kiosk/second-screen reference view
> (multi-window support, PR 18/25, stage 5), depending on PR 5 (`VW.windows`) and PR 17 (C —
> screen-aware placement, `[1.68.0]`) for its `opts.screen` placement preference. New minimal server
> route (`/reference`, registered in `static.py`'s `_PAGES` dict the same way every other page in
> this app is — never a new Python-side HTML-templating mechanism) plus the first two real callers
> of PR 17's `opts.screen` hint: "Send to second screen" buttons on `torque.html`/`procedure.html`.
> **Two doc/code gaps resolved:** the design doc's "existing `viewer_kiosk` styling primitives"
> phrase names a module that does not exist in this codebase (confirmed by grep) — it actually means
> this app's real `body.kiosk-mode` convention (`base.css`'s own rules, toggled elsewhere by
> `palette.js`), which this page forces on unconditionally via a plain `classList.add("kiosk-mode")`
> call, then layers jumbo type on top using `base.css`'s own color tokens; and "a new server route +
> template" follows the SAME client-rendered-static-file pattern every other page uses (`workspaces.html`/
> PR 16 included), fetching from the SAME `/api/torque`/`/api/procedure_full` endpoints
> `torque.html`/`procedure.html` themselves already call, never a duplicated data path. Both launch
> buttons read their page's current query context at click time (mirroring A2/B's own launch
> controls) and share the identical literal window name `"vw-reference"` — one shop, one second
> screen, one reused window regardless of which page sent to it; `procedure.html`'s button computes
> "the current step" from the SAME per-step `localStorage` state its own checkboxes already
> read/write, never a second invented notion of "current." New `test_g_reference_view.py`, 54 real
> assertions against a real `ThreadingHTTPServer` instance + source-text checks, proven load-bearing
> by breaking 5 representative guarantees one at a time (7/2/2/1/8 failures respectively) and
> confirming a clean 54/0 on revert. New standing document `docs/MULTI-WINDOW-MANUAL-QA.md` — the
> plan doc's own note said this should have landed with PR 17 or this PR, whichever shipped first;
> PR 17 merged without creating it — covers real multi-monitor screen-placement checks for both PR
> 17's `opts.screen` and this PR's launch buttons, RPS-tier gating on real lite/legacy hardware, and a
> marked placeholder for PR 24's Picture-in-Picture/Wake-Lock checks (not yet built). Manually
> verified in a real running browser against a real fixture server: a real torque spec, a real
> 5-step procedure with live per-step "current step" tracking (ticking steps 1-2 correctly surfaced
> "Step 3 of 5"), and all three graceful "nothing to show" states. **Stated plainly:** this session's
> browser-automation sandbox collapses every `window.open()` into one tab (a known, previously-
> documented limitation of the tool, not the code under test) — every verification above was
> confirmed via that one tab's resulting page/network requests, never two genuinely separate
> windows; whether "Send to second screen" lands on a DIFFERENT physical monitor is real hardware
> behavior only a human on real multi-monitor hardware can confirm, the same caveat PR 17's own
> `[1.68.0]` entry states, now tracked as a repeatable checklist in `docs/MULTI-WINDOW-MANUAL-QA.md`
> §1 rather than a one-off PR-body note. Landed as PR 18 (not yet merged as this note is written —
> update on merge if renumbered), `[1.72.0]`.
>
> **Reconciliation note (2026-09-05, forty-third pass):** the last remaining flake from this session's
> `verify_all.py --snapshot` audit — `test_ingest_routes.py`'s real, unmocked e2e upload check —
> measured with the same discipline as the forty-second pass's `/api/ask` fix rather than re-guessed.
> **Not the same shape of problem**: `viewer_ingest.py`, the real subprocess this check launches, has
> zero network dependency at all (confirmed by grepping every import/`subprocess.run()` call site —
> only local `pdfinfo`/`pdftoppm`/`tesseract`). **What it actually is:** `ingest_feature.py`'s
> `_launch()` takes a real, synchronous `safeguard.snapshot("pre-ingest")` before ever spawning the
> subprocess (R1: always recoverable before any write) — `[1.50.0]` already correctly diagnosed this
> and set a 60s timeout once; that budget has quietly been exceeded again as the project grew.
> Measured directly, twice, in complete isolation: a real `snapshot()` call over this project's
> current 749 tracked files took 102.4s and 99.6s. The actual driver is NOT file-count/data-volume
> (the tracked-file payload is only ~12.3MB, sub-second even hashed by hand) — it's `atomic_copy()`'s
> per-file `fsync()` plus its paranoia post-copy verify-reread, the same per-file-open Windows tax
> `_replace_retry()`'s own docstring already names elsewhere. **Deliberately NOT weakened**: that
> `fsync()`/verify-reread is a real safety guarantee (R1), not incidental slowness — trading it for
> test speed was never the right fix. **What did change, safely:** `entry_for()` used to call
> `sha256_file()` + `_count_lines()` separately, reading the same file twice for nothing; new
> `safeguard._hash_and_count()` computes both in one pass, verified byte-identical across all 749
> tracked files (confirmed too small alone to explain the 100s figure, but a free, zero-behavior-
> change win taken regardless). The actual fix: the upload request's timeout widened 60s → 240s
> (~2.4x the measured worst case) and the "landed in DB" polling deadline 30s → 90s, both matching
> `_launch()`'s own explicit "no hard limit" design instead of picking another number that just moves
> the same false-failure to the next growth milestone. Verified: `test_ingest_routes.py` standalone,
> 2 consecutive runs, 175/0 every time; `safeguard.py`'s dependent suites (`test_truncation.py`,
> `test_backupdb.py`, `test_build_pipeline.py`, `test_prune.py`) all clean; full `verify_all.py
> --snapshot` 75/75 ALL GREEN including `safeguard verify` itself at 749/749 OK. Landed as PR 62,
> `[1.71.0]`. This is the third and final entry in this session's flake-fixing arc (PR 59 →
> `[1.69.0]`, PR 60 → `[1.70.0]`, PR 62 → `[1.71.0]`) — `verify_all.py --snapshot` now runs genuinely
> ALL GREEN with no known pre-existing flakes remaining. As with PR 60, PR 62 shipped with only
> `CHANGELOG.md` updated; this doc-sync completion (`PROJECT-SUMMARY.md`/`MASTER-RECONCILIATION.md`/
> this file/the snapshot files) follows in its own PR, the same pattern established for PR 60.
>
> **Reconciliation note (2026-09-05, forty-second pass):** root-caused this project's long-standing
> "known pre-existing `/api/ask` timeout flake," named across a dozen-plus prior `CHANGELOG.md`
> entries with the same shrug — reproduced on unmodified `main`, not this change's fault, moving on.
> **It was never slow compute; it was a live network call.** `/api/ask` and `/api/search_hybrid` both
> lazily `import embed`, and `embed.py`'s `SentenceTransformer(...)` call reaches the live Hugging
> Face Hub on every fresh process — measured directly at 15.97s with a real "unauthenticated requests"
> warning on the wire, vs. a consistent 8.4-8.7s once forced fully offline against an already-warm
> local cache. An unbounded network round trip is exactly why widening the timeout never once fixed
> it in over a dozen attempts (45s wasn't enough either, reproduced live while diagnosing this) — and
> it directly contradicted `.github/workflows/ci.yml`'s own header claim that this suite has "no
> network egress." **Fix:** `HF_HUB_OFFLINE`/`TRANSFORMERS_OFFLINE` set via `os.environ.setdefault(...)`
> near the top of `test_routes.py` (never an overwrite — an explicit ambient override still wins),
> verified safe both warm-cache (real semantic path, purely from disk, 8.4-8.7s) and cold-cache
> (offline mode fails immediately, ~5s, caught by `ask.answer()`'s own pre-existing fallback to
> FTS-only passages — never a hang, never a 5xx); `_get()` gained an optional `timeout=`, with a new
> `SLOW_ROUTE_TIMEOUT` dict giving just these two routes 25s (~3x the observed warm-cache worst case)
> while every other route keeps the tight 10s default. **Trade-off stated plainly:** CI, having no
> Hugging-Face-model cache step, no longer exercises the real semantic path for these two routes at
> all — only FTS fallback — same risk that was always silently there on any run whose download stalled
> past its timeout, just deterministic now instead of a coin flip; a follow-up CI model-cache step
> would restore full coverage, left out to keep this fix scoped. Verified: `test_routes.py` standalone,
> 3 consecutive runs, 298/0 every time (was 297/1); full `verify_all.py --snapshot` 75/75 ALL GREEN.
> Landed as PR 60, `[1.70.0]`. This doc-sync completion pass (`PROJECT-SUMMARY.md`/
> `MASTER-RECONCILIATION.md`/this file/the snapshot files) was itself needed because PR 60 shipped with
> only `CHANGELOG.md` updated — completed here the same way PR 59's own incomplete doc-sync was
> completed, in its own follow-up PR since PR 60 had already merged by the time the gap was noticed.
>
> **Reconciliation note (2026-09-04, forty-first pass):** `test_windows_layout.py`'s own PR-6 sanity
> check (`the_diff_genuinely_adds_the_restore_layout_declaration`) became a permanent false-failure
> the moment PR 6 merged — it asserted the diff against `origin/main` genuinely adds
> `windowsRestoreLayout`'s declaration, true only while PR 6 was still unmerged; once merged,
> `origin/main` already contains it, so the diff is naturally, permanently empty and the assertion
> could never pass again on any branch cut from current `main`. Fixed with a new
> `declaration_already_merged()` helper reading `origin/main`'s own tree via `git show`, so the check
> now passes on EITHER "the diff adds it" (live-PR case) OR "it's already merged" (post-merge case).
> Also fixed a real `UnicodeDecodeError` crash found while writing that fix: `git show`'s output hit
> this Windows box's default `cp1252` decoding on a UTF-8 "←" already in `shared.js`'s comments — both
> the new and the pre-existing `git diff` subprocess calls now pass `encoding="utf-8"` explicitly.
> `test_windows_layout.py` standalone: 11 passed, 0 failed (was 10/1). Two unrelated, pre-existing
> flakes (`test_hardening.py`'s J68 check, `test_routes.py` timeouts) reproduced independently and
> confirmed clean in isolation — neither touches this fix's files. Landed as PR 59, opened directly
> against `main` from a branch cut before PR 17 merged; both claimed `[1.68.0]` in `CHANGELOG.md`,
> resolved on merge by retitling this fix to `[1.69.0]`, the genuinely next-free version, the same
> renumbering-on-late-merge pattern this project has used since `[1.54.0]`'s own PR 47.
>
> **Reconciliation note (2026-09-04, fortieth pass):** stage 5, PR 17 of the multi-window/multi-tab
> initiative — **C, screen-aware placement** — extends `VW.windows.open(url, opts)` with an opt-in
> `opts.screen` hint (truthy = "prefer a different screen than this tab's own, if one exists and is
> available"), depending on PR 6 (`VW.windows` layout capture/restore, merged as `[1.67.0]`).
> Feature-detected via the Window Management API's `getScreenDetails()`, gated to the design doc's
> own "modern tier only" requirement. **The doc/code gap, resolved the same way the thirty-sixth
> pass's PR 15 resolved an identical one:** the design doc names `VW.capabilities.windowPlacement` as
> the gate, but `VW.capabilities` is Stage 6 (PR 19–25) and does not exist yet. PR 15 had genuinely
> nothing real to fall back to, so it shipped feature-detected but INERT. This PR is not in that
> position — `rps.js`'s `window.RPS.mode` (`"modern"`/`"lite"`/`"legacy"`, set on every page that
> loads it) IS the capability ladder item 10 asks for, just not yet wrapped in the Stage-6 name, so
> this gates for real, right now, on an EXACT `=== "modern"` string match (never truthy) — `"premium"`
> is an additive flag layered on an already-`"modern"` mode per `rps.js`'s own comment, never a mode
> value of its own. `window.RPS` is genuinely `undefined` on 32 of this app's 49 pages (confirmed by
> grep, not assumed) — treated exactly like "not modern," never a throw. A future Stage 6 PR may swap
> this for `VW.capabilities.windowPlacement`, the same way PR 15's own comment points a future PR at
> itself. **The permission-timing crux this PR exists to respect:** `getScreenDetails()` returns a
> Promise (it IS how the permission prompt surfaces), but `window.open()` must run synchronously
> inside the click-handler call stack or a popup blocker can treat it as not user-gesture-initiated.
> `windowsOpen()`'s existing synchronous open/reuse/toast/broadcast path runs FIRST, completely
> unchanged, and returns its real handle before any of this PR's code is reached; only then, if
> `opts.screen` is truthy and the gate passes, does `getScreenDetails()` fire — fire-and-forget, never
> awaited, never delaying the synchronous return. The resolved target screen is repositioned to via
> `win.moveTo()`, picked from `.screens` by reference identity against `.currentScreen` first, a
> comparable `left`/`top` key as fallback; fewer than 2 screens, or every entry matching current, is a
> silent no-op. Every failure (API absent, denied/rejected promise, a synchronous throw, one screen,
> a since-closed window) is caught silently — no unhandled rejection, no throw, ever, under normal
> denial. **New `test_windows_screen_placement.py` + `test_windows_screen_placement_node.js`, 32 real
> assertions** through the real production code in a `vm.createContext()` sandbox extending PR 5's own
> dual-sandbox convention (the same one PR 6 itself extended): `opts.screen` absent NEVER calls
> `getScreenDetails()` at all (the single
> most important guarantee given this feature's stated permission philosophy); the API absent, `lite`/
> `legacy`/undefined `RPS.mode` all skip cleanly, never throw; a resolved 2-screen result moves to the
> OTHER screen's bounds, never current's; a resolved 1-screen result attempts no move; a rejected
> promise AND a synchronously-throwing `getScreenDetails()` are both caught with zero unhandled
> rejections (a real `process.on("unhandledRejection", …)` listener backs this, not just an absent
> crash); and the call ORDER itself is proven via a shared log — `window.open()` always before
> `getScreenDetails()`, checked immediately with no wait. **Proven load-bearing by breaking 6
> representative guarantees one at a time** (the truthiness guard, the tier gate, the pick function's
> identity/key check against both the 2-screen and 1-screen cases, the `["catch"]` handler, the
> feature-check + outer `try`/`catch` together, and a premature call before `window.open()`) and
> confirming the right assertions genuinely failed each time (3, 2, 2, 3, 1, 4 respectively), then
> reverting to a clean 32/0. **The thirty-fifth pass's own `test_a2_popout.py` cross-PR coupling
> hazard checked for and avoided the same way the thirty-ninth pass (PR 6) already avoided it:** every
> new function lands immediately after `windowsRestoreLayout()`, before the bench/checkpoint/
> `popoutControl()` sections — confirmed `test_a2_popout.py` unaffected at a clean 62/0. **One
> pre-existing, NOT-this-PR's-regression issue
> found and confirmed, not glossed over:** `test_windows_layout.py`'s own
> `the_diff_genuinely_adds_the_restore_layout_declaration` sanity check fails on a clean `origin/main`
> checkout with ZERO changes (confirmed via `git stash` before writing a single line of this PR) — a
> self-referential git-diff check that can never pass again now that PR 6 is merged and its
> declaration lives in `origin/main` itself, not something this PR broke; flagged as a separate
> follow-up task rather than touched here (out of this PR's scope — PR 6's own test file). `rps_lint.py`
> clean (`shared.js` is ES5-required; two prose word choices read as false-positive ES6 `let` hits and
> were reworded, same near-miss category the thirty-ninth pass already named). Design doc's own `C's
> extension to VW.windows` section updated to reflect the real `window.RPS.mode` gate instead of the
> not-yet-existing `VW.capabilities.windowPlacement` name. **Deliberately out of scope:** any UI
> page/button passing `opts.screen` (PR 18/G, named next in the plan, is the first real consumer);
> `win.resizeTo()`; and, stated plainly, the actual on-screen placement behavior on real,
> possibly multi-monitor, Chromium hardware — Node has no `getScreenDetails`, no real permission
> prompt, and no real screens to be right or wrong about any of it, a real human-only verification
> step called out as manual in the PR body, the same honest framing every other real-hardware-only
> behavior in this initiative has used since PR 5. Shipped as `[1.68.0]`. `main` is at `[1.67.0]` as
> of this pass.
>

> **Reconciliation note (2026-09-04, thirty-ninth pass):** stage 2, PR 6 of the multi-window/
> multi-tab initiative — **`VW.windows` layout capture + user-triggered restore**, landed OUT OF the
> plan doc's own stage order (same shape the thirty-seventh pass's PR 3 already used): it belongs
> right after PR 5 (open/reuse/toast core) but was skipped over during this session's earlier
> parallel-dispatch of other PRs, and is inserted now because PR 17 (C — screen-aware placement, next
> in the queue) explicitly depends on it existing first. `registry()` now returns LIVE
> `screenX`/`screenY`/`outerWidth`/`outerHeight` per tracked window, read off the SAME handle
> `_winReg` already holds at CALL time (never captured once at open-time and cached — a technician can
> move/resize a window after opening it), each property read guarded INDEPENDENTLY so one
> throwing/unreadable field degrades only itself to `null`, never the other three, never another
> window's entry in the same call. `windowsOpen(url, opts)` gained an optional
> `opts.left`/`top`/`width`/`height` position/size hint, matching `window.open()`'s own
> features-string vocabulary directly — threaded into the real third `window.open()` argument ONLY on
> a genuinely NEW open, NEVER a reuse (browsers generally only honor position/size features on a
> window's first open — a real, stated-plainly browser limitation), sanity-checked against
> `window.screen.availWidth`/`availHeight` first (a generous 4x ceiling — the design doc's own named
> "monitor unplugged since the position was saved" fallback), dropped ENTIRELY rather than partially
> on any failure, never a throw. New `VW.windows.restoreLayout(entries)` calls THROUGH `windowsOpen()`
> — not a second, parallel copy of open/reuse/toast/broadcast — once per well-formed entry, skipping a
> malformed one without aborting the batch, returning one `{name, url, ok, reused}` result per input
> entry. **MUST NEVER be called from a load/init/`DOMContentLoaded` handler anywhere in this
> codebase** — restoring windows unprompted is exactly the design doc's own "a web page cannot run
> code 'on app launch' unprompted" case; nothing in this diff wires one, an API-only PR matching PR
> 2/3/5's own precedent of shipping without a dedicated UI page. New `test_windows_layout.py` +
> `test_windows_layout_node.js`, **51 real assertions** (41 behavioral through the real production
> code in a `vm.createContext()` sandbox extending PR 5's own dual-sandbox convention, + 10 static
> checks proving `restoreLayout` is never auto-invoked anywhere in the diff — a comment-stripped
> full-source scan, a `git diff`-scoped scan of this PR's own added lines, and a check that no
> `DOMContentLoaded`/`load`/`pagehide` handler body mentions `restoreLayout` even in a comment),
> proven load-bearing by breaking 6 representative guarantees one at a time (live-not-cached read,
> per-field throw independence, implausible-hint drop, reuse-never-threads-bounds, malformed-entry
> skip, load-handler-never-calls-it) and confirming the right assertions genuinely failed each time
> (5, 1, 5, 2, 7, 1), then reverting to a clean 51/0. PR 5's own `test_windows_node.js` updated for
> the new registry shape, not broken around. **A real hazard checked for and avoided, not just
> hoped around:** PR 16's own agent had discovered `test_a2_popout.py` slices `popoutControl()`'s
> body up to the next `"var VW = {"` marker, so inserting new functions BETWEEN existing marked
> sections can silently get swallowed into that scan — this PR's new functions all landed immediately
> after `windowsOpen()`, before `popoutControl()`'s own section begins, specifically to avoid it; a
> full `verify_all.py` run confirmed `test_a2_popout.py` unaffected at a clean 62/0. One unrelated,
> pre-existing flake observed and confirmed NOT this PR's regression: `test_hardening.py`'s
> cross-origin-POST check failed once inside a full-suite run, then passed clean both standalone and
> on an immediate full-suite re-run — the same fixed-port test-isolation flakiness class
> `test_ingest_routes.py`'s own documented port-8894 hazard already names. `rps_lint.py` clean
> (`shared.js` is ES5-required; two prose word choices — "let alone" and an "…" ellipsis inside new
> comments — read as false-positive ES6 `let`/spread-rest hits, reworded not suppressed, same
> near-miss category the thirty-seventh pass already named). Design doc's own `VW.windows` item-4
> header updated from "PR 5 — in progress ...; layout capture/restore is PR 6" to "PR 5 + PR 6
> landed" — nothing else in that spec file touched. **Deliberately out of scope, matching this PR's
> own plan-doc scope:** any UI page/button calling `restoreLayout()` (PR 17 and/or a later PR's job);
> PR 17's own feature-detected, permission-gated `getScreenDetails()` placement API; and the actual
> on-screen placement behavior on real, possibly multi-monitor, hardware — Node has no `window.open`
> to be right or wrong about whether position/size features are genuinely honored on a new window and
> genuinely ignored on a reuse, or whether the "monitor unplugged" fallback actually lands somewhere
> reachable; both stated plainly as manual, real-hardware-only checks in the PR body. Shipped as
> `[1.67.0]`. `main` is at `[1.66.0]` as of this pass.
>

> **Reconciliation note (2026-09-04, thirty-eighth pass):** stage 5, PR 16 of the multi-window/
> multi-tab initiative — **F, save & reopen named workspaces + the auto-checkpoint**, the UI over
> everything PR 2/3/15 built. New `engine/ui/workspaces.html` (`/workspaces`): list every saved
> workspace (most-recently-opened first); **save** turns THIS TAB's own `VW.windows.registry()` into
> `{page, params}` items by hand-parsing each open window's url, names it via a plain
> `window.prompt()` (matching `index.html`'s existing pattern), calls
> `VW.workspace.create(name, items, "manual")`; **reopen** calls `VW.workspace.touch(id)` then opens
> every item via the SAME `VW.windows.open(url, {name: VW.popoutWindowName(url)})` pairing A1/A2/B
> all already use, never a re-implemented naming copy; **export** offers a real share-link copy
> (`navigator.clipboard`, with a visible fallback field) and a real `.json` download (the same
> `Blob`+`URL.createObjectURL`+`<a download>` pattern `circuitlab.html` already established);
> **import** accepts a pasted share link (full URL, `?ws=...` fragment, or bare `ws=...`, all three
> normalized) or an uploaded `.json`, both catching PR 3's real thrown/rejected `Error` rather than
> letting it propagate. **Gap filled: `VW.workspace.delete(id)`** — the one CRUD op PR 2 shipped
> without, added because a list UI that only ever grows is a real problem for a page a technician
> returns to across a career; same shape as `touch()`, wired behind a real `confirm()` on the page.
> **The auto-checkpoint (design doc item 9's "Addition this revision") built for real:** a single
> `viewer_last_session` slot (genuinely distinct from `viewer_workspaces`), silently holding a
> snapshot of a tab's `VW.windows.registry()`, overwritten every time, never surfaced by
> `VW.workspace.list()`. Written on `pagehide` **and** a 2-minute `setInterval` safety net (the
> design doc's own named risk: a crash mid-shift fires no unload event at all), wired at the
> `shared.js` TOP LEVEL so it reflects windows opened from ANY feature — made safe by skipping the
> write whenever the writing tab's own registry is empty, so an idle tab can never clobber a real
> checkpoint a different tab just wrote. `workspaces.html` is the one place that ever offers to
> restore it, strictly via a real button click — never automatic — "a checkpoint exists" is the
> whole heuristic, the design doc's own sanctioned baseline. **Handover integration**: a real,
> findable "Hand off your open workspace" section on `handover.html` linking to `/workspaces`,
> showing LIVE `VW.workspace.list().length` data, not a static blurb. New
> `test_f_workspace_reopen.py` + `test_f_workspace_reopen_node.js`, **40 checks** — source-level
> call-site proof for every required function plus the naming-regex reuse check, and real Node
> round trips for `workspaceDelete()` (create/delete/confirm-gone, a refused-write case, the
> cross-tab delete notification over a real `BroadcastChannel`) and the checkpoint (a sandbox with a
> REAL `addEventListener`/`setInterval` that captures and fires shared.js's own module-load-time
> handlers directly, rather than reimplementing what they do) — proven load-bearing by breaking 5
> representative guarantees one at a time and confirming the right assertions failed (2, 3, 3, 6, 1),
> then restoring a clean 40/0. **A real regression caught before shipping:** the checkpoint block was
> first inserted between `popoutControl()` and the final `VW` object assembly, which broke
> `test_a2_popout.py`'s own body-slicing assumption (it scans from `popoutControl`'s declaration to
> the NEXT `"var VW = {"`, so anything inserted between them gets swallowed into what it inspects) —
> its "exactly one `VW.windows.open(` call" assertion started seeing 2 because of this PR's own
> comment prose. Caught by running the FULL `verify_all.py`, not just the new suite; fixed by
> reordering `shared.js` so the checkpoint block sits before `popoutControl()` again. Shipped as
> `[1.66.0]`. `main` is at `[1.65.0]` as of this pass.
>

> **Reconciliation note (2026-09-04, thirty-seventh pass):** stage 2, PR 3 of the multi-window/
> multi-tab initiative — **`VW.workspace` export/import**, landed OUT OF the plan doc's own stage
> order: it belongs right after PR 2 (CRUD) but was skipped over during this session's earlier
> parallel-dispatch of other PRs, and is inserted now, after PR 15/B, because PR 16 (F — save &
> reopen named workspaces, next in the queue) explicitly depends on it existing first. Four new
> `shared.js` exports alongside PR 2's `create`/`list`/`get`/`touch`: `exportUrl(id)`/`exportFile(id)`
> hand a workspace's `{name, items}` (deliberately never its id or timestamps — meaningless or
> actively misleading once recreated on a different machine) to a different technician's browser as a
> `"ws=<json>"` query string or a downloadable `application/json` `Blob`; both return `null` (never
> throw) for an unknown id, matching `get()`'s own not-found convention. `importUrl(qs)`/
> `importFile(blob)` (the latter a `Promise`, via a plain `.then()` chain — never an arrow function or
> async/await) share one internal parse-validate-create helper: shape-validated BEFORE anything
> touches storage, throwing/rejecting with a specific `Error` message on any mismatch, matching the
> design spec's edge case verbatim ("validated before being written, rejected with a clear message on
> any mismatch") — deliberately stricter than `create()`'s own lenient item coercion, since an import
> is trusting a file that could have been hand-edited, corrupted, or tampered with. **Item shape
> checking is not reimplemented a second time:** validation reuses PR 2's own `_wsItems()` as the
> arbiter — if `_wsItems()` would drop an entry, that entry was invalid, and the whole import is
> refused rather than silently keeping only the entries that survived. **A fresh id is always
> minted**, via the same `workspaceCreate()`/`_wsNewId()` path every other workspace goes through;
> neither import function ever reads (or trusts) an `id` field the incoming payload might carry, even
> a deliberately spoofed one — proven directly in the new test, not merely argued. New
> `test_workspace_export_import.py` + `test_workspace_export_import_node.js` (both under
> `engine/tests/`): **53 real round-trip assertions** (not source-text matching — actual calls through the
> real exported functions, exportUrl→importUrl and exportFile→importFile each run across TWO
> SEPARATE `localStorage` stores, one per simulated browser, so the round trip proves the exported
> payload is genuinely portable), proven load-bearing by temporarily making import trust an incoming
> `id` field (3 assertions genuinely failed) and by temporarily skipping shape validation before the
> write (9 assertions genuinely failed), each confirmed failing then reverted and re-confirmed a
> clean 53/0. `rps_lint` clean (`shared.js` is ES5-required; the only close call was a doc comment's
> own `"..."` ellipsis reading as a false-positive spread/rest hit, reworded rather than suppressed).
> Design doc's own `VW.workspace` API-block header comment updated from "CRUD in progress;
> export/import/templates next" to "CRUD + export/import landed; built-in templates next" — nothing
> else in that spec file touched. Deliberately out of scope, matching PR 3's own plan-doc scope:
> `schemaVersion`/migration-on-read (Stage 6), the File System Access API path for `exportFile` (the
> design doc's own deferred note), and any UI over these four functions — that's PR 16/F's job, which
> depends on this PR existing first. Shipped as `[1.65.0]`. `main` is at `[1.64.0]` as of this pass.
>

> **Reconciliation note (2026-09-04, thirty-sixth pass):** stage 5, PR 15 of the multi-window/
> multi-tab initiative — **B, curated workspace launcher**. Two real launch sets, one click each:
> "Launch Work Order" on `jobcard.html` opens `procedure.html` + `torque.html` + `part.html`; "Launch
> Solve It" on `solve.html` opens `troubleshoot.html` + `procedure.html` + `locate.html`. Both follow
> the plan's own required order — one `VW.workspace.create(name, items, "template")` call persists a
> real workspace record FIRST, then each page opens via `VW.windows.open()` — and both thread the
> page's CURRENT `#q` value (read inside the click handler, never a page-load-time value) onto every
> launched URL as `?q=...`, the same convention `index.html`'s `threadQuery()`/A1 already established.
> **`shared.js` gained one new export, not a new naming rule:** PR 14's `_popoutWindowName()` was
> private to its closure, sufficient for `popoutControl()` (which only ever names the CURRENT page),
> but B opens pages other than whichever one it's running on and needed the same transform reachable
> directly — exported as `VW.popoutWindowName`, the exact same function, so a page already open via
> A1's home-nav ↗, A2's own pop-out control, or a previous B launch is REUSED, never duplicated;
> neither `jobcard.html` nor `solve.html` re-implements any fragment of the naming regex, both call
> `VW.windows.open(url, {name: VW.popoutWindowName(url)})`, byte-for-byte identical text in both files.
> **The design doc's item 8 "Addition this revision" — a `VW.capabilities.tier` guard before opening
> several windows at once — is written forward-compatible, not built out:** `VW.capabilities` is Stage
> 6 (PR 19-25) and does not exist on `main`, and PR 15's own "Depends on" list names no Stage 6 PR, so
> both launch functions feature-detect it end to end (`window.VW && VW.capabilities`, then `caps &&
> typeof caps.tier==='string'`) — reads as "no tier info" today and does nothing, starts warning on
> `lite`/`legacy` the day a real `VW.capabilities.tier` ships, with zero further code change needed
> here. New `engine/tests/test_b_workspace_launcher.py`: **52 assertions**, proven load-bearing by
> reverting 6 representative fixes one at a time (the `shared.js` export, one page's item order,
> `workspace.create()`'s ordering relative to the open loop, the capabilities guard's
> short-circuiting, one page's button id, a simulated re-implemented naming regex) and confirming the
> relevant assertion(s) genuinely failed before restoring and re-confirming a clean 52/0. `rps_lint`
> clean (`solve.html`/`shared.js` are ES5-required; `jobcard.html` modern-by-design). **Popup-blocker
> behavior tested for real, with an honest limitation found and reported rather than assumed away:**
> this session's automated Browser-pane preview tool cannot demonstrate genuine multi-window fan-out —
> every `window.open()` call there returns `null` (the already-tested blocked-popup path in
> `VW.windows.open()` handles that cleanly, no crash), and the pane's one visible tab is separately
> redirected to only the LAST attempted URL by the harness itself, confirmed identical with a
> code-independent page containing nothing but 3 raw `window.open()` calls — i.e. a property of that
> sandboxed preview tool, not a finding about real desktop Chrome/Firefox. What WAS confirmed live
> against a running server: both buttons correctly thread the live `#q` value onto the final URL
> (`/part?q=alternator`, `/locate?q=brake pad`). Whether a real desktop browser opens all 3 as separate
> windows within one synchronous click, and whether a second click reuses them, is called out as a
> genuine unverified manual check — same honest treatment this initiative already gives A1/A2's window-
> reuse (real multi-monitor placement, C/PR17, isn't built yet but is planned to get the identical
> treatment). Deliberately out of scope, matching the plan's own PR
> 15 scope: these workspaces launch fresh every time and are never saved/listed/reopened — that's PR
> 16/F's job, which depends on B existing first. Shipped as `[1.64.0]`. `main` is at `[1.63.0]` as of
> this pass.
>

> **Reconciliation note (2026-09-04, thirty-fifth pass):** stage 4, PR 14 of the multi-window/
> multi-tab initiative — **A2, per-page pop-out control**, the mirror image of PR 12's A1: a page a
> technician is *already on* now gets its own control to pop itself out into a second window, instead
> of having to navigate back to the home nav first just to duplicate the page they're already reading.
> `shared.js` gained `VW.popoutControl()` — called once, zero-config, by a page's own inline script —
> injecting a real, keyboard-focusable `<button id="vw-popout-pill">` (never a `div`+click handler,
> the same `[1.46.0]`/`[1.47.0]` accessibility convention) labeled with A1's own `"Open X in a new
> window"` phrasing, and one shared `doPopout()` inner function backs both the button and the new
> Ctrl+K palette entry so the open call is never duplicated. **The window-naming logic is a
> byte-for-byte copy of A1's `popoutName()`** (index.html, ~line 592) — the entire reason A1's own
> comment named this PR in advance: popping `/torque` out from the home nav, then clicking `/torque`'s
> own new control, lands on the SAME window rather than a second one. `test_a2_popout.py` extracts and
> compares the two files' actual regex/string-transform source text to prove that, not just eyeballs
> it. **The palette entry required a new, order-independent registration hook that did not exist
> before this PR:** `popoutControl()` cannot reach into `palette.js`'s `COMMANDS` array directly (on
> the normal load order — `shared.js` in `<head>`, then the page's own inline script, then
> `palette.js` last — `COMMANDS` doesn't exist yet at that moment), so it pushes a plain descriptor
> onto a new `window.__paletteQueue` instead, and `palette.js` drains that queue into `COMMANDS` at
> **two** points (right after `COMMANDS` is built, and again as the first statement inside `open()`)
> so a descriptor lands correctly regardless of which of the two real script orders a future page ends
> up using. Placement (`base.css`, `#vw-popout-pill{right:288px;bottom:12px}`) was **measured in a
> real browser**, not guessed — `#bench-pill`'s own rendered left edge sits around `right:217px` at
> every width tested (1400/960/720 CSS px, and in kiosk mode), leaving this pill a genuine ~70px clear
> gap; it does not touch the separately-filed, already-known `#vw-footer`/`#cmdk-pill`/`#bench-pill`
> overlap flagged earlier this session. Adopted on the 5 pages the plan names — `part`, `procedure`,
> `torque`, `jobcard`, `bench` — each already carrying its PR 8/`[1.58.0]` responsive pass. New
> `engine/tests/test_a2_popout.py`: **62 assertions**, proven load-bearing by reverting 5
> representative fixes one at a time (the helper's own existence, the naming-transform identity with
> A1, both palette drain call sites, one page's adoption call, the pill's placement offset) and
> confirming the relevant assertion(s) genuinely failed before restoring and re-confirming a clean
> 62/0. `rps_lint` caught the exact same false-positive class `[1.51.0]` first documented (backticks
> used as plain code-reference punctuation in a doc comment, here around `location`/`_footerNav`,
> read as ES6 template literals by the blunt text scan) — reworded without backticks, not
> suppressed. **Owed manual check, not automatable here, same as A1's own PR:** pop out
> `/torque` from its own new control, then pop out `/torque` again from the home nav's ↗ — confirm one
> window, not two. Shipped as `[1.63.0]`. `main` is at `[1.62.0]` as of this pass.
>

> **Reconciliation note (2026-09-04, thirty-fourth pass):** not a multi-window-plan PR — found in
> passing while reviewing `/api/coverage` output during the PR 8-11 responsive-verification
> batches. `coverage.html`'s CAD-renders meter could read `156.3%`, and the display bug and the
> root cause were both real. Display: the three percent meters built their bars via string
> concatenation and never clamped the width (the page's own `pctBar()` helper already did it right
> but was dead code) — routed all three through it, bar clamped to 0-100, but per R13 the number
> stays honest (still `156.3%`, now with a visible "over 100%" flag) rather than being silently
> corrected. Root cause: `representative_parts` only counted `ref_nsn` rows with FLIS dimensional
> characteristics, undercounting against `make_cad.py`'s real render pool (which unions that with
> every NSN appearing in `parts` against a figure) by roughly a third — 20,869 counted vs 32,622
> actually eligible; a smaller numerator bug (`rendered_v3` counting turntable `_spinNN_v3.png`
> sprite sheets as separate parts) compounded it. Fixed both, with sync comments so the two files'
> copies of the query logic don't drift apart again. Verified live: `cad.pct` now reads a clean
> `100.0%`. Filed as its own PR (`fix/coverage-bar-clamp`) since it's unrelated to the multi-window
> initiative in flight — shipped as `[1.62.0]`, after the four responsive batches. `main` is at
> `[1.61.0]` as of this pass; see `CHANGELOG.md` `[1.62.0]`.
>

> **Reconciliation note (2026-09-04, thirty-third pass):** stage 3, PR 11 of the multi-window/
> multi-tab initiative — **responsive verification, batch 4 of 4**, and the last of the four per-page
> batches that turn the twenty-ninth pass's shared breakpoints from *written* into *verified*. That
> note said plainly that not one real page had been opened in a resized window; this pass does it for
> twelve: `master`, `mastercov`, `packet`, `exploded`, `schematics`, `threed`, `deepzoom`, `stepflow`,
> `keywords`, `publog`, `audit`, `cadtex_test` — the specialized-visualization group. **Scope first,
> because it is the thing most likely to be misread:** several of these render a WebGL/canvas/SVG
> stage that sizes itself by script inside its own clipped viewport (exactly why `base.css` excludes
> `svg`/`canvas` from its `max-width:100%` clamp), and **those stages were out of scope and were not
> touched.** What was checked is the chrome around them: toolbars, title bars, card grids, tables,
> search rows. Each page was served by a real `viewer_app.py` on a real port, opened in a real
> browser and measured at **960px and 720px** with `getComputedStyle`/`getBoundingClientRect`.
> **A methodological trap worth carrying forward, because it manufactures false findings:** the
> browser automation here switches into **mobile device emulation below 768px** (Android UA,
> `maxTouchPoints:5`), which makes `(pointer:coarse)` match — and `base.css`'s coarse block sets
> `min-width:44px` on inputs at specificity `0,2,1`, outranking a page's own
> `.search input{min-width:240px}` at `0,1,1`. The first 720px reading therefore showed
> `master.html`'s search box collapsed to **55px**, which is real touch-tablet behaviour but *not*
> the popped-out-desktop-window scenario this work is about. Every 720px measurement was re-taken
> with that one media block surgically disabled (rewriting its `mediaText`, so nothing else changes),
> and `cadtex_test.html` — which has **no `<meta name="viewport">` at all**, so emulation falls back
> to a 980px layout viewport and hides its defect entirely — was measured at **768px**, the widest
> point still inside the ≤960px band and still on the desktop pointer path.
> **Three real defects found, each fixed in that page's own inline `<style>`, none in `base.css`.**
> `cadtex_test.html` was the worst: `.g` asks for three *fixed* tracks, `repeat(3,310px)` + `2x14px`
> gap + `body{margin:20px}` both sides = **998px** of content, giving `scrollWidth` **978** against
> `clientWidth` **768** (210px out, the whole third column of test cards and their canvases
> off-screen) and 978 vs 960 (18px out, clipping the right-hand canvas); no shared rule can reach it
> and none should, since `.g` is not in the `:where(.grid,.grid2,.cards,.tiles,…)` list and
> `min-width:0` cannot shrink a fixed track — fixed with an `auto-fit` repeat of the *same* 310px
> track, chosen over anything that resizes the cards precisely so the `290x220` canvases stay
> untouched. `deepzoom.html`'s `.top` is one flex row of up to **11 controls** with no `flex-wrap`
> and is not one of the class names the shared wrap rule covers — checked, not assumed: `.top` is
> declared on exactly **two** pages app-wide, here and `pmcs.html`, and `pmcs.html` already wraps
> itself, so a genuine one-page gap; with `#edbtn`/`#pqabtn` live (they are `display:none` on a bare
> host but real whenever `dedup.db` holds another edition or the host is GPU-tier) 720px gave
> `scrollWidth` **797** vs **720**, `#cinfo` at `711..797` entirely past the edge → fixed, 797 → 720.
> `schematics.html`'s sheet title (`.gbar .sp`, `flex:1 1 0%` in a ~15-control bar) got only the
> leftover space on its flex line and measured **66px at 1400, 60px at 960, 3px at 720** against the
> 182px it needed — not one legible character while the operator is still looking at the drawing; a
> `min-width` floor was tried and rejected (it only steals the space back from the controls), so the
> title takes a row of its own below 960px → 917px / 692px. **All three are scoped inside
> `@media (max-width:960px)` and re-measured at 1400px to prove wide-desktop layout is byte-identical
> (R1)** — for `deepzoom` that was verified in both the default *and* the all-buttons configuration.
> **Nine pages needed no change, and that is measured, not assumed:** `scrollWidth == clientWidth`
> with zero escaping elements at both widths, and where this host has no data built (Masterfile,
> PUBLOG, provenance, figure-parts are all empty here) each page's *own* render output was injected
> verbatim — the exact markup its `renderFiltered`/`renderRaw`/`renderRecord`/`renderList` build,
> with realistic long NSNs, CAGE codes and characteristic strings — so the tables and card lists were
> actually exercised rather than measured empty. Two things fell out of that: `stepflow.html`'s
> `.bar` declares no `flex-wrap` of its own and gets `wrap` **from `base.css`** (the shared rule
> doing real work on a real page, confirmed by reading the computed value), and `threed.html`'s
> `.gside` is a fixed 320px rail that correctly does **not** match `body .side{width:100%}`.
> **`packet.html` got the print check it was owed, and the answer is specific rather than "probably
> fine":** the new breakpoints **do** bind during print — measured in an iframe at the real printed
> page box, US Letter 816px and A4 794px each minus this page's own `@page{margin:14mm}` (2 x 52.9px)
> → **710px / 688px**, where both queries match — but of the seven shared rules exactly **one**
> reaches this page, `body{overflow-wrap:break-word}`, which *helps* (it stops a long NSN pushing
> `table.parts` off the paper). The page carries none of
> `.grid/.grid2/.cards/.tiles/.cols/.chips/.tabs/.side`, its only `<img>` is the QR at an inline
> `width:74px`, and its screen-only `.toolbar` is `display:none!important` in print regardless. No
> screen-only chrome leaks into the printed sheet; no change needed.
> **Two honest negatives, recorded rather than quietly dropped.** `publog.html` was expected to
> demonstrate `overflow-wrap:break-word` earning its keep; measured with the rule and with it forced
> back to `normal`, `scrollWidth` was **720 both ways** — the real characteristic string breaks at its
> own commas anyway. And a **pre-existing, width-independent** overlap was found in the shared
> bottom-right chrome: `#vw-footer` (bottom:52px) bottom-edge 848 against the `palette.js` pills'
> top-edge 844 (4px), and the read-aloud button overlapping the bench pill by 21px — `base.css`'s own
> comment claims `bottom:52px` clears those pills, which stopped being true once they became 44px
> tall. Confirmed identical at 1400px with `pointer:fine`, so **not** a responsive regression; it
> predates this initiative and affects all 46 pages, and fixing shared chrome from inside a 12-page
> batch while three sibling branches were in flight would have been the wrong call. On the record so
> the next pass can pick it up deliberately.
> **`base.css` was not touched, and the new suite asserts that rather than promising it** — three
> sibling batches of this same pass were in flight and the shared sheet is the one file they could
> collide on. **ES5 classification was read from `rps_lint.py`'s own source, not its printout:** the
> gate prints `[ ok ] … ES5-clean` both for an ES5-required page and for a modern page that merely
> contains no ES6, so the output alone cannot tell them apart. In this batch `packet.html`,
> `stepflow.html` and `keywords.html` are ES5-required and the other nine modern-by-design — moot in
> practice, since **this PR changes no JavaScript at all, only CSS**, but the new suite now guards
> those three pages' inline scripts directly. New `engine/tests/test_responsive_batch4.py`, **58
> checks**, auto-discovered by `verify_all.py`'s glob; it states its own limits (no browser, so it
> does not re-assert pixel numbers) and locks down what a browser check cannot — that each fix is
> still present and still *inside* its breakpoint, that the preconditions have not drifted, that the
> canvases kept their fixed sizing, and that `base.css` still holds all six of the twenty-ninth
> pass's rules with `svg`/`canvas` still excluded from the image clamp. Two of its checks are real
> arithmetic over numbers parsed from the page's own CSS (`3*310 + 2*14 + 2*20 = 998 > 960`), and the
> `@media` rule is only *required* while that arithmetic still overflows, so shrinking the cards
> later will not fail spuriously. Proven load-bearing by mutation: the three fixes deleted,
> `deepzoom`'s wrap moved outside its breakpoint, and `cadtex_test`'s canvas given a percentage width
> were injected in turn and **all five were caught**. `1.61.0` and the doc-list numbers
> (`MASTER-RECONCILIATION` item 44, `PROJECT-SUMMARY` item 43, this thirty-third pass) were reserved
> up front alongside three sibling batches claiming `1.58.0`/`1.59.0`/`1.60.0` and the numbers between
> — if one does not land, this renumbers on merge exactly as `[1.57.0]` did from its reserved
> `1.54.0`. Shipped as `[1.61.0]`; `main` is at `[1.57.0]` until this merges.
> **Reconciliation note (2026-09-04, thirty-second pass):** stage 3, **PR 10** of the multi-window/
> multi-tab initiative — the per-page responsive verification pass, **batch 3 of 4**, and the first
> half of the debt `[1.57.0]` recorded against itself ("not one real page has been checked against
> these rules in a resized window yet"). Eleven pages — `learn`, `binaudit`, `coverage`, `ingest`,
> `ops`, `status`, `verify`, `command`, `collections`, `review`, `demo` — were each loaded from the
> real server in a real browser **with their real data** and measured at **960 CSS px** (half a 1080p
> monitor, the spec's own scenario) and **720 CSS px** (a docked or quarter-width window). Three real
> defects, eight pages clean, and the eight are reported as measurements rather than as a shrug.
> **(1) `binaudit.html` split every NSN in half, mid-identifier.** Its audit table's NSN column is
> 127px wide and holds one NSN per line at 1440px, but 123px at 960px and **94px at 720px**, where
> the hyphens inside an NSN become ordinary break opportunities and each identifier lands across two
> lines (`6115-01-` / `036-6374`) — on the one page whose stated job is telling apart look-alike
> NSNs. Checked rather than assumed: with `base.css`'s `overflow-wrap:break-word` suppressed on that
> column the NSNs *still* broke, so this is the per-page identifier override `[1.57.0]` explicitly
> left to these PRs, not a shared-rule bug. Fixed with `white-space:nowrap` on the NSN column **plus**
> `overflow-x:auto` on `#out`, because the nowrap alone was measured pushing `scrollWidth` to 435
> against a 400px client; with both, 400px gives `scrollWidth` 400 = `clientWidth` 400 and `#out`
> scrolls internally at 419/368. **(2) `status.html`'s NIIN format-drift queue split a variant
> mid-NSN** at 720px (variants column 232px, vs 375px at 960px where nothing breaks) — measured
> character-by-character with a `Range`, the live first row read `5305-00-292-4587 · 5306-00-292-` /
> `4587 · 5605-00-292-4587`, on the table whose entire purpose is comparing those strings. Fixed with
> nowrap on the NIIN/variants columns at ≤720px inside a real `.tscroll` wrapper, because nowrap
> alone with a synthetic 5-variant row pushed the page to `scrollWidth` 1023 against 720, and
> `overflow-x` on a `<table>` element does nothing (Chrome keeps computing it `visible` — measured).
> After: 40 live rows, **0 broken variant cells**, page 720 = 720; at 960px the column widths are
> byte-identical to the pre-change measurement (80/375/141/267, 863px table). **(3) `demo.html`'s
> guided tour placed its tooltip *behind* the control bar in a narrow window.** `place()` clamped
> against a hard-coded `barH = 56`, true only while the bar fits one row; at 720px the bar is **119px**
> (86px from its own dots strip wrapping, then 119px once `[1.57.0]` added `flex-wrap:wrap` to the
> shared `.bar` selector at ≤960px), so at **720x620** steps 3, 14 and 15 of the 19-step Mechanic tour
> put the tooltip **44px, 3px and 59px behind the bar**. Fixed by reading the bar's real
> `offsetHeight`; after, all 18 measured steps clear it (worst −5px, the clamp's own margin) and at
> 1440px the measured height is **exactly 56**, so the change is inert at desktop width. ES5 only —
> and **`rps_lint`'s false positive bit this initiative again**: the phrase "the shared `.bar` class
> at 960px" in that fix's comment matched `(?<![\w.])class\s+[A-Za-z_$]` as a class declaration and
> turned the gate red on an ES5-clean file; reworded to "selector". **`base.css` was deliberately not
> touched** — every defect was page-specific, three sibling batches were in flight against the same
> shared sheet, and the new suite asserts `#out`/`#niintbl`/`.tscroll` never appear in it. New
> `engine/tests/test_responsive_batch3.py`, **25 checks, all passing**, and proven non-vacuous rather
> than claimed to be: with all three fixes deliberately reverted it reported **18 passed, 7 failed**,
> exit 1, naming exactly the reverted ones, after which the three files were restored and confirmed
> `diff`-identical to their backups. `1.58.0`/`1.59.0`/`1.61.0` are claimed by the three sibling
> batches of this same pass built in parallel off the same `main`, so this branch reserved
> **`1.60.0`** up front rather than race for a number — and, for the same reason, took the **third**
> free ordinal/number in each doc's own list (this note, `PROJECT-SUMMARY` item 42,
> `MASTER-RECONCILIATION` item 43), matching `1.60.0` being third of the four reserved versions, so
> four parallel branches cannot land on the same number in non-overlapping lines.
> Shipped as `[1.60.0]`. `main` is at `[1.57.0]` until this merges.
> **Reconciliation note (2026-09-04, thirty-first pass):** stage 3, PR 9 of the multi-window/
> multi-tab initiative — **per-page responsive verification, batch 2 of 4.** `[1.57.0]`/PR 7 added
> the shared breakpoints to `base.css` and said plainly that not one real page had been opened in a
> resized window yet; this is that work for one of the four batches. Three sibling batches are being
> built in parallel on this machine and claimed `1.58.0`/`1.60.0`/`1.61.0`, so `1.59.0` was taken up
> front to keep the four from colliding (and this pass numbered **thirty-first** on the same logic —
> `[1.57.0]` is the twenty-ninth, `1.58.0` the thirtieth; if the merge order differs, renumber, the
> same way `[1.57.0]` renumbered its own version). **The 12 pages:** `solve`, `troubleshoot`, `ask`,
> `handover`, `circuitlab`, `scan`, `semantic`, `visual`, `kg`, `related`, `index`, `help` — each
> opened against the running server at **960** and **720 CSS px** with real content (not an empty
> shell: `solve` driven through both stages, `troubleshoot` onto a tree that really has checks, `ask`
> left to finish its ~25s round trip, `circuitlab` with the RLC sample simulating, `index` past its
> side-gate with 30 results and the in-app viewer open). Two instrumented passes on every one: an
> **overflow probe** (any element past the viewport, any `scrollWidth > clientWidth` under
> `overflow-x:visible`, anything clipped >20px under `overflow-x:hidden` — the silent-content-loss
> case an ordinary overflow check misses — plus document-level scroll width) and a
> **mid-word-break detector** (record every leaf height, set `body.style.overflowWrap='normal'`,
> re-measure, report anything *taller* with the shared rule than without). **Two pages needed a fix,
> both in the page's own inline `<style>`; `base.css` is untouched.** (1) **`index.html`** — the
> in-app viewer's densest `.pgctl` row (Clean, four sliders, Mirror/HD/Loupe/Callouts/Reset) is a
> flex row with no wrap, so below ~960px every control is shrunk narrower than its own label, and
> `[1.57.0]`'s shared `body{overflow-wrap:break-word}` then split four labels **mid-word**: measured
> at 720px, `contrast` 16→32px, `zoom` 16→32px, and Mirror/Loupe/Callouts/Reset 52→71px each,
> rendering as `Mirr / or`, `Loup / e`, `Callou / ts`, `Rese / t`. **No overflow check would have
> found this** — the row's `scrollWidth` and `clientWidth` were both 688px either way.
> `@media(max-width:960px){.pgctl{flex-wrap:wrap}}` returns every button to natural width at a
> uniform 33px with its label whole, for 18px of toolbar height (`.vbar` 249→267px), and the
> detector then reports zero breaks. This is the first page where `[1.57.0]`'s own honestly-declared
> `break-word` trade came due. Scoped at 960, beside — not merged into — this file's own 920px block,
> which keeps its separate job (collapsing `main` and the `.vside` rail, both re-verified at 720px).
> (2) **`handover.html`** — `.card` is `overflow:hidden` for its rounded corners, so a table wider
> than the card is cut off with **no scrollbar and nothing on screen to say a column is missing**:
> measured at 720px, a 1299px table inside a 670px card, 629px simply gone.
> `@media(max-width:960px){.card{overflow-x:auto}}` makes it reachable, keeps `overflow-y:hidden`,
> keeps the corners. **Honest scope:** latent, not observed — both *wired* tables fit at 720px with
> realistic rows (hyphenated NSNs, a superseded `MS51922-17`); the two that would hit it first render
> raw `JSON.stringify` output (which `overflow-wrap` cannot break, because it does not affect a table
> column's min-content width) and are not wired server-side yet, as the page's own notes say.
> **The other ten needed nothing**, confirmed rather than assumed — notably **`circuitlab.html`**,
> flagged up front for its canvas/SVG stage: the `194px 1fr 236px` shell still fits at 720px (stage
> 290px) and 960px (530px), and the stage is **not** distorted or mis-tiled — its background grid
> `<rect>` measures exactly the stage width at both. One scare was chased to ground rather than
> written up as a bug: a stale 530px grid rect after resizing turned out to be the *harness*, since
> CDP device-metrics emulation changes the viewport without firing `resize` and this page redraws on
> `window.addEventListener("resize", draw)`; dispatching it manually snapped the grid to 970px, and a
> fresh load at each width is correct. Also confirmed: A1's `↗` pop-out buttons from `[1.55.0]` are
> fully on screen in the Tools dropdown at 720px (289px wide, left 138 / right 427). **One real
> collision found and deliberately NOT fixed here:** the bottom-right pill cluster overlaps itself
> (`#vw-read-btn` 458→524, `#bench-pill` 503→570, `#cmdk-pill` 552→708 — 21px and 18px). It is *not*
> a responsive bug: re-measured at **1500px** the identical overlap is present, so it is
> width-independent, pre-existing, and lives in shared `palette.js`/`readaloud.js` chrome affecting
> all 48 pages — exactly the shared-file change most likely to conflict with the three sibling
> batches in flight. Recorded, not lost; it belongs in its own PR. New
> `engine/tests/test_responsive_batch2.py` — **49 checks, 49 passed** — parses each page's inline
> `<style>` **with CSS comments stripped first** (both fixes carry doc comments naming the very
> properties they set, so a naive substring search would pass on the prose alone), brace-matches the
> `@media` blocks, and asserts each fix exists, is scoped to its measured breakpoint and not global,
> that the pre-existing 920px/`.card`-`overflow:hidden` rules survive, that all 12 pages still link
> `/base.css` and declare a `width=device-width` viewport meta (without which a narrow browser lays
> out at ~980px and scales, and every rule verified here would silently never fire), and that the
> eight no-fix pages still have no page-local width breakpoint. **Negative-controlled**: with the two
> fixes programmatically removed it returns `45 passed, 4 failed`, exit 1.
> **`rps_lint` was checked before touching anything**, as the ES5 gate requires: of these 12 only
> `solve.html` and `help.html` are `ES5_REQUIRED` — and in the event **no inline `<script>` was
> touched on any page**, both fixes being CSS, so the ES5 question never arose. `RPS GATE: PASS`.
> Final full `verify_all.py --snapshot`: **`67 checks | 67 ok | 0 FAILED` · `ALL GREEN -- suites
> pass and every protected file matches the vault.`** All **64** `test_*.py` suites PASS, including
> the new `test_responsive_batch2.py`, `test_uiux_fixes.py` at 273/273 (the suite that string-splits
> `base.css` itself — the direct check that this PR did not disturb the shared sheet, which it does
> not touch) and `test_routes.py` at 296/296 with no sign of the known `/api/ask` timeout flake,
> plus `RPS GATE: PASS` and `safeguard verify: 737 files, 737 OK, 0 DAMAGED`.
> **It went green on the first attempt** — nothing re-run until it passed. Free disk was checked
> first (**38.5 GB** on `C:`), and **port 8894 was confirmed free** before starting, because
> `test_ingest_routes.py` binds it unconditionally and `[1.52.0]`/`[1.57.0]` both documented a
> confusing `IndexError` on `_popen_calls[0]` when a *different worktree's* copy of that suite
> already holds it (`allow_reuse_address` lets the second bind succeed on Windows, so requests reach
> the other process). With three sibling batches running the same suite concurrently tonight that
> was a live risk; it did not fire, and `test_ingest_routes.py` PASSed in 37.2s. As in `[1.57.0]`,
> the docs edits and the `ITERATION-SNAPSHOTS.md`/`ITERATION-DASHBOARD.html` regeneration recording
> the run necessarily happened *after* it — writing a result into the repo modifies the tree it just
> verified. **The confirmatory post-edit run then came back `67 checks | 66 ok | 1 FAILED`, and that
> one failure is reported rather than buried:** `test_routes.py`, on a single line —
> `FAIL GET /api/ask?q=... -> request error: timed out`, the known pre-existing flake `[1.57.0]`
> already names, and the one this PR independently measured while checking `ask.html` (a real
> `/api/ask` round trip takes ~25-30s here against the test's shorter timeout). Not this change's
> content — both fixes are CSS, `ask.html` needed none — it passed 296/296 in the run that went
> fully green, and standalone immediately after gave **296 passed, 0 failed** again; three sibling
> batches running the same suite concurrently is the plausible difference. `safeguard verify` was
> clean in both runs (737/737, 0 damaged). Shipped as `[1.59.0]`.
> **Reconciliation note (2026-09-04, thirtieth pass):** stage 3, PR 8 of the multi-window/multi-tab
> initiative — **responsive verification batch 1**, the first of the four per-page passes `[1.57.0]`
> deliberately left undone. `[1.57.0]` shipped the shared breakpoints and said plainly that not one
> real page had been opened in a resized window; this covers 13 of them — `part`, `procedure`,
> `torque`, `jobcard`, `bench`, `dossier`, `partdiff`, `locate`, `decode`, `fastener`, `pmcs`,
> `measures`, `readiness` — with the first five landing here because **PR 14 (A2, the per-page
> pop-out control) is blocked on exactly those.** Three sibling batches of the same pass are in
> flight in parallel and have claimed `1.59.0`/`1.60.0`/`1.61.0`, so this branch took the lowest
> free number rather than racing for one. **`engine/ui/base.css` is not touched** — neither defect
> found was a shared-layer problem, and shared-file edits are precisely what would collide with the
> three sibling batches. Method, since "verified" is the word most likely to be doing no work in a
> pass like this: the real server against the real 227,908-row corpus, every page loaded with a
> query that actually returns data (`alternator` / NSN `3040-01-521-7377` / `brake` / `5 TON` /
> `5310-01-359-2198`) rather than an empty shell, then measured in a real browser at 960px and
> 720px and swept to 360px with a probe that walks every non-fixed element in `body` for a right
> edge past the viewport and for internal `scrollWidth > clientWidth`. `readiness`'s fluids/
> intervals and `measures`'s external references return nothing on this machine (unbuilt data /
> needs the open internet), so those two were exercised with stubbed responses of the documented
> shape rather than counted as passing on a blank page. **Two real defects found, both fixed in the
> page's own inline `<style>`.** (1) `procedure.html`: `.side{width:420px;max-width:46vw}` next to
> `.steps{min-width:340px}` — **756px is the last side-by-side width** (348/348); at **755px** the
> row wraps, which makes the page taller, which brings in a 15px scrollbar, which drops the usable
> width to 740px and holds it wrapped (a stable equilibrium, reproducible, not a flicker) — and the
> rail then **keeps its 420px/46vw cap, landing 332-347px wide inside a 677-696px row**, so the
> scanned page a technician checks the steps against renders at under half the width sitting empty
> beside it. That held 755px→721px until `base.css`'s shared 720px rule took over. Closed with
> `@media(max-width:755px){ .side{width:100%;max-width:none} }`; after, 756px is unchanged and
> 755-721px gives a **677-711px** rail. **`[1.57.0]` predicted this band at ~20px; it is 35px** —
> the estimate came from the layout arithmetic alone and missed the scrollbar the wrap itself brings
> in. (2) `measures.html`: `.m`/`.em` are row-shaped flex containers that never declared
> `flex-wrap`, and neither name is in `base.css`'s shared wrap list — correctly, since those are
> shared names and these are the page's own (adding them there is the exact mistake `[1.57.0]`
> warned about for `.grid`). Content floor ~411px, so the page overflowed at **490px** (1px),
> **480px** (11px), **375px** (116px), pushing the `p.N ↗` citation link — the one control on the
> row — off the right edge. One `flex-wrap:wrap` on each. **Called out honestly as below this
> batch's own 960/720 anchors**, fixed anyway because 480px is a quarter of the same 1080p monitor
> the 960px anchor is half of, and because it provably changes nothing above 491px. The other
> **11 pages needed nothing**, and that is a per-page statement rather than a blanket one — see the
> `[1.58.0]` CHANGELOG entry for what was looked at on each. Also measured: all 13 at 720px with
> device emulation on (`pointer:coarse` matching, 44×44 minimums live), and at 960px with a coarse
> pointer forced, which is the case that matters since `jobcard`'s and `dossier`'s two-column grids
> are still live at 960px while collapsed at 720px — zero overflow in every combination.
> **Found, measured and deliberately NOT fixed:** the bottom-right fixed chrome (`#cmdk-pill`,
> `#bench-pill`, `#vw-footer`, `#vw-read-btn`) overlaps by 18×44/156×4/66×4/21×29 px — but the four
> overlap rectangles are **byte-identical at 1400px, 960px and 720px on a desktop pointer** (with a
> coarse pointer they are still there, touch sizing only growing the last pair 21×29 → 21×44, never
> creating them), so it is pre-existing and width-independent, comes from `palette.js`/`readaloud.js`/
> `base.css` chrome shared by all 48 pages, and belongs in its own PR rather than in one of four
> parallel batches touching the same files; `procedure.html` overflows 17px at 360px from its own
> deliberate `.steps{min-width:340px}` (the exact floor `[1.57.0]` used `:where()` to protect); and
> `fastener.html`'s 5-column table overflows 26px at 360px. Both are below any named scenario.
> **One trap worth carrying forward:** the server holds UI files in memory after first read, so the
> first post-edit measurement showed the fix doing nothing — it was not a bad fix, the browser was
> being served the pre-edit file. Every "after" number here comes from a server restarted on the
> edited tree, confirmed by `curl`-ing the page and grepping for the new rule before measuring.
> Tests: `test_uiux_fixes.py` 273 → **285** (12 new checks) guarding both rules, including a
> comparison of the two breakpoint numbers **read back out of both files** rather than restated;
> negative-tested — reverting both fixes gives `280 passed, 5 failed`, restoring gives 285/0. These
> are source-text assertions, **not layout measurements**; the layout evidence is the before/after
> numbers above. Shipped as `[1.58.0]`; `main` was at `[1.57.0]` when this branch was cut, and PRs
> 9-11 (the other three batches, covering the remaining 35 pages) are still open after this.
>
> **Reconciliation note (2026-09-04, twenty-ninth pass):** stage 3, PR 7 of the multi-window/
> multi-tab initiative — the **responsive baseline**, this app's first width-based breakpoints in
> `engine/ui/base.css`, and the design spec's priority 3. **Read the scope first, because it is the
> thing most likely to be misread: this is CSS only.** No `engine/ui/*.html` file is touched and
> **not one real page has been opened in a resized window and checked** — that is PRs 8-11, batched
> by the home nav's own 6 section groupings, where actual overflow and collision get found and fixed
> page by page. This PR is only the shared foundation those four inherit. The spec's premise was
> verified rather than trusted: before this change `base.css` held exactly three media queries and
> not one was width-based (`pointer:coarse`, `print`, `prefers-reduced-motion`), so the one sheet all
> 48 pages link contributed literally nothing to a narrow window, while eight pages had grown their
> own ad-hoc breakpoints at seven different numbers (1280/920/820/780/760/720/620) and the other
> forty had none. Two anchors, neither invented: **960px** is exactly half a 1080p monitor — the
> scenario `[1.53.0]`'s `VW.windows` turns from hypothetical into ordinary, since the whole point of
> a pop-out is reading `torque.html` at ~960 CSS px instead of ~1900 — and **720px** is the number
> four of this app's own pages already picked for themselves (`help`/`jobcard`/`solve` at 720-760,
> `part` at 760). Seven rules: a self-limiting `#vw-toast{max-width:calc(100vw - 24px)}` outside any
> breakpoint (`base.css`'s own chrome, and `[1.53.0]` made toasts routine with strings longer than a
> narrow pop-out is wide); at ≤960px `flex-wrap:wrap` on the row-shaped classes — **not a new
> convention but the app's own, finished**, since `.search` already declares it in 18 of 18 flex
> definitions, `.toolbar` 2/2, `.chips` 2/2, `.cols` 1/1, `.tools` 1/1, `.row` 7/8, `.bar` 8/14,
> `header` 5/9, `.tabs` 0/1 — plus `min-width:0` on layout-container children (generalising a lesson
> `index.html` had already learned locally twice, in its `minmax(0,1fr)` comment and its own
> `.vside{min-width:0}`), `body{overflow-wrap:break-word}` so an unbreakable NSN cannot scroll the
> page sideways, `max-width:100%` on `img`/`video`/`iframe` (`svg`/`canvas` excluded — the
> 3-D/deep-zoom/circuit stages size theirs by script), and a `.grid2` collapse; at ≤720px `.side`
> stacks full-width. **The thing that would have made the whole PR inert:** `base.css` is linked
> *before* every page's inline `<style>` and a media query adds no specificity, so a plain
> `.grid2{...}` written here loses to `part.html`'s later equal-specificity rule — it would parse,
> match, and be silently overridden. Every rule therefore picks its weight deliberately: `:where()`
> at specificity 0 for the safety nets any page must stay free to override, a bare selector where no
> page declares that property at all, and `body .x` only where it genuinely has to win.
> **Deliberately not done, and worth knowing because it is the obvious move:** `.grid` is not
> collapsed — it means an explicit `1fr 1fr` split on 5 pages (all already collapsing themselves at
> 720-820px) *and* an `auto-fill` card grid on 6 others that already reflows, so one blanket rule
> cannot be right for both; per-page judgement belongs in PRs 8-11. Also dropped: tightening
> `.wrap`'s padding, since 2 of the 44 `.wrap` pages use it as a full-viewport app shell with no
> padding at all. Verified three ways, there being no CSS linter here: a brace/comment audit (`{`57 =
> `}`57, depth never negative, `/*`31 = `*/`31); a **real browser made to parse the file**, reading
> back `document.styleSheets[…].cssRules` (43 top-level rules; all five media rules intact with every
> inner rule — `(max-width: 960px)`:5, `(max-width: 720px)`:1 — nothing silently dropped, `:where()`
> included); and a cascade harness reproducing the real load order (this `base.css`, then a second
> `<style>` holding verbatim copies of `part.html`'s `.grid2`, `procedure.html`'s
> `.cols`/`.steps`/`.side`, `solve.html`'s `header`/`.bar`, `collections.html`'s `.grid`) served over
> HTTP and measured with `getComputedStyle` at 1200/960/720/400px. That harness proves three things:
> at 1200px **every value is byte-identical to before the change** (inert above the breakpoint, R1);
> at 960px the `auto-fill` `.grid` still shows 3 columns and `procedure.html` still keeps its
> intentional `.steps{min-width:340px}`, so the specificity-0 choice really does let pages win where
> they should, while `.grid2`/`.side` show `body .` really does beat a page where it must; and at
> 400px `scrollWidth` 400 = `clientWidth` 400 with no horizontal overflow, where toggling that same
> live page's `base.css` to `disabled=true` makes the identical markup overflow to **534px**.
> **Explicitly not proven:** how the other 44 real pages actually look at 960px — the harness holds
> copies of four pages' rules and says nothing about the rest; only a human resizing each one does,
> which is PRs 8-11. Final full `verify_all.py --snapshot`: **`64 checks | 64 ok | 0 FAILED` ·
> `ALL GREEN`** — all 61 `test_*.py` suites PASS including `test_uiux_fixes.py` at 273/273 (the suite
> that string-splits `base.css` itself to assert on its kiosk-mode and `pointer:coarse` blocks, and
> therefore the direct check that inserting a new section did not disturb them), `RPS GATE: PASS`,
> `test_routes.py` PASS with no sign of the known pre-existing `/api/ask` timeout flake, and
> `safeguard verify: 734 files, 734 OK, 0 DAMAGED`. **Getting there took three full runs, and both
> intermediate failures are written down rather than re-run until green — neither was this change's
> content.** Run 1: every suite PASS, `63 ok | 1 FAILED` on `safeguard verify` naming `base.css`,
> `HANDOFF-NOTE.md` and `MASTER-RECONCILIATION.md` as `MODIFIED (grew / edited)` — self-inflicted
> ordering, since `--snapshot` baselines at the *start* of a ~3.5-minute run and those three were
> still being edited while it was in flight (nothing truncated or shrunk; all three grew by exactly
> the bytes edited). Run 2: every suite PASS but `safeguard verify` crashed with a
> `FileNotFoundError` on a missing `manifest.json` — root-caused, not guessed: `verify_all.py` calls
> `safeguard.py verify` with **no** snapshot id, so `latest_snapid()` picks the last `SNAP_*`
> directory, which after a full run is one the *tests* created (`ingest_feature.py` snapshots
> `pre-ingest` before every ingest; `[1.53.0]`'s own entry records exactly that, so the behaviour is
> long-standing), and one of those had a `files/` dir but no manifest after an aborted launch — all
> inside `backups/`, which is **gitignored and not part of this PR**. Verifying against run 2's own
> baseline (`safeguard.py verify --snap SNAP_20260903_230713_verify_all`) gave **734 files, 734 OK, 0
> DAMAGED**, and after removing that garbage directory a plain verify gave the same. Run 3:
> `62 ok | 2 FAILED` — `test_routes.py` (the known `/api/ask` timeout flake, 295 passed / 1 failed)
> and `test_ingest_routes.py` with `IndexError` on `_popen_calls[0]`, traced to that suite's
> **hard-coded port 8894** already being `LISTENING`, held by a `test_ingest_routes.py` process
> whose parent shell belonged to **a different worktree** — one of the sibling PRs being built in
> parallel on this machine, looping the same suite. `allow_reuse_address` lets the second bind
> succeed on Windows, so requests reached the other process, whose `Popen` was not the one this run
> patched; this is exactly the false-failure mode `[1.52.0]` already documented for this file
> ("checks depend on process-global state and a fixed port"). Their processes were **left alone**;
> once 8894 was free, `test_ingest_routes.py` standalone → **175 passed, 0 failed**, and the final
> run came back ALL GREEN. The docs edits + snapshot regeneration recording this necessarily happened
> *after* that green run (writing a result into the repo modifies the tree it just verified — run 1's
> exact trap), so a confirmatory post-edit run on the finished tree is reported in the PR body
> instead. `1.54.0` was reserved up front when this branch was built in parallel with two sibling
> PRs that went on to claim `1.55.0`/`1.56.0`; both merged first while this PR was still under
> review, so on merge it takes the next free number instead — `[1.57.0]`, not `[1.54.0]`.
> Shipped as `[1.57.0]`. `main` is at `[1.57.0]`.
>
> **Reconciliation note (2026-09-03, twenty-eighth pass):** stage 4, PR 13 of the multi-window/
> multi-tab initiative — `VW.bench`, and **the first change in this initiative a technician can
> actually see.** PRs 1/2/5 built plumbing nothing rendered; feature D is the first real UI consumer
> of `[1.51.0]`'s `VW.channel`: pin a part on one page, watch it appear on `/bench` in the other
> window, no reload. The same two-line bench read/write pair had been written out twice,
> independently — inline in `bench.html` and again in `palette.js`'s ☆ pin pill — both parsing the
> same `viewer_bench` key, both re-applying the same 100-entry cap, neither knowing the other
> existed. Promoted into `shared.js` as `VW.bench.get()`/`VW.bench.put(list)`, keeping the stored
> shape and the cap byte-for-byte, and `bench.html`'s local copy is **deleted**, not kept as a
> fallback. `get()` now returns an array unconditionally (a stored JSON *object* used to make
> `palette.js`'s pin fail silently, since its pin path called `.filter` on whatever came back — a
> real live bug, not a hypothetical), and `put()` returns a real true/false so a caller can tell a
> stored bench from an unstored one. Every write publishes a deliberately thin `{action, count, at}`
> on `VW.channel` — storage is already shared across tabs on this origin for free, so the message is
> only "re-read and repaint", never a second copy of the truth; the write happens first and the
> notification second; reads publish nothing. **Conflicts are last-write-wins with no merge**, per
> the design spec and unchanged since scoping — merging would trade a rare, immediately visible
> surprise for a permanent family of subtle ones (rows the user explicitly removed coming back).
> `palette.js` routes through `VW.bench` too, which is what makes D real rather than scope creep:
> the pin pill performs nearly every actual bench write in the app, so without it the only sync that
> would ever fire is one `/bench` tab editing while a *second* `/bench` tab is open. It keeps its
> direct `localStorage` path for exactly `circuitlab.html` and `scan.html` — the only two pages that
> load `palette.js` without `shared.js`, both of which show the pin pill — and that is not a
> redundant copy of live logic, since a page with no `shared.js` has no `VW.channel` to notify with
> either. Verified with **77 checks** in `engine/tests/js/test_bench_node.js`: two
> `vm.createContext()` sandboxes sharing one `localStorage` object (exactly what two tabs on one
> origin have), a real `BroadcastChannel` between them, a controllable clock, the storage-event
> fallback transport, seven shapes of corrupt stored value, storage that refuses reads and storage
> that refuses writes, last-write-wins with nothing merged, and that a read, a refused write and a
> rejected argument all publish nothing. **Adversarially checked with 7 injected mutations, all 7
> caught** — and two of those runs improved the test rather than confirming it: dropping the publish
> originally *crashed* the run instead of reporting failures (the record is now defaulted), and the
> non-array guard originally *survived* until an array-like stored object was added as a fixture,
> which is the one shape only that guard rejects. A third mutation attempt was itself wrong and is
> worth remembering: the first patch aimed at `benchGet`'s guard silently hit `_wsRead`'s
> byte-identical line higher up the file and "survived" for that reason alone — caught by printing
> the mutated function back out rather than trusting the patch. `rps_lint` caught one more ES5 false
> positive, the third time this initiative has hit that class: the plain-English phrase "a permanent
> **class of** subtle ones" in a doc comment, which the linter's blunt text scan reads as a `class`
> declaration. Reworded, not suppressed. **Owed manual check, not automatable here:** two real
> browser windows — `/bench` in one, any page in the other, click ☆ pin, confirm the row appears
> with no reload; then remove a row and confirm the other window repaints. `1.54.0`/`1.55.0` are
> claimed by sibling PRs from this same initiative built in parallel off the same `main`, so this
> branch reserved `[1.56.0]` from the start rather than race for a number. **Two `verify_all`
> failures were chased rather than re-run until green.** `safeguard verify` reported exactly two
> files `MODIFIED` and was self-inflicted: a line-ending normalization ran *after* that pass's own
> snapshot was taken, silently converting `engine/viewer_app.py` and `docs/PROJECT-SUMMARY.md` from
> CRLF to LF — the byte deltas match their line counts exactly (`+805`, `+1032`), `git diff --stat`
> never moved because `core.autocrlf=true` normalizes both forms to the same committed content, and
> both files were restored to CRLF. `test_ingest_routes.py` died on an `IndexError` at
> `_popen_calls[0]`, passed **20/20** standalone (10 on this branch, 10 more with `main`'s own copies
> of every file this PR touches checked out over it), and was then **reproduced deliberately**: two
> instances run concurrently fail **6/6**. The cause is in that test file — it binds a **fixed port
> 8894** and mutates process-global state (`V._EXPOSED`, `V._AUTH_TOKEN`, `VIEWER_INGEST_ROOTS`), so
> a second instance's requests reach the other process's server, whose mocks and `_popen_calls` list
> are different ones. That port is machine-wide, not per-worktree, which matters because sibling PRs
> from this initiative are being built in parallel in other worktrees on this same host. Same suite
> and same class of sensitivity `[1.52.0]` already documented; deliberately left alone rather than
> fixed in an unrelated PR, and written down rather than left as folklore.
> Shipped as `[1.56.0]`. `main` is at `[1.56.0]`.
>
> **Reconciliation note (2026-09-03, twenty-seventh pass):** stage 4, PR 12 of the multi-window/
> multi-tab initiative — **A1, home nav pop-out links**, and the first real UI consumer of
> `[1.53.0]`'s `VW.windows`, which until now had nothing calling it outside its own tests. All 30
> entries in `index.html`'s Tools nav are now rows carrying their **original, byte-for-byte unchanged
> `<a>`** (same href/title/label — still navigates in place, still ctrl/middle-clickable into a tab
> exactly as before) plus an adjacent ↗ button that opens that same section in its own reusable
> window via `VW.windows.open(url, {name})`. The ↗ is an *additional* affordance, never a
> replacement: the spec's framing is that this app could always open things in new tabs and what was
> missing is discoverability, not capability. Each pop-out is a real `<button type="button">` — in
> the tab order, picking up `base.css`'s shared `:focus-visible` outline — with its own `aria-label`
> naming its own destination, not a bare icon; confirmed live in a real browser (all 30 report
> `tabIndex 0`, each exposed by full name in the accessibility tree), because an unlabeled icon
> target is exactly what the `[1.46.0]`/`[1.47.0]` a11y passes went through this app to remove. Two
> load-bearing decisions: the **url is read off the sibling link at click time**, not baked into the
> button, so the menu's existing `threadQuery()` (which rewrites every href on every open so the
> current search carries into the tool) is not silently defeated; and the **window name is derived
> from the base path with the query stripped** (`/torque?q=bolt` → `vw-torque`), because the name is
> the entire reuse mechanism and must be identical across clicks while the href is not — derived in
> one function rather than 30 hand-written `data-` attributes so a copy-paste collision (one row
> stealing another's window) is impossible, and keyed to the *destination page* so A2's
> `popoutControl()` (PR 14) can name its window the same way and land on the same one. The Tools
> popup's existing "any button in here closes the menu" rule now exempts `.popout` (popping several
> sections out in a row is the whole point, and closing after each would force a re-open per pop-out
> and discard the focus just placed); `#pnReviewBtn` still closes it and deliberately gets no
> pop-out, being a modal opener rather than a link. Deliberately untouched: the three header pills
> (Collections/My Bench/Help — a `flex` row that already wraps, and all still ctrl-clickable) and the
> `#legacyHome` ES5 fallback's link list (the capability ladder puts the legacy tier at "no advanced
> affordances at all"); the gate protecting that fallback is asserted still green by the new test.
> `index.html` is `MODERN_BY_DESIGN` per `rps_lint.py` — checked in the gate's own output before any
> JS was written, not assumed — but the wiring is ES5 `var`/`function` anyway, since it lives in the
> same IIFE as the Tools-menu toggle, which *is* ES5 and does run on legacy hardware. Verified with
> **36 checks** in the new `engine/tests/test_home_nav_popout.py`, against the real shipped markup
> (every link in a row beside exactly one pop-out; no link missed, proved by stripping the rows and
> finding nothing left; every `aria-label` non-empty and naming its *own* row; every href still a
> registered route, cross-checked against `features/routes/*.py`; unique, query-stable window names;
> the wiring really calling `VW.windows.open` with a name; `/shared.js` loaded and loaded first;
> `node --check` on the inline scripts; the ES5 fallback span still clean) — and checked for
> vacuousness with **7 injected mutations**, all caught. That mutation run **found a real bug in the
> test itself**: its diagnostic print crashed with `UnicodeEncodeError` on a cp1252 console (the nav
> labels are emoji-heavy), turning a clean FAIL into a swallowed exception and skipping every later
> assertion in that block; fixed with an ASCII-safe helper and re-run. **Explicitly manual and still
> owed**, in the same framing `[1.53.0]` used for the layer underneath: that clicking ↗ opens a real
> separate window and that a second click *refocuses* it rather than opening a third. The embedded
> preview browser refuses popups outright (`window.open()` returned `null` and navigated in place),
> so reuse is unobservable there — though that did usefully exercise `VW.windows`'s documented
> blocked-popup path for real (null returned; toast, registry write and broadcast all correctly
> skipped, no error). What *was* observed live: the menu renders correctly, and at a 375px viewport
> with a coarse pointer each pop-out measures exactly 44×44 via the existing
> `@media (pointer:coarse)` rule, with no row overflow and no horizontal page overflow. `1.54.0` and
> `1.56.0` are claimed by sibling PRs built in parallel off the same `main`, so this branch reserved
> `[1.55.0]` from the start rather than race for a number; `main` is at `[1.53.0]` until this merges.
> No `shared.js` change — this PR only *calls* the already-merged `VW.windows.open` and needed
> nothing new exported. **One real, previously-undocumented test-infrastructure hazard was found and
> run to ground on the way through, worth knowing before the next session hits it:**
> `test_ingest_routes.py` serves its in-process `ThreadingHTTPServer` on a **fixed** port (8894), and
> `ThreadingHTTPServer.allow_reuse_address` is `1` by stdlib default — so on Windows a second bind of
> a port another process already holds **succeeds silently**, and the client's requests are answered
> by the *first* listener. With sibling agents running the same suite concurrently on this machine,
> that suite failed hard (`IndexError`, no results printed) because the route reply came from
> *someone else's process*: it said "A scan/OCR run is already in progress" while this process's own
> `_INGEST` (same module object, id-checked) still read `{"proc": None}` and its mocked
> `subprocess.Popen` had recorded nothing. `netstat` confirmed a foreign `python3.13` on 8894 with a
> different PID each run; the mechanism was reproduced in isolation (second bind raises nothing, all
> requests `answered-by-FIRST`); and a copy of the suite differing **only** by `PORT = 8897` ran
> `175 passed, 0 failed` on this exact tree. Pre-existing, unrelated to A1 (that suite mentions
> nothing this PR touches), and deliberately left alone rather than fixed in an unrelated PR — an
> ephemeral port, or `allow_reuse_address = 0` so a collision fails loudly instead of silently, is a
> real change to a suite this PR does not otherwise go near.
>
> **Reconciliation note (2026-09-03, twenty-sixth pass):** stage 2, PR 5 of the multi-window/
> multi-tab initiative — `VW.windows`, the one shared window-opening path, built on `[1.51.0]`'s
> `VW.channel`. `VW.windows.open(url, opts)` makes the *named* form of `window.open` the ergonomic
> default (passing the same name twice is how a browser natively reuses a window, and it is the thing
> every call site forgets), and layers on the three things a bare call site cannot do for itself: an
> in-tab registry (`VW.windows.registry()` reports `[{name, url}]`, the hook PR 6 extends with real
> window bounds), a broadcast of every open on `VW.channel`'s `"windows"` channel (plumbing for a
> future cross-tab "N windows open" — nothing renders it yet), and an instant toast on open *and* on
> refocus, reusing `shared.js`'s existing `toast()` — design priority 2's "snappy UI", aimed squarely
> at the reuse case, where a reused window can come forward behind the current one and the click
> otherwise looks like it did nothing. Limits documented in the code, not left to be discovered:
> the registry is per tab, in memory, and is a best-effort mirror of the browser's own named-window
> table rather than the truth (closed windows are pruned on every read); an unnamed open still opens
> and toasts but cannot be tracked at all; a blocked or throwing `window.open` returns `null` and
> skips the toast, the registry write and the broadcast alike. Verified with 48 checks in
> `engine/tests/js/test_windows_node.js`: the real `shared.js` in a `vm` sandbox with a **mocked
> `window.open`** that records every call, asserting what the production code actually did (same name
> twice → ONE registry entry while still really calling `window.open` again; different names →
> separate entries; unnamed → no entry but still a toast; blocked/throwing → null, no toast, no
> broadcast; closed-window pruning; a copy-on-read registry), plus the broadcast delivered *unmocked*
> to a second sandbox over Node's real `BroadcastChannel`. The test was checked for vacuousness by
> deliberately breaking `shared.js` three ways and confirming the right checks flipped to FAIL — which
> caught a real weakness in an earlier draft (a toast assertion that compared text and so missed a
> wrongly-repeated identical message; it now counts real DOM writes). **Explicitly not proven and not
> provable here: that a real browser reuses a named window** — that is browser behavior, not this
> codebase's; a human opening a pop-out twice in a real browser is the only check for it, called out
> as manual in the PR. `rps_lint` caught one ES5 false positive on the way (the word "let" in a doc
> comment, the same class `[1.51.0]` hit twice) — reworded, not suppressed. `1.52.0` is claimed by a
> sibling stage-2 PR (`VW.workspace` CRUD, the twenty-fifth pass below) built in parallel off the
> same `main`, so this branch reserved `[1.53.0]` from the start rather than race for a number; that
> sibling has since merged and this branch was rebased onto it, with the real `shared.js` conflict
> (both PRs add a block just above the `VW` export) resolved by keeping both, `VW.workspace` then
> `VW.windows`, and both suites re-run green afterward. `main` is at `[1.52.0]` until this merges.
> Nothing calls `VW.windows` outside its own tests yet. One pre-existing flake was found
> and run to ground rather than re-run until green: a second confirmatory `verify_all.py --snapshot`
> came back `62 ok | 1 FAILED` on `test_hardening.py`'s `cross-origin POST -> 403 (J68)` check (the
> first full run was `63 ok | 0 FAILED`); it failed 2/30 standalone runs on this branch and, with
> `main`'s own `shared.js`/`viewer_app.py` checked out over this branch's, **1/60** on genuinely
> pristine pre-`1.53.0` code — same check, same rate, no `VW.windows` present. Intermittent and
> pre-existing, not a regression from this PR (nothing here runs server-side); deliberately left
> alone rather than fixed in an unrelated PR, and written down rather than left as folklore.
>
> **Reconciliation note (2026-09-03, twenty-fifth pass):** second implementation PR of the
> multi-window/multi-tab initiative (`docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md`,
> stage 2, PR 2 of 18) — `VW.workspace`, the data behind "reopen everything I had open for this
> job": `create/list/get/touch` over a record of `{id, name, items: [{page, params}], created,
> lastOpened, source}`, stored as one JSON **array** under a new `viewer_workspaces` localStorage
> key (an array, not an id-keyed object, because `list()` is the dominant read and an array
> preserves a stable creation order for free — documented in the code itself, not left implicit).
> CRUD only: export/import (PR 3) and templates (PR 4) build on this exact shape and are
> deliberately not here. Every mutation publishes on `[1.51.0]`'s `VW.channel` with a deliberately
> thin `{action, id, name, at}` payload — `localStorage` is already shared across tabs on this
> origin for free, so a second tab does not need the data pushed to it, it needs to be *told* to
> re-read and repaint (the same philosophy the design spec describes for D, Bench sync); the write
> happens first and the notification second, so a reacting tab always reads an already-committed
> value, and read-only calls publish nothing. Verified with a genuinely real test, not a
> reimplementation: two `vm.createContext()` sandboxes stand in for two tabs **sharing one
> `localStorage` object** — exactly what two tabs on one origin have — so tab A creates, tab B is
> notified over Node's real global `BroadcastChannel`, and tab B then really finds the workspace
> through its own `list()`. 73 checks, all passing, including a controllable clock that makes
> "touch moves `lastOpened`" a real observable change rather than a vacuous same-millisecond
> assertion. Adversarially checked by injecting 6 real mutations: 5 caught; the 6th (dropping the
> id generator's random suffix) survives because the collision-regeneration guard independently
> preserves uniqueness — confirmed directly and reported as the equivalent mutant it is, not
> papered over. `rps_lint` clean on `shared.js` first try this time. Full `verify_all --snapshot`:
> **63 checks, 63 ok, 0 FAILED, ALL GREEN** — but reported rather than quietly re-run, the *first*
> pass showed 1 failure (`test_ingest_routes.py`, 5 auth/fence checks) that was self-inflicted:
> three other suites were being run by hand concurrently with it, one standing up its own live
> server, against a test file whose checks depend on process-global state and a fixed port. Disk
> was checked first (48G free, so not `[1.51.0]`'s low-disk cascade); that file then passed
> standalone twice at 175/175 and the clean full re-run came back 63/63. Nothing calls
> `VW.workspace` yet outside its own tests; `VW.windows` and the consuming features follow.
> Shipped as `[1.52.0]`. `main` is at `[1.52.0]`.
>
> **Reconciliation note (2026-09-03, twenty-fourth pass):** first implementation PR of the
> multi-window/multi-tab initiative (`docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md`,
> 18 PRs across 5 stages) — `VW.channel`, a real cross-window publish/subscribe layer in
> `shared.js`: `BroadcastChannel` primary transport, `storage`-event fallback for RPS/legacy
> browsers, per-(channel,tab) sequence numbers for gap detection, schema versioning, an explicit
> oversized-payload guard on the fallback path. Verified with a genuinely real test, not a
> reimplementation of the logic under test: two independent `vm.createContext()` sandboxes stand in
> for two browser tabs, sharing Node's real global `BroadcastChannel` constructor — 16 checks, all
> exercising production code against a real `BroadcastChannel` implementation. Caught and fixed two
> `rps_lint` false positives along the way (backticks/ellipses in my own doc comments — the linter's
> text scan doesn't distinguish comments from code). Nothing calls `VW.channel` yet outside its own
> tests; `VW.workspace`/`VW.windows` and the consuming features (D, then B/F/C/G) follow in
> subsequent PRs. Shipped as `[1.51.0]`. `main` is at `[1.51.0]`.
>
> **Reconciliation note (2026-09-03, twenty-third pass):** the final, fresh `verify_all.py --snapshot`
> pass at the actual release-cut point (same independent-verification discipline every change this
> session has followed) found something worse than `[1.49.0]`'s hang: `test_patterns.py` was failing 3
> real-looking checks against `patterns.tm_side("TM 9-2320-280-10")` on a file `git diff` showed was
> byte-identical to its committed source. Root cause: `mutate.py`'s restore step only ever rewrote the
> target's *source text* (SHA-256 verified) — it never touched the *derived bytecode cache* a subprocess
> `import` during a mutant's test window leaves in `__pycache__/`, keyed by mtime+size. The rapid
> mutate/restore cycle can alias a mutant's cached `.pyc` onto the restored original's mtime+size, so the
> cache silently outlives the source it no longer matches — and every later process that imports the
> module, **including the actual running application**, inherits the mutant's logic invisibly. This sat
> undetected for two real days before this pass caught it. Fixed: `mutate.py` now purges the target's
> cached `.pyc`/`.pyo` after every restore (both per-mutant — the one that actually matters, since a
> hard-killed run like `[1.49.0]`'s own incident skips final cleanup entirely — and in the final cleanup).
> Verified directly: re-ran mutation testing against `patterns.py` with the fix, confirmed no `.pyc`
> survived and `tm_side()` was immediately correct with no manual intervention. Every `__pycache__/` under
> `engine/` was purged as emergency remediation, and every test file whose module was a mutation target
> this session was re-run clean. A second, unrelated issue in the same pass: `test_ingest_routes.py`'s
> real e2e upload check now exceeds its hardcoded 15s HTTP timeout, because `_launch()`'s real, by-design
> synchronous `safeguard.snapshot()` cost has grown past that budget as the project has accumulated
> hundreds of tracked source/doc/diagram files — reproduced the underlying pipeline by hand (works
> correctly, ~1-2s once running), and widened just that check's timeout to 60s rather than touching the
> feature. Shipped as `[1.50.0]`. `main` is at `[1.50.0]`.
>
> **Reconciliation note (2026-09-01, twenty-second pass):** running `RUN-MUTATION.bat`'s 7-step
> mutation-testing sequence as direct commands (pre-release verification) surfaced a real bug in the
> project's own test tooling: `tests/mutate.py --target procedure_feature.py` hung for 5+ hours past its
> own `--timeout 60`, silently, with no crash and no output. Root cause: a mutant (`i += 1` → `i -= 1` in
> the blank-line-skip branch of `parse_procedure()`) puts the parser into a genuine infinite loop, and
> `run_test()`'s `subprocess.run(cmd, shell=True, timeout=...)` only kills the intermediary `cmd.exe` on
> Windows timeout — the real hung test process survives as an orphaned grandchild holding the stdout pipe
> open, so `communicate()` never sees EOF and never returns. A second run (`rps.py`, step 4/7) was killed
> pre-emptively before repeating the same hang once the pattern was recognized. **Fixed**: `run_test()`
> now kills the whole process tree on timeout (`taskkill /F /T` on Windows). Verified directly: a
> deliberately-hanging grandchild now times out in ~3s under a 3s cap (previously unbounded); normal
> pass/fail exit codes unaffected; a full real run against `patterns.py` still restores source and passes
> SHA-256 verification. Both mutated source files (`procedure_feature.py`, `rps.py`) were left corrupted
> on disk mid-run by the hang and were restored from their `.orig` backups before anything else touched
> them. Shipped as `[1.49.0]`. `main` is at `[1.49.0]`.
>
> **Reconciliation note (2026-09-01, twenty-first pass):** running `VERIFY.bat`'s full per-module
> self-test loop (~68 modules) as part of pre-release verification — a check `verify_all.py --snapshot`
> doesn't cover — surfaced two more instances of the exact env-assumption bug this session already fixed
> twice the same day (`test_routes.py`, `test_pageqa.py`): a hardcoded assumption that
> `transformers`/`torch` are never installed, broken once `sentence-transformers` pulled them in earlier
> this session. `engine/vlm.py`'s self-test called `ask()`/`ground()` with no explicit backend, relying
> on `_load_backend()` finding nothing — once `vlm_backend.py`'s default Florence-2 backend became
> importable, `available` flipped from the expected `False` to `True`. `engine/pageqa.py`'s self-test hit
> a subtler cascade: `pageqa.available()` is `vlm.available() and _gpu_tier()`, so once `vlm.available()`
> flipped, that gate silently passed on this real GPU-equipped machine and fell through to a real
> page-render attempt instead of the intended "no backend" short-circuit. Same fix both places: force
> `VIEWER_VLM` to a genuinely-nonexistent module name before the "no backend" assertions, matching the
> identical fix already applied to `test_pageqa.py`. Shipped as `[1.48.0]`. `main` is at `[1.48.0]`.
>
> **Reconciliation note (2026-09-01, twentieth pass):** an adversarial-verification pass on the
> nineteenth-pass accessibility work (`[1.46.0]`, directly below) found three real, confirmed,
> blocking issues, all fixed here and shipped as `[1.47.0]`. **(1) The "generalized" contrast guard
> couldn't actually catch compound-selector failures.** `verify_ui.py`'s `_is_pure_class_selector()`
> used the regex `^\.[A-Za-z0-9_-]+$`, which has no `.` in its character class — it could never match
> a multi-class token like `.tag.bad` (a second `.` before "bad"). `_parse_css_rules()` gated *both*
> the single- and compound-selector branches behind this one check, so every compound-selector rule on
> every page was silently discarded before parsing — the `compound` dict was provably always empty and
> that code path was dead, directly contradicting `[1.46.0]`'s own claim of closing "exactly the gap
> that let `status.html`'s real `.tag.bad` failure ship invisibly before" (`.tag.bad` **is** a compound
> selector). Confirmed via a real adversarial test: injecting a genuine severe-contrast rule as
> `.injectedbad.contrast{color:#333333;background:#222222}` into `status.html` was **not** caught (the
> scan's own pair count stayed at 146, 0 FAIL) before the fix. **Fixed**: the regex now matches
> one-or-more `.class` segments (`^(?:\.[A-Za-z0-9_-]+)+$`), so a single class still matches (one
> repetition) and a compound chain now also matches (two-plus repetitions) — `_classes_in()` already
> knew how to pull every class out of either shape. Re-ran the identical adversarial test after the
> fix: the pair count rose to 147 and the injected rule was correctly flagged `FAIL -- 1.26:1, below
> the 4.5:1 floor`; the injection was then fully reverted (`git diff` on `status.html` clean, 146/0
> FAIL restored). The scanner's real, corrected final state across the real 48 pages is **146
> class/descendant pairs, 117 OK, 0 FAIL, 29 SKIP** (vs. `[1.46.0]`'s claimed-but-never-actually-live
> 67/51/0/16). **(2) A disclosure-list count/list mismatch, repeated across all 5 canonical docs.**
> Every doc said "27 pages still carry zero ARIA" while enumerating exactly 30 names (`CHANGELOG.md`
> even self-flagged this: "that's 30 names", unresolved). Separately, `review.html` is genuinely
> zero-ARIA (confirmed: zero occurrences of `aria-`/`role=`), was untouched by `[1.46.0]`, and was
> absent from every one of the "named in full" lists in all 5 docs — despite `[1.46.0]`'s own stated
> ethos being "not silently implied as covered." **Fixed**: recounted the real zero-ARIA page set
> directly from `ui/*.html` (fresh grep, not trusted from the prior draft) — **31 pages** (32 total
> zero-ARIA pages minus `cadtex_test.html`, excluded on the same unreachable-route basis `[1.46.0]`
> already established), the 30 original names plus `review.html`. The number and the enumerated list
> now agree everywhere: `CHANGELOG.md`, `PROJECT-SUMMARY.md`, `MASTER-RECONCILIATION.md`,
> `HANDOFF-NOTE.md` (this file, nineteenth-pass note below), `ITERATION-SNAPSHOTS.md` (regenerated via
> `build_iteration_snapshot.py` from the corrected `CHANGELOG.md`, never hand-edited). **(3) A false
> "0 flakes / 61/61 GREEN" claim.** `[1.46.0]`'s PR body, `CHANGELOG.md`, this file, `PROJECT-SUMMARY.md`,
> and `ITERATION-SNAPSHOTS.md` all identically claimed "61/61 GREEN, 0 failures... no flakes needed
> this run." Three independent re-runs of `verify_all.py --snapshot` this pass never once reproduced
> that exact "0 flakes" outcome: the authoritative run (zero files touched anywhere in the repo for its
> whole duration) got **60/61**, `test_routes.py`'s pre-existing `/api/ask` timeout — re-ran
> `test_routes.py` standalone immediately after and reproduced the same timeout. An earlier run flagged
> `test_http.py`'s equally pre-existing `/api/pageqa` timeout instead; both are already documented as
> pre-existing, load-sensitive flakes in this repo's house rules, alongside `test_ingest_routes.py`.
> The specific "no flakes occurred" claim was still false as stated, whichever of the two actually
> fired on a given run. **Fixed**: this pass's own three `verify_all.py --snapshot` runs are reported
> exactly as observed, not assumed clean — see `CHANGELOG.md` `[1.47.0]` for the literal results,
> including the two runs whose `safeguard verify` failures were this pass's own concurrent doc edits
> (not real corruption) and the third, clean run that confirms it. No app behavior changed by this pass
> beyond `engine/verify_ui.py`'s regex fix; everything else is documentation correction.
>
> **Reconciliation note (2026-09-01, nineteenth pass):** a research pass re-verified `[1.29.0]`'s own
> accessibility disclosure against the real files (grepping all 48 pages for `aria-`/`role=`, reading
> `verify_ui.py`/`shared.js` in full) and found a correction to its own numbers: `status.html`'s
> `.tag.ok` was carried as a 3.10:1 WCAG failure, but that figure is base.css's un-overridden `--grn`
> — this page's own local `--grn:#2f9d63` override (loaded after `/base.css`, wins the cascade)
> actually measures 4.56:1, a genuine pass, left untouched. **Fixed for real:** `demo.html`'s full
> local `:root` token override (shadowing all 12 of base.css's tokens plus `--grn2`, which base.css
> lacked) removed — every value matched base.css exactly except `--red` (`#c4585a` vs. base's
> `#e0564f`), the direct cause of a real `.warn .n` contrast failure (3.94:1, below the 4.5:1 AA
> floor); fixed via the existing `--red-tx` text-safe token (now 6.13:1), `--grn2` moved into
> `base.css` itself. Two more confirmed real failures fixed the same way: `status.html` `.tag.bad`
> (4.18:1 → 5.65:1) and `index.html`'s 2 remaining inline `color:var(--red)` stragglers (recomputed
> at 4.53:1, a narrow existing pass — swapped anyway for consistency with the token convention its
> sibling spans already use, now 6.13:1). `schematics.html`/`threed.html`'s gate modals now carry
> `role="dialog" aria-modal="true"` + `VW.trapFocus()` — real dialog semantics and a real focus trap,
> not a copy-paste call site: both gates toggle open/closed via `classList.add/remove('on')` against
> a CSS rule, never touching the inline `style` attribute `trapFocus()` originally watched, so
> attaching it as-is would have silently never trapped focus (no error, no visible breakage — exactly
> the failure mode this pass exists to catch). `shared.js`'s `trapFocus()` generalized instead of
> touching either page's own open/close call sites: `isVisible()` now reads `getComputedStyle()`, the
> `MutationObserver` watches both `style` and `class`, and the Escape handler detects which
> convention is live before closing — verified live in a real browser for both pages, `index.html`'s
> 5 existing modals confirmed unaffected. `engine/verify_ui.py`'s WCAG contrast guard rewritten from a
> 3-pair hardcoded list (that only ever opened `base.css`'s/`index.html`'s own tokens) to a real
> per-page scan across all 48 `ui/*.html` pages, with cascade-aware token resolution (each page's own
> `:root{}` override layered on `base.css`'s) — exactly the gap that let `status.html`'s real failure
> ship invisibly to CI while its neighboring, visually-identical `.tag.ok` was actually fine. Building
> the new scan caught (and fixed) 2 more previously-unknown real failures outside the `--red`/`--grn`
> family this pass otherwise touched (`index.html`'s `.sheetprev .e`, 2.26:1 → 5.00:1;
> `measures.html`'s `.em .tagx`, 4.43:1 → 5.00:1), and one bug in the scanner's own logic (a
> descendant selector's self-declared background was being ignored in favor of its ancestor's —
> caught and fixed before landing). Baseline ARIA (`role="main"`, `aria-label`s on unlabeled inputs,
> `aria-live="polite"` result regions, dialog semantics) landed on 10 pages — `collections`, `threed`,
> `status`, `schematics`, `verify`, `jobcard`, `part`, `visual`, `procedure`, `demo` — scoped from
> real (thin) click-analytics traffic plus the pages already open for the contrast/modal work above.
> **Honestly left open, same disclosure convention as `[1.29.0]`**: 31 pages still carry zero ARIA of
> their own, named in full in `CHANGELOG.md` `[1.46.0]` (including `review.html`, restored to the
> list by a follow-up adversarial-verification fix — it was genuinely zero-ARIA but had been omitted
> from every one of the 5 canonical docs' lists in the original pass); `cadtex_test.html` confirmed
> unreachable through any route in `static.py`'s dispatch table and excluded from the ARIA pass on
> that basis.
> Shipped as `[1.46.0]`. Verified (as originally claimed when this pass shipped): `engine/tests/
> verify_all.py --snapshot` — **61/61 GREEN, 0 failures**, no flakes needed this run. **See the
> twentieth-pass note above: this "no flakes" claim, and the WCAG scan's compound-selector coverage
> claim above, were both found false by adversarial verification and corrected in `[1.47.0]`.**
> One pre-existing, unrelated failure found (not fixed, out of scope) while running `verify_ui.py`
> standalone: `index.html` declares an inline `function esc(...)` while also loading `/shared.js`,
> tripping the separate shared.js-dedup guard — confirmed present on `origin/main` before this branch,
> not reachable from `verify_all.py --snapshot`'s own suite.
>
> **Reconciliation note (2026-09-01, eighteenth pass):** `hybrid.hybrid_search()` (behind
> `/api/search_hybrid`, the search UI's primary endpoint) called `embed.search()` but kept only
> `.get("results")`, discarding `ready`/`stale` entirely — the only trace of semantic-index health
> reaching the UI was `signals.semantic === 0`, identical whether the index was never built, stale,
> mid-rebuild, or the query just had zero semantic matches. There was also no way at query time to
> tell "never built" apart from "actively rebuilding" — `build_index()` writes
> `embeddings.progress.json` while a rebuild runs, but nothing read it. **Fixed**: new
> `embed.semantic_status(index_dir)` (`engine/embed.py`) reads `embeddings.progress.json` for a live
> percent-complete and returns one honest state — `ready`/`never_built`/`rebuilding`/`stale`;
> `hybrid_search()` forwards it as a new top-level `semantic_status` field, unrelated to the unchanged
> `signals` block. New `renderSemanticStatus(d, q)` in `engine/ui/index.html`, styled identically to
> the existing `renderSearchHints()` quiet `.searchhints` card (`afterbegin` into `#results`) —
> deliberately not `shared.js`'s `_staleBanner()` treatment (fixed/red/non-dismissible), which stays
> reserved for the unrelated code-version-mismatch emergency. Shown only when semantic search isn't
> `ready` **and** the search actually returned keyword results, so it never displaces the "No matches"
> empty state. Dismissible per-state via `sessionStorage`, so dismissing one state doesn't suppress a
> later different one. Four distinct copy strings (nothing renders when `ready`) — see `[1.45.0]` in
> `docs/CHANGELOG.md` for the exact wording. **Verified live, not just static HTML**: this session's
> own background embeddings rebuild (`embed_rebuild_v2.py`, already running per house rules, confirmed
> via `tasklist`/`embeddings.progress.json` before touching anything) put the real repo in a genuine
> `rebuilding` state throughout — `embed.semantic_status()` called directly against the real `index/`
> dir returned `{"state": "rebuilding", "progress": {"percent": 25, ...}}`; a real second
> `viewer_app.py` instance (read-only, unused port) hit live `/api/search_hybrid?q=brake` and the
> response's `semantic_status` field matched, progressing to `26%` moments later. `never_built` and
> `stale` were verified the same way against isolated scratch index directories outside the repo (one
> empty, one with `embeddings.npy`/`.tsv` but no meta/progress file) — real function calls against
> real files, not simulated. Test server killed by PID matched via `netstat` to its own port; the
> pre-existing background rebuild was never touched. Shipped as `[1.45.0]`. Verified: `verify_all.py
> --snapshot` clean except the three now-documented pre-existing flakes.
>
> **Reconciliation note (2026-08-31, seventeenth pass):** `safeguard.py backupdb()`'s `PRAGMA
> quick_check` (`[1.25.0]`) only ever proved a backup file's SQLite B-tree was internally consistent —
> it never opened a connection against app tables, ran a real query, or fed a result through the app
> layer, so this had never actually been tested end-to-end. **Ran a real restore drill**: copied
> (never moved) `backups\db\viewer-20260830-1348.db` (3.64 GB, SHA-256-verified identical after copy)
> to an isolated scratch location outside the repo, started a genuinely separate `viewer_app.py`
> instance against only that copy on an unused port, and hit `/healthz`, `/api/part_record`,
> `/api/part_by_number`, `/api/search`, and `/api/pmcs` with real queries. **Found a real gap**:
> `/api/search` and `/api/pmcs` both silently return `200` with empty results against this backup —
> root cause confirmed directly against the restored file: the backup's `pages` table predates the
> `ocr_confidence` column (`schema_version=8` vs. migrations through `12`; `healthz`'s own `schema`
> check already said `WARN` but nothing gated on it), and current app code unconditionally selects
> that column in the search/pmcs query paths, throws, and swallows the error into an empty `200` with
> no error surfaced anywhere. The identical FTS query run directly against the restored file (no app
> layer) returns correct hits immediately — a pure app/schema-version mismatch, not a corpus problem.
> `part_record`/`part_by_number` are unaffected and served correct real data. No code changed to work
> around this — left for a human decision. Cleanly shut the drill instance down (Windows needed a
> forceful `taskkill /F`; non-forceful didn't stop a console-less Python server within 2 s), deleted
> only the scratch copy, and verified byte-for-byte (size + mtime + SHA-256) that the original backup
> and `index/viewer.db` were untouched throughout. Also found live free disk on `E:` at **6.3 GB**, an
> order of magnitude below a prior planning pass's ~63 GB estimate — flagged, not silently corrected;
> the drill used `C:` instead (8.69 GB free at the time). Full request/response record:
> `docs/RESTORE-DRILL-LOG.md`. Shipped as `[1.44.0]`. Verified: `verify_all.py --snapshot` run four
> times while the (deliberately undisturbed) background embeddings rebuild competed for CPU/IO —
> results varied between the two previously documented flakes and a third, newly-observed
> `test_http.py` `/api/pageqa` transport timeout, confirmed pre-existing via `git stash` back to
> unmodified `origin/main` (identical timeout reproduced). All failures across all runs were transport
> timeouts on slow model-backed endpoints, never a correctness assertion — docs-and-drill-only, no app
> code touched.
>
> **Reconciliation note (2026-08-31, sixteenth pass):** the LAN-exposed deployment path
> (`--host 0.0.0.0`) had authentication hardening (`VIEWER_ALLOWED_HOSTS`/`VIEWER_AUTH_TOKEN` gating
> `X-Viewer-Token`) but no transport-layer option at all -- the token and every request/response
> (search, TM/parts/NSN content) still crossed the LAN in plaintext, readable to anyone else on the
> same network segment. **Fixed**: new, off-by-default `--tls`/`--cert`/`--key` flags
> (`engine/viewer_app.py`) wrap the server's listening socket in a stdlib `ssl.SSLContext` (TLS 1.2+)
> once, at startup -- `Handler` and the bounded-worker semaphore are completely unmodified; an
> existing `--host 0.0.0.0` invocation is byte-for-byte unchanged unless `--tls` is passed
> explicitly, and the server fails fast (never binds, never falls back to plaintext) if `--tls` is
> passed with no cert/key resolvable. New one-time cert-minting CLI `engine/gen_cert.py`: RSA-2048,
> 10-year self-signed cert, SAN auto-detects LAN IPs. **Dependency decision**: gated behind an
> optional `cryptography` import -- commented out in `requirements.txt`'s OPTIONAL tier, suggested by
> hand in `INSTALL.bat`, the exact existing pattern `sentence-transformers`/`rapidocr-onnxruntime`/
> `pyzbar` already use -- rejected an `openssl` shell-out (this app's documented Win7/Vista floor has
> no guaranteed `openssl.exe` on PATH) and a vendored ASN.1/X.509 encoder (hand-rolled crypto is
> riskier to maintain than depending on the field-standard library); `cryptography` is needed for
> this one offline step only, never by the running server, which serves TLS entirely via stdlib
> `ssl`. `safe_public_base()` (feeds `/api/qr`) now emits `https://` when TLS is active; the
> loopback-detection check reading its output was made scheme-agnostic to match. New test
> `test_tls.py`: a real cert, a real `ThreadingHTTPServer` wrapped exactly as `main()` wraps it, a
> genuine TLS handshake (not mocked) confirming `https://` succeeds, plain `http://` on the same port
> is rejected, an untrusting client is rejected, the plain-HTTP path is unaffected when `--tls` is
> never passed, and `main()` fails fast on a missing cert -- skips gracefully if `cryptography` isn't
> installed. New doc `docs/TLS-LAN-SETUP.md`: cert generation, per-platform browser-trust steps, and
> an explicit "what this does/doesn't protect against" section (passive LAN sniffing: yes; an
> unverified active on-LAN attacker: no; a substitute for a real CA-signed cert beyond a trusted
> LAN/VPN: no). Shipped as `[1.43.0]`. Verified: `verify_all.py --snapshot` clean except the two
> now-documented pre-existing flakes (`test_ingest_routes.py`'s real-subprocess-e2e flake,
> `test_routes.py`'s `/api/ask` timeout).
>
> **Reconciliation note (2026-08-31, fifteenth pass):** a running server left up across a `git pull`
> (or any on-disk edit that never got a restart) looked completely healthy — answered every request
> fine — while quietly running stale code, with nothing anywhere recording when the process started
> or whether its code still matched disk. **Fixed**: `STARTUP_VERSION`/`STARTUP_TIME`
> (`engine/viewer_app.py`, captured once at import) plus `current_disk_version()` (a TTL-cached, 30s,
> plain-`open()`+regex re-read of just the `VERSION =` line — never a re-import, never `git`, fails
> open on any read error) feed new `started_with_version`/`started_at`/`code_changed_since_start`
> fields on `/healthz` and `/api/ops` (`version` itself is unchanged — still the in-memory version
> actually running). A non-dismissible banner (`shared.js`, `#vw-stalebanner`, following the existing
> `_footerNav` self-injecting/id-guarded pattern) shows on every page, not just `/ops`, polling
> `/healthz` on load and every 5 minutes, with no `localStorage` suppression by design — a dismissible
> banner is exactly the "silent for weeks" failure this closes. `ops.html` gets a dedicated "Code
> freshness" stat card. New test `test_version_staleness.py`: real `ThreadingHTTPServer`, confirms no
> mismatch on a fresh process, safely mutates the real on-disk `VERSION =` line (saved/restored in
> `try`/`finally`) and confirms the mismatch **is** reported, confirms a second fresh subprocess
> against that same changed file reports **no** mismatch, confirms the TTL cache keeps 20 back-to-back
> `/healthz` calls fast. Shipped as `[1.42.0]`. Verified: `verify_all.py --snapshot` clean except
> `test_routes.py`'s pre-existing `/api/ask` timeout, confirmed identical on unmodified `origin/main`
> via `git stash` before this work began — unrelated to this change.
>
> **Reconciliation note (2026-08-31, fourteenth pass):** a readiness audit's completeness pass found
> `part.html`'s shared `gj()` fetch helper collapsing a real transport/server failure and a genuine
> "nothing here" result into the exact same falsy shape across all 15 of its `fetch()` call sites (the
> primary `/api/partsummary` card + 14 lazy panels) — the primary card showed a flat "Nothing found."
> on any network hiccup, and the two safety-relevant panels (cross-manual conflicts, one-time-use/TTY
> fasteners) failed completely silently. **Fixed**: `gj()` now resolves `{ok,status,body}` (never
> rejects, so no call-site `.then()` shape changed) with `ok` true only for a 2xx response whose body
> actually parsed; every site branches on `res.ok` first, showing a distinct `⚠ Couldn't load <thing>
> — try again.` on failure vs. its existing (or newly-added, for 7 panels that had none) honest empty
> message. The two safety panels get explicitly-worded "do not treat this as..." copy matching
> `dossier.html`'s existing precedent. **Two real bugs caught live while verifying, not shipped**: (1)
> the primary card's new empty-test initially included `s.title`, which `jobcards.py`'s
> `_jobpack_data()` always sets to the raw query string as a bare fallback even on a genuine no-match —
> a nonsense query rendered as a match until this was caught with a real no-match query against the
> real corpus and dropped from the test; (2) `#conflictcard` is shared by two lazy functions and one of
> them used to overwrite (`box.innerHTML=h`) rather than append, which would have silently erased the
> other's new failure marker — both now append-only, verified live that a validate-failure message and
> a real conflicts result render together without either erasing the other. Verified live against the
> real corpus (`index/viewer.db`, ~39,700 documents): a real part renders unchanged; a genuine no-match
> query shows "Nothing found."; a forced failure (both a true `fetch()` rejection and a real HTTP 404)
> was injected at all 15 call sites in-browser and each showed its own distinct failure message. New
> coverage follows this repo's existing static-source-text-assertion convention for UI-page tests (no
> real browser/JS test harness exists for any UI page in this repo — confirmed, not assumed) — see
> `test_uiux_fixes.py` (22 new checks, 272/272 total). Shipped as `[1.41.0]` (branched from
> `origin/main` at `[1.39.0]`; `[1.40.0]` may land from concurrent work — a VERSION/doc conflict at
> merge time is expected and resolved by a human per this repo's established parallel-PR pattern).
> `main` is at `[1.41.0]` on this branch (pending merge).
>
> **Reconciliation note (2026-09-01, thirteenth pass — CRITICAL fix):** adversarial verification of the
> tenth pass's `[1.36.0]` (embed.py full-rebuild prep), before the full-corpus rebuild it gates was
> actually launched, found a real defect: `build_index()` snapshotted `cur_backend = backend()` once,
> before the chunk loop, and stamped it into `embeddings.meta.json` unconditionally — but if a
> chunk's `model.encode()` call threw (bad input, transient OOM), the bare per-row
> `except Exception: hash-fallback` pattern silently substituted hash vectors for THAT CHUNK ONLY
> while the meta stamp still claimed a pure `"sentence-transformers"` index. **Confirmed
> pre-existing, not introduced by the tenth pass** — the original unbatched `embed_text()` had the
> identical bare fallback and the old `build_index()` also stamped the backend after the fact with no
> per-row correlation; batching just enlarged one failure event's blast radius from 1 row to up to
> `chunk_size` (5,000) rows. This is the `[1.32.0]` failure mode again (real vectors compared against
> incompatible vectors → near-noise cosine scores silently trusted), now possible at row/chunk
> granularity inside an otherwise-valid build, with zero warning or trace. **Fixed**: every chunk
> whose encode() call actually raised is tracked in `fallback_events`, persisted through
> `embeddings.progress.json` so the record survives an interrupt+resume; if any remain once the
> shard merge succeeds, `embeddings.meta.json` is deliberately withheld (any stale one from a prior
> clean build is removed) — reusing `_index_is_stale()`'s existing no-meta-stamp-means-stale branch,
> zero new per-row staleness logic — and `embeddings.fallback.json` records exactly which rows are
> suspect. `BUILD-EMBEDDINGS.bat` now prints an explicit warning instead of a bare success line when
> this happens. Directly verified with a real injected mid-build encode() failure (not a mock),
> confirming the meta stamp is withheld, staleness/`search()` both refuse the index end-to-end, the
> on-disk array genuinely mixes real vectors and hash vectors only where expected, the record
> survives a genuine interrupt+resume, and a clean rebuild clears the stale fallback report — see
> `engine/tests/test_embed_partial_fallback.py` (32 new checks). **No full-corpus rebuild was run** —
> this PR is code + tests only; the rebuild stays a separate, human-supervised action once this fix is
> on `main`. Shipped as `[1.39.0]` (branched from `origin/main` at `[1.36.0]`, rebased onto `[1.38.0]`
> once `[1.37.0]` and `[1.38.0]` both merged ahead of it — a straightforward doc-reconciliation rebase,
> no logic-file overlap with either, same pattern as this repo's prior `docs/reconcile-changelog-*`
> branches). `main` is at `[1.39.0]`.
>
> **Reconciliation note (2026-09-01, twelfth pass):** implemented the `parts.cagec`/`parts.smr` cross-
> database correlation design `[1.33.0]` scoped but deliberately didn't start. `correlate_parts_cagec()`
> joins `index/rpstl.db`'s `parts_rows` into `parts` on `(document_id, page, nsn)`, filtered through
> `index/cage.json` before writing anything — confirmed live against this repo's own real rpstl.db that
> the filter is load-bearing, not decorative (raw regex candidates include real garbage: vehicle model
> numbers, nomenclature words, RPSTL boilerplate that happens to fit CAGEC's 5-alphanumeric-char shape).
> SMR rides on that SAME candidate row's cagec validation; a genuinely ambiguous key (2+ distinct valid
> cagecs) is skipped, never guessed. Wired as the new 8th/final ingest stage, deliberately full-corpus
> every run (not `_TOUCHED_DOC_IDS`-scoped like its neighbors) since `extract_parts()` unconditionally
> rebuilds the whole `parts` table every time; also standalone via `python viewer_ingest.py cagec` for
> backfilling an already-ingested corpus. **A real bug was caught during verification, not shipped**: the
> first draft batched `UPDATE`s via `executemany()` INSIDE the same cursor loop it was reading from —
> passed at small synthetic scale, then reproduced immediately as `sqlite3.OperationalError: database is
> locked` against this repo's real 227,908-row `parts` table (this corpus has never been under the
> 1,000-row batch-flush threshold, so this would have crashed the stage on every real ingest run).
> Fixed by `.fetchall()`-ing the SELECT before writing, matching `extract_parts()`'s own existing
> convention. Real yield measured against a random 4,000-row sample of this repo's actual corpus:
> **48.0%**, matching the `[1.33.0]` scoping research's ~48.2% full-corpus estimate closely; every
> written cagec round-tripped as genuinely present in the real `cage.json`, and no known-garbage token
> reached a written column. Sampled (not full-corpus) in the test suite for a real, measured reason:
> per-row `UPDATE` cost on this dev host is dominated by real-time antivirus scanning of SQLite's small
> writes (confirmed via `Get-MpComputerStatus` — real-time protection on, no exclusions configured),
> making a full 227,908-row write pass take 15+ minutes of pure AV overhead; the candidate index side is
> still read in full regardless. One caveat flagged, not fixed: `index/rpstl.db`'s mtime is ~7 weeks
> older than `index/viewer.db`'s on this deployment — worth a fresh `python build_rpstl.py` before
> trusting the first real backfill's yield as current rather than a July snapshot. **Independently
> adversarially verified before merge** (own scripts, disposable read-only-sourced DB copies): 0
> incorrect writes across ~5,300 audited real writes; a targeted attack against all 49 real genuinely-
> ambiguous keys (rebuilt from the full unsampled `rpstl.db`) found all 49 correctly refused; idempotency
> confirmed via two full runs plus a deliberately corrupted row correctly self-healed on a third —
> clarifying the real contract is "recompute and correct," not "never touch a populated row." One
> non-blocking note: the write loop has no try/except, matching `extract_parts()`'s own existing
> precedent in the same file rather than a new regression. Shipped as `[1.38.0]` (branched from
> `origin/main` at `[1.33.0]`, rebased onto `[1.37.0]` once that PR and `[1.36.0]` both merged — the
> third rebase-and-renumber this session's parallel-PR pattern has required, all handled the same way).
> 2 of the original 5 Gap-Sweep dead columns (`[1.31.0]`) remain open (`parts.uoc`, `ref_nsn.data_date`).
> `main` is at `[1.38.0]`.
>
> **Reconciliation note (2026-08-31, eleventh pass):** closed the one open item `[1.33.0]` deliberately
> left on the table — `/api/ingest_scan` now has a UI entry point (`engine/ui/ingest.html`), shipped as a
> SEPARATE "Broader file scan" link/panel next to the existing Preview button rather than merged into it,
> exactly per `[1.33.0]`'s stated concern about two disagreeing "how many new files" counts. The panel's
> copy states plainly what it adds over Preview (`.txt`/`.html`/`.htm`/`.xml`/`.csv`/`.md`/`.tiff`/`.tif`/
> `.png`/`.jpg`/`.jpeg` — the real `ingestpipe.SUPPORTED` set, **not** `.docx`/`.xlsx`/`.pptx`/`.rtf`/
> `.bmp`/`.gif`, which an earlier draft of this shipped copy briefly and incorrectly claimed; caught by
> adversarial verification before merge and corrected, confirmed live against a running server), what's
> still not covered (legacy `.doc`/`.xls`/`.ppt`, `.svg` — discovered, never content-extracted), that
> `.xml`/`.csv`/`.md` are themselves a partial win (counted/deduped by this scan, but zero content
> extracted by the real ingest job either way), and that this scan's dedup method (hash-or-filename)
> differs from Preview's (exact path only) — so a legitimate count mismatch is explained, not left as a
> mystery. Separately traced whether `/api/ingest_scan` needed the same `_exposed_read_guard()` gate
> `/api/ingest_preview`/`/api/ingest_status` carry (a gap an earlier research pass flagged) — confirmed it
> does NOT: it's a `POST` route, and `do_POST` already requires the shared `X-Viewer-Token` for every POST
> when network-exposed, before any handler runs. Left a code comment recording that so it isn't
> mis-"fixed" by a future pass. Verified live, twice: once at initial ship (`test_ingest_routes.py`'s real
> e2e `/api/ingest_scan` coverage re-run clean, plus a direct `ingestpipe.scan_folder()` call confirming
> the extension gap), and again after the copy correction (a standalone script started the real server,
> built a temp folder with one file per extension across both sets, POSTed to `/api/ingest_scan`: exactly
> the 12 real `SUPPORTED` extensions came back, all 6 previously-misclaimed extensions correctly absent).
> Shipped as `[1.37.0]` (branched from `origin/main` at `[1.33.0]`, rebased onto `[1.36.0]` once that PR
> merged — a straightforward doc-reconciliation rebase, same pattern as this repo's prior
> `docs/reconcile-changelog-*` branches). `main` is at `[1.37.0]`.
>
> **Reconciliation note (2026-08-31, tenth pass):** implemented the one remaining prerequisite the
> eighth pass's research flagged and left open — `embed.build_index()`'s row cap was hardcoded at
> `limit=200000`, covering only ~11.9% of this deployment's real 1,682,054 eligible pages. Now
> `limit=None` resolves to `VIEWER_EMBED_LIMIT` (env var, default 200000, same convention as
> `VIEWER_DB`/`VIEWER_OCR_PAGE_TIMEOUT`) — byte-identical behavior for the sole existing caller
> (`BUILD-EMBEDDINGS.bat`, which sets no override and now prints the effective cap). Unbatched
> per-row `embed_text()` calls inside the build loop replaced with real chunked
> `model.encode(list, batch_size=...)` calls — re-measured fresh on this host against real corpus
> text: ~40 pages/sec unbatched vs. ~53–54 pages/sec batched, ~1.3x, matching the eighth pass's own
> standalone benchmark almost exactly. Checkpointed/resumable: each completed chunk (default 5,000
> rows) lands in shard files (`index/_embed_build/`) plus a progress marker
> (`index/embeddings.progress.json`) keyed on the query's `ORDER BY id` cursor (`pages.id`, the real
> rowid) and the run's own parameters, so a killed mid-run process resumes from its last completed
> chunk instead of restarting — verified directly by injecting a real fault mid-loop (not a mock),
> confirming the resumed run's final `embeddings.npy`/`embeddings_ids.tsv` is byte-identical to an
> uninterrupted run over the same sample. **The `[1.32.0]` safety invariant needed zero changes to
> `_index_is_stale()` itself** — `embeddings.meta.json` is still written exactly once, immediately
> after the shard merge succeeds and nowhere else in `build_index()`, so a process killed at any
> earlier point never produces a meta stamp and the existing no-meta-stamp-means-stale branch keeps
> refusing an incomplete build, structurally, the same way it always has. New coverage:
> `engine/tests/test_embed_checkpoint.py` (34 checks, including the direct interrupt-then-resume
> reproduction). **No full-corpus rebuild was run as part of this pass** — that stays an explicit
> ~9–12 hour unattended, ~2.6GB commitment for a human to launch separately, per the eighth pass's own
> NO-GO-for-autonomous-execution finding, which this pass adopted rather than revisited. Shipped as
> `[1.36.0]`. `main` is at `[1.36.0]` once this PR merges (branched from `origin/main` at `[1.33.0]`;
> other PRs may land on `main` concurrently, in which case a human reconciles the version number at
> merge time per this repo's established parallel-PR pattern).
>
> **Reconciliation note (2026-08-30, ninth pass):** picked up 2 of the 3 remaining orphan-route
> candidates a follow-up research pass identified after `[1.31.0]`: `GET /api/form_2404`/`/api/form_2407`
> (blank DA-2404 PMCS worksheet / DA-2407 maintenance-request worksheet) were real, tested routes with
> zero UI entry point — each got an always-enabled print link on `pmcs.html`/`jobcard.html` respectively,
> deliberately ungated since a blank form needs no prior search. Both verified live via `curl` returning
> genuine single-page PDFs before shipping. The third candidate, `/api/chapter_jump`, was confirmed
> genuinely not worth wiring — `index.html`'s `openViewer()` already calls the richer `/api/chapters`,
> which `chapter_jump` is a strict subset of, so wiring it in would add a second round-trip for data
> already in hand. `/api/ingest_scan` stays open on purpose (needs a product decision — its own supported-
> extension list undercounts what the real ingest job processes, and a naive UI addition risks two
> disagreeing "how many new files" counts). Shipped as `[1.33.0]`, branched off `main` before `[1.32.0]`'s
> critical stale-embeddings-index fix merged, then rebased on top of it once that PR went green — a
> straightforward doc-reconciliation rebase, same pattern as this repo's prior
> `docs/reconcile-changelog-*` branches. `main` is at `[1.33.0]`.
>
> **Reconciliation note (2026-08-30, eighth pass — CRITICAL fix):** while researching semantic search's
> feasibility as a `[1.31.0]` follow-up, a real `pip install sentence-transformers` on this host
> silently reclassified the pre-existing, unstamped, hash-fallback-built `index/embeddings.npy` as
> "not stale" — `embed._index_is_stale()` only ever compared the *current* backend against itself,
> never against what actually built the index. That stale index started feeding through
> `/api/search_hybrid`'s RRF fusion — **the primary search endpoint as of `[1.31.0]`** — as
> near-noise cosine scores (0.18–0.19, confirmed live) treated as a legitimate semantic signal. Fixed
> the same day, before reaching any real user: `_index_is_stale()` now requires proof (a meta stamp)
> that an index was built by the backend that's currently active. Also fixed: `embed.py`'s own
> self-test had silently stopped exercising this exact check once a real model backend became
> available (was gated behind `if backend()=="hash-fallback"`), and two other tests
> (`test_routes.py`/`test_pageqa.py`) had baked in the same "transformers/torch never installed"
> environment assumption. **Lesson for future sessions**: installing any optional heavy dependency
> (sentence-transformers, easyocr, camelot, etc.) can change more than the one thing being tested for —
> re-run the full suite and think through what else reads `backend()`- or `available()`-style
> environment probes before trusting a "looks fine" result.
>
> **Reconciliation note (2026-08-30, seventh pass):** a Gap Sweep audit (5-agent parallel research
> answering "what's going on with OCR confidence, and what other gaps exist" after `[1.30.0]`) shipped
> its 5 priority items in `[1.31.0]`. RapidOCR installed and independently re-verified live (the
> confidence write path was already correct; this machine's OCR engine — Tesseract fallback — was the
> real gap). `/api/search_hybrid` is now the home search box's primary endpoint — but only after a
> second research pass found the route silently dropped side/operators/match_any/fuzzy/mode entirely
> (would have broken the SIDE toggle and offline did-you-mean outright); fixed first, then verified
> extensively (100% result-count parity across ~20 diverse queries) before switching. Of the 5 dead
> columns the Sweep found, only `ref_nsn.superseded` at the FLIS site was genuinely trivial (value
> already parsed, never bound to the column) — the other 4 need real cross-database integration or new
> extraction logic entirely, correctly left open rather than rushed. 3 more orphaned routes wired in:
> `rpstl.py` (part.html card), `partspdf.py` (jobcard.html button), `handover.py` (a genuinely new page,
> `/handover` — none of the 3 candidate existing pages fit). A real `"search"` analytics event added —
> `"search"` had been a declared-valid kind since `analytics.py`'s `_VALID` set was first written, but
> nothing had ever logged one; `top_searches` was always silently empty. `main` is at `[1.31.0]`;
> `PROJECT-SUMMARY.md`/`MASTER-RECONCILIATION.md` updated in the same pass.
>
> **Reconciliation note (2026-08-30, fifth pass):** a second scoping audit (companion to the fourth-pass
> dossier below — real benchmarks + a real programmatic WCAG contrast audit run on this host) produced a
> 19-item, 4-tier Build Roadmap; all 6 "Now" items shipped in `[1.29.0]`, each re-verified live before
> shipping rather than trusted from the roadmap's own claims. Two bugs turned out worse than scoped: the
> home page's `--acc` CSS var wasn't just missing a fallback, it plus `--grn`/`--amb`/`--red`/`--teal`/
> `--pur` were never defined on `index.html` at all — confirmed live via `getComputedStyle()` that the
> operator/mechanic side badges, "Saved" confirmations, and chapter-count status text were silently
> rendering in plain white, not their intended colors, before this fix. Also shipped: a fuzzy-search
> vocabulary scan that was running 2-3x per query for zero behavior difference (request-scoped cache,
> `search_feature.py`); a shared `VW.trapFocus()` (`shared.js`) wired into all 5 real modals, verified
> live (auto-focus, Tab-wrap, Escape-close); `alt` text on the 3 primary viewer images; `aria-label`s on
> the 10 highest-traffic unlabeled controls (home + 8 tool search boxes + `collections.html`'s form); and
> the 3 real WCAG AA text-contrast failures the restored color tokens exposed (2.98:1/3.36:1/4.02:1,
> all below the 4.5:1 floor) — fixed with new lightened text-only siblings (`--grn-tx`/`--red-tx`),
> locked in by a new automated contrast guard in `engine/verify_ui.py` so a future hex change can't
> silently reintroduce this. **Still genuinely open** (Next/Later tiers of the same roadmap, not started):
> the 5 orphaned modules (`commonality.py`/`tmrev.py`/`harnesstrace.py`+`pinouts.py`/`macchart.py`/
> `crossmethod.py`), semantic search's non-functional production state, RRF hybrid fusion's zero UI
> callers, symptom/procedural query routing, and a real learned re-ranker (gated on click volume that
> doesn't exist yet — `index/analytics.jsonl` logs zero `search`/`click` events today). `main` is at
> `[1.29.0]`; `PROJECT-SUMMARY.md`/`MASTER-RECONCILIATION.md` updated in the same pass.
>
> **Reconciliation note (2026-08-30, sixth pass):** the Build Roadmap's "Next" tier (all 6 items,
> everything listed as open at the end of the fifth-pass note above) shipped in `[1.30.0]`, grounded in
> 4 parallel research passes reading the real modules/routes/UI patterns before any code was written.
> The 5 orphaned modules are wired in on `part.html`/`procedure.html`, each verified live; one placement
> deviated from the roadmap's own suggestion (`commonality.py` moved from `readiness.html` to
> `part.html` — confirmed live that `readiness.html` is vehicle-scoped end-to-end while `commonality.py`
> does an exact NSN/name/part-number lookup, a genuine shape mismatch, not a nitpick). A "Related parts"
> card (`xref.py`) landed on both `part.html` and `dossier.html`. OCR-confidence and cross-manual-
> conflict signals now reach the search results list — `ocr_confidence` via a one-column SELECT fix in
> `search_feature.py` (real corpus finding, disclosed honestly: this deployment has zero populated
> `ocr_confidence` values across 53,391 OCR'd pages, so the fix is correct but currently invisible until
> a data pipeline populates that column); the conflict flag redesigned from the roadmap's own sketch
> after `conflicts.py`'s `check_query()` measured 200+ms on common queries (confirmed directly) — now an
> independent, non-blocking client-side call instead of baked into `/api/search`'s own response, which
> would have roughly doubled search latency. Symptom/"how do I" query routing shipped with the same
> measurement-driven adjustment: `/api/ask` measured 900–1855ms (confirmed directly), so question-shaped
> queries get an instant static suggestion link, never an automatic fetch — only `/api/faulttree`
> (112–206ms, acceptable) fires inline for symptom-shaped queries. `index.html` finally loads
> `/base.css` — a real visual-diff pass, not a blind strip-and-link: the fully-redundant `:root`/
> `[hidden]` duplication is gone, but the kiosk-mode/touch-target rules stay (this page's buttons use
> `a.ghost`, base.css's shared rule targets `a.btn` — confirmed `.ghost` is 69× local-only, not an
> app-wide convention); a real checkbox-distortion bug this page's duplicate had inherited (already
> fixed once in base.css) got fixed in the same pass. Paired with a new `--line-ctl` interactive-control
> border token (`--line` itself measured 1.05–1.45:1, far under the 3:1 UI floor). **Genuinely still
> open** (Later tier, calendar/data-gated by design): semantic search's non-functional production state,
> RRF hybrid fusion's zero UI callers (sequenced after the semantic-search fix), and a real learned
> re-ranker (gated on click volume that still doesn't exist). `main` is at `[1.30.0]`;
> `PROJECT-SUMMARY.md`/`MASTER-RECONCILIATION.md` updated in the same pass.
>
> **Reconciliation note (2026-08-30, fourth pass):** a production-readiness/end-user-friendliness audit
> against fielded military IETM viewers (EMS-VIEWER/EMS-NG, IADS) plus an honest search-accuracy
> scorecard was published this session as a standalone dossier. Three "do now" items from it shipped in
> `[1.28.0]`: the parts-request cart (`engine/ui/index.html`) now persists to `localStorage` from every
> mutation path and restores on load with a visible toast — previously the app's other core workflow had
> zero autosave while the procedure checklist and ingest job both already had it; `stepflow.html` (the
> page built for hands-free at-the-vehicle use) now actually triggers `readaloud.js`'s voice step-nav bar
> via additive `class="node step"`/`class="num n"` aliases (confirmed zero style impact before shipping);
> `docs/PORTING.md` — the document a new site would use to stand itself up cold — updated from a
> 14-version-stale v1.13.2 to current, now explicitly warning about the real `[1.25.0]` schema-migration
> trap. All three verified live in a real browser, not just read. **Genuinely still open from the same
> audit** (see item 10 below and the dossier for the full prioritized list): semantic search is real but
> non-functional in production today (no embedding model installed, stale index); RRF hybrid fusion has
> zero UI callers; ARIA/`<label>`s exist on only 2 of 45 UI pages; the home page's 6 modals lack real
> focus traps; no user accounts/RBAC, TLS, offsite backup automation, or accreditation artifacts exist
> for multi-site fielding. `main` is at `[1.28.0]`; `PROJECT-SUMMARY.md`/`MASTER-RECONCILIATION.md`
> updated in the same pass.
>
> **Reconciliation note (2026-08-30, third pass):** the UI-wiring follow-up the second-pass note below
> flagged as "genuinely still open" is now done, in `[1.27.0]`: `engine/ui/part.html`'s `lazyConflicts()`
> shows each disagreeing value's vehicle inline and a "⚠ Spans N different vehicle labels..." caveat when
> `cross_vehicle: true`. Verified live against the real running server and the exact WINCH INSTALLATION
> corpus example this whole investigation started from — both the ambiguous `electrical`/`weight`
> conflicts (correctly showing the caveat with all real vehicle labels listed) and the confirmed
> single-vehicle `length` conflict (correctly showing neither) rendered as intended, no console errors.
> `main` is at `[1.27.0]`; see item 10 below for the remaining, lower-priority disclosed limitations.
>
> **Reconciliation note (2026-08-30, second pass):** the `build_conflicts.py`/`conflicts.py` follow-up
> the note below flagged as "deliberately NOT fixed yet" is now fixed, in `[1.26.0]` — and its own first
> attempt needed a second pass. Pass 1 grouped `conflicts.detect()` by `(type, unit, vehicle)` to stop
> unrelated vehicles' naturally-different specs pooling into a false "conflict"; adversarial review
> caught it silently DROPPING a genuine cross-manual disagreement whenever the same real vehicle was
> filed under two different ingest-folder spellings (confirmed live: a real 35-vs-50-ft-lb torque
> conflict returned `[]`) — reverted before merge. Pass 2 (shipped) restores byte-identical recall to
> the pre-bug code and annotates each conflict with `vehicle`/`vehicles`/`cross_vehicle` instead of
> filtering by it. Re-swept for real against production: 1548 conflicts unchanged (recall confirmed
> unregressed), 5,071 now marked `cross_vehicle: true`, 1,466 `cross_vehicle: false`. Genuinely still
> open: `engine/ui/part.html` doesn't yet read any of the new fields (available via the API, not yet
> shown to a technician) — see `CHANGELOG.md` `[1.26.0]` and item 9 below for the full story and the
> remaining, lower-priority disclosed limitations. `main` is at `[1.26.0]`;
> `PROJECT-SUMMARY.md`/`MASTER-RECONCILIATION.md` updated in the same pass.
>
> **Reconciliation note (2026-08-30, first pass):** while re-running host-side follow-up items
> (backupdb, the weekly backup task, `BUILD-CONFLICTS.bat`) directly on the real host, found and fixed a
> critical, previously undiscovered bug: the real `index/viewer.db` was missing 4 schema migrations
> (0009–0012), silently breaking `measures`/`ask`/`cautions`/`pmcs`/`oneuse` since v1.13.5 (~3 weeks) with
> no test ever catching it (the suite runs against a synthetic fixture DB, never the real corpus). Fixed
> via the already-built `python viewer_ingest.py migrate` (auto-backs up, applies atomically); confirmed
> live and via a clean `verify_all.py` re-run. See "RUN THESE ON THE HOST" item 5 below and
> `CHANGELOG.md` `[1.25.0]` for full detail. Also completed this pass: the weekly DB-backup task
> (registered + test-fired, did not exist before), a real `backupdb` run, and `BUILD-CONFLICTS.bat`'s
> first-ever real run — the real follow-up that run surfaced in `conflicts.py`'s subject-scoping is
> covered by the second-pass note directly above, not repeated here.
>
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

### RUN THESE ON THE HOST (updated 2026-08-30, was "2026-08-24")
1. **`VERIFY.bat`** (→ `engine/tests/verify_all.py`) — ✅ **DONE, confirmed GREEN**, repeatedly through
   v1.13.4, every tier of the v1.14.0 audit run, and every commit of the v1.15.0 session — the range ends at
   **46/46, ALL GREEN** (`9b0e5b9`), up from 26/26 at the start of v1.14.0. CI (`.github/workflows/ci.yml`)
   runs the same gate on every push/PR to `main`; the CI-fix work landing alongside PR #3's merge into this
   pass (see `CHANGELOG.md`) also fixed a tesseract-binary gap and a Windows-only-font gap in the CI runners
   themselves, plus made `verify_all.py` print full output on a suite failure instead of just its last 3 lines.
   `VERIFY-099.bat` still forwards to it.
2. **R10 screenshot:** capture the running app (e.g. `/part` red one-use card, `/command` gap card, or home with the
   operators hint) at `127.0.0.1:8765` → `docs/screenshots/`. **Still not done as a saved artifact** — a
   2026-08-30 session (`[1.25.0]`) confirmed live-in-browser against the real running app once again
   (session-modal + home page render correctly with real corpus counts) but had no tool available to
   persist the actual PNG bytes to disk — same exact limitation every prior session has hit. **To finish
   R10:** capture and save at least one real screenshot per major page into `docs/screenshots/` using the
   `<version>-<page>.png` convention; needs either the Claude-in-Chrome extension or a manual save.
3. ~~Optional while OCR is paused: **`BUILD-CONFLICTS.bat`**~~ — **RUN, `[1.25.0]`:** `index/conflicts.db`
   now exists. First attempt was vacuous (0 conflicts, `n_values=0` everywhere) — this surfaced a critical
   bug (see item 5 below), not a clean corpus. Re-run after the fix found real data, but its headline
   "1548 of 2000 subjects flagged" is **not trustworthy as a safety-conflict list** — see item 5.
4. ~~**`safeguard.py backupdb`**~~ — **DONE, `[1.25.0]`:** run for real (3.64 GB `VACUUM INTO`, verified via
   `PRAGMA quick_check`, 147.5s); `THE_VIEWER_WeeklyDBBackup` scheduled task registered (it did not exist
   before) and test-fired via `schtasks /Run` — confirmed it actually executes end-to-end.
5. **`[1.25.0]` CRITICAL — the real `viewer.db` was missing 4 schema migrations (0009–0012)**, silently
   breaking `measures`/`ask`/`cautions`/`pmcs`/`oneuse` since v1.13.5 (~3 weeks) — every call into
   `features/corpus.py`'s shared FTS retrieval hit `sqlite3.OperationalError: no such column:
   p.ocr_confidence`, silently caught and turned into an empty result by that function's own "degrade
   safe, never a 500" contract. Nothing caught it because the test suite runs against a synthetic fixture
   DB with the correct schema, never the real corpus. **Fixed:** `python viewer_ingest.py migrate` (backs
   up first, applies atomically) — `schema_meta` now `12`; confirmed live (`find_for_query('torque')`: 0 →
   26 real cited results); `verify_all.py` re-run clean after (48/49, only the known pre-existing flake).
   **Real follow-up this surfaced, deliberately not fixed:** `build_conflicts.py`'s subject selection picks
   generic, corpus-wide phrases (e.g. "WINCH INSTALLATION") that FTS matches across hundreds of unrelated
   documents/vehicles; `conflicts.detect()` pools every incidentally-matched value under that one subject
   string with no per-document/per-part disambiguation, inflating its "conflict" rate with noise (spot-
   checked: one flagged row pools values from 4 different manuals, almost certainly 4 different real
   winches, not one part with disputed specs). The live `/api/conflicts?q=...` route has carried this same
   scoping gap for any sufficiently generic query since v1.13.0 — this just made it visible at scale. See
   `CHANGELOG.md` `[1.25.0]` for full detail.
6. **Re-baseline the pre-OCR safeguard snapshot** — ✅ **DONE**, repeatedly, through v1.13.4 (baseline at that
   point: `SNAP_20260808_184421_v1.13.4-changelog`, 658/658 OK). Not confirmed re-baselined again during either
   the v1.14.0 or v1.15.0 sessions until `[1.25.0]`'s real `backupdb`/`migrate` runs (2026-08-30), which each
   took their own fresh, verified `viewer.db` backup as a side effect (`backups/db/`, 2 copies kept).

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
- Duplicate route paths silently override — re-audited `[1.24.0]` (2026-08-29): **276 routes (250 GET + 26
  POST), zero collisions**, verified at the source level, not just the final live-dict size (which can't
  distinguish a real registration from a silent same-path overwrite) — every `@get`/`@post` decorator path
  across `features/routes/*.py` (135 GET + 26 POST, no internal duplicates) cross-checked against every path
  `static.py`'s `register_static()` registers programmatically from `_PAGES`/`_SCRIPTS`/`/base.css` (115 GET,
  no internal duplicates): `135 + 115 = 250` exactly, zero overlap. Up from 265 (244 GET + 21 POST) at
  v1.14.0 — new routes since then: `/api/pageqa` (1.16.0), `/api/vlm` (1.17.0), `/api/layout` (1.22.0),
  `/api/editions`/`/api/symbols`/`/api/symbols_page_image` (1.15.0) on GET; `/api/airgap_export_decisions`/
  `/api/airgap_import_decisions`/`/api/ingest_upload`/`/api/ocr_backlog_start`/`/api/symbols_template`
  (1.15.0), `/api/analytics_log` (1.20.0) on POST. A real, mechanical check for a DIFFERENT bug class (built
  but never wired in — dead code, not a collision) already exists separately (`audit_features.py [7]`,
  added v1.15.0).
- Standing rules R1–R13 are **THE VIEWER-only**; do not carry them to other projects.

## Suggested next
1. **R10 screenshots** — still the one item from the v1.13.0-era host checklist not done as a saved artifact
   (see "RUN THESE ON THE HOST" above); unchanged by either the v1.14.0 audit run or the v1.15.0 session.
2. **`measures.py`'s deferred bare-unit-fusion ambiguity** (item "489A" reading as "489 Amps") — the
   **labeled** sub-case ("ITEM 489A", "TABLE 3W", any bare-letter unit immediately preceded by a
   figure/table/item/detail/etc. reference word) is fixed as of `[1.18.0]`, generalizing the existing
   degF/degC `_CALLOUT` guard to every unit in `_BARE_LETTER_UNITS`. The **unlabeled** sub-case (a bare
   "489A" with no preceding label word at all) is still deliberately open — a blanket no-space-required
   guard (the fix that worked safely for temperature) is confirmed NOT safe to generalize to V/A/W:
   "12V"/"5A"/"60W" fused with no space is standard, common electrical-rating notation in this corpus,
   so requiring whitespace there would silently drop real readings, a recall regression this module has
   no way to verify without the real corpus (the original reason this was deferred, still true for this
   narrower remaining piece). Flagged since `CHANGELOG.md` `[1.13.4]`.
3. ~~**Staleness-audit Tiers 2, 5, 6**~~ — **CORRECTED, `[1.24.0]`:** `[1.23.0]`'s "only Tiers 2/5/6 remain
   genuinely unstarted" claim was itself wrong. `git log --all --grep="Drift Report\|Tier"` shows the Viewer
   Drift Report staleness audit only ever had **4 tiers total, not 6** — Tier 1 (`3054dad`), Tier 2
   (`132132f` — the [1.14.0] documentation-reconciliation commit itself, missed by `[1.23.0]`'s check the
   same way Tiers 3/4 initially were), Tier 3 (`8f795bc`, dependency/CI hardening), Tier 4 (`1b3c6d8`, repo
   bloat/env vars/Windows CI) — whose own commit message states outright: "This closes out all 4 tiers of
   the Viewer Drift Report staleness audit run across this session." **All 4 tiers are complete; there is no
   Tier 5 or 6 and never was.** Note this was a DIFFERENT deferred-items list from the "5 deferred items"
   v1.15.0 closed (item 4 below, and distinct again from item 5's audit-reachability findings) — three
   separate tracking threads with similar names, easy to conflate; now down to two.
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
8. **Tier-2 "learned search re-ranker" — Phase 1 shipped in `[1.20.0]`, the actual learned model is still
   open.** `[1.20.0]` corrected a false premise (the backlog item assumed click-through training data already
   existed; it didn't — `analytics.py` only ever logged zero-result queries) and shipped both halves that
   were actually possible now: real click instrumentation (`analytics.clicked_pages()`, a `"click"` event
   kind, `POST /api/analytics_log` from `index.html`'s result rows) and a modest hand-tuned heuristic (a 4th
   `search_feature.search()` stable-sort key that floats a previously-opened result — inert with zero click
   history, by construction). The actual learned model — trained on the click log this now produces — is
   still open, gated on accumulating enough real click volume to be worth it. See `CHANGELOG.md` `[1.20.0]`.
9. **`[1.18.0]`–`[1.23.0]`, 6 PRs from the same session as this reconciliation, all now merged.** Beyond
   items 2 and 8 above, each shipped its own remaining open piece: `[1.19.0]` home-page nav regroup (nothing
   left open — self-contained UI fix); `[1.21.0]` per-line OCR confidence capture (true per-word confidence
   stays open, gated on GPU hardware this environment can't build/verify against); `[1.22.0]` multi-column
   reading-order reconstruction (3+ column layouts not specifically detected, and the row-alignment threshold
   is tuned against synthetic fixtures only — worth validating against real corpus pages if mis-detections
   ever surface). `[1.23.0]` (this entry) is documentation-only.
10. ~~**`[1.26.0]`'s own genuinely open follow-up: wire `engine/ui/part.html`'s conflict card to show
    the new `cross_vehicle`/`vehicles` fields.**~~ — **DONE, `[1.27.0]`:** `lazyConflicts()` now shows
    each value's vehicle inline and a "⚠ Spans N different vehicle labels..." caveat on
    `cross_vehicle: true` conflicts, verified live against the real WINCH INSTALLATION example (both the
    `electrical`/`weight` cross-vehicle hits and the `length` confirmed single-vehicle hit rendered
    correctly). Lower-priority, still open: the citation-completeness quirk and the "vehicle is a raw
    folder name, not a curated identity" limitation, both disclosed in `conflicts.py`'s own docstring
    (see `CHANGELOG.md` `[1.26.0]`/`[1.27.0]`).
11. ~~**A real accessibility pass, not another ad hoc fix.**~~ — **DONE (partially), `[1.29.0]`:** the
    home page's `--acc`/`--grn`/`--amb`/`--red`/`--teal`/`--pur` tokens (previously undefined, silently
    dropping colors app-wide) restored; 3 real WCAG AA contrast failures fixed with new text-only shades,
    locked in by an automated guard; all 5 real modals now have a working `VW.trapFocus()`; the 3 primary
    viewer images have `alt` text; the 10 highest-traffic controls (home + 8 tool search boxes +
    `collections.html`'s form) have `aria-label`s. Still open: the other 35 of 45 UI pages carry no ARIA
    of their own beyond the shared palette/toast components.
12. ~~**5 orphaned-but-built modules with no UI entry point at all.**~~ — **DONE, `[1.30.0]`:**
    `commonality.py`/`tmrev.py`/`harnesstrace.py`+`pinouts.py`/`macchart.py`/`crossmethod.py` all wired
    in (`part.html`/`procedure.html`), each verified live against the real corpus or a synthetic
    response where this corpus has no organic example. Also done in the same pass: a "Related parts"
    card (`xref.py`) on `part.html`+`dossier.html`; OCR-confidence + cross-manual-conflict signals in
    the search results list; symptom/"how do I" query-shape routing; `index.html` now loads
    `/base.css`; a new `--line-ctl` interactive-control border token. See `CHANGELOG.md` `[1.30.0]` for
    the full list, including where the shipped shape deviated from the roadmap's own sketch and why
    (real measurements, not preference).
13. ~~**Route the default search box through the real RRF hybrid-fusion code.**~~ — **DONE, `[1.31.0]`:**
    `/api/search_hybrid` gained full parameter parity with `/api/search` (it was silently dropping side/
    match_any/fuzzy/mode/tm:/vehicle:/nsn: entirely — fixed first, not glossed over) and is now the home
    search box's primary endpoint, verified extensively before switching (100% result-count parity
    across ~20 diverse queries; genuine glossary-aware ranking improvement for acronym queries, confirmed
    live). Effectively also closes RapidOCR (installed + independently re-verified) and one real
    analytics gap (a `"search"` event kind that had been declared-valid since `analytics.py` was written
    but never actually logged — `top_searches` was always silently empty). See `CHANGELOG.md` `[1.31.0]`.
14. **Remaining items from the production-readiness/EMS-VIEWER-parity work, roughly in priority order
    (full detail + real benchmarks: the published Build Roadmap, Readiness Dossier, and Gap Sweep
    artifacts, plus `CHANGELOG.md` `[1.28.0]`–`[1.31.0]`):**
    - **Semantic search: decide and act.** `embed.search()` returns `{ready:false, stale:true,
      results:[]}` on this real corpus today — no `sentence-transformers` installed, the on-disk index
      has no version stamp so it's treated as stale. Either install the model + rebuild the index so it
      actually works, or pull its UI entry point (`/semantic`, the "🧠 Semantic search" nav link) until
      it does — leaving it live-but-empty is the one finding in the whole audit that actively misleads.
      Now the real prerequisite for hybrid fusion to deliver its full value (the route itself is already
      wired and safe, per item 13 above — semantic hits will fuse in automatically once this ships).
    - **4 of the 5 dead columns the Gap Sweep found, still genuinely open** (only `ref_nsn.superseded`
      was trivial, fixed in `[1.31.0]`): `parts.cagec`/`smr` are extracted by a real parser
      (`rpstl_feature.py`) that feeds a *different* database file (`rpstl.db`'s `parts_rows`), needing
      real cross-database integration to reach the main `parts` table; `parts.uoc` and `ref_nsn.data_date`
      have no extraction logic anywhere in the codebase at all.
    - **A real learned re-ranker** — gated on click volume that doesn't exist yet: `index/analytics.jsonl`
      logged zero `search`/`click` events as of the last check, though `"search"` events now log for real
      as of `[1.31.0]` (previously declared-valid but never actually written) — worth re-checking after
      real field usage accumulates.
    - **Offsite backup automation + one real restore drill.** The weekly `backupdb()` writes to the same
      disk as the live data; `docs/IMPROVEMENT-BACKLOG.md` already lists automating the offsite mirror as
      open. Nobody has ever actually restored the real 3.65GB+ index and served from it.
    - **TLS for any non-loopback deployment.** The docs already instruct units to expose the server on a
      LAN; that path currently sends the shared auth token and all manual content in cleartext.
    - **~17 more orphaned routes the Gap Sweep found, beyond the 10 now wired** (5 from `[1.30.0]`, 3 from
      `[1.31.0]`, 2 from `[1.33.0]`): standouts include `/api/tables_plus`, `/api/ingest_scan` (needs a
      product decision — see the eighth-pass note above), and `/api/schemgraph_review`. `/api/chapter_jump`
      was investigated and confirmed genuinely not worth wiring (redundant with `/api/chapters`, already
      called); the DA-2404/2407 blank-form PDFs were wired in `[1.33.0]`. See the Gap Sweep artifact for
      the full, prioritized list with placement recommendations.
    - **Strategic, not incremental** (only worth starting if multi-site fielding becomes an actual near-
      term goal): real user accounts + RBAC, a fleet update/version-inventory mechanism, load-testing at
      10× today's corpus scale, and 508/VPAT + dependency-scanning + a real pen-test toward any future
      accreditation package.

<!-- END OF FILE -->
