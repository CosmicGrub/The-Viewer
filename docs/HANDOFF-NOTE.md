# THE VIEWER — Handoff Note (reconciled 2026-09-03)

**Purpose:** hand this project to another chat/device without losing context. Read this + the canonical docs
(`docs/EXTRACTION-COVERAGE.md`, `docs/ROADMAP-1.1.md`, `docs/CHANGELOG.md`, `docs/ITERATION-SNAPSHOTS.md`,
`docs/MASTER-RECONCILIATION.md`).

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
