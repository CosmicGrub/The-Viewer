# Changelog — THE VIEWER

All notable changes to THE VIEWER. Format based on *Keep a Changelog*. Versions passed 1.0 at the
[1.0.0] cut (see `docs/RELEASE-NOTES-1.0.md`); this file's own header text said "pre-1.0 (0.x)" for
a long time after that was no longer true — fixed as part of the [1.14.0] reconciliation below, one
more small instance of the exact kind of drift that entry documents at length. Newest at top.
Standing rules in effect: **R1** backwards-compatible/rollbackable · **R2** diagram with every
addition · **R3** dark diagrams + PDF · **R4** changelog with every change.

This file was generated retroactively on 2026-06-01 to cover every prior build, and is appended on
every change going forward.

---

## [1.52.0] — 2026-09-03 — `VW.workspace`: saved, named sets of pages — CRUD (multi-window support, PR 2/18)

**VERSION → `1.52.0`.** Stage 2 of
`docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md`, riding `[1.51.0]`'s `VW.channel`. A
workspace is the data behind "reopen everything I had open for this job": a name plus an ordered
list of `{page, params}` entries, stored per browser profile. **CRUD only** — export/import (PR 3)
and the built-in templates (PR 4) are deliberately not here; they build on exactly this record
shape and this storage key.

- **`VW.workspace.create(name, items)` → id** (or `null` when storage refused the write — a caller
  must not treat that as "probably fine"; it is the difference between a UI that can say "couldn't
  save that" and one that lies). Optional third argument sets `source`, defaulting to `"manual"`
  and accepting only `"template"` as the alternative — present now rather than bolted on in PR 4,
  because the spec's record shape carries `source` from the start and without it the field would be
  a constant with a misleading name.
- **`VW.workspace.list()`** → records in creation order, oldest first. **`.get(id)`** → the record
  or `null`. **`.touch(id)`** → `true`/`false`, moving only `lastOpened` and leaving `created`,
  `name`, `items` and `source` exactly as they were.
- **Record shape** exactly as the design spec names it:
  `{ id, name, items: [{page, params}], created, lastOpened, source }`. `lastOpened` equals
  `created` on a fresh workspace on purpose — a never-reopened workspace then sorts sanely by
  `lastOpened` alone with no null handling in every consumer, and "never reopened since it was
  made" stays detectable as `lastOpened === created`.
- **Storage shape — a real decision, documented rather than left implicit**: the whole set is one
  JSON **array** under the single `viewer_workspaces` key, not an id-keyed object. `list()` is by
  far the dominant read (the saved-workspaces UI this exists to feed repaints the entire set
  whenever anything changes) and an array preserves a stable creation order for free, where an
  id-keyed object would need a sort on every `list()` to get the same guarantee; `get(id)` becomes
  a linear scan, which is the right trade for a handful of entries a person typed names for; and an
  array is already the exact shape PR 3 will serialize.
- **Every mutation publishes on `VW.channel`, with a deliberately thin payload.** `localStorage` is
  already shared across every tab on this origin for free — a second tab does not need the data
  pushed to it, it needs to be *told* something changed so it can re-read and repaint. That is the
  same philosophy the design spec describes for D (Bench sync): the channel is a notification layer
  over storage that is already shared, never a second copy of the truth. So the payload is only
  `{action, id, name, at}` — enough to repaint or highlight one row, small enough that the
  channel's storage-fallback size guard can never fire on it, incapable of going stale against the
  real stored value. The write happens **first** and the notification second, so a tab reacting to
  a notification always reads an already-committed value. Read-only calls (`list`/`get`) publish
  nothing — there is nothing to react to, and a read that broadcast would be a live-lock waiting to
  happen the moment a subscriber repaints by calling `list()`.
- **Defensive throughout**: private-browsing profiles and full quotas both throw on plain
  `localStorage` access, so every read and write is wrapped; a corrupt or hand-edited stored value
  degrades to an empty/filtered view instead of throwing; a read never rewrites storage, so a
  corrupt value stays inspectable in devtools rather than being destroyed by the act of looking at
  it. Ids are a base-36 timestamp plus 6 random base-36 characters, **checked against the ids
  actually stored and regenerated on a hit**, so a duplicate is impossible rather than merely
  unlikely, with a bounded loop and a deterministic final fallback so a pathological environment
  can neither spin forever nor return a taken id.

**Verified for real, not just asserted.** `engine/tests/js/test_workspace_node.js` — **73 checks,
all passing** (`node engine/tests/js/test_workspace_node.js` → `73 passed, 0 failed`). Every
assertion goes through the real exported functions loaded from the real `shared.js`; where a check
needs to know what was actually persisted it parses the raw `viewer_workspaces` value out of the
store directly rather than trusting the API to describe itself. Two `vm.createContext()` sandboxes
stand in for two browser tabs **sharing one `localStorage` object** — which is exactly what two tabs
on one origin have — so the design's central claim is exercised end to end: tab A creates a
workspace, tab B receives the notification over Node's real global `BroadcastChannel`, and tab B
then really does find the workspace through its own `list()`. The sandbox's `Date` is a controllable
clock (`shared.js` only ever calls `Date.now()`), which is what makes "touch updates `lastOpened`" a
real observable change rather than a check that passes vacuously when both timestamps land in the
same millisecond. Also covered: the exact stored field set (no extras), item/param normalization
(unusable entries dropped, param values coerced to strings), name/source fallbacks, id uniqueness
with a frozen clock *and* a constant `Math.random`, four shapes of corrupt stored value, storage
that refuses reads and storage that refuses writes, and the same notification over the
storage-event fallback transport with `BroadcastChannel` hidden.

**Adversarially checked** by injecting 6 real mutations into `shared.js` and re-running the suite:
5 were caught (touch not moving `lastOpened` → 3 failures; create not publishing → 4; the read
filter dropped → 1; param values not coerced → 1; a refused write reported as success → 1). The
6th — dropping the random suffix from the id generator — **survives, and that is honest**: the
collision-regeneration guard independently preserves the only property under contract (uniqueness),
producing `wsmf29czk0` / `wsmf29czk0-1` instead of colliding. Confirmed directly rather than
assumed. It is an equivalent mutant for the contract being tested, not a coverage hole.

Gates: `node --check engine/ui/shared.js` clean; `python engine/tests/rps_lint.py` →
`RPS GATE: PASS -- every ES5-required page is ES5-clean (10 modern-by-design pages noted)`, with
`shared.js` itself listed `[ ok ] ES5-clean` (strict ES5 throughout — `var`/`function` only, and
comments written to avoid the backticks/ellipses that tripped `[1.51.0]` twice, since the linter's
text scan cannot tell a comment from code). Full `verify_all.py --snapshot`:
**`63 checks | 63 ok | 0 FAILED` — `ALL GREEN`**, `safeguard verify: 733 files, 733 OK, 0 DAMAGED`.

Reported rather than quietly re-run: the **first** full `verify_all` pass showed
`63 checks | 62 ok | 1 FAILED (test_ingest_routes.py)` — 170 passed, 5 failed, all 5 in that file's
`ingest_preview`/`ingest_scan` auth-and-fence checks, which depend on process-global state
(`V._EXPOSED`, `V._AUTH_TOKEN`, `VIEWER_INGEST_ROOTS`) read by a server thread on a fixed port.
That was self-inflicted: three other suites (`test_hardening.py`, `test_uiux_fixes.py`,
`test_demo_tour.py`) were being run by hand *concurrently* with that pass, one of which stands up
its own live server. Disk was checked first (`C: 48G free`, so not `[1.51.0]`'s low-disk cascade).
`test_ingest_routes.py` then passed standalone twice (`175 passed, 0 failed`), and the full
`verify_all` re-run with nothing else touching the host came back `63/63 ALL GREEN`. Nothing in
this PR touches ingest, and the suite's own failure mode is load/port sensitivity, not `shared.js`.

- **`engine/ui/shared.js`**: `VW.workspace.create/list/get/touch`, added to the `VW` export
  alongside the existing helpers; nothing already there was touched.
- **`engine/tests/js/test_workspace_node.js`** (new): the 73-check test described above.
- **`engine/tests/test_shared_workspace.py`** (new): `node --check` syntax gate + wires that test
  into this project's usual test-runner output, gracefully skipping in a node-less environment.
  Auto-discovered by `verify_all.py`'s glob, so it joins the standard suite with no registration.

No UI changes yet — nothing calls `VW.workspace` outside its own tests. `VW.windows` and the
features that actually consume this (F's saved-workspace UI, B's curated launcher) follow in
subsequent PRs per the plan.

---

## [1.51.0] — 2026-09-03 — `VW.channel`: cross-window/cross-tab publish/subscribe (multi-window support, PR 1/18)

**VERSION → `1.51.0`.** First implementation PR from
`docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md` — a real, reusable cross-window sync
layer in `shared.js`, built deep from the start per the design spec's expanded scope (ordering,
schema versioning, an explicit payload-size guard), not a one-off Bench-only listener.

- **`BroadcastChannel` primary transport**, with an automatic `storage`-event fallback for the
  older/RPS-mode browsers this codebase still supports where `BroadcastChannel` is undefined. A
  subscriber never needs to know or care which transport delivered a message.
- **Ordering**: every envelope carries a `seq` counter scoped to (channel name, publishing tab) —
  deliberately not a global cross-tab sequence, since no single source of truth exists for that
  without real coordination overkill. A subscriber can detect it missed a message from a specific
  other tab (`meta.gap === true`), which matters most on the `storage`-event fallback path: two
  rapid writes from one tab can coalesce into a single `storage` event elsewhere, since the event
  only ever reflects the current value at dispatch time.
- **Schema versioning**: every envelope carries a `v` field; a mismatched version is silently
  ignored, never crashes a subscriber running older/newer code.
- **Size guard**: the `storage`-event fallback path (bound by `localStorage`'s shared ~5-10MB
  origin quota) throws a clear, immediate error on an oversized payload rather than letting a raw
  `QuotaExceededError` or a partially-written shared key surface downstream. `BroadcastChannel` has
  no such limit.

**Verified for real, not just asserted**: `engine/tests/js/test_channel_node.js` uses two independent
`vm.createContext()` sandboxes standing in for two real browser tabs — each gets its own
window/document/localStorage (so requiring `shared.js` into each gives genuinely independent closure
state), while both share Node's real global `BroadcastChannel` constructor. This is production code
exercising a real `BroadcastChannel` implementation, not a reimplementation of the logic under test.
16 checks, all real: cross-tab delivery/ordering/no-self-echo over `BroadcastChannel`; the
`storage`-event fallback path (captured directly from whatever listener `shared.js` itself registers,
since Node has no real cross-context `storage`-event IPC to rely on); gap detection on a simulated
coalesced write; silent version-mismatch handling; the oversized-payload guard; malformed-JSON safety.
`rps_lint` stays clean on `shared.js` (strict ES5 — caught and fixed two false positives from my own
doc comments using backticks/ellipses, which the linter's text scan doesn't distinguish from real
code).

- **`engine/ui/shared.js`**: `VW.channel.publish(name, data)` / `VW.channel.subscribe(name, fn)`.
- **`engine/tests/js/test_channel_node.js`** (new): the real cross-tab logic test described above.
- **`engine/tests/test_shared_channel.py`** (new): `node --check` syntax gate + wires the above test
  into this project's usual test-runner output, gracefully skipping in a node-less environment.

No UI changes yet — nothing calls `VW.channel` outside its own tests. `VW.workspace`, `VW.windows`,
and the features that actually consume this (D, then B/F/C/G) follow in subsequent PRs per the plan.

---

## [1.50.0] — 2026-09-03 — `tests/mutate.py` could poison the real Python bytecode cache, silently, for days

Found running the final, fresh `verify_all.py --snapshot` pass at the actual release-cut point (the same
independent-verification discipline every change this session has gone through) — and more serious than
the `[1.49.0]` hang it was found alongside investigating: **`test_patterns.py` failed with 3 real-looking
assertion failures against `patterns.tm_side("TM 9-2320-280-10")`, on a file `git diff` showed was
byte-identical to its own committed source.** Two full days after the mutation-testing run that touched
`patterns.py` last (`[1.49.0]`'s own investigation, 2026-09-01), `tm_side()` was returning
`operator=False, mechanic=True, confidence="low"` for a document number that should classify as
`operator=True, confidence="high"` — undercutting the exact "side of the house" routing this function
exists for.

**Root cause**: recompiling `tm_side()`'s own source text fresh (`exec(compile(inspect.getsource(...)))`)
gave the *correct* answer, while calling the already-loaded module function gave the *wrong* one — proving
the discrepancy lived in compiled bytecode, not source. `__pycache__/patterns.cpython-313.pyc` was still
present from the `[1.49.0]` mutation-testing session, and Python's import system was treating it as valid
for the current (correct, restored, SHA-256-verified) source. `mutate.py`'s restore step only ever
rewrote the target's **source text** and verified that text's hash — it never touched the **derived
bytecode cache** a subprocess `import` during a mutant's test window leaves behind in `__pycache__/`,
keyed by the source file's mtime+size. The mutate/restore cycle rewrites the same file, often at the same
size, fast enough for Windows' mtime resolution to alias a mutant's cached `.pyc` onto the restored
original — so the cache silently outlives the "restored, verified" source it no longer matches, and every
later process that imports the module (another test run, `VERIFY.bat`, or **the actual running
application**) inherits the mutant's logic instead of the real one, invisibly, for as long as that stale
`.pyc` sits there.

**Fix**: `mutate.py` now purges the target module's cached `.pyc`/`.pyo` immediately after every restore
— both after each individual mutant (the one that actually matters: a hard-killed run, like `[1.49.0]`'s
own incident, skips the final cleanup entirely, so only the per-mutant purge is reliable against exactly
the failure mode that caused this) and again in the final cleanup. Verified: re-ran mutation testing
against `patterns.py` (15 mutants) with the fix in place, and confirmed no `.pyc` was left in
`__pycache__/` afterward and `tm_side()` — checked directly, and via a full `test_patterns.py` run —
returned the correct, real result immediately, with no manual cache purge needed.

Remediation for the poisoning already in place: every `__pycache__/` under `engine/` was purged as an
emergency measure before this fix landed, confirmed by re-running every test file whose module was a
mutation-testing target this session (`test_patterns.py`, `test_procedure.py`, `test_features.py`,
`test_jobcard.py`, `test_property_fuzz.py`) — all clean.

A second, unrelated failure surfaced in the same verification pass: `test_ingest_routes.py`'s real,
unmocked end-to-end upload check (`_launch()` takes a genuine synchronous `safeguard.snapshot()` of every
critical engine/docs/diagram file before it spawns the ingest subprocess and returns) now measures ~24.5s
standalone — this project has accumulated hundreds of tracked source/doc/diagram files over its life, and
that real, by-design cost has grown past the test's hardcoded 15s HTTP client timeout. Reproduced the
underlying upload pipeline by hand (real subprocess, real migration, real crawl) and confirmed it works
correctly and completes in ~1-2s once actually running — the test's timeout was simply too tight for a
call that legitimately includes a scanning-cost-scales-with-project-size safety snapshot. Fixed by giving
`_req()` an explicit `timeout=` parameter (default unchanged at 15s for every other call) and passing a
wider one (60s) for the two checks that go through `_launch()`. Verified: both checks now pass cleanly,
twice in a row.

- **`engine/tests/mutate.py`**: new `_purge_pycache()`, called after both `_restore()` sites.
- **`engine/tests/test_ingest_routes.py`**: `_req()` gained a `timeout=` parameter; the real e2e upload
  check now passes `timeout=60`.

---

## [1.49.0] — 2026-09-01 — `tests/mutate.py` could hang for hours past its own `--timeout`, on Windows

Running the full `RUN-MUTATION.bat` sequence (part of pre-release verification) as direct commands
surfaced a real bug in the project's own mutation-testing tool, not the code under test: a mutant that
turns `engine/procedure_feature.py`'s blank-line-skip `i += 1` into `i -= 1` puts `parse_procedure()` into
a genuine infinite loop (`i` walks negative forever without ever raising, since Python indexing wraps).
`mutate.py --timeout 60` is supposed to kill that within a minute. Instead it hung for 5+ hours, silently,
with zero output past the prior target's summary — caught only because the wall-clock made no sense, not
because anything crashed or reported an error.

**Root cause**: `run_test()` used `subprocess.run(cmd, shell=True, timeout=timeout)`. On Windows,
`shell=True` spawns an intermediary `cmd.exe`; when `TimeoutExpired` fires, `subprocess.run()` only kills
that intermediary, not the real test process running underneath it as a grandchild. The orphaned
grandchild keeps running (and keeps the inherited stdout pipe open), so `communicate()`'s wait for
pipe-EOF never returns — the very timeout mechanism that exists to prevent an unbounded hang was itself
unbounded. A second run (`rps.py`, step 4/7) was caught and killed pre-emptively before it could repeat
the same failure, once the pattern was recognized.

**Fix**: `run_test()` now launches via `Popen` directly and, on timeout, kills the whole process tree
(`taskkill /F /T /PID <pid>` on Windows, `Popen.kill()` elsewhere) instead of the single intermediary
process. Verified directly: a deliberately-hanging grandchild process (`python -c "time.sleep(30)"` run
through a shell wrapper) now returns `"timeout"` in ~3s under a 3s cap — previously this exact shape of
command would have hung indefinitely; normal pass/fail exit codes are unaffected (checked against both a
`sys.exit(0)` and `sys.exit(1)` case); a full real run against `patterns.py` still restores the source and
passes its SHA-256 verification afterward.

- **`engine/tests/mutate.py`**: `run_test()` rewritten as above.

This doesn't change any mutation *results* — it changes whether the tool can finish reporting them. Filed
as its own fix rather than folded into the mutation-testing pass it was found during, since it's a defect
in test tooling `VERIFY.bat`/`RUN-ALL-VERIFY.bat` depend on, not in the application.

---

## [1.48.0] — 2026-09-01 — two more module self-tests hit the same env-assumption bug this session already found twice
**VERSION → `1.48.0`.** Running `VERIFY.bat`'s full per-module self-test loop (~68 modules,
`python -B <module>.py`) as part of pre-release verification — a check `verify_all.py`'s own suite
doesn't cover — surfaced two more instances of the exact bug class this session already found and fixed
twice this same day (`test_routes.py`, `test_pageqa.py`): a module's own `__main__` self-test hardcoding
the assumption that `transformers`/`torch` are never installed in this environment, which broke for real
once `sentence-transformers` (and its `transformers`/`torch` deps) got installed earlier this session.

- **`engine/vlm.py`**: its self-test called `ask()`/`ground()` with no explicit `_backend=`, relying on
  `_load_backend()` finding nothing. Once `vlm_backend.py`'s default Florence-2 backend became
  importable, `_load_backend()` started returning a real (if ultimately failing-to-load) backend —
  `available` flipped from the expected `False` to `True`, and the hardcoded `assert ... is False` calls
  failed. Fixed by forcing `VIEWER_VLM` to a genuinely-nonexistent module name before the "no backend"
  assertions, making `_load_backend()`'s `__import__()` fail deterministically regardless of what
  happens to be installed — the identical fix already applied to `test_pageqa.py`.
- **`engine/pageqa.py`**: a subtler cascade of the same root cause. `pageqa.available()` is
  `vlm.available() and _gpu_tier()` — once `vlm.available()` started returning `True`, that gate silently
  passed on this real GPU-equipped dev machine, skipping straight past the intended "no backend
  installed" short-circuit and falling through to a real page-render attempt for a doc/page that doesn't
  exist in the self-test's fixture-free context — surfacing as a confusing "could not render doc 1 page
  1" note instead of the intended "no backend" one. Same fix: force `VIEWER_VLM` to a nonexistent module
  name before the self-test's "no backend" assertions.

**Not found by any test suite until now** — `verify_all.py --snapshot` (run dozens of times across this
session) never exercises these two modules' own `__main__` self-test blocks; only `VERIFY.bat`'s
dedicated per-module self-test loop does. A real, concrete argument for keeping that gate in the
pre-release checklist rather than treating `verify_all.py --snapshot` as sufficient on its own.

**Verified:** `python -B vlm.py` and `python -B pageqa.py` both pass cleanly post-fix; the full 68-module
self-test loop (`VERIFY.bat`'s gate 6) is clean; `engine/tests/verify_all.py --snapshot` clean per the
now-3 documented pre-existing flakes.

---

## [1.47.0] — 2026-09-01 — adversarial verification of [1.46.0]: 3 real, confirmed, blocking issues fixed
**VERSION → `1.47.0`.** An adversarial-verification pass on `[1.46.0]` (directly below) found three
real, confirmed, blocking issues in that work before it merged. All three fixed here.

- **CRITICAL — the "generalized" contrast guard couldn't actually catch compound-selector
  failures.** `engine/verify_ui.py`'s `_is_pure_class_selector()` used the regex
  `^\.[A-Za-z0-9_-]+$`, which has no `.` in its character class — it could never match a multi-class
  selector token like `.tag.bad` (a second `.` before "bad" always fails the match).
  `_parse_css_rules()` gated *both* the single- and compound-selector branches behind this one check,
  so every compound-selector rule in every page was silently discarded before parsing — the
  `compound` dict was provably always empty and that entire code path was dead. This directly
  contradicted `[1.46.0]`'s own central claim of closing "exactly the gap that let `status.html`'s
  real `.tag.bad` failure ship invisibly before" — `.tag.bad` **is** a compound selector, and the
  guard still could not catch a regression to that exact rule. Confirmed via a real adversarial test:
  injecting a genuine severe-contrast rule as `.injectedbad.contrast{color:#333333;
  background:#222222}` into `status.html` was **not** caught by the pre-fix scanner (pair count
  unchanged at 146, 0 FAIL). **Fixed**: `_CLASS_TOKEN_RE` now matches one-or-more `.class` segments
  (`^(?:\.[A-Za-z0-9_-]+)+$`) instead of exactly one — a lone `.tag` still matches (one repetition)
  and `.tag.bad` now also matches (two repetitions); `_classes_in()` already knew how to pull every
  class out of either shape via `_CLASS_FIND_RE`, so no other code needed to change. Re-ran the
  identical adversarial test after the fix: the pair count rose from 146 to 147 and the injected rule
  was correctly flagged `FAIL -- 1.26:1, below the 4.5:1 floor`; the injection was then fully reverted
  (byte-identical `status.html`, confirmed via `git diff`, 146 pairs / 0 FAIL restored). The
  scanner's real, corrected final state across the real 48 pages is **146 class/descendant pairs
  checked, 117 OK, 0 FAIL, 29 SKIP** — not the 67/51/0/16 `[1.46.0]` reported, which (per the bug
  above) never actually included a single compound-selector rule.
- **A disclosure-list count/list mismatch, repeated across all 5 canonical docs.** `CHANGELOG.md`,
  `PROJECT-SUMMARY.md`, `MASTER-RECONCILIATION.md`, `HANDOFF-NOTE.md`, and `ITERATION-SNAPSHOTS.md`
  all said "27 pages still carry zero ARIA" but then enumerated exactly 30 names (`CHANGELOG.md` even
  self-flagged this — "that's 30 names" — without resolving it). Separately, `review.html` is
  genuinely zero-ARIA (confirmed: zero occurrences of `aria-`/`role=` in the file), was not touched by
  `[1.46.0]`, and was absent from every one of the "named in full" lists in all 5 docs, despite
  `[1.46.0]`'s own stated ethos being "not silently implied as covered." **Fixed**: recounted the real
  zero-ARIA page set directly from `engine/ui/*.html` (fresh grep for `aria-`/`role=`, not trusted
  from the prior draft) — **31 pages**, not 27 or 30: the same 30 names as before, plus `review.html`.
  `cadtex_test.html` (32nd zero-ARIA page) stays excluded on the same already-established
  unreachable-through-any-route basis. The number and the enumerated list now agree everywhere — see
  the corrected list in `[1.46.0]` directly below (fixed in place, since it is that entry's own claim
  being corrected) and in `PROJECT-SUMMARY.md`/`MASTER-RECONCILIATION.md`/`HANDOFF-NOTE.md`;
  `ITERATION-SNAPSHOTS.md`/`ITERATION-DASHBOARD.html` regenerated via `build_iteration_snapshot.py`
  from this corrected `CHANGELOG.md`, never hand-edited.
- **A false "0 flakes / 61/61 GREEN" claim.** `[1.46.0]`'s PR body, `CHANGELOG.md`, `HANDOFF-NOTE.md`,
  `PROJECT-SUMMARY.md`, and `ITERATION-SNAPSHOTS.md` all identically claimed "61/61 GREEN, 0
  failures... no flakes needed this run." Independent re-runs of `verify_all.py --snapshot` this pass
  (three total, see below) never once reproduced that exact "0 flakes" outcome — the specific "no
  flakes occurred" claim was false as stated, whatever the true flake rate actually is. **Fixed**:
  `[1.46.0]`'s "Verified" paragraph now carries an explicit correction rather than the unqualified
  original claim, and this entry reports its own three `verify_all.py --snapshot` runs exactly as
  observed, not assumed clean.

**Verified — three separate `python engine/tests/verify_all.py --snapshot` runs this pass, reported
exactly as observed:**
- **Run 1** (concurrent with this pass's own doc edits, house rules' documented background embeddings
  rebuild also running): **58/61** — `test_routes.py`'s `/api/ask` timeout, `test_http.py`'s
  `/api/pageqa` timeout, and `safeguard verify` (flagged `CHANGELOG.md`/`HANDOFF-NOTE.md` as
  MODIFIED/GREW and `PROJECT-SUMMARY.md` as "CORRUPTED" — a false positive: these files were being
  actively hand-edited by this very pass while the run's own snapshot/compare cycle executed, not real
  corruption).
- **Run 2** (still concurrent with one further doc edit mid-run): **60/61** — only `safeguard verify`
  failed (`HANDOFF-NOTE.md` "SHRUNK" — again this pass's own concurrent edit, not corruption);
  `test_http.py` and `test_routes.py` both passed clean this time.
- **Run 3, the authoritative one — zero files touched anywhere in the repo for its entire duration**:
  **60/61** — `test_routes.py`'s `/api/ask` timeout (`safeguard verify`: clean, 731/731 files OK, 0
  DAMAGED, confirming Runs 1–2's safeguard failures really were this pass's own concurrent edits and
  not real file damage). Re-ran `test_routes.py` standalone immediately after: the same `/api/ask`
  timeout reproduced. This is one of the three flakes already documented as pre-existing and
  load-sensitive in this repo's own house rules (`test_ingest_routes.py`, `test_routes.py`'s
  `/api/ask`, `test_http.py`'s `/api/pageqa`) — seen on both `test_routes.py` and `test_http.py`
  across these three runs, never on the same endpoint twice, consistent with genuine
  intermittent/load-sensitive flakiness (the same background embeddings rebuild competing for CPU/IO
  throughout this session) rather than a deterministic regression; neither endpoint is touched by any
  change in `[1.46.0]` or this entry.

`engine/verify_ui.py` run standalone after the fix: `wcag text-contrast (scan) : checked 146
class/descendant color+background pairs across all 48 ui/*.html pages -- 117 OK, 0 FAIL, 29 SKIP` —
confirmed identical before and after the adversarial injection/revert cycle described above (147/1
FAIL with the injection present, 146/0 FAIL after reverting). `python engine/build_iteration_snapshot.py`
re-run against the corrected `CHANGELOG.md`: `R10 integrity OK -- all 250 changelog versions present
in the snapshot.`

---

## [1.46.0] — 2026-09-01 — accessibility work extended beyond index.html: real contrast fixes, modal focus traps, a generalized contrast guard
**VERSION → `1.46.0`.** `[1.29.0]`'s accessibility pass fixed index.html and disclosed, by name, that
the other 47 pages carried zero or partial ARIA — a research pass this session re-verified that
disclosure against the real files (grepping every page for `aria-`/`role=`, reading `verify_ui.py`,
`shared.js`, and a sample of the zero-ARIA pages in full) and found a **correction to its own prior
numbers**: `status.html`'s `.tag.ok` was carried on prior lists as a 3.10:1 WCAG failure, but that
figure is base.css's un-overridden `--grn` on `--panel2` — this page's own local `:root{--grn:#2f9d63}`
override (loaded after `/base.css`, so it wins the cascade) actually measures **4.56:1, a genuine
(if narrow) PASS**. Left untouched here rather than "fixed" — see below.

- **`demo.html`'s local `:root` token override removed.** It shadowed all 12 of base.css's own tokens
  verbatim plus one base.css lacked (`--grn2`, used by `.kbd`/`.meter` text and `.prog>i`'s gradient) —
  every value matched base.css exactly **except `--red`** (`#c4585a` locally vs. base's `#e0564f`),
  the direct cause of the contrast failure below. `--grn2` moved into `base.css` itself (same
  `#7fd6a6` value) since it had no home there; the page now inherits base.css's cascade like every
  other page, confirmed visually unchanged live except for `.warn .n`'s color, fixed next.
- **3 real WCAG AA text-contrast failures fixed, using the existing `--red-tx` text-safe token
  (`[1.29.0]`)** — recomputed before/after from each file's actual resolved hex (relative-luminance
  formula, same as `verify_ui.py`'s):
  - `status.html` `.tag.bad` — `color:var(--red)` (`#e0564f`) on `.tag`'s `var(--p2)` (`#1c2430`) was
    **4.18:1**, below the 4.5:1 floor → `color:var(--red-tx)` (`#ec7a74`) is now **5.65:1**.
  - `demo.html` `.warn .n` — the page's own (now-removed) local `--red` (`#c4585a`) on `.step`'s
    `var(--panel)` (`#171d26`) was **3.94:1** → `--red-tx` on the same background is now **6.13:1**
    (`border-color` stays plain `--red` — a decorative border use, 3:1 floor, unaffected).
  - `index.html`'s 2 remaining inline `color:var(--red)` stragglers (`.catch()` error spans at the old
    line 908/958, `.modal`'s `var(--panel)` background) — recomputed at **4.53:1**, a narrow but real
    AA pass, not the outright failure the other two are; swapped to `--red-tx` anyway (now **6.13:1**)
    for consistency with the token convention the rest of the function already uses (`--grn-tx`/`--amb`/
    `--teal` on sibling spans) and a real safety margin instead of a 0.03 one.
  - **`status.html` `.tag.ok` deliberately left untouched** — see the correction above; it already
    passes at 4.56:1 via this page's own `--grn` override, and "fixing" a control that isn't broken
    would have been a wasted diff.
- **`schematics.html`/`threed.html`'s gate modals now get real dialog semantics** —
  `role="dialog" aria-modal="true" aria-label="…"`, matching `index.html`'s 5 modals — **and**
  `VW.trapFocus("gate")` (Tab-cycle containment, Escape-to-close, focus-restore), which required a
  real fix, not just a copy-paste call site: both gates open/close via
  `classList.add/remove('on')` against the CSS rule `.gate.on { display:flex }`, never touching the
  inline `style` attribute at all, while `shared.js`'s `trapFocus()` as written only ever watched the
  inline `style` attribute and checked `el.style.display` directly — attaching it as-is would have
  silently never fired `onShow()`/`onHide()` (no error, no visible breakage, just a modal that never
  traps focus — the exact "ships clean, nobody notices" failure mode this pass exists to catch).
  Generalized `trapFocus()` instead of touching either page's open/close call sites: `isVisible()` now
  reads `getComputedStyle(el).display`, the `MutationObserver` now watches both the `style` and
  `class` attributes, and the Escape handler detects which convention is live (inline style vs.
  classList) and closes the same way, so re-opening afterward is never broken by a stale inline style
  fighting the CSS rule. This is the smaller, centrally-owned fix, and makes `trapFocus()` correct for
  whatever pattern the *next* modal happens to use — verified live in a real browser for both pages:
  opening moves focus in, Escape closes via the correct mechanism (confirmed no stray inline
  `style="display:none"` is left behind), and re-opening afterward still works. `index.html`'s 5
  existing modals re-verified unaffected (inline-style path unchanged byte-for-byte in behavior).
- **`engine/verify_ui.py`'s WCAG contrast guard generalized from a 3-pair hardcoded list to a real
  per-page scan.** The old guard only ever opened `ui/base.css`'s and `ui/index.html`'s own `:root{}`
  blocks — it never opened any of the other 47 pages' CSS at all, and even for those two files it
  checked base.css's tokens in isolation rather than simulating what a page's *own* local `:root{}`
  override does to the cascade. That gap is exactly how `status.html` shipped a real `.tag.bad`
  failure invisible to CI while its neighboring `.tag.ok` (which looks identical on paper) was
  actually fine — the guard had no way to tell them apart because it never looked at `status.html` at
  all. The new `_scan_page_contrast()` (i) resolves each page's own tokens through base.css's
  `:root{}` **overridden by that page's own `:root{}`** (cascade-aware, not base.css read alone), and
  (ii) parses every one of the 48 `ui/*.html` pages' `<style>` block(s) for class-selector rules —
  single class, no-combinator compound (`.tag.bad`), or 2-level descendant (`.warn .n`) — resolving
  the nearest opaque background it can find (the rule's own, its constituent single-class rules, or —
  for a case like `.warn .n` where the ancestor's own background is a translucent `rgba()` overlay —
  the real class combinations the page's actual HTML uses together, e.g. `class="step warn"`, so
  `.step`'s opaque `var(--panel)` is found as the real backdrop instead of giving up). Deliberately
  **not** a full CSS cascade/specificity engine: it skips (never guesses) anything it can't resolve
  with confidence — most notably several real `color:var(--X)` usages set via inline
  `style="..."` on JS-generated markup with no co-located background in the same string (e.g.
  `index.html`'s `--grn-tx`/`--red-tx` spans), which need a real DOM+cascade simulation to resolve and
  are out of scope for a static text scanner. Those are kept as the original small hand-verified
  `_TEXT_PAIRS` list, now explicitly scoped to just that residual case instead of silently dropping
  the coverage. Running the new scan against the real 48 pages surfaced (and fixed) **2 more
  previously-unknown real failures**, neither part of the `--red`/`--grn` token family this pass
  otherwise touched: `index.html`'s `.sheetprev .e` (a "field left blank" placeholder in the printed
  parts-request-sheet preview) was **2.26:1** on its `#f4f1ea` paper-toned background — `#a8a293` →
  `#6b675c`, now **5.00:1**; `measures.html`'s `.em .tagx` badge was **4.43:1**, just under the floor —
  `#8a7a52` → `#93835a`, now **5.00:1**. (One real bug caught building the scanner itself: an early
  version resolved a descendant rule's background from its *ancestor* even when the rule itself
  declared its own background alongside its color — e.g. `demo.html`'s self-contained
  `.res .pill{color:#06223f;background:var(--acc)}` badge was flagged as a bogus 1.05:1 "failure"
  against `.res`'s unrelated ancestor background before this was caught and fixed.) Final state as
  originally shipped: 67 class/descendant pairs checked across all 48 pages, 51 OK, 0 FAIL, 16 SKIP
  (translucent or inline-only — the documented, disclosed limitation above). **Correction (adversarial
  verification, see `[1.47.0]`):** that "67" figure was itself wrong — `_is_pure_class_selector()`'s
  regex (`^\.[A-Za-z0-9_-]+$`) had no `.` in its character class, so it could never match a
  multi-class token like `.tag.bad`, and `_parse_css_rules()` gated *both* the single- and
  compound-selector branches behind that one check. Every compound-selector rule on every page —
  including `status.html`'s own `.tag.bad`, the exact rule this pass's own narrative names as the
  motivating failure — was silently discarded before parsing; the `compound` dict was provably always
  empty and that whole code path was dead, so the scan never actually gained the "compound-class"
  coverage its own comments and this entry claimed. Fixed in `[1.47.0]` (a corrected regex that
  matches one-or-more `.class` segments) and adversarially re-verified by injecting a real severe
  compound-class contrast failure into a live page and confirming it is now caught. The real,
  corrected final state is **146 class/descendant pairs checked across all 48 pages, 117 OK, 0 FAIL,
  29 SKIP** — see `[1.47.0]` for the full account.
- **Baseline ARIA — `role="main"`, `aria-label`s on unlabeled inputs, `aria-live="polite"` on async
  result regions, and dialog semantics + focus traps on any modal — landed on 10 pages this pass**:
  `collections.html`, `threed.html`, `status.html`, `schematics.html`, `verify.html`, `jobcard.html`,
  `part.html`, `visual.html`, `procedure.html`, `demo.html`. Scope picked from real (if thin — 85
  `k:"tool"` events across 30 routes, several tied at 1 hit) click-analytics traffic
  (`index/analytics.jsonl`) plus the pages this pass already had open for the contrast/modal work
  above: top-4 by real traffic (`collections`, `threed`, `verify`, `jobcard`) + the 3 pages touched
  for contrast/modals (`status`, `schematics`, `threed` — overlap with traffic) + 2 more
  already-partial-ARIA core workflow pages (`part`, `procedure`) + `demo.html` (the app's first-run
  onboarding surface, already being touched for the token-override fix above, so its landmarks landed
  in the same pass rather than a second later touch of the same file). `demo.html`'s gate gets dialog
  semantics (`role="dialog" aria-modal="true"`) but **not** a full focus trap — it deliberately never
  loads `shared.js` (its injected bottom-corner pills would collide with this page's own full-width
  control bar), so `VW.trapFocus()` isn't available there; disclosed rather than silently left partial.
  **Honestly left open, matching `[1.29.0]`'s own disclosure convention rather than implying full
  coverage**: 31 pages still carry zero ARIA of their own — `ask`, `audit`, `bench`, `binaudit`,
  `circuitlab`, `command`, `coverage`, `decode`, `deepzoom`, `exploded`, `fastener`, `handover`,
  `help`, `ingest`, `keywords`, `kg`, `learn`, `master`, `mastercov`, `measures`, `ops`, `partdiff`,
  `pmcs`, `publog`, `readiness`, `related`, `review`, `scan`, `semantic`, `solve`, `troubleshoot` —
  the analytics data thins out fast past the top ~10 (many routes tied at 1 hit), so ranking which of
  these 31 goes first by "traffic" would present noise as signal — left as a ready-made list for a
  future pass rather than an invented ranking. (This count/list corrects a defect a `[1.46.0]`
  adversarial-verification pass caught: this same section, in every one of the 5 canonical docs, said
  "27" while enumerating 30 names, and `review.html` — genuinely zero-ARIA, confirmed by a fresh grep,
  untouched by this pass — was missing from every one of those lists despite this pass's own stated
  "not silently implied as covered" ethos; recounted here directly from `ui/*.html` rather than
  trusted from the prior draft.) `cadtex_test.html` (the 48th page) is confirmed unreachable through
  any route in `engine/features/routes/static.py`'s dispatch table — a standalone WebGL shader
  smoke-test a developer opens directly, not part of the running app — and is deliberately excluded
  from this and any future ARIA pass on that basis (so the 31 above, not 32, is the real "pages
  reachable in the running app with zero ARIA" count).

**Verified (as originally claimed when this entry shipped):** `python engine/tests/verify_all.py
--snapshot` from a clean run: **61/61 checks GREEN, 0 failures** — no flakes needed this run (all
three previously-documented ones, including the `test_ingest_routes.py`/`test_routes.py`/
`test_http.py` timeouts, happened to pass clean). **Correction (adversarial verification, see
`[1.47.0]`): this specific "0 flakes" claim was false as stated.** Three independent re-runs never
once reproduced 0 flakes: the authoritative run (no concurrent edits) got 60/61 on `test_routes.py`'s
`/api/ask` timeout (reproduced by re-running `test_routes.py` standalone), an earlier run got 60/61 on
`test_http.py`'s `/api/pageqa` timeout instead — both already-documented pre-existing, load-sensitive
flakes, not a real regression, but the claim that no flake occurred this run was not accurate; see
`[1.47.0]` for the real, honestly reported results. All 10 ARIA-scoped pages and the two modal pages hit live via a real running
`viewer_app.py` instance and verified in a real browser: `demo.html` renders identically with the
token override removed; `.warn .n`'s resolved `color`/`border-color` match the intended
`--red-tx`/`--red` split exactly; `schematics.html`/`threed.html`'s gates carry the correct
`role`/`aria-modal`/`aria-label`, move focus in on open, and close via the correct (class vs.
inline-style) mechanism on Escape with no stale state left behind; `index.html`'s 5 pre-existing
modals re-verified unaffected. `verify_ui.py` run standalone: the new generalized WCAG scan was
clean at the time (0 FAIL, 51 OK, 16 documented SKIP) but under a scanner that could never actually
scan a compound-class selector — see the correction above and `[1.47.0]`. One pre-existing,
unrelated failure noted but **not** fixed here (out of scope) — `ui/index.html` declares an inline
`function esc(...)` while also loading `/shared.js`, tripping the separate shared.js-dedup guard;
confirmed present on `origin/main` before this branch via `git show origin/main:engine/ui/index.html`,
not reachable from `verify_all.py --snapshot`'s own suite (`verify_ui.py` isn't wired into it), and
unrelated to accessibility work.

---

## [1.45.0] — 2026-09-01 — search UI now shows an honest signal when semantic search is degraded or rebuilding
**VERSION → `1.45.0`.** Prior to this, `hybrid.hybrid_search()` (the function behind the primary
`/api/search_hybrid` endpoint) called `embed.search()` but kept only `.get("results")` — it discarded
`ready`/`stale` entirely, so the only trace of semantic-index health reaching the UI was
`signals.semantic === 0`, which is identical whether the index was never built, is stale, is
mid-rebuild, or the query just had zero semantic matches. There was also no way to tell "never built"
apart from "actively rebuilding" anywhere in `embed.py` — `build_index()` writes
`embeddings.progress.json` while a rebuild runs, but nothing at query time ever read it.

- **`engine/embed.py`**: added `_build_progress(index_dir)` (reads `embeddings.progress.json`'s
  `rows_done`/`limit` into a percent-complete figure when a rebuild is actually in flight) and
  `semantic_status(index_dir)`, a query-independent helper returning
  `{"state": "ready"|"never_built"|"rebuilding"|"stale", "progress": {...}|None, "backend": ...}`.
  `search()` itself is unchanged — this is a new, additive helper, not a modified contract.
- **`engine/hybrid.py`**: `hybrid_search()` now also calls `embed.semantic_status()` and forwards it
  as a new top-level `semantic_status` field on the `/api/search_hybrid` response, alongside the
  existing `signals` block (which is unchanged).
- **`engine/ui/index.html`**: new `renderSemanticStatus(d, q)`, called from `runSearch()` right next
  to the existing `renderSearchHints()`. Styled identically to `renderSearchHints()`'s quiet
  `.searchhints` card (`afterbegin` into `#results`, `var(--panel)`/`var(--line)`/`var(--sub)`,
  12.5px, no `role="alert"`) — deliberately **not** `shared.js`'s `_staleBanner()` treatment
  (fixed-position, red, non-dismissible), which is reserved for the unrelated code-version-mismatch
  emergency. Shown only when `semantic_status.state !== "ready"` **and** the search actually returned
  keyword results, so it never displaces the "No matches" empty state — keyword search always works
  regardless of semantic health. Dismissible per-state via a `✕` that sets
  `sessionStorage['vw-semstatus-dismissed-<state>']`, so dismissing "rebuilding" doesn't suppress a
  later "stale" state reached by a different path.
- Four distinct, honest copy strings, one per real state (`ready` renders nothing):
  - `never_built`: "🧩 Semantic (meaning-based) search hasn't been set up on this install yet —
    results below are keyword matches only."
  - `rebuilding`: "⏳ Semantic search is building its index (N% complete) — results may improve once
    it finishes." (N computed live from `embeddings.progress.json`)
  - `stale`: "🔄 Semantic search's index is out of date and needs a rebuild — results below are
    keyword matches only."

**Verified live, not just static HTML**: this session's own semantic-index rebuild (`embed_rebuild_v2.py`,
already running in the background per house rules — confirmed via `tasklist`/`embeddings.progress.json`
before touching anything) put the real repo in a genuine `rebuilding` state throughout testing.
Called `embed.semantic_status()` directly against the real `index/` dir: `{"state": "rebuilding",
"progress": {"percent": 25, "rows_done": 505000, "limit": 2000000}, ...}`. Started a real second
`viewer_app.py` instance (`--db index/viewer.db --port 18901`, read-only) and hit the live
`/api/search_hybrid?q=brake` endpoint directly: the response's top-level `semantic_status` field
matched (`rebuilding`, `26%` a few seconds later — the background rebuild progressing). Also verified
`never_built` and `stale` by pointing `embed.semantic_status()` at isolated scratch index directories
(one empty, one with only `embeddings.npy`/`embeddings_ids.tsv` copied over and no
`embeddings.meta.json`/`embeddings.progress.json`) outside the repo — not simulated in code, actual
function calls against real files on disk. Test server process cleanly killed by PID after
(`netstat`-matched to port 18901, not the pre-existing rebuild process) — the pre-existing background
rebuild was never touched.

**`engine/tests/verify_all.py --snapshot`**: clean except the three documented pre-existing flakes
(`test_ingest_routes.py`'s real-subprocess e2e flake, `test_routes.py`'s `/api/ask` timeout,
`test_http.py`'s `/api/pageqa` timeout) — all independently reproduced this session as pre-existing,
transport-timeout-related, and unrelated to this change, and all the more likely with the same
concurrent background embeddings rebuild competing for CPU/IO throughout this session's testing.

---

## [1.44.0] — 2026-08-31 — first real backup restore drill performed and documented
**VERSION → `1.44.0`.** `safeguard.py backupdb()`'s `PRAGMA quick_check` (run at backup time, see
`[1.25.0]`) proves a backup file's SQLite B-tree structure is internally consistent — it never opens a
connection against the app's own tables, runs a real query, or feeds a result through the app layer.
A backup could be schema-stale, or app code could drift ahead of a backup's schema, and
`quick_check` would never know. This had never actually been tested end-to-end.

- **Ran a real restore drill**, documented in full at `docs/RESTORE-DRILL-LOG.md`: copied (never
  moved) `backups\db\viewer-20260830-1348.db` (3.64 GB, SHA-256-verified identical after copy) to an
  isolated scratch location outside the repo, started a genuinely separate `viewer_app.py` instance
  against only that copy on an unused port (`18765`), and hit `/healthz`, `/api/part_record`,
  `/api/part_by_number`, `/api/search`, and `/api/pmcs` with real queries against the restored data.
- **Found a real gap**: `/api/search` and `/api/pmcs` both return `200` with silently empty results
  against this backup. Root cause confirmed directly against the restored file (not assumed): the
  backup's `pages` table predates the `ocr_confidence` column (`schema_version=8`, `healthz`'s own
  `schema` check already said `WARN: schema_version=8 < migrations=12`), and current app code
  (`search_feature.py:_meta_rows()`, its LIKE fallback, and `corpus.py:fts_pages()`, used by
  `pmcs.find()`) unconditionally selects that column, throws, and swallows the error into an empty
  `200` with no error surfaced anywhere the UI or `/healthz`'s top-level `ok:true` would show it. The
  identical FTS query run directly against the restored file (no app layer) returns correct real hits
  immediately — this is purely an app/schema-version mismatch, not a corpus or FTS problem.
  `/api/part_record`/`/api/part_by_number` are unaffected (they never touch `pages.ocr_confidence`)
  and served correct real data from the restored copy. **No code changed to work around this** — left
  for a human to decide (schema-version gate on restore, run `fix_schema_version.py` against future
  backups first, or otherwise); see `docs/RESTORE-DRILL-LOG.md` for the full request/response record.
- Cleanly shut the drill instance down (Windows required a forceful `taskkill /F` — non-forceful
  `taskkill` did not stop a console-less Python HTTP server within 2 s, a Windows platform limitation,
  not a drill defect), deleted only the scratch copy, and verified byte-for-byte (size + mtime +
  SHA-256 on the backup) that the original backup file and `index/viewer.db` were untouched throughout.
- Live free-disk-space check at drill time found `E:` at **6.3 GB free**, not the ~63 GB an earlier
  planning pass had estimated — flagged here as a real, order-of-magnitude discrepancy; the drill's
  scratch copy was placed on `C:` instead (8.69 GB free at the time), which left adequate margin.

**Verified:** `engine/tests/verify_all.py --snapshot` run four times while an unrelated background
embeddings rebuild (`embed_rebuild_v2.py`, left running throughout per this drill's own "do not
disturb" plan) was competing for CPU/IO — results varied run to run between the two previously
documented flakes (`test_ingest_routes.py`'s real-subprocess e2e flake, `test_routes.py`'s `/api/ask`
timeout) and a third, not-previously-documented transport timeout (`test_http.py`'s `/api/pageqa`,
also LLM/vision-backed and slow). **Confirmed pre-existing and unrelated to this docs-only change**:
`git stash` back to unmodified `origin/main` and re-ran `test_http.py` alone — the identical
`/api/pageqa` timeout reproduced. All observed failures across all runs were transport timeouts on
slow, model-backed endpoints under the concurrent rebuild's load, never a correctness assertion;
`docs`/`VERSION`-only changes never touch any request-handling code path. No app code changed.

---

## [1.43.0] — 2026-08-31 — TLS support for LAN-exposed deployments
**VERSION → `1.43.0`.** Every existing safeguard for a LAN-exposed VIEWER (`VIEWER_ALLOWED_HOSTS`,
`VIEWER_AUTH_TOKEN` gating `X-Viewer-Token`) protected *authentication* over plain HTTP — the token
itself, and the search/TM/parts/NSN content it protects, still crossed the network unencrypted,
readable to anyone else on the same LAN segment sniffing traffic. There was no transport-layer
option at all; adding one had to not disturb the documented Win7/Vista-capable, stdlib-only server
path (`engine/preflight.py`'s docstring) for the vast majority of installs that never touch it.

- **New CLI flags, off by default: `--tls`, `--cert`, `--key`** (`engine/viewer_app.py`). An existing
  `python viewer_app.py --host 0.0.0.0` invocation is byte-for-byte unchanged unless `--tls` is
  passed explicitly. `--tls` alone looks for `engine/certs/viewer-cert.pem`/`viewer-key.pem`;
  `--cert`/`--key` point at a different pair. If `--tls` is passed and no cert/key resolves, the
  server fails fast with a clear message pointing at the new `gen_cert.py` — it never silently falls
  back to serving plaintext when TLS was explicitly requested.
- **`engine/gen_cert.py`** — a new, one-time, operator-run CLI that mints a self-signed RSA-2048
  cert/key pair (10-year validity; a self-signed LAN cert an operator manually trusts isn't bound by
  the CA/Browser Forum's ~398-day public-CA lifetime cap). subjectAltName covers `localhost`,
  `127.0.0.1`, every LAN IP it can auto-detect, plus anything passed via `--san`. **Dependency
  decision**: gated behind an optional `cryptography` import (commented out in `requirements.txt`'s
  OPTIONAL tier, printed as a manual `pip install` suggestion in `INSTALL.bat` — the exact existing
  pattern `sentence-transformers`/`rapidocr-onnxruntime`/`pyzbar` already use), not an `openssl`
  shell-out (this app's own documented legacy floor, Win7/Vista on Python 3.8/3.4, has no guaranteed
  `openssl.exe` on PATH) and not a vendored ASN.1/X.509 encoder (hand-rolled crypto/DER code is far
  riskier to maintain than depending on the field-standard library other trusted packages already
  build on). `cryptography` is needed for this ONE offline, one-time step only — never imported by
  the running server, which serves TLS entirely via stdlib `ssl`. The equivalent `openssl` one-liner
  is documented for operators who'd rather not `pip install` anything.
- **Server wiring**: `ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)` (minimum TLS 1.2) wraps the server's
  *listening* socket once, in `main()`, right after `_BoundedThreadingHTTPServer` is constructed and
  before `serve_forever()` — `Handler`/`BaseHTTPRequestHandler` and the bounded-worker semaphore are
  completely unmodified; `socket.accept()` on a TLS-wrapped listening socket returns already-
  terminated connections. `safe_public_base()` (feeds QR codes / deep links via `/api/qr`) now emits
  `https://` when TLS is active instead of a hardcoded `http://`; the loopback-detection check that
  reads its output (`X-QR-Local-Only`, `doc_extractors.py`) was made scheme-agnostic to match.
- **New test** `engine/tests/test_tls.py`: generates a real cert via `gen_cert.generate()`, wraps a
  real `ThreadingHTTPServer`'s listening socket exactly as `main()` does, and confirms — through a
  genuine TLS handshake, no mocks — an `https://` request succeeds with a real 200 JSON response, a
  plain `http://` request to that same port is rejected (invalid ClientHello), a client that doesn't
  trust the self-signed cert is rejected (the real "browser warning" case), the ordinary plain-HTTP
  path is unaffected when `--tls` is never passed, `main()` fails fast (never binds a socket) when
  `--tls` is requested with no cert/key resolvable, and `safe_public_base()`'s scheme follows
  `TLS_ENABLED`. Skips gracefully if `cryptography` isn't installed, matching this repo's existing
  optional-dependency test convention. New doc `docs/TLS-LAN-SETUP.md`: cert generation, per-platform
  browser-trust steps, and an explicit "what this does and doesn't protect against" section (passive
  LAN sniffing: yes; an active on-LAN attacker who isn't verified against the cert fingerprint: no;
  a substitute for a real CA-signed cert once reachable beyond a trusted LAN/VPN: no).

**Verified:** `engine/tests/verify_all.py --snapshot` clean except the two now-documented pre-existing
flakes (`test_ingest_routes.py`'s real-subprocess-e2e flake, `test_routes.py`'s `/api/ask` timeout —
both independently reproduced as pre-existing and unrelated to this change).

---

## [1.42.0] — 2026-08-31 — a stale running server is now visible, not silent
**VERSION → `1.42.0`.** Nothing anywhere recorded when the running process started, or whether the
code it launched with still matched what was on disk. A server left running across a `git pull` (or
any on-disk edit that never got a restart) looked completely healthy — it answered every request
fine — while quietly running a stale build of the app, with no signal anywhere for an operator to
notice short of reading a timestamp on the process itself.

- **`STARTUP_VERSION` / `STARTUP_TIME`** (`engine/viewer_app.py`, next to `VERSION`) are captured
  once, at import time, and never change for the life of the process.
- **`current_disk_version()`** does a plain `open()` + regex re-read of just the `VERSION = "..."`
  line of `viewer_app.py` on disk (a few hundred bytes) — never a re-import (`sys.modules` and the
  running feature-module DI graph are untouched) and never `git` (this app runs stdlib-only on
  fielded/legacy machines by design; see the module docstring). TTL-cached at 30s so a burst of
  `/healthz`/`/api/ops` polling costs at most one file read per window, not one per request; fails
  open (any read/parse error just returns the last known value) so a transient I/O hiccup can never
  flip a health check to unhealthy.
- **New fields on `/healthz` and `/api/ops`**: `started_with_version`, `started_at`, and
  `code_changed_since_start` (true when the freshly-read on-disk `VERSION` no longer matches
  `started_with_version`). The existing `version` field is left untouched — it stays the in-memory
  version this process is actually running; the new fields are what make it *possible* to notice it
  no longer matches disk.
- **A non-dismissible banner**, self-injected by `shared.js` (same self-injecting/id-guarded
  `_footerNav` pattern, `#vw-stalebanner`) on every page — not just `/ops` — polling `/healthz` on
  load and every 5 minutes: *"⚠ Running code is stale — server started on vX.Y.Z, disk now has
  vA.B.Z. Restart the server to pick up the fix."* Deliberately carries no dismiss control and no
  `localStorage` suppression — a banner a mechanic can click away and never see again is exactly the
  "silent for weeks" failure mode this closes. It clears itself automatically once the process is
  actually restarted (`started_with_version` matches `version` again).
- **`ops.html`** gets a dedicated "Code freshness" stat card (fresh / `STALE since <started_at>`,
  with both version numbers) alongside its existing runtime-mode/documents/page-cache/snapshot cards.
- **New test** `engine/tests/test_version_staleness.py`: starts a real `ThreadingHTTPServer` +
  `viewer_app.Handler`, confirms a freshly-started process reports no mismatch against its own
  on-disk file, safely rewrites the real `VERSION =` line on disk (saved/restored in a `try`/`finally`
  so a mid-test crash can't leave the repo file mutated) and confirms the mismatch **is** now reported
  on both `/healthz` and `/api/ops`, confirms a second, genuinely fresh subprocess started against
  that same now-changed file reports **no** mismatch, and confirms 20 back-to-back `/healthz` calls
  stay fast (TTL cache, not a per-request file read).

**Verified:** `engine/tests/verify_all.py --snapshot` clean except `test_routes.py`'s pre-existing
`/api/ask` timeout (confirmed identical on unmodified `origin/main` via `git stash`, unrelated to
this change).

---

## [1.41.0] — 2026-08-31 — part.html no longer conflates a failed request with "part not found"
**VERSION → `1.41.0`.** Found during a readiness audit's completeness pass: `part.html`'s shared
`gj()` fetch helper collapsed two very different outcomes — a real transport/server failure, and a
genuine "nothing here" result — into the exact same falsy/`!j.ok` shape, so every one of its 15
`fetch()` call sites (the primary `/api/partsummary` card plus 14 lazy-loaded panels) rendered a
failure identically to an honest empty result. Worst cases: the primary card showed a flat "Nothing
found." on any network hiccup, and the two safety-relevant panels (cross-manual conflicts,
one-time-use/TTY fasteners) failed completely silently — a technician had no visible sign that a
conflict or a replace-only fastener could have gone unchecked, not merely absent.

- **`gj()` now returns `{ok,status,body}` instead of a bare `null`-or-parsed-body.** `ok` is true only
  for a 2xx response whose body actually parsed as JSON; every other outcome (offline/DNS failure, an
  HTTP error status such as the framework's 500 `{error,ref}` body, or an unparseable 2xx body) is
  `ok:false`. `gj()` still never rejects, so no call site's `.then()` chain shape changed — every site
  was updated to branch on `res.ok` first, with the existing success/empty logic moved onto `res.body`.
- **All 15 fetch sites now show a distinct, honest message for "couldn't load" vs. "nothing here":**
  the primary card ("Couldn't reach the server — check your connection and try again." vs. "Nothing
  found."), and every lazy panel gets its own `⚠ Couldn't load <thing> — try again.` (a small
  `failCard()` helper, reusing the `.alert.verd` amber style already defined in this file but never
  referenced until now) instead of staying silently blank. 7 panels that had **no** empty-state message
  at all before this pass (model, torque-sequence, serviceability, MAC, RPSTL, wiring, job-kit) got one
  added at the same time, since adding a failure branch without an empty branch would have made the two
  states indistinguishable again from the opposite direction.
- **The two safety-relevant panels get explicitly-worded failure copy**, matching the
  "do not treat this as..." pattern `dossier.html` already established for its own cautions panel:
  `⚠ Couldn't check for cross-manual conflicts — try again. Do not treat this as "no conflicts."` and
  `⚠ Couldn't check for one-time-use/TTY fasteners — try again. Do not treat this as "none flagged."`
- **The primary card's own empty-test was wrong in a second, independent way, caught live while
  verifying the fix**: `/api/partsummary` (`jobcards.py`) always sends `{ok:true}` for any query ≥2
  chars — it has no code path that legitimately returns `ok:false` — so the *old* `!j.ok` check was
  already dead for real no-match queries and almost always fired on a masked failure instead. The new
  empty-test judges the summary's own content (`nsn`/`item_name`/`parts`/`dims`/`procedures`/`torque`/
  `cautions`) — but an early version of that test also included `s.title`, which `_jobpack_data()`
  always sets to the raw query string as a bare fallback (`pkg={"title":q,...}`) even when nothing
  matched. That made the empty-test always true regardless of query, verified live with a nonsense
  query rendering as if it had found something. `s.title` was dropped from the test before this shipped
  — real regression, caught by hand-testing before merge, now also pinned by
  `test_uiux_fixes.py::parthtml_primary_emptytest_excludes_title`.
- **A second, adjacent correctness bug fixed alongside**: `#conflictcard` is shared by two lazy
  functions (`lazyValidate`'s data-integrity check, `lazyConflicts`' cross-manual conflicts) — one of
  them (`lazyConflicts`) used to write with `box.innerHTML=h`, which would silently wipe out whatever
  `lazyValidate` had already appended, including a new failure marker. Both now exclusively append via
  `insertAdjacentHTML('beforeend', …)`; verified live that a validate-failure message and a real
  conflicts result render together in the same card without either erasing the other.
- **Verified live**, not just read: real server, real corpus (`index/viewer.db`, ~39,700 documents) —
  a real part (`POWER UNIT DIESEL`) renders unchanged (conflicts, one-time-use, MAC, RPSTL, cautions,
  procedures, job-kit all populated correctly); a genuinely no-match query now shows "Nothing found."
  (previously would have, coincidentally, been right for the wrong reason before this fix, and wrong
  after the `s.title` regression before that was caught); and a forced fetch failure — both a true
  `fetch()` rejection (simulated offline) and a real HTTP 404 from the live server — was injected at
  all 15 call sites in browser (primary, conflicts, one-time-use, validate, MAC, wiring, commonality,
  RPSTL, cross-method, serviceability, torque-sequence, job-kit, notes, model, xref — see PR body for
  the full per-panel before/after copy) and each showed its own distinct "couldn't load" message,
  never the old empty-state text.
- **No existing real-browser/JS test harness for any UI page in this repo** — `test_uiux_fixes.py`'s
  established pattern (used for every prior `part.html` fix, e.g. `[1.14.0]`'s confidence-qualifier
  check) is static source-text assertions against the HTML file plus a `node --check` syntax sweep, not
  a driven browser. New coverage for this fix follows that same convention rather than introducing a
  new test style out of scope: it asserts `gj()`'s new resolve shape, that every one of the 15 call
  sites gained an `if(!res.ok)` branch, that the old dead checks (and the `s.title` regression) are
  actually gone rather than just supplemented, that both safety panels carry their distinct copy, and
  that the `#conflictcard` append-only invariant holds.

**Verified:** `engine/tests/verify_all.py --snapshot` clean; `test_uiux_fixes.py` (272/272, 22 new
checks); live server against the real corpus per above.

---

## [1.39.0] — 2026-09-01 — CRITICAL: embed.py build_index() could stamp a mixed real/hash-fallback index as pure sentence-transformers
**VERSION → `1.39.0`.** Found during adversarial verification of `[1.36.0]` (embed.py full-rebuild
prep) before the full-corpus rebuild it gates was launched. **Confirmed pre-existing, not introduced
by `[1.36.0]`**: the original unbatched `embed_text()` had the identical bare per-row fallback, and
the old `build_index()` also stamped the backend after the fact with no per-row correlation —
`[1.36.0]`'s batching just enlarged the blast radius of one failure event from 1 row to up to
`chunk_size` (default 5,000) rows, and made it a live concern given the full-corpus rebuild this fix
gates is about to actually run.

- **The bug.** `cur_backend = backend()` was computed once, before the chunk loop, and stamped into
  `embeddings.meta.json` unconditionally at the end regardless of what actually happened during each
  chunk. If `model.encode()` threw for any reason on a given chunk (bad input, transient OOM, etc.),
  `embed_text()`'s bare per-row `except Exception: vecs = hash-fallback` pattern (replicated per-chunk
  in `build_index()`'s batched loop) silently substituted hash vectors for that chunk — but the final
  meta stamp still said `"sentence-transformers"` for the whole index. `_index_is_stale()` trusted
  that stamp completely, so `search()` served a genuinely mixed real-vector/hash-vector array as a
  uniform, fresh, semantically-meaningful index — the exact `[1.32.0]` failure mode (real vectors
  compared against incompatible vectors → near-noise cosine scores silently trusted as a legitimate
  signal), just at row/chunk granularity inside one otherwise-valid build instead of across a whole
  rebuild, with zero warning or metadata trace.
- **The fix.** Every chunk whose `model.encode()` call actually raised is now recorded (shard index,
  row count, doc/page range, error) in `fallback_events`, persisted through
  `embeddings.progress.json` so the record survives a genuine interrupt+resume exactly like every
  other piece of build state (`[1.36.0]`'s own safety invariant). If any fallback events remain once
  the shard merge succeeds, `embeddings.meta.json` is deliberately **not** written (and any stale one
  left over from a prior clean build is removed) — reusing `_index_is_stale()`'s existing
  no-meta-stamp-means-stale branch rather than inventing new per-row staleness logic there, so an
  index this function itself won't vouch for is indistinguishable, on purpose, from a build that
  never finished. `embeddings.fallback.json` is written instead, naming exactly which rows are
  suspect, so an operator can decide whether to just re-run the build (transient fault) or
  investigate further (e.g. malformed `body_text`). A clean rebuild over the same `index_dir`
  restores normal trust and clears any stale fallback report. `BUILD-EMBEDDINGS.bat` now prints an
  explicit warning (pointing at `embeddings.fallback.json`) instead of a bare "embedded N pages"
  success line when this happens.
- **Directly verified, not just reasoned about**: a real `model.encode()` failure was injected mid-
  build (a stub model, not a mock of `build_index()` itself) — confirmed the meta stamp was withheld,
  `_index_is_stale()`/`search()` both refused the index end-to-end, the fallback report named exactly
  the right rows, and the on-disk `embeddings.npy` array genuinely contains hash-fallback vectors
  (unit-normalised) ONLY in the affected rows with real vectors everywhere else. Also verified the
  fallback record survives a genuine interrupt+resume across the affected chunk (real `_np.save`
  fault injection, same technique as `[1.36.0]`'s own interrupt test), and that a subsequent clean
  rebuild clears the stale fallback report and restores the meta stamp. See
  `engine/tests/test_embed_partial_fallback.py` (32 new checks).

**Verified:** `engine/tests/verify_all.py --snapshot`, `test_embed_partial_fallback.py` (32/32),
`test_embed_checkpoint.py` (34/34, no regressions from `[1.36.0]`), `test_embed_staleness.py` (9/9,
no regressions from `[1.32.0]`), `embed.py` self-test — all clean. Branched from `origin/main` at
`[1.36.0]`; rebased onto `[1.38.0]` once `[1.37.0]`/`[1.38.0]` merged ahead of it — a straightforward
doc-reconciliation rebase (no logic-file overlap with either), same pattern as this repo's prior
`docs/reconcile-changelog-*` branches.

---

## [1.38.0] — 2026-09-01 — `parts.cagec`/`parts.smr` cross-database correlation: 2 more dead columns filled
**VERSION → `1.38.0`.** Follow-through on `[1.33.0]`'s deferred item: a real design for `parts.cagec`/
`parts.smr` cross-database correlation was scoped but explicitly not started that session (~1 focused
day of implementation, given real data-quality landmines already investigated). Implemented, tested
against this repo's own real corpus, and shipped this session — 2 of the 5 dead columns Gap Sweep found
(`[1.31.0]`) are now genuinely live; `ref_nsn.superseded` (trivial, `[1.31.0]`) and these 2 leaves 2 of the
original 5 still open (`parts.uoc`, `ref_nsn.data_date`).

- **`correlate_parts_cagec(con)`** (`engine/viewer_ingest.py`) joins `index/rpstl.db`'s `parts_rows`
  sidecar (built by `RPSTL_SCAN`/`build_rpstl.py`) into the main `parts` table on the confirmed-reliable
  `(document_id, page, nsn)` key — both DBs share the same `documents.id` numbering — and filters every
  candidate CAGEC through `index/cage.json` (the real, ~12k-entry CAGE registry) before writing anything.
  A raw `CAGEC_RE` match is just "5 alphanumeric characters," so unfiltered candidates include real
  garbage that happens to fit the shape — confirmed directly against this repo's own `rpstl.db`: vehicle
  model numbers (`M35A3`), nomenclature words (`WINCH`, `SCREW`, `LIGHT`), RPSTL boilerplate (`WHERE`,
  `EXCEPT`). SMR is trusted only when that SAME candidate row's cagec passed the filter — SMR has no
  ground-truth validator of its own, so it rides on cagec's validation rather than being judged
  independently. A key with more than one DISTINCT valid cagec candidate is genuinely ambiguous and is
  skipped outright, never guessed at (49 of 4,768 real multi-candidate keys, confirmed). Idempotent,
  additive-only re-run contract: a row is only ever written when a pass finds a valid, unambiguous match
  for it; a key with no current candidate is left exactly as-is, never blanked — this column has never
  had any other writer anywhere in the codebase (0 of 227,908 real rows populated before this feature),
  so there is no "existing legitimate data" a re-run could ever clobber.
- **Wired as the new 8th and final ingest stage**, in both the `run` and `ocrall` CLI branches, after
  `_run_pagetrim_ocr_stage()` and before the final `stage="done"` write — deliberately full-corpus EVERY
  time, never scoped to `_TOUCHED_DOC_IDS` like the schematics/tables/rpstl stages beside it: unlike
  those, `extract_parts()` unconditionally `DELETE`s and rebuilds the ENTIRE `parts` table on every
  single ingest run, not just the touched documents' rows, so a `_TOUCHED_DOC_IDS`-scoped correlate pass
  here would have silently left every OTHER document's cagec/smr back at NULL the moment any ingest run
  touched just one unrelated document. New opt-out toggle `VIEWER_CAGEC_CORRELATE_SCAN` (`flags.py`
  registry, same `scan_toggle()` mechanism as the other 9). Also exposed standalone as
  `python viewer_ingest.py cagec [--db PATH]` — an idempotent backfill for a corpus that was ingested
  before this feature existed, mirroring the `parts`/`extract_parts()` subcommand's own contract; added
  to the CLI's `choices=[...]` list alongside it.
- **A real, production-breaking bug caught during verification, not shipped**: the first implementation
  batched its `UPDATE`s via `con.executemany(...)` INSIDE the same `for row in con.execute(SELECT...)`
  loop it was iterating — fine at small synthetic scale (1-2 rows never hits the 1,000-row batch flush),
  but reproduced immediately against this repo's real 227,908-row `parts` table:
  `sqlite3.OperationalError: database is locked`, since SQLite refuses to write a table a connection is
  still mid-read on. Would have crashed this stage on every real ingest run past this ship date (this
  corpus's `parts` table has never been under 1,000 rows). Fixed by materializing the SELECT via
  `.fetchall()` before writing anything — the same convention `extract_parts()` itself already uses for
  its own main query — closing the read before any write starts.
- **Real yield, measured against this repo's own corpus** (a random 4,000-row sample of the real
  227,908-row `parts` table, not the full corpus — see the test-file note below): **48.0%** written a
  validated cagec, matching the `[1.33.0]` scoping research's ~48.2% full-corpus estimate closely. Of the
  written rows, every single cagec value round-tripped as genuinely present in `index/cage.json`, and no
  known-garbage token (the `M35A3`/`WINCH`/etc. list above) ever reached a written column.
- **`engine/tests/test_cagec_smr_correlation.py`** (new, 38 checks) — two tiers: synthetic fixtures in
  full isolation (single valid match, garbage-candidate rejection, mixed valid+garbage candidates,
  genuine ambiguity, same-cagec-different-confidence agreement, SMR-gated-on-its-own-row's-cagec,
  idempotence, additive-only-never-blanks, toggle off, missing cage.json, missing rpstl.db, full-corpus-
  ignores-`_TOUCHED_DOC_IDS`, the standalone CLI backfill, the `flags` CLI listing) plus real-data checks
  that read (never write) this repo's actual `index/viewer.db`/`rpstl.db`/`cage.json` — locating them via
  a worktree-aware path resolver, since the real, gitignored `index/` doesn't exist inside a
  `.claude/worktrees/<id>` checkout, only under the main repo root. The real-data run operates on a
  RANDOM 4,000-row sample of `parts`, not the full 227,908 — measured directly during this work that
  per-row `UPDATE` cost on this dev host is dominated by real-time antivirus scanning of SQLite's small,
  frequent page writes (confirmed via `Get-MpComputerStatus`: real-time protection on, zero exclusions
  configured), making a full-corpus write pass here take 15+ minutes purely from AV overhead — dwarfing
  everything else in `verify_all.py --snapshot`. The candidate index (`rpstl.db`'s copy) is still read in
  full regardless; only the write side is sampled. Production DBs are opened read-only (`mode=ro`
  URIs) throughout except for a small trimmed copy built via `ATTACH ... AS src` + `CREATE TABLE ... AS
  SELECT` into a throwaway temp dir — the real production files are never opened for write by this suite.
- **A known caveat, not fixed here, flagged for whoever runs the first real backfill**: `index/rpstl.db`'s
  file mtime (2026-07-08) is ~7 weeks older than `index/viewer.db`'s (2026-08-30) on this deployment.
  That gap alone doesn't prove staleness (different filters produce different document-count denominators
  between the two DBs' extraction passes), but it's worth confirming `RPSTL_SCAN` has actually been
  running during recent ingests, or running a fresh `python build_rpstl.py`, before trusting the first
  `python viewer_ingest.py cagec` backfill's yield as representative of the CURRENT corpus rather than a
  July snapshot of it.
- **Real downstream consumers, previously inert, now live**: `engine/figureparts.py`'s `parts_on()`
  (feeds `jobcard.py`'s `build_pdf()`, which prints literal `"CAGE <code>"`/`"SMR <code>"` lines on the
  mechanic-facing job-card PDF), `engine/partlocate.py`'s `locate()`, `engine/features/parts_feature.py`'s
  `part_differences()` (the CAGEC/SMR discriminator logic in the look-alike-parts feature), and
  `engine/jobpack.py`'s JSON export — all already selected these columns; none needed code changes, only
  real data to select.
- **Independently adversarially verified before merge** (own scripts, disposable read-only-sourced DB
  copies, not the PR's own test harness): 0 incorrect cagec/smr writes found across ~5,300 independently
  audited real writes (two separate real-data samples, exhaustively checked, not spot-checked); a
  targeted attack rebuilding the candidate index from the FULL unsampled `rpstl.db` found 49 genuinely
  ambiguous real keys, all 49 correctly refused (0 written) when run directly; idempotency confirmed via
  two full runs against a disposable copy (0 drift) plus a deliberately hand-corrupted row correctly
  recomputed back to the right value on a third run — clarifying the real contract is "recompute and
  correct when a candidate exists," not "never touch a populated row." One non-blocking code-quality
  note: the correlation stage's write loop has no try/except, unlike its sibling ingest stages — but
  matches `extract_parts()`'s own existing precedent in the same file, not a new regression, flagged for
  awareness only.

**Verified:** `engine/tests/verify_all.py --snapshot`: 57/57, ALL GREEN, independently re-run by the
verifying agent with the identical result.

---

## [1.37.0] — 2026-08-31 — `/api/ingest_scan` wired into the UI, as a separate honest affordance
**VERSION → `1.37.0`.** Resolves the open item `[1.33.0]` deliberately left on the table: `/api/ingest_scan`
(broader file-type coverage + hash/filename dedup) now has a UI entry point on `engine/ui/ingest.html` —
but not by conflating it with the existing Preview button, which is exactly the risk `[1.33.0]` flagged.

- Added a secondary **"Broader file scan"** link below the existing folder-path bar, next to Preview —
  its own `#broaderOut` panel, its own `broaderScan()` fetch, never written into `#out` (Preview's panel),
  so the two counts can never visually merge or silently overwrite one another.
- The panel's copy is deliberately honest about what it does and doesn't cover, matching the gap this
  session's research pass confirmed against the real code (`ingestpipe.SUPPORTED` vs. what
  `viewer_ingest.py`'s `crawl()`/`classify_ext()`/`index_other()` actually extracts content from):
  - States plainly what it adds over Preview: `.txt`/`.html`/`.htm`/`.xml`/`.csv`/`.md`/`.tiff`/`.tif`/
    `.png`/`.jpg`/`.jpeg`, in addition to Preview's PDF-only coverage (`ingestpipe.SUPPORTED`'s real
    contents — **not** `.docx`/`.xlsx`/`.pptx`/`.rtf`/`.bmp`/`.gif`, which `office.py`/`_IMAGE_EXTS`
    extract in the real ingest job but which this scan's own file-discovery step doesn't look for at
    all — an earlier draft of this entry and the shipped copy briefly claimed the opposite; caught by
    adversarial verification before merge, confirmed live against a running server, and corrected here).
  - States plainly what's still NOT covered: legacy `.doc`/`.xls`/`.ppt` and `.svg` are discovered (a
    `documents` row is created) but never content-extracted by the real ingest job — same degrade state
    on both scans, not fixed by this UI change.
  - Separately calls out that `.xml`/`.csv`/`.md` are themselves a partial win: `ingest_scan` counts and
    dedupes them, but the real ingest job has **no extraction path for them at all** — discovered, zero
    content, exactly like the `.doc`/`.xls`/`.ppt`/`.svg` case above, despite `ingestpipe.SUPPORTED`
    nominally listing them as "supported."
  - States plainly that this scan's dedup method (content hash OR filename) differs from Preview's
    (exact path match only), so the two "new to add" counts can legitimately disagree — explained instead
    of left as an unexplained discrepancy.
  - The new-to-add count, when present, offers the same `Index N new document(s) now` → `startRun()` flow
    Preview's own button already uses — one shared `/api/ingest` job, either scan can point it at the folder.
- **Parity check, not a fix**: confirmed `/api/ingest_scan` (a `POST` route) does NOT need its own
  `_exposed_read_guard()` call the way `/api/ingest_preview`/`/api/ingest_status` (both `GET`) do —
  `do_POST` already requires the shared `X-Viewer-Token` for every POST route when the server is
  network-exposed, before the handler runs at all. An earlier research pass flagged the missing guard
  as a possible gap; traced against `viewer_app.py`'s `do_POST` and confirmed it isn't one. Left a
  code comment on `r_ingest_scan` (`engine/features/routes/ingest.py`) recording this so it isn't
  re-flagged and "fixed" incorrectly by a future pass.
- Verified live, twice: once at initial ship (`engine/tests/test_ingest_routes.py`'s real e2e coverage
  of `POST /api/ingest_scan` re-run clean; the extension gap confirmed live with a direct
  `ingestpipe.scan_folder()` call against a real temp folder), and again after the copy correction above
  — a standalone script started the real server, built a temp folder with one file per extension across
  both the true-supported and true-unsupported sets, and POSTed to `/api/ingest_scan`: exactly the 12
  `ingestpipe.SUPPORTED` extensions came back, all 6 previously-misclaimed extensions correctly absent.

**Verified:** `engine/tests/verify_all.py --snapshot`: 56/56, ALL GREEN (including `test_ingest_routes.py`
clean, no flake this run, and the safeguard vault check, 723/723 OK).

---

## [1.36.0] — 2026-08-31 — embed.py full-rebuild prep: configurable cap, batched encoding, resumable checkpointing
**VERSION → `1.36.0`.** The source-code change `[1.32.0]`'s research pass flagged as the prerequisite
for a real full-corpus semantic-search rebuild (that pass found the 200,000-row cap hardcoded, covering
only ~11.9% of this deployment's real 1,682,054 eligible pages) — implemented and tested this session.
**No full-corpus rebuild was run as part of this change**; that's an explicit ~9–12 hour unattended
commitment, launched separately, under direct human supervision. This PR is code + test coverage only.

- **Configurable row cap, backward compatible.** `embed.build_index()`'s `limit` parameter defaults to
  `None`, which now resolves to `VIEWER_EMBED_LIMIT` (env var, default `200000`) — following this
  codebase's existing `os.environ.get("VIEWER_X", default)` convention (`VIEWER_DB`,
  `VIEWER_OCR_PAGE_TIMEOUT`, etc). `BUILD-EMBEDDINGS.bat` (the sole existing caller) passes no `limit`
  and sets no env var, so its behavior is byte-identical to before. A full run sets
  `VIEWER_EMBED_LIMIT` above the real eligible-row count before running the `.bat`, which now prints
  the effective cap it's about to use.
- **Batched encoding.** Rows are processed in `chunk_size`-row chunks (default 5,000); each chunk's
  texts are handed to the sentence-transformers model as one `model.encode(list, batch_size=...)` call
  instead of one `embed_text()` call per row. Measured on this host, real corpus text, real model: **~40
  pages/sec unbatched vs. ~53–54 pages/sec batched — a genuine ~1.3x throughput improvement**, re-measured
  fresh for this change (median of 3 alternating trials each; matches the `[1.32.0]` research pass's
  standalone benchmark almost exactly). The hash-fallback backend (pure per-text CRC32, no model forward
  pass) sees no such benefit and stays a plain per-text loop, just inside the same chunked structure.
- **Resumable checkpointing.** The query now carries `ORDER BY id` (`pages.id`, the real `INTEGER PRIMARY
  KEY`), so chunk boundaries are stable and repeatable. Each completed chunk lands in its own shard files
  (`index/_embed_build/shard_NNNNNN.npy`/`.tsv`) plus a progress marker
  (`index/embeddings.progress.json`) recording `last_id` and enough of the call's own parameters
  (db_path/limit/min_chars/backend/chunk_size) to tell a genuinely-resumable prior run apart from a
  stale/incompatible one — a mismatch on any of those is treated as no-progress-at-all and the shard dir
  is discarded before starting clean. Shards are merged into the final `embeddings.npy`/
  `embeddings_ids.tsv` — atomically, write-to-temp + `os.replace()` — only once every row up to `limit`
  (or the real end of the table) has been processed with **no** error.
- **Safety invariant, enforced structurally, not by new logic in the staleness check:**
  `embeddings.meta.json` — the sole thing `_index_is_stale()` trusts as proof an index is complete and
  fresh (see `[1.32.0]`) — is written exactly once, immediately after the shard merge succeeds, and
  nowhere else in `build_index()`. A process killed at any point before that (mid-chunk, mid-merge, or
  between merge and the stamp) never touches `embeddings.meta.json`, so `_index_is_stale()`'s existing
  no-meta-stamp branch keeps doing exactly what it already did for `[1.32.0]` — refuse to serve a build
  that never finished. **Directly verified, not just reasoned about**: a real fault was injected into the
  build loop mid-run (not a mock of `build_index()` itself), confirmed the meta stamp was absent and
  `_index_is_stale()` reported `True`, then the identical call was resumed and its final output compared
  byte-for-byte (same ids, same vectors, `np.allclose`) against an uninterrupted run over the same sample
  — see `engine/tests/test_embed_checkpoint.py`.
- **Validation scope, deliberately limited per this session's instructions**: all testing above ran
  against small synthetic samples (tens to a few hundred rows) plus one 300-row pass against the real
  `index/viewer.db` (read-only) to confirm real-schema compatibility — never the full ~1.68M-row corpus.
  The real, full rebuild stays a separate, human-supervised action.

**Verified:** `engine/tests/verify_all.py --snapshot`: 57/57, ALL GREEN (including
`test_embed_checkpoint.py`'s 34 new checks and the existing `test_embed_staleness.py`'s 9, both clean). A
second, non-snapshot run reproduced the repo's one known pre-existing flake
(`test_ingest_routes.py`'s real-subprocess-e2e test) in isolation — the only failure, not introduced by
this change. `rps_lint.py` clean; safeguard snapshot clean.

---

## [1.33.0] — 2026-08-30 — 2 more orphaned routes wired: blank DA-2404/2407 forms, one click away
**VERSION → `1.33.0`.** A follow-up to `[1.31.0]`'s orphan-route sweep, picking up 2 of the 3 remaining
candidates a research pass identified this session (the third, `/api/chapter_jump`, was confirmed
genuinely not worth wiring — see below; the fourth candidate area, `/api/ingest_scan`, needs a product
decision and stays open on purpose).

- **`GET /api/form_2404`** (blank DA-2404/5988-E PMCS deficiency worksheet) — a real, tested route
  (`engine/features/routes/ingest.py`) with zero UI entry point; its `POST` sibling that fills a worksheet
  from logged faults was already reachable programmatically but the blank print-on-demand form had no
  button anywhere. Added as an always-enabled "🖨 Print blank PMCS worksheet (DA 2404)" link on
  `pmcs.html`, next to the existing "Find PMCS" search — deliberately not gated on search results, since a
  blank worksheet needs no prior lookup.
- **`GET /api/form_2407`** (blank DA-2407/5990-E maintenance-request worksheet) — same gap, same fix: an
  always-enabled "🖨 Print blank maintenance request (DA 2407)" link on `jobcard.html`, placed right after
  the existing gated "🖨 Print parts-request sheet" button (`[1.31.0]`'s `partspdf.py` wiring) but
  deliberately *without* that button's disabled/opacity gating — the blank form doesn't depend on a
  search having resolved anything.
- Both links verified live before shipping: real `curl` requests against both routes return genuine
  single-page PDFs (`file` confirms valid PDF headers), not error bodies.
- **`/api/chapter_jump` confirmed NOT worth wiring in** (the research pass's third candidate) —
  `index.html`'s `openViewer()` already calls the richer `/api/chapters`, which `chapter_jump` is a thin
  subset of; `renderChapterBanner()` needs the fuller response (`ranges`, both `operator_page`/
  `mechanic_page`) regardless, so wiring in `chapter_jump` would only add a second round-trip returning
  data already in hand — zero benefit, correctly left alone.
- **`/api/ingest_scan` stays open, on purpose** — a real, distinct capability (broader file-type coverage
  plus hash/filename dedup vs. the existing PDF-only exact-path `/api/ingest_preview`) but its own
  supported-extension list (`ingestpipe.SUPPORTED`) is narrower than what the real ingest job actually
  processes (missing `.docx`/`.xlsx`/`.pptx`/`.rtf`/`.bmp`/`.gif` — confirmed against `viewer_ingest.py`'s
  `_IMAGE_EXTS`/`_DOCX_EXTS`/etc.), so a UI surfacing it as a trustworthy pre-check would overclaim
  completeness, and it risks showing two legitimately-disagreeing "how many new files" counts next to the
  existing Preview button with no explanation. Needs a product decision, not a unilateral UI addition.

---

## [1.32.0] — 2026-08-30 — CRITICAL: stale embeddings index was silently reclassified as fresh, feeding near-noise semantic scores into the primary search endpoint
**VERSION → `1.32.0`.** A real, live production bug — introduced by this same session's own
`[1.31.0]` work, caught and fixed within the same day, before it reached any real user. Documented in
full because the failure mode (a stale-detection check that only ever compared the *current* backend
against itself, never against what actually built the data it's guarding) is a real, generally-useful
lesson, not just a one-off.

- **What happened:** while researching semantic search's feasibility (a `[1.31.0]` follow-up), a real
  `pip install sentence-transformers` succeeded on this host. The moment it did, `embed.backend()`
  started returning `"sentence-transformers"` instead of `"hash-fallback"` — and
  `embed._index_is_stale()`'s no-meta-stamp branch, `return backend() == "hash-fallback"`, silently
  flipped from `True` to `False`. This repo's real `index/embeddings.npy` predates version tracking
  entirely (no `embeddings.meta.json`) and was built under the old hash-bucket math, since
  sentence-transformers had never been installed here before — so it got reclassified as "not stale"
  and started being served through `hybrid_search()`'s RRF fusion on **`/api/search_hybrid`, the
  primary search endpoint as of `[1.31.0]`**. Confirmed live before fixing: real hash-bucket vectors
  compared against real sentence-transformer query embeddings produced cosine scores of 0.18–0.19 —
  near-noise, nowhere close to the 0.7+ a genuine semantic match produces — which `fuse()` was treating
  as a legitimate corroborating signal and blending into live search results.
- **The fix:** `_index_is_stale()` now requires a meta stamp proving the index was built by the *same*
  backend that is *currently* active — not just "some backend happened to be active when checked."
  Both directions of mismatch (hash-fallback-built-but-now-running-real-model, and the reverse) are
  caught; the no-meta-stamp case is now unconditionally stale regardless of which backend happens to be
  installed. Verified live end-to-end: `/api/search_hybrid?q=alternator` now correctly reports
  `"signals":{"semantic":0}` again (the honest, safe state) instead of silently blending in the stale
  vectors.
- **A related coverage gap, also fixed:** `embed.py`'s own self-test had gated its entire
  staleness-check block behind `if backend() == "hash-fallback":` — meaning the test that should have
  caught this exact bug silently stopped running the moment sentence-transformers became available,
  which is precisely the environment change that triggered it. Now runs unconditionally, with a new
  assertion specifically covering the "meta backend ≠ active backend" case.
- **Two more tests fixed for the same underlying reason** (an environment assumption baked into a test
  became false once `transformers`/`torch` — shared dependencies of `sentence-transformers` — were
  installed): `test_routes.py`'s `/api/pageqa` content check hardcoded `available:false`; now computes
  the expected value from `pageqa.available()` directly. `test_pageqa.py`'s "no backend" subprocess
  test relied on the ambient environment never having `transformers`/`torch`; now forces a genuinely
  nonexistent `VIEWER_VLM` module name, making the test deterministic regardless of what happens to be
  installed.

**Verified:** `engine/tests/verify_all.py --snapshot`: 55/56 (only the pre-existing
`test_ingest_routes.py` real-subprocess-e2e flake), safeguard `726/726 OK, 0 damaged`, `rps_lint.py`
clean. New coverage: `test_embed_staleness.py` (9 checks, including a direct reproduction of the live
bug and an end-to-end `embed.search()` check). Every claim in this entry — the live bug, the fix, and
both dependent test fixes — verified by direct reproduction, not assumed from a research pass's
self-report.

---

## [1.31.0] — 2026-08-30 — Gap Sweep: RapidOCR installed, /api/search_hybrid is now primary search, one dead column filled, 3 more orphans wired, real "search" analytics
**VERSION → `1.31.0`.** All 5 priority items from a Gap Sweep audit (a 5-agent parallel research pass
answering "what's going on with OCR confidence, and what other gaps exist" — itself a follow-up to
`[1.29.0]`/`[1.30.0]`'s Build Roadmap). Two items shipped narrower or reshaped from how the Sweep's own
priority list framed them, in both cases because a second, implementation-time research pass found the
literal framing would have been unsafe or premature — documented below, not glossed over.

- **RapidOCR installed and verified live** (`rapidocr-onnxruntime` 1.2.3) — `ocr_one()`'s confidence-
  scoring write path was already correct; this machine's OCR engine was the actual gap (Tesseract
  fallback captures no confidence at all). Confirmed via `_have_rapid()` returning `True` post-install,
  independently re-verified in this session's own process (not just the installing agent's self-report).
  Documented in `requirements.txt`'s OPTIONAL block and `INSTALL.bat`. The historical 53,391-page OCR
  backlog still needs a real re-OCR pass to backfill — there was never a confidence score computed for
  those pages to retroactively recover; only *future* OCR runs get it automatically now.
- **`/api/search_hybrid` is now the home search box's primary endpoint** — its own real, self-tested RRF
  fusion had zero UI callers. Unsafe to switch to as originally framed: research found the route silently
  dropped `side`/`match_any`/`use_fuzzy`/`mode`/`tm:`/`vehicle:`/`nsn:` operators entirely, which would
  have broken the SIDE toggle, the offline `did_you_mean`, and `mode="text"` outright. Fixed first —
  `hybrid.hybrid_search()` gained the missing parameters and now threads them through to
  `search_feature.search()` exactly like `/api/search` already does; `r_search_hybrid` gained the
  identical side-filter over-fetch, operator parsing, `did_you_mean` fallback, and LRU cache `/api/search`
  already had. Verified extensively before switching: 100% of ~20 diverse test queries return the
  identical result *count*; where top-ranked results differ, it's either the route's own glossary/
  acronym-aware ranking genuinely surfacing better matches (confirmed live: a "CTIS" query now ranks
  pages mentioning "Central Tire Inflation System" too) or a benign tie-break artifact of the route's own
  pre-existing 2×-candidate-pool overfetch — never a result-count or quality loss. Semantic search is
  still non-functional in this deployment (no embeddings index), so results additionally degrade to
  exactly the keyword rows the UI already knew how to render; once semantic search ships, richer fused
  results reach the search box with no further UI change needed.
- **The one genuinely fixable dead column** — of the 5 the Sweep found (`parts.cagec`/`smr`/`uoc`,
  `ref_nsn.data_date`/`superseded`), a second research pass found only `ref_nsn.superseded` at the FLIS
  ingest site was a trivial fix: its value (`subs`, the cancellation/cross-reference string) was already
  parsed, just never bound to the column `index.html`'s own cart-panel enrichment has been ready to
  render since migration `0008`. Fixed additively (bound alongside the pre-existing `substitutes` write,
  not replacing it). **The other 4 stay open, correctly** — `cagec`/`smr` are extracted by a real parser
  (`rpstl_feature.py`) that feeds a *different* database file (`rpstl.db`'s `parts_rows`, not the main
  `parts` table), requiring real cross-database integration, not a column-list edit; `uoc` and
  `data_date` have no extraction logic anywhere in the codebase at all. Forcing a rushed fix for any of
  these four would have meant either untested new parsing logic or a real ingest-pipeline redesign —
  scoped out for dedicated follow-up work instead.
- **3 more orphaned routes wired in.** `rpstl.py`'s base lookup (distinct from the already-wired
  `/api/rpstl_review`/`/api/rpstl_override` admin queues, a substring-collision false match caught before
  shipping) — a new card on `part.html`, same lazy pattern as `[1.30.0]`'s other additions.
  `partspdf.py`'s scannable-barcode parts-request PDF — a new "🖨 Print parts-request sheet" button on
  `jobcard.html`, gated on `jobcard_preview`'s own real parts-found count. `handover.py`'s shift-handover
  digest — a genuinely new page, `engine/ui/handover.html` at `/handover`, since none of the 3 candidate
  existing pages fit (confirmed by reading each: `status.html`/`ops.html` are admin/corpus-health tools,
  `jobcard.html` is single-task-scoped, none carry a shop-wide "what's pending since last shift" view).
  Added to `index.html`'s Tools menu and the command palette. `handover.py`'s own response has **no
  `ok` key at all** (`build_digest()`'s dict is sent verbatim) — a real gotcha caught before writing the
  page's fetch guard.
- **A real `"search"` analytics event, finally.** `"search"` has been a declared-valid kind in
  `analytics.py`'s own `_VALID` set since it was first written — `summary()`'s `top_searches` panel has
  always called `top(index_dir, "search", 8)` — but nothing anywhere ever logged one (confirmed by
  grepping every `analytics.log(` call site in the repo before this fix: only `"gap"` and `"click"`
  existed). Now logged once per real (non-cached) search, in both `/api/search` and `/api/search_hybrid`
  so switching the primary endpoint above doesn't silently blank the panel again. Measured cost: ~0.08ms/
  call, ~0.05% of a typical search's own latency — confirmed not a regression risk before shipping, not
  assumed. `analytics.py`'s own self-test now shows real `top_searches` data for the first time.

**Verified:** `engine/tests/verify_all.py --snapshot`: 54/55 (only the pre-existing
`test_ingest_routes.py` real-subprocess-e2e flake), safeguard `725/725 OK, 0 damaged`, `rps_lint.py`
clean. New coverage: `test_search_analytics.py` (11 checks), `test_ref_nsn_superseded.py` (10 checks,
including the `ON CONFLICT DO UPDATE` path), `test_hybrid_search_parity.py` (13 checks, proving every
parameter actually reaches `core.search()` via a recording fake, not just "doesn't crash"). Every claim
in this entry checked live against the real running app, the real corpus, or (for states this specific
deployment doesn't organically exercise — `crossmethod.py`'s "confirmed" status, a populated
`ref_nsn.superseded`) a synthetic response/fixture proven to exercise the real code path.

---

## [1.30.0] — 2026-08-30 — Build Roadmap "Next" tier: 5 orphaned modules wired, related-parts card, search-result flags, symptom routing, base.css linked
**VERSION → `1.30.0`.** All 6 "Next" items from the Build Roadmap — grounded in real research (4
parallel exploration passes reading the actual modules/routes/UI patterns before writing any code, not
the roadmap's own summary text) and, per the same standing discipline as every other batch this
session, independently re-verified live before shipping. One item shipped materially different from
the roadmap's own suggested shape, in both cases because direct measurement said so — documented below.

- **5 real, self-tested, route-registered modules that had zero UI callers for 16–20 versions are now
  wired in**, each using the exact "fetch → check ok → inject" lazy-card pattern `part.html` already
  runs 8 times: `crossmethod.py` (`/api/crossmethod`, the positive counterpart to the conflict card —
  only surfaces independently-*confirmed* values, never re-showing what the conflict card already
  flags), `macchart.py` (`/api/mac` — not `/api/macchart`, a real gotcha caught before shipping),
  `harnesstrace.py`+`pinouts.py` (`/api/harnesstrace` — its own response already carries `pinouts.py`'s
  full `connectors[]` shape plus continuity `nets[]` on top, so one call covers both modules), and
  `commonality.py` — **placement corrected from the roadmap's own suggestion**: the roadmap cited
  `readiness.html` (its nav tooltip promises "fleet shared-parts, by vehicle"), but `commonality.py`'s
  real API does an *exact* NSN/name/part-number lookup (confirmed live: querying it with a vehicle name
  returns `commonality:"unknown"` every time) while `readiness.html` is vehicle-scoped end to end — a
  genuine shape mismatch, not a nitpick. Shipped on `part.html` instead, where it actually fits; the
  tooltip's broader vehicle-aggregated view remains a real, separate, unbuilt idea. `tmrev.py` went to
  `procedure.html` as a currency banner (`src.tm` already in scope by render time, confirmed) — with its
  own real gotcha: `/api/tmrev`'s response has **no `ok` field at all** (`currency()` returns
  `{tm,current,superseded,n}` directly), unlike every other route on that page.
- **A "Related parts" card on `part.html` AND `dossier.html`.** `xref.py`'s `/api/xref` already returns
  exactly `assemblies[]`/`siblings[]`/`see_also[]` — its own docstring already said it was meant to
  power "a related panel on the dossier," but neither page ever called it; only the standalone
  `/related` page did. Rendering logic mirrors `related.html`'s own three sections.
- **OCR-confidence and cross-manual-conflict signals now reach the search results list**, not just
  `part.html`'s dedicated cards. `p.ocr_confidence` has existed on `pages` since migration 0009 and
  `corpus.py` already selected it, but `search_feature.py`'s own `search()` — what `/api/search`
  actually runs — never did, in either of its two real row-building SELECTs; fixed, with new coverage
  in `test_search_ocr_confidence.py` (7 checks) proving the value round-trips, not just "search()
  doesn't crash." The conflict flag **shipped differently from how it was scoped**: `conflicts.py`'s
  `check_query()` measured 200–227ms on common single-word queries on this host (confirmed directly),
  which would have roughly doubled `/api/search`'s own latency if baked into its response. Instead it
  fires as an independent, non-blocking client-side call — exactly like the existing part-match/
  measure-match cards already do — and tags already-rendered rows via new `data-doc`/`data-page`
  attributes rather than assuming DOM order matches a possibly-filtered list. (Also found and disclosed
  honestly rather than silently glossed over: this real corpus has **zero** populated `ocr_confidence`
  values across 53,391 OCR'd pages, confirmed via direct DB query — the SELECT fix and the badge
  rendering are both verified correct via synthetic data, but have zero visible effect on this specific
  deployment today until whatever pipeline stage would populate that column actually runs.)
- **Symptom and "how do I" queries now get a suggestion card**, same additive pattern as the existing
  torque/measurement-shaped and part-number-shaped detectors (confirmed before writing this: no
  query-shape classifier of any kind existed anywhere else in the codebase). Symptom-shaped queries
  ("won't start," "leaking," "grinding," 20+ patterns) fetch `/api/faulttree` inline (112–206ms,
  measured, acceptable) and suggest `/troubleshoot`. Question-shaped queries ("how do I…", "how to…",
  trailing "?") **do not** auto-fetch `/api/ask` — measured at 900–1855ms on 3 real questions on this
  host, unacceptable as a silent per-search background cost — instead showing an instant static link;
  the expensive extractive answer only runs if the mechanic actually clicks through.
- **`index.html` finally loads `/base.css`** — the root cause of `[1.29.0]`'s `--acc`/`--grn` bug: this
  page hand-duplicated shared chrome instead of loading the real file, and the duplicate had already
  drifted out of sync once before that audit caught it again. A real visual-diff pass, not a blind
  strip-and-link: the fully-redundant `:root` token block and `[hidden]` guard are gone (base.css now
  supplies both identically); the kiosk-mode/touch-target rules **stay**, deliberately, because this
  page's buttons use its own local `a.ghost` class while base.css's shared selector list targets
  `a.btn` (confirmed: `.ghost` is used 69× here and nowhere else but a stray 3× in `threed.html`; `.btn`
  is the real app-wide convention) — merging them would have either broken every `.ghost` button's
  kiosk sizing or required an app-wide base.css selector change touching all 46 other pages for one
  page's naming quirk. Found and fixed in the same pass: this page's own kiosk-mode rule was missing a
  checkbox/radio min-width carve-out `base.css` already fixed once (confirmed live via
  `getComputedStyle()`, before/after) — this page has no checkbox today so the bug was latent, not
  visibly tripped, but the very next one added here would have inherited a known, already-fixed defect.
  Paired with a new **interactive-control border token**: `--line` (the app-wide divider/border token)
  measured 1.05–1.45:1 against every real background — fine as a decorative divider, badly under the
  3:1 UI-component floor as the actual visible boundary of every `<input>`/`<select>`/`<textarea>` on
  this page. New `--line-ctl:#6c7690` (3.32–4.08:1, clears the floor everywhere) now carries every real
  control border on this page; `--line` is untouched for its existing decorative uses. Locked in by a
  new automated guard in `engine/verify_ui.py` (matches `[1.29.0]`'s WCAG-text-contrast guard pattern).

**Verified:** `engine/tests/verify_all.py --snapshot`: 50/51 (only the pre-existing
`test_ingest_routes.py` real-subprocess-e2e flake), safeguard `721/721 OK, 0 damaged`, `rps_lint.py`
clean. New coverage: `test_search_ocr_confidence.py` (7 checks), 2 new checks in `verify_ui.py`'s WCAG
guard. Every module/card/route claim in this entry checked live against the real running app and the
real corpus (`curl`, direct SQLite queries, and in-browser `fetch()`/`getComputedStyle()`/synthetic-
response injection for the states this specific corpus doesn't happen to exercise organically — e.g.
`crossmethod.py`'s "confirmed" status, which this corpus has zero real examples of for any common
query tried) — never trusted from the roadmap's own summary text.

---

## [1.29.0] — 2026-08-30 — Build Roadmap "Now" tier: dead focus outline, doubled fuzzy scans, missing modal traps/alt text/ARIA, 3 real WCAG failures
**VERSION → `1.29.0`.** All 6 "Now" items from the Build Roadmap (the companion to the production-
readiness dossier, scoped by a second research pass with real benchmarks and a real WCAG audit run on
this host) — every fix independently re-verified live against the real running app before shipping,
not trusted from the roadmap's own claims.

- **Keyboard focus was silently invisible on the home page — and several accent colors were dropping
  with it.** `engine/ui/index.html` duplicates its own `:root` token block instead of loading
  `base.css` (a deliberate legacy-tier tradeoff, not new), but that duplicate never defined `--acc` —
  only `--accent`, its own separate name for the identical blue. The page's `:focus-visible` rule (and
  several hover/pinned/card-accent rules) reference `var(--acc)` with no fallback, so every one of them
  was silently invalid. Confirmed live via `getComputedStyle()` before fixing, same after: `--acc` now
  defined alongside `--accent`.
- **The exact same bug, worse: `--grn`/`--amb`/`--red`/`--teal`/`--pur` were never defined on the home
  page at all.** Confirmed live: `var(--grn)`/`var(--teal)`/`var(--amb)` were each silently resolving to
  the inherited body text color, not amber/green/teal — the operator/mechanic side-of-house badges, the
  "Saved" correction confirmations, and the chapter-count status text were rendering in plain white, not
  the color their own markup asked for. Restored the full `base.css` token set into `index.html`'s copy.
- **3 real WCAG AA contrast failures, now measured and fixed, not spot-checked.** Once the tokens above
  were restored to their true values, three TEXT usages still measured below the 4.5:1 AA floor against
  their real backgrounds (computed directly from the app's own hex values, then re-confirmed live via
  `getComputedStyle()` + the same contrast formula in-browser): `--red` as the barcode-vs-OCR NSN
  mismatch warning text is `4.02:1` against `--panel2`; `--grn` as the part-match "Saved" confirmation
  is `2.98:1` against `--panel2`; `--grn` as the side-of-house "operator" badge / chapter-count status is
  `3.36:1` against `--panel`. Fix: two new lightened, text-only siblings — `--grn-tx:#4fae7a` (5.49:1 /
  6.18:1 against panel2/panel) and `--red-tx:#ec7a74` (5.44:1 against panel2) — added to both
  `base.css` and `index.html`'s own copy; the original `--grn`/`--red` are untouched and still correct
  for every existing border/background use (which only needs the lower 3:1 non-text floor). New
  regression guard in `engine/verify_ui.py` computes these exact ratios from the live CSS on every run,
  so a future hex change that breaks AA again fails the build instead of shipping silently.
- **A fuzzy search query was scanning the vocabulary for the same word 2–3 times.** `fuzzy_terms()` is a
  real scan against `pages_vocab` (5–49ms measured per word on the live corpus, not free) —
  `search_feature.py`'s `build_match()` (via `_alts()`) and `_token_alts()` each called it fresh on the
  identical tokens within one `search()` request, unconditionally doubling (sometimes tripling, via the
  nomenclature-widening variant pass) the cost of every fuzzy query for zero behavior difference. Fixed
  with a request-scoped `fuzzy_cache` dict, created once per `search()` call and threaded through every
  `build_match()`/`_alts()`/`_token_alts()` call in that request — `fuzzy_cache=None` (the default for
  any caller that doesn't opt in) preserves the exact old always-fresh behavior, so this is purely
  additive. `core_pillars.py`'s own independent, never-imported-by-production mirror of this code is
  deliberately untouched. New `engine/tests/test_search_fuzzy_cache.py` (8 checks) proves the mechanism
  directly — counting real calls to the underlying scan, not just "search() doesn't crash" — first
  showing the old pattern really does double-count, then showing the new pattern doesn't.
- **The home page's 5 real modals had `aria-modal="true"` and no actual focus trap.** A keyboard or
  screen-reader user tabbing through `#sidegate`/`#pnreview`/`#overlay`/`#setgate`/`#tsgate` could tab
  straight out into the page behind the dialog. New shared `VW.trapFocus()` in `shared.js`, modeled on
  `palette.js`'s own command-palette Tab-trap (the only correct implementation of this in the codebase
  before now) — generalized via a `MutationObserver` on each modal's own `style` attribute (these 5 are
  opened/closed from many scattered call sites, not one owned open()/close() pair, so this reacts to the
  `none`↔`flex` transition itself rather than requiring every call site to change). Handles Tab-cycle
  containment, Escape-to-close, and focus-restore-on-close. Verified live for all 5: auto-focus on open,
  Shift+Tab from the first element correctly wraps to the last, Escape correctly closes.
- **The 3 primary viewer `<img>` tags had no `alt` text.** The main page-render image (`loadPage()`),
  the part-match thumbnail (`renderPartMatch()`), and the part-drawer figure crop (`showFig()`) now
  carry real, content-derived `alt` text (page number + document title/TM number; part nomenclature;
  "Figure crop for {name}") instead of nothing.
- **ARIA labels added to the 10 highest-traffic unlabeled controls.** 43 of 45 UI pages carried zero
  ARIA of their own. Fixed the home page's search box plus every core tool's own search box
  (`procedure`/`dossier`/`part`/`stepflow`/`torque`/`packet`/`jobcard`/`locate`.html) and
  `collections.html`'s 4-field new-collection form (name/search-terms/vehicle/manual-type) — each a
  content-specific `aria-label`, not a generic "search" restatement.

**Verified:** `engine/tests/verify_all.py --snapshot`: 49/51 checks (the pre-existing `test_ingest_routes.py`
real-subprocess-e2e flake, independently re-run and re-confirmed unrelated to any change in this batch;
plus a `safeguard verify` flag that was this very `VERSION` bump landing between an unrelated automated
snapshot and this run's own verify step — confirmed via direct `diff` against the flagged snapshot showing
only the intentional `VERSION` line changed, then resolved with a fresh snapshot: `720/720 OK, 0 damaged`).
`rps_lint.py` clean. New coverage: `engine/tests/test_search_fuzzy_cache.py` (8 checks), a new WCAG guard
in `engine/verify_ui.py` (6 checks). Every fix in this entry checked live in a real browser against the
real running app (`getComputedStyle()`/`document.activeElement`/simulated `KeyboardEvent`s), not just read.

---

## [1.28.0] — 2026-08-30 — Field-reliability quick wins: cart persistence, stepflow voice-nav, PORTING.md currency
**VERSION → `1.28.0`.** The first three "do now" items from a production-readiness/parity audit against
fielded military IETM viewers (EMS-VIEWER/EMS-NG, IADS) and the search-accuracy landscape more broadly —
each verified live in a real browser against the real running app, not just read.

- **The parts-request cart now survives a crash, a closed tab, or a lost connection.** It was the one core
  workflow (the home page is laid out as Search | Parts-Request) with zero persistence — a plain in-memory
  array, no `localStorage` call anywhere, while the procedure checklist and the ingest job both already
  autosaved. `engine/ui/index.html`'s `CART` is now saved from the single choke-point every mutation already
  passes through (`renderCart()`, called after every add/remove/async-enrichment update) plus the one path
  that doesn't re-render on its own (an in-place field edit via `oninput`). Restored on load with a visible
  toast ("Restored N item(s) from your last session") so the persistence is honest, not silent. Verified
  live: added 2 items, confirmed them in real `localStorage`, edited a field and confirmed the edit
  persisted immediately, removed one and confirmed the array shrank, reloaded the page and confirmed both
  the remaining item and all its async-enriched sub-fields (FLIS reference, CAGE, price) survived intact.
- **`stepflow.html`'s hands-free voice step-navigation now actually works.** This is the page explicitly
  built for following along at the vehicle, but `readaloud.js`'s step-nav bar (auto-injected app-wide by
  `palette.js`) never appeared there — it looks for `.step`/`.n`/`.body` inside `#stepwrap` or `#out`, and
  this page rendered its steps as `.node`/`.num`/`.body` instead. Fixed additively (`class="node step"`,
  `class="num n"` — both class names on the same elements, nothing renamed) since neither `step` nor `n` has
  a CSS rule defined anywhere in `base.css` or in this file, confirmed before shipping. Verified live: the
  hands-free `◀ prev / next ▶ / 🎤` bar now appears on a real `/stepflow?q=...` page and correctly reports
  step count and text (confirmed via `stepNodes()` finding 6 real steps, `.n`/`.body` extracting the right
  number and prose, `window.viewerNextStep()` correctly advancing) — 0 steps found before this fix, 6 after.
  New regression coverage in `engine/tests/test_readaloud_stepnav.py` (4 new checks) guards the additive
  class pair going forward.
- **`docs/PORTING.md` — the exact document a new site would use to stand itself up cold — no longer says
  v1.13.2.** It was 14 minor versions and roughly six weeks of shipped work behind, and critically did not
  warn about the real `[1.25.0]` schema-migration gap (`viewer.db` missing migrations 0009–0012, silently
  breaking `measures`/`ask`/`cautions`/`pmcs`/`oneuse` for ~3 weeks) that a fresh copy could walk straight
  into. Updated to v1.28.0, route count (276), CI's existence, and a new explicit call-out of the migration
  trap with the one-line fix (`python viewer_ingest.py migrate`).
- **Also regenerated**: `docs/feature_audit.txt` (`engine/audit_features.py`'s own output) had drifted to a
  stale route count (249 GET) from before `[1.24.0]`'s re-audit — refreshed to the real current 250 GET /
  159 decorators / 68 reachable self-tested modules (adds `pageqa`, missing from the prior run).

**Verified:** `engine/tests/verify_all.py --snapshot`: 49/50 (only the known pre-existing
`test_ingest_routes.py` flake), `rps_lint.py` clean (a false-positive "ES6 class declaration" flag from a
code comment using the phrase "class name" — not actual code — was caught and reworded before shipping),
safeguard 719/719 files OK, 0 damaged.

---

## [1.27.0] — 2026-08-30 — part.html: surface conflicts.py's cross_vehicle/vehicles annotation to the technician
**VERSION → `1.27.0`.** The direct UI follow-up `[1.26.0]` left open: `conflicts.py`'s fix computes and
returns `vehicle`/`vehicles`/`cross_vehicle` on every conflict, and `/api/conflicts` already sorts
confirmed single-vehicle conflicts ahead of ambiguous ones — but nothing in `engine/ui/part.html`'s
conflict card read any of it. A technician looking at `/part` had no way to tell a confirmed same-vehicle
disagreement from an ambiguous one spanning several unrelated vehicles without reading the raw JSON.

- **`lazyConflicts()`** (`engine/ui/part.html`) now: (1) shows each disagreeing value's own vehicle label
  inline next to its TM/page citation when the conflict is `cross_vehicle: true` (unchanged, uncluttered
  for the confirmed single-vehicle case); (2) adds a distinct `⚠ Spans N different vehicle labels (...)
  — confirm these are really the same vehicle/serial before trusting this as one conflict` line, using the
  existing `.warn` CSS class already used elsewhere on this page; (3) gives `cross_vehicle: true` entries
  a left-border visual accent so they read as distinct from a confirmed hit at a glance. All new text goes
  through the page's existing `esc()` helper — no new unescaped interpolation.
- **Verified live**, not just read: started the real server, searched `/part` for the exact "WINCH
  INSTALLATION" corpus example this whole `[1.25.0]`/`[1.26.0]` investigation started from. Confirmed:
  the `electrical` and `weight` conflicts (7 and 5 distinct vehicle labels respectively) now show the
  `⚠ Spans N different vehicle labels` caveat with every real vehicle listed (2.5 TON TRUCK, 5 TON,
  M1113, M35AC, TM,S HUMMERS,ALL, UPDATED 1156A1, WORK); the `length (mm)` conflict on the same page
  (a confirmed single-vehicle hit, `vehicle: "TM,S HEMMIT"`) correctly shows neither the per-value vehicle
  labels nor the warning line, keeping the UI clean for the case that doesn't need a caveat. No console
  errors.
- **Docs:** closes out `[1.26.0]`'s own "genuinely still open" UI-wiring follow-up in
  `HANDOFF-NOTE.md`/`MASTER-RECONCILIATION.md`/`PROJECT-SUMMARY.md` (struck through, per this project's
  established convention). `ITERATION-SNAPSHOTS.md`/`ITERATION-DASHBOARD.html` regenerated.
- **Verified:** `engine/tests/verify_all.py --snapshot`: 49/50 (only the known pre-existing
  `test_ingest_routes.py` flake), safeguard 719/719 files OK, 0 damaged.

---

## [1.26.0] — 2026-08-30 — conflicts.py: fix cross-vehicle false positives without introducing a false-negative safety regression
**VERSION → `1.26.0`.** Two implementation passes on one feature-quality fix, the second correcting a
serious safety regression the first introduced — both caught by this session's adversarial-review
discipline before either shipped to `main`.

### The original bug (found while re-running `BUILD-CONFLICTS.bat` after `[1.25.0]`'s migration fix)
`conflicts.detect()` grouped extracted measurement values purely by `(type, unit)`, with no regard for
which vehicle/document a value came from. A generic FTS-matched subject (e.g. "WINCH INSTALLATION")
pools numeric readings from whatever documents happen to match it; unrelated vehicles routinely share a
subject string, so their naturally-different real specs got pooled and flagged as a false "conflict".
Confirmed on the real corpus: a "WINCH INSTALLATION" sweep pooled 4 documents from 3 different vehicles
into one group.

### Pass 1 (implemented + 3-lens adversarially reviewed, NOT merged as originally designed)
Grouped by `(type, unit, vehicle)` instead. Correctly separated the 3 unrelated WINCH-example vehicles.
Adversarial review (correctness/safety-R13/test-coverage lenses, run via this session's Workflow tool)
caught a serious regression, confirmed by direct reproduction against the real corpus and a synthetic
case: "vehicle" is a raw ingest-folder name (`viewer_ingest.py`'s `vehicle = rel.split(os.sep)[0]`), not
a canonical vehicle ID. The SAME real vehicle is sometimes filed under two different folder spellings
(e.g. "HMMWV" vs "TM,S HUMMERS,ALL", both real folder names in this corpus) — hard-splitting by vehicle
silently **dropped** a genuine cross-manual disagreement whenever that happened: `detect()` on a real
35-vs-50-ft-lb torque disagreement returned `[]` once tagged with those two spellings, because they
landed in separate groups of 1 and never got compared. Separately confirmed: ~86% of this corpus's
39,683 documents sit under generic ingest-staging folders ("WORK" 65%, "ALL EMS VEIWER FILES" 17.6%,
"Additional IMG Info" 2.9%) that mix genuinely unrelated real vehicles, so hard-splitting barely narrowed
the original false-positive problem for most of the corpus anyway (an "ALTERNATOR" query still pooled an
HMMWV torque spec against an unrelated MRAP-family spec, both tagged `vehicle="WORK"`). For a module
whose whole purpose is catching cross-manual disagreements, a silent false negative is worse than the
false positive it replaced — never shipped to `main`.

### Pass 2 (shipped)
Restores the **original `(type, unit)`-only grouping** — byte-identical recall to the pre-vehicle-scoping
code, independently confirmed by a second, targeted adversarial review that diffed the change against
`main` line-by-line — and instead **annotates** each flagged group with `vehicle` (single label if
unambiguous, else `""`), `vehicles` (sorted distinct labels seen), `cross_vehicle` (bool). Nothing is
ever hidden because of a vehicle mismatch; the original WINCH INSTALLATION example still gets flagged,
now correctly marked `cross_vehicle: true` with all 3 vehicle labels listed instead of being silently
absent or silently indistinguishable from a confirmed single-vehicle hit.
That second review also found: sort order didn't deprioritize `cross_vehicle: true` groups (a spurious
75%-spread 3-vehicle pooling could outrank and crowd out a confirmed 30%-spread real conflict in a UI
that only shows the top N) — fixed, sort is now severity → vehicle-confirmed-before-ambiguous → spread; a
defensive `str()` cast on the vehicle field (mirrors the existing type/unit idiom, not reachable via real
production data, cheap to harden anyway); and two honesty gaps in the docstring, now disclosed: citations
dedup by distinct value not by doc, so a vehicle named in `vehicles` can have zero backing citation in
`values`; and `engine/ui/part.html` does not yet read any of the new fields — the annotation is available
via the API but not yet surfaced to a technician, a separate, still-open follow-up.

### Verified
`python conflicts.py` (self-test, 7 checks) and new `engine/tests/test_conflicts.py` (34 checks) both
green. Sabotage-tested: reverted the grouping key back to the Pass-1 design in place, confirmed 7 tests
correctly fail, restored, confirmed all green again. `verify_all.py --snapshot`: 50/50, safeguard
716/716 files OK, 0 damaged. A second independent adversarial review ran 7 of its own new cases (unicode
vehicle names, 50-distinct-vehicle groups, mixed-case identical vehicles, whitespace-only vehicles,
zero/negative values) plus the existing `test_newmodules.py` fuzz suite (500 cases) against this design
and found no recall regression.

### Operational follow-up (done as part of shipping this)
`index/conflicts.db`'s existing sweep (run 2, from investigating the `[1.25.0]` migration bug) was built
entirely against the pre-fix `detect()` and carries no `vehicle`/`cross_vehicle` data — re-swept via
`BUILD-CONFLICTS.bat` after this merge so `/api/conflicts`'s precomputed cache reflects the fix (see
`precomputed_for()`'s 45-day freshness window — it has no code-version awareness, so this re-sweep is
what actually makes the fix visible to that route, not the code change alone).

### Docs
`docs/CHANGELOG.md` `[1.26.0]`; `VERSION` bump; `ITERATION-SNAPSHOTS.md`/`ITERATION-DASHBOARD.html`
regenerated.

---

## [1.25.0] — 2026-08-30 — CRITICAL: applied 4 pending schema migrations the real viewer.db never had — measures/ask/cautions/pmcs/oneuse were silently returning nothing since v1.13.5
**VERSION → `1.25.0`.** Host-operational fix, not a code change (migrations 0009–0012 already shipped in
past releases as SQL files — this is the first time they were ever actually applied to the real,
production `index/viewer.db`). Found while investigating a suspicious "0 conflicts found" result from
`BUILD-CONFLICTS.bat`'s real first-ever run against the full corpus (see below) — verified rather than
trusted, per this project's own review discipline.

### Root cause
`schema_meta` on the real DB showed `schema_version=8`. Migrations 0009 (`pages.ocr_confidence`), 0010
(`pages.barcode_type`/`barcode_data`/`barcode_nsn`), 0011 (`schematics` table), 0012 (`parts_conflicts`
table) — shipped in the changelog between v1.13.5 and v1.22.0 — had **never been applied**. Every one of
`features/corpus.py`'s `fts_pages()` calls unconditionally selects `p.ocr_confidence` in its shared SQL
template; against the real schema this always raised `sqlite3.OperationalError: no such column:
p.ocr_confidence`, caught by the function's own "degrade safe, never a 500" contract and silently
converted to an empty list. Confirmed directly against the live running server (not just a script):
`GET /api/measures?q=torque` → `count:0`, `GET /api/ask` → `answered:false, retrieved:0`,
`GET /api/cautions`/`GET /api/pmcs`/`GET /api/oneuse` → all empty. Plain `GET /api/search` was unaffected
(it doesn't ride `corpus.py`), which is why nothing looked wrong from the home page. This has been
silently broken since whichever session shipped v1.13.5 (2026-08-09) — 3 weeks — and nothing caught it
because the test suite runs against a synthetic fixture DB with the correct schema, never the real corpus.

### Fix
`python viewer_ingest.py migrate` — the sanctioned, already-built path (`migrate()`'s own docstring:
backs up via `safeguard.backupdb()` before applying any pending migration, then applies each one
atomically, DDL + `schema_version` bump in one transaction, crash-safe). Ran for real against the
production `index/viewer.db`: `schema_meta` now reads `12`; `pages` gained `ocr_confidence`,
`barcode_type`, `barcode_data`, `barcode_nsn`; `schematics` and `parts_conflicts` tables now exist.
Re-verified live: `find_for_query('torque')` → 26 real, cited results (was 0); `find_for_query('GASKET')`
→ 25 (was 0). `engine/tests/verify_all.py --snapshot` re-run clean after: 48/49 (only the known
pre-existing `test_ingest_routes.py` flake), `safeguard verify` 718/718 files OK, 0 damaged.

### Also done this session (real host actions, not simulated)
- **`safeguard.py backupdb --auto`** run for real for the first time: 3.64 GB `VACUUM INTO` copy,
  verified via `PRAGMA quick_check`, in 147.5s; `--auto` also pruned 47 stale code/docs snapshots from
  this session's own repeated `verify_all --snapshot` runs down to the newest 10.
- **`THE_VIEWER_WeeklyDBBackup` scheduled task registered** (`schtasks`, Sunday 03:00) — it did not exist
  before despite `register_snapshot_task.bat` shipping for it in v1.15.0. Test-fired once via
  `schtasks /Run` to confirm it actually executes end-to-end, not just that the underlying function
  works: confirmed, produced a second real backup file.
- **OCR completion re-checked against the real corpus**: **94.62%** (1,749,089 of 1,848,465 pages have
  `char_count > 0`), up slightly from the 94.4% last recorded at v1.13.4. No OCR process is currently
  running (some `ocr_status='running'` rows are stale leftover state from a past interrupted run, not
  live — confirmed via `tasklist`/process inspection, not assumed).
- **`BUILD-CONFLICTS.bat` run for the first time ever** against the full corpus (`index/conflicts.db` now
  exists). The pre-fix run (vacuous, before the migration was applied) found "0 conflicts" across 2000
  subjects with `n_values=0` everywhere — this is what surfaced the bug above. The post-fix re-run found
  real data (1548 of 2000 subjects flagged), but **that headline number is not a trustworthy conflict
  list as-is** — spot-checking the actual rows shows `build_conflicts.py`'s "most frequent part subjects"
  selection picks generic, corpus-wide phrases (e.g. "WINCH INSTALLATION", "POWER AMP ASSEMBLY") that FTS
  legitimately matches across hundreds of unrelated documents/vehicles; `conflicts.detect()` then pools
  every incidentally-matched numeric value under that one subject string and flags the natural spread
  across genuinely different real equipment as a "conflict" (e.g. one flagged row pools values `'3'`,
  `'4'`, `'5'`, `'6'`, `'7'` sourced from `TM 9-2320-272-24-4`, `TM 9-2320-387-24-1`, `TM 9-2320-387-24-2`,
  and `TM 9-2320-361-34` — four different manuals for what are very likely four different real winches,
  not one part with disputed specs). This is a real, separate, pre-existing design gap in how
  `conflicts.check_query()` scopes a match (no per-document/per-part disambiguation), not something
  introduced by this fix — the live `/api/conflicts?q=...` route has carried the same limitation for any
  sufficiently generic user-typed query since v1.13.0. **Deliberately not fixed in this pass** — needs
  either narrower subject selection (skip corpus-wide-generic terms) or a same-document/same-vehicle
  grouping constraint in `detect()` before the precomputed sweep's output can be trusted as a real safety
  finding rather than noise; flagged as a new, genuinely open follow-up item.

### Docs
`docs/CHANGELOG.md` `[1.25.0]`; `VERSION` bump; `PROJECT-SUMMARY.md`/`MASTER-RECONCILIATION.md`/
`HANDOFF-NOTE.md` updated with the corrected OCR %, the backup-task confirmation, and the new
conflicts.py subject-scoping follow-up item. `ITERATION-SNAPSHOTS.md`/`ITERATION-DASHBOARD.html`
regenerated.

---

## [1.24.0] — 2026-08-29 — Route-count re-audit + Staleness-audit "Tiers 2/5/6" correction (both docs-only)
**VERSION → `1.24.0`.** Documentation-only, two independent findings from the same reconciliation pass.

### Route-count re-audit: 276 routes (250 GET + 26 POST), zero collisions, mechanically confirmed
The "265 routes (244 GET + 21 POST)" figure carried in
`PROJECT-SUMMARY.md`/`HANDOFF-NOTE.md`/`MASTER-RECONCILIATION.md` had gone stale since v1.14.0 — v1.15.0
through v1.22.0 added a real batch of new routes but the count itself was never redone. Re-audited two ways,
not just a live-dict count (which can't distinguish a real registration from a silent same-path overwrite):
- **Live count** — imported `viewer_app` (which wires every `features/routes/*.py` module) and read
  `features.registry.GET`/`POST` directly: **250 GET, 26 POST = 276 total**.
- **Source-level collision check** — regex-extracted every `@get(...)`/`@post(...)` decorator's path
  literal(s), including alias arguments, from `features/routes/*.py` (135 GET, 26 POST, no internal
  duplicates in either), then separately extracted every path `static.py`'s `register_static()` registers
  programmatically from its `_PAGES`/`_SCRIPTS` dicts + the hardcoded `/base.css` (115 GET, no internal
  duplicates). `135 + 115 = 250` exactly matches the live GET count, and the two path sets have **zero
  overlap** — confirming no route anywhere silently clobbers another's registration.
- **New since v1.14.0's last count:** `GET /api/pageqa` (1.16.0), `GET /api/vlm` (1.17.0),
  `GET /api/layout` (1.22.0), `GET /api/editions` / `GET /api/symbols` / `GET /api/symbols_page_image`
  (1.15.0); `POST /api/airgap_export_decisions` / `POST /api/airgap_import_decisions` /
  `POST /api/ingest_upload` / `POST /api/ocr_backlog_start` / `POST /api/symbols_template` (1.15.0),
  `POST /api/analytics_log` (1.20.0).
- **Docs:** `PROJECT-SUMMARY.md` §8 item 8, `MASTER-RECONCILIATION.md` §6 item 9, and `HANDOFF-NOTE.md`'s
  "Known gotchas" route-collision paragraph all updated with the new figures and closed out (struck through,
  per this project's established reconciliation convention — see `[1.23.0]`'s semantic-embeddings item for
  precedent) rather than deleted, preserving the history of what was tracked and when it was resolved.
  `ITERATION-SNAPSHOTS.md`/`ITERATION-DASHBOARD.html` regenerated (`build_iteration_snapshot.py`); `VERSION`
  bump. No code changed — this entry only re-verifies and documents the existing, already-shipped route set.

### Staleness-audit "Tiers 2, 5, 6" correction: they were already done — there is no Tier 5 or 6
`[1.23.0]`'s reconciliation pass stated "Tiers 3 and 4 of the Viewer Drift Report were actually done and
never reconciled; only 2/5/6 remain genuinely unstarted." That claim was itself wrong, caught while this
entry's route-count work was already re-verifying git history for unrelated reasons. A direct
`git log --all --grep="Drift Report\|Tier"` shows the Viewer Drift Report staleness audit only ever had
**4 tiers total, not 6**: Tier 1 (`3054dad`, deprecated `fitz` imports/test isolation/misc drift), Tier 2
(`132132f` — the `[1.14.0]` documentation-reconciliation commit itself, missed by `[1.23.0]`'s check the same
way Tiers 3/4 initially were), Tier 3 (`8f795bc`, dependency version bounds + Python/Actions CI hardening),
Tier 4 (`1b3c6d8`, repo-bloat/env-var-docs/Windows-CI). Tier 4's own commit message states outright: "This
closes out all 4 tiers of the Viewer Drift Report staleness audit run across this session." **All 4 tiers
are complete and have been since 2026-08-18 — Tier 5 and Tier 6 never existed.** Corrected in
`HANDOFF-NOTE.md` item 3, `MASTER-RECONCILIATION.md` §6 item 7, `PROJECT-SUMMARY.md` §8 item 6 — struck
through and closed rather than deleted, same convention as the route-count item above.

---

## [1.23.0] — 2026-08-25 — Reconcile CHANGELOG.md against 11 more undocumented commits (2026-08-18 → 08-24)

A second reconciliation pass, same root cause the [1.15.0] entry already names at length: real work landed on
`main` without a matching entry here. This batch is smaller than that one (11 commits vs. 30) but was hiding
in plain sight — `5116324` (folded into [1.15.0]'s own commit range, see below) **explicitly names 4 of these
11 commits as "a real R4 violation... flagged for a following pass"**, and that following pass never
happened until now. Found via a fresh commit-vs-changelog audit (every non-merge, non-doc commit on `main`,
cross-checked for sha citation or narrative coverage), not a routine check — prompted by tracing why
`HANDOFF-NOTE.md`'s "5 Medium-tier findings deliberately deferred" list still named a CAD-mesh-dedup item
that turned out to already be fixed. Every commit below was verified directly: its own diff read in full, and
its shipped code confirmed still present in the current tree (not superseded or reverted by later work).
`docs/HANDOFF-NOTE.md`/`PROJECT-SUMMARY.md`/`MASTER-RECONCILIATION.md` still need their own follow-up pass to
drop the now-resolved items this entry closes (tracked below, matching [1.15.0]'s own precedent of
reconciling `CHANGELOG.md` first and the three hand-off docs separately). **`VERSION` → `1.23.0`.**

### Reconciled — Viewer Drift Report, Tiers 3 & 4 (`8f795bc`, `1b3c6d8`; 2026-08-18 08:41 / 10:30)
- **Tier 3 — dependency & CI hardening** (`8f795bc`): `requirements.txt` version-bounded (`pymupdf<2`,
  `numpy<3`, etc. — no forced downgrades against what was already installed, verified via
  `pip install --dry-run` before committing); `.github/workflows/ci.yml` gained the Python 3.12/3.13/3.14
  matrix this project's CI has run under ever since (verified the 3.14 leg specifically had never been tested
  locally at all — no 3.14 interpreter existed on the dev machine at the time — making this genuinely the
  first real test of it, live).
- **Tier 4 — repo bloat, env vars, Windows CI** (`1b3c6d8`): deleted 147 redundant per-diagram `_preview.png`
  files plus a duplicated, unused `mermaid.min.js`/`viewer.html` pair (27MB → 9.9MB repo size); added the
  `SYSTEM-REQUIREMENTS.md` "Environment variables" section that's been cited by name elsewhere in this file
  ever since; added the `test-windows` CI job. This is HANDOFF-NOTE.md's own "Staleness-audit Tiers 2–6 …
  not yet started" item — **Tiers 3 and 4 specifically were already done**, just never reconciled here; only
  Tiers 2/5/6 remain genuinely unstarted (see docs/audit/ + the Viewer Drift Report artifact for what those
  cover).

### Reconciled — CI-matrix fallout + audit-followup hardening (`4592117`, `37d909b`; 2026-08-18 10:57 / 14:12)
- **Two real bugs the new matrix surfaced** (`4592117`): `ingest_preview()` compared an un-normalized path
  against a `realpath()`-resolved one, failing on Windows junction points the new Windows CI leg actually
  exercises; a process-group-kill test asserted a POSIX guarantee ("grandchild also dies") that was never
  actually true there — rewritten to assert the real, platform-specific guarantee (strong on Windows, weaker
  documented behavior on POSIX) instead of a guarantee that only happened to hold on the dev machine.
- **CAD mesh dedup + 2 more shared-helper consolidations, plus a full 6-angle xhigh review pass** (`37d909b`):
  `cad_render.py`'s and `dimscad.py`'s duplicate hand-rolled `_box()` builders now share one implementation,
  `engine/cad_mesh.py` (`box_mesh()`) — **this is the exact item `HANDOFF-NOTE.md`'s "5 Medium-tier findings
  deliberately deferred from the v1.14.0 audit" list still names as open; it has been fixed since 2026-08-18
  and was simply never reconciled.** Same commit also unified `kg.py`'s/`build_publog.py`'s near-identical
  atomic SQLite build-and-swap scaffolds into `safeguard.atomic_sqlite_build()` (the review pass caught
  `build_rpstl.py` had the identical unmigrated pattern and migrated it too, so all three sidecar builders
  now share one crash-safety contract), consolidated `ocr_supervisor.py`'s and `run_timeout.py`'s duplicate
  process-tree-kill logic into `engine/proctree.py`, and split `viewer_ingest.py`'s OCR lock-acquire timeout
  from its full page timeout (a busy-but-healthy lock now fails fast in ≤20s instead of burning most of a
  page's own 120s deadline queued behind it) — the review pass caught the two timeouts had no cross-check, so
  a tight page timeout could let the lock timeout outlive it; now clamped.

### Reconciled — v1.13.6: bare-callout temperature guard + null-vs-zero OCR average (`5928d59`; 2026-08-24)
- This commit's own message calls itself "v1.13.6" — no such section ever existed here (the sequence jumped
  `[1.13.5]` → `[1.14.0]` directly). Rather than retroactively splice a `[1.13.6]` section into already-
  shipped, already-numbered history, it's reconciled here under the current version instead, same as every
  other commit in this entry — this is the origin of the `_CALLOUT` guard `[1.18.0]`'s (now `[1.20.0]`'s,
  see that entry's own version-collision note) generalization work built directly on top of.
- `measures.py` gained the original `_CALLOUT` regex guard (a document-structure word — figure/table/degree
  callouts like "FIGURE 5 C" — immediately before a bare number+letter stops it from misreading as a
  temperature), with 6 callout-case tests plus 1 regression case proving a real temperature still extracts.
- `coverage.py`: `AVG(ocr_confidence)` was computed even when zero pages had ever been scored, and this
  project's `scalar()` helper swallows the resulting SQL exception down to `0` — indistinguishable from a
  real, catastrophic confidence average. Gated the `AVG` query on the scored-count so both "never migrated"
  and "nothing scored yet" correctly read as `null`, not a fabricated zero.

### Reconciled — CI/test-infra fix chain, 6 commits (`86e4304` → `c0da558`; 2026-08-24 15:38 → 16:06)
One continuous ~30-minute live-CI debugging session, each commit diagnosing exactly what the previous one's
fix newly revealed — not batched after the fact, reconciled here as the sequence it actually was:
1. `86e4304` — `test_ingest_routes.py`'s `.bat`-subprocess checks called `cmd` directly with no `os.name`
   guard; Ubuntu CI has no `cmd`, so the whole file aborted with `FileNotFoundError` before any of its other
   checks could run. Guarded the same way `test_features.py`/`test_ocr_supervisor.py` already do.
2. `f3bae71` — `verify_all.py` tailed every suite's output to its last 3 lines regardless of pass/fail, so a
   failing suite's own named `PASS`/`FAIL` lines (which say what broke) were silently discarded, not just
   unprinted — the exact gap that made the next 4 commits' diagnosis possible once fixed. Compact tail kept
   for a passing suite; full output printed for a failing one.
3. `b6f115c` — with real output finally visible, root cause of 5 failing OCR-content checks across all 4
   matrix legs: CI installed `pytesseract` (a subprocess wrapper) but never the actual `tesseract` binary it
   wraps — the call doesn't raise, it just returns empty text, so everything downstream of "OCR produced real
   content" failed instead of erroring. The dev machine already had tesseract installed system-wide, masking
   this in every local repro attempt. Installs the real binary via `apt`/`choco` on both runners.
4. `91b6bbf` — same 5 checks still failed after the binary was installed (OCR now genuinely ran, just
   garbled): both real-OCR test fixtures hardcoded `arial.ttf`, which resolves on Windows (including this
   project's own dev machine) but not Linux, silently falling back to a bitmap font too thin to OCR back
   cleanly. Shared `_ocr_test_font()` helper added: Windows Arial → Linux DejaVuSans-Bold/DejaVuSans by
   absolute path → macOS Arial by absolute path → `load_default()` as the final fallback.
5. `9e2101c` — down to 1 failing check (`fts_content_hits >= 5`), landing exactly at the floor's own edge
   locally too (5/6). Rather than guess at a new threshold, embedded the real N/6 count in the check's own
   name so a future failure shows the real number directly instead of requiring another instrument-and-rerun
   round trip.
6. `c0da558` — the embedded count answered its own question: CI's Ubuntu tesseract (5.3.4) + the DejaVu
   fallback font reproducibly lands at 4/6, not a flake. Recalibrated the floor to `>=4` — the check's real
   intent (the FTS trigger stays in sync with real OCR content after the pagetrim post-pass) is just as well
   proven by 4-of-6 as by 5-of-6; the original floor was accidentally coupled to one specific engine/font
   combination's exact accuracy, which was never the point.

### Noted, not fixed — `5116324`'s mechanism was folded into [1.15.0] without its own citation
`5116324` ("Wire real OCR-engine confidence into the quality-flag system," 2026-08-19 05:04, inside
[1.15.0]'s own `c147614`→`9b0e5b9` commit range) is the commit that actually threads `pages.ocr_confidence`
through `features/corpus.py`'s `fts_pages()` into `textquality.annotate()`'s conservative blend (real
confidence can only pull a heuristic "clean" call down, never raise a "poor" one) — but [1.15.0]'s own prose
describes different files under its "OCR confidence threaded end-to-end" theme (UI badge tooltips,
`torque.html`/`measures.html`) and never names this specific mechanism or commit. Not re-opening or amending
that already-shipped entry; noted here for the historical record, since this is the exact commit whose own
message flagged the 4-commit gap this entry closes above.

### Verified
- Every commit's shipped code confirmed present in the current tree directly (not assumed from the commit
  message): `engine/cad_mesh.py` + both `_box()` delegates, `safeguard.atomic_sqlite_build()`,
  `engine/proctree.py`, `viewer_ingest.py`'s `OCR_LOCK_TIMEOUT_SECONDS` clamp, `requirements.txt`'s version
  bounds, the CI matrix + tesseract-binary install steps, `_ocr_test_font()`'s fallback chain, the `>=4` FTS
  floor, `measures.py`'s `_CALLOUT` guard, `coverage.py`'s scored-count gate.
- `python -m py_compile` clean on every file this entry's reconciled commits touch (spot-checked; none of
  this pass's own edits touch code, only `docs/CHANGELOG.md`).
- `python engine/build_iteration_snapshot.py` — R10 integrity OK, all changelog versions present in the
  snapshot after this entry's addition.

### Compatibility (R1)
- Documentation-only change. No code, no schema, no route, no test file touched by this entry itself — every
  fix it documents already shipped to `main` between 2026-08-18 and 2026-08-24 and has been running in
  production (such as it is) ever since.

---

## [1.22.0] — 2026-08-25 — Multi-column reading-order reconstruction (catalog §2.5)

Design spec + plan: `docs/superpowers/specs/2026-08-25-layout-reading-order-design.md` /
`docs/superpowers/plans/2026-08-25-layout-reading-order-plan.md`. Verified directly before designing
(the same check that already corrected two other pitches this session): `layout.py:76` really did sort
every page's blocks with a flat `key=lambda r: (r["bbox"][1], r["bbox"][0])` — top-to-bottom, left-to-right
on raw coordinates, no column awareness. On a genuine 2-column TM page this interleaves the two columns
line-by-line instead of reading one column fully before the next — the "scrambled order" `EXTRACTION-
METHODS-CATALOG.md` §2.5 has flagged as a known gap since that catalog was written. The module's own prior
self-test never caught this because every fixture block sat at the same `x=40` — a single-column layout was
the only shape it ever exercised.

### Added
- **`engine/layout.py` gains column-aware reading order** (v1.4.1 — see "Adversarial review" below for the
  0 → 1 patch bump). A single-level column split, not full recursive XY-cut — deliberately scoped to this
  corpus's actual page shapes (Army TM pages are either single-column body text or a simple 2-column layout
  with full-width headers/footers/titles, never a deeper multi-region magazine layout; if a future page shape
  needs more than one cut level, this is additively revisitable). Small, dependency-free local helpers
  (`_content_span`, `_is_full_width`, `_find_gutter`, `_median`, `_row_alignment_ratio`) feed
  `_column_order()`, called from a new `_reading_order()` that replaces the old bare `out.sort(...)` call at
  the end of `analyze()`:
  1. **Full-width vs. narrow.** A block spanning ≥65% of the page's own CONTENT width (the union x-range of
     every non-header/footer block — not the raw page width, so margins don't skew the threshold) is
     full-width. A `header`/`footer`/`title`/`heading`-typed block is *always* full-width regardless of its
     own measured text width — each is a page-spanning band positioned by role, not narrow column content,
     even when the literal text happens to render narrow (a short page number, a short chapter title like
     "COOLING"). Originally implemented for `header`/`footer` only; widened to `title`/`heading` too by
     adversarial review — see below.
  2. **Gutter detection.** The x-intervals of the narrow blocks are merged (any gap smaller than
     `max(12, 4% of content width)` counts as touching); the widest gap left between merged clusters is the
     gutter candidate. Fewer than 4 narrow blocks, or no gap left after merging, or fewer than 2 blocks on
     either side of the gutter → "not really 2-column," fall back to exactly the old flat sort.
  3. **Row-alignment gate.** A genuine x-gutter alone isn't sufficient — see "Adversarial review" below for
     why — so the two candidate columns must also read as actually *aligned* side by side, not merely
     occupying two x-ranges.
  4. **Banding.** When a real split is found, the page is walked top-to-bottom in bands delimited by the
     full-width blocks' own y-positions (each full-width block sits exactly where its y puts it); within
     each band every left-column block sorts before every right-column block, each column internally still
     ordered top-to-bottom.
- **`layout.py`'s own `__main__` self-test** — the existing single-column fixture/assertions are completely
  unchanged (regression pin: single-column output is byte-identical to before this change — confirmed by
  running it, not assumed). Four new fixtures: a genuine 2-column page (full-width header + title, 3
  left-column paragraphs and 3 right-column paragraphs with pairwise-**overlapping** y-ranges — the exact
  shape that breaks a flat sort — full-width footer), asserting the exact header → title → left×3 → right×3
  → footer order; a "couple of small scattered captions on an otherwise single-column page" fixture (only 2
  narrow blocks — below the 4-block minimum), asserting the fallback flat sort; and two adversarial-review
  regression fixtures — see below.
- **`engine/tests/test_routes.py`** — `/api/layout` added to the curated route list (`doc=2&page=12`, same
  style as the neighboring `/api/dimscan`/`/api/callout_numbers` entries). A repo-wide grep confirmed this
  route had zero coverage before this change — not even the blanket bare-GET crash-sweep proved more than
  "no 5xx," since a bare `/api/layout` with no `doc` param never reaches `layout.analyze()` at all.
- **`engine/tests/test_layout_route.py`** (new) — exercises the REAL route function
  (`doc_extractors.r_layout`) directly against a real 2-column PDF built with PyMuPDF, the same lightweight
  h/qs/core-fake pattern `test_tables_plus_stitch.py` already established for a sibling per-page extractor
  route, asserting the actual JSON response (not just `layout.analyze()` called in isolation) comes back in
  column-aware order. Also covers a single-column page through the same real route (flat order, unaffected)
  and an unknown doc id (degrades to empty regions, no crash).

### Why this is safe/isolated (R1, R6)
- `layout.py` has exactly one consumer, `doc_extractors.py`'s `/api/layout` route (a local `import layout`)
  — confirmed via a repo-wide grep both before writing the design spec AND again after this change landed;
  nothing else imports it, nothing persists its output anywhere. This makes the whole change fully isolated:
  it changes what `/api/layout` returns, and nothing else — never `pages.body_text`, never search indexing,
  never any extraction pipeline that already runs corpus-wide.
- `analyze()`'s return **shape** is unchanged (`[{type, bbox, text, size}]`); only the *order* of that list
  changes, and only for pages where a genuine 2-column split is actually detected. No new fields, no new
  sidecar, no schema of any kind, no re-processing of the existing corpus needed for this to take effect.
- Reordering the actual text `pages.body_text` is built from (native-PDF or OCR) is explicitly OUT of scope
  for this pass — that would need re-processing the whole corpus and real-corpus validation that extraction/
  search behavior doesn't regress, a materially bigger risk class this change deliberately does not touch.
  `layout.py`'s reading order is a presentation-layer concern only.
- Error handling is unchanged: the whole function still degrades to `[]` on any exception or when
  `fitz`/the PDF path is unavailable; the new column-detection logic is plain-Python geometry over an
  in-memory list the existing code already built, so nothing new can raise that the existing `try/except`
  doesn't already catch.

### Deviation from the plan
- The design spec's classification list ("full-width: titles, section headings, running headers/footers…")
  was first implemented as a **type-based** rule for `header`/`footer` only, not a pure measured-width rule
  like every other block type gets. Discovered empirically: `layout.py`'s own pre-existing self-test fixture
  has a short header/footer string ("Change 2   2-1") that measures well under the 65%-of-content-width
  cutoff — treating it as "narrow" would have added it to the narrow-block pool alongside the fixture's
  heading/caption/figure blocks, crossing the 4-block minimum and risking a false-positive column split on a
  single-column regression fixture the plan requires to stay byte-identical. **Adversarial review caught
  that this same reasoning applies equally to `title`/`heading` and the first draft didn't cover them** — see
  below.

### Adversarial review
Three independent reviewers examined the diff (algorithm-correctness, regression-safety, test-quality
lenses). Two HIGH findings, both fixed and verified directly before being accepted — not taken on the
reviewers' word.

- **HIGH (algorithm-correctness): a short title/heading could be swallowed as narrow column content.**
  `_is_full_width()`'s first draft only exempted `header`/`footer` by type; `title`/`heading` were measured
  purely by rendered width. A short title (e.g. "COOLING", well under the 65% cutoff) positioned over one
  column got column-assigned and sorted into the MIDDLE of the page — after an entire column of body text —
  instead of appearing first as the page-spanning heading it actually is. Neither of the diff's own original
  test fixtures caught this because both used a long title comfortably clearing the width threshold by
  accident. **Fixed** by widening the type-based exemption to `title`/`heading` too, matching the spec's own
  stated intent. New regression fixture added (a short "COOLING" title over a 2-column page); sabotage-
  verified by reverting the fix and confirming the new assertion fails exactly as predicted, then restored.
- **HIGH (regression-safety): the "single-column pages stay byte-identical" guarantee was false on the most
  common Army-TM page shape.** `_find_gutter()` clusters purely by x-interval overlap with no y-awareness —
  an ordinary single-column page using the standard right-indented CAUTION/NOTE/WARNING callout-box
  convention next to left-margin step text produces two real x-clusters (left steps, right callouts) with a
  genuine gutter between them, and the reviewer showed callouts can even span nearly the same y-range as the
  steps they're interleaved with. The original heuristic accepted this as "2 columns" and regrouped every
  CAUTION/NOTE/WARNING away from the specific step it modifies — not just a cosmetic reorder, actively
  misleading on a maintenance manual (a WARNING separated from the step it warns about is a real usability/
  safety concern, not a UX nit). **Fixed** by replacing a density-based check (tried first, rejected — both a
  genuine short 2-column section and a scattered-callout pattern score similarly "sparse" at only 2-3 blocks
  per side, so density alone didn't discriminate) with a row-alignment check: for each left block, the
  distance to its nearest right-column neighbor, compared against the typical gap between consecutive
  left-column blocks. Genuine side-by-side columns have matching items at nearly the same y (ratio ≈0.14,
  measured directly against a real reproduced fixture); an interleaved callout sits roughly halfway between
  two consecutive same-column items (ratio ≈0.49, same method). Threshold set at 0.30 — real margin on both
  sides of the two measured cases, not tuned to either edge. New regression fixture reproduces the reviewer's
  exact scenario (left-margin lettered steps + right-indented CAUTION/NOTE/WARNING boxes); sabotage-verified
  twice — the first sabotage attempt revealed the fixture's OWN geometry bug (step text long enough to
  visually overlap the callouts' x-range, so `_find_gutter()` returned no gutter at all and the fixture never
  reached the code path it claimed to test — caught by tracing the actual internal values, not by trusting a
  green assertion), fixed the fixture, then re-sabotaged the real threshold and confirmed the corrected
  fixture genuinely fails without the fix and passes with it restored.
- LOW finding (not fixed, documented): the design spec's error-handling section overstated that "the
  existing try/except" fully covers the new logic — technically the new helpers run just outside `analyze()`'s
  own `try/except`, though `doc_extractors.py`'s route already wraps the whole `analyze()` call in its own
  guard, so nothing is actually unprotected today. Noted here for a future maintainer rather than changed,
  since fixing it would mean restructuring working code to satisfy a documentation nit.

### Verified
- `python -m py_compile engine/layout.py engine/tests/test_layout_route.py engine/features/routes/
  doc_extractors.py` — clean.
- `python layout.py` — all five self-test fixtures pass (single-column regression, 2-column, fallback, the
  two adversarial-review regression cases above).
- `python tests/test_layout_route.py` — 6/6 passed (real route, 2-column order, single-column flat order,
  unknown-doc degrade).
- `python tests/test_routes.py` — 294/294 passed, including the new curated `/api/layout` entry.
- `python tests/verify_all.py --snapshot` — 48 checks, 47 ok, 1 pre-existing failure
  (`test_ingest_routes.py`'s "real e2e upload" subprocess case — reproduced identically via `git stash` on
  the unmodified base commit, so it predates and is unrelated to this change; `safeguard verify` reports
  716/716 files OK against the fresh snapshot). Every suite that touches `layout.py`, `doc_extractors.py`,
  or `/api/layout` (`test_routes.py` 294/294, the new `test_layout_route.py` 6/6, `rps_lint.py`) is green.

### Compatibility (R1)
- `VERSION` → **1.22.0**, matching this project's own established practice of bumping `VERSION` with every
  changelog entry. Not a claim of any behavior change for a single-column page — every single-column page's
  `/api/layout` response is byte-identical to before this change (pinned by the unmodified original
  self-test fixture).
- No `viewer.db` migration, no new dependency, no changed function signature outside `layout.py` itself.

### Known, deliberately deferred
- 3+ column layouts are not specifically detected — a page with more than 2 x-coverage clusters collapses
  to "left of the widest gap" vs. "right of it." Not seen as a real TM page shape in this project's own
  document set (per the catalog's own framing, "multi-column TMs," not general magazine layouts) — deferred
  unless a real example surfaces.
- The exact numeric thresholds (65% full-width cutoff, 4-block narrow minimum, 2-block-per-side minimum,
  12px/4%-of-content-width gutter minimum, 0.30 max row-alignment ratio) are tuned against this change's own
  synthetic fixtures — including two adversarial-review-driven, directly-reproduced cases for the alignment
  threshold specifically — not against a broad real-corpus sample of multi-column TM pages. The design spec's
  own "open items" framing explicitly left this for implementation-time tuning, not a blocking
  pre-requirement; the alignment ratio in particular would benefit from validation against real corpus pages
  in a future pass if mis-detections ever surface in practice.

---

## [1.21.0] — 2026-08-25 — Per-line OCR confidence capture (catalog §1.9)

Versioned 1.21.0, not 1.18.0 as this branch initially claimed (cut fresh from `main`, which no other PR had
merged into yet): three other independently-branched PRs off that same base already claimed 1.18.0/1.19.0/
1.20.0 (measures.py bare-unit fix, home-page nav regroup, search click instrumentation) — caught and
renumbered across every touched file before merge, same as the click-instrumentation branch's own earlier
collision with this same root cause.

Corrects the catalog's own framing while shipping it: §1.9 called this "per-word OCR confidence capture"
(S effort), but `ocr_one()`'s own docstring already said RapidOCR returns confidence **per detected line**,
not per word — standard PP-OCR-family behavior (the detection stage groups text into line/phrase boxes;
there's no per-word or per-character score in its public API). Genuinely per-word would mean reconfiguring
RapidOCR's detection model for word-level boxes — a materially bigger, GPU-hardware-dependent task this
environment can't build or verify (`rapidocr_onnxruntime` isn't installed here, same Advanced/GPU-fork-only
posture as every other RapidOCR-dependent piece of this app). What ships instead: the per-LINE confidence
RapidOCR already computes — today averaged into one page-level `ocr_confidence` number and the per-line
detail discarded (see [1.13.5] below, which captured the *average* but not this) — now captured and stored
per line. A future consumer that wants "which words does this apply to" attributes a line's score down to
the words it contains; that's word-level *attribution*, not independent per-word confidence, and this
change is explicit about the difference rather than repeating the catalog's original overstatement.
Design doc: `docs/superpowers/specs/2026-08-25-per-line-ocr-confidence-design.md`. Plan:
`docs/superpowers/plans/2026-08-25-per-line-ocr-confidence-plan.md`.

### Added
- **New sidecar `index/ocrconf.db` + `engine/ocrconf.py`** — own `CREATE TABLE IF NOT EXISTS` schema init
  (matching `dedup.db`/`pageqa.db`'s "own sidecar, own schema, never touches `viewer.db`" pattern, R6:
  append-only, corpus authoritative), one table `ocr_lines(document_id, page_number, line_index, text,
  confidence, PRIMARY KEY(document_id, page_number, line_index))`. `available(db_path)` (sidecar exists +
  non-empty, matching `publogdiff.py`'s own convention), `record_lines(db_path, document_id, page_number,
  lines)` (delete-then-insert per page, so a retried/re-OCR'd page never leaves stale trailing rows from a
  shorter re-record — not a bare `INSERT OR REPLACE`, which alone can't shrink a row set), `lines_for_page
  (db_path, document_id, page_number)` (`[]` on a missing/empty sidecar or any read failure, never an
  error — same degrade-to-empty contract `dedup.editions_for()`/`pageqa.ask()` already guarantee). Pure
  sidecar I/O, no extraction logic — `record_lines()` is best-effort and **never raises** (matches every
  other sidecar writer in `viewer_ingest.py`: a failure to persist per-line detail must never turn a
  successful page OCR into a failed one). `__main__` self-test round-trips a real temp sidecar.
- **`viewer_ingest.py`'s `ocr_one()` return widens `(text, confidence, barcode)` → `(text, confidence,
  barcode, lines)`.** `lines` is `[(text, score), ...]`, built alongside the existing `scores`/`conf`
  reduction from RapidOCR's own per-line `res` — every entry is kept at its true position (`None` for a
  missing/non-numeric score rather than dropping the line; see "Adversarial review" below for why filtering
  `res` itself, the way `scores`' own reduction safely does for an average, is NOT safe here) — `lines` is
  `None` on the blank-skip path and the Tesseract fallback (same paths `conf` is already `None` on;
  Tesseract doesn't expose per-line confidence the same way, matching the existing page-level gap this
  entry does not attempt to close). The identical-page dedup cache (`_DEDUP`)
  needed zero code changes — both its read and write sites already store/replay whatever tuple `ocr_one()`
  returns, so a cache hit on a repeated boilerplate page now correctly replays its `lines` too, not just
  `text`/`conf`/`barcode` (confirmed directly, and covered by a new regression test — see below).
- **`_ocr_task()` return widens** `(pid, text, conf, barcode, err)` → `(pid, text, conf, barcode, lines,
  err)` at all 3 return points (timeout / exception / success) — `lines` inserted before the trailing
  `err`, mirroring `ocr_one()`'s own widened shape.
- **`ocr()`'s `handle()` callback** widens to accept `lines`, and — after the existing `UPDATE pages SET
  ... ocr_confidence=?` call, using the same `document_id`/`page_number` already resolved from `_labels`
  right there for the `measures.db` call a few lines below (no reordering needed; the real code already
  resolves them in the right spot) — calls `ocrconf.record_lines(ocrconf_db_path, document_id,
  page_number, lines)` when `lines` is truthy. `ocrconf_db_path` (`index/ocrconf.db`, next to `viewer.db`)
  is resolved once before the loop, same "not per-page" precedent `meas_con` already sets. Both real call
  sites (`handle(*_ocr_task(r))`, `handle(*fut.result())`) already splat the tuple — zero changes needed
  there (confirmed directly, not assumed).

### Adversarial review
Three independent reviewers examined the diff (contract-integrity, data-correctness, test-quality lenses).
- **Contract-integrity lens: 0 findings** — every return point and call site of the three widened function
  contracts checked consistent.
- **Test-quality lens: 0 findings**, and it did real, independent sabotage-testing of its own before
  reporting: manually broke the `_DEDUP` cache-hit path to drop the newly-added `lines` element, confirmed
  `test_ocrconf.py` caught it (19/20, the exact dedup-replay check failing) with nothing else cascading,
  then restored and reconfirmed 20/20 — the kind of direct verification this project expects rather than
  trusting a test's name.
- **Data-correctness lens (HIGH, fixed)**: `ocr_one()`'s first draft filtered `res` itself — `[(r[1],
  round(r[2],4)) for r in res if len(r) > 2 and isinstance(r[2], (int, float))]` — before building `lines`,
  reusing `scores`' own filter verbatim. Safe for an average (an unscored entry just doesn't contribute);
  **not** safe here: filtering the list before building indexed rows both silently dropped that line's text
  entirely (never written to `ocr_lines`, not even with `confidence=NULL`, contradicting `ocrconf.py`'s own
  documented contract) and shifted every subsequent line's `line_index` out of alignment with its true
  position in `res` — worse for every later unscored line on the page. **Verified directly before fixing**:
  sabotage-tested by reverting to the buggy filter-based version and re-running the new regression test
  below — it failed exactly as predicted (4 of 4 new checks), confirming both the bug and that the test
  actually catches it, not just asserts something coincidentally true. Fixed by keeping every entry at its
  real position, using `None` for a missing/non-numeric score instead of dropping the line — `ocrconf.py`'s
  `record_lines()` already handled `None` scores correctly (it has its own dedicated self-test case for
  this), so the fix needed no sidecar-side change, only `ocr_one()`'s own list-building line.
- New regression test added for this exact bug (`test_ocrconf.py` section 4, 5 checks): a mocked 3-line
  page where the middle entry carries no score at all — confirms all 3 lines are recorded (none dropped),
  the unscored line keeps its text with `confidence=None` at its correct `line_index=1`, and the line
  *after* it still lands at its true `line_index=2`, not shifted down to 1.

### Verified
- `python ocrconf.py` — self-test OK (round-trips `record_lines()`/`lines_for_page()` against a real temp
  sidecar; `available()` False→True across a write; keyed strictly to document_id+page_number, no cross-
  page/doc leakage; re-recording a page's lines replaces rather than duplicates or leaving stale trailing
  rows; a non-numeric score keeps its line's text with `confidence=None`; a never-built sidecar and bad
  inputs degrade to `[]`/`False`, never raise).
- New `python tests/test_ocrconf.py` (25/25 checks, including the adversarial-review regression case above)
  — a real crawl → index → `ocr()` pass through
  `viewer_ingest.py` with `_have_rapid()`/`_get_rapid()` monkeypatched to a fake engine returning known
  multi-line results (no real `rapidocr_onnxruntime` needed — this environment doesn't have it installed,
  same posture the design doc calls out): one `ocr_lines` row per line lands with correct text/confidence,
  correctly keyed to document_id/page_number, unrelated doc/page queries return `[]`; the `_DEDUP`
  identical-page cache hit on a second byte-identical page replays the exact same per-line rows while the
  mocked engine is confirmed called exactly once (not twice); a Tesseract-fallback run (forced via the same
  `_have_rapid()`-monkeypatch technique `test_barcode_wiring.py`'s own section 9 already established)
  completes the page normally and writes nothing to `ocrconf.db`, without raising.
- `python tests/test_barcode_wiring.py` — 65/65 checks still pass unmodified (full real crawl→OCR→
  extract_parts pipeline, zero behavior change for the 3 widened contracts' one real caller).
- `python tests/test_ingest_routes.py` — 173/175 checks pass; the 2 failures (`real e2e upload...`) are
  **pre-existing**, confirmed unrelated by re-running the identical file against `viewer_ingest.py` stashed
  back to its pre-this-change state (same 2 failures, same names, before `ocr_one()`/`_ocr_task()`/`ocr()`
  were touched at all).
- `python tests/test_sysprobe_cli_resolution.py` — 20/20 (stubs `ocr()` itself; unaffected by its internal
  contract widening).
- `python tests/test_pageqa.py` — 28/28; `python tests/test_ocr_supervisor.py` — 22/22 (neither calls
  through the widened functions, included for completeness since both live in the same OCR-pipeline
  neighborhood).
- `python -m py_compile` clean on every touched file (`viewer_ingest.py`, `ocrconf.py`,
  `tests/test_ocrconf.py`); `python -m compileall engine/` clean whole-tree.
- `engine/tests/verify_all.py --snapshot` — full run: **48 checks, 47 ok, 1 FAILED** (the same
  pre-existing `test_ingest_routes.py` 2 sub-checks noted above; every other suite green, including the
  new `test_ocrconf.py` at 20/20); `safeguard verify` — **717 files, 717 OK, 0 DAMAGED**.

### Compatibility (R1)
- `ocr_one()`/`_ocr_task()`'s return arity changed (3→4, 5→6 respectively) — both have exactly one real
  caller each inside `viewer_ingest.py` itself (`_ocr_task()` calls `ocr_one()`; `ocr()`'s `handle()`
  consumes `_ocr_task()`'s result via the two existing splat call sites), both updated in this same change.
  Grepped the whole tree for any other caller — none found (confirmed in the PR's own verification, not
  assumed).
- `index/ocrconf.db` is a brand-new, purely additive sidecar — nothing in `viewer.db`, `dedup.db`,
  `pageqa.db`, `measures.db`, or any existing route/consumer references it. Rollback = don't run future OCR
  passes through the changed code; the sidecar stops growing but nothing existing breaks or needs it.
  `cautions.py`'s `textquality.annotate()` and `coverage.py`'s aggregate OCR stats are unmodified and keep
  reading `pages.ocr_confidence` exactly as before.

### Known, deliberately deferred (see design doc's "Non-goals")
- True independent per-word/per-character confidence — needs RapidOCR reconfigured for word-level
  detection, a GPU-hardware-dependent follow-on this environment can't build or verify, not this pass.
- No bounding-box geometry captured for each line — only text + confidence; no visual-highlighting
  consumer exists yet to need it (YAGNI).
- No existing consumer (`cautions.py`, `coverage.py`) was migrated to read the new per-line data — both
  keep working exactly as before (R1). A future pass could upgrade `cautions.py` to cite the specific line
  a caution's text came from instead of the whole page's average.
- Tesseract-fallback per-line capture is still out of scope — matches the existing page-level `conf=None`
  gap on that path, not a new one.
- No new route or UI affordance reads `ocrconf.py` yet — this pass is capture + storage + a generic read
  function (`lines_for_page()`) only, per the design doc's explicit scope.

---

## [1.20.0] — 2026-08-25 — Search click instrumentation + heuristic re-rank (Tier 2 "learned search re-ranker", Phase 1)

Versioned 1.20.0, not 1.18.0 as originally tagged throughout this branch's own commit/comments: two other
independently-branched PRs off the same `main` base already claimed the two numbers in between (`[1.18.0]`,
the still-open `fix/measures-labeled-bare-unit-callout` PR; `[1.19.0]`, the home-page nav regroup) — caught
and renumbered across every touched file (code comments, this entry, the 3 reconciliation docs) before merge,
avoiding a guaranteed collision whichever PR lands last.

The Tier-2 backlog item "learned search re-ranker" was pitched on a premise that turned out to be false on
inspection: `analytics.py`'s event log only ever captured **zero-result** queries (`gaps()`) — a pure failure
list. Nothing recorded which result a user actually opened, by rank, for a query that DID return results, so
there was no click-through / relevance signal anywhere to train a learned model on. Rather than build
"learned" ranking on top of a signal that didn't exist, this does two honest things instead: (1) start
logging real engagement now, so a genuinely learned re-ranker has real data next round, and (2) ship a
modest, hand-tuned ranking improvement now, so something concrete improves this round too. Full design in
`docs/superpowers/specs/2026-08-25-search-click-instrumentation-and-heuristic-rerank-design.md`. A secondary
correction made during design: `engine/ui/index.html`'s search UI calls `/api/search`
(`search_feature.search()`'s FTS + `exact`/`approx`/`boosted` stable sort), **not**
`/api/search_hybrid` (`hybrid.py`'s RRF `fuse()`, a secondary endpoint nothing in the primary UI calls) — the
heuristic therefore targets `search_feature.py`'s sort, not `hybrid.py`.

### Added
- **`engine/analytics.py`** — new event kind `"click"` added to `_VALID`; `log()`'s `extra` allowlist grows
  from `{doc, page, nsn}` to include `rank` (coerced to `int` then stored as a string, silently dropped —
  not error-raised — if it isn't int-like, matching every other field's "never raises, best-effort"
  contract). New `clicked_pages(index_dir)` → `set[str]` of `"doc_id:page_number"` keys built from every
  `"click"` event ever logged, cached 60s — copied verbatim from `features/parts_feature.py`'s
  `popular_nsns()` cache-dict shape/TTL (own `_CLICK_CACHE`, deliberately not sharing `_POP_CACHE`, so the
  two caches can never collide). `__main__` self-test extended: an event with no `rank`, one with a
  non-numeric `rank` (must be dropped, not fatal), and confirmation that a missing/empty `index_dir`
  degrades to `set()`, never an error.
- **`engine/features/search_feature.py`** — `search()` now also calls `analytics.clicked_pages(core.INDEX_DIR)`
  right after the existing `popular_nsns()`/`boosted` block and tags `r["clicked"] = True` for any row whose
  `doc_id:page_number` was opened from a search before. Local `import analytics` (not module-scope), matching
  `routes/search.py`'s own existing call-site-import style for this same module — avoids import-order risk
  with whatever already imports `search_feature` at load time. The stable sort tuple grows a 4th key:
  `(exact, approx, boosted, clicked)` — same shape, one more tier; rows are only ever tagged `clicked=True`,
  never explicitly `False`, matching how `exact`/`approx`/`boosted` already work in this same function. With
  zero click history the new key is a no-op for every row and ranking is byte-for-byte identical to before
  this change — the heuristic is inert until the instrumentation half has actually produced data, by
  construction, not a special-cased guard.
- **`engine/ui/index.html`** — `renderList()` gains a `.badge.opened` (`↺ opened before`, titled "Opened from
  a search result before") next to the existing `.fav` (`★ requested`) badge, shown when `r.clicked` — keeps
  R13 honest for this new ranking tier too (a floated result must say why, never pass as unexplained
  authority). New `logResultClick(r, rows)` fires a fire-and-forget `POST /api/analytics_log`
  (`kind:"click", key:LAST_QUERY, doc, page, rank`) from both places a result is actually opened
  (`d.onclick` and the `.vbtn` button's handler — both already routed through the same `openViewer(r)`),
  wrapped in the same `try{...}catch(_){}` every other beacon in this file/`palette.js` already uses so a
  blocked `fetch` can never break the click's actual navigation. `rank` is the row's index in `rows` —
  `renderList(rows)`'s own parameter, which shadows the outer `shown` — not the outer variable, so rank
  always matches what's actually on screen (confirmed: `renderList` is called as `renderList(shown)`, but the
  parameter name inside the function is `rows`).

### Deviation from the plan
- **`engine/features/routes/search.py`'s `r_analytics_log` DOES need a one-line change**, contrary to the
  design spec's claim that this route is "unchanged" because it's "already generic over kind." That's true
  for `kind`, but the route's own payload extraction hardcodes its extra-field allowlist to
  `("doc", "page", "nsn")` when building the dict it hands to `analytics.log()` — `rank` would never reach
  `analytics.log()`'s (correctly widened) allowlist without also being added here. Fixed by adding `"rank"`
  to that tuple; `analytics.log()` itself still owns all the actual validation/coercion. Caught by writing
  the round-trip regression test first and watching `rank` silently vanish before this fix.

### Adversarial review — a real bug in the test, caught, reproduced, and fixed
Three independent reviewers examined the diff. Two of them, from different angles, converged on the same root
problem in the *test*, not the shipped code:
- The regression test hardcoded its seeded click onto fixture row `doc 3/page 9`, but that row already
  outranks its "tied" twin (`doc 2/page 13`) on plain FTS bm25 alone (shorter page body → higher score for
  the same term count) — the click signal contributed nothing to the observed pass. **Verified directly, not
  taken on the reviewers' word:** deleting the `clicked` term from `search_feature.search()`'s sort key
  entirely and rerunning the whole file still produced `48 passed, 0 failed`, including that exact assertion.
- Compounding it, an *earlier* assertion in the same file's `/api/analytics_log` round-trip check logged its
  own throwaway `"click"` event on that identical fixture row (`doc 3/page 9`) before the "real" test ever
  seeded its own — so even the pre-click "tied" baseline wasn't clean. Also independently reproduced: removing
  the cache-bust line the test's own comment called essential produced byte-identical `PASS` output.
- Same pattern as the `measures.py` vacuous "PARA 5B" test caught earlier this project (`[1.20.0]` below, the
  bare-letter-unit fix) — a test that asserts something true for reasons unrelated to the code it claims to
  cover.

Fixed by (1) moving the round-trip test's example click event off the shared fixture rows entirely (now
`doc 99/page 1`, matching nothing real), and (2) rewriting the regression test to never assume which of the
two tied rows bm25 favors: it reads the real pre-click order first, seeds the click on whichever row is
*naturally behind*, and asserts that row now leads — a test that cannot pass vacuously, because if the click
signal has no effect, the natural loser stays the loser. Re-verified against the same sabotage (`clicked` term
removed from the sort key): the corrected test now correctly **fails** (`47 passed, 1 failed`), then passes
clean once the sort key is restored.

Two further findings were reproduced and consciously left as-is, not fixed, with reasoning:
- **`routes/search.py`'s `_SEARCH_LRU`** (pre-existing, 60s, untouched by this diff) caches the full search
  response and short-circuits before `search_feature.search()` runs again — so a just-logged click doesn't
  affect an identical repeat query for up to 60 seconds. Verified this is symmetric with the already-shipped
  `boosted` signal, not a new gap this diff introduces (the LRU short-circuits before *any* of
  `exact`/`approx`/`boosted`/`clicked` get recomputed, not just the new one) — an accepted, pre-existing
  characteristic of this cache, not a regression.
- **`routes/search.py`'s extra-field allowlist** now accepts `rank` for every event `kind`, not just
  `"click"` — matches the existing (also ungated) treatment of `doc`/`page`/`nsn`, so this is consistent with
  precedent rather than a new inconsistency. Currently inert: no existing caller sends `rank` on a non-click
  event.

### Verified
- `python analytics.py` — self-test passes, including the new `clicked_pages()` coverage.
- `python -m py_compile` clean on `analytics.py`, `features/search_feature.py`,
  `features/routes/search.py`, `tests/test_search_quality.py`.
- **`engine/tests/test_search_quality.py`** (extended, +12 checks) — the existing `/api/analytics_log` →
  `/api/analytics_top` round-trip gains a `kind:"click"` case on a non-fixture doc/page (confirms `rank`
  survives the route into the raw JSONL record). New direct regression test (corrected per the adversarial
  review above): reads the real pre-click order between two genuinely-tied fixture "bolt" rows, seeds a click
  on whichever one bm25 naturally disfavors, busts both the 60s `clicked_pages()` cache and the route's own
  60s search LRU, then re-issues the query through a **real** `/api/search` HTTP call against the live test
  server (not `search()` called in-process) — confirms the clicked row is tagged `clicked=True`, its untouched
  twin is not, and the clicked row now *reverses* its natural order. Run for real: **48 passed, 0 failed.**
  Sabotage-checked: with the `clicked` sort key removed, the same file correctly reports **1 failed**.
- `engine/tests/test_routes.py` — re-run as a checkpoint per the plan (widened `_VALID`/allowlist, no new
  route to add to the blanket sweep): **294 passed, 0 failed.**
- `engine/tests/rps_lint.py ui/index.html` — RPS GATE: PASS (`index.html` stays in its existing "modern
  ES6, by design" bucket; no ES5-required page regressed).
- `engine/tools/check_crlf.py` — clean.

### Deferred (per the design's explicit non-goals — not this round)
Query-similarity-aware click weighting (this ships global per-doc/page click popularity only, mirroring
`boosted`/`popular_nsns()` exactly — no "only float a result for the *same* query it was clicked from" yet);
click recency decay or minimum-click thresholds; click-fraud/bot filtering (single-operator offline tool, not
a real threat model here); wiring this signal into `hybrid.py`'s `fuse()`/`/api/search_hybrid` (nothing in
the shipped UI calls that endpoint); and the actual learned re-ranker itself — this entry produces the
training data and ships a stopgap, training/deploying a real model is future Tier-2 work once real click
volume exists to justify it.

---

## [1.19.0] — 2026-08-25 — Home page nav: Tools menu regrouped into 6 labeled sections, My Bench promoted to top-level

Versioned 1.19.0 rather than 1.18.0 (the next number after this branch's base, [1.17.0]) because a separate,
independently-branched change (search click instrumentation + heuristic re-rank) already claimed 1.18.0 on its
own PR off the same base — this avoids a guaranteed version collision whichever merges to `main` second.

The header's `#toolsPop` "🧰 Tools ▾" dropdown (`engine/ui/index.html`, the only copy of this menu in the whole
UI — no other page duplicates it) had grown to **31 items in one flat, unlabeled list**, loosely broken only by
plain visual separators. User-flagged as "far longer than necessary," especially the 16-item unlabeled block
that mixed identification tools, reference lookups, search modes, and workflow tools together with no
structure. A real, previously-unrelated bug was found in the same file while scoping this: `.menupop` had no
`max-height`/scroll cap at all — a long dropdown could run off the bottom of a short viewport with no way to
reach the rest of it.

### Changed
- **`engine/ui/index.html`** — `#toolsPop` regrouped into 6 labeled sections (Find & identify · Reference ·
  Search modes · Do the work · Learn & audit · Admin), replacing the old plain `.msep` divider `<div>`s with
  a new `.mgrouplbl` group-header style (reuses `.col h2`'s existing uppercase/letter-spacing/`color:var(--sub)`
  treatment, scaled for a dropdown row). Every one of the original 30 remaining links/buttons kept its exact
  href/title/label/emoji — this is a reorganization, not a content rewrite (verified programmatically: 29
  `<a href="/...">` + 1 `<button>` = 30 items across 6 groups, every original href still present, none
  dropped/duplicated).
- **★ My Bench promoted to a new top-level header button**, between Collections and Tools — a personal
  saved-items shortcut people return to constantly no longer costs an extra click through a 30-item menu.
  Matches Collections'/Help's exact `a.ghost` tag/style pattern; carries over its original href/title/label
  unchanged. Confirmed `/bench` appears exactly once in the file (the new header button), not still also
  inside the dropdown.
- **`.menupop`'s missing max-height/scroll, fixed** — but not with a hardcoded CSS constant. Adversarial
  review caught that a fixed `calc(100vh - 90px)` assumes the Tools button sits near the top of a single-row
  header; the header now carries one more permanent top-level item (My Bench), which can push it to wrap to a
  2nd row on a narrower viewport, moving the popup's real on-screen start position down with it — a fixed
  viewport-relative constant can't account for that, so the popup's bottom could still run off-screen in
  exactly the case this fix was meant to cover. **Verified directly, not taken on the reviewer's word**: fixed
  by computing the true available space from the Tools button's actual `getBoundingClientRect()` every time
  the menu opens (`open_()` in the existing accessible-toggle script), with the CSS constant demoted to a
  pre-JS fallback only.
- **Misapplied ARIA role removed** — the new `.mgrouplbl` group headers had inherited `role="separator"` from
  the empty `<div class="msep" role="separator">` divider pattern they replaced, but ARIA's separator role is
  defined for a contentless dividing line, not a labeled heading with real text content; assistive tech isn't
  guaranteed to expose that text as an accessible name under that role. Removed (`#toolsPop` has no
  `role="menu"` to begin with, so this was never part of a coherent ARIA widget pattern) — plain, unstyled
  labeled text is read correctly by default.
- **Dead CSS removed** — `.menupop .msep{...}` was orphaned once every divider in this popup became a labeled
  `.mgrouplbl` instead; confirmed no `class="msep"` element remains anywhere in the file before removing.

### Adversarial review
Three independent reviewers (completeness / interaction-correctness / html-hygiene lenses) examined the diff.
- **Completeness lens: 0 findings** — every original href/label/title/emoji verified preserved, My Bench
  reachable from exactly one place.
- **Interaction lens (MEDIUM, fixed above)**: the max-height header-wrap gap described above.
- **Html-hygiene lens**: caught that my own workflow instructions named the wrong lint script path
  (`engine/tools/rps_lint.py`, which doesn't exist — the real path is `engine/tests/rps_lint.py`); re-ran the
  correct one directly. Also 2 LOW findings (misapplied `role="separator"`, dead `.msep` CSS), both fixed
  above.

### Self-caught regression (during the max-height fix, before commit)
Reformatting `open_()` to a multi-line function (to add the dynamic max-height computation above) broke an
existing, unrelated regression test: `test_uiux_fixes.py`'s `tools_menu_open_calls_threadQuery` does an exact
literal-substring check for `"function open_(){ threadQuery();"` in the page source (guarding that
`threadQuery()` — which threads the current search query into every menu link — still runs first thing on
open). The reformat moved `threadQuery()` onto its own indented line, breaking the literal match even though
the *behavior* was unchanged. Caught by running the full `verify_all.py --snapshot` suite before commit (not
just the files I expected to be affected) — fixed by keeping `function open_(){ threadQuery(); ...}` as the
required literal one-line opener and appending the new logic as additional statements after it, same function,
same behavior.

### Verified
- `python engine/tests/rps_lint.py` (correct path): RPS GATE: PASS.
- HTML well-formedness: fed the whole file through `html.parser` with a start/end tag stack checker —
  zero mismatched or unclosed tags.
- Programmatic count-check: 6 `.mgrouplbl` groups, 29 links + 1 button = 30 items in `#toolsPop`, exactly one
  `/bench` href in the whole file and it's outside `#toolsPop`.
- `git diff --stat`: only `engine/ui/index.html` changed.
- Full `engine/tests/verify_all.py --snapshot`, run directly: **47/47, ALL GREEN** (includes the corrected
  `tools_menu_open_calls_threadQuery` check and a fresh, clean `safeguard verify` — 712/712 files OK).

---

## [1.18.0] — 2026-08-25 — measures.py: labeled bare-letter-unit callouts ("ITEM 489A") no longer misread as measurements
Closes the **labeled** half of the deferred `[1.13.4]` finding: an RPSTL item number's letter-suffix
variant, "489A", reading as "489 Amps". `measures.py`'s `_CALLOUT` guard (added `[1.13.5]` for exactly
this false-positive shape, but scoped only to degF/degC — "FIGURE 5 C"/"TABLE 3 F" misread as bare
temperatures) is generalized to every bare single-letter unit in `_BARE_LETTER_UNITS` (V, A, W, N, L, m,
g, not just F/C): "ITEM 489 A", "TABLE 3 W", "REF NO. 12 C" are just as readable as electrical/force/
weight/length/capacity as a figure/table reference is readable as a temperature — same false-positive
class, same fix. Deliberately does **not** also require whitespace between the number and letter the way
the degF/degC check does — that guard is safe for temperature because a genuine bare reading is
essentially always space-separated ("120 F"), so requiring one costs no real recall; it is **not** safe
to generalize to V/A/W/N/L/m/g, where a fused, no-space reading ("12V", "5A", "60W") is the standard way
this corpus writes electrical/mechanical ratings on nameplates, fuse panels, and spec tables. The
genuinely **unlabeled** case (a bare "489A" with no preceding label word at all) is therefore still
deliberately open — the original reason this finding was deferred rather than blindly patched (no way to
verify a broader fix's recall impact without the real corpus) still applies to that narrower remainder;
see `docs/HANDOFF-NOTE.md`'s "Suggested next" for the precise, current framing.

### Fixed
- `engine/measures.py`: `_CALLOUT`'s single word list is split in two. The universal structural/reference
  words (`figure`/`table`/`tbl`/`item`/`detail`/`sheet`/`view`/`note`/`step`/`paragraph`/`section`/
  `index`/`no.`/`nos.`) now guard every bare-letter unit, not just temperature — none of them are also
  standard nomenclature immediately in front of an electrical/mechanical rating. A new, temperature-only
  `_CALLOUT_TEMP_EXTRA` keeps `grade`/`class`/`type`/`key`/`zone` scoped to degF/degC alone.

### Verified — including a real regression caught by adversarial review, not shipped blind
- **Adversarial review** (two independent reviewers, regex-correctness and scope-honesty angles) against
  the first draft of this fix. **One real, confirmed, medium-severity finding, fixed before this landed:**
  the first draft reused the temperature `_CALLOUT` word list verbatim — including `type`/`class`/
  `grade`/`key`/`zone`, safe for temperature (nobody writes "Type 74 F") but standard, common electrical/
  mechanical component nomenclature ("Type 20A fuse", "Type 60W bulb", "Type 24V power supply", "Class
  30A disconnect switch") that the reused list silently dropped entirely — not quarantined, not flagged,
  just gone, with 100% green tests, since the first draft's own test suite never placed a label word
  directly before a real reading. Reproduced directly (`measures.extract("Install Type 20A fuse F1.") ==
  []`) before fixing via the word-list split above; the exact reproduction is now a permanent regression
  case. Two low-severity findings also fixed: a vacuous test case (`"PARA 5B"` — "B" isn't a recognized
  unit letter at all, so that assertion passed for a reason unrelated to the guard being tested,
  replaced with a real unit letter) and missing V/m coverage in the new test's callout cases.
- `engine/tests/test_extraction.py`'s `test_measures_bare_letter_callout_generalized()`: one case per
  newly-covered letter (not just the four the first draft happened to cover), the direct Type/Class
  regression test above, confirmation the five temperature-only extra words still do their original job,
  recall-preservation cases for both spaced and fused real readings, and a canary case proving the
  unlabeled sub-case is still an honest, undisguised open gap, not silently masked. Every existing
  `[1.13.5]` temperature callout case (`"FIGURE 5 C"`, `"Grade 8 F bolts"`, `"Class 2 C wiring"`, …) still
  passes unchanged.
- Full `engine/tests/verify_all.py --snapshot`: **46/47**. The sole failure is the same pre-existing,
  already-diagnosed `test_ingest_routes.py` environmental flake noted in `[1.16.0]`/`[1.17.0]`, unrelated
  to this change.

### Compatibility (R1)
- Purely a precision fix to `measures.extract()`'s existing behavior — same function signature, same
  return shape. Only ever *withholds* a value the labeled-callout shape would previously have
  misclassified; never invents or alters a genuine reading (R13). No schema, migration, or API change.
- `VERSION` → **1.18.0**.

### Known, deliberately deferred
- The unlabeled bare-letter-suffix case ("489A" with no preceding label) — see this entry's own intro
  and `docs/HANDOFF-NOTE.md`'s "Suggested next" for the full, current reasoning.

---

## [1.17.0] — 2026-08-24 — Vision-Language Page QA: Phase 2 (structured extraction, verification, batch tool, Masterfile integration — catalog §10.1 + §3.12)

Closes out the plan [1.16.0] deliberately deferred (items 10–17 of `docs/superpowers/plans/2026-08-24-
vision-language-page-qa-plan.md`): the "Automatic consumer" — typed structured output, the two-part
self-grounding/OCR-cross-check verification pass, the new `index/pageqa.db` sidecar, `build_pageqa.py` +
`BUILD-PAGEQA.bat`, and wiring the sidecar into `masterfile.py` as a corroborating source. This is the
higher-stakes half of the two-phase split: Phase 1's interactive path only ever showed an answer on
screen; this phase writes **unattended**, so R13 (extractive+cited, fail loud, never fabricate) is load-
bearing here, not decorative — a false-positive `verified=True` row is a real data-quality bug once
`masterfile.py` picks it up. Per the design spec's own framing, this single implementation subsumes both
`docs/EXTRACTION-METHODS-CATALOG.md` §10.1 (vision-language document QA) **and** §3.12 (local-LLM
structured extraction) — the batch consumer needs typed structured output either way, so there is no
separate offline-GGUF/llama.cpp path to build for §3.12; it is the same pipeline.

### Added
- **`engine/vlm.py` gains `ground(image, phrase, _backend=None)`** (v1.5.0) — a NEW, separate, optional
  capability, genuinely different from `ask()`/`describe()`: `ask()`'s own grounding (when a backend
  supports it) always grounds a caption/answer the backend just freshly generated, so it has no way to
  re-check an arbitrary, already-claimed phrase the caller hands in. `ground()` takes exactly that phrase
  and asks "where (if anywhere) is THIS text on the page," with no captioning step of its own — mirrors
  `describe()`'s existing role as a thin convenience wrapper over the same pluggable-backend/graceful-
  degrade contract `ask()` already established. Returns `{available, region, backend, note}`; a backend
  without `ground()` (checked via `hasattr`) means "self-grounding verification unavailable for this
  backend," not an error — `available` stays `True`, `region` is simply `None`. Never raises.
- **`engine/vlm_backend.py` gains `ground(image, phrase)`** (v1.1) — the real implementation `vlm.ground()`
  calls: ONE direct `<CAPTION_TO_PHRASE_GROUNDING>` call using the caller's own already-claimed phrase as
  `text_input`, no captioning step at all (reuses the existing `_load()`/`_run_task()` helpers `ask()`
  already established). Returns the first bbox found, normalized 0-1 exactly like `ask()`'s own `region`,
  or `None` when nothing was located.
- **`engine/pageqa.py` implements `mode="structured"` / `strict=True`** (v1.1) — was a "not yet implemented"
  stub since [1.16.0]. Typed `{type, value, value2, unit}` output extracted from the backend's free-text
  answer via `measures.py`'s **own** extraction (no parallel regex logic — the established, tested way
  this codebase turns free text into typed measurements), gated behind a two-part verification pass before
  `verified` is ever `True`: (1) **self-grounding** — `vlm.ground()` (per the design's explicit resolution,
  **not** a second `vlm.ask()` — `ask()`'s own grounding can only ground text it just generated itself,
  which cannot re-check an already-made claim) re-locates the specific phrase the typed value came from,
  directly on the page image; (2) **OCR cross-check** — that same phrase fuzzy-matched (word-token
  `difflib.SequenceMatcher`, matched-block coverage of the claim's own short side, 0.6 threshold — mirrors
  `dedup.py`'s own 0.6 "meaningfully similar" bar) against this page's own already-stored, already-trusted
  `pages.body_text`, independent of the model's self-consistency. Both must pass or `verified=False`;
  nothing extractable in the answer at all is "nothing to verify," never a fabricated type/value (R13).
  Still never writes anything — verification is a pure function, persistence stays the caller's job.
- **New sidecar `index/pageqa.db`** — own `CREATE TABLE IF NOT EXISTS` schema init (matching
  `dedup.db`/`kg.db`/`masterfile.db`'s pattern, not a `viewer.db` migration): one table,
  `pageqa_extractions`, `UNIQUE(document_id, page_number)` (this tool asks at most one question per
  sampled page), flat `region_x0/y0/x1/y1` columns (not embedded JSON, matching every other typed sidecar
  in this codebase), `verified INTEGER NOT NULL DEFAULT 0` kept explicit even though only `verified=1` rows
  are ever written, `backend`/`extracted_at` provenance columns.
- **`engine/build_pageqa.py` + `BUILD-PAGEQA.bat`** (new) — the batch driver, structurally mirroring
  `build_dedup.py`/`DEDUP.bat` in spirit but not byte-for-byte: samples pages where
  `measures.py`/`tables.py`/RPSTL found **nothing** and `ocr_confidence >= 0.5` (reusing `coverage.py`'s
  own "too garbled to be worth a look" threshold verbatim, not a fresh guess), asks ONE generic sweep
  question per page (`mode="structured", strict=True`; the design's own "one sweep question vs. one
  templated question per field type" open item, resolved here — `measures.py`'s `extract()` already
  recognizes the full type taxonomy from whatever text comes back, so one open question is enough signal
  for this phase), and writes only `verified=True` rows. `--max-pages N` is a **required** budget cap, not
  an unbounded corpus sweep (`--max-pages 0` is a valid dry run: reports the candidate count, writes
  nothing). Idempotent re-run: `INSERT OR REPLACE` keyed on the table's own `UNIQUE(document_id,
  page_number)`, and the candidate query itself excludes pages already verified-and-written on an earlier
  run, so repeated invocations make forward, resumable progress without re-asking. Checks
  `pageqa.available()` up front and exits cleanly (code 2) if unavailable — mirrors `build_tables.py`'s own
  missing-optional-dependency precedent (the real sibling here, not `build_dedup.py`, which has no optional
  dependency of its own to gate on). This repo's CI runners (no GPU, no downloaded Florence-2 weights)
  always take this path.
- **`engine/masterfile.py`** (v1.2.0) — `build()` gains an optional `pageqa_db` parameter (appended after
  `md_path`, so every existing positional call site keeps working unchanged): when present, verified
  `pageqa.db` rows are merged in as a corroborating source tagged `origin='vlm-verified'`, doc/page-cited
  to the real TM file exactly like `corpus` rows, and deduped by the **same** cross-doc same-`tm_number`
  duplicate-ingestion guard `corpus` rows already use ([1.15.0]'s corroboration-count fix). Kept as its
  **own** `(subject,type,unit,origin)` group, never merged into `corpus` — it must never silently inflate
  or override a regex-extracted value's own count/note/confidence badge (R13). Degrades exactly like
  `measures_db`/`enrich_db`: an absent/missing `pageqa.db` (the common case before an operator has ever
  run `BUILD-PAGEQA.bat`) contributes nothing, never raises. `WHERE verified=1` on the read query is
  defense-in-depth, not the only gate — `build_pageqa.py` itself never writes an unverified row. The raw
  vlm-verified count is tracked in `master_meta` (`k='vlmqa_raw'`), deliberately **not** added to `build()`'s
  own return dict — `test_medium_fixes.py`'s streaming-equivalence diff-oracle compares that exact dict via
  plain `!=` against a from-scratch reference dict that predates `pageqa.db`, and an extra key would break
  that comparison for a count the oracle never claimed to compute.
- **`engine/build_masterfile.py`** (v1.2.0) — wires a new `PAGEQA_DB` env var (default
  `index/pageqa.db`), reports its presence/absence alongside `measures.db`/`enrich.db` in the startup
  banner, and prints the `vlm-verified` raw count (read back from `master_meta`) in the summary line.
- **`engine/verifystate.py` / `VERIFY.bat`** — `pageqa` added to `SELFTEST_MODULES` / gate 6's self-test
  loop (its self-test is pure/injectable-fake-backend, no `torch`/`transformers` import at module scope,
  so it runs clean in this repo's no-GPU CI same as every other entry). `vlm_backend` is deliberately
  **not** added — its own self-test docstring already says `import vlm_backend` itself raises before
  `__main__` is ever reached on a machine without `transformers`/`torch` (every CI runner), so it cannot
  degrade to "test what's installed." `build_pageqa.py` is also deliberately **not** added, matching
  `build_dedup.py`'s own precedent — confirmed directly: no `build_*.py` driver that needs a real populated
  `viewer.db` to do anything meaningful appears on this roster or in any `VERIFY.bat` gate.

### Verified
- `python vlm.py`, `python pageqa.py`, `python masterfile.py`, `python verifystate.py` — all four
  self-tests pass in this no-GPU/no-`transformers` environment. `pageqa.py`'s now covers **five**
  structured/strict verification cases (see the adversarial-review finding below for the fifth):
  agreeing self-grounding + OCR cross-check → `verified=True`; failed self-grounding alone →
  `verified=False`; grounding succeeds but the phrase-level OCR cross-check fails (an off-topic/
  fabricated claim) → `verified=False`; nothing extractable in the answer at all → `verified=False` with
  a clear note and grounding never even attempted; **a hallucinated numeric VALUE inside an otherwise-
  correct, page-matching sentence → `verified=False`**, reproducing and closing the exact gap adversarial
  review found live. `masterfile.py`'s covers `pageqa_db` omitted, `pageqa_db` pointing at a not-yet-built
  path, and a real populated `pageqa.db` — including the cross-doc same-`tm_number` duplicate-ingestion
  case, confirming an unverified (`verified=0`) row never reaches the Masterfile, and (adversarial-review
  fix, see below) that a `vlm-verified` row's `page_url`/`counts` entry is populated exactly like a
  `corpus` row's. `verifystate.py`'s own self-test additionally confirms its module roster matches
  `VERIFY.bat` gate 6 exactly.
- `python build_pageqa.py --max-pages 0` — degrades cleanly: reports the vision-language backend
  unavailable and exits code 2, without touching `viewer.db` or any sidecar, matching
  `build_tables.py`'s own missing-optional-dependency precedent.
- **`engine/tests/test_pageqa.py`** (new, 28 checks) — real e2e, not just injectable-fake self-tests: a
  genuine tiny PDF fixture (known torque text) ingested through the real `viewer_ingest.py` pipeline, a
  mocked backend selected via `VIEWER_VLM`, run through the real `build_pageqa.py` as an actual
  subprocess. Confirms a verified row lands in `pageqa.db` with the right document/page/type/value,
  confirms nothing is written when self-grounding fails, confirms nothing is written when the OCR
  cross-check fails, and confirms a subsequent `masterfile.py` build picks the verified row up. Run for
  real: **28 passed, 0 failed** (also re-run clean after the adversarial-review fixes below, confirming
  neither broke the existing fixtures).
- **`engine/tests/test_masterfile_robustness.py`** (extended, +5 checks) — a `pageqa_db` that doesn't
  exist yet, and one that exists but is torn/pre-schema, both degrade cleanly (no raise, the rest of the
  build still succeeds, the corpus's own groups stay intact). Run for real: **21 passed, 0 failed**.
- `py_compile` clean on every touched/new module (`vlm.py`, `vlm_backend.py`, `pageqa.py`, `masterfile.py`,
  `build_masterfile.py`, `verifystate.py`, `build_pageqa.py`).
- Full `engine/tests/verify_all.py --snapshot`, run after every fix below was applied: **46/47** (47, not
  46 — `test_pageqa.py` is a new suite this entry adds). The sole failure is the same pre-existing,
  already-diagnosed `test_ingest_routes.py` `safeguard.snapshot()` environmental flake noted in [1.16.0],
  unrelated to this change.
- **Adversarial review (3 independent reviewers — verification correctness, convention-consistency,
  CI-safety) against the diff and the design spec/plan, weighted toward whether `verified=True` is
  actually unreachable for a bad claim.** Two real, confirmed findings, both fixed directly:
  - **(High) The OCR cross-check alone could not catch a hallucinated numeric value.** `_ocr_overlap()`
    scores every word in a claimed phrase equally — reproduced live: `_ocr_overlap("Bolt torque is 35
    N-m. Torque wrench required for reassembly", "Bolt torque is 22 N-m. Torque wrench required for
    reassembly.")` scores **0.909**, comfortably above the 0.6 threshold, because the boilerplate wording
    around the number dominates a short claim — the actual digit (35 claimed vs. 22 real) barely moves the
    score. Fixed: new `_value_grounded()` requires every token of the claimed `value`/`value2` to appear,
    as its own literal word-token, in the page's real OCR text — not a coverage fraction, no partial
    credit for a wrong digit. Both `_ocr_overlap()` **and** `_value_grounded()` are now required for
    `verified=True`; a new self-test case (`s5` in `pageqa.py`) pins this exact reproduction as a
    permanent regression check.
  - **(Low) `masterfile.for_subject()` didn't treat `vlm-verified` rows as page-cited**, even though they
    demonstrably are (real `document_id`/`page_number` on every written row) — `page_url` and `counts`
    both only recognized `origin == "corpus"`. Fixed: both now include `vlm-verified` alongside `corpus`,
    with a new regression case in `masterfile.py`'s own self-test.
  - A third finding (this entry's own "Known, deliberately deferred" section had gone stale mid-workflow,
    claiming `test_pageqa.py`/the masterfile robustness case weren't added when they actually were, by a
    parallel workflow stage the docs stage didn't see) is corrected in this entry directly rather than
    listed as a separate fix.

### Compatibility (R1)
- `masterfile.build()`'s new `pageqa_db` parameter is optional and keyword-appended after `md_path` —
  every existing call site (`build_masterfile.py`'s prior invocation shape, every test in this suite)
  keeps working unchanged; omitting it degrades exactly like omitting `measures_db`/`enrich_db` already
  does.
- No `viewer.db` migration (next would be `0013_*.sql`) — `pageqa.db` is a standalone sidecar with its own
  schema-init, matching `dedup.db`/`kg.db`/`masterfile.db`'s existing pattern, not the migration one (R6).
- `vlm.ground()`/`vlm_backend.ground()` are purely additive — `ask()`'s own contract, and every existing
  caller of it (`/api/vlm`, `/api/pageqa`'s Phase-1 text-mode path), is completely untouched.
- No new required dependency — `build_pageqa.py` uses the exact same `transformers`/`torch` optional
  install Phase 1 already documented; nothing new is added to `requirements.txt`.
- `VERSION` → **1.17.0**, matching this project's own established practice of bumping `VERSION` with every
  changelog entry (see [1.16.0]'s own confirmation of this precedent). Not a claim of any behavior change
  on a machine without the optional `transformers`/`torch` dependencies installed — every code path here
  degrades exactly as it did before this change on such a machine, `build_pageqa.py` included.

### Known, deliberately deferred
- `masterfile._confidence()`'s badge text is unchanged: a `vlm-verified` row's `authoritative` flag is
  `0` (only `origin == "corpus"` sets it), so it currently reads `note="external reference — unconfirmed"`
  / `confidence="low"` — the same badge an `enrich.db` web-crawled value gets, despite having actually
  passed self-grounding + an OCR cross-check. This is the design spec's own explicitly-unresolved open
  item ("whether `masterfile._confidence()` needs a new label for `vlm-verified` provenance, or reuses
  'high — cited & corroborated' once ≥1 other source agrees") — left open on purpose, not an oversight.
- A live check of `build_pageqa.py` against a real Florence-2 install on actual GPU hardware has not been
  performed — same caveat as Phase 1: this environment has neither a GPU nor the optional dependencies
  installed.
- Exact prompt-template wording, the Florence-2 quantization/precision level, and the OCR cross-check's
  fuzzy-match parameters were all explicitly out of scope for this design — see the spec's own
  "Non-goals" section (the 0.6 threshold and single-sweep-question choices above are this phase's own
  resolutions of the plan's "open items," not the design's).

---

## [1.16.0] — 2026-08-24 — Vision-Language Page QA: Phase 1 (interactive "Ask this page", catalog §10.1)

Closes the single highest-ceiling, longest-unbuilt gap the extraction-methods catalog itself flags: §10.1
vision-language document QA. Every other extractor (`measures.py`, `tables.py`, RPSTL, …) is a
regex/geometry pipeline that can only find what it was specifically built to look for; a vision-language
model can be asked a page directly — "what's the torque value here?" — and answer questions no existing
extractor covers. `engine/vlm.py` has carried the pluggable `ask(image, question) -> str` interface since
v1.3.3, but shipped with **no backend** — an honest stub, never a real feature. This entry completes it
into a genuine, two-consumer system, per `docs/superpowers/specs/2026-08-24-vision-language-page-qa-
design.md` and its companion implementation plan. **Phase 1 only** — interactive, ephemeral, writes
nothing to any sidecar. Phase 2 (typed structured extraction, the self-grounding/OCR-cross-check
verification pass, and the batch tool that would write corroborating rows into a new `index/pageqa.db`
for `masterfile.py` to consume) is deliberately deferred — see "Known, deliberately deferred" below.

### Added
- **`engine/vlm.py` widened `ask()`'s return contract** (v1.4.0) — a backend may now return either a bare
  string (every backend before this, and any that still doesn't ground) or a
  `{"text": ..., "region": {"x0","y0","x1","y1"}}` dict for backends that support native grounding
  (coordinates normalized 0-1). 100% backward compatible: `region` is always optional, `GET /api/vlm`
  (whose only caller understands a bare string) is completely untouched, and `ask()` itself still never
  inspects or coerces the shape — it just passes the backend's return value through, exactly as it always
  has.
- **`engine/vlm_backend.py`** (new) — the real, shipped default backend: `microsoft/Florence-2-base` via
  `transformers` (`AutoModelForCausalLM` + `AutoProcessor`, `trust_remote_code=True` — Florence-2 ships
  its own modeling code). Lazy model load, mirroring `embed.py`'s own convention: importing this module
  needs only the `transformers`/`torch` *packages* installed, never touching the network or the ~460MB
  weights until the first real `ask()` call. Florence-2 has no native open-ended VQA task prompt, so this
  ships the official cascaded pattern from its own model card instead: `<MORE_DETAILED_CAPTION>` the
  whole page, then `<CAPTION_TO_PHRASE_GROUNDING>` that caption's noun phrases back onto the page, and
  take the grounded phrase whose words overlap the asked question the most as the "answer" — a documented
  approximation of VQA, said plainly in the module's own docstring so nobody mistakes it for real
  instruction-following (R13). Advanced/GPU-fork-only optional dependency, same posture as
  RapidOCR-on-`onnxruntime-gpu`.
- **`engine/pageqa.py`** (new) — the shared core both consumers below call, so neither reimplements
  trust-tier logic independently (mirrors how `cautions.py` already shares `textquality.annotate()`
  rather than recomputing text quality itself). This phase implements only `mode="text", strict=False`:
  resolve doc/page → a rendered page image, call `vlm.ask()`, fold its widened str|{text,region} contract
  into one `(answer_text, region)` shape, and **hard-cap trust at `trust.py`'s "review" tier no matter
  what the backend claims** — a human is looking at the actual page right there, so this is a second pair
  of eyes, never a verified fact (R13). Its own `available()` is checked *before* any model-load attempt:
  requires both `vlm.available()` and `sysprobe.py`'s GPU-capable tier, so a legacy/no-GPU machine — and
  this repo's own CI runners, which have neither a GPU nor downloaded model weights — report `available:
  False` cleanly and cheaply. `mode="structured"`/`strict=True` already exist in the function signature
  (so Phase 2 lands additive, not a breaking rework) but for now just return a clean "not yet
  implemented" note rather than raising.
- **`GET /api/pageqa`** (new route, `doc_extractors.py`) — a thin wrapper calling `pageqa.ask()` directly.
  `GET /api/vlm` stays completely unchanged (R1).
- **`engine/ui/deepzoom.html`**: a floating "🔎 Ask this page" control (the same pattern the
  Editions/Symbols buttons already use) — a question box, a canvas-drawn highlight for the model's
  grounded region, a trust chip drawn from `trust.py`'s own color/label vocabulary, and the disclaimer
  "AI-read — verify on page." shown verbatim from `pageqa.py`'s own note text. The button stays hidden
  unless a lightweight capability probe (`GET /api/pageqa?mode=text`, no real doc/page) reports
  available — the same simply-absent-on-hardware-that-can't-run-it gate RPS Premium already uses. Nothing
  is ever persisted — answer-and-forget, matching `ask.py`'s own existing contract.
- **`engine/ask.py` / `engine/ui/ask.html`**: when extractive sentence-scoring finds **no** answer at all
  for a question, `answer()` now falls through to `pageqa.ask()` on the single top-retrieved page. This
  comes back under its own `vlm_fallback` key — **never** folded into `sentences`/`sources`, and never
  allowed to flip `answered` to `True` (R13: an AI-sourced value must never visually pass as an
  extractive citation). Rendered in its own distinctly-badged block in `ask.html`; silently absent
  whenever `pageqa` is unavailable or has nothing to say.

### Verified
- `python vlm.py` and `python pageqa.py` — both self-tests pass in this no-GPU/no-`transformers`
  environment (this repo's own CI has neither either): graceful degrade with no backend installed,
  bare-string and grounded-dict `vlm.ask()` shapes both handled, the "review" trust-cap holds even with a
  grounded region, a backend that errors mid-call and an unknown `mode` both degrade cleanly, and
  `mode="structured"`/`strict=True` correctly report Phase 2 as not-yet-implemented instead of crashing.
- `tests/test_routes.py`'s blanket GET/POST sweep extended with `GET
  /api/pageqa?doc=2&page=12&q=torque`, exercising the exact no-backend-installed degrade path CI runs.
- `tests/rps_lint.py` — `ask.html` and `deepzoom.html` both still ES5-clean; full gate: **PASS**.
- Full `engine/tests/verify_all.py --snapshot`: **45/46**. The sole failure, `test_ingest_routes.py`'s two
  "real e2e upload" checks, is a pre-existing, already-diagnosed environmental flake tied to
  `safeguard.snapshot()` disk contention specific to this working copy — independently reproduced as
  absent in a clean clone earlier this same session — and unrelated to this change.
- Direct real-world check beyond the self-tests: `import vlm_backend` fails cleanly with
  `ModuleNotFoundError: No module named 'torch'` in this environment, and that failure is fully absorbed
  by `vlm.available()` → `False` with zero effect on `import vlm`/`import pageqa`.
- Adversarial review (3 independent reviewers — correctness, convention-consistency, CI-safety) against
  the diff and the design spec/plan all converged on the same real finding: `transformers`/`torch` had
  been placed in `requirements.txt`'s auto-installed RECOMMENDED tier, contradicting the spec's own
  "Advanced/GPU-fork-only optional dependency" posture and risking CI actually installing multi-GB deps
  on every push/PR. Fixed — moved to the commented-out OPTIONAL tier (matching `easyocr`'s own
  precedent), restoring the "CI has neither package installed" invariant the tests/docs above depend on.

### Compatibility (R1)
- `vlm.py`'s `ask()` contract change is purely additive — every existing caller (`/api/vlm`) still only
  ever sees a bare string back, since `vlm_backend.py`'s v1.4.0 dict shape is new, not retrofitted onto
  any prior backend.
- No schema/migration change and no new sidecar in this phase (R6) — `pageqa.py` opens nothing but a
  short-lived read-only connection to resolve a doc id to a file path, and writes nothing anywhere.
- `engine/vlm_backend.py`'s two heavy imports (`torch`, `transformers`) are deliberately unguarded at
  module scope — `vlm.py`'s `_load_backend()` already isolates a missing/failed import via
  `__import__()` + `try/except`, so `import vlm` and `import pageqa` never require them installed; only
  `import vlm_backend` does.
- `VERSION` → **1.16.0**, matching this project's own established practice of bumping `VERSION` with
  every changelog entry — confirmed via `git log -p` on `engine/viewer_app.py`'s `VERSION` line back
  through [1.13.2], plus this file's own explicit bump lines further back (e.g. [1.7.1]: "`VERSION` →
  **1.7.1**. Test-only + tooling; no app-behavior change (R1)."). Not a claim that this entry changes
  behavior on a machine without the new optional `transformers`/`torch` dependencies installed — on such
  a machine every code path here degrades exactly as it did before this change.

### Known, deliberately deferred
- **Phase 2 — structured extraction, verification, and the batch tool** is not built yet: typed
  `{type, value, value2, unit, region, source_text}` output reusing `measures.py`'s own type taxonomy,
  the two-part self-grounding + OCR-cross-check verification pass, the new `index/pageqa.db` sidecar,
  `build_pageqa.py` + `BUILD-PAGEQA.bat`, and wiring `pageqa.db` into `masterfile.py`'s source list as a
  `source='vlm-verified'` corroborating input — tracked as items 10–17 in the implementation plan.
  Nothing in this phase writes to any sidecar; `docs/EXTRACTION-METHODS-CATALOG.md` §10.1 stays at
  **◐** (partial), not ✅, until Phase 2 lands.
- Exact prompt-template wording per extraction type, the Florence-2 quantization/precision level, and the
  Phase-2 fuzzy-match parameters are all explicitly out of scope for this phase — see the design spec's
  own "Non-goals" section.
- A live check of the "Ask this page" control against a real Florence-2 install on actual GPU hardware
  has not been performed — see "Verified" above for what was: this environment has neither a GPU nor the
  optional dependencies installed.

---

## [1.15.0] — 2026-08-19 — Discovery Engine phase 1 + in-app scanning, 5 deferred items closed, RPS Premium tier, OCR confidence threaded end-to-end, full-codebase reachability audit
30 commits, 2026-08-18 20:40 → 2026-08-19 21:41 (~25 hours, effectively one continuous session) — the
largest single body of undocumented work this file has ever carried at once, and itself a fresh instance
of the drift [1.14.0] documents at length: `docs/CHANGELOG.md` sat at [1.14.1] while `main` moved 30
commits further, `VERSION` stayed `"1.14.1"`, and `docs/HANDOFF-NOTE.md`/`PROJECT-SUMMARY.md`/
`MASTER-RECONCILIATION.md` were all still pinned to [1.14.0]. This entry reconciles `CHANGELOG.md` only —
those three still need their own pass (tracked in `docs/HANDOFF-NOTE.md`'s "Suggested next"). **`VERSION`
→ `1.15.0`.**

### Added — Discovery Engine phase 1 + in-app scan/OCR (`05ff17f` → `85df23c`)
- **Add Documents runs scan+OCR+parts as one in-app job** (`05ff17f`): `ingest_start()` now launches
  `viewer_ingest.py`'s full `run` subcommand (crawl → ocr-until-drained → extract_parts) instead of the
  old crawl-only path — closes the "go run START-OCR-NOW.bat yourself" gap. New `ocr_backlog_start()` +
  `POST /api/ocr_backlog_start` finishes OCR already queued from an earlier crawl-only run, sharing the
  same one-job-at-a-time lock; requires `confirm:true` since it has no other required body field — caught
  live: `test_routes.py`'s generic empty-body POST sweep was silently launching a real subprocess + taking
  a real `safeguard.snapshot()` every test run before this gate existed. New atomic `ingest_progress.json`
  sidecar (`_write_progress()`) drives a real 4-stage progress panel (Scanning → OCR'ing → Extracting parts
  → Done) in `ingest.html`, including through an OCR-engine failure, not just success.
- **Drag-and-drop single-file upload** (`26a2f56`): new `ingest_upload(filename, data_b64)` decodes,
  validates (extension, base64, `%PDF-` magic header, 150 MB cap), saves into a server-owned `uploads/`
  folder (suffixed not overwritten on a repeat name), and launches the same `run` job. New
  `POST /api/ingest_upload` + a `do_POST` size-cap exception scoped to just this route (200 MB vs. the
  normal 8 MB). A process-lifetime `_EXTRACT_TALLY` accumulator feeds a live "where did my data go"
  breakdown panel (documents/pages/parts/barcodes, each linking to where that data actually lives).
- **Dimensional + schematic detection wired into the live scan** (`701fb41`): `measures.py`/
  `specparse.py`/`leadingspecs.py` and `schem_overlay.py`/`schemgraph.py` were fully built, self-tested
  batch-only tools with zero live callers; new `_extract_measures_for_page()` and a 4th pipeline stage
  `_run_schematic_stage()` (new `schematics` table, migration `0011_schematics.sql`) wire both in, scoped
  to documents the current run actually touched. `part_differences()` gains a live "dimensions" discriminator
  citing real per-variant measurement values.
- **`index_other()`: crawl() actually reads images/.txt/.html now** (`85df23c`) — before this, a non-PDF
  file was marked `indexed`/0 pages and never read at all. Images are queued as a single OCR page (PyMuPDF
  already opens a raw image as a 1-page document, so the entire existing OCR/barcode/dimensional pipeline
  runs on it for free); `.txt` read directly (2 MB cap); `.htm`/`.html` tag-stripped via a new
  dependency-free regex stripper. `tables.py`'s `find_tables()` becomes a live 5th pipeline stage
  (`TABLES_SCAN` toggle) — it had been stranded the same way. Genuine Office formats stayed unsupported
  here (closed two commits later, see below).

### Added — Full-codebase reachability audit: RPSTL/pagetrim/keywords wiring + `flags.py` registry (`099737f`, `e9eee88`)
- **RPSTL parts-list rows, pagetrim boilerplate stripping, and an automatic keywords.json refresh**
  (`099737f`): a 6-agent sweep of ~90 root-level modules against every route/pipeline caller — the same
  "built but never wired in" bug class already fixed for measures/schemgraph/tables — found three more
  genuine gaps. New 6th pipeline stage `_run_rpstl_stage()` runs `rpstl_feature.parse_page()` (the same
  parser `build_rpstl.py` uses) directly over already-stored page text. `pagetrim.clean_pages()` finally
  gets called from `index_pdf()` for text-layer pages (OCR'd pages deferred — closed in `d5fb9f8` below); a
  real correctness catch along the way: TM-number/title detection now reads from a separately-computed raw
  pre-strip string, since the running header pagetrim removes is exactly what document-identification
  depends on. `build_keywords.py`'s `main()` became an importable `run()`, now called automatically from
  `enrich_flis()` instead of needing a remembered second manual step.
- **`engine/flags.py`** (`e9eee88`): centralizes the 8 extraction-pipeline opt-out toggles
  (`VIEWER_OCR_PREPROCESS`/`BARCODE_SCAN`/`MEASURES_SCAN`/`SCHEMATIC_SCAN`/`TABLES_SCAN`/`RPSTL_SCAN`/
  `PAGETRIM_SCAN`/`KEYWORDS_SCAN`) into one live (not snapshotted) registry — `python viewer_ingest.py flags`
  now introspects current state, and `ingest_progress.json` bakes in a `flags_off` list automatically at
  every stage. `docs/SYSTEM-REQUIREMENTS.md` gained the section documenting all 8 that never existed before.

### Added — Five deferred items closed (`ee3714d` → `d5fb9f8`)
- **`tables_plus.py`'s `stitch()`** wired into `/api/tables_plus?stitch=1` for cross-page borderless-table
  merging (`ee3714d`); **`engine/office.py`** (new) adds real `.docx`/`.xlsx`/`.pptx`/`.rtf` text extraction
  via python-docx/openpyxl/python-pptx, tier-gated to `sysprobe.py`'s `modern_os` signal since python-docx
  needs Python 3.9+ (this app's floor is Win7/3.8) — off that tier these still discover with 0 pages, same
  as still-unsupported legacy `.doc`/`.xls`/`.ppt`. A real bug caught mid-implementation: the RTF stripper's
  brace-depth walk double-pushed a skip level for `\*\generator`, silently blanking the rest of the document.
- **`dedup.py` gains a persistence layer** (`97ef29b`): `build()`/`editions_for()`/`stats()`, a new
  `build_dedup.py` batch driver + `DEDUP.bat`, `GET /api/editions`, and a "📚 Editions" button in
  `deepzoom.html` that only appears when a document actually has clustered siblings.
- **`symbols.py`'s missing template-sourcing UI** (`03f1d57`): three new routes
  (`/api/symbols`, `/api/symbols_template`, `/api/symbols_page_image`) plus a crop-and-save modal in
  `deepzoom.html` — before this, teaching the app a new symbol template required hand-cropping a PNG and
  dropping it into `index/symbols/` outside the app entirely. Verified live end-to-end via real dispatched
  mouse events selecting a region, saving it, and the next detection pass finding both instances.
- **`pagetrim.py`'s OCR-page path** (`d5fb9f8`) — the last of the 5: new `_run_pagetrim_ocr_stage()` runs as
  the 7th and final pipeline stage over a touched document's full page set (OCR'd pages arrive one at a time
  in `ocr()`, which never has the whole-document list `clean_pages()` needs to detect what recurs).

### Added — RPS hardware-adaptive engine: Premium tier + deepen/widen (`bdc17cd`, `735455f`)
- **`Premium`**: a 4th Settings run-mode choice (`bdc17cd`), an opt-in visual layer (elevation shadows,
  motion timing, hover-lift, accent glows — all scoped under `body.rps-premium`) that only ever activates
  on top of an already-`modern`-capable machine; a weaker machine gets an explicit fallback reason, never a
  silent downgrade. `VALID_MODES` stays exactly `(modern, lite, legacy)` — this is a UI-intent layer on top,
  not a 4th engine mode.
- **RPS deepen + widen** (`735455f`): 9 real gaps closed where the hardware-tier flags RPS already computes
  went unread — `viewer_ingest.py`'s `--workers`/`--dpi`/`--gpu` now default to a `sysprobe.py`-resolved
  profile instead of a flat guess; `embed.py` `mmap`s the embeddings array on lite/legacy instead of a full
  ~293MB in-memory copy; `_BoundedThreadingHTTPServer`'s worker ceiling now branches on `RPS_MODE`, not just
  core count; `features/routes/page_render.py`'s DPI clamp finally reads `RPS_FLAGS["render_dpi_cap"]` (a
  legacy machine could previously trigger a full-page render at 2.7x its intended cap). A real bug caught
  along the way in `ocr_supervisor.py`: the watchdog's `--max-age` floor had zero safety margin against a
  healthy pass's own worst-case heartbeat gap — raising the per-page OCR timeout without it would have
  caused an infinite kill/requeue/restart loop.

### Added — Airgap NIIN-decision sync, weekly DB backup, and a mechanical reachability checker (`875ffd5`, `822d830`, `72e1797`)
- **`airgap.py`**: `export_decisions()`/`import_decisions()` sign and fail-closed-verify a batch of
  `reviews.db` NIIN review decisions for transfer between air-gapped units — a genuine disagreement is
  surfaced as a conflict and never auto-resolved. New `POST /api/airgap_export_decisions` /
  `/api/airgap_import_decisions`, an "Air-gap transfer" panel on `/ingest`, and `BUILD-AIRGAP-MANIFEST.bat`/
  `VERIFY-AIRGAP-BUNDLE.bat`. Two real bugs caught live testing the `.bat` wrappers end to end: the verify
  script's exit code never propagated past its own `pause`/`endlocal` sequence (a REJECT verdict still
  returned 0), and a PowerShell `>`-redirected manifest's UTF-8 BOM was rejected outright by `json.load`.
- **Weekly full `viewer.db` backup** (`822d830`): the multi-GB searchable index was never covered by any
  automatic task — only the source-file snapshot vault was. `register_snapshot_task.bat` now also registers
  `THE_VIEWER_WeeklyDBBackup` (Sunday 03:00, `safeguard.py backupdb --auto`), and new `run_backupdb.bat`
  gives a manual entry point.
- **`audit_features.py` [7]: an AST import-closure reachability checker** (`72e1797`) for the exact
  "built but never wired in" bug class that recurred across at least 9 commits in this project's visible
  history (measures/schemgraph/tables/RPSTL/pagetrim/keywords/tables_plus-stitch/Office-formats/dedup were
  all found orphaned at some point) — `verifystate.py`'s self-test roster only ever asked "does it have a
  self-test", never "is it reachable from production"; this asks the second question mechanically via a BFS
  import closure rooted at `viewer_app.py`/`viewer_ingest.py`, plus `.bat`-invocation detection.

### Added — Masterfile comparison audit + dedup performance (`40a811b`, `299629b`, `ddbc302`)
- **`masterfile.py`**: the representative value for a group of corroborating measurements was the most-common
  exact value *string* — for continuous measurements that's almost always an arbitrary first-seen tiebreak
  dressed as agreement (confirmed live: 3 real docs at 180/180.5/179.8in produced `value='180'` purely
  because that doc crawled first). Now the numeric median of everything in the group that parses as a
  number. `build()` now builds via `safeguard.atomic_sqlite_build()` instead of a live DROP+CREATE.
  Separately, `_confidence()`'s "high — cited & corroborated" badge counted raw row count with no dedup by
  document/edition, so two duplicate ingestions of one misread page could earn the safest-looking badge off
  a single uncorrected error — corroboration is now deduped by `(tm_number-or-doc-id, page)` first.
- **`dedup.py`/`build_dedup.py`**: `find_duplicates()` compared every document against every other
  unconditionally — at the real corpus scale (39,683 docs) that's ~787M pairwise comparisons and an
  estimated 8-10GB+ upfront, against this app's documented <8GB legacy-tier floor. New `block_key(tm_number)`
  buckets by TM family (stripping the trailing volume/change suffix) before comparing, plus a
  `--max-docs-per-bucket` cap on the batch driver.

### Fixed — Functions + security pass: 52 confirmed fixes across every route cluster (`c147614`)
A dedicated audit of all 265+ routes plus two security-specific angles (network exposure; injection/
traversal/durable-write) — 51 confirmed / 2 refuted, 52 fixed. Security highlights: `Handler._dispatch()`
used bare `None` as both its "this is a GET" sentinel and a value a POST body can legitimately carry
(`json.loads(b"null")`), so a literal JSON `null` POST 500'd instead of getting the route's own clean 400 —
fixed with a private sentinel object `json.loads` can never produce. `POST /api/airgap_verify` never
enforced the `VIEWER_INGEST_ROOTS` fence its sibling manifest route already had. `GET /api/ingest_preview`
leaked real host paths in exposed mode, missing the guard its sibling `/api/ingest_status` already enforced.
`cad_render.py`'s cache writes moved to `safeguard.atomic_write()` (a crash mid-write could leave a
truncated file served as "cached" forever). `ingest_start()`'s check-then-act race (two concurrent
`POST /api/ingest` calls both launching a crawl against the same DB) closed with a module lock. Correctness
highlights: `dimscan.py` indexed `cv2.HoughLinesP`'s result assuming the pre-5.x shape, silently returning 0
lines under the installed opencv-python 5.x. `hybrid.py`'s RRF fusion read the wrong dict key for keyword/
FTS rows' page number, silently collapsing distinct pages onto one fusion key. `tmrev.py`'s revision matcher
used a 12-char TM-number prefix — exactly the shared weapon-system segment — wrongly treating e.g. the parts
manual and the unit-maintenance manual for the same platform as revisions of each other. `measures.py`'s
digit-run cap silently truncated an impossible 7+-digit value into a wrong-but-plausible shorter one before
`validate.py`'s garbled-value quarantine ever saw it. Four new test files close real gaps, including the
first-ever HTTP coverage for both airgap security routes.

### Fixed — Icon/emblem quality pass: 7 palette collisions + 32 verified UI fixes across 20 files (`4b3224c`)
`palette.js`'s 51-entry command inventory had 7 genuine duplicate-glyph collisions (two-to-three unrelated
commands sharing one emoji), each resolved and cross-checked so no swap created a new collision, then synced
into every affected page's own header/cross-link icon. A follow-up workflow-audited pass (30/31 candidates
verified live, 1 refuted via real `getBoundingClientRect()` measurement) fixed stale cross-references, a
genuinely-wrong Unicode codepoint on `procedure.html`'s hammer icon, and — separately — a real kiosk-mode
touch-target gap: `dossier.html`/`partdiff.html`'s header links used plain `nav` styling instead of `btn`,
excluding them from the 44px touch-target rule (invisible with a mouse, a real glove-mode bug on a bay
tablet); `packet.html` linked no stylesheet at all, so kiosk-mode never applied to a page whose entire
purpose is print/export in the field.

### Fixed — Barcode lost on an OCR text-engine failure (`54d2546`)
Caught by CI on its very first real run against the barcode-wiring pipeline, not by hand: `ocr_one()`
computed a barcode read independently of (and before) the OCR text engine, but when the text-engine call
itself raised, the exception unwound the stack with no way to recover the already-successful barcode value
— `ocr_status='failed'` silently discarded a decoded NSN. Fixed by attaching the barcode to the exception
before it propagates, so a genuine OCR-engine outage still queues the page as `failed` for retry (never a
silently-empty `done`) while the barcode value survives and still promotes into `parts`.

### Fixed — Confidence signaling: badge tooltips, RPSTL exact-match ordering, fuzzy-match badge, barcode/OCR conflict table (`9b0e5b9`)
Four instances of the same pattern — confidence/provenance data the backend already computed but the UI
never surfaced, or computed in whatever order SQLite happened to return rather than a real ranking. New
`shared.js` `VW.confTier()` buckets a raw confidence float into high/verify/low, cross-checked at test time
against `rpstl_feature.review()`'s own threshold so the two numbers (which had already silently drifted
once) can't drift apart unnoticed; backported to the home-page OCR badge (previously no tooltip at all) and
the part-match card. `rpstl_feature.py`'s exact-match lookup had no `ORDER BY confidence` — unlike its own
fallback two lines below — so `best=rows[0]` depended on incidental SQLite row order in the function behind
tapping a part number on a scanned page, likely the single most common lookup in the app; now ordered.
`search_feature.py`'s `exact`/fuzzy-match flag existed but was never read by the UI, so a synonym-only hit
rendered identically to a literal one — now tagged and badged "≈ approx". New migration
`0012_barcode_ocr_conflict.sql` adds a `parts_conflicts` table: `extract_parts()` already inserted both an
OCR-regex NSN and a barcode-decoded NSN per page with separate dedup keys, but nothing compared them when
they disagreed — now flagged and rendered explicitly ("barcode reads X, page reads Y"), never auto-resolved.

### Fixed — UX pass: adjacent-page warnings, honest failure states, hands-free navigation, touch sizing, inline search answers (`da0c996` → `cc02caa`)
- **`procedure_feature.py`** (`da0c996`): `procedure_full()` only ever parsed WARNING/CAUTION/DANGER boxes
  off the single best-matched page — a box printed at the bottom of the *preceding* page of the same work
  package (a common TM layout) was silently absent; now looked back exactly one page. Separately,
  `dossier.html`/`procedure.html`'s cautions/warnings panels rendered identical "none found" copy for three
  different situations (genuinely empty, a fetch/parse failure, a backend retrieval error) — a mechanic had
  no way to tell "no hazards" from "the lookup silently failed"; now three distinct states.
- **`readaloud.js`** (`32614b7`): step-aware hands-free navigation for `procedure.html` — voice commands
  ("next"/"previous"/"repeat"/"stop") plus a floating touch-sized prev/next bar, active only when real
  `.step` DOM nodes exist so every other page is unaffected.
- **`palette.js`** (`00b1d4a`): the "⌘K jump" discovery pill — a keyboard-shortcut convention this audience
  has no reason to recognize — relabeled "🔍 Jump to anything" and resized unconditionally to the 44px
  touch-target floor (was below it, on the single fastest way around the app).
- **`index.html`** (`cc02caa`): the mechanic path's full-screen session modal opened on *every* cold start,
  not just first run — now gated by a 12-hour "already chose to browse" preference. A torque/measurement-
  shaped home search now renders an inline answer card (value/tolerance/unit/trust badge) instead of leaving
  the structured answer one undiscovered menu click away. Kiosk-mode touch-sizing, previously local to
  `index.html`'s own `<style>` block, generalized into `base.css` so every other page gets it too.
- **`torque.html`/`measures.html`** (`fcd0d75`): both were silently discarding real OCR confidence and an
  already-computed trust signal (`quality_reason`, `quarantined_count`) that never rendered anywhere.
- **Demo tour** (`9852279`): wired in `rps.js`, fixed 3 drifted Solve-it-hub icons, trimmed the mechanic path
  20→18 steps, and gave `demo.html` its first-ever test coverage (previously zero, despite being the first
  thing a new user sees).
- **`START-HERE.bat`** (`804bb08`): the guided menu walked Install → Verify → Build PUBLOG → Resume OCR →
  Launch without ever mentioning the corpus folder — a first-time user was never told where to put their
  unit's manuals until one menu deeper. New "Add your unit's manuals" option now shown first.

### Verified
Every commit in this range was independently `verify_all.py --snapshot`'d before landing; the range ends at
**46/46 checks, ALL GREEN** (`9b0e5b9`), up from 26/26 at the start of [1.14.0]. New test files added across
the range: `test_ingest_routes.py`, `test_ops_status.py`, `test_parts_request_route.py`,
`test_render_feature.py`, `test_demo_tour.py`, `test_flags.py`, `test_dedup.py`, `test_dedup_scale.py`,
`test_symbols_routes.py`, `test_tables_plus_stitch.py`, `test_office_formats.py`,
`test_masterfile_robustness.py`, `test_backupdb.py`, `test_audit_reachability.py`,
`test_sysprobe_cli_resolution.py`, `test_page_render_dpi_cap.py`, `test_build_keywords.py`,
`test_readaloud_stepnav.py`.

### Compatibility (R1)
All additive. Two new migrations (`0011_schematics.sql`, `0012_barcode_ocr_conflict.sql`), both new tables
with no change to existing schema. Every new pipeline stage is gated by its own opt-out toggle (default on)
via the new `flags.py` registry; every new route degrades cleanly (empty result, not an error) when its
sidecar DB doesn't exist yet.

### Known, deliberately deferred
- `camelot_tables()` (the 3rd table-extraction engine pilot) stays unwired into `/api/tables_plus` — a
  documented cv2/opencv-python binary-collision risk on version skew, not just "unmeasured benefit".
- `dedup.py` cross-TM-family duplicates are not caught by design (TM-family blocking trades that for
  bounded runtime); a duplicate re-filed under an unrelated TM number won't cluster.
- `docs/HANDOFF-NOTE.md`, `docs/PROJECT-SUMMARY.md`, `docs/MASTER-RECONCILIATION.md` still need their own
  reconciliation pass to this version — this entry only reconciles `CHANGELOG.md`.
- OCR-confidence blending stays conservative-only (can pull a heuristic quality call down, never raise it)
  — a deliberate asymmetry, not a partial implementation.

---

## [1.14.1] — 2026-08-18 — Barcode/QR wired into the OCR pass (catalog §4.9) + routes/ package split, embed cache, camelot pilot, KG page, fingerprint consolidation
`barcodes.py` had been a fully-built, self-tested, dual-backend (pyzbar/OpenCV) barcode/QR/Data-Matrix
`detect()` since it was written — its own docstring states the intent (some TMs print NSNs/part numbers
as barcodes; a machine-decoded value is higher-trust than OCR text) — but it had **zero callers**
anywhere in the codebase, only its own `__main__` self-test and the module import-check in
`verifystate.py`. Wired in. This release also bundles five smaller, independent changes landed in the
same working tree (R4): a `features/routes.py` → `features/routes/` package split, an `embed.py` search
cache, an opt-in camelot-py table-extraction pilot, a new `/kg` browsing page, and a hardening pass on
`ingestpipe.quick_hash()`'s content-only-vs-`viewer_ingest.fingerprint()` distinction — each documented
in its own bullets below rather than only getting scattered mentions in `ROADMAP-1.1.md` /
`feature_audit.txt`.

### Added
- **`viewer_ingest.ocr_one()` now reads barcodes off the same rendered page PNG `_render_png()` already
  produces for OCR** — never a second render of the page. New `_scan_barcode()` helper is opt-in
  (`VIEWER_BARCODE_SCAN=0` to disable, default on, mirroring `VIEWER_OCR_PREPROCESS`'s toggle pattern)
  and cheap: it no-ops instantly whenever `barcodes.available()` is `False` (neither pyzbar nor OpenCV
  installed), the exact same graceful-degradation contract `barcodes.py` already has. Reuses the
  existing identical-page dedup cache, so a repeated boilerplate page (covers, dividers) reuses the
  barcode read exactly like it already reuses OCR text.
- `ocr_one()`'s return type grew from `(text, confidence)` to `(text, confidence, barcode)`, where
  `barcode` is `None` or `{'type','data','nsn'}` — the first decoded record, preferring one that
  actually carries a recognizable NSN over one that doesn't when a page has more than one barcode.
  Three new nullable columns on `pages` (migration `0010_barcode_capture.sql`, additive/R1, same shape
  as [1.13.5]'s `ocr_confidence` column): `barcode_type`, `barcode_data` (truncated to 500 chars),
  `barcode_nsn`.
- **`extract_parts()` now also mines `pages.barcode_nsn`** on every full rebuild and inserts those rows
  into `parts` tagged `confidence='barcode'` — distinguishable, higher-trust provenance next to the
  existing regex-extracted `'page'`/`'aligned'` rows, picked up for free by every existing
  `confidence IS NOT NULL` consumer (`features/parts_feature.py`'s `part_lookup()` / `part_differences()`)
  with no changes needed to those callers. Full-rebuild-safe: `extract_parts()`'s own
  `DELETE FROM parts WHERE confidence IS NOT NULL` at the top of the function removes barcode rows too,
  but they're deterministically regenerated from `pages.barcode_nsn` every run, exactly like the regex
  rows are regenerated from `body_text` — confirmed idempotent by the new test.
- **`engine/features/routes.py` split into a `features/routes/` package** (`_shared.py` plus 13
  per-domain submodules: `browse`, `diagnostics`, `doc_extractors`, `field_tools`, `ingest`, `jobcards`,
  `ops_status`, `page_render`, `parts_media`, `parts_refs`, `schematics`, `search`, `static`) — the
  monolith had grown to 2,198 lines. Every route/handler moved verbatim (behavior unchanged);
  `viewer_app.py` now DI-wires `core` onto each submodule in `_froutes.SUBMODULES`, not just the
  package `__init__.py`, since each submodule's handler bodies reference their own module-level `core`
  global. `audit_features.py`'s duplicate-route-path scan and the route-registration cross-checks in
  `test_uiux_fixes.py` were updated to scan every `.py` file under the directory instead of one file.
- **`engine/embed.py`'s `search()` now caches the loaded `embeddings.npy`/`embeddings_ids.tsv` pair**
  in-process (`_ARR_CACHE`, keyed by `index_dir` + both files' mtimes, guarded by `_ARR_CACHE_LOCK`)
  instead of `_np.load()`-ing fresh off disk on every `/api/semantic` call — mirrors the keyword-search
  path's existing TTL'd `_SEARCH_LRU` pattern in `features/routes.py`. A rebuild (`BUILD-EMBEDDINGS.bat`
  reran) is still picked up immediately because the mtime check invalidates the stale cache entry.
- **`engine/tables_plus.py` gained an opt-in `camelot_tables()` pilot** — a THIRD, independent
  table-extraction engine (camelot-py 2.0, documented as an optional extra in `requirements.txt`, not a
  hard dependency) for cross-validating `tables.py` (PyMuPDF `find_tables`, ruled) and this module's own
  `borderless_tables()` (pdfplumber) against the same page. `_camelot_backend()` picks camelot's PDF→image
  backend from the same legacy/modern tier signal `sysprobe.py` already uses for page rendering (forces
  `poppler` on the legacy tier, otherwise leaves camelot's bundled `pdfium` default alone) and fails open
  to `pdfium` if the tier probe can't run. `camelot_available()` exposes the optional-import guard the
  same way `available()` already does for pdfplumber. **Not wired into the served app** — same "built,
  tested, zero callers" posture `barcodes.py` was in before this release's own barcode-wiring work above:
  `/api/tables_plus` (`features/routes/doc_extractors.py`) still calls only `borderless_tables()`, and no
  ingest step calls `camelot_tables()` either; its only callers today are `tests/test_camelot_tables.py`
  (new file — the pilot's self-test lives there, not in `tables_plus.py`'s own `__main__`).
- **New `/kg` page (`engine/ui/kg.html`)** — a browsing front-end for the knowledge graph `build_kg.py`
  already builds and `/api/kg` already served with no UI before this; linked from the nav in
  `engine/ui/index.html`. Alongside it, `build_kg.py`'s figureparts sample is now CLI-overridable
  (`--sample-docs` / `--parts-cap`, same `--flag N`/`--flag=N` style as `build_publog.py`'s `--sample`)
  and its defaults were raised 10x (400→4,000 docs, 5,000→50,000 parts cap) since the old sample covered
  roughly 1% of the corpus; `BUILD-KG.bat` now forwards its own CLI args through.
- **`ingestpipe.quick_hash()`'s docstring and self-test now say explicitly why it stays
  content-only** (size + SHA1 of the first 1 MB, mtime never consulted) instead of delegating to
  `viewer_ingest.fingerprint()` (`size:mtime:MD5(first 64KB)`), even though both are conceptually
  "cheap file fingerprint" helpers: `viewer_ingest.fingerprint()` is built for per-path change
  detection (has *this* file changed since it was last ingested — mtime-sensitivity is correct there),
  while `quick_hash()`'s job is spotting byte-identical duplicate manuals arriving from mixed sources
  (re-downloads, archive extractions, USB copies) whose mtimes don't reliably track "same content".
  The self-test now forces a duplicate file's mtime to differ from the original's and asserts
  `quick_hash()` still matches, so a future edit that makes it mtime-sensitive again would fail loudly
  instead of silently missing duplicates.

### Verified
- `python tests/test_barcode_wiring.py` (new, 49 checks) — built a REAL, machine-decodable QR (OpenCV's
  `QRCodeEncoder`, the encoder actually available in this environment; `pyzbar`/`segno`/`qrcode` are not
  installed here, decode backend is OpenCV-QR) encoding an NSN, embedded it into a synthetic PDF page via
  PyMuPDF, and ran it through the real `crawl`→`index_pdf`→`ocr`→`extract_parts` pipeline against the
  actual migrated schema: the barcode round-trips through `pages.barcode_*` and lands in `parts` with
  `confidence='barcode'`, survives a second `extract_parts()` rebuild unchanged, and surfaces through
  `features/parts_feature.py.part_lookup()`. Also covers the opt-out toggle, simulated
  `barcodes.available()==False` degradation, a real non-barcode page (decodes to `None`, no crash), a
  real barcode with no NSN in its payload (type/data captured, `nsn` stays `None`, no `parts` row), and
  the NSN-preferring selection/truncation logic. Skips cleanly (exit 0, reason printed) instead of
  faking a pass on an environment that can't actually decode or generate a barcode.
- `python barcodes.py` / `python qrgen.py` self-tests — unchanged, still pass (backend=opencv-qr here).
- `python engine/tests/test_features_integration.py` — new `embed_cache_hit_no_reload` /
  `embed_cache_invalidates_on_rebuild` checks confirm `embed.search()` loads the embeddings array once
  across two calls against an unchanged `index_dir`, then reloads exactly once after a real,
  `os.utime`-forced mtime bump simulating a rebuild.
- `python engine/tests/test_camelot_tables.py` (new, 19 checks) — camelot-py 2.0 happens to be installed
  in this environment, so every check ran for real (not skipped): builds a real ruled-table PDF via
  reportlab, round-trips it through `camelot_tables()` and recovers the actual NSN/item-name cell data,
  covers empty-cell/no-table/missing-file/out-of-range-page degradation, the `_camelot_backend()`
  legacy/modern tier-gating (incl. a simulated probe-glitch fail-open), a forced-backend override, the
  `camelot_available()==False` degradation path, and a direct cross-validation against `tables.py`'s
  PyMuPDF extraction on the same synthetic page (row/column counts and recovered figures agree). Skips
  cleanly (exit 0) instead where camelot-py isn't installed, same posture as `tables_plus.py`'s own
  pdfplumber self-test.
- `python engine/tables_plus.py` — unchanged borderless/stitch self-test still passes; the camelot pilot
  regression itself was moved out of this file's `__main__` and now lives entirely in
  `test_camelot_tables.py` (strictly more coverage than duplicating a subset here would give).
- `python engine/audit_features.py` and `python engine/tests/test_uiux_fixes.py` — both updated to read
  every file under `features/routes/` instead of the old single `routes.py`; `[0] duplicate route paths`
  and the nav-link / QR-header route-registration checks all still pass against the split package.
- `python engine/verify_ui.py` and `python engine/tests/rps_lint.py` — `ui/kg.html` added to both pages
  lists; passes the syntax check and is classified alongside `related.html`/`semantic.html` as a
  discovery tool (not a core ES5-required mechanic) in `MODERN_BY_DESIGN`.
- `python engine/ingestpipe.py` — self-test extended so the duplicate fixture file's mtime is forced
  to differ from the original's (`os.utime`, +10000s) and asserts `quick_hash()` still returns the same
  value for both, proving the content-only behavior the docstring now documents.
- Full suite: `python tests/verify_all.py` — 26/26 suites pass (the new file auto-discovered via the
  existing glob, [1.14.0] finding #41's own fix). The one non-suite check in that gate,
  `safeguard verify`, reports pre-existing drift against a stale snapshot from unrelated, already
  in-progress work in this tree at the time of this change — not caused by this change (`viewer_ingest.py`
  is the only one of its 14 flagged files this change touched, and it's flagged only because it grew, as
  expected).

### Compatibility (R1)
- `pages.barcode_type/barcode_data/barcode_nsn` are additive, nullable columns — no existing query,
  index, or FTS trigger references them; NULL for every page OCR'd before this migration (not
  backfilled — same posture [1.13.5] took for `ocr_confidence`).
- `ocr_one()`'s return type changed again (`(text, conf)` → `(text, conf, barcode)`) — grepped the whole
  tree; `_ocr_task()` was the only caller, updated in the same change, same as the [1.13.5] precedent.
- Rollback = don't run future OCR/`extract_parts()` passes; the columns and any `confidence='barcode'`
  rows stay, but nothing new writes to them.
- `features/routes.py` no longer exists as a file — `import features.routes` still works unchanged
  (the package `__init__.py` re-exports every name the monolith exposed), but anything reading
  `features/routes.py` as a single file path breaks; grepped the whole tree, found and fixed the only
  two such callers (`audit_features.py`, `test_uiux_fixes.py`).
- `quick_hash()`'s actual output format (`sha1(size + first 1MB)[:16]`, content-only) is unchanged —
  only its docstring and self-test coverage grew — so nothing that reads its return value is affected.

### Known, deliberately deferred
- The existing corpus is not backfilled — barcode capture only grows as pages are naturally re-OCR'd.
- `pyzbar` (1-D barcode + Data-Matrix, beyond OpenCV's QR-only detector) remains an optional install
  (see `requirements.txt`) — not installed in this environment, so this change's own regression test
  ran against the OpenCV-QR backend only.
- `search()`'s free-text NSN routing (`features/search_feature.py`) was deliberately left untouched —
  barcode-sourced NSNs are consumed via the `parts` table / `part_lookup()`, the integration point
  named for this work; wiring them into full-text search too would need a separate design (there's no
  page body text for a barcode-only value).
- `camelot_tables()` itself is deliberately NOT wired into `/api/tables_plus` or any ingest step yet —
  it's a cross-validation pilot, not a replacement for `borderless_tables()`; deciding how (or whether)
  to surface a three-way extraction disagreement to a route/consumer is separate follow-on work.

---

## [1.14.0] — 2026-08-18 — 50-finding 4-tier audit + UX pass + CI + doc reconciliation
The largest single effort in this project's history by commit count (12 commits, 2026-08-17 to
2026-08-18): a full 4-tier code audit (Critical/High/Medium/Low, 50 findings from the original
manifest), a follow-up UI/UX audit and priority-5 fix pass, this repo's first-ever CI workflow (plus
a real bug it caught on day one), and the documentation reconciliation finding #41 of the Medium
tier explicitly deferred until everything else was done. Every tier was implemented, then
independently xhigh-effort multi-agent code-reviewed, with every real review finding fixed in its
own follow-up commit before moving to the next tier — the same discipline applied to the review
findings themselves in the CI-fix and staleness passes.

### Fixed — Critical tier (`08bbb81` → `086aed3`, 8 findings + 13 review findings)
- An infinite loop in `procedure_feature.py` (wrong loop-index direction on the blank-line branch)
  hung on virtually any real OCR'd page, backing `GET /api/procedure_full` and exhausting the bounded
  thread pool one request at a time. `test_procedure.py` (22 tests, previously never wired into
  `verify_all.py`) now passes instantly instead of hanging.
- `airgap.py verify()` now fails closed against both a file-existence oracle and a path-traversal
  escape, instead of probing every listed file even with an invalid signature.
- `/api/airgap_manifest` and `/api/ingest_scan` now go through the same `VIEWER_INGEST_ROOTS` fence
  the sibling ingest routes already enforced.
- A negative `Content-Length` used to sail past the POST body cap and read until EOF; a malformed
  one desynced keep-alive connections. Both rejected outright now.
- `GET /api/audit`, `/api/ops`, `/api/status` (and, per the review pass, 4 more: `command_status`,
  `ingest_status`, `provenance`, `integrity`) now require the same token the POST auth path already
  enforced in network-exposed mode.
- `embed.py`'s hash-fallback semantic search used Python's per-process-randomized `hash()` — silently
  broken across every server restart on the documented zero-download default. Switched to
  `zlib.crc32`, with a version stamp (`embed.HASH_ALGO_VERSION`) so a stale pre-fix index now reports
  `ready=False` with a rebuild instruction instead of silently serving broken results.
- `build_publog.py`'s destructive rebuild (delete-then-rebuild-unprotected) now builds into a temp
  file and only swaps it in (`safeguard.atomic_replace`) once every table/index has committed.
- Non-atomic sidecar-cache writes across `vectorize.py`/`schemgraph.py`/`routes.py`'s `?fresh=1`
  switched to `safeguard.atomic_write`; a real race in that helper's own temp filename (PID-only,
  unsafe once wired into multi-threaded request handlers) fixed too — verified live with 16 threads,
  320 racing writes, zero corruption.
- `verify_all.py`'s test gate was a hardcoded filename allowlist — replaced with glob-based
  auto-discovery, surfacing 9 previously-never-run test suites (~1,200 lines) in the same change
  (test_accuracy, test_congruency, test_extraction, test_features_integration,
  test_features_modules, test_http, test_jobcard, test_newmodules, test_property_fuzz — the commit
  that shipped this fix said "8," undercounting by one; corrected here against `verify_all.py`'s
  own source comment, the authoritative, currently-verifiable count).

### Fixed — High tier (`04bd4a5` → `48c7a63`, 12 findings + 15 review findings)
- `kg.py` now rebuilds into a temp file and atomically swaps in, matching `build_publog.py`'s
  crash-safe pattern.
- A SQL condition in `xref.py` matched NULL-`fig_no` rows regardless of the doc filter, leaking a
  part's loose rows into every other document's sibling-parts list.
- New `viewer_ingest.py prune` subcommand reconciles documents whose source file was deleted/renamed
  since the last crawl (rename detection via fingerprint match, cascade-safe cleanup, dry-run by
  default, missing-fraction abort threshold so an unmounted drive can't look like a mass deletion).
- `migrate()` now snapshots the DB before applying any pending migration.
- The NSN regex across `patterns.py`/`core_pillars.py`/`partlocate.py` is now word-boundary-anchored
  (no longer matches inside invoice/PO numbers).
- OCR preprocessing (deskew/denoise/binarize) is now actually wired into the OCR path — it existed
  but was never called.
- New `ocr_supervisor.py` + `run_ocr_auto.bat`: a heartbeat-staleness watchdog that force-kills and
  recovers a HUNG (not just crashed) OCR pass, plus a per-page timeout. The review pass caught a real
  bug in the watchdog itself: a leftover heartbeat from a *prior* session made it kill a brand-new,
  healthy pass on its very first poll — fixed by tracking the child's own start time as the baseline.
- The QR-code base URL now comes from a validated allowlist (`safe_public_base`) instead of trusting
  the raw `Host` header.
- This repo's first CI workflow (`.github/workflows/ci.yml`) — runs `verify_all.py` on every push/PR.
- 171 new regression checks across 3 new test files covering 7 previously-zero-coverage feature
  modules and the Tier-1 corpus-build pipeline.

### Fixed — Medium tier (`0059dc8` → `3590cb2`, 19 of 24 findings + 14 review findings)
- `xref.py` fabricated a fake NSN from any 13+-digit run instead of rejecting it; now anchored.
- `dedup.py`'s shingle hashing had the same process-randomized-`hash()` bug as the Critical-tier
  `embed.py` fix — switched to `zlib.crc32`.
- A large-format foldout page could rasterize uncapped (a 48×36in page at 200 DPI was ~69MP against a
  25MP intended ceiling); fixed, and extended to the Poppler fallback render path, which had no cap
  at all. The review pass caught the ceiling's own 100-DPI floor could itself push a large enough page
  back *over* the cap — lowered.
- `masterfile.py build()` rewritten to stream into an incremental aggregator instead of materializing
  every measurement row into one Python list first — verified byte-for-byte output-equivalent to the
  original across 10 rounds of randomized data plus a dedicated edge case.
- `kg.py neighbors()` now tries an indexed exact/prefix lookup before the slow substring scan (every
  lookup used to force a full table scan). The review pass caught the initial version of this fix
  silently dropped valid substring matches whenever an exact/prefix match also existed for the same
  query — both queries now always run, merged and deduped.
- 8 batch-script hardening fixes (hardcoded personal-machine paths, silent-success anti-patterns,
  busy-looping retry logic, missing errorlevel checks) across `VERIFY.bat`, `FIRST-RUN.bat`,
  `RUN-ALL-VERIFY.bat`, `run_indexing.bat`, `RE-RENDER-CAD.bat`, `RUN-CAD-TIERS.bat`,
  `FIX-PORT.bat`, `KILL-ZOMBIE-ADMIN.bat`.
- 5 deferred with recorded reasoning (a genuine FTS5-vs-completeness tradeoff in `kg.py`, two
  duplicated-but-differently-wound CAD mesh builders left unmerged pending visual verification, this
  doc reconciliation itself), 1 not applicable (an orphaned mockup with no live surface).

### Fixed — Low tier (`aad1709` → `e4f4bd0`, 6 findings + 2 review findings)
- Removed a stray `.orig` backup file, a dead duplicate module (`crossval.py`, zero external callers),
  and a superseded batch script still carrying a bug its own successor's header documents fixing.
- Fixed a `tables.py` short-circuit (`if False`) that always returned 0 regardless of actual content.
- Fixed an unescaped SQL `LIKE` wildcard in `ocr_diag.py` that double-counted diagnostics into "other".
- `verifystate.py`'s self-test module roster had drifted ~40% behind `VERIFY.bat`'s actual gate list —
  fixed, and hardened to cross-check itself against the real gate list going forward so this exact
  class of silent drift can't recur unnoticed.

### Fixed — Priority-5 UI/UX pass (`71c9c4c`, `a32aee9`; 10 UX findings + 20 review findings)
A follow-up UI/UX audit (rendering, 3D/CAD, schematics, OCR-facing UX, motion/gestures, scanning)
surfaced 52 findings; the 10 highest-priority shipped here, each verified live against a running
instance of the app:
- `index.html`'s front door was ES6-only with no fallback — added a genuine ES5 capability probe +
  minimal fallback shell (RPS-Legacy/IE11/old-Firefox support, this app's own stated tier).
- Interactive 3D and its SVG fallback gained touch-orbit + pinch-zoom (ported from the sibling
  CAD-rotate tab) plus an always-visible zoom/reset row.
- The local AI-illustrative 3D model gained an on-canvas watermark on its default tab (R13: AI tiers
  must never visually pass as authoritative).
- Circuit Lab wires can now be selected and deleted individually instead of only wiping the canvas.
- Deep Zoom now falls back to a chip list for OCR-only-page callouts instead of discarding them.
- Safety callouts (WARNING/CAUTION/DANGER) now propagate their OCR-quality confidence signal to all
  4 pages and the printed Job Card that render them (2 more caught by the review pass).
- Kiosk/glove-mode's touch-target minimum now covers `[role=button]` controls and the app-wide footer
  nav, with a `min-width` fix so circular badges can't distort into ovals.
- Bin/shelf audit no longer fabricates a fake NIIN from a scan that isn't a clean 9/13-digit NSN.
- The QR job-packet deep-link now explains itself instead of silently failing under the app's own
  documented default (loopback-only) deployment.
- Look-Alike Parts gained an inline cited-figure thumbnail per variant.
- The review pass caught two severe regressions that re-introduced the exact bugs the fixes above
  were meant to close (a rejected bin-audit scan could still silently discard the whole in-progress
  scan list; the NIIN-fabrication fix used `>=13` instead of `===13`, so 14+-digit codes were still
  fabricated) — both fixed and verified live, along with 18 more real findings (a legacy-fallback
  redraw path wiping the new 3D zoom bar/watermark, a checkbox-sizing regression, an unintended
  button-height change, a missed IPv6 deployment case, a blob URL leak, and cleanup).
- New `engine/tests/test_uiux_fixes.py`: 174 checks.

### Fixed — CI (`7c4a3ba`; 3 root causes + 6 review findings)
CI's own Autofix flagged `test_http.py` failing on the very first PR this workflow ran against.
- 8 of 11 failing routes shared one root cause: the test's synthetic DB fixture had drifted from the
  real `documents` schema (missing `type`/`nsn`/`page_count`) — fixed the fixture, matching this
  app's own dispatcher philosophy that column drift should stay a loud signal, not get papered over.
- 3 more were flagged as "non-JSON" but are legitimately binary PDF endpoints by design — the test's
  blanket JSON assumption was wrong for these (and, latently, 6 more not yet triggered).
- `/api/search` had one genuinely unguarded query, missing the same guard its sibling already had.
- Stress-testing beyond CI's own config surfaced 3 more real, unrelated crashes fixed in the same
  pass: `registry.qint()` had no ceiling against SQLite's 64-bit bind range (`OverflowError` on an
  oversized numeric param); two routes passed `page` through unvalidated into an unguarded `int()`;
  a non-ASCII "digit" character surviving a filename filter crashed a PDF response mid-write with a
  Latin-1 encoding error.
- The review pass on all of the above caught a genuine concurrency race in one of its own new guards
  (two threads could pair a valid cache signature with an empty map, permanently) — serialized under
  a lock and verified with a 64-thread stress test against a live-broken-then-fixed schema.

### Fixed — Staleness pass, Tier 1 (`3054dad`; 6 items + 10 review findings)
A follow-up full-project staleness audit (dependencies, git hygiene, docs-vs-reality, backlog-vs-
fixed, dead code, repo bloat — see `docs/audit/` and the Viewer Drift Report artifact from this
session) found this project's dependency on PyMuPDF's deprecated `fitz` import alias was printing an
unsuppressible warning on every server start; all 19 (then 3 more, caught by review) call sites
migrated to `import pymupdf as fitz`. Also fixed: a real test-isolation bug that had already
contaminated the live, git-tracked `keywords_user.json` sidecar with leftover test data (cleaned);
two stale, fully-merged git branches; and 6 small hygiene fixes (a 14-release-stale version comment,
hardcoded personal-machine paths, a dead `.gitattributes` rule, a drifting hardcoded test-file count).

### Verified
`engine/tests/verify_all.py`: 26/26, ALL GREEN, stable across every run from the CI-fix commit
onward. Every commit above ran the full suite before and after; the 2-failure baseline
(`test_http.py`, `safeguard verify`) that held through most of this run was itself eliminated by the
CI-fix and Tier-1-staleness commits respectively — this is the first point in the project's history
this file records a fully clean `verify_all.py --snapshot` run.

### Compatibility (R1)
Every fix above is additive or corrective within its own function/route — no schema change beyond
the CI-fix commit's test-fixture-only schema correction, no removed public route or changed response
shape, no breaking config default. The `KEYWORDS_USER_PATH`/`safe_header_token`/`_kill_tree`-style
refactors extracted shared helpers from existing, already-tested logic rather than introducing new
behavior.

### Known, deliberately deferred
- 5 Medium-tier findings and the Medium-tier's own `_box()` mesh-builder duplication (see that
  tier's entry above) — each documented with explicit reasoning at the commit that deferred it.
- 3 items surfaced by the Tier-1 staleness review, deliberately not applied: `KEYWORDS_USER_PATH` is
  never reset after a test run (consistent with the pre-existing, also-unreset `V.DB_PATH` pattern);
  CI's "tests are self-contained" comment is true by convention, not structural enforcement; 7 launch
  scripts still probe via the deprecated `fitz` alias but already self-heal.
- Tiers 2-6 of the Tier-1-staleness Drift Report (the documentation reconciliation this entry partly
  *is*, dependency-version hardening, and repo-bloat cleanup) — tracked separately, not this entry.

---

## [1.13.5] — 2026-08-09 — OCR quality signal + temperature extraction gap
Prompted by a direct question ("check the current OCR accuracy numbers") that split into two different
answers: the *extraction* layer (measures.py's regex over already-OCR'd text) had a measured, root-caused
80% recall gap; the *OCR* layer itself (image-to-text transcription) had **no accuracy signal of any kind**
beyond completion percentage. Both addressed.

### Fixed
- **Temperature extraction missed bare F/C entirely.** `measures.extract()`'s temperature pattern required
  a `°` symbol or the word "deg"/"degrees" before F/C — a bare reading like "-40 F to 120 F" (a real,
  common way TMs write temperature ranges) extracted **nothing at all**. This was the entire gap behind
  `test_accuracy.py`'s 80% recall score. Added a bare-letter F/C alternative, guarded against the two real
  collision classes this corpus is full of: hyphen-suffixed military designators (F-15, F-16, F/A-18, C-5,
  C-17, C-130 — excluded via the same `(?!-\d)` technique already used for the 5W-30 oil-grade guard) and
  no-space battery C-rate notation (0.5C, 1C — excluded via a new whitespace-required check in `extract()`,
  since the isolated per-unit regex `_classify()` re-derives from can't see surrounding-text context).
  `degF`/`degC` added to `_BARE_LETTER_UNITS` (the OCR-linearized-table newline guard, v1.13.4) since the
  new bare alternative has the identical bridging risk. `test_accuracy.py` now reports **100% recall
  (10/10)**; added a negative ground-truth case (designators + C-rate, expects zero extractions) and a
  dedicated regression test (`test_extraction.py::test_measures_bare_temperature`) asserting the real
  readings are found and the collisions are not.

### Added
- **OCR confidence is now captured, not discarded.** RapidOCR computes a per-line confidence score for
  every text detection; `ocr_one()` reduced its output to text only and threw the score away — meaning the
  *only* OCR-quality signal in the entire app was "OCR ran" vs. "OCR did not run," never "OCR probably got
  this right." `ocr_one()` now returns `(text, confidence)` (the page-level average of RapidOCR's per-line
  scores, 4dp; `None` for the Tesseract fallback path, which doesn't expose per-line scores the same way).
  New additive column `pages.ocr_confidence` (migration `0009_ocr_confidence.sql`, nullable, R1-clean — old
  rows read NULL until naturally re-OCR'd; no backfill/re-OCR pass was run against the live corpus).
  `coverage.overview()`'s `ocr` block now reports `avg_confidence`, `confidence_scored_pages`, and
  `low_confidence_pages` (< 0.5 — a deliberately conservative, not-yet-calibrated first-pass bar), feeding
  `/api/coverage` and `/api/command_status` (both already TTL-cached, v1.13.4).

### Verified
- `python tests/test_accuracy.py` — recall 100% (10/10), precision 100%, extras=0 (was 80%/10).
- `python tests/test_extraction.py` — all checks pass incl. the new bare-temperature regression test.
- `python measures.py` — self-test OK (all target dimension types still found, no regression).
- Isolated temp-DB checks: migration 0009 applies cleanly (schema_version → 9), `ocr_one()`'s new
  `(text, confidence)` contract verified on the blank-page path, `pages.ocr_confidence` round-trips
  correctly through the exact `UPDATE` statement `ocr()`'s `handle()` uses, and `coverage.overview()`'s
  new fields compute correctly against known values (avg/scored-count/low-count all asserted).
- Full `VERIFY.bat` gate: see follow-up note.

### Compatibility (R1)
- `pages.ocr_confidence` is an additive, nullable column — no existing query, index, or FTS trigger
  references it, so unmodified code paths are unaffected. Rollback = don't run future OCR passes; the
  column stays but nothing new writes to it (the migration itself is not reversed, consistent with every
  prior additive migration in this file).
- `ocr_one()`'s return type changed from `str` to `(str, float|None)` — every call site (`_ocr_task()`,
  `ocr()`'s `handle()`) was updated in the same change; grepped the whole tree for other callers (none
  found).
- The temperature regex change is additive (a new alternative in an existing pattern) — no existing
  torque/pressure/length/electrical/capacity/rotation/flow/angle pattern was touched.

### Known, deliberately deferred
- The existing 39,683-document corpus is **not** backfilled with confidence scores — that requires a full
  re-OCR pass (hours+), which was not run in this change. Confidence coverage grows only as pages are
  naturally re-ingested going forward.
- Tesseract-fallback OCR still captures no confidence signal. RapidOCR is the primary engine in this
  deployment, so this was judged lower priority than shipping the RapidOCR signal now.
- The `< 0.5` "low confidence" bar in `coverage.py` is a conservative placeholder, not a calibrated
  threshold — there's no real corpus data yet to tune it against.

---

## [1.13.4] — 2026-08-08 — Full live-driving pass + parallel audit: 36 real bugs found and fixed
Drove every core feature end to end in the actual running app (not just the automated suites) — search,
part/dossier, procedures/troubleshoot, job packet, 3D/CAD, schematics/Circuit Lab, PUBLOG, decode, master/coverage,
command center/status, review/collections, ask/learn/verify, command palette/kiosk — then ran a parallel static
audit (7 finders → dedup → adversarial verify-by-refutation, every finding independently re-derived from the
real file before being trusted) looking for the same bug classes elsewhere in the codebase. **36 real,
independently-verified bugs found and fixed**, all root-caused with a live repro before patching, none patched
by re-running until quiet.
### Fixed — found live-driving (10)
- **Search: side filter starved results.** `?side=operator` filtered *after* the SQL `LIMIT`, so common terms
  ("brake", "gasket", "filter") could legitimately return **zero** operator-side hits even though real matches
  existed deeper in the corpus (operator is ~29% of the corpus, and relevance ranking doesn't know about side).
  Over-fetch a larger candidate pool before filtering, with a floor so small `?limit=` values still work.
- **Search: "did you mean" suggested OCR garbage** (`braae`, `brabe`) because the fuzzy-suggestion query never
  used the document-frequency data already sitting in the FTS vocab table. Now ranks by frequency and filters
  one-off scan artifacts — only on the user-facing suggestion path, never the actual search-matching path (rare
  OCR variants there are genuinely useful for finding garbled scanned pages).
- **5 of 6 hardcoded example NSNs (index.html/jobcard.html/demo.html) didn't match their labelled item in
  PUBLOG** — e.g. the "GASKET" placeholder pointed at a NIIN that's actually a screw. These are the clickable
  "commonly requested" quick-picks on a fresh install. All 6 replaced with NSNs verified to round-trip exactly
  through the app's own `publog.lookup()`. Traced the bad NSN's real-world footprint into live analytics too
  (flagged for the user, not silently altered — R6).
- **`faulttree.find_for_query()` had no dedup across duplicate corpus documents** — the same 4-symptom fault-tree
  group repeated 4-6× because that many duplicate copies of one manual exist in the corpus under different
  `doc_id`s. Deduped by `(tm_number, page, symptom)`, keeping a `dupe_copies` corroboration count instead of
  silently dropping the signal.
- **`/api/command_status` and `/api/integrity` had zero caching** on genuinely expensive aggregates — 12-53s
  (a `COUNT(*)` scan of every page's `body_text`) and 32-49s (a full SHA-256 over ~13GB of DB files)
  respectively, on *every single page load* of `/command` and `/verify`. Both read as the page silently hanging
  on "Loading…". TTL-cached (60s / 300s with a `?force=1` escape hatch on integrity).
- **`measures.py`'s torque regex missed Unicode dot variants** — "854 N•m" (bullet, not the coded middle-dot)
  fell through to the bare-N FORCE pattern and got silently mislabeled as force, surfacing as a generated quiz
  question asking "what is the force" with Newton-only answers for a torque-nut spec. Added the missing
  variants; while there, also found and fixed that a plain **hyphen** ("25 N-m") had never matched at all.
- **`verifystate.py` + its route: three compounding bugs meant `/verify` had found ZERO logs, ever, since the
  v0.96.0 restructure.** (a) Hardcoded the legacy `verify_099.log` filename instead of the `verify.log` root
  `VERIFY.bat` actually writes. (b) The pass-counting regex was written for the old log format and never
  recognized the current format's dominant `PASS <name>` bare-line style, severely undercounting. (c) A naive
  `"Error:"` substring check produced a **false-positive failure** on a line that was itself a PASS message
  quoting an expected error string it had just verified recovery from. Separately, the route handler's
  `docs/` path used two `os.path.dirname()` hops instead of three — correct for the old monolith location,
  never updated when this code moved into the deeper `engine/features/` during the restructure, so it had been
  silently pointed at the nonexistent `engine/docs/` the entire time. Page now correctly shows "✓ GREEN · 629
  PASS markers" instead of "not run yet".
### Fixed — found by the parallel audit (26)
**Resource leaks (12 sites, 10 files)** — same shape as the `db_integrity()` leak fixed in v1.13.3: a query
throws after `sqlite3.connect()` succeeds (lazy validation), `close()` sits unreached on the exception path,
leaking a Windows file handle that can block the next write to the same path. All now `con=None` + `finally`
(or, where the original design intentionally let the exception propagate to a generic 500 handler, `finally`
alone without swallowing it): `collections_feature.py` (`_collections_defs`, `_seen_map`), `fieldnotes.py`
(`_con`), `features/parts_feature.py` (`correlations_for`, `niin_review`, `nsn_aliases` — two leaks),
`features/browse_feature.py` (`status_summary`'s correlations block, polled repeatedly during OCR),
`specparse.py` (`find_for_query`, reachable via ordinary malformed user input, not just a corrupted sidecar),
`figuresheet.py` (`figuresheet`), `safeguard.py` (`_sqlite_backup` — both connections), `masterfile.py`
(`build`'s three optional-source connections), `kg.py` (`neighbors`, `stats` — had no exception handling at
all), `tmrev.py` (`currency`).
**Sidecar / dedup / caching (3)** — `sides_feature.save_override()` appended an unbounded, never-read-back
audit-log entry on every call, including no-op repeats (same waste class as the keywords bug already fixed);
now only logs a real change. `features/procedures_feature.procedure_for()` deduped by `(doc_id, page)` instead
of `(tm_number, page)`, missing the same duplicate-corpus-document problem `faulttree.py` already had fixed —
a part's procedure list could repeat one procedure up to 6× instead of showing distinct ones; same
`(tm, page)` + `dupe_copies` fix applied. `/api/coverage` (backing `/coverage` and `/ops`) had the identical
uncached-aggregate problem as `/command` on its other call site — factored into one shared, TTL-cached
`_coverage_overview_cached()` both routes now use.
**Regex / classification (10)** — `rpstl.py`'s SMR-code parser could grab a nomenclature word ("PLATE",
"MOTOR") ahead of the real SMR code on an RPSTL line, mislabeling repair authority AND manufacturer identity;
now reuses `smrdecode`'s full curated-table decode (all four SMR fields must resolve, not just a first-letter
check) — which also fixed the CAGEC field's identical leftmost-match flaw once SMR stopped absorbing it.
`smrdecode.py`'s own character class excluded the letter L by a range-syntax mistake (real codes `ML`/`AL`
could never be found), and its `scan()` only checked the 2-letter source pair, flooding false positives on any
word starting with one (e.g. "PARTS" → "PA"); both fixed by requiring the full decode. `standards.py` used
prefix-matching for its curated item table, so an uncatalogued series sharing leading digits with a curated one
got a **fabricated item name** (e.g. "AN9600-5" → the curated AN960 washer) — directly violating the module's
own "never fabricate" docstring; now exact-match (with a single trailing revision-letter still allowed, e.g.
MIL-PRF-2104H). Its designation regex was also case-insensitive, so the English word "an" ("an 85 gallon
tank") was misread as an AN hardware-standard code with no way to tell; now requires uppercase, matching how
designations actually appear in source text. `measures.py`: a bare-W Watts pattern misread SAE oil-viscosity
grades ("5W-30") as negative electrical wattage; and the zero-required-whitespace number-unit gap could bridge
*across a newline* in OCR-linearized tables, fabricating measurements from unrelated table cells — both fixed
(the newline guard applies only to the ambiguous bare-letter units, not full-word units, to avoid costing
recall on genuinely line-wrapped prose). `fluidsmatrix.py`: the same zero-whitespace ambiguity let an RPSTL
item-number suffix ("12L") get read as "12 liters", displacing the real capacity later in the same text — now
requires a space before the bare "l"; separately, a system was marked "seen" (permanently skipped) on its
*first* phrase occurrence even with no fluid/capacity nearby, silently losing a real spec that appeared later
in the same document — now tries every occurrence before giving up.
**Misc (2)** — `ingestpipe.scan_folder()`'s `cap=` parameter only broke the inner per-directory loop, so
`os.walk()` kept traversing the entire remaining tree regardless — the cap existed specifically so a folder-
scan endpoint can't hang on a large drive, and wasn't doing that; now returns immediately (which also stops
advancing the `os.walk()` generator). `pinouts.py` had a literal U+FFFD Unicode replacement character baked
into a wire-colour dictionary key (a save/encoding accident, confirmed via hexdump) — dead weight that also
leaked into the compiled color-token regex; removed (redundant with the correct `WHT` entry).
### Verified
- Every finding above independently confirmed by an adversarial second pass before being trusted (default:
  REFUTED unless the actual file proves it) — not taken on the finder agent's word.
- All touched modules' self-tests pass; the core regression suites (pillars/features/integration/modules/
  patterns/hardening/search_quality) pass 135/135.
- Full `VERIFY.bat`, run three times as fixes landed (the middle run's one `test_hardening` failure was a
  transient port-cooldown artifact from a standalone test run moments earlier — reproduced, explained, and
  confirmed absent on the next clean run): final **RESULT: ALL GREEN — every step exited 0.** 563 PASS / 0 FAIL;
  gate 9 (`safeguard verify`): 658/658 files OK, 0 damaged.
### Compatibility (R1)
- All 36 fixes are internal correctness fixes to existing functions — same signatures, same call sites, no
  schema or API change. Pure stdlib. Additive only: no fix removes previously-saved data (the dedup/log fixes
  only prevent *future* duplication); the `standards.py`/`rpstl.py`/`smrdecode.py` classification tightenings
  only *withhold* a previously-fabricated or previously-misrouted answer, never invent a new one (R13).
### Known, deliberately deferred
- **`measures.py`: a bare number fused with no space to a single-letter unit** (e.g. an RPSTL item number
  "489A" reading as "489 Amps") is the same ambiguity class as the `fluidsmatrix.py`/newline fixes above, but
  broader in the codebase and needs corpus-wide regression testing before a safe fix — flagged, not patched.
- The live analytics record carrying the original bad "GASKET, WATER PUMP" NSN (dated 2026-06-01, predates
  today) was traced but not altered — real historical data, R6 append-only; left for the user to decide.

---

## [1.13.3] — 2026-08-08 — VERIFY.bat confirmed GREEN on host: two real bugs found + fixed
`VERIFY.bat` had never been confirmed green on an actual host for the v1.13.0–1.13.2 work (a standing item in
`HANDOFF-NOTE.md`). Running it end-to-end surfaced two real, previously-undetected bugs — both root-caused with
an isolated repro before fixing, not just re-run until quiet.
### Fixed
- **`safeguard.db_integrity()` leaked its SQLite connection on the error path**, deterministically breaking the
  very next write on Windows. `sqlite3.connect()` succeeds even against a corrupted header (validation is lazy),
  so a genuinely-corrupted DB threw inside the `try` and skipped `c.close()`. On Windows an unclosed read handle
  blocks `os.replace()` over the same path, so `recover()` called immediately after detecting corruption — the
  exact scenario the function exists for — failed with `PermissionError: [WinError 5] Access is denied`. Confirmed
  100% reproducible (identical failure across two independent runs) and isolated with a minimal repro before the
  fix. Now wrapped in `try/finally` so the connection always closes. Also reachable (rarer) from `snapshot()` and
  the manual `backupdb` command if either is ever run against an actually-corrupted DB.
- **`search_feature.user_keywords_save()` (`POST /api/keywords`) appended every submitted group with no dedup**,
  unlike its sibling `user_tags_add()` a few lines below which already deduped case-insensitively. Since
  `test_routes.py`'s route smoke-sweep POSTs the same fixed payload every `VERIFY.bat` run, this had been silently
  accumulating duplicates for a while — **29 identical copies** were already sitting in the live
  `engine/keywords_user.json` sidecar. Added the same case-insensitive dedup `user_tags_add()` already had (a
  group is a duplicate if its lowercased term set matches an existing one, any order); verified idempotent against
  repeated and case-varied resubmission. Cleaned the 29 accumulated duplicates out of the live sidecar (29 → 1;
  harmless data, not corruption — just unbounded test-traffic pollution).
### Verified
- Re-baselined the stale `safeguard.py` vault snapshot (was `SNAP_20260708_102259_pre-publog`, from before PUBLOG
  and all of v1.13.x — a separately-flagged known gap) to `SNAP_20260808_090205_v1.13.2-verify-final`.
- Full `VERIFY.bat`, third run (after both fixes + the clean re-baseline): **RESULT: ALL GREEN — every step exited
  0.** 563 PASS / 0 FAIL across the log; gate 9 (`safeguard verify`): 658/658 files OK, 0 damaged.
### Compatibility (R1)
- Both fixes are internal correctness fixes to existing functions — same signatures, same call sites, no schema
  or API change. Pure stdlib; additive only (the dedup check does not remove any previously-saved data, only
  prevents future duplicates).

---

## [1.13.2] — 2026-07-18 — Retroactive Post-Support: run-mode is now a saved Settings choice (auto-pick + manual override)
### Added
- **Persistent run-mode selection.** The Retroactive-Post-Support runtime mode (`modern` / `lite` / `legacy`) is no
  longer env/CLI-only — the user's choice is now saved in `index/viewer_settings.json` and survives restarts. New
  `engine/settings.py` (tiny, stdlib-only, durable via `safeguard.atomic_write` with an atomic-rename fallback;
  **fail-open on read, fail-loud on write**; preserves unknown keys so older/newer builds never clobber each other).
- **Settings-panel control** on the System-Status page (`status.html`): a **Run mode** card with three choices —
  **Auto (recommended)** · **Performance** · **Retroactive Post-Support** — showing the resolved mode + reason, the
  hardware recommendation, and the page-cache size. ES5-safe (XHR/`var`) so it works on the legacy UI too. New
  `POST /api/rps_mode` persists + re-applies the choice live; `GET /api/rps` now reports the saved `setting`,
  its labels, whether an env var is overriding it, and sysprobe's `recommended_mode`.
- **`rps.mode_for_setting()`** maps the user-facing choice onto a concrete engine mode: *auto* → hardware auto-pick,
  *performance* → force full experience, *retro* → force the compatibility path (never full-effects) while still
  auto-distinguishing `lite` (modern-but-weak) from `legacy` (old OS / Poppler / old Python). `mode_for()` is unchanged.
- **`sysprobe.py` now surfaces the recommendation** (`recommended_run_mode` / `_reason` / `run_mode_ui`) in the profile
  and its printed summary, so launchers and the UI show a hardware-based pick without re-deriving the rule.
### Precedence / compatibility (R1)
- A concrete `VIEWER_MODE` env/CLI value still wins over everything (existing launch scripts behave exactly as before);
  then `VIEWER_RUN_MODE` env, then the saved Settings choice, then `auto`. Additive — no schema or corpus change.
- Live-apply note: UI effects, page-cache and render-DPI switch immediately; SQLite tuning applies to new connections,
  so it takes full effect on the next restart. The response says so (fail-loud, no silent partial apply).

## [1.13.1] — 2026-07-18 — AI-generated 3-D models: illustrative tier (Meshy import lane)
### Added
- **`localmodel.py` AI illustrative tier + `index/models3d/ai/` folder.** Drop an AI-generated model
  (e.g. a Meshy image-to-3D export) named `<NSN>.obj|.stl` into `models3d/ai/` and it loads in the Interactive
  3-D tab as an **illustrative approximation** — rendered with a red *"AI-GENERATED APPROXIMATION — illustrative
  only, NOT to scale, NOT for part identification or measurement"* banner in `threed.html`. New `localmodel.find_any()`
  returns `(path, fmt, tier)`; `status()`/`mesh_vf()` now carry `tier` + `caveat`.
- **The accuracy boundary is enforced STRUCTURALLY, by folder (R13):** an **authoritative** model in the parent
  `models3d/` folder always wins over an `ai/` one, so a generated mesh can never shadow or be mistaken for a real,
  to-scale model. The look-alike part-ID feature (`/partdiff`) is text/DB-only and never consumes these meshes.
  Back-compatible: `find()` is unchanged (authoritative-only). Docs: `index/models3d/ai/README.txt` (Meshy workflow —
  offline authoring; export OBJ/STL, not GLB).

## [1.13.0] — 2026-07-18 — HOLISTIC HARDENING: dev-team review implemented — trust everywhere, one verify gate, UI coherence, safety features
Final ship entry for v1.13.0. Four parallel work packages (ACCURACY · VERIFY/OPS · UI · FEATURES) implemented the
dev-team review's recommendations on top of the concurrent groundwork (pooled `doc_path()`, exposure posture); this
entry consolidates and extends the preliminary [1.13.0] draft below (retained per R6). The whole wave was then
independently audited, adversarially hardened, and polished before shipping. All changes additive/rollbackable (R1);
backup at `backups/pre-v1.13`.
### Added — FEATURES (safety + search intelligence)
- **Fielded search operators `tm:` / `nsn:` / `vehicle:` / `side:`** — `search_feature.parse_operators()` pulls the
  operators out of the query text (quoted values OK: `vehicle:"M915 Truck"`); the free text runs the normal pipeline
  while tm/vehicle become parameterized document filters, `nsn:` digit-normalizes against `d.nsn`, and `side:` feeds
  the existing side filter (an explicit `?side=` wins; an unknown `side:` value is **dropped, never mis-filtered**).
  Bare-operator queries (no free text) answer with the matching documents. Hint on the home page; +10 tests
  (`test_search_quality` 23 green).
- **`engine/oneuse.py` + GET `/api/oneuse`** — ONE-TIME-USE / torque-to-yield / discard-after-removal fastener flags
  (roadmap #41/#42, SAFETY). Sentence-level lexical classifiers over FTS-matched pages; **R13 extractive + cited**:
  every flag carries the manual's exact sentence (≤200 chars) + doc/tm/page — if the TM doesn't say it, no flag
  exists. `mentions_query` ranks flags whose cited sentence names the queried part first. Red warning card on
  `/part`; **`bom.build_kit()` merges the flags as cited `warnings`** so the kit itself says which fasteners MUST be
  replaced (deduped by kind+sentence; back-compat: no warnings → empty list).
- **Zero-result GAP LOG (#19)** — `/api/search` misses (≥3 chars) append a `gap` event to the analytics sidecar
  (best-effort, never breaks search); new GET **`/api/searchgaps`** ranks the distinct unanswered queries; a
  "Search gaps" card on `/command` shows what the corpus could NOT answer, with one-click retry.
- **`engine/build_conflicts.py` + `BUILD-CONFLICTS.bat` (#88-lite)** — precomputed cross-manual conflict sweep over
  the top part subjects into append-only `index/conflicts.db` (every sweep = a new run_id; R6). `/api/conflicts`
  answers a **fresh, exact-subject** swept entry instantly (`precomputed: true` + build timestamp); unswept/stale/
  non-default-tolerance queries fall back to the live scan unchanged; the sweep itself always scans live
  (`use_precomputed=False` — it can never read its own output). Best run while OCR is paused.
### Added / Changed — ACCURACY (R13 trust everywhere)
- **`features/corpus.py`** (see draft below) is now the ONE corpus FTS retrieval; **measures / ask / faulttree /
  cautions / pmcs / oneuse** all ride it — pooled per-thread connection in-app, leak-proof `try/finally` standalone,
  identical SQL + citation shape everywhere.
- **`validate.py` woven in:** every `/measures` row carries `quality` (ok|suspect|quarantined) and quarantined
  garble is **withheld from results but returned in `quarantined`** (flagged, never silently dropped, never shown as
  fact); `conflicts.detect()` **drops quarantined values before grouping** so garbled OCR can never manufacture a
  false safety-critical conflict (the response reports how many were held back and why).
- **Trust badges** on `/measures`, `/ask`, `/api/conflicts` (a detected conflict is by definition `review` — a human
  adjudicates) and `/publogdiff`.
- **`patterns.niin_of()` is the one canonical NIIN extractor** — publog, publogdiff, xref_feature and build_publog
  now delegate to it (one source of truth for NIIN parsing).
- **Concurrency/durability fixes:** `hybrid.py` `_GLOSS` lazy-init behind a lock; `sessions_feature` transaction
  rollback on failed writes; `signoff.py` DDL-once + read-only reads; `registry.qfloat()` central float param
  parsing (NaN/±inf → clean 400); `viewer_ingest.migrate()` atomic per-migration transactions (a failed migration
  can no longer leave columns without the schema_version bump — the crash-loop class from the migration gotcha).
### Changed — VERIFY / OPS (one gate, exit-code truth)
- **Root `VERIFY.bat` is THE authoritative union gate** (see draft below); `VERIFY-099.bat` forwards to it.
- **`test_routes.py` gained a blanket POST sweep** to match the GET sweep — every `registry.POST` route is hit with
  an empty body asserting no 5xx; **281 route cases green**. A new POST route can never ship uncovered.
- **`tests/rps_lint.py`: unclassified page = FAIL** — a new UI page must be explicitly classified ES5-required or
  modern-by-design; silent escape from the RPS gate is now impossible.
- **NEW `engine/tools/check_crlf.py`** — repo-wide CRLF gate for every `.bat` (the LF-only blink-crash gotcha made
  LOUD); 20 engine bats converted to CRLF; 83 bats verified.
- **`safeguard.py backupdb`** — `VACUUM INTO` full-DB backup with disk-space guard + keep-2 rotation; fixed the dead
  `gc` CLI branch (documented but unreachable); `run_ocr_auto.bat` runs a post-run `gc`.
### Changed — UI (coherence + a11y)
- **Tools menu regrouped**: new "Diagnose & decode" group (troubleshoot / ask / decode / readiness / binaudit /
  learn + verify / command) on `index.html`.
- **`shared.js` footer nav injector** (+ `base.css` `#vw-footer`) — consistent footer navigation on every page;
  **`esc()`/`toast()` dedup across 29 pages** (all now load `/shared.js`; `verify_ui.py` gained a dedup guard so a
  page that re-declares them fails verification).
- **`base.css` linked into** `schematics` / `threed` / `circuitlab` / `demo` / `cadtex_test`; **every `alert()` is
  now a `toast()`** (no more blocking modals mid-job).
- **A11y:** `palette.js` gets `aria-modal` + a focus trap; the index modals carry `role=dialog`.
- **Cross-linking:** dossier → `/part` banner; packet ↔ jobcard cross-links.
### Audited / Hardened / Polished (this session's independent pass)
- **Compile gate:** 188/188 `.py` compile clean in an isolated copy; 0 NUL-padded/truncated files; all HTML/JS/BAT
  end-sane; CRLF gate PASS (83 bats).
- **Integration audit:** all six `corpus.fts_pages` callers match its signature; **no route collisions** (244 GET +
  20 POST, registry-level overwrite detector); the search LRU key `(q, limit, mode, any, fuzzy, side)` keys on the
  **raw** query so operator variants can never hit a stale cache entry (verified live: plain vs `vehicle:`-filtered
  same-text queries return distinct results); bom `warnings` shape matches the `/part` + job-package consumers;
  the precomputed conflicts path stores post-validate/post-trust results and never rereads its own output.
- **Suites green in the isolated copy:** test_routes **281/281** (GET+POST sweeps) · search_quality 23 · hardening
  12 · patterns 20 · features 21 · pillars 23 · rps_lint PASS · verify_ui PASS · check_crlf PASS + 12 module
  self-tests (corpus, measures, conflicts, oneuse, bom, analytics, publog*, publogdiff, signoff, hybrid, ask,
  build_conflicts --selftest; *publog data-dependent step correctly SKIPs off-host).
- **Adversarial pass** on `/api/search`, `/api/oneuse`, `/api/searchgaps` via a live fixture server: 63 hostile
  cases (missing/empty/10KB params, unicode, quotes, SQL-ish strings, `vehicle:"unclosed`, `side:'; DROP`, repeated
  operators, FTS metacharacters, absurd limits) — **0×5xx, 0 tracebacks, 0 fixes needed**.
- **Polish:** dead `sqlite3`/`os` imports removed from `measures.py` + `faulttree.py` (they no longer open sqlite —
  corpus does); v1.13.0 tags on `check_crlf.py`; shebang on `oneuse.py`; no stray debug prints or console.log.
- **Host-verify pending:** run root `VERIFY.bat` on the Windows host (R10 screenshot too — server not running in
  the audit sandbox); optionally `BUILD-CONFLICTS.bat` while OCR is paused.

---

## [1.13.0] — 2026-07-03 — HOLISTIC REVIEW: unified data access · hardening · trust-everywhere · a11y
A "dev-team" review (three parallel reviewers: architecture/perf, robustness/security, data-integrity/UX)
produced strong recommendations; this release implements them, then audits/hardens/polishes the result. Every
change is additive and rollback-safe (R1); the full suite is green in-sandbox (11 regression suites + 279 route
cases + 24k fuzz + audit 0 FAIL/0 WARN).
### Added
- **`features/corpus.py`** — ONE shared FTS-retrieval implementation that measures/ask/cautions/conflicts/
  faulttree/pmcs each carried privately (every copy opened its own `sqlite3.connect(mode=ro)` and **leaked the
  handle on error**). In-app it reuses the pooled per-thread connection; standalone it closes via `try/finally`.
  The leak class is gone and retrieval is identical everywhere (R13: same query, cited the same way).
- **`viewer_app.doc_path()`** — pooled, leak-free document-path lookup; replaced ~15 raw `mode=ro` connects in
  `routes.py` that both leaked on error and bypassed the pool.
- **Auto-optimizer at startup** — WAL journal is set synchronously (concurrent reads during OCR writes) and the
  missing indexes build in a background daemon thread (OCR-safe, idempotent). The fast state is now the shipped
  default, not a manual `optimize_index.py` step. Opt out with `VIEWER_NO_AUTO_OPTIMIZE=1`.
- **Exposure posture** — binding to a non-loopback host now prints a loud banner and requires `VIEWER_AUTH_TOKEN`
  (constant-time compared, `X-Viewer-Token`) for mutating requests; loopback (the mechanics' path) is unchanged.
- **`patterns.niin_of`** canonical NIIN extractor (publog/xref/build_publog now delegate — one source of truth);
  **`safeguard.py backupdb`** (VACUUM INTO full-DB backup with rotation) + a fixed missing `gc` subcommand branch.
- **`/decode` page in the home Tools menu** plus `/part`, `/measures`, `/scan`; audit rule **[6] durable-write
  guard** (flags any raw `os.replace` in a serving module).
### Changed / Hardened
- **Error boundary is now a hard contract:** a `_sent` flag set inside `_send` means the boundary emits its 500
  only when nothing has been sent — a handler that sends-then-raises can no longer double-send and desync the
  keep-alive stream (B9 becomes structural, not by-convention). Chunked `Transfer-Encoding` is rejected (411).
- **All sidecar/override/keyword writers route through `safeguard.atomic_write`** (fsync + `_replace_retry`) —
  the override POSTs used to 500 on the transient Windows lock the retry exists to absorb, and could lose the file.
- **Bounded front door** — a connection semaphore caps concurrent worker threads (scales with cores, override via
  `VIEWER_MAX_WORKERS`) so an asset burst can't thrash the laptop. `_SEARCH_LRU` reads/writes are now lock-guarded.
- **`/api/layout` + `/api/tables_plus`** degrade to empty on a bad page instead of 500; **`/api/request`** never
  orphans its temp PDF (`try/finally`); the `LIKE` search fallback is scan-capped.
- **R13 trust, everywhere:** `/measures` now runs every value through `validate.py` and **withholds quarantined
  garble** (returned flagged, never shown as fact); `/part` "Key dimensions" carry a **real page cite** (cross-
  referenced against the cited measures path) or an honest "verify on /measures" — never a fake cite; **safety
  callouts on `/part` regained their page cite** (a corpus-refactor key rename `cautions`→`results` had silently
  dropped them from the part page + job package — caught and fixed in this audit).
- **Home-page a11y fix:** `index.html` didn't load `base.css`, so kiosk/glove-mode + focus rings were dead on the
  most-used screen (the kiosk toggle was a silent no-op there); the rules are now inlined.
- **`VERIFY.bat`** is the one authoritative gate (VERIFY-099.bat forwards to it): rebuilt on **exit-code truth**
  (per-step `if errorlevel 1`, no `&&`-chains that silently skip, no keyword-grep summaries) while keeping the
  console-hang lessons (subroutine+log, `pause >nul`, `run_timeout` wrapping, CRLF).

---

## [1.12.9] — 2026-07-03 — DEEP AUDIT: route-coverage gap closed, decoders reachable + fuzzed
A full audit of the v1.12 tower. It found three real problems — the most serious being that the reassuring
`test_routes 87/87 PASS` was **testing none of the new work**.
### Fixed
- **The 8 new v1.12 routes had ZERO test coverage.** `test_routes.py` drives a **hardcoded** ROUTES list, so
  `/api/standards`, `/api/nsndecode`, `/api/smr`, `/api/cage`, `/api/harnesstrace`, `/api/mac`, `/api/form_2404`
  and `/api/form_2407` were never once exercised over HTTP — the green 87/87 was false confidence. All are now
  curated with realistic params **plus their error paths** (missing `q` → 400, junk input → graceful null decode,
  invalid CAGE → reasons). Curated cases: **87 → 106**.
- **51% of the whole API surface was untested** (68 of 133 routes). Rather than hand-patch, `test_routes` gained a
  **blanket crash-sweep**: it auto-discovers every route in `registry.GET` that the curated list misses and hits it
  **bare**, asserting no 5xx (a 400/404/503 is a correct answer to a bare request). **A newly added route can never
  again ship with zero smoke coverage** — the sweep finds it automatically.
- **Name collision:** the new decoder page was briefly `/reference`, which collides semantically with the
  pre-existing `/api/reference` (part reference enrichment — a different thing). Renamed to **`/decode`**
  (alias `/reference-codes`) before it could confuse anyone.
- **`verify_ui.py`'s inline-JS gate is a hardcoded list**, so new pages silently escaped it — `ui/decode.html`
  added; noted as a standing gap.
### Added
- **`/decode` page + palette command "Decode a code (NSN/SMR/CAGE/MS)"** — the v1.12 decoders were **completely
  unreachable**: no page, no palette entry, no link. A mechanic could not use any of them. One input now
  auto-detects which kind of code was pasted (NSN / SMR / CAGE / standard designation) and renders the decode,
  showing R13 nulls honestly as *"not in the published tables — not guessed"* rather than hiding them.
- **Fuzz coverage for all six new pure modules** in `test_newmodules.py` — 4,000 hostile/random cases each
  (24,000 total, verified: 0 crashes, 0 invariant violations). It asserts the **R13 invariants** hold under fuzz:
  curated-flag ↔ named-item agreement, NIIN=9/FSC=4, every name is `None`-or-`str` (**never fabricated**), CAGE
  `valid` XOR `reasons`, harness nets are never singletons, and every MAC row names a real function.

---

## [1.12.8] — 2026-07-03 — Maintenance Allocation Chart (MAC) parser (roadmap Vol.2 #56)
### Added
- **`macchart.py` + GET `/api/mac`** — parse the MAC, the central maintenance-planning table in a TM, into
  structured rows: group number, component, maintenance **function** (Inspect / Test / Service / Adjust /
  Aline / Calibrate / Remove-Install / Replace / Repair / Overhaul / Rebuild), the **level** authorized
  (C crew / O unit / F field / H sustainment / D depot) with its name, and the **man-hour** time. It carries
  the component name down the follow-on function rows (the MAC groups several functions under one component),
  and `for_component()` answers "how do I service X, and at what level?". The route parses the matched pages or
  supplied text, optionally filtered to one component.
- **R13 discipline:** extractive only — a row is emitted **only when it contains a recognised MAC function
  keyword**; the function comes from the fixed MAC vocabulary; the level, man-hours and references are
  best-effort from the same line and left **NULL when the columnar layout can't be read** (never guessed,
  self-test asserts `Overhaul` with no readable level/time → both NULL); and every row carries its **raw source
  line** so a mechanic can verify against the chart. Stdlib only, additive (R1), self-tested; wired into VERIFY-099.

---

## [1.12.7] — 2026-07-03 — VERIFY-099 hang-proofing + two no-truncation false-positive fixes
### Fixed
- **VERIFY-099 "stalled for hours."** Diagnosis from the run log: the verification **body completed** (all suites
  through `test_hardening` passed in ~1 min) — the apparent stall was the launcher's tail behavior: it `type`d the
  entire ~750-line log to the console and then sat on a blocking `pause`, which on a Windows console in QuickEdit
  mode (a stray click) freezes output indefinitely. Replaced the full-log dump with a concise **RESULT summary**
  (GREEN/RED + the exact FAIL/Traceback/TIMEOUT lines + the PASS markers) and a clear "VERIFY COMPLETE" finish.
- **Real completeness FAILs surfaced by that summary and fixed:** the R9 no-truncation check was flagging literal
  `[...]` list-shorthand in the docstrings of **`airgap.py`** (1) and **`harnesstrace.py`** (2) as truncation
  markers. Reworded to prose; both now pass `verify_complete.py`. (The old blocking dump had buried these in the
  scroll — the new summary makes any such line impossible to miss.)
### Added
- **`engine/tools/run_timeout.py`** — a stdlib wall-clock guard: `run_timeout.py <seconds> <cmd...>` runs a step,
  streams its output, and if it exceeds the budget **kills the whole child tree** (taskkill /T on Windows) and
  exits 124 with a clear `!!! TIMEOUT !!!` banner, so no single hung step can ever stall the run for hours. Wrapped
  the only steps that could realistically hang — the HTTP server test (`test_routes`, 600 s) and the two fuzz runs
  (`test_newmodules`, `test_property_fuzz`, 900 s each). Passing runs are unaffected (child exit code passes through).
- Backwards-compatible (R1): the verification logic is unchanged; only the launcher's reporting and per-step
  timeouts were added. `run_timeout.py` is itself syntax- and completeness-checked by VERIFY-099.

---

## [1.12.6] — 2026-07-03 — Harness continuity trace (roadmap Vol.2 #55)
### Added
- **`harnesstrace.py` + GET `/api/harnesstrace`** — turn the pinouts `pinouts.py` extracts into **electrical nets**
  so a mechanic can trace a wire end to end: "voltage on J5-A — where else should it appear?" `build_nets()` groups
  pins that name the same signal (with common aliases, e.g. `GND`↔`GROUND`) into nets; `trace(connector, pin)`
  returns the other endpoints on that pin's net. The route extracts pinouts from the matched pages (or supplied
  text), then returns either all nets or a single trace.
- **R13 discipline:** continuity is **inferred from the pin tables, not asserted as measured** — every net is
  labelled `method: shared-signal` with a confidence (`high` when wire colours agree, `medium (verify)` when they
  differ), grouping is done **only on an explicit shared signal name** (never wire colour alone, which is far too
  common), and a pin with no partner is reported as "no continuity partner found" rather than force-joined. Missing
  pins return `found: false`. Builds on `pinouts.py`; stdlib only, additive (R1), self-tested; wired into VERIFY-099.

---

## [1.12.5] — 2026-07-03 — CAGE / NCAGE code validator (roadmap Vol.2 #54)
### Added
- **`cage.py` + GET `/api/cage`** — validate and structurally classify the 5-character CAGE (Commercial and
  Government Entity) code that identifies the maker/supplier of each RPSTL part. `validate()` checks the published
  format rules — exactly 5 characters, alphanumeric, the hard **no-I/O rule** (I and O are never used), and the
  1st/5th-numeric shape of a domestic code — and classifies the token as **US** (domestic), **NCAGE**
  (NATO/foreign-assigned, alpha first position), or flags an atypical shape with a reason. `scan(text)` pulls only
  **labelled** codes (`CAGE: 19207`, `CAGEC 0VGN7`) so it doesn't match arbitrary 5-char part fragments.
- **R13 discipline:** the module asserts only what the format guarantees and lists every failed rule rather than
  silently accepting; it **never returns a company name** — the assignee identity lives in PUBLOG's CAGE table, and
  the route says so explicitly (`identity_note` → look up via `/api/publog`). Stdlib only, additive (R1),
  self-tested; wired into VERIFY-099.

---

## [1.12.4] — 2026-07-03 — SMR (Source / Maintenance / Recoverability) code decoder (roadmap Vol.2 #53)
### Added
- **`smrdecode.py` + GET `/api/smr`** — decode the 5-character SMR code that rides on every RPSTL / repair-parts
  line (e.g. `PAOZZ`). It splits into four fields and names each from the published SMR tables: **source** (how the
  item is obtained — procured & stocked, kit component, manufacture/assemble at a level, or not-stocked/cannibalize),
  the **use** maintenance level (who may remove/replace it), the **repair** maintenance level (lowest level that may
  fully repair it), and **recoverability** (discard vs. return-for-overhaul, and at what level). `summary()` gives a
  one-line plain-language gloss; `scan(text)` pulls real SMR codes out of a page and ignores look-alike words by
  requiring a known source code.
- **R13 discipline:** the split is deterministic and each field is named from a curated standard table; an unknown
  source pair or level letter returns the raw letters with a **null meaning rather than an invented interpretation**
  (self-test asserts unknown source `QQ` → `source_meaning=None`) — because a mis-decoded SMR could scrap a
  repairable part or the reverse. Stdlib only, additive (R1), self-tested; wired into VERIFY-099.

---

## [1.12.3] — 2026-07-03 — NSN structure decoder (roadmap Vol.2 #51/#52)
### Added
- **`nsndecode.py` + GET `/api/nsndecode`** — decode the **structure** of a NATO Stock Number. Every NSN is a
  4-digit Federal Supply Classification (FSC = 2-digit **Federal Supply Group** + 2-digit class) followed by a
  9-digit NIIN whose first two digits are the **National Codification Bureau** code (which country codified the
  item). `decode(nsn)` returns the split plus the **FSG name** (from the complete published 78-group list) and the
  **NCB country** (from a curated well-established set: US 00/01, NATO 11, Germany 12, France 14, UK 99, Canada 21,
  Australia 66, etc.). `scan(text)` finds and decodes every NSN-shaped token on a page. Accepts dashed or undashed
  input; normalizes output to the standard `FSC-NN-NNN-NNNN` grouping.
- **R13 discipline:** the decode is **deterministic** — the FSG/NCB split is mechanical, the names come from
  published reference tables, and for an unassigned group or an NCB code we don't carry we return the raw code with
  a **null name rather than a fabricated country/name** (self-test asserts uncurated NCB 45 → `country=None`). It does
  **not** claim what the specific item is — that stays PUBLOG's job (`publog.py`). Stdlib only, additive (R1),
  self-tested; wired into VERIFY-099 (parse + completeness + `-B` self-test).

---

## [1.12.2] — 2026-07-03 — DA Form 2407 / 5990-E maintenance request (roadmap Vol.2 #72)
### Added
- **`forms.build_2407()` + GET/POST `/api/form_2407`** — a printable **maintenance request** worksheet for when a
  fault exceeds crew level and goes to support maintenance. Composes the requesting unit + work-order/JON + priority,
  the full **equipment identity** (admin no. / nomenclature / model / serial / NSN / miles-hours), and free-form
  **FAULT / DEFICIENCY** and **WORK REQUESTED** blocks + remarks + requested-by/approved-by signature lines. GET returns
  a blank form (prefill via `?org=&admin=&q=&nsn=`); POST fills it from a JSON body. Pairs with the existing DA 2404
  PMCS worksheet in the same module.
- **Worksheet-aid discipline (R13):** the PDF is explicitly labelled a worksheet aid — *transcribe onto the
  authoritative DA Form 2407 / 5990-E or GCSS-Army work order; verify the requested work against the TM.* Pure
  (returns PDF bytes), reportlab-gated (503 if unavailable), self-tested (filled + blank both valid `%PDF-`), covered
  by the existing VERIFY-099 wiring for `forms.py` (parse + completeness + `-B` self-test).

---

## [1.12.1] — 2026-07-03 — Standard-hardware / spec designation decoder (roadmap #58/#59)
### Added
- **`standards.py` + GET `/api/standards`** — decode the standard-hardware and specification codes that saturate a TM
  (`MS35338-46`, `AN960-10`, `NAS1149`, `MIL-PRF-2104`, `SAE J429`, `ASTM A193`). `classify(token)` returns the
  **family / kind** (hardware-standard vs performance-spec vs detail-spec vs material-standard vs test method) — which is
  unambiguous from the designation itself — plus, **only for a small curated series set we're confident about**, the item
  it names (AN960 → flat washer, MS35338 → split lock washer, MIL-PRF-2104 → engine oil OE/HDO, MIL-PRF-46176 → silicone
  brake fluid, etc.). `scan(text)` extracts every designation on a page, deduped. The route classifies the query token
  itself and scans matching pages.
- **R13 honesty:** the decoder classifies family reliably but **never fabricates an item meaning** for an uncatalogued
  MS/AN number — self-test asserts `MS12345-99` yields a family but no invented item. Stdlib only; wired into
  VERIFY-099 (parse-list + completeness + self-test).

---

## [1.12.0] — 2026-07-02 — Air-gap signed update package (brief-req E + security)
### Added
- **`airgap.py` + POST `/api/airgap_manifest` + `/api/airgap_verify`** (roadmap Vol.2 #95) — build a **signed update
  package** to carry manuals to a disconnected machine: a manifest of files (name + size + SHA-256) signed with an
  **HMAC-SHA256** over a canonical serialization. The receiving side re-hashes every file and re-checks the signature
  before anything is ingested — **fail-closed**: any missing file, changed byte, wrong key, or forged manifest → REJECT.
  Stdlib only; self-tested (ACCEPT clean, REJECT tamper/wrong-key/forgery). Pairs with `ingestpipe.py` (the folder scan).

---

## [1.11.4] — 2026-07-02 — Fixes from the first host VERIFY-099 of the v1.4-1.11 tower
The consolidated host verify ran: **6/9 green — test_pillars 23/23, test_features 21/21, test_patterns 20/20,
test_routes 87/87 (every new route, no 5xx), test_hardening, test_search_quality.** Three failures surfaced; the two
real ones are fixed:
### Fixed
- **RPS gate (rps_lint):** the `palette.js -> let declaration` failure was the *word* "let" inside a comment (a lint
  false-positive) — reworded in `palette.js` and `scanner.js` (0 ES6 tokens now in the injected scripts). Classified the
  29 UNCLASSIFIED pages: `scanner.js` + `readaloud.js` → ES5_REQUIRED (injected app-wide, verified ES5-clean); all
  feature pages → MODERN_BY_DESIGN.
- **test_truncation (`safeguard`):** `PermissionError: [WinError 5]` on the atomic replace — a transient Windows lock
  (antivirus / search indexer / lingering handle). Added `_replace_retry` (backoff, 6 tries) around `atomic_write` and
  `atomic_copy` so a momentary denial no longer fails the write.
- **no-truncation guard (R9):** 9 files (specsheet, conflicts, integrity, tmrev, verifystate, bom, crossmethod, rpstl,
  commonality) tripped the completeness guard on literal `[...]` / `(...)` / `... more` in DOCSTRINGS — false positives,
  not real omissions. Reworded every one (0 markers remain); self-tests unchanged and still pass. This closes the last
  host-verify failures: the tree is now green except the intentional stale-baseline drift (re-baseline to clear).
### Note (not a code defect)
- **safeguard "8 DAMAGED":** the baseline snapshot `SNAP_...200649_pre-ocr` predates this session's ~15 doc/code edits,
  so changed files read as drift (CHANGELOG/HANDOFF shown as MODIFIED/grew). The Edit/Write tools write full host files,
  so this is stale-baseline drift, not truncation — **re-baseline after confirming the 8 files are complete**
  (`py engine\tests\verify_all.py --snapshot`).

---

## [1.11.3] — 2026-07-02 — Bulk folder ingestion (brief-req E)
### Added
- **`ingestpipe.py` + POST `/api/ingest_scan` + `BULK-INGEST.bat`** (roadmap Vol.2 #96 / brief-req E) — point it at a
  FOLDER of manuals; it scans every supported file (pdf/txt/html/xml/csv/img), quick-hashes each to spot duplicates,
  and returns an ingestion **plan** (new vs already-in-corpus) for the existing ingest/OCR queue to process. Read-only
  over the source folder; corpus untouched (R6). Self-tested (recursive scan, unsupported skipped, dup-content detected).

---

## [1.11.2] — 2026-07-02 — PMCS worksheet (DA 2404 / 5988-E style)
### Added
- **`forms.py` + `/api/form_2404`** (roadmap Vol.2 #71) — generate a **PMCS worksheet PDF** in the DA-2404 / 5988-E
  column layout (TM item no. | deficiencies & shortcomings | corrective action | status) with the standard status-symbol
  legend (X / — / / / circle-X). GET → a blank worksheet; POST logged faults → a filled one. Labelled a worksheet aid
  (transcribe onto the authoritative form/GCSS-Army). reportlab; self-tested (valid PDF, faults + blank lines + legend).

---

## [1.11.1] — 2026-07-02 — Shift-handover digest
### Added
- **`handover.py` + `/api/handover`** (roadmap Vol.2 #83) — a shop-wide **shift-handover digest**: what's awaiting SME
  sign-off + recent field notes (extensible to open conflicts + due services), with a red/amber/green priority flag
  (red on any unresolved safety conflict or pending safety-critical value). Pure + self-tested. Wired into VERIFY-099.

---

## [1.11.0] — 2026-07-02 — Fleet readiness wave: service intervals · fluids matrix · commonality (+ /readiness)
Closes the deferred readiness item (roadmap #51/#61/#62). Built under **R13**, verified, additive (R1), no new deps.

### Added
- **`intervals.py` + `/api/intervals`** (#62) — extracts **service intervals** and normalizes them (every 3,000 miles /
  250 hours / 6 months / weekly / annually / before-operation) into {value, unit, basis=usage|calendar|event}. Self-tested.
- **`fluidsmatrix.py` + `/api/fluids`** (#51) — a per-system **fluids & capacities matrix** (engine/transmission/cooling/
  brake/differential/…): fluid spec + capacity + unit. Self-tested (engine OE/HDO 6 qt, cooling 20 qt, diff GO 80/90 2.5 pt).
- **`commonality.py` + `/api/commonality`** (#61) — **fleet commonality**: which platforms use a given NSN/part →
  single-platform / shared / fleet-common. Self-tested.
- **`/readiness`** page (alias `/fluids`) — the fluids matrix + service intervals for a vehicle in one servicing view; palette entry.

### Ops / docs
- `VERSION` → **1.11.0**; VERIFY-099 self-tests `intervals` + `fluidsmatrix` + `commonality`. Remaining open roadmap
  items continue in verified waves (air-gap update, bulk ingestion, wiring fault isolation, forms/compliance, …).

---

## [1.10.0] — 2026-07-02 — Recommendations wave: RPSTL structured import + cross-method agreement (+ 200-idea backlog)
The high-leverage picks from the 100-idea backlog. Built under **R13**, verified, additive/rollbackable (R1), no new deps.

### Added
- **`rpstl.py` + `/api/rpstl`** (idea #1) — structured import of the **Repair Parts & Special Tools List**: parses each
  row into figure ↔ item ↔ SMR ↔ CAGEC ↔ part-number ↔ NSN ↔ qty ↔ nomenclature, grouped by figure, ignoring prose.
  Self-tested (item 7 → NSN 5305-01-674-1467, SMR PAOZZ, CAGEC 19207, qty 4; rows without an NSN still parse).
- **`crossmethod.py` + `/api/crossmethod`** (idea #81) — **cross-METHOD agreement**: gathers the same dimension from
  independent extractors (measures now, tables/PUBLOG when present) and reports **confirmed** (≥2 agree) / **single** /
  **conflict** per value — defense-in-depth accuracy, distinct from the cross-*manual* conflict checker. Self-tested.

### Docs
- **`docs/UPGRADE-IDEAS-100.md`** + **`docs/UPGRADE-IDEAS-100-vol2.md`** — a curated **200-item R13 roadmap** across 20
  themes (extraction, search, diagrams, wiring, fasteners, fluids, workflow, PUBLOG, trust/QA, security; then
  operator/crew, extreme conditions, recovery/rigging, armament, BDAR, interoperability, OCR depth, forms/compliance,
  collaboration, deployment). Each item flagged ★ high-leverage / ⚑ safety-critical.
- `VERSION` → **1.10.0**; VERIFY-099 self-tests `crossmethod` + `rpstl`.
- **Sequenced program (R13):** the remaining ~190 backlog items are built in **verified waves, not unverified bulk** —
  each proven before the next. Deferred earlier items still open: fleet commonality, service-interval/fluids readiness,
  wiring fault isolation, air-gap update package, bulk folder ingestion.

---

## [1.9.0] — 2026-07-02 — Serviceability & safety graphics · kit/BOM · wiring pinouts · training · field notes
Built under **R13**. Additive & rollbackable (R1); read-only except the append-only notes sidecar. No new deps. Every
new pure module self-tested in-sandbox.

### Added — serviceability & safety graphics
- **`serviceability.py` + `/api/serviceability`** — extracts SERVICEABLE / WEAR limits (min/max, "replace if",
  not-to-exceed, wear-limit) distinct from nominal dimensions, and a **go/no-go tolerance checker** (`?measured=`) that
  answers "is my measured value still in spec?" (serviceable / marginal / replace). Wired onto `/part`. Verified:
  0.475 in vs a 0.480 min → **replace**; 0.485 → **marginal**.
- **`torqueseq.py` + `/api/torqueseq`** — detects the tightening **pattern** (star / criss-cross / sequential) + the
  staged torque values, and renders a **numbered bolt-pattern diagram** (the number = the tightening order). On `/part`.

### Added — logistics
- **`bom.py` + `/api/bom`** — a complete **kit / bill of materials** for a job: parts (deduped, with quantities) +
  consumables (gaskets/seals/O-rings/cotter pins/lubricants/sealant, flagged from the procedure) + tools. On `/part`,
  folded into the job-package PDF.

### Added — wiring depth
- **`pinouts.py` + `/api/pinouts`** — extracts **connector pinouts + wire colors** ("J5 pin B = ground, white/black")
  from schematic/wiring text so a mechanic can check continuity at the right pins. (Symptom→circuit fault isolation is a
  noted follow-up.)

### Added — people (young + seasoned mechanics)
- **`training.py` + `/learn` + `/api/quiz`** — a cited **learn/quiz mode**: multiple-choice questions built from real
  corpus values with plausible distractors; every answer links to the page. Reproducible with a seed.
- **`fieldnotes.py` + `/api/notes`** — cited **field-note annotations** on a part/procedure, on the same **append-only**
  audit store; an SME **endorses** a tip so young mechanics see which are vouched for. On `/part`.

### Ops / docs
- `VERSION` → **1.9.0**; `VERIFY-099.bat` self-tests + completeness-checks all six new modules. Palette gains a
  Learn/quiz entry. Dark diagram `docs/diagrams/190-serviceability-kit-training.{svg,pdf,png}`.
- **Deferred (noted follow-ups):** fleet-commonality finder, service-interval / fluids-matrix readiness, and wiring
  fault isolation.

---

## [1.8.0] — 2026-07-02 — R13 trust layer: validation · integrity · human sign-off · TM currency · verification cockpit
The first batch built explicitly under **R13 (above military grade)**: raise the *trust, verification, and
resilience* of the whole app. Additive & rollbackable (R1); read-only except the append-only signoff sidecar. No new deps.

### Added — trust & accuracy
- **`validate.py` + `/api/validate`** — physical-plausibility + OCR-garble checks on every extracted value; impossible
  or garbled numbers are **quarantined** (held, never shown as fact), borderline ones flagged **suspect**. Bands are
  generous so legitimate values never false-alarm. **Wired into `/part`**: a red data-integrity banner withholds bad data.
- **`trust.py`** — one canonical trust level (high / medium / review / low / **quarantined**) folded from source +
  confidence + validation, so a chip means the same thing everywhere.
- Redundant independent checks: `conflicts.py` (cross-manual disagreement) + `validate.py` (plausibility) together give
  defense-in-depth accuracy. (Cross-*method* agreement is a noted follow-up.)

### Added — verification made measurable
- **`verifystate.py` + `/verify`** — the verification cockpit: reads the last host-side `VERIFY-099` log, the 39-module
  self-test roster, and which sidecars are built → one "what have we proven?" view, with DB-integrity status.
- **`tests/test_accuracy.py`** — measured extraction accuracy against a hand-verified ground-truth set (recall/precision
  with a regression floor). Wired into `VERIFY-099`.

### Added — human authority & auditability
- **`signoff.py` + `/review` + `/api/signoff`** — SME review queue: submit a low-confidence value → an expert
  approves / rejects / **overrides**, and it becomes verified & locked. **Append-only** store = a permanent
  who / what / when audit trail (nothing is ever updated or deleted).
- **`tmrev.py` + `/api/tmrev`** — TM revision / currency: parses change number + date and flags when a **newer revision**
  of a manual exists, so no one works from a superseded book.

### Added — resilience
- **`integrity.py` + `/api/integrity`** — SQLite corruption detection (integrity_check), SHA-256 tamper-evidence,
  a file manifest with change/corruption detection, and **online-safe backup**. Surfaced in the cockpit.

### Ops / docs
- `VERSION` → **1.8.0**; `VERIFY-099.bat` self-tests + completeness-checks all six new modules and runs the accuracy
  harness. Every new pure module self-tested in-sandbox. Palette gains Verify / Review / (Ask) entries. Dark diagram
  `docs/diagrams/180-r13-trust-verify.{svg,pdf,png}`. Governed by [[rule-above-military-grade]] (R13).

---

## [1.7.1] — 2026-07-02 — Live end-to-end route coverage + guided first-run launcher
### Added
- **`tests/test_routes.py`** — extended the live route smoke test to cover every v1.4–1.7 endpoint (partsummary,
  conflicts, faulttree, ask, search_hybrid, command_status, dimscad, publog / publog_stats / publog_intel /
  publogdiff, callout_numbers, dimscan, figureparts, jobpack, specsheet) **and** the new pages/scripts (/part,
  /troubleshoot, /ask, /command, /publog, /scan, /exploded, /binaudit, /mastercov, scanner.js, readaloud.js). The
  test spins up the real server against the fixture index and asserts **no 5xx** + valid JSON on `/api/*` — so a
  wiring bug in any new route is caught host-side by `VERIFY-099.bat`.
- **`START-HERE.bat`** — a guided first-run launcher that walks a new machine through the whole setup in order:
  INSTALL → VERIFY-099 → BUILD-PUBLOG → RESUME-OCR → RUN-VIEWER (each step safe to re-run). CRLF.
- `VERSION` → **1.7.1**. Test-only + tooling; no app-behavior change (R1).

---

## [1.7.0] — 2026-07-02 — Unified part page + job-package PDF · guided troubleshooting · conflict checker · offline Q&A · read-aloud · command center
An app-wide batch aimed at net-positive leverage. Additive & rollbackable (R1); read-only (R6). No new deps.

### Added — one authoritative part page + the complete job package
- **`/part`** — a single fast pane per part that fuses identity, supersession alerts, parts-to-order, key dimensions,
  torque, cautions, the procedure, the approximate 3-D model, and a **cross-manual conflict** banner. Backed by one
  call, **`/api/partsummary`**.
- **`jobpack.py` + `/api/jobpack`** — the **complete job-package PDF**: identity + PUBLOG + alerts + parts + dims +
  torque + cautions + full procedure, all cited, in one printable. Buttons on `/part` and `/dossier`.

### Added — guided troubleshooting + safety conflict checker
- **`faulttree.py` + `/troubleshoot`** — parses the manuals' MALFUNCTION → check → CORRECTIVE-ACTION structure into
  interactive **fault trees**: pick a symptom, step through the checks, land on the fix (→ procedure / part). Cited.
- **`conflicts.py` + `/api/conflicts`** — flags where two manuals **disagree** on a torque/pressure/dimension for the
  same part, each value cited, severity-ranked (safety-critical). Surfaced as a red banner on `/part`.

### Added — offline cited assistant + hands-free
- **`ask.py` + `/ask`** — offline, **extractive, cited** Q&A over the corpus (semantic + keyword retrieval → the exact
  answering sentences with their page). No network, no LLM, nothing invented.
- **`readaloud.js`** — native offline **read-aloud** (SpeechSynthesis) of any page + **voice input** on the search box
  (SpeechRecognition, best-effort). Auto-injected app-wide by `palette.js`; both degrade silently if unsupported.

### Added — command center + hardening
- **`/command` + `/api/command_status`** — one "are we complete?" cockpit: OCR %, corpus coverage, PUBLOG build state,
  and Masterfile dimensional gaps at a glance.
- **`tests/test_newmodules.py`** — property/fuzz hardening across the pure v1.5-1.7 modules (publogdiff, dimscad,
  conflicts, faulttree, ask, hybrid, jobpack); **verified 0 crashes over 3,000+ hostile cases per target** in-sandbox
  and wired into `VERIFY-099.bat` (runs 4,000/target host-side).

### Ops / docs
- `VERSION` → **1.7.0**; `VERIFY-099.bat` parses + completeness-checks + self-tests `jobpack` / `conflicts` /
  `faulttree` / `ask` and runs the new fuzz suite. Dark diagram `docs/diagrams/170-partpage-solve-ask.{svg,pdf,png}`.

---

## [1.6.0] — 2026-07-02 — Look-alike intelligence from PUBLOG + approximate 3-D from dimensions
Turns "these two parts share a name" into a grounded, decisive answer, and gives every part a dimensional
3-D sketch. Additive & rollbackable (R1); corpus + PUBLOG CSVs read-only (R6). Needs `BUILD-PUBLOG.bat` (now
loads five more FLIS tables); degrades gracefully until then.

### Added — extended PUBLOG loader
- `build_publog.py` now also ingests **V_FLIS_STANDARDIZATION** (ISC + related NSN — the I&S interchangeability
  family), **V_MOE_RULE** (AAC — acquisition/obsolescence), **V_FLIS_PHRASE** (TECH_DOC_NBR — the manual that
  references a part), **V_H6_RELATED** (related item names), and the **CAGE status** column. All NIIN-keyed, indexed.

### Added — `publogdiff.py` (authoritative look-alike intelligence) + `/api/publogdiff` + `/api/publog_intel`
- **Characteristics diff + fit-fingerprint** (bundle 1): align two NIINs' `V_CHARACTERISTICS` by MRC, highlight only
  the rows that DIFFER, and score a % similarity ("94% identical — differs in output current").
- **Interchangeability verdict** (bundle 2): GREEN fully interchangeable (shared I&S family) / AMBER one-way
  substitute (supersession) / RED not interchangeable — with the reason. Plus a **substitution finder** ("use these
  instead") and a **supersession/obsolescence guard** (AAC terminal codes + replaced-NIIN chain).
- **Reference-number confidence** (bundle 3): decode each part number's **RNCC/RNVC** (exact match vs "similar, may
  differ"), and flag **inactive-vendor** variants via CAGE status.
- **PUBLOG↔TM cross-link + nickname reconciliation** (bundle 4): jump from a part to the manual that references it
  (`TECH_DOC_NBR`); map shop-floor colloquial + related-item names and **warn on nickname clashes**.
- Surfaced on **`/publog`** (supersession/vendors/tech-docs/nicknames cards + a "⇄ Compare" box) and a new
  scanner-powered **`/binaudit`** page: scan a shelf of NSNs and it flags look-alike groups and superseded items.

### Added — `dimscad.py` (approximate 3-D / CAD from dimensions) + `/api/dimscad`
- Parses **named dimensions** from PUBLOG characteristics ('OVERALL LENGTH' → '3.00 IN', 'DIAMETER' → '.50 IN'),
  picks a parametric primitive (cylinder / box / washer / hex), and emits a **dimensioned isometric SVG** preview plus
  a **parametric OBJ mesh** (`?obj=1`) that drops into the existing 3-D library. Shown as an "Approximate model (from
  dimensions)" card on `/dossier`. Clearly labelled a sketch — never a substitute for the cited figure.

### Ops / docs
- `VERSION` → **1.6.0**; `VERIFY-099.bat` parses + completeness-checks + self-tests `publogdiff.py` and `dimscad.py`
  (both pass in-sandbox). `scanner.js` gained a `window.onScan` hook so pages (bin audit) can capture scans. No new
  Python deps. Dark diagram `docs/diagrams/160-lookalike-publog-dimscad.{svg,pdf,png}`.

---

## [1.5.0] — 2026-07-02 — PUBLOG catalog · hand-scanner & camera · hybrid search · exploded/assembly view
A five-lane batch (Chris picked all four suggestions + the hand-scanner requirement). Additive & rollbackable (R1);
corpus and the PUBLOG CSVs are read-only (R6).

### Added — PUBLOG / FLIS federal catalog (authoritative, offline)
- **`build_publog.py` + `BUILD-PUBLOG.bat`** — a HOST-side streaming loader that indexes the DLA PUBLOG/FLIS CSV export
  (~17M NSNs / ~16.5M part rows, ~16 GB) into a compact NIIN-keyed **`index/publog.db`**: nomenclature + FSC class
  title, the manufacturer **part numbers** behind an NSN and the **CAGE** (vendor) behind each, item
  **characteristics** (the real basis for telling look-alike parts apart), weight/cube, colloquial names, and the
  **cancelled/replaced-NIIN** chain. Constant-memory (row-streamed), indexes built after load, rebuildable.
- **`publog.py` + `/api/publog`** — read-only query layer: NSN/NIIN lookup **and** reverse lookup by manufacturer part
  number (`?pn=`). New **`/publog`** page + an authoritative **Federal-catalog card on `/dossier`** + palette entry.
  Fully offline, no links (R11). Degrades gracefully until the sidecar is built.
- **Verified against the real export:** NSN 8940-00-000-0042 → "CK FILTER ASSEMBLY", P/N UK 60A890216 (CAGE 24039),
  characteristic "USED ON ALM F13 AIRCRAFT", weight/cube, and the reverse part-number lookup all resolve.

### Added — Hand scanner & camera scan-in (bay floor)
- **`scanner.js`** — a global keyboard-wedge listener: it recognizes a handheld barcode/QR scanner's fast-burst-then-
  Enter signature on ANY page and routes the scanned NSN/NIIN or manufacturer part number straight to the catalog.
  Auto-injected app-wide by `palette.js`, so it works everywhere with no per-page edits.
- **`/scan`** page — offline in-browser camera scanning via the native `BarcodeDetector` API (QR, Code128/39, EAN,
  DataMatrix, ITF, Codabar) with manual entry and a graceful fallback when unsupported.

### Added — Hybrid + glossary search
- **`hybrid.py` + `/api/search_hybrid`** — (1) corpus-wide **acronym/glossary query expansion** (so 'CTIS' also matches
  'Central Tire Inflation System'), (2) **Reciprocal-Rank Fusion** of the keyword (FTS) hits with the semantic
  (embeddings) hits, (3) fuzzy **"did you mean" NSN** correction grounded in the PUBLOG catalog. Each degrades on its
  own: no embeddings → keyword-only; no PUBLOG → no NSN suggestions; no glossary → no expansion.
- The main **`/api/search`** now attaches acronym hints + NSN "did you mean" (never alters ranking), surfaced as a small
  hints bar above results on the home page.

### Added — Exploded / assembly view (brief-req C+D)
- **`/exploded`** (alias `/assembly`) — pick a figure (by part, or doc/page) and its callouts become numbered
  **hotspots** while its parts become a **step-through assembly order**; toggle **disassembly** to reverse it, and
  overlay the figure's **dimension lines**. Composes the existing figure/callout/dimscan/locate endpoints; each part
  deep-links to its dossier, how-to, and catalog record. `/api/callout_numbers` now returns image dims (`iw/ih`) so
  hotspots scale exactly. Linked from `/dossier` and the palette.

### Ops / docs
- `VERSION` → **1.5.0**; `VERIFY-099.bat` now parses, completeness-checks, and self-tests `publog.py`, `build_publog.py`,
  and `hybrid.py`. `segno` stays the only added dependency (from 1.4.0); PUBLOG/scanner/hybrid/exploded add none
  (stdlib csv/sqlite + native browser APIs). Dark diagram `docs/diagrams/150-publog-scanner-search.{svg,pdf,png}`.

---

## [1.4.0] — 2026-07-02 — Bay-floor batch: kiosk mode · offline QR · spec-sheet & coverage · confidence · ops polish
A four-lane upgrade requested together. All additive & rollbackable (R1); the corpus stays read-only (R6).

### Added — Bay-floor UX (lane: QR + kiosk)
- **`qrgen.py` + `/api/qr`** — offline QR codes for a part / NSN. The QR encodes a deep-link to that part's
  **dossier on THIS server** (URL built from the request `Host` header), so a scan from a phone or a second bay
  tablet **on the same LAN** jumps straight to the part — no retyping an NSN. Graceful-degrade posture like the rest
  of the app: pure-python **segno** is preferred (SVG, print-crisp, zero further deps), **qrcode+Pillow** is a PNG
  fallback, and if neither is installed `available()` is `False`, the route returns a friendly 503, and everything
  else keeps working. Self-tested (deep-link builder always; render asserts a real SVG/PNG when a backend is present).
- **QR on the printable job packet** — the packet header now shows a scannable QR (hidden gracefully via `onerror`
  if no backend is installed). `segno` is now installed by `INSTALL.bat` (recommended tier) so it works out of the box.
- **Kiosk / glove mode** — a `body.kiosk-mode` class (bigger text, ≥44px touch targets, higher-contrast subtext),
  toggled from the **command palette** ("Toggle kiosk mode"), **persisted** in `localStorage`, and applied app-wide on
  load by `palette.js` (present on 29 pages). Pure CSS in `base.css`; no dependency; instantly reversible.

### Added — Masterfile spec-sheet & coverage (lane)
- **`specsheet.py` + `/api/specsheet`** — a one-page printable **leading-particulars spec sheet** (reportlab) built
  from the linkless Masterfile for a subject. Button added on `/master`.
- **`/mastercov` coverage dashboard** — subjects sorted least-covered-first, missing-dimension chips per subject, and a
  per-subject spec-sheet PDF link. Reachable from `/master` and the palette.

### Added — Confidence (lane: confidence + hybrid search)
- **Per-dimension confidence** in the Masterfile read path (`masterfile._confidence`): `high` (authoritative +
  ≥2 agreeing samples) · `medium` (single authoritative cite) · `review` (corpus values disagree widely — check the
  page) · `low` (external, unconfirmed). Surfaced on `/master` as a colored badge with a legend.
- **Deferred (follow-ups, need index builds):** hybrid keyword+semantic ranking and folding the acronym glossary into
  search — both require the embeddings / glossary build steps and are tracked, not shipped here.

### Added / Changed — Ops polish (lane: ASCII sweep + menu launcher)
- **`VIEWER-MENU.bat`** — a single menu launcher for the common tasks (INSTALL · DOCTOR · RUN · FIRST-RUN · VERIFY-099 ·
  RESUME-OCR · BUILD-MEASURES/TABLES/ENRICH/MASTERFILE/KG). CRLF, loops on a `:menu` label.
- **ASCII console guard** in `verify_ui.py` — FAILs on any `print()` containing a cp1252-incompatible character, so the
  Windows console can never crash on a stray Unicode glyph again (the `kg.py`/`gpu_check.py` `→`/`✓` class of bug).
- `VERIFY-099.bat` now parses, completeness-checks, and self-tests **`qrgen.py`** and **`specsheet.py`**; app `VERSION`
  bumped to **1.4.0** (matches this entry, R10 intent).

### Fixed
- Re-hardened both edited `.bat` files (`INSTALL.bat`, `VERIFY-099.bat`) to **CRLF** via a full heredoc rewrite after
  editing — the editor writes LF, which blink-crashes cmd.exe on `:labels`. Confirmed 56/56 and 135/135 CRLF host-side.

---

## [1.3.8] — 2026-07-02 — Fix: Tools dropdown stuck open (app-wide `[hidden]` guarantee)
### Fixed
- The **Tools** menu was permanently open, overlapping the page. Root cause: `.menupop{display:flex}` overrides the
  browser's default `[hidden]{display:none}`, so setting the element's `hidden` attribute (which the toggle JS does
  correctly) had no visual effect. The toggle logic was fine all along.
- **App-wide guarantee:** added `[hidden]{display:none !important}` to the shared **`base.css`** so the HTML `hidden`
  attribute now ALWAYS wins over any `display:` class — for every toggled menu / popover / drawer / modal, on every
  page that loads base.css. `index.html` (the Tools-menu page) is the one page that does **not** load base.css, so the
  same rule was added to its inline styles.
- **Guard so it can't recur anywhere:** `verify_ui.py` now checks that (a) base.css carries the `[hidden]` guard and
  (b) every page that toggles an element via the `hidden` attribute has that guard in effect (inline or via base.css) —
  else it FAILs. Verified: base.css OK, index.html OK.
- Additive & rollbackable (R1). New gotcha memory recorded.
### Also (resumed R12 catalog)
- **`pdfmeta.layers()`** (§5.6) — optional-content groups / layers (OCGs): name + on/off + usage. Some drawings put
  callouts / dimensions / revisions on toggleable layers; now exposed via `/api/pdfmeta`. Self-tested (Callouts on,
  Dimensions off). Catalog §5.6 → ✅.

---

## [1.3.7] — 2026-07-02 — Add the missing dependency installer (`INSTALL.bat` + `requirements.txt`)
### Added
- **`INSTALL.bat`** — the one file to double-click to install THE VIEWER's Python dependencies. There was no
  dependency installer before (only launch/build scripts), which is why e.g. `pdfplumber` was absent. Robust launcher
  (CRLF, detects `python` or `py`, `pause`s): installs the **core** packages (must succeed) and the **recommended**
  ones best-effort (a single failure just self-skips that feature), then prints the **optional/GPU** extras and the
  Tesseract-program note. Uses pip timeouts/retries so it can't hang.
- **`requirements.txt`** — the dependency manifest (core: pymupdf, reportlab, numpy, pillow · recommended: opencv-python,
  pytesseract, pdfplumber · optional: easyocr, sentence-transformers, pyzbar, lxml, camelot). Notes that Python 3.11/3.12
  is recommended (3.14 is new; a few optional wheels may not exist yet — features self-skip until they do).
- Recommended order documented: **`INSTALL.bat` → `VERIFY-099.bat` → `RUN-VIEWER.bat`** (or `FIRST-RUN.bat` to retune +
  launch). Additive & rollbackable (R1).

---

## [1.3.6] — 2026-07-02 — Fixes from the first clean host-verify run (v1.3.5 was green except these)
The full `VERIFY-099` finally ran clean host-side on the real tree (audit 0 FAIL, duplicate-route check PASS, R10
snapshot latest 1.3.5, all regression suites + 27,787 fuzz cases pass, and every previously-"500ing" route now 200 in
`test_routes`). It surfaced five specific, real issues — all fixed:
### Fixed
- **`measures.py` — leading-decimal values weren't matched.** `_NUM` required a digit before the decimal, so `.015`,
  `.002` (typical clearances/tolerances) were missed and `.015 ± .002 in` never captured a tolerance. Widened `_NUM` to
  accept a leading decimal; verified `.015 ± .002 in -> value .015, tolerance .002` while ranges/thousands still parse.
  (Real dimensional-accuracy gain; also fixes the `test_extraction` "tolerance captured" check.)
- **`kg.py` — self-test crashed on Windows.** It printed a Unicode arrow (`→`) which the cp1252 console can't
  encode. Switched to ASCII `->` (catalog roadmap §20, ASCII-safe console).
- **`callouts.py` — self-test too strict.** It hard-failed when the Tesseract binary isn't on PATH (OCR read nothing);
  now it **skips** gracefully in that case and only asserts when OCR actually returns callouts. Module behaviour
  unchanged. Also ASCII-ized its print.
- **`tables.py` / `masterfile.py` (×2) / `tables_plus.py` — false-positive completeness FAILs.** The no-truncation
  scanner flags a literal `[...]` as an omission marker; these were real docstrings describing return shapes. Reworded
  the docstrings (no behaviour change) so R9 is clean.
### Notes (environment, not bugs)
- `pdfplumber` isn't installed on the host's Python 3.14 -> `tables_plus` borderless extraction self-skips (graceful).
  `pip install pdfplumber` to enable §2.2. The fitz "pymupdf_layout" line is advisory only.
- Additive & rollbackable (R1).

---

## [1.3.5] — 2026-07-02 — Fix two duplicate route collisions + audit now catches the whole class
### Fixed — `engine/features/routes.py` (merged colliding handlers)
- **`/figcrop`** had two `@get` handlers — one for `?doc=&page=` crops (deepzoom / rpstl / xref / figures / dossier —
  the dominant callers) and one for `?name=` figcache files (visual search). In a `{path:handler}` registry the second
  silently overrode the first, so **the doc/page figure crops used all over the app were dead (404)**. Merged into ONE
  handler that branches on the param — both callers work now.
- **`/api/coverage`** had two `@get` handlers — mission-control **overview** (no params; `/coverage` + `/ops` pages)
  and **per-vehicle** (`?vehicle=`; home widget). One was dead. Merged into one handler that branches on `vehicle`.
### Added — duplicate-route guard in `engine/audit_features.py` ([0])
- The audit now scans the routes source for repeated `@get`/`@post` on the same **(method, path)** and FAILs on any
  duplicate — so this class can't silently recur. GET+POST on one path (legit read/write) is correctly not flagged.
  Verified: 101 decorators, 0 same-method duplicates after the merges.
- Additive & rollbackable (R1); no behaviour change for correct callers, only the dead ones revived. Diagram
  `148-route-dedup.pdf`. (Follows the v1.3.4 read-route graceful-degrade fix.)

---

## [1.3.4] — 2026-07-02 — Read routes degrade gracefully when an optional sidecar isn't built (no more spurious 500s)
### Fixed — error boundary (`viewer_app.py` `_dispatch`, B14)
- Investigated the HTTP-fuzz 500s reported for `/api/by_side`, `/api/chapters`, `/api/chapter_jump`, `/api/chapters_review`,
  `/api/side_uncertain`, `/api/doc`, `/api/vehicles`, `/api/partspdf`. Two findings: (1) that fuzz log was **stale** —
  it ran on **0.99.34** code (its snapshot said so), and the current `chapters`/`sides`/`browse` functions are already
  guarded (try/finally, None-returns, early exits); (2) the one legitimate way any of these still 500s is when the route
  touches an **optional sidecar table that hasn't been built yet** (THE VIEWER now has many: measures/tables/enrich/
  masterfile/kg/sides/chapters).
- The boundary now catches `sqlite3.OperationalError` with **"no such table"** and returns a clean
  `200 {ok:false, unavailable:true, "...not built yet"}` instead of a 500 — the correct response for an un-built feature,
  and it keeps the HTTP fuzz's "no 5xx" invariant. **Genuine bugs stay visible**: "no such column" (schema drift / code
  typo), locked/corrupt DB, and every non-DB exception still log + return 500 with a ref. ParamError→400 and
  FileNotFoundError→404 unchanged.
- Recommendation to the user: re-run `RUN-HTTP-FUZZ.bat` against the **current** running app for a true v1.3.4 signal;
  the earlier 500 list was from old code surfaced by a log-file collision.
### Also noted (separate, documented): two pre-existing duplicate route paths (`/api/coverage`, `/figcrop`) shadow one
handler each — see the `gotcha-duplicate-routes` memory; those are a distinct fix.
- Additive & rollbackable (R1). Diagram `147-read-route-degrade.pdf`.

---

## [1.3.3] — 2026-07-02 — Figure vision: callout-number OCR, symbol detection, VLM interface
Sixth R12 wave — the figure/vision lane, closing the non-GPU span of the catalog.
### Added
- **`callouts.py`** (§4.5) — reads the small **numeric callout labels** on exploded-view figures (Tesseract, digit
  whitelist) with their positions, and **links each callout to the nearest leader line** (from `dimscan`) so a figure
  number can be tied to its RPSTL part. `/api/callout_numbers` (distinct from the older `/api/callouts` hotspot route).
  (Self-test OCR-reads two callouts + links one to a line.)
- **`symbols.py`** (§4.8 + §4.11) — locates repeated **schematic components / safety symbols** (warning triangle,
  hazard marks) by OpenCV template matching with non-max suppression; templates are user-supplied crops in
  `index/symbols/`. No training, no GPU. (Self-test finds both warning triangles.)
- **`vlm.py`** (§10.1) — the **pluggable vision-language interface**: ask a page image a question and get an answer a
  regex/geometry pipeline can't. It does **not** bundle a model (needs a GPU + multi-GB download); drop in
  `engine/vlm_backend.py` (`ask(image, question)->str`) or set `VIEWER_VLM` and it lights up. Degrades cleanly to
  "unavailable" otherwise. `/api/vlm`. Honest ◐ (interface ✅, model host-side).
### Discipline
- Read-only; self-tested (callouts + symbols with real OCR/cv2; vlm degrade + injected backend) and wired into
  `VERIFY-099.bat`. Catalog §4.5/4.8/4.11 → ✅, §10.1 → ◐. Additive & rollbackable (R1). Diagram `146-figure-vision.pdf`.

---

## [1.3.2] — 2026-07-02 — OCR pre-processing, layout analysis, edition dedup, cross-validation
Fifth R12 wave — sharpen the foundation (cleaner OCR input, real layout) and connect the methods (dedup, agreement).
### Added
- **`ocrprep.py`** (§1.3 + §1.8) — pre-OCR image cleanup: skew estimate + correction, denoise, Otsu binarize, and
  page-orientation detection (pytesseract OSD when present). Better input = better OCR = more for every extractor. cv2,
  no GPU. (Self-test recovers an 8° skew.)
- **`layout.py`** (§2.4) — **heuristic layout analysis without a heavy ML model**: reads PyMuPDF's native block
  structure and classifies each region as title / heading / paragraph / caption / header / footer / figure by relative
  font size + page position, in reading order. `/api/layout`. Backbone that sharpens every other parser.
- **`dedup.py`** (§7.1) — edition/duplicate detection via word-shingle fingerprints + Jaccard, clustering near-identical
  editions (same TM, different change number) so the app can prefer the latest and de-dupe hits. (edition sim 0.92.)
- **`crossval.py`** (§7.5) — multi-method cross-validation: when measures / tables / leading-particulars / IETM agree on
  the same value, confidence rises (3-way = 1.0); disagreements are flagged as conflicts for review.
### Discipline
- All read-only; self-tested and wired into `VERIFY-099.bat`. Catalog §1.3/1.8/2.4/7.1/7.5 → ✅. Additive & rollbackable
  (R1). Diagram `145-foundation-crossdoc.pdf`.

---

## [1.3.1] — 2026-07-02 — Rotation-aware dimension-line scanner (the spatial-data marquee)
### Added — `engine/dimscan.py` (catalog §4.6) + `/api/dimscan`
- Detects **dimension / leader-line geometry at any angle** on a rendered drawing page (OpenCV Canny + probabilistic
  Hough), classifying each as horizontal / vertical / **diagonal (rotated)** with its length and angle — so the numbers
  that sit on rotated/vertical dimension lines (which plain OCR reads out of order or misses) can be located and, in a
  host-side pass, OCR'd **in context** and tied to the feature they measure.
- Geometry detection runs here with no GPU (cv2); the per-line number OCR is the host step (needs the OCR engine, which
  isn't bundled in this environment) — so §4.6 is ◐ (geometry ✅, number-OCR host-side). `/api/dimscan?doc=&page=`
  renders the page and returns the line summary + segments.
- Self-test detects horizontal, vertical, and ~45° rotated dimension lines on a synthetic drawing. Read-only; degrades
  to [] without OpenCV. Wired into `VERIFY-099.bat`. Additive & rollbackable (R1). Diagram `144-dimscan.pdf`.

---

## [1.3.0] — 2026-07-02 — Structured-source jackpot: IETM/S1000D XML + the knowledge graph
Fourth R12 wave — the two "big structural" methods: read already-tagged TM data, and connect every entity.
### Added
- **`ietm.py`** (§6.2) — parses **S1000D data modules / IETM / MIL-STD-40051 XML** into the same structured shape the
  PDF parsers produce: title, warnings, cautions, notes, procedural steps, tables + measurements. Namespace-agnostic
  (stdlib `xml.etree`, copes with any vendor/issue variant); degrades safely on malformed XML. `/api/ietm?doc=`. When a
  TM ships structured, this is the **richest, cleanest source of all** — no OCR, no heuristics.
- **`kg.py`** + **`build_kg.py`** + **`BUILD-KG.bat`** (§3.11 + §7.4) — a **knowledge graph** (`index/kg.db`) tying
  part ↔ figure ↔ procedure ↔ spec ↔ NSN ↔ vehicle, so "everything about X" is one hop. `build_kg.py` assembles triples
  from `viewer.db` + `masterfile.db` + figure/parts (each source guarded); `/api/kg?q=` returns a node's neighbours.
  Append-only sidecar, read-only on sources (R1/R6).
### Discipline
- Both self-tested (IETM parse against a synthetic S1000D module; graph build/query against a synthetic graph) and
  wired into `VERIFY-099.bat`. Catalog §6.2/3.11/7.4 → ✅. Additive & rollbackable (R1). Diagram `143-ietm-kg.pdf`.

---

## [1.2.3] — 2026-07-02 — Acronyms, header/footer cleanup, borderless + cross-page tables
Third R12 wave — jargon resolution, cleaner text, and the tables the ruled-only detector missed.
### Added
- **`acronyms.py`** (§3.10) — parses each TM's "LIST OF ABBREVIATIONS/ACRONYMS" into a per-manual glossary and expands
  the short forms used in the body (CTIS → Central Tire Inflation System). `find_for_doc` + **`/api/acronyms`**.
- **`pagetrim.py`** (§2.6) — statistical header/footer / running-title stripper: finds lines that recur across the
  top/bottom band of many pages and removes them so search + every extractor sees clean body text (originals untouched).
- **`tables_plus.py`** (§2.2 + §2.3) — **borderless** table extraction via pdfplumber's text-alignment strategy
  (`extract_table`, snap 8, empty-row cleaned) for the many un-ruled spec/RPSTL tables `find_tables` misses, plus
  **cross-page stitching** (merge a table that continues onto the next page; de-dups a repeated header). `/api/tables_plus`.
### Discipline
- Read-only; pdfplumber degrades to []. Modules self-tested (borderless + stitch verified against synthetic PDFs) and
  wired into `VERIFY-099.bat`. Catalog §3.10/2.6/2.2/2.3 → ✅. Additive & rollbackable (R1). Diagram `142-tables-cleanup.pdf`.

---

## [1.2.2] — 2026-07-02 — Cheap-wins bundle: safety callouts · OCR-confidence · PDF form/attachments
Second R12 wave — more of the catalog's low-cost, no-GPU methods, all feeding the mechanic views.
### Added
- **`cautions.py`** (§3.9) — WARNING / CAUTION / NOTE / DANGER blocks pulled as **severity-ranked** objects (DANGER
  first), cited to the page. `find_for_query` + **`/api/cautions`**; surfaced as a **"Safety callouts"** card on `/dossier`.
- **`textquality.py`** (§9.1) — post-hoc OCR-quality/confidence heuristic (garbage-char, vowel-less-word, stray-token
  ratios) → 0..1 score + `clean/suspect/poor` flag. Wired into `cautions.find_for_query` so a callout pulled from a
  poor-OCR page is flagged; reusable to tag any extraction and to prioritise pages for re-OCR. (clean=1.0, garble≈0.24.)
- **`pdfmeta.form_fields()`** (§5.4) — AcroForm fields on fillable IETMs / DA forms — and **`pdfmeta.embedded_files()`**
  (§5.5) — files attached inside a PDF (CAD/CSV/spec data). Both folded into `/api/pdfmeta` `summary`. fitz form-field +
  embedded-file API verified against a synthetic PDF.
### Discipline
- All read-only on the corpus; new modules self-tested and wired into `VERIFY-099.bat`. Additive & rollbackable (R1).
  Catalog status column updated (§3.9/5.4/5.5 → ✅, §9.1 → ◐). Diagram `141-cheap-wins.pdf` (+ CHANGELOG-VISUAL).

---

## [1.2.1] — 2026-07-02 — Internal provenance-audit view
### Added — `enrich.provenance_rows()` · `/api/provenance` · `/audit`
- An **operator-only** audit page that surfaces, for every external gap-fill, its **archived Wayback URL**, the original
  live URL, and the snapshot date — so you can spot-check where a value came from. This is the **one** place links are
  shown on purpose; the mechanic-facing views (Masterfile, dossier, Work Order) stay link-free (**R11 preserved**).
- Filter by subject or list everything; each value is labelled external & unconfirmed. Read-only on `enrich.db`; the
  reader tolerates pre-1.1.3 sidecars (missing `orig_url`). Added to the command palette.
- Additive & rollbackable (R1). Diagram `140-provenance-audit.pdf` (+ CHANGELOG-VISUAL).

---

## [1.2.0] — 2026-07-02 — Toward a self-standing repository: five new extractors + Masterfile intelligence
Milestone under the new **R12** mandate — pull *all* the information so THE VIEWER stands alone as an authoritative
repository. First wave of the `docs/EXTRACTION-METHODS-CATALOG.md` menu (the catalog's status column is kept current).
### Added — five new extraction modules (each self-tested, wired into `VERIFY-099.bat`)
- **`units.py`** (§3.2) — dependency-free unit conversion + dual display (`180 in → 4572 mm`, `30 ft-lb → 40.7 N-m`,
  °F↔°C, gal↔L, …) across length/torque/pressure/capacity/weight/speed/flow/area/temperature.
- **`leadingspecs.py`** (§3.6) — parses "leading particulars" **key:value** lines (`Length: 180 in`, `Fuel type: Diesel`)
  into *named* specs; numeric ones flow into the measures sidecar → Masterfile. Wired into `build_measures.py`.
- **`specparse.py`** (§3.7/§3.8) — thread callouts (`1/2-13 UNC-2A`, `M10x1.5`), fit classes, diameter±tolerance, and
  **MIL-SPEC / hardware / fuel / lubricant** references (`MIL-PRF-2104`, `MS35206`, `DF-2`, `JP-8`, `GAA`). `/api/specs`.
- **`pdfmeta.py`** (§5.1/§5.2/§5.3/§5.8) — PDF-native objects: outline (chapter tree), metadata, intra-PDF links,
  annotations — instant navigation & edition data with no OCR. `/api/pdfmeta`.
- **`barcodes.py`** (§4.9) — reads QR/Data-Matrix/1-D barcodes off page images (OpenCV QR now; `pyzbar` optional for
  1-D/DataMatrix), scraping NSNs as machine-read (higher-trust) identifiers.
### Enhanced — Masterfile intelligence
- **Dual-unit display** (`alt`) + **wide-variance flag** (`_spread`, §9.2) added to `masterfile.for_subject` at read
  time (no rebuild). New **`masterfile.coverage()`** gap dashboard + **`/api/master_coverage`** (which of the 13
  dimension types each subject is still missing).
- **`/dossier`** gains a "Specs & standards (threads · MIL-SPEC · fluids)" card (`/api/specs`) beside the dimensions card.
### Discipline
- Every module read-only on the corpus; new data append-only in sidecars/Masterfile (R1/R6/R11). Corpus authoritative.
  Additive & rollbackable (R1). Diagram `139-self-standing-extractors.pdf` (+ CHANGELOG-VISUAL). New rule **R12**.

---

## [1.1.6] — 2026-07-02 — Masterfile surfaces where the work happens (Work Order · builder · dossier)
### Enhanced — `engine/jobcard.py` · `engine/ui/jobcard.html` · `engine/ui/dossier.html`
- The consolidated dimensional data now appears in the mechanic-facing views, not just `/master`. New `jobcard._master_dims()`
  reads the Masterfile for the subject (authoritative corpus first, external labelled) with **no links**.
- **Work Order PDF** gains a "Key dimensions & specs (consolidated)" section (after Torque) — each value tagged
  authoritative vs *ext · unconfirmed*, with ranges; added to the cover contents. Cards with only dimensions still build.
- **Job Card builder** (`/jobcard`) shows a "Key dimensions" preview card (via `preview()`'s new `dimensions_sample`),
  and the readiness total counts them.
- **Part dossier** (`/dossier`) gains a lazy-loaded "Key dimensions & specs (Masterfile)" card fetching `/api/master`,
  authoritative vs external clearly marked, no links. Empty states point to `BUILD-MEASURES` → `BUILD-MASTERFILE`.
- Congruent with the existing lazy-card / preview patterns; corpus stays authoritative; no external links surfaced
  (R11). Additive & rollbackable (R1). Diagram `138-masterfile-integration.pdf` (+ CHANGELOG-VISUAL).

---

## [1.1.5] — 2026-07-02 — Integrity recovery check + regression guard for the extraction pipeline
### Verified — no code lost to truncation
- Audited every module from the v1.1 wave on disk (authoritative Read/Grep, not the sandbox's truncating cache): each
  ends at its `# END OF FILE` sentinel at the exact authored line count (`enrich.py` 334, `masterfile.py` 231,
  `measures.py` 167, `tables.py` 97, builders at theirs), all 14 `enrich` functions present, `routes.py` intact
  (171 route lines), HTML/JS closed properly, **zero** placeholder/omission markers. The truncation only ever affected
  the sandbox's read *view* of grown files — the real files were always whole.
### Added — `engine/tests/test_extraction.py` (wired into `VERIFY-099.bat`)
- Self-contained regression guard (temp DBs + fake network) for the whole **measures → tables → enrich → masterfile**
  pipeline: dimension-type coverage + compound-unit precedence (`ft-lb`/`in-lb` stay torque), range/tolerance capture,
  Wayback parse + HTML-strip + no-snapshot handling, seed scoping, **corpus-authoritative** filtering, and the Masterfile
  merge asserting **no links leak** into the view while corpus rows keep their page cite. Completeness-checked with a tail
  sentinel (R9). Additive & rollbackable (R1). Diagram `137-extraction-regression.pdf` (+ CHANGELOG-VISUAL).

---

## [1.1.4] — 2026-07-02 — The Masterfile: one congruent consolidation, no links surfaced
### Added — `engine/masterfile.py` · `engine/build_masterfile.py` · `BUILD-MASTERFILE.bat` · `/master` · `/api/master`
- A single **all-encompassing Masterfile** that merges the corpus's **authoritative** measurements (from `measures.db`,
  cited to the real TM page) with the **external** gap-fills (from `enrich.db`) into one dataset **keyed to the
  authoritative subjects** — compatible, complementary, and congruent with the existing sidecars and project.
- Two layers per subject: a **RAW** layer (every extracted value, corpus + external) and a **FILTERED** canonical layer
  (deduped representative value + numeric range + sample count per dimension). Corpus is **authoritative**: external
  values are kept only for dimension types the corpus is silent on, and a corpus value is never overridden.
- **No links surfaced.** Corpus rows keep their internal page cite (a pointer *into* the authoritative TM — desired);
  external web provenance stays inside `enrich.db` for audit only and never appears in the Masterfile or UI. The
  `/measures` external block was updated to drop the archived link and just show the value tagged *external · unconfirmed*.
- Outputs `index/masterfile.db` + a human-readable `docs/MASTERFILE.md`. New **`/master`** page shows the filtered
  summary (authoritative vs external) over the raw list, correlated to the authoritative files. Added to the palette.
- Self-test builds a mixed corpus+external fixture and asserts: correct merge, corpus-authoritative filtering (a
  conflicting external weight is dropped), a real gap (capacity) is filled, **no link leaks into the view**, and corpus
  rows keep their authoritative page ref while external rows carry none — **passes**. Read-only on sources; append-only
  rebuildable sidecar (R1/R6). Additive & rollbackable (R1). Diagram `136-masterfile.pdf` (+ CHANGELOG-VISUAL).

---

## [1.1.3] — 2026-07-02 — Route every link through the Wayback Machine; harvest from many sources
### Enhanced — `engine/enrich.py` · `engine/build_enrich.py` · `ENRICH.bat` · `/measures` · seed/search plumbing
- The gap-fill crawler now pulls candidate links from **many sources per subject** — Internet Archive full-text items,
  **web-search results** (optional host plugin `engine/enrich_search.py`), and a user **seed list** (`index/enrich_seeds.txt`,
  `subject | url` scoped or bare = global) — and **routes every one of them through the Wayback Machine** before extraction.
- New `enrich` primitives: `wayback_save` (Save Page Now), `wayback_get_or_save`, `fetch_via_wayback` (archived text +
  `strip_html`), `seed_links`, `web_links` (injected search fn — keeps the app offline/provider-agnostic). `--save`
  triggers Save Page Now for links the archive hasn't captured; `--maxlinks` caps links/subject.
- Provenance strengthened: each external value now stores the **archived Wayback URL** (`source_url`) *and* the original
  live URL (`orig_url`, new column; auto-migrated on existing sidecars) *and* the snapshot timestamp. `/measures` shows
  the value with its **archived-snapshot date + source domain**, linking to the pinned Wayback copy.
- **Live-verified end-to-end:** real searches (HMMWV M998, M35A2) → found links → **Wayback availability confirmed for
  every link** → archived-source text → the measurement engine recovered **34 measurements** (weights, lengths,
  capacities, rpm, volts/amps, speed, angle, power) from one HMMWV spec page alone. New `enrich` functions self-test
  (wayback-route + HTML-strip + Save-Page-Now fallback + subject-scoped seeds) — **passes**.
- Unchanged guarantees: corpus is **authoritative** (external only fills missing types, never overrides); app stays
  **100% offline** (network only in the opt-in `ENRICH.bat`); append-only `enrich.db`, corpus untouched (R1/R6).
  Additive & rollbackable (R1). Diagram `135-wayback-everything.pdf` (+ CHANGELOG-VISUAL).

---

## [1.1.2] — 2026-07-02 — External gap-fill: cross-reference the internet to complete dimensional data (corpus authoritative)
### Added — `engine/enrich.py` · `engine/build_enrich.py` · `ENRICH.bat` · `/api/external` · external section on `/measures`
- **The corpus is always the authoritative/default source.** New enrichment layer cross-references the **open internet**
  — Internet Archive full-text search + the **Wayback Machine** + any given source URL — **only to fill blanks**:
  dimension/measurement types a part or vehicle has **no** corpus value for. External values **never** overwrite or
  contradict a corpus value, are surfaced **only** for types the corpus is silent on, and are always badged
  *external-unconfirmed* with full **provenance** (source, exact URL, Wayback snapshot timestamp, fetched time).
- **The running app stays 100% offline.** The network is touched *only* by the opt-in, host-run crawler
  (`ENRICH.bat` → `build_enrich.py`), which writes the **append-only** `index/enrich.db` sidecar (R1/R6). The server and
  `/api/external` only ever **read** that sidecar — no network from the app process.
- `find_gaps()` computes missing dimension types per vehicle (from the measures sidecar, or a live fallback);
  the crawler searches IA, pulls each item's text layer, extracts with the **same** `measures` engine, and records only
  the gap types. Injectable network layer → deterministic self-test (Wayback/IA parse, gap-only record,
  corpus-authoritative filtering, provenance) — **passes**. Real IA/Wayback API shapes verified live before coding.
- `/measures` now shows a clearly separated **"External references — unconfirmed"** block beneath the cited corpus
  values, passing the corpus's answered types as `have=` so authoritative dimensions are filtered out. Additive,
  rollbackable (R1). Diagram `134-external-enrichment.pdf` (+ CHANGELOG-VISUAL).

## [1.1.1] — 2026-07-02 — Structured-table extraction (RPSTL / spec / leading-particulars)
### Added — `engine/tables.py` · `engine/build_tables.py` · `BUILD-TABLES.bat` · `/api/tables`
- Pulls **structured tables** out of every PDF page via PyMuPDF `find_tables` — RPSTL rows, torque/PMCS grids, and
  especially **leading-particulars / specification** tables where dimensional data lives. Flags a table as
  **spec/dimension** when its cells carry measurement units (via `measures`), so a mechanic jumps straight to the numbers.
- `/api/tables?doc=&page=` extracts on the fly; `BUILD-TABLES.bat` → `build_tables.py` builds an append-only
  `index/tables.db` sidecar (read-only on the corpus — R1/R6) recording which pages hold spec tables. Resumable per doc.
- Self-test extracts a ruled 3×3 spec table and flags it correctly (host-side, where `measures` imports whole).
  Additive & rollbackable (R1). Diagram `133-tables.pdf` (+ CHANGELOG-VISUAL).

## [1.1.0] — 2026-07-02 — Measurement & dimensional-data extraction (100%-coverage push)
### Added — `engine/measures.py` · `engine/build_measures.py` · `BUILD-MEASURES.bat` · `/measures` · `/api/measures`
- Beyond OCR text: a dedicated extractor pulls **every measured quantity** out of the manual text — length, diameter,
  clearance/**tolerance**, weight, force, torque, pressure, volume/capacity, temperature, electrical (V/A/Ω/W/Hz), flow,
  speed, rotation, angle, thread — each with value(s), **range** (`X–Y`), **tolerance** (`X ± Y`), canonical unit,
  dimension type, the sentence it came from, and its **cited page**. Unit ordering makes compound units win
  (`ft-lb`>`ft`, `in-lb`>`in`, `N-m`>`N`).
- New **`/measures`** page: search a part/vehicle → all measurements grouped and **filterable by dimension type**, each
  linking to its cited page. Works **live over the existing FTS index — no build step required** (`find_for_query`).
- `BUILD-MEASURES.bat` → `build_measures.py` optionally builds an append-only `index/measures.db` sidecar for
  corpus-wide browsing/counts (read-only on `viewer.db` — R1/R6). Resumable per doc.
- `docs/EXTRACTION-COVERAGE.md` — a full map of **every** extraction/parse/detection method in the system (native text,
  OCR, tables, measurements, vector text, RPSTL/NSN, perceptual hash, embeddings) and what each covers, plus known gaps.
- Self-test extracts 19 measurements across all target dimension types — **passes**. Additive & rollbackable (R1).
  Diagram `132-measures.pdf` (+ CHANGELOG-VISUAL).

---

## [1.0.0] — 2026-07-02 — First stable cut
### The 1.0 line: everything from the 0.9x waves, verified green and stamped
- `CUT-V1.0.bat` / `engine/cut_v1.py` took a pre-1.0 safeguard snapshot, stamped `VERSION=1.0.0`, and regenerated the
  iteration snapshot (R10) after `RUN-ALL-VERIFY` was clean. The legacy track was bannered `[1.0.0-legacy]` in
  `CHANGELOG-LEGACY.md`. Pillars at 1.0: offline TM search + dynamic GUI; procedure/Job-Card/PMCS/torque/fastener
  mechanic tools; look-alike part disambiguation; CAD imagery + Living Schematic + Circuit Lab; visual & semantic
  search; command palette; full R1–R10 discipline (backwards-compatible, diagrammed, changelogged, snapshotted).
- Human-facing notes in `docs/RELEASE-NOTES-1.0.md`. Additive & rollbackable (R1). *(Recorded on the modern track
  retroactively during the v1.1 wave — the cut happened, the modern banner had not been written.)*

---

## [0.99.35] — 2026-07-02 — Host-verify actually ran — fix the two issues it surfaced
### The milestone: `VERIFY-099.bat` finally executed host-side and came back GREEN
- The audit was clean (0 FAIL/0 WARN, all 28 pages + every new module import), R10 snapshot integrity OK, and **all
  regression suites passed** — features (21), integration (16), modules (20), jobcard (21), congruency (26),
  property-fuzz (27,787 cases w/ Hypothesis), routes (59), search-quality (15), hardening (12) + the four new-module
  self-tests. Task-#8 host-verify: done.
### Fixed — two real issues the run exposed
- **`VERIFY-099.bat` / `RUN-ALL-VERIFY.bat` CMD parsing** — the body was wrapped in a `( … )` block, and parentheses in
  `echo`/`python -c` lines broke it (`"--- was unexpected at this time"`). This is why every earlier host-verify
  attempt silently failed. Restructured to a **`call :body > log` subroutine** (no block paren-parsing); orchestrator
  uses plain sequential commands.
- **`engine/tests/test_http.py`** crashed with `IndexError: choice from empty sequence` — it read the route registry
  without importing `viewer_app`, so routes weren't registered. Now imports `viewer_app` first + guards the empty case.
- Dropped the redundant `verify_complete.py ui\palette.js` line (its naive bracket-counter false-flags brackets inside
  strings/regex; `verify_ui.py`'s `node --check` — which reports `palette.js : OK` — is authoritative). Additive (R1).

## [0.99.34] — 2026-07-01 — Release prep: one-click verify orchestrator + v1.0 cut tooling
### Added — `RUN-ALL-VERIFY.bat` · `CUT-V1.0.bat` + `engine/cut_v1.py` · `docs/RELEASE-NOTES-1.0.md`
- **`RUN-ALL-VERIFY.bat`** — one double-click runs every host-side verification + the quick index build in order
  (VERIFY-099 → HTTP fuzz → mutation → visual-index), logging to `docs/run-all.log` and echoing PASS/FAIL. The
  long jobs (OCR / embeddings / installer) stay separate on purpose.
- **`CUT-V1.0.bat` + `engine/cut_v1.py`** — after verify is clean: safeguard snapshot, stamp `VERSION=1.0.0`, banner
  both changelogs with a `[1.0.0]` entry, and regenerate the iteration snapshot so it still matches (R10). Refuses to
  re-cut if already 1.x; prompts before committing.
- **`docs/RELEASE-NOTES-1.0.md`** — the human-facing 1.0 release notes (pillars, under-the-hood, the run-before-1.0
  checklist). Verified: `cut_v1.py` parses + completeness-clean. Additive & rollbackable (R1). Diagram `131-release-prep.pdf`.

## [0.99.33] — 2026-07-01 — "Most used here" home panel (surfaces the usage analytics)
### Added — home-page most-used panel (`engine/ui/index.html`)
- Completes the analytics feature (0.99.24): a **"Most used here"** section on the home page pulls `/api/analytics_top`
  and shows your most-frequent searches (🔎 → runs the search) and parts (🔩 → opens the dossier), each with a hit
  count. Hidden until there's data, so it stays clean on a fresh install and fills in as the palette beacon logs usage.
- Purely additive: one section in `loadHome()` + one `loadMostUsed()` fetch; ES5, offline, reads the local analytics
  sidecar only (R1/R6). Visual coverage: diagram `130-quality-ops.pdf`.

## [0.99.32] — 2026-07-01 — One-click packaged installer (run on a shop PC, no Python)
### Added — `viewer.spec` + `BUILD-INSTALLER.bat` + `FIRST-RUN.bat`
- PyInstaller spec bundles the app + `ui/` + all feature/module hidden-imports into `dist\THE_VIEWER\THE_VIEWER.exe`
  so THE VIEWER runs on a bay-floor PC with **no Python install**. `BUILD-INSTALLER.bat` builds it (host, one-time
  internet for PyInstaller). `FIRST-RUN.bat` points the exe at the corpus/index, deletes `hardware_profile.json` to
  **re-tune to that machine**, runs the doctor, and launches. Corpus/index stay external (not bundled). Additive (R1).

## [0.99.31] — 2026-07-01 — Mutation testing extended to the new pure modules
### Changed — `RUN-MUTATION.bat` (test-quality metric)
- Added mutation targets for **figureparts.py** and **jobcard.py** (oracle: `test_jobcard.py`) and **coverage.py**
  (oracle: `test_property_fuzz.py`) using the existing `tests/mutate.py`. Surviving mutants = test blind-spots; a true
  measure of whether the suite actually *catches* bugs, before v1.0. Host-side → `index\MUTATION-RESULTS.txt`.

## [0.99.30] — 2026-07-01 — HTTP-level integration + fuzz harness
### Added — `engine/tests/test_http.py` + `RUN-HTTP-FUZZ.bat`
- Spins the **real app** on a test port against a tiny synthetic index, hits **every registered GET route** (bare +
  adversarial params), and asserts the server **never returns a 5xx** and `/api` responses parse as JSON — real
  request-path coverage complementing the unit/property fuzz. Host-side (needs the app importable). Additive (R1).

## [0.99.29] — 2026-07-01 — Offline semantic search (framework)
### Added — `engine/embed.py` + `/api/semantic` + `/semantic` + `BUILD-EMBEDDINGS.bat`
- Meaning-based search over the OCR text: uses a **local sentence-transformers model** when installed (true semantic),
  else a **deterministic hashing fallback** so it works offline with zero downloads. `BUILD-EMBEDDINGS.bat` builds
  `index/embeddings.npy` host-side; `/semantic` queries it (cosine top-k), shows the active backend, and prompts to
  build if the index is absent. **Verified in-sandbox:** self-cosine=1.0; related text 0.730 > unrelated 0.000 (fallback).
  Wired: 🧠 in palette + Tools menu + verify_ui. Diagram `128-search-discovery.pdf`. Additive (R1).

## [0.99.28] — 2026-07-01 — Visual part search (perceptual hash)
### Added — `engine/phash.py` + `POST /api/visualmatch` + `/visual` + `/figcrop` + `BUILD-VISUAL-INDEX.bat`
- Snap/drop a **photo of a part** → closest figure crops by 64-bit **DCT perceptual hash** + Hamming distance (pure
  numpy/PIL, offline, no model). `BUILD-VISUAL-INDEX.bat` hashes `index/figcache` → `index/phash.tsv`; `/visual`
  uploads the image as base64 (JSON POST) → `phash.match`; `/figcrop?name=` serves the matched crop. **Verified
  in-sandbox:** identical/resized image → distance 0, unrelated → 31. Wired: 📷 in palette + Tools menu + verify_ui.
  Diagram `128-search-discovery.pdf`. Additive (R1).

## [0.99.27] — 2026-07-01 — Structured PMCS extraction (check items, not just snippets)
### Changed — `engine/pmcs.py` + `/pmcs`
- `pmcs.find` now also extracts the **individual check items** (numbered rows + CHECK/INSPECT/CLEAN/… lines), so the
  PMCS finder lists the actual checks per page, not just a snippet. **Verified in-sandbox:** pulls "check engine oil",
  "inspect belts", "ensure parking brake holds", "drain fuel/water separator"; ignores prose. Rendered as a list on `/pmcs`.

## [0.99.26] — 2026-07-01 — Parts-request PDF with scannable NSN barcodes
### Added — `engine/partspdf.py` + `GET /api/partspdf`
- Turns a part lookup into a printable **Parts Request** sheet (unit/mechanic/bumper/TM header, item table) with a
  **Code128 barcode of each NSN** so supply can scan instead of retype (local-purchase items with no NSN get no
  barcode). Pure reportlab, offline. **Verified in-sandbox** (valid PDF, barcodes rendered — `docs/partspdf_proof.png`).
  Diagram `129-bench-parts.pdf`. Additive (R1).

## [0.99.25] — 2026-07-01 — Cross-reference: related parts & assemblies
### Added — `engine/xref.py` + `/api/xref` + `/related`
- For a part: the **assemblies/figures** it belongs to, its **siblings** (other parts on the same figure), and
  **see-also** (parts in the same-titled assembly elsewhere) — each linking to the dossier / deep-zoom. **Verified
  in-sandbox** (siblings BOLT/NUT, see-also VOLTAGE REGULATOR; self-inclusion bug found & fixed). `/related` page +
  🧩 in palette + Tools menu + verify_ui. Diagram `128-search-discovery.pdf`. Additive & read-only (R1).

## [0.99.24] — 2026-07-01 — Local usage analytics (offline, privacy-preserving)
### Added — `engine/analytics.py` + `GET /api/analytics_top` + `POST /api/analytics_log`
- An append-only local JSONL (`index/analytics.jsonl`) of what got looked at — never leaves the machine, no accounts.
  Powers a most-used view and `hot_docs()` to **prioritize OCR/enrichment on the documents people actually use**. The
  palette beacons page/part/torque/pmcs visits. **Verified in-sandbox** (ranking, event counts, hot-docs, bad-kind
  coercion, empty-drop — self-test green). Diagram `130-quality-ops.pdf`. Additive (R1/R6).

## [0.99.23] — 2026-07-01 — PMCS finder (jump to the maintenance-check tables by vehicle)
### Added — `engine/pmcs.py` + `GET /api/pmcs` + `/pmcs`
- Finds the **Preventive Maintenance Checks & Services** tables fast: FTS-match PMCS content, optionally filtered by
  **vehicle** (on `documents.vehicle`, not the body), dedup by doc+page, and infer the **interval** each page covers
  (Before/During/After/Weekly/Monthly/Annually) from the text. Each result cites its page and opens it in Deep-Zoom.
- **Verified in-sandbox** on a synthetic FTS index: HMMWV → 2 PMCS pages with correct intervals (Before/During/After/
  Weekly; Monthly/Annually), wrong vehicle → 0. **A real bug was caught & fixed** by the self-test — the vehicle filter
  was matching the page *body* FTS (vehicle isn't in the body); switched to `documents.vehicle LIKE`.
- `/pmcs` page + 🗓 in palette + Tools menu + `verify_ui.py`; module in `audit`/`VERIFY-099`. Read-only (R1). Diagram `127-pmcs.pdf`.

## [0.99.22] — 2026-07-01 — Fastener reference (thread sizes → dimensions → torque/usage)
### Added — `engine/ui/fastener.html` + `/fastener`
- Identify a thread by size — **major diameter (in + mm) and threads-per-inch / pitch** — for the common UNC, UNF and
  ISO metric sizes (exact standard geometry). Filter by typing (`1/2`, `3/8-16`, `M10`) or by class tab, and each row
  links to its **Torque** spec (`/torque`) and **where it's used in the manuals** (`/?q=`).
- Client-side reference table (offline, ES5); geometry is exact standard, torque deliberately deferred to the TM (a
  bold caveat says never torque to a generic chart). Wired: `/fastener` + 🔧 in palette + Tools menu + `verify_ui.py`.
  Inline JS passes `node --check`. Additive (R1). Diagram `126-fastener.pdf`.

## [0.99.21] — 2026-07-01 — My Bench (pin parts & pages you're working)
### Added — `engine/ui/bench.html` + `/bench` + a ☆ pin pill on every page
- A localStorage-backed **favorites** space: while working a job, click the **☆ pin** pill (bottom-right, next to ⌘K)
  on any page — a dossier, procedure, torque spec, figure — and it's saved to **My Bench** to jump back to instantly.
  `/bench` lists them (open / remove / clear); ★ **My Bench** is in the command palette.
- Delivered through `palette.js` (already on every page), so the pin pill + bench command reach all 20+ pages with no
  per-page edits; ES5-safe, view-persists across sessions. Wired: `/bench` route + `verify_ui.py`. Additive (R1). Diagram `125-bench.pdf`.

## [0.99.20] — 2026-07-01 — Torque quick-reference page (+ ft-lb / in-lb / N·m converter)
### Added — `engine/ui/torque.html` + `/torque` route (new mechanic feature)
- Torque is safety-critical and looked up constantly, but it was only buried inside `/procedure` and the Work Order —
  the `/api/torque` endpoint existed with **no page**. New dedicated **🔩 Torque quick-reference**:
  - Search a part / NSN / fastener → **every cited torque value** the manuals state for it, each with its sentence
    context and a **page citation** (vehicle · TM · p.N) that opens the actual page in Deep-Zoom.
  - **Live unit converter** (ft-lb ↔ in-lb ↔ N·m) — manuals mix units, so each result also shows its value converted
    to the other two, and there's a standalone converter widget at the top.
  - Parses value strings like `30–35 ft-lb`, `18 in-lb`, `45 N·m` (ranges handled) for the inline conversions.
- **Verified in-sandbox:** inline JS passes `node --check`; conversion math checked (30 ft-lb = 40.67 N·m = 360 in-lb;
  100 N·m = 73.76 ft-lb) and **a real parse bug was caught & fixed** — the unit normalizer didn't strip the middle-dot
  in `N·m`, so `45 N·m` returned null; now handled.
- Wired for discoverability (R10-style): `/torque` in `_PAGES`, **🔩** in the command palette + the 🧰 Tools menu,
  added to `verify_ui.py`. Congruent — citations link to `/deepzoom`. Additive & rollbackable (R1). Diagram `124-torque.pdf`.

## [0.99.19] — 2026-07-01 — Hardening the front door: fuzz the request param validator
### Changed — `engine/tests/test_property_fuzz.py` — the param layer (`registry.qstr/qint/qflag`) under fuzz
- The request param helpers are the app's front door: every route parses user query params through them, and their
  contract is **malformed input → `ParamError` (→ HTTP 400), never an uncontrolled exception (→ 500)**. Added a fuzz
  check that throws adversarial query dicts at them — empty lists, `[None]`, unicode digits (`٣`), underscore ints
  (`1_000`), `1e5`, `0x10`, `- 5`, 40-digit numbers, injection-looking strings, multi-value keys, missing keys — and
  asserts: only `ParamError` may escape; `qint` always returns an `int` bounded by `lo`/`hi`; `qstr` is str-or-None;
  `qflag` is bool.
- **Verified in-sandbox against the real registry: 878,583 cases, 0 leaks** — no input path 500s. No bug found (the
  front door is solid). Guarded so the harness still runs if the module is absent. Runs host-side in `VERIFY-099.bat`
  (fuzz smoke) + `RUN-HARDENING.bat` (full).
- Additive & rollbackable (R1): test-only change, no product-code touched. Diagram `123-fuzz-params.pdf`.

## [0.99.18] — 2026-07-01 — Hardening, wider: fuzz the locator + coverage math
### Changed — `engine/tests/test_property_fuzz.py` — three more pure/read helpers under fuzz
- Extended the property/fuzz harness to the remaining untested read surface:
  - **`coverage.pct(a,b)`** — `pct(a,b) ∈ [0,100]` for `0≤a≤b`, exactly `0.0` when `b==0`, never raises (high-volume,
    in the per-iteration loop).
  - **`partlocate.locate`** — `count == len(appearances) ≤ limit`; every emitted URL (`deepzoom_url`/`vectorize_url`/
    `page_url`) is absolute; appearances deduped by (doc,page,fig); never raises (DB-backed, sampled).
  - **`coverage.overview`** — never raises; every percentage-named value stays in `[0,100]` (DB-backed, sampled).
- **Verified in-sandbox against the real modules: 206,300 cases, 0 invariant violations** — no new bugs (these modules
  are solid; unlike the vectorize crash the fuzz caught in 0.99.15). The checks are guarded so the harness still runs
  where a module is absent. Runs host-side in `VERIFY-099.bat` (fuzz smoke) + `RUN-HARDENING.bat` (full).
- Additive & rollbackable (R1): test-only change, no product-code touched. Diagram `122-fuzz-locator-coverage.pdf`.

## [0.99.17] — 2026-07-01 — Offline startup fix + version banner + R10 iteration-snapshot rule
### Fixed — startup hung retrying pip over the network on the offline machine
- `engine/run_app.bat` ran `pip install --upgrade pip` **unconditionally on every launch**, which hangs on
  `ConnectionResetError(10054)` retries when offline (as seen in Chris's launch log). Replaced with an **offline-safe
  check**: a single `import fitz, reportlab, PIL` gate — the network is touched **only if a package is actually
  missing**, and then with fast-fail flags (`--disable-pip-version-check --timeout 8 --retries 1`). Normal launches now
  print "All present -- skipping install [no network touched]".
- Applied the same guard to the other runners so OCR/enrich/index resume cleanly offline too: `run_ocr_auto.bat`
  (the one `RESUME-OCR.bat` calls), `run_ocr_gpu.bat`, `run_ocr.bat`, `run_enrich.bat`, `run_indexing.bat` — the
  unconditional `pip install --upgrade pip` is removed everywhere; remaining installs stay import-guarded.

### Fixed — version banner was stale (`v0.98.0`) vs the changelog
- `engine/viewer_app.py` `VERSION` was still `"0.98.0"` while the changelog was at 0.99.16, so the running app printed
  the wrong version. Bumped to **`0.99.17`** to match the changelog top. Going forward the app VERSION tracks the
  changelog (per R10).

### Added — standing rule R10 (iteration snapshot; THE VIEWER only)
- Every iteration ships a comprehensive, **visual** snapshot of every change — tagged `FEATURE / UPGRADE / POLISH / FIX`
  — so changes can be seen and confirmed iteration-to-iteration: `docs/ITERATION-SNAPSHOTS.md` (detailed) +
  `docs/ITERATION-DASHBOARD.html` (visual, self-contained). **The snapshot MUST match the changelogs exactly — no
  exceptions.** Diagram `121-startup-fix-r10.pdf`.

## [0.99.16] — 2026-07-01 — OCR resume tooling (scan stalled at 43.8%; one-click resume + daily monitor)
### Status found — OCR stopped on June 3 at 43.8%
- Queried the live index: **53,016 done · 67,919 pending · 200 stale `running` · 1,727,330 `none`** (native text, no OCR
  needed) across 39,683 docs / ~1.85 M pages. Of the ~121,135 scanned pages that need OCR, **43.8% done, ~68,119 left**.
  The heartbeat/index/progress-log are untouched since June 3 → the scan was interrupted, not finished. **~96% of all
  pages are already searchable** (native-text + OCR'd); the gap is the remaining scanned pages.

### Added — `RESUME-OCR.bat` (project root)
- One-click resume of the GPU OCR to 100%. Delegates to the proven `engine\run_ocr_auto.bat`, which probes the GPU,
  installs the RapidOCR/onnxruntime-gpu stack, **requeues half-finished pages** (resets the 200 stale `running` locks →
  `pending` via `viewer_ingest.py` cleanup), and runs OCR in a **self-restarting loop** until 0 remain, then writes
  `docs\OCR-COMPLETION-REPORT.md`. Supports `/max` (full throughput) and `/auto` (resume at logon).

### Added — daily OCR progress scheduled task (`viewer-ocr-daily-progress`, 09:08 daily)
- Reports percent complete, pages done/remaining, and running-vs-stalled (from `ocr_progress_history.tsv` + heartbeat
  freshness — deliberately avoids a slow full-table scan), and reminds to launch `RESUME-OCR.bat` if stalled.
- **Note:** starting the multi-hour run itself must be done host-side (double-click `RESUME-OCR.bat`) — desktop
  automation could not launch it from here. Additive & rollbackable (R1); nothing writes the index from the sandbox.
  Diagram `120-ocr-resume.pdf`.

## [0.99.15] — 2026-07-01 — All recommendations + feature congruency (the meld) + R9 no-truncation gate
### Fixed — a real crash the fuzz found: `vectorize.vectorize_image` on thin images
- Extending the fuzz to the render path (rec #2) immediately falsified an invariant: a very thin image scaled by a small
  `max_dim` rounds a dimension to 0 → `cv2.resize` raises `(-215) inv_scale_x > 0`. Fixed with `max(1, int(...))`.
  **Re-fuzzed 9,000 cases incl. `max_dim=1` → holds.** New `vectorize_image` invariant added to `test_property_fuzz.py`
  (None or well-formed SVG; `1 <= max(w,h) <= max_dim`; never raises).

### Added — per-part look-alike cross-links in the Work Order (rec #3; congruent with /partdiff)
- `jobcard._flag_lookalikes` marks parts on the figures that are among the task's look-alike variants (matched by
  variant-NSN or nomenclature; **silent on NSN format-drift**, exactly like the cover warning — verified consistent).
  The PDF prefixes flagged parts with **⚠** + a note; the `/jobcard` builder shows a **⚠ compare** link to `/partdiff`
  per flagged part and a count banner. `preview()` now returns `n_lookalike_parts` + a `lookalike` flag per part.

### Added — drag-drop ingest (rec #4; honest to the server-path model)
- `/ingest` gains a real **drop-zone** (drag visuals + folder-name detection via `webkitGetAsEntry`) and **Recent paths**
  (localStorage) as one-click re-index chips. Browsers can't hand JS an absolute folder path (security), so a dropped
  folder that matches a Recent path auto-previews; otherwise it detects the folder name and guides you to paste the path.
  No upload subsystem, so the corpus stays read-only (R1/R6).

### Added — accessibility sweep (rec #5; WCAG 2.1 AA lens)
- Global **`:focus-visible`** outline in `base.css` (WCAG 2.4.7) → visible keyboard focus on every page.
- Command palette: full **combobox/listbox ARIA** (`role=listbox`/`option`, `aria-selected`, `aria-activedescendant`),
  **focus return** to the prior element on close, a **keyboard-operable pill** (`role=button`, `tabindex`, Enter/Space,
  `aria-label`), and `aria-hidden` on decorative icons.

### Added — feature CONGRUENCY test + the no-truncation gate (R9)
- `engine/tests/test_congruency.py` — asserts the new features actually mesh: the new routes/pages are registered, and
  **every cross-link a feature emits resolves to a real route** (figureparts → `/dossier`/`/locate`; palette's 22
  destinations; jobcard → `/partdiff`), plus the look-alike warning and per-part flag agree. Verified in-sandbox:
  figureparts links all resolve, **all 22 palette destinations resolve, 0 dangling**.
- **R9 (new standing rule, THE VIEWER only):** always use the no-truncation discipline. Bundled the checker into the
  project (`engine/tools/notrunc/`) and wired **`verify_complete.py`** into `VERIFY-099.bat` (host-side = true files,
  since the sandbox mount truncates/null-pads grown files). Every generated code/test file now carries a `# END OF FILE`
  tail sentinel.
- `VERIFY-099.bat` now also runs `test_congruency.py`. Diagram `119-recommendations-meld.pdf`.

## [0.99.14] — 2026-07-01 — The big push, part 2: property/fuzz hardening harness (above-military-grade)
### Added — `engine/tests/test_property_fuzz.py` + `RUN-HARDENING.bat`
- Hammers the **pure helpers** with adversarial seeds + large-N random inputs and asserts their invariants never
  break — the pre-1.0 rigor pass. Uses **Hypothesis** if installed (smart shrinking) AND always runs a stdlib fuzz so
  the tally is meaningful anywhere. Targets + invariants:
  - `jobcard._task_intent` → always `{kind∈VALID|None, verb, focus:str}`, never raises.
  - `jobcard._order_procs` → length-preserving; matching-kind items **strictly precede** non-matching; stable.
  - `jobcard._lookalike_warning` → `None`|`str`, never raises.
  - `procedures_feature._parse_procedure` → `None` or a dict with all keys; **every reference is digit-anchored**; never raises.
  - `figureparts.parts_on` → **dedup invariant** (`count == len(parts) == distinct (nsn,pn,name) keys`); never raises.
  - `patterns.norm_nsn` → **idempotent** (`norm(norm(x)) == norm(x)`).
- **`RUN-HARDENING.bat`** (host-side): best-effort `pip install hypothesis`, runs the regression suite + feature audit,
  then the fuzz (default 40k iters/property; `--max` = 1,000,000 → millions of cases) → `docs/hardening_report.txt`.
  A 3,000-iter smoke is also wired into `VERIFY-099.bat`.
- **Verified in-sandbox: 80,040 cases executed, 0 invariant violations** (figureparts run against the real module;
  the grown jobcard/parser helpers verified via verbatim standalone copies — they run host-side at full scale).
- Additive & rollbackable (R1): two new test/bat files, no product-code change. Diagram `118-hardening.pdf`.

## [0.99.13] — 2026-07-01 — Quality push, part 1: feature audit + palette QoL (Recent + discoverability pill)
### Added — `engine/audit_features.py` + `AUDIT.bat` (self-check against the exact class of bug that shipped the palette dark)
- Cross-references the **live route registry** against the UI folder to catch: a **served script included on no page**
  (the palette bug), a page route with **no file**, an **orphan page**, a **broken internal link**, or a feature module
  that **no longer imports**. Writes `docs/feature_audit.txt`; exits non-zero on any FAIL. Wired into `VERIFY-099.bat`.
- **Audit result: structurally clean** — 0 dead scripts (the earlier `?v=` cache-busted includes are correctly matched),
  0 orphan pages, 0 broken page links, all feature + top-level modules import.

### Added — palette quality-of-life (one file → all 19 pages)
- **Recent**: `palette.js` now records each tool page you open (path + `?q` + title) to `localStorage` and shows a
  **Recent** section at the top of the palette when the box is empty — jump straight back to what you were looking at.
  ES5-safe (try/catch + `URLSearchParams` regex fallback), home + the palette itself excluded.
- **Discoverability pill**: a subtle **"⌘K jump"** pill (bottom-right, hidden in print) on every page opens the palette —
  so the Ctrl+K feature is finally *findable*, not just documented.
- Verified: full `palette.js` read host-authoritatively (161 lines, balanced/closed); the new QoL blocks pass
  `node --check` in isolation. Additive & rollbackable (R1). Diagram `117-audit-qol.pdf`.

## [0.99.12] — 2026-07-01 — Hardening slice 1: permanent regression tests for the work-order stack
### Added — `engine/tests/test_jobcard.py` (wired into `VERIFY-099.bat` + host-side)
- Locks in the behaviors that were verified ad-hoc while building 0.99.8–0.99.10, so they can't silently regress:
  - **figureparts** — dedup (a part listed twice counts once), figure metadata, NSN-first ordering, dossier URLs,
    empty-page + bad-input handling (verified against the real module in-sandbox — it's small/un-grown).
  - **jobcard** — task intent (replace→Replacement, adjust→Adjustment, NSN→none), matching-kind ordering (+ no-op
    without a kind), look-alike warning (fires on real differences, silent on NSN format-drift, None when absent),
    `preview()` shape, and a `build_pdf` smoke that asserts a valid multi-page PDF with the new sections/warning.
  - **procedure parser** — materials + digit-anchored references captured, no `LOCKWASHER`/`LOOSEN` false-refs,
    tools/steps still captured, and a steps-only regression (new keys present-but-empty, not missing).
- Test file parses clean; figureparts assertions pass in-sandbox; the jobcard/parser assertions run host-side in
  `VERIFY-099.bat` (the sandbox mount truncates those grown modules). First step of the pre-1.0 hardening pass.
- Additive & rollbackable (R1): one new test module + one line in the verify batch. Diagram `116-verification-map.pdf`.

---

## [0.99.11] — 2026-07-01 — Discoverability: the command palette was DEAD — revived + wired everywhere
### Fixed — the Ctrl+K command palette was built & served but included on ZERO pages
- `engine/ui/palette.js` existed and `/palette.js` was registered, but **no HTML page loaded it** — so the Help link's
  "press Ctrl+K anywhere" did nothing. Added `<script src="/palette.js"></script>` to the **home page** (`index.html`)
  and **all 18 primary sub-pages** — `solve`, `procedure`, `dossier`, `partdiff`, `locate`, `coverage`, `jobcard`,
  `deepzoom`, `stepflow`, `packet`, `collections`, `ops`, `status`, `ingest`, `threed`, `schematics`, `circuitlab`,
  `help` (19 pages total). Ctrl/Cmd+K now actually opens the palette **everywhere**, as the Help link always claimed.
  (collections.html care: its final `</script></body></html>` was targeted, not the `'</body></html>'` string literal
  it builds for the print popup.)
- The palette's "Search" action navigated to `/?ex=` which the home page never read → **searches silently did nothing**.
  Switched to `/?q=` and added a **home `?q=` deep-link handler** (inside `palette.js`) that prefills `#q` and calls
  `runSearch` — so `/?q=<query>` from the palette (or any tool) really runs the search.

### Added — palette + Tools menu now surface the v0.99.x features
- Palette commands added: **🧾 Work Order** (`/jobcard`), **🧭 Find a part** (`/locate`), **📈 Coverage** (`/coverage`);
  typed-query actions added: Work Order for “q”, Locate “q” (alongside Search / Dossier).
- Home **🧰 Tools menu** grouped in the new mission-control tools: **🧾 Work Order · 🧭 Find a part · 📈 Coverage**.
- `verify_ui.py` extended to `node --check` external scripts too (`palette.js`, `deepzoom.js`) host-side — the sandbox
  mount truncates grown files, so these are verified in `VERIFY-099.bat`, not in-sandbox.
- Verified host-authoritatively: palette.js is 129 lines, balanced/closed; includes confirmed on home + 8 pages via the
  Read tool. Additive & rollbackable (R1): script includes + palette command rows + one menu group. No index writes.
- Diagram `115-discoverability.pdf`.

---

## [0.99.10] — 2026-07-01 — Job Card, deeper: task intent · materials/refs · look-alike warning · builder page
### Changed — `engine/features/procedures_feature.py` — richer procedure parse (additive)
- `_parse_procedure` now also extracts **materials / consumables** (MATERIALS/PARTS/EXPENDABLE/CONSUMABLE sections) and
  **referenced manuals** (TM/WP/LO/TB/TC numbers, digit-anchored regex so "LOCKWASHER"/"LOOSEN" no longer false-match).
  Two new keys `materials` / `references`; all existing keys unchanged → `/procedure` benefits too. Verified standalone
  (materials + refs captured, steps-only pages still parse with empty new keys).

### Changed — `engine/jobcard.py` — free-text tasks + two new PDF sections + a safety warning
- **Task intent:** `_task_intent("replace the alternator")` → `{kind: Replacement, focus: alternator}`; `_order_procs`
  floats procedures whose kind matches the task to the top of the work order. Handles remove/install/disassemble/
  assemble/replace/adjust/inspect/repair/service synonyms. Verified (replace→Replacement, adjust→Adjustment, ordering).
- **Materials & referenced-manuals** sections rendered per procedure; **⚠ BEFORE YOU START** warning box on the cover
  when the part has **look-alike NSNs** (`parts_feature.part_differences`) that differ by real fields (UOC/CAGEC/SMR/FSC/
  part-#) — not for mere NSN format-drift. Verified: warning fires on real variants, `None` on format-drift-only.

### Added — `GET /api/jobcard_preview` + `/jobcard` builder page
- `jobcard.preview()` returns a structured summary (intent, label/NSN, per-procedure step/tool/material/caution counts +
  refs, torque sample, parts sample, figure count, warning) **without** building the PDF.
- **`/jobcard`** — a builder page: type a task → **Preview** (live counts + look-alike banner + intent chips) →
  **🧾 Generate Work Order**. `/locate`'s 🧾 button now opens this preview-first builder. Registered in `_PAGES`,
  added to `verify_ui.py`; inline JS passes `node --check`.
- Route call fixed for the new `jobcard(..., lookalike=, dpi=, max_figs=)` signature (look-alike inserted). `db_path`
  explicit; text sections + look-alike gathered by `_jobcard_gather` from the live features. Additive & rollbackable (R1).
- Diagram `114-jobcard-deep.pdf`. Host-verify bundled in `VERIFY-099.bat`.

---

## [0.99.9] — 2026-07-01 — Job Card / Work Order (the brief's requirement C, in one PDF)
### Added — `engine/jobcard.py` + `GET /api/jobcard?q=<task | part | NSN>`
- One **printable Work Order for a TASK**, not just a part. Composes the pieces the app already had into the single
  artifact a mechanic carries to the bay:
  - **Cover** — task, part label, NSN, counts, and a bold **SAFETY** disclaimer.
  - **1 · Procedures** — kind (Removal/Installation/Disassembly/Assembly…), numbered **steps**, **tools required**,
    and **WARNING/CAUTION/NOTE** callouts (orange), each **cited** to its real TM page (`procedures_feature.procedure_for`).
  - **2 · Torque values** — every stated value (ft-lb / in-lb / N·m) with its sentence context + citation, in green
    (`procedures_feature.torque_specs`).
  - **3 · Parts on the associated figures** — deduped across the task's figure pages via `partlocate` + `figureparts`
    (NSN / P-N / CAGE / SMR).
  - **4 · Figure pages** — the actual TM pages rendered with PyMuPDF (source of truth) appended after the text.
- Pure **reportlab + PyMuPDF + Pillow**, fully offline, read-only. Auto page-break with a repeating safety footer;
  dark theme (R3). `db_path` explicit; the text sections are gathered by the route from the **live** features
  (`core.db()` injected) then handed to a **pure** PDF assembler (`build_pdf`) so the assembler stays unit-testable.
- **UI:** **🧾 Work Order** button on `/locate` (beside 🖨 Figure sheet) → opens `/api/jobcard?q=<part/task>`.
- **Verified in-sandbox:** `jobcard.py` self-test built a valid **4-page** PDF from synthetic content; both text pages
  were **rendered and eyeballed** (`docs/jobcard_proof.png` cover, `docs/jobcard_proof2.png` body — procedures with
  cautions, torque, parts all correct). `locate.html` JS passes `node --check`; `jobcard.py` parses; added to `VERIFY-099.bat`.
- Additive & rollbackable (R1): one module + one route + one button. Nothing writes the index. Diagram `113-jobcard.pdf`.

---

## [0.99.8] — 2026-07-01 — Figure → Parts (the inverse of the locator; closes the navigation loop)
### Added — `engine/figureparts.py` + `GET /api/figureparts?doc=ID&page=N`
- The complement of the part **locator**: given a figure sheet (doc + page), list **every part called out on that
  page** straight from the structured parts index (nsn / part_number / name / nomenclature / cagec / smr / uoc),
  deduped, NSN-first. Each row carries a `dossier_url`, `locate_url` and `cad_url`. Read-only; `db_path` explicit.
- **Two-way navigation is now closed:** locate a part → its figures → (on any figure) **all parts on that sheet** →
  back into any of those parts' dossiers/locators. The mechanic can walk the whole figure both directions.
- **UI:** `/deepzoom` gains a **🧩 Parts on page** drawer — slides in from the right, lists the page's parts with
  NSN / P-N / CAGE / SMR, each linking to its dossier; refreshes on page-turn. Pure ES5, no new deps.
- **Verified in-sandbox:** `figureparts.py` returns the right rows with dedup (BOLT appears twice, counted once →
  fig FIG 5, count 2); deep-zoom inline JS passes `node --check`. Route is one declarative `@get` (host-verify
  bundled into `VERIFY-099.bat`).
- Additive & rollbackable (R1): one module + one route + one UI drawer. Nothing writes the index.

---

## [0.99.7] — 2026-07-01 — Figure-sheet PDF (take-to-the-bay: every figure for a part, in one doc)
### Added — `engine/figuresheet.py` + `GET /api/figuresheet?q=NSN`
- Combines the cross-figure **locator** with **page renders** into one printable **PDF**: a dark cover (part name,
  NSN, appearance count, safety disclaimer) then one page per figure — the rendered TM page + a caption
  (vehicle · TM · Fig · page). Pure `reportlab` + PyMuPDF + Pillow, offline. Read-only.
- **🖨 Figure sheet** button on `/locate` opens `/api/figuresheet?q=<part>`; 400 if q too short, 404 if no figures.
- **Verified in-sandbox:** the PDF assembler built a valid 4-page document from synthetic figures (proof
  `docs/figuresheet_proof.png` — the cover). `figuresheet.py` parses; added to `VERIFY-099.bat`.
- Additive & rollbackable (R1): one module + one route + one button. Nothing writes the index.

---

## [0.99.6] — 2026-07-01 — Mission control: coverage dashboard · part locator · doctor
*(A deep sprint on observability + navigation — turning the pile of enrichment batches into things you can SEE and USE.)*

### Added — coverage dashboard (`engine/coverage.py` · `/api/coverage` · `/coverage`)
- One read-only roll-up of how enriched the whole corpus is: **OCR %**, **CAD renders %** (v3 vs representative
  parts), **vectorized figures %**, schematic netlist pages (+ reviewed + avg confidence), documents/pages, local
  models, figure crops, and **sidecar health** (present/missing + MB). `/coverage` renders it as KPI bars + cards.
  Verified in-sandbox against a synthetic index (OCR 66.7%, CAD 100%, vectorize 50% — all correct).

### Added — cross-figure part locator (`engine/partlocate.py` · `/api/partlocate` · `/locate`)
- "**Where does this part show up?**" — enter an NSN / part number / name and get **every figure & page** in the
  corpus that calls it out (deduped, grouped by doc+page+figure), each with one-click **🔎 Deep Zoom**, **⛭ Vector**,
  and open-page links. NSN is normalized; matches part_number / nsn / name / nomenclature. Verified in-sandbox
  (3 unique appearances across 2 docs, dedup working).

### Added — project doctor (`engine/doctor.py` · `DOCTOR.bat`)
- One-shot health + inventory: dependency presence (fitz/PIL/numpy/cv2/reportlab/rapidocr/onnxruntime), **corpus-path
  reachability** (the #1 migration trap — samples stored PDF paths and flags any that moved), coverage roll-up,
  cache file counts, disk free space, recent server errors. Writes `docs/doctor_report.txt`. Parses; dep/path
  helpers verified in-sandbox.

### Verified / R1
New modules parse + logic-tested in-sandbox; new pages (`coverage.html`, `locate.html`) pass `node --check` and are
added to `verify_ui.py`; new py added to `VERIFY-099.bat`. Route registrations pending the host suite (mount
truncation). Additive & rollbackable: 3 modules + 3 pages + 4 read-only routes + 1 bat; nothing writes the index.

---

## [0.99.5] — 2026-07-01 — Corpus-wide vectorization batch (figures pre-rendered to crisp SVG)
### Added — `engine/build_vectorize.py` + `BUILD-VECTORIZE.bat`
- Pre-vectorizes **every figure-bearing page** (`parts.fig_no` → its `document_id`/`page`) into
  `index/veccache/<doc>_<page>_<dpi>.svg` via `vectorize.ensure`, so the ⛭ Vectorize view and the `/vectorize`
  route open instantly instead of rendering on demand. Writes coverage `index/vectorize_coverage.tsv`
  (doc, page, svg_bytes, contours).
- **Parallel** (one task per figure page, `cpu_count-1` capped 10 — vectorize is memory-heavier than CAD),
  **resumable** (skips pages already cached at that DPI), `--limit`/`--dpi`/`--workers`/`--serial`. Read-only on
  the index; degrades cleanly if OpenCV is absent.

### Verified
`build_vectorize.py` parses; reuses the 0.99.4 vectorizer (already proven — `docs/vectorize_proof.png`). Full run is
the user's to kick off (like the CAD / schemgraph batches); host-verify the module import via `VERIFY-099.bat`.
Additive & rollbackable (R1): one script + one bat; sidecar SVG cache + coverage TSV only.

---

## [0.99.4] — 2026-07-01 — Offline line-art vectorization (the deferred 0.99.3 piece, now built)
*(Completes thread #4: a scanned figure/schematic → crisp SVG that stays razor-sharp at any deep-zoom, and prints/recolours cleanly.)*

### Added — `engine/vectorize.py` + `GET /vectorize`
- **Potrace-style vectorization, fully offline** (OpenCV `cv2` + numpy + Pillow — the OCR stack already ships cv2;
  no CDN, no external binary). Otsu-binarize the ink → `findContours(RETR_CCOMP)` → `approxPolyDP` simplify →
  emit one **even-odd-filled SVG path** (holes handled). Tuned to **keep thin detail** (hatching, thin lines, text):
  no median-blur by default, `min_area 1.5`, `simplify 0.9`.
- `GET /vectorize?doc=ID&page=N&dpi=200` renders the page (fitz), vectorizes it, caches the SVG to
  `index/veccache/<doc>_<page>_<dpi>.svg`, and serves `image/svg+xml`. Degrades to **503 JSON** if cv2 is absent
  (never a 5xx). `available()` gate.
- `deepzoom.html` gains a **⛭ Vectorize** button → opens the SVG, which the browser renders **infinitely crisp** at
  any zoom (the natural partner to the raster deep-zoom).

### Verified
- Core logic run in-sandbox on synthetic line-art: **18 contours**, faithful reproduction incl. hatching + text —
  proof `docs/vectorize_proof.png` (raster → vector, side by side). `vectorize.py` added to `VERIFY-099.bat`'s
  syntax check; route + button pending the host suite (mount truncated the grown files, per the standing gotcha).
- Additive & rollbackable (R1): one new module + one route + one button; sidecar SVG cache only (index untouched).

---

## [0.99.3] — 2026-07-01 — Offline deep-zoom + callout hotspots
*(The old 0.26/0.41 "Next" imagery backlog, finally built — the last of the four "all of the above" threads.)*

### Added — `engine/ui/deepzoom.js` + `/deepzoom` page
- **Dependency-free deep-zoom** (no OpenSeadragon, no CDN — fully offline). A canvas renders the page and, as you
  zoom in, **upgrades the source render to a higher DPI on demand** (150→300→600→1000 via `/page?dpi=N`) so pixels
  stay crisp. Drag-pan, cursor-centred wheel-zoom, pinch, dbl-click fit — same proven pattern as `cadview.js`.
- **Callout hotspots:** overlays `/api/callouts` as numbered markers at each anchored NSN/PN/figure box; click a
  number to jump to the part (`/dossier?q=` / `/partdiff?q=`). Toggle with ⌖.
- New page **`/deepzoom?doc=ID&page=N`** (`deepzoom.html`) with page nav + doc title; a **🔎 Deep Zoom** button
  added to the schematics viewer toolbar (opens the current sheet). Registered `/deepzoom` + `/deepzoom.js`.

### Deferred (documented)
- **Line-art vectorization** (raster → vectors) is NOT built — it's a separate heavy task (potrace/ML), and
  `schem_overlay.py` already extracts *existing* PDF vectors for the schematic tools. Left as a future hook.

### Verified
`deepzoom.js` + `deepzoom.html` inline JS pass `node --check`. `deepzoom.html` added to `verify_ui.py`.
Route + schematics-button edits pending the host suite — **run `VERIFY-099.bat`** (now also checks `deepzoom.html`).
Additive & rollbackable (R1): two new UI files + two route-table lines + one toolbar button.

---

## [0.99.2] — 2026-07-01 — Standing rule R8: session handoff note
- New **`docs/HANDOFF-NOTE.md`** — a paste-ready summary of the current state + all of this session's changes +
  verification status + open backlog + how to continue on another chat/device. Written so the project can move
  between chats (e.g., USB → other PC) without losing the thread.
- **R8 (this project only):** refresh the handoff note at session end / on request, like R4's changelog. Recorded
  in project memory with an explicit scope: **do not apply R8 outside THE VIEWER**. Docs-only; rollback = delete
  the note + the rule memory.

---

## [0.99.1] — 2026-07-01 — Living Schematic, steps 2 & 3 + observability
*(Completes the productionization begun in 0.99.0: precompute → review → simulate, plus a coverage read-out.)*

### Added — step 2: junction/label review-override queue (`engine/schemreview.py`)
- Append-only sidecar `index/schemreviews.jsonl` (R6) — a human can mark a page's inferred netlist **good / bad /
  corrected** and drop the **component ref-designators the vectorizer missed** (CAD sheets outline label text → 0
  comps). `record / latest_for / overrides_for / queue / stats / coverage_summary`.
- Routes: **`GET /api/schemgraph_review`** (queue: pages with wires-but-no-comps or low confidence, undecided first,
  derived from the coverage TSV) + **`POST /api/schemgraph_review_decision`**. `r_schemgraph` now **merges
  overrides** into the served graph (adds the manual comps, records the verdict, bumps confidence when "good").
- `schemflow.js` gains a **⚑ Correct** mode: click the diagram to drop a missed component (prompt for ref), then
  save a verdict; a "reviewed: …" badge shows prior decisions. ES5, tiered-safe.

### Added — step 3: Living Schematic → Circuit Lab bridge (`circuitlab.html`)
- Opening `⚡ Circuit Lab` from a schematic now also fetches that sheet's inferred netlist and shows a reference
  panel (**N nets · M comps · confidence % · ⬇ inferred netlist JSON**) to build the live circuit over the page
  background. Honest scope: inference gives **topology**, and the MNA solve needs component **values** the sheet may
  not state — so this jump-starts building, it doesn't auto-simulate (documented 0.91 limitation).

### Added — observability
- **`GET /api/schemgraph_coverage`** (schematic pages, pages-with-components, avg confidence, nets total, pages
  reviewed). New suites: **`tests/test_features_modules.py`** (every `features/` module imports; registry populated;
  the new routes registered; schemreview round-trip) and the earlier `test_features_integration.py`.

### Verified
Core logic verified in-sandbox (schemreview queue/record/override/coverage; schemflow `node --check`; build_schemgraph
cached **4,743** real pages in 0.99.0). **Full host suite pending** — run **`VERIFY-099.bat`** (deferred: a USB copy
was in progress). Additive & rollbackable (R1): new module + routes + one UI mode + a reference panel; sidecars only.

---

## [0.99.0] — 2026-07-01 — Living Schematic, step 1/3: corpus-wide netlist batch + coverage
*(Productionizing the 0.91 PoC. First of three: precompute, then review, then simulate.)*

### Added — `engine/build_schemgraph.py` + `BUILD-SCHEMGRAPH.bat`
- Host batch that scans every document's pages for **vector wiring** (`schem_overlay.schem_paths`), infers the
  netlist (`schemgraph.graph_from_paths`), and caches it to `index/schemcache/<doc>_<page>.json` — the same cache
  the live `/api/schemgraph` route serves, so precomputed pages open instantly. Writes a **coverage report**
  `index/schemgraph_coverage.tsv` (doc, page, segments, nodes, edges, nets, components, confidence).
- **Parallel** (one worker per document, `cpu_count-1` capped 12; `--workers`/`--serial`), **resumable**
  (`index/schemgraph_done.txt` marks scanned docs), bounded `--limit`, tunable `--min-edges`. Read-only on the
  index; sidecar-only (R1/R6).

### Verified (host-side, real corpus)
- `VERIFY-SCHEMGRAPH.bat` (`--limit 200`): the batch runs, and already cached **4,743 schematic-page netlists**
  (e.g. one page: 287 wire-segments · 11 nets · confidence 0.80). `build_schemgraph.py` parses. MuPDF "Layer config"
  lines are harmless. *Known:* many pages report 0 components — CAD-exported sheets outline their label text, so
  ref-designators don't OCR from vectors (feeds step 2, the review queue). Additive; rollback = delete the script +
  bat + the two sidecar files.

---

## [0.98.2] — 2026-07-01 — Restore the run button to the project root
*(User report: "the run batch file is missing." The maintained launcher `engine/run_app.bat` was intact but buried in `engine/`; every other launcher lives at the root, so from the project folder there was no run button.)*

### Added — `RUN-VIEWER.bat` (project root)
- One-click launcher at the root, where users look. **Delegates to `engine/run_app.bat`** (single source of truth:
  Python detection, ensures PyMuPDF/reportlab/Pillow, runs `preflight.py`, opens the browser, serves
  `http://127.0.0.1:8765`). If `run_app.bat` is ever missing it **falls back** to starting `engine/viewer_app.py`
  directly with the right `--db`/`--port`, so the button always works.
- `CHECK-RUN-VIEWER.bat` — optional helper that boots the server on a throwaway port (8799), checks
  `/healthz` + `/api/status` + `/3d`, then stops it — a non-disruptive "does the launcher's target serve?" probe.

### Verified
The exact server this launches (`viewer_app.py` + `features/`) is already proven to boot and serve by
`test_routes.py` in `VERIFY-V098.bat` (**59/59 routes green**, part of the 123-check pass). Launcher files confirmed
present at root; delegation target present. Additive; rollback = delete the two bats.

---

## [0.98.1] — 2026-07-01 — Post-restructure gap-fill: integration coverage for the imagery/CAD/schematic stack + refreshed hand-off docs
*(Additive verification pass by a separate session that had been paused at 0.95. No behavior change — confirms THE RESTRUCTURE carried the 0.90–0.95 features through intact, and closes two overlooked gaps: no integration test spanning those features on the new registry, and stale hand-off docs.)*

### Added — `engine/tests/test_features_integration.py`
- 16 checks that the monolith→`features/` split kept the imagery/CAD/schematic stack whole: every route
  registered in the declarative registry (`/cadimg`, `/cadspin`, `/cadstl`, `/cadobj`, `/api/cadmaterial`,
  `/api/schempaths`, `/api/schemgraph`, `/api/localmodel`, `/api/localmodel_mesh`); `cad_render.CAD_VERSION == 7`;
  `material_for` shape; `render_spin` frame math; a **v1 render** (proves colour+texture on every tier survived);
  `schemgraph` T-junction → one net; `localmodel` OBJ round-trip. Self-contained, no corpus.

### Added — `VERIFY-V098.bat`
- One host-side button: parses the shell + `features/*.py`, then runs `test_features` · the new integration test ·
  `test_routes` · `test_search_quality` · `test_hardening` to `docs/verify_v098.log`.
  **Result on the real v0.98 tree: 21 + 16 + 59 + 15 + 12 = 123 checks, 0 failures.**

### Changed — docs
- `docs/PROJECT-SUMMARY.md` + `docs/PORTING.md` updated from the (stale) 0.95 monolith description to the v0.98
  thin-shell + `engine/features/` architecture, registry/routes model, the new `backups/pre-v0.9{6,7,8}-*` rollbacks,
  and the nav consolidation.

### Verified / Rollback (R1)
Additive only — new test + new bat + doc edits. Rollback = delete the two new files and revert the doc/changelog
edits; no engine code touched.

---

## [0.98.0] — 2026-06-10 — Nav consolidation: libraries live in Collections; tools live in a Tools menu
*(Two direct requests: "place schematics and the 3D library under collections" and "place the part
dossier and other tools behind a Tools section". The header drops from 16 items to 7.)*

### Changed — Collections is now the gateway to the libraries
- `collections.html` gains a **LIBRARIES** section up top: two prominent cards — **📐 Schematics &
  wiring** and **🧊 3D Library** — each describing what it holds and how it grows. The existing
  Smart Collections grid follows under its own heading. (Conceptually they ARE collections:
  curated, auto-growing groups of the corpus.)
- The two standalone header buttons are gone from the home page; `/schematics` and `/3d` routes are
  untouched, so every deep link, palette entry, and bookmark still works (R1).

### Changed — ONE 🧰 Tools menu replaces nine top-level buttons
- New accessible dropdown (aria-haspopup/expanded, Esc + outside-click close) holding the mechanic
  tools — **Solve it · Part dossier · How to do it · Look-Alike Parts · Circuit Lab** — and, below a
  separator, the admin pages — **Add documents · Ops · OCR status · Part# review** (same `id`, so
  the existing review-UI binding works unchanged).
- Top level is now: **Browse chip · Collections · Tools ▾ · Help · Settings · Side · Parts
  session** — it fits one row on most screens (finishing what the v0.97.0 E39 wrap fix started).

### Verified (isolation tree)
10/10 acceptance checks (menu present, tools nested, libraries cards render, all old routes 200) +
all 7 suites green + RPS GATE PASS + `node --check` clean. Rollback: `backups/pre-v0.98-nav/` (R1).

### Diagram (R2/R3)
`docs/diagrams/109-nav-consolidation.svg/.pdf`. CHANGELOG-VISUAL-FULL regenerated (129 releases).

---

## [0.97.0] — 2026-06-10 — Search quality + UI dedup finished + the header-wrap layout fix
*(The "next natural steps" after the restructure: backlog C18/C20/C22/C23, A2/A3 completed across
12 pages, the E39 overflow fix the home page needed, and the #81 visual-changelog stall fixed at
its root.)*

### Added — search quality (features/search_feature.py + routes)
- **Exact-match boost (C18):** a verbatim hit of the whole query, or a row whose NSN is cataloged
  under the query as an exact part number, now carries `exact: true` and sorts above plain keyword
  hits (stable bands: exact → ★requested → rank). Additive flags; nothing removed.
- **Did-you-mean (C20):** zero-result searches return up to 3 offline suggestions — each long token
  replaced by its closest indexed term (edit-distance 1 via the FTS vocab) plus a strongest-token
  fallback that is verified to actually hit the index. The home page renders them as clickable links
  under "No matches".
- **Explicit operators (C22):** `"quoted phrase"` passes through as a true FTS phrase (adjacency),
  and `a NEAR b` becomes `NEAR("a" "b", 10)`. Unquoted queries build the exact same expression as
  before. *(C17 per-column bm25 weighting resolved as N/A by design: `pages_fts` is single-column
  body text; rank already uses bm25, and C18 covers the intent.)*
- **Result LRU (C23):** identical query+filter sets within 60 s are served from a 200-entry cache —
  repeat searches (paging back, palette re-runs) no longer touch SQLite. TTL-bounded, so OCR-grown
  results appear within a minute.

### Changed — UI dedup finished (A2/A3) + layout fix (E39)
- **12 pages** (collections, partdiff, procedure, solve, dossier, packet, stepflow, ingest, ops,
  status, help, keywords) now load `/base.css` + `/shared.js`; their **11 inline `esc()` copies and
  12 inline `:root` palettes are stripped**. `packet.html` keeps its paper-preview styling
  (shared.js only); procedure/status keep their deliberate brighter green as a one-token override.
  Only the three modern pages (index/schematics/threed) keep their own ES6 helpers, by design.
- **Home-page overflow fixed (E39):** the 16-button header nav was a single non-wrapping flex row
  (~2000 px minimum) — any narrower window scrolled the whole page sideways and cut off the left
  edge. The header now wraps at every width, nav buttons wrap *between* (never inside) labels, and
  the main grid uses `minmax(0,1fr)` (+ a 1280 px breakpoint for the request column) so content can
  never force sideways scroll again.

### Added — the visual changelog can no longer stall (#81 root cause)
- `docs/diagrams/_make_changelog_visual_full.py` **parses CHANGELOG.md at runtime** — no manual
  list to forget. Output: `CHANGELOG-VISUAL-FULL.svg/.pdf`, all **127 releases** (0.1.0 → 0.97.0)
  as kind-coded cards with flow nodes + summaries. The original generator and its outputs are
  retained untouched (R6); the 0.28→0.95 backfill is thereby complete.

### Verified (isolation tree)
All 8 suites green: pillars 23 · features 21 · patterns 20 · routes 59 · truncation 11 ·
hardening 12 · **search_quality 15 (new, in VERIFY-ALL)** · RPS GATE PASS. Every modified page
fetched 200 from the live fixture server with `node --check`-clean inline scripts.
Rollback: `backups/pre-v0.97-batch/` (R1).

### Diagram (R2/R3)
`docs/diagrams/108-search-dedup-layout.svg/.pdf`.

---

## [0.96.0] — 2026-06-10 — THE RESTRUCTURE: monolith → thin shell + `engine/features/` package (+ server hardening)
*(Backlog phases 1–3 of the holistic review executed: A1–A8 structure, B9–B16 robustness, J66–J70 security,
G47/G48/K71/K73/K77 gates. Behavior unchanged — structure, safety, and dedup improved.)*

### Changed — structure (backlog A1/A5/A7; the "task #36" modularization)
- `engine/viewer_app.py` **2,407 lines → ~330-line shell** (config, per-thread SQLite plumbing, RPS init,
  Handler, main). Domain logic moved **verbatim** into a new `engine/features/` package:
  `registry` (declarative `{path: handler}` routes + central param validation), `routes` (every endpoint,
  declared once; static pages/scripts as tables), `search_feature`, `parts_feature`, `browse_feature`,
  `procedures_feature`, `render_feature`, `ingest_feature`, `sessions_feature`.
- Same dependency-injection pattern as the earlier extractions (`<module>.core = viewer_app`) — no import
  cycles; `--db` / RPS-mode changes still propagate. **Every public name is re-exported** from the shell, so
  `import viewer_app as V` (tests, scripts) is unchanged. `run_app.bat`, the watchdog, and `make_portable.py`
  (copytree picks up `features/` automatically — Lite parity, N88) all work untouched.
- The ~90 if/elif route blocks became **108 GET + 10 POST registry entries** dispatched by one dict lookup.
- **Rollback (R1):** the pre-split monolith is preserved byte-for-byte at
  `backups/pre-v0.96-restructure/viewer_app.py` (md5-verified) — restoring it (and removing `features/`)
  reverts the whole restructure.

### Added — foundation / dedup (A2/A3/A4/A6/A8)
- `engine/theme.py` — the **single source of truth for the dark-theme tokens**; `ui/base.css` mirrors it for
  pages (served at `/base.css`, includes `prefers-reduced-motion`, F46); `docs/diagrams/_common.py` now
  imports the palette from it instead of hardcoding (existing generators untouched).
- `engine/ui/shared.js` — the **one ES5-safe copy** of `esc()/$/getJSON/postJSON/toast()/debounce/fmtInt`
  duplicated across ~14 pages, served at `/shared.js`. Pages adopt it incrementally; inline copies keep
  working meanwhile (identical behavior), then get stripped page-by-page with browser verification.
- `patterns.py` **adopted** as the canonical NSN/FIG/PN regex source — search/callouts/parts/render features
  now import it (A6); the copies in the monolith are gone with the monolith.

### Added — robustness & security (B9–B16, J66–J70)
- **One error boundary** (B9): handlers can never drop the socket; `ParamError → 400`,
  `FileNotFoundError → 404`, anything else → **logged** 500 with a short `ref` id.
- **Central param validation** (B11): `?limit=abc` now answers **400** (was 500) on every route; hard
  server-side row ceilings regardless of client (J67).
- **Rotating error log** `engine/logs/server-errors.log` (1 MB ×3, B10), surfaced as `recent_errors`
  in `/api/ops`; raw exception text no longer echoes to the client (J69).
- **POST hardening:** 8 MB body cap answered 413 *without reading the body* + connection close (B13);
  same-origin check on POST — a foreign `Origin` answers 403 (J68); per-connection timeout 60 s.
- **/api/ingest paths canonicalized** (`realpath`, J70) + optional `VIEWER_INGEST_ROOTS` fence
  (unset = original behavior). `/page` confirmed traversal-safe by design — documents are addressed only
  by id; the path always comes from the `documents` table (B12).
- **Graceful Ctrl+C** (B16): sockets closed + `wal_checkpoint(TRUNCATE)`. Binds 127.0.0.1 by default,
  documented `--host 0.0.0.0` to expose deliberately (B15). LIKE/GLOB filters audited — all parameterized (J66).
- `VERSION = "0.96.0"` surfaced in `/healthz`, `/api/status`, `/api/ops` (N89).

### Added — gates & tests (G47/G48, K71/K73/K77)
- `rps_lint.py` (the ES5/legacy gate) now runs in **VERIFY-ALL** with every verify; all 31 UI files
  classified (6 tiered overlays locked ES5-required; `partgeo.js`/`cadtex_test.html` modern-by-design).
  Fixed a comment-only `...` false positive in `tagger.js`.
- New `tests/test_hardening.py` — 12 acceptance checks for the defenses above, on the fixture index.

### Verified (isolation tree, full suites)
`test_patterns` 20 ✓ · `test_features` 21 ✓ · `test_pillars` 23 ✓ · `test_truncation` 11 ✓ ·
**route smoke 59 ✓ (every endpoint on the real server)** · **hardening 12 ✓** · **RPS GATE: PASS**.
Run `VERIFY-ALL.bat` host-side for the coherent-file confirmation + snapshot.

### Diagram (R2/R3)
`docs/diagrams/107-restructure.svg/.pdf` — request lifecycle, the features package, and the safety rails.
*(R5: entry appended to `_make_changelog_visual.py`; regenerate the master strip host-side per backlog #81.)*

---

## [0.95.0] — 2026-06-05 — Hardware-aware boost: parallel CAD batch + CAD textures grafted onto the 3-D model
*(Tuned to the dev machine — 16-core Alder Lake + RTX 4050. The GPU already drives WebGL 3-D and GPU-tier OCR; the CAD batch was the CPU-bound straggler.)*

### Fixed (design flaw) — `engine/make_cad.py` was single-threaded
- The pre-render loop now **fans out across CPU cores** (`multiprocessing.Pool`, auto-sized to `cpu_count-1`, capped
  at 12; `--workers` / `--serial` overrides). Renders are independent and write distinct cache files, so there's no
  contention; the parent pre-filters already-cached parts (resumable).
- **Measured on this machine (16 cores):** 120 parts **15.4 s serial → 5.26 s on 12 workers ≈ 2.9× faster**
  (per-worker startup amortizes further at full scale). The whole v7 colour+texture re-render drops from **~210 min
  → ~72 min**. `bench_cad_parallel.py` reproduces it.

### Added — CAD colour + material texture grafted onto the WebGL 3-D model
- `cad_render.material_for(name,chars,nsn)` → `{color, metal, klass, klass_id, gl}`; new route **`/api/cadmaterial`**.
- `gl3d.js` shader gained a **material-class procedural texture** (`klass` uniform): brushed metal, speckled rubber,
  wood rings, plastic, CARC orange-peel, brass — so the **3-D model now matches the CAD image's colour + surface**.
  `load()`/`setKlass()` carry it; falls back gracefully (a shader that didn't compile would just disable WebGL, not
  crash — but it compiles: `gl3d.js` passes `node --check`).
- `threed.html` `applyCadMaterial(m)` fetches the CAD material on open and applies colour + class to the Interactive
  3-D model (and the parametric/rebuild paths). The flat-steel **Rotate CAD** view stays texture-free (`klass 0`) so
  the technical look is preserved.

### Note on the GPU
The CAD renderer is pure Pillow (CPU) by design (runs anywhere) — so the boost here is **CPU parallelism**. The
**RTX 4050 is already used** where it helps: WebGL for the interactive 3-D/CAD turntable, and GPU-tier OCR.

### Verified (host-side)
`VERIFY-BOOST.bat` → `docs/boost_verify.log`: `cad_render.py` / `make_cad.py` / `viewer_app.py` parse, `gl3d.js`
passes `node --check`, both UI pages parse, and the parallel benchmark above. Additive & rollbackable (R1).

---

## [0.94.0] — 2026-06-04 — Wire your own local 3-D models into the viewer (replace the placeholder)
*(Drop a real OBJ/STL for a part and the 3-D tab shows it instead of the representative geometry — authoritative, not an approximation.)*

### Added — `engine/localmodel.py`
- Looks for a user-provided model at **`index/models3d/<NSN>.obj`** or **`.stl`** (sidecar, R1/R6) and parses it to
  `{V,F}` for `gl3d.js`. Handles **OBJ** (n-gon triangulation, 1-indexed + negative indices), **ASCII STL**, and
  **binary STL** (stdlib `struct`). Faces capped at 300k. `status()` / `mesh_vf()`.

### Added — routes `GET /api/localmodel` + `GET /api/localmodel_mesh`
- Status (`exists`/`fmt`/`mesh_url`/`filename`) and the parsed mesh JSON. Mirrors the image3d route style; 404 JSON
  when there's no file (never a 5xx).

### Changed — `threed.html` (3-D modal)
- On opening a part, the viewer checks for a local model; if present it **loads that mesh into the Interactive 3-D
  tab in place of the parametric placeholder** (gl3d auto-centres + auto-fits any units). A green **🧩 LOCAL 3-D
  MODEL** badge shows the filename/format/face-count with a **toggle** back to the representative placeholder.
- Distinct from the gated, watermarked image→3D **Approximation** tab — local models are **authoritative** (your
  file, no watermark).

### Verified (host-side)
`VERIFY-LOCALMODEL.bat`: `localmodel.py` + `viewer_app.py` + both UI pages parse; round-trip parse of a sample
**OBJ (8v/12f), ASCII STL and binary STL (36v/12f each)** → all OK, test files cleaned up. How-to:
`docs/LOCAL-MODELS.md`. Additive; rollback = drop the module + 2 routes + the `loadLocalModel` block.

---

## [0.93.3] — 2026-06-04 — Material TEXTURE on EVERY CAD tier too (CAD_VERSION 6 → 7)
- The per-material procedural **surface texture** (brushed metal / brass, rubber & cast grain, wood grain, plastic,
  painted/CARC orange-peel) now renders on **v1, v2 and v3** — it was v3-only. Pairs with the colour change so every
  tier is now both **coloured and textured** at max quality (SS4 + key/fill lighting + dense meshes).
- `render()` gained a `texturize` flag (default = textured; `False` reproduces the old untextured look for the
  before/after). Texture uses numpy and is wrapped in try/except, so a legacy box without numpy simply skips it —
  never an error. **Tier ladder kept** (v1 flat · v2 +specular · v3 originally the textured one — now all textured);
  RPS mapping unchanged.
- Before/after proof: `docs/cad_color_texture_before_after.png`; refreshed sheet: `docs/cad_tier_comparison.png`.
  `CAD_VERSION` → **7** — refresh the cache with **`RUN-CAD-TIERS.bat`**. Verified host-side (`cad_render.py` parses;
  pages render).

---

## [0.93.2] — 2026-06-04 — FLIS colour on EVERY CAD tier (CAD_VERSION 5 → 6)
- Colour (FLIS stated colour, else a material-based tint) now renders on **v1, v2 and v3** — previously it was
  v3-only and v1/v2 were grey. `render()` gained a `colorize` flag (default = coloured; `False` reproduces the old
  grey look, used for the before/after page). All parts now carry their colour at max quality (SS4 + key/fill).
- **Tier ladder still intact:** v1 flat-matte **coloured**, v2 +specular/metallic **coloured**, v3 +procedural
  texture **coloured**. RPS tier→style mapping unchanged.
- Before/after proof: `docs/cad_color_before_after.png` (each cell = old grey | new colour, per tier). Refreshed
  all-colour tier sheet: `docs/cad_tier_comparison.png`. `CAD_VERSION` → **6** — refresh the cache with
  **`RUN-CAD-TIERS.bat`**. Verified host-side (`cad_render.py` parses; pages render).

---

## [0.93.1] — 2026-06-04 — Max-quality CAD pass on every tier (CAD_VERSION 4 → 5)
*(As much quality as the Pillow renderer can give — applied to v1, v2 and v3 — without touching the RPS tier mapping or the modern build.)*

### Changed — `engine/cad_render.py`
- **Supersample 3× → 4×** (render large, LANCZOS-downsample) — the crispest anti-aliasing the renderer can do.
- **Key + fill + ambient lighting** — a soft fill light now lifts the shadow side of every part, so modeling reads
  cleaner and more three-dimensional (was a single key light). v1 keeps its flat/no-specular character.
- **Denser curved meshes** — cylinder 48→64, tube 52→72, torus 48×26→64×34, sphere 28×20→40×28, helix sv 12→16 /
  su→128 min. Bearings, bushings, gaskets, springs are now smoothly round.
- Still **all three tiers, ladder + RPS intact**: v1 flat (legacy) · v2 +specular/metallic (lite) · v3 +FLIS
  colour/texture (modern). The faceted families (hex heads, gears) are unchanged by design.
- **Fast:** measured **avg 0.15 s, max 0.26 s per image** at SS4 — on-demand stays snappy and the full re-render is
  hours, not days. Proof grid: `docs/cad_quality_v5.png`.
- `CAD_VERSION` → **5**. Cache is style-keyed, so refresh the library with **`RUN-CAD-TIERS.bat`** (clears +
  re-renders v1/v2/v3) to push v5 everywhere; on-demand parts pick it up as their cache entry is recreated.

### Verified (host-side)
`VERIFY-CAD-QUALITY.bat`: `cad_render.py` + both UI pages parse (exit 0); all-tiers grid renders with the timing
above. Additive & rollbackable (R1): revert SS, the lighting block, and the mesh-density constants.

---

## [0.93.0] — 2026-06-04 — Higher-quality CAD across all tiers + CAD vs 3-D now visually distinct
### Changed — `engine/cad_render.py` (quality pass, every tier — CAD_VERSION 3 → 4)
- **Supersample 2× → 3×** — noticeably cleaner anti-aliased edges on every render.
- **Finer tessellation** of the curved primitives (cylinder 28→48, tube 32→52, torus 30×16→48×26, sphere 16×12→
  28×20, helix sv 8→12) — round families (bearings, bushings, gaskets, springs) read as round, not faceted.
- **Crisp silhouette / hole "ink" outline** drawn from the part mask (the CAD line), plus a **soft contact shadow**
  under the part for depth. **Softer facet edges** (a darkened tint of each face instead of a hard black wire) so
  the finer mesh looks clean, not like a wireframe.
- Applies to **all three tiers** while preserving the ladder: **v1** flat (legacy), **v2** +specular/metallic
  (lite), **v3** +FLIS colour/texture (modern). Proof grid: `docs/cad_quality_v4.png`.
- *Note:* `CAD_VERSION` is now **4**; existing cached PNGs are the old quality until re-rendered — run
  **`RUN-CAD-TIERS.bat`** to refresh the full set (it clears + re-renders). On-demand renders of newly-opened parts
  pick up the new quality once their cache entry is (re)created.

### Changed — `threed.html` (🔄 Rotate CAD vs ◳ Interactive 3-D now look different)
- **Rotate CAD** renders the mesh as **flat-faceted neutral machined steel, matte** (`GLV.load(geom, '#9aa6b2',
  false, [0.18,14,0.30])`) on a cool blueprint-grey stage — a deliberately **technical CAD** look.
- **Interactive 3-D** keeps the **realistic** treatment: the part's FLIS colour + smooth shading + the scanned
  material finish. Same smooth WebGL motion for both; only the look differs, so the two tabs are no longer
  near-identical.

### Verified (host-side)
- `VERIFY-CAD-QUALITY.bat`: `cad_render.py` parses, both UI pages' inline JS parse (exit 0), and the all-tiers
  quality grid renders (`docs/cad_quality_v4.png`). Additive; rollback = revert the render edits + the cadspin
  `GLV.load` line + CAD_VERSION.

---

## [0.92.1] — 2026-06-04 — Rotate CAD now spins on real WebGL — exactly as smooth as the 3-D model
### Changed — `threed.html` (🔄 Rotate CAD tab)
- The **Rotate CAD** view now renders through the **same `GL3D` WebGL viewer and the same orbit/zoom controls as
  the Interactive 3-D tab** — `GLV.load(G.model.geom, colour, smooth, material)` on the CAD mesh — so it rotates
  **identically and just as smoothly** (continuous WebGL, not frame-by-frame). It carries the part's FLIS colour +
  material, scaled to FLIS dims.
- The **sprite-sheet turntable** (`/cadspin` + `cadview.js`) is **kept as the legacy / no-WebGL fallback** so the
  view still rotates on machines without WebGL (Win7/Vista, RPS legacy). When `GL3D.supported()` is true you get the
  smooth WebGL path; otherwise the GPU-free sprite path.
- The static **🖼 CAD image** tab is unchanged (still the default). Verified host-side: `threed.html` +
  `schematics.html` inline JS parse clean (exit 0). Additive; rollback = revert the `cadspin` branch.

---

## [0.92.0] — 2026-06-04 — Interactive CAD: the CAD image now rotates, zooms, and scales like the 3-D model
*(You can grab the CAD image and spin it — and it stays the real CAD render: shaded, coloured, textured, with the dimension callouts.)*

### Added — `engine/cad_render.py`
- `render()` gained `yaw` (spin about the vertical axis), `pitch` (camera tilt override), and `title` (drop the title
  block for clean turntable frames) — all defaulted so the canonical CAD image is unchanged (R1).
- **`render_spin()` / `ensure_spin()`**: render the same CAD pipeline at **N viewpoints around a full 360°** and pack
  them into one cached **turntable sprite sheet** (`<nsn>_spin<n>_<style>.png`). Tier-aware frame counts
  `SPIN_FRAMES = {v1:12, v2:16, v3:24}` (legacy/lite/modern).

### Added — route `GET /cadspin?nsn=&n=&style=&tier=` (cached)
- Serves the sprite sheet + `X-CAD-Frames` / `X-CAD-FrameW` headers so the viewer knows how to scrub. Mirrors
  `/cadimg`'s name/chars/style/tier resolution; cached in `index/cadcache/`, rendered on demand.

### Added — `engine/ui/cadview.js` + wired into the 3-D library
- A GPU-free, ES5-safe interactive widget: **drag to rotate** (scrubs the turntable frames), **scroll / pinch to
  zoom (scalable)**, **drag-to-pan when zoomed**, an **auto-rotate** toggle, **+ / − / reset** controls. Loads the one
  sprite-sheet PNG and draws frames to a canvas — no WebGL, so it runs on every RPS tier (legacy just gets fewer
  frames). `threed.html` now has **both** views as separate tabs, like the multi-mode 3-D and schematic viewers:
  **🖼 CAD image** (the static `/cadimg`, still the default + the grid thumbnail + no-JS fallback) and **🔄 Rotate
  CAD** (this interactive turntable). Complements the existing WebGL "Interactive 3-D" tab rather than replacing it.

### Verified (host-side)
- `VERIFY-CADSPIN.bat` → `verify_cadspin.py` rendered turntables for a bearing, a bolt, and a gear; proof montage
  `docs/cadspin_proof.png` shows the hex head, gear teeth, and bore **visibly rotating** across frames while the
  shading + H/L dimension callouts are preserved. `cad_render.py` + `viewer_app.py` parse host-side; `cadview.js`
  passes `node --check`. Additive; rollback = revert the three `render()` args + drop `/cadspin`, `cadview.js`, and
  the CAD-tab mount.

---

## [0.91.0] — 2026-06-04 — "Living Schematic" (PoC): inferred netlist + animated flow overlay
*(The schematic equivalent of the CAD engine — reconstruct structured connectivity from a flat page, then render something richer than the scan.)*

### Added — `engine/schemgraph.py`
- Infers a **connectivity graph (netlist)** from a schematic page's vectors. Reuses `schem_overlay.schem_paths`
  (lines/polylines/rects/text, normalized 0..1), then: decomposes into wire **segments**, snaps near-coincident
  endpoints into **nodes** (spatial hash), splits **T-junctions** (a tap touching a wire's interior joins the net),
  groups edges into **nets** (union-find), attaches **component** ref-designators (R1, C12, K3…), and scores a
  **confidence**. Pure read; never touches the corpus (R1). `graph_from_paths()` / `graph_for()` / `--selftest`.

### Added — route `GET /api/schemgraph?doc=&page=` (cached)
- Serves the inferred graph, cached to `index/schemcache/<doc>_<page>.json`. `&fresh=1` bypasses the cache.

### Added — `engine/ui/schemflow.js` + viewer Flow toggle
- **`▶ Flow`** button on the schematics viewer. On a vector sheet it overlays the inferred graph and **animates the
  wires in the direction of flow** (dashes travel power → load, oriented by BFS from power/ground labels). **Click a
  wire** to isolate its whole net; **click a component** for a breakdown panel (find every mention in the manual).
  Tiered (RPS): **modern** = `requestAnimationFrame` dash flow · **lite** = browser-driven SMIL `<animate>` ·
  **legacy** = no loop — static highlight + a **STEP** button that advances the flow one hop at a time.

### Verified (real corpus)
- Self-test: synthetic loop + mid-wire tap → **one** connected net (T-junction split works).
- Ran the full pipeline on real wiring diagrams: **Engine Wiring Harness p1 → 77 components, 1,652 wire-segments,
  65 nets, confidence 0.97**; many wiring pages score ≥0.94. Visual proof (`docs/schemflow_proof.png`) shows the
  inferred netlist tracing the actual Caterpillar C7 engine schematic. `schemflow.js` passes `node --check`;
  `viewer_app.py` + `schematics.html` validated. Additive; rollback = drop the route + the two files + the toggle.
- *Known PoC limit:* sheets exported as pure CAD vector (label text outlined, not real text) yield wires/nets but
  zero components — the breakdown needs a text layer (OCR), consistent with the proposal's noted risks.

---

## [0.90.0] — 2026-06-04 — CAD-first 3-D library: the CAD image is now the face of every part
*(CAD officially at the forefront, replacing the parametric/"stock" representation.)*

### Changed — `threed.html`
- **Every grid card now leads with the rendered CAD image** (`/cadimg`), not the parametric SVG. The SVG stays only
  as the instant loading placeholder; the cited manual figure (when one exists) is remembered for the modal.
- **The part modal opens on the CAD image by default.** Tabs reordered to **🖼 CAD image · ◳ Interactive 3-D ·
  📄 Manual illustration · ⚠ Approximation** — CAD first, the spin/zoom WebGL second, the real TM scan third.
- CAD requests carry the build tier (`&tier=`), so the detail level matches the RPS mode (modern v3 / lite v2 /
  legacy v1). Library header + modal header reworded to "CAD images of every part / Representative CAD &
  interactive 3-D."

### Net effect
The "stock" parametric 3-D and artistic-approximation SVGs are no longer the face of the collection — the textured,
dimensioned **CAD image is**. The interactive model and the authoritative manual figure are one click away.

### Verified
`threed.html` JS passes `node --check`; all CAD-first markers present. Every CAD/3-D bat was compile-audited (all
reference an existing, compiling script). Additive UI; rollback = revert the card + setupTabs/showStage edits.

---

## [0.89.1] — 2026-06-04 — Failure-proof CAD renders + render all three tiers
### Hardened
- `cad_render.ensure()` now **always yields an image** for a known part: the texture step is wrapped (cosmetic,
  never fatal) and any render exception falls back to a clean **placeholder card** (`_fallback_card`) — so the
  batch can't leave gaps. (In practice the v3 batch finished **32,622 / 32,622 with 0 failures**, so the earlier
  "~89 missing" was just the tail still rendering.)
### Added
- **`RUN-CAD-TIERS.bat`** — renders all three detail tiers in sequence: fills modern **v3**, then **v2** (lite),
  then **v1** (legacy), into the per-tier cache (`<nsn>_v1/_v2/_v3.png`). Resumable; stops any running batch first.
- `CAD-STATUS.bat` now reports **per-tier counts** (legacy/lite/modern), and the auto-notify scheduled task watches
  all three tiers and pings when every level is complete.
### Compatibility (R1)
Additive + defensive; default render path unchanged. Rollback = drop `_fallback_card` + the try/except.

---

## [0.89.0] — 2026-06-04 — CAD detail level scales with the program build (RPS tier)
*(Idea: the CAD image's level of detail follows the build's specs — like the rest of RPS.)*

### Changed
- The **CAD detail level now follows the RPS tier**: **modern → v3** (FLIS colour + material textures + specular),
  **lite → v2** (oriented + specular/metallic, no texture), **legacy → v1** (the lightest: flat, head-down,
  **no numpy needed** — so it renders on Win 7/Vista and low-end machines).
- **`/cadimg`** resolves the style automatically from the server's `RPS_MODE` (`cad_render.TIER_STYLE`), with an
  explicit override via `?style=v1|v2|v3` or `?tier=modern|lite|legacy`. The response carries an `X-CAD-Style`
  header. Each level caches separately (`<nsn>_v1/_v2/_v3.png`), so a build only renders (and ships) the images it
  needs — the legacy build never pays for textures it can't afford.
- `cad_render.ensure(..., style=)` + `cache_path(..., style=)`; `make_cad.py --style v1|v2|v3` pre-renders a chosen
  tier (default v3). The modern v3 set already in `cadcache` is unchanged (same `_v3.png` filenames).

### Why
This makes the auto-CAD engine RPS-native: heavier hardware gets the richest render, the legacy build gets a
dependency-free lightweight one, and the on-disk cache is per-tier so nothing is wasted.

### Verified
`cad_render.py`, `viewer_app.py`, `make_cad.py` all `py_compile` clean; the v1/v2/v3 looks were already proven by
the contact + comparison sheets. Additive + backwards-compatible (R1) — default stays v3.

---

## [0.88.1] — 2026-06-04 — CAD render `style` switch + comparison/contact-sheet tooling
- `cad_render.render(..., style="v1"|"v2"|"v3")` — render any historical look on demand: **v1** original (head-down,
  flat diffuse, no colour/texture), **v2** + right-side-up + specular/metallic, **v3** + FLIS colour + material
  texture (default, unchanged). `material_props(..., use_color=False)` skips colour for v1/v2.
- **`make_contact.py` / `RENDER-CONTACT.bat`** — a 10-part textured contact sheet (`docs/cad_contact_sheet.png`).
- **`make_compare.py` / `RENDER-COMPARE.bat`** — a 50-part **v1-vs-v2 comparison sheet** (`docs/cad_v1_vs_v2.png`),
  pulling real parts from the index across families.
- **`RUN-CAD-BATCH.bat`** — stops any running CAD batch, clears orphaned older-version renders, starts a fresh
  textured (v3) render of the whole set (resumable).
- All verified by rendering through the host (the sandbox mount tears reads of the grown file; host/server reads are
  whole). Additive, R1.

---

## [0.88.0] — 2026-06-04 — CAD engine: wrap models in material textures + parse FLIS colours
### Added — procedural surface textures
- Each CAD render is now **wrapped in a per-material surface texture** (screen-space, masked to the part
  silhouette, numpy): **brushed streaks** for steel/aluminium/stainless and **brass/bronze**, fine **grain** for
  cast iron, matte **speckle** for rubber/elastomer, subtle variation for plastic, directional **grain** for wood,
  and faint **orange-peel** for painted/CARC surfaces. Falls back gracefully (no texture) if numpy is absent.
### Added — colour parsing
- `material_props()` now parses the **FLIS colour** (OLIVE DRAB, CARC GREEN, FOREST GREEN, DESERT SAND/TAN, FIELD
  DRAB, BLACK, GRAY, RED, …) and uses it as the base tint while keeping the material's metalness + texture — so an
  olive-drab steel bracket renders **green and painted-textured**, a brass gear renders **gold and brushed**. A
  coloured "metal" part is treated as **painted** (orange-peel, not bare brushed metal).
### Changed
- `material_props()` returns `(rgb, metalness, texture_class)`; expanded the material table (cast iron, titanium,
  glass/acrylic, more polymers). **`CAD_VERSION` → 3** to re-render the cache with textures + colours.
### Verified
- Colour parsing + texture-map generation unit-tested in isolation (OLIVE DRAB→green, CARC GREEN→green, each
  material yields a correct surface map). Renderer compiles clean (`py_compile`). NOTE: a `MAKE-CAD.bat` run started
  on an older version writes orphaned `_v1` files — **re-run `MAKE-CAD.bat`** to populate the textured `_v3` set
  (or let `/cadimg` render them on demand).
### Compatibility (R1)
Additive + visual only; numpy-guarded. Rollback = revert the `material_props` + texture block in `cad_render.py`.

---

## [0.87.0] — 2026-06-04 — CAD roadmap items: real STL/OBJ export + fidelity pass + downloads
*(First items off the v0.86.0 roadmap.)*

### Added — real CAD output (export)
- **`/cadstl?nsn=` and `/cadobj?nsn=`** — download the representative part as an actual **STL** (triangulated, ASCII)
  or **OBJ** mesh, scaled to its FLIS dimensions, openable in any CAD / slicer / 3-D tool. `cad_render.mesh_for()`
  + `to_stl()` / `to_obj()`.
- **Download buttons**: the 3-D modal now offers **CAD image (PNG) · STL · OBJ**; the part-assets drawer adds
  **⤓ STL** and **⤓ CAD PNG**.

### Improved — fidelity pass (`cad_render.py`)
- **Right-side-up orientation** — fixed the Y axis so parts render heads-up (the bolt's hex head is now on top).
- **Specular + metallic shading** — added a Blinn-Phong highlight whose strength/tint comes from the material
  (steel/aluminium/brass shine and tint the highlight; rubber/plastic stay matte), porting the WebGL "product
  render" look to the Pillow renderer. Material lookup now returns a metalness value.
- **`CAD_VERSION` → 2** so the cache re-renders every part with the new orientation + shading.

### Operational
- The stale **elevated zombie server is cleared** (the machine reboot freed port 8765); a fresh server was started
  and **verified live** — `/api/threed` now returns `mode=figures` / 24,312 on 8765, so the whole app (figures-first
  3-D, CAD images, callout→assets drawer, loupe) is finally live in the normal browser.

### Verified
`cad_render.py` compiles + renders (bolt now head-up with a metallic highlight); STL/OBJ host code confirmed
correct; live 8765 probe shows the current code.

### Compatibility (R1)
Additive routes + UI; renderer changes are visual only. Rollback = revert the `cad_render.py` shading/orientation
edits + remove the `/cadstl` `/cadobj` routes + the download buttons.

---

## [0.86.0] — 2026-06-04 — CAD images for the whole representative 3-D library (~20,869 parts)
*(“Give them CAD images. Create them if you must.” — done: rendered, cached, served, shown.)*

### Added — `cad_render.py` (Python CAD-image renderer)
- A pure-Python + **Pillow** renderer (no GPU, no heavy deps). For any part it **classifies the shape** (name +
  NSN supply class), builds the **same parametric geometry as `partgeo.js`** (ported faithfully — all 22 families),
  scales it to the **FLIS dimensions**, and renders a **shaded isometric CAD image**: facet shading + edge lines on
  a faint drafting grid, **overall-dimension callouts** (⌀ / L / H in inches), and a **title block** (NSN, name,
  shape, “REPRESENTATIVE CAD APPROXIMATION — scaled to FLIS dims”). Output cached to the **`index/cadcache/`
  sidecar** (never touches the index, R1).

### Added — route + batch
- **`/cadimg?nsn=`** — renders on first request and caches (the figcrop pattern); subsequent requests are instant.
- **`make_cad.py` + `MAKE-CAD.bat`** — pre-render the **whole representative set** (ref_nsn with FLIS dims, ~20,869,
  plus the figure-bearing parts) into `cadcache`. Resumable (skips done), prints progress + ETA.

### Wired
- The **3-D library** now shows the **CAD image** as the thumbnail for representative parts that have no cited
  manual figure (parametric SVG stays as the instant placeholder/fallback). Figure-bearing cards still lead with the
  real manual figure; the interactive WebGL model is still in the modal.

### Verified
- Rendered sample families in isolation (bolt/gear/bearing/canister/bracket/switch) and **end-to-end through the live
  server** (`/cadimg?nsn=…` → valid PNG). All correct.

### Compatibility (R1)
Additive: one renderer module, one route, one batch, one sidecar cache; UI falls back to the parametric SVG if a CAD
image isn’t available. Rollback = remove `cad_render.py` + the `/cadimg` route + the `showCAD` call.

---

## [0.85.0] — 2026-06-04 — Streamlined image search: number → results → figure/3-D/pages, + reusable loupe
*(The flow you asked for: navigate to a TM page → click an NIIN/NSN/part# → pick the matching result → see the
images / schematics / 3-D — without leaving the page.)*

### Added — part-assets side drawer (`index.html`)
- The **🏷 Callouts** markers on a TM page now open a **right-side drawer** (page stays visible) instead of jumping
  to a separate tab. The drawer shows:
  - **Matching results** for the clicked number (NSN → `/api/part_record`, part# → `/api/part_by_number`).
  - **📄 Manual figure** (the cited crop), with the **magnifier loupe** on it.
  - **🧊 live 3-D** — the detailed parametric model embedded right there (drag to orbit, scroll to zoom), via the
    new shared **`partview.js`** widget (PartGeo + GL3D, SVG fallback on legacy).
  - **📃 Schematics & pages that hold the part** (`/api/threed_refs`) as clickable thumbnails.
- **Page highlighting**: clicking a number highlights it on the current page; clicking one of the "pages that hold
  the part" **jumps the viewer there and highlights the matching callout** on that page.

### Added — reusable loupe (`loupe.js`)
- Extracted the magnifier into a **dependency-free, reusable lens** (`Loupe.attach(img)`): follows the cursor,
  scroll to change magnification, works on **any image** (barring 3-D). Wired onto the **schematics viewer** and
  the drawer's figure image. (The main page viewer's own 🔎 Loupe toggle was never removed — it's still in the page
  toolbar; this makes the magnifier present on schematics and the asset images too.)

### Routes
- `/partview.js`, `/loupe.js` (additive). `index.html` now loads gl3d/partgeo/partview/loupe.

### Compatibility (R1)
Additive UI + two small modules + two static routes. Legacy-safe (SVG fallback, CSS-magnification loupe). Rollback
= remove the drawer block + the two `<script>`s.

---

## [0.84.2] — 2026-06-04 — Detailed geometry in BOTH views + full 3-D wiring audit
### Changed — detail everywhere
- The grid **card thumbnail** (the drawn "artist approximation") now builds the **same detailed `PartGeo` mesh**
  as the opened modal (the "representative rendering"), instead of the light hex/disc/cyl/box primitive. So a bolt
  shows its hex head, a bearing its races + balls, a gear its teeth — on the card *and* in the modal, identically.
  (`buildModel` now carries `geom`/`smooth`/`detailed`; the SVG skips its redundant bore-overlay when the mesh
  already models the bore.) The modal's WebGL and SVG paths already shared the detailed mesh — now all three match.

### Verified — 3-D geometry wiring is complete (host-side audit)
- **Name classifier → 22 distinct families → all 22 have a builder.**
- **NSN FSC/FSG fallback → 95 mappings → every value is one of those 22 builders.**
- **22 builders → all real `f_*` functions, each producing a valid finite mesh** (no empty shapes).
- `build()` falls back to `f_box` for any unknown family — a guaranteed safety net.
- The full path is wired both ways: `classify(name,chars,nsn)` → `fam` → `PartGeo.build` → `{V,F}` → the card SVG
  thumbnail **and** the modal (WebGL + SVG), with the material/colour (`appearance`) and the real figure (`figcrop`)
  layered on top. The parameter panel lists all 22 families and rebuilds live.

### Compatibility (R1)
UI-only; additive. Rollback = revert the `buildModel`/`renderSVG` lines in `threed.html`.

---

## [0.84.1] — 2026-06-04 — NSN/FSC shape fallback for nameless parts: box-rate 9.3% → 1.5%
*(For the parts that "simply say name" — no usable nomenclature.)*

### Added
- **`familyFromNSN()` + `classify()` in `partgeo.js`.** When a part's name is missing, generic ("NAME", "ITEM",
  a fragment like "FOR 1") or otherwise unclassifiable (→ box), the shape is now recovered from the **NSN's
  Federal Supply Class** — the first 4 digits, which authoritatively encode the commodity (5305=screws,
  5330=gaskets, 5331=o-rings, 3110=bearings, 5945=relays, 4720=hose, 6240=lamps, 5340=hardware, …). Falls back to
  the 2-digit Federal Supply Group when the exact class isn't mapped. A real name still wins; unknown classes stay
  box. `threed.html` now calls `PartGeo.classify(name, chars, nsn)`.

### Measured (`ANALYZE-SHAPES.bat`, 24,312 figure-bearing parts)
- **Name-only: 9.3% box.  + NSN/FSC fallback: 1.5% box → 98.5% recognizable.**
- Of **129** parts with a generic/blank name, **74** now get a real shape from their NSN. The residual 1.5% is a
  long tail of rare supply classes (shop equipment, instruments, lumber) with tiny counts and a real figure anyway.

### Verified
JS FSC logic unit-tested in isolation (nameless→NSN recovery, name-wins, unknown→box) — all pass. `partgeo.js`
`?v=` bumped to 0841.

### Compatibility (R1)
Purely additive (a lookup table + two functions + the export). Rollback = revert `partgeo.js` + the one
`threed.html` line.

---

## [0.84.0] — 2026-06-04 — Parametric shape pass: box-rate 24.7% → 9.3% on the real corpus
*(Data-driven — measured against the live index, not guessed.)*

### Added — 9 new geometry families in `partgeo.js`
`plate` (flat slab + bolt-holes), `cover` (open panel/pan), `pad` (cushion/insulation), `link` (bar + two end
eyes), `lever` (arm + pivot eye + grip knob), `rivet` (shank + button head), `switch` (body + toggle + terminals),
`cylinder` (body + end rims + port — motors/pumps/actuators), `canister` (domed cylinder — air cleaners/filters/
tanks). All built from the existing primitives, driven by FLIS dims; **22 families total, all verified to produce
valid finite meshes.**

### Fixed — classifier
- **`CLAMP` was misclassified as `shaft`** because the pattern `LAMP` had no word boundary and matched “cLAMP”.
  Bounded `LAMP`/`BULB`/`CAP` (and `STUD`, `COIL`, etc.) so clamps now correctly read as brackets.
- Routed the real top offenders to shapes: covers/doors/panels/guards → `cover`; markers/decals/labels/armor/
  plates → `plate`; insulation/pads/straps → `pad`; links → `link`; levers/handles/cranks → `lever`; rivets →
  `rivet`; switches/relays → `switch`; motors/pumps/actuators/valves → `cylinder`; air-cleaners/filters/cartridges/
  tanks → `canister`; wiring/harness → `tube`.

### Measured (host analyzer `ANALYZE-SHAPES.bat` / `engine/analyze_shapes.py`, on 24,312 figure-bearing parts)
- **Before: 75.3% recognizable / 24.7% box.  After: 90.7% recognizable / 9.3% box.**
- The residual box is overwhelmingly large assemblies (ENGINE, POWER UNIT, VAN, FRAME, TOOL KIT, TRANSMISSION) and
  OCR name fragments — no meaningful primitive exists, and they all carry the real manual figure regardless.

### Compatibility (R1)
`partgeo.js` is browser-cached `?v=`-busted and consumed by both the WebGL renderer and the SVG fallback; the grid
thumbnail classifier got the matching cylindrical mappings. Purely additive geometry; rollback = revert `partgeo.js`.

---

## [0.83.3] — 2026-06-04 — End-to-end verification harness + cache the heavy coverage stat
*(Double-checked that the real app does everything the demo shows — on the actual code, over HTTP.)*

### Added
- **`RUN-E2E.bat` + `engine/diag_e2e.py`** — a full end-to-end smoke test. It starts a **clean server on port 8766**
  (so it never collides with the 8765 instance), then HTTP-probes every core endpoint, **chaining real ids**
  (search → doc/page → page render + find-in-manual; threed → nsn/figure → figcrop + part record), for both sides,
  and reports status + shape. Reusable regression tool; writes `index/diag_e2e.txt`.
- Result of the first run: **48 / 49 checks passed.** All 17 shell pages, all 8 JS assets, search (both sides),
  predictive, page render, find-in-manual, procedure, torque, **3-D figures-first (`mode=figures`, total 24,312, real
  figure PNG loads)**, part-diff, part record, collections, schematics, ingest — all green. This also confirms the
  figures-first 3-D fix works on clean code (the earlier “nothing changes” was the elevated zombie on 8765).

### Fixed
- **`/api/coverage` timed out** on the full corpus — it aggregates all 891k pages JOIN documents GROUP BY vehicle on
  every call. It’s correct, just heavy. Added an **in-process TTL cache** (`_COVERAGE_TTL`, 600 s) for the
  all-vehicles form, so it computes once then serves instantly; single-vehicle queries stay uncached (already cheap).
  Pure in-memory, no schema/DB change (R1).

---

## [0.83.2] — 2026-06-04 — Skip buttons: skip the demo, and skip straight to browsing
*(Two escape hatches, per request.)*

### Added
- **Skip the demo** — a “Skip the demo →” button on the tour’s opening gate (so you can bail before picking a
  walkthrough side), in addition to the existing **Skip demo** button in the tour’s bottom bar. Both route through
  the same hand-off: embedded → the real side chooser; standalone → the app’s chooser.
- **Skip to browsing** — a “Skip to browsing →” button placed **next to “▶ Watch the guided tour”** in the side
  chooser. It drops you straight into the app as a pure repository: `BROWSE_ONLY` on, **no side filter** (search
  spans everything), and the choice is remembered (`viewer_browse_only`) so it doesn’t prompt again. Picking a real
  side later still overrides it; `?onboard=1` still forces the chooser.

### Compatibility (R1)
Additive UI + one localStorage flag; reuses the existing browse-only mode. Flow depicted in
`docs/diagrams/91-demo-handoff.pdf` (escape hatches). Rollback = remove the two buttons + `skipToBrowsing`.

---

## [0.83.1] — 2026-06-04 — Demo becomes the onboarding intro; “Finish” hands off to the real side chooser
*(Per request: the guided tour now lives inside the actual onboarding and ends straight in the genuine modal — no coach-marks.)*

### Changed
- **First-run flow** (`index.html`): a new first-run user now sees the **guided tour first** (the demo loaded in a
  full-screen `iframe` at `/demo?embed=1`), and only after it do they reach the real **“Choose your side”** modal.
  A `viewer_demo_seen` flag in localStorage means it auto-shows only once.
- **“Finish” / “Skip” hand-off**: when the tour ends, the demo (in the iframe) posts a message to the app, which
  closes the tour and calls `openSideChooser()` — so the user lands in the **actual** `#sidegate` modal with **no
  guides**. The same happens if they skip.
- **Replay**: added a **“▶ Watch the guided tour”** button inside the side-chooser footer, plus a **“Skip tour →
  choose side”** button pinned on the tour overlay.
- **`?onboard=1`** deep link now forces the side chooser (this is where the standalone demo’s Finish navigates).

### demo.html
- Detects **embed mode** (`?embed=1` or running in an iframe). `finishTour()` posts `{viewerDemo:'finish'}` to the
  parent when embedded; standalone (DEMO.bat / `file://`) it navigates to `…:8765/?onboard=1`. Last step’s button
  is **Finish ✓**; ←/→/Enter and the bottom bar all route through the same finish logic.

### Compatibility (R1)
Additive and behavior-preserving for returning users (a saved side still bypasses everything). Rollback = revert
the `index.html` load block and remove the embed branch in `demo.html`.

---

## [0.83.0] — 2026-06-04 — Interactive demo / onboarding tour (both sides), one double-click
*(Self-contained: runs straight from a bat with no server — so it works regardless of server/port state.)*

### Added
- **`engine/ui/demo.html`** — a single, self-contained guided demo (pure ES5, dark theme R3, zero external
  dependencies, RPS-safe so it runs on the old-OS browsers too). It opens on the real **"Choose your side"**
  gate, then plays a scripted, **end-to-end** walkthrough of the core features for the chosen side:
  - **Coach-mark tour engine**: full-screen scrim with a **spotlight** cutout around the active element,
    animated **SVG arrows**, numbered **callout tooltips** with step text, a progress-dots strip, and a control
    bar (Back / Next / Skip / **Switch side** / **Autoplay**). Keyboard: ←/→/Enter/Esc. Click a dot to jump.
  - **Both sides of the house**: Operator (-10) sees search → page → find-in-manual → operator checks → solve;
    Mechanic (-20) adds procedure+tools, torque, 3-D parts (real figure + parametric), look-alike part-diff,
    Circuit Lab, Smart Collections and Add-docs. Steps are tagged `op` / `mech` / `both` and filtered per side.
  - Faithful in-HTML **mock screens** for each feature, so every step is deterministic and always renders.
- **`DEMO.bat`** — double-click to open the demo in the default browser. No server, no install.
- **`/demo` route** (also `/demo.html`, `/onboarding`) added to `viewer_app.py` so the same page is reachable
  in-app once a clean server is running (additive; needs a server restart to appear).

### Why it’s robust
The demo is decoupled from the live server and live data, so it is immune to the port/zombie-process issue that
was masking earlier changes — it always shows the intended experience.

### Compatibility (R1)
Purely additive — two new files plus one new route; nothing existing changed. Rollback = delete the two files
and the four-line route block.

---

## [0.82.0] — 2026-06-03 — Figures-first 3-D library: lead with the parts that have a real manual image
*(Interim measure while the broader 3-D approximation work continues — surface the proven-good cards up top.)*

### Changed
- **`threed_list()` now defaults to figures-only.** The 3-D library is sourced from the `parts` table where a
  cited figure exists (`fig_no IS NOT NULL` and a non-empty NSN), `LEFT JOIN ref_nsn` for the name/part#/CAGEC.
  Every card in this mode carries a real `image_url` (`/figcrop`), so the page leads with working examples that
  actually show the manual breakdown image — no blank/blocky placeholders at the top.
- **`/api/threed` honors `?all=1`** to fall back to the full FLIS-dimension set (representative parametric shapes,
  some without a figure). Default (no flag) is the figures-first set.

### UI (`threed.html`)
- Added an **"include parts without a manual figure"** checkbox; toggling it re-fetches with `&all=1`.
- The hint line now states the mode: *"working examples — parts with a real manual figure"* vs. *"all parts
  (representative shapes; some have no figure)."*
- Card preview uses the server-attached `image_url` first; per-card `/api/part_image` only as a fallback.

### Compatibility (R1)
- Purely additive: the `all=1` path preserves the prior full-set behavior; no schema change; corpus untouched.
  Rollback = revert `threed_list` default to `figures_only=False`.

### Operational
- Server restarted to load the change. Front-end is no-cache, so a normal reload of `/3d` picks it up.

---

## [0.81.5] — 2026-06-03 — Diagnosed the "all squares" report: empty FLIS names + browser cache
*(Built `diag_3d.py`/`DIAG-3D.bat` and ran it on the live data to find the real cause.)*

### What the diagnostic found (live, 15-part sample)
- **Cited figure FOUND 15/15; crop PNG on disk 15/15** — the figure pipeline is correct and complete; the
  images exist. They weren't showing only because the browser was serving the old cached 3-D page.
- **shape=box 12/15** — root cause: `ref_nsn.item_name` is **empty** for many parts, so the shape classifier
  (which keys on the part noun) had nothing and defaulted to a box.
- material recognized 12/15.

### Fixed
- **Backfill the name**: `/api/threed` now fills an empty `item_name` from the cited figure's title, so the
  shape classifier and the card/modal titles work instead of showing a nameless box.
- **Card uses the server-attached figure** (`item.image_url` from `/api/threed`) directly, with the per-card
  lookup only as a fallback — so the real manual figure shows without depending on a second request.
- (with 0.81.4) `threed.html` no-cache + versioned `partgeo.js`/`gl3d.js` so a normal reload loads the new code.

### Operational
The data + server are correct; the remaining step is a **hard reload of the 3-D page** (Ctrl+Shift+R) — a
running Python server doesn't hot-reload and the browser had cached the old JS.

---

## [0.81.4] — 2026-06-03 — 3-D library shows the real cited figure + stop stale-JS caching
*(Root-cause of "everything is still squares": a stale running server + browser-cached JS, not a code bug.)*

### Changed
- **`/api/threed` now resolves each part's cited figure server-side** and includes `image_url` + `fig_no`, so
  the 3-D library shows the actual manual breakdown image directly (no per-card round trip required).
- **`partgeo.js` and `gl3d.js` are now served `Cache-Control: no-cache`** (was `max-age=3600`). The hour-long
  cache is why edits to the parametric/shape code didn't appear without a hard refresh.

### Operational note (the actual fix for a running install)
The server is a plain Python `http.server` (no hot-reload), so **new routes only exist after a restart**.
After pulling new code: **close the app window and re-run `run_app.bat`, then hard-refresh the page (Ctrl+F5)**.
Until then the browser runs old JS against a server missing `/api/part_image`, `/figcrop`, `/api/part_material`
— which is exactly why the figures/materials/shapes don't show and "nothing changed" after EXTRACT-FIGURES.

---

## [0.81.3] — 2026-06-03 — Silence harmless MuPDF colour-profile noise
- Some scanned PDFs carry a broken embedded ICC colour profile; MuPDF logs `cmsOpenProfileFromMem failed`,
  falls back to a default colour space, and **still renders the page** (the figure crop is unaffected -- runs
  show `failed 0`). `figures_feature.py` now calls `fitz.TOOLS.mupdf_display_errors(False)` on import to stop
  the cosmetic message flooding the console, for both the bulk extractor and the on-demand `/figcrop` route.
- No PDF is modified (corpus stays read-only); the messages were noise, not errors.

---

## [0.81.2] — 2026-06-03 — One-click installer for the 3-D / imagery prerequisites
- **`INSTALL-3D-DEPS.bat`** — installs the imagery pipeline's Python deps (**PyMuPDF, Pillow, numpy,
  pytesseract**) via pip, then runs the checker and reports. Idempotent; safe to re-run.
- **`engine/verify_3d_deps.py`** — reports each prerequisite as OK/missing and what it enables; detects the
  optional **Tesseract** binary and links the Windows installer. Exit 0 when the required ones are present.
- Note: the **3-D viewer itself needs nothing** (browser WebGL); these only power figure/breakdown crops and
  scanned-page tightening. Verified: all four packages + the Tesseract engine import/run cleanly.

---

## [0.81.1] — 2026-06-03 — Shape + colour + material on EVERY 3-D representation
*(The parametric shape and the scan's colour/material/finish now apply consistently to all 3-D images — the
collection cards, the SVG fallback, and the modal — not just the opened model.)*

### Changed — `threed.html`
- The client `appearance()` was upgraded from a 4-colour stub to the **full colour + material + finish
  vocabulary** (mirroring the server `material_feature`): military colours (olive drab, CARC, sand, field
  drab…), materials (steel/stainless/aluminium/brass/bronze/rubber/plastic/glass/wood/titanium) and finishes
  (zinc/cadmium/nickel/chrome plating, phosphate, black oxide, anodize, paint). It returns a render spec
  `{fill, src, gl:[spec,shininess,metal]}`.
- So **every collection-card thumbnail and the SVG fallback** now show the part in its actual colour + finish
  (offline, instantly), and the modal applies the client material immediately, then refines with the
  authoritative FLIS material from `/api/part_material`.

### Changed — `partgeo.js`
- **Expanded the shape classifier**: grommet/band/belt → o-ring; filter/element/cartridge/coupling/adapter/
  elbow/fitting/connector/cable/wire → tube; valve/plug/cap/key/cotter/lamp/fuse → shaft; terminal/lug/contact/
  retainer/clip → bracket. More parts get an **actual parametric shape** instead of a plain box.

### Verified
- Client material port matches the server across rubber/steel+zinc/olive-drab+paint/brass cases; the expanded
  classifier maps the new keyword families correctly; all 13 geometry families still build valid meshes.

### Compatibility (R1)
Client-only, ES5; no server/route/schema change. The authoritative server material still wins in the modal.
RPS-safe (SVG fallback gets the colour; WebGL gets the full finish).

---

## [0.81.0] — 2026-06-03 — Live parametric CAD panel (procedural geometry, editable)
*(The 3-D models were already procedural — now you can drive the parameters and they rebuild live.)*

### Context
`partgeo.js` already generates each mesh **procedurally from FLIS dimensions** (13 families: bolt with hex head
+ threads, nut, washer, gasket with holes, bearing races+balls, toothed gear, helical spring, tube, shaft,
bracket, o-ring, battery, box). This release exposes those parameters as a true **parametric CAD** experience.

### Added — 3-D viewer
- **PARAMETRIC CAD panel** in the modal: a **Family** selector + editable **Length / Width / Height /
  Diameter / Bore** (and **Teeth** for gears, **Coils/turns** for springs). Editing any value **rebuilds the
  geometry live** (WebGL, or the SVG fallback). **↺ Reset to FLIS dims** restores the cited values.
- Values are **cited from FLIS** but editable — the mesh is generated, not fixed.

### Changed — `partgeo.js`
- Gear **teeth** and spring **turns** are now explicit, clamped parameters (`p.teeth`, `p.turns`), so the panel
  can drive feature counts — not just envelope dimensions. Gear bore also honours `p.bore`.

### Verified
- All **13 families** build valid meshes with the new params; **gear teeth** (12 vs 40) and **spring turns**
  (4 vs 20) measurably change the geometry. Backward-compatible: with no extra params, output matches before.

### Compatibility (R1)
Additive, client-only (ES5 panel + parametric `partgeo.js`); no server/route/schema change. WebGL where
available with the existing SVG fallback (RPS-safe).

---

## [0.80.0] — 2026-06-03 — Map the scan's colour + material onto the 3-D models
*(If the scans/FLIS state a colour, material or finish, the 3-D model now wears it.)*

### Added — `engine/material_feature.py`
- **`material_for(characteristics, name)`** parses the scan's **COLOR**, **MATERIAL** and **SURFACE
  TREATMENT/FINISH** into a renderable spec: a base **colour** + a procedural **finish** (metalness /
  roughness / shininess). Covers military colours (olive drab, CARC, sand, field drab…), materials (steel,
  stainless, aluminium, brass, bronze, rubber, plastic, glass, wood, titanium) and finishes (zinc/cadmium/
  nickel/chrome plating, phosphate, black oxide, anodize, paint/CARC). Plating/oxide overrides the colour.
- **`/api/part_material?nsn=|chars=|name=`** — reads FLIS characteristics (`ref_nsn`) when only an NSN is given.

### Changed — 3-D renderer
- **`gl3d.js`** shader now takes a material uniform `mat = [specStrength, shininess, metallic]`; metals tint
  their own highlight and drop the plastic rim. New `setMaterial()`, and `load(geom,hex,smooth,mat)`.
- **`threed.html`** fetches `/api/part_material` on open and applies the colour + finish to the WebGL model
  (and the SVG fallback), with the Appearance line showing **"scan: <olive drab · aluminium · painted>"**.

### Honest scope
The scans give material **words**, not surface photographs — so "texture" here is a **procedural finish**
(colour + metalness + roughness), not a photographic image map. It makes a steel bolt read metallic, a rubber
hose matte-black, a brass fitting warm-glossy, a zinc screw silvery, an olive-drab bracket flat green.

### Verified
- Parser across 8 cases: RUBBER+BLACK → matte black (gl shininess 12, metal 0) · STEEL+ZINC → silvery
  metallic (0.7/61/0.85) · BRASS → warm gloss · ALUMINIUM+OLIVE DRAB+PAINT → flat olive · STAINLESS → bright ·
  RED PLASTIC → semi-matte red · STEEL+PHOSPHATE → dull dark · unknown → representative. Route in `test_routes`.

### Compatibility (R1)
Additive: a new parser + one endpoint + backward-compatible `gl3d.js` (default material = the original look).
Read-only on the index; ES5/WebGL with the existing SVG fallback (RPS-safe).

---

## [0.79.1] — 2026-06-03 — xref coverage in Ops + cross-reference in procedure & 3-D
- **Ops dashboard** gains a **Part-number cross-reference** card: parsed rows · with NSN (%) · FLIS-validated
  (%) · **in review** (low-confidence %), from `xref_coverage()` (now also reports `with_part_no`, `in_review`,
  and percentages). Points to 🔧 Part# review.
- **3-D modal** side panel gains a **CROSS-REFERENCE** block for the opened part — FLIS name (OCR conflict
  noted), manufacturer (CAGEC→company), the vehicles it fits, interchangeable / superseded, colloquial name,
  and confidence + sources — via `/api/part_record`.
- **Procedure page** parts panel now resolves each part to its name + vehicles (+ manufacturer) inline.
- Additive, ES5, read-only (R1/R6).

---

## [0.79.0] — 2026-06-03 — Cross-reference & verification engine (X1–X5)
*(One provenance-tracked part record: FLIS-validated name · the vehicles it fits · interchange/supersession ·
manufacturer · the breakdown image — resolving the OCR-noisy tail, offline-first.)*

### Added — `engine/xref_feature.py` (live resolver)
- **`part_record(pn|nsn)`** unifies everything we hold offline: the RPSTL row + **FLIS** official name
  (`ref_nsn`, **preferred, with the OCR name kept visible and conflicts FLAGGED**) + **vehicles** it fits
  (`correlations.db nsn_platforms`, noise-filtered) + **interchangeable** (`niin_aliases`) + **superseded_by**
  (`supersession_held`) + the **breakdown image** + links to dossier/schematic/procedure/look-alike. Every
  field carries a **source (provenance)** and the record a **confidence**. (X1 FLIS repair · X2 vehicle
  assignment · X3 asset cross-link · X5 provenance/conflict.)
- **`/api/part_record`**, **`/api/xref_coverage`**.

### Added — `engine/build_xref.py` + `BUILD-XREF.bat` (PUB LOG enrichment)
- The two things only the 16 GB CSVs have: **CAGEC → manufacturer** (`P_CAGE` → `cage.json`) and **PN+CAGEC →
  NSN recovery** for rows the OCR lost the NSN on (`V_FLIS_PART` → `pn_nsn.json`). Small JSON sidecars; the
  index is never written.

### Added — X4 online enrichment (`engine/xref_online.py`, OFF by default)
- Optional, **public-data-only**, **cached** (`xref_online.json`), **ITAR/EAR-aware** enrichment for the
  residual unknowns (NSN catalog nomenclature / manufacturer / colloquial). Gated behind
  `VIEWER_XREF_ONLINE=1` + a user-configured public endpoint; the app only **reads the cache** and never
  fetches while serving. `GET /api/xref_online` status. Setup: `docs/XREF-ONLINE-SETUP.md`.

### UI
- The **part-number match card** now shows the FLIS-validated name with **⚠ OCR-read** when they conflict,
  **Fits: <vehicles>** chips, **CAGEC (manufacturer)**, **interchangeable** and **→ superseded by** — all from
  the unified record.

### Verified
- `part_record("12420572-010")` on a fixture: PN→NSN, FLIS name `HOSE,NONMETALLIC` preferred (OCR `HOSE NONMET`
  kept, **conflict flagged**), vehicles `M915/HMMWV` (junk filtered), interchangeable NSN, **confidence 0.9**,
  full per-field provenance. `cage.json`/`xref_online.json` reads surface manufacturer + colloquial. Routes
  added to `test_routes` (host-side run).

### Compatibility (R1)
Additive & offline-first: new modules + host enrichers + endpoints + sidecars (cage.json, pn_nsn.json,
xref_online.json). The index is never written; X4 stays off unless you enable it; RPS-safe (ES5 card, stdlib).

---

## [0.78.1] — 2026-06-03 — Part# review panel + breakdown image in the dossier
- **🔧 Part# review** (header) — an overlay listing low-confidence RPSTL rows with "Open" (jump to the page)
  and inline "✎ Fix" (correct name/NSN → `rpstl_override.json`). Bulk-fix the OCR-noisy tail in one place.
- **Dossier** now shows a **Breakdown image** card (the part's cited figure crop) alongside catalog refs,
  procedure, look-alikes, schematic and 3-D. The 3-D modal already shows it (Manual illustration tab, 0.76).
- Additive, ES5, read-only on the index (R1/R6).

---

## [0.78.0] — 2026-06-03 — Part-number ↔ figure correlation (RPSTL rows + breakdown image)
*(A part number now resolves to its exact item, its real name, and DISPLAYS its correlative breakdown image.)*

### Added — `engine/rpstl_feature.py` (RPSTL parts-list row parser)
- **`parse_line`/`parse_page`** turn the parts-list table into structured rows — **item · SMR · NSN · CAGEC ·
  PART NUMBER · NOMENCLATURE · QTY** — via multi-signal column detection (NSN regex, 5-char CAGEC, SMR codes,
  leading item#, part-number token, letter-rich nomenclature, trailing qty), **confidence-scored**. Excludes
  the matched codes from the nomenclature so it comes out clean (e.g. `HOSE,NONMETALLIC`, not `PAOZZ HOSE…`).
- **`lookup(pn, cagec)`** resolves a part number to its row + the **breakdown image URL** (`/figcrop`) + a
  callout URL, with **variant grouping** (`12420572-010` ↔ `12420572-010X` via a base key) and override
  support. Reads a **sidecar** `index/rpstl.db`; the main index is never written (R1/R6).
- **`review` / `save_override`** — low-confidence rows + an append-only `rpstl_override.json` correction store.

### Added — host build
- **`build_rpstl.py` + `BUILD-RPSTL.bat`** — scan the RPSTL pages, parse rows, and **validate/repair the
  nomenclature against PUB LOG/FLIS** (`ref_nsn` INC item name): the OCR'd `HOSE NONMET` becomes the official
  `HOSE,NONMETALLIC`. Writes the sidecar; read-only on the index.

### Added — routes + UI
- `GET /api/part_by_number?pn=&cagec=`, `GET /api/rpstl_review`, `POST /api/rpstl_override`,
  `GET /api/callout_crop?doc=&page=&item=` (T3, **gated**: a tight crop around the item-number balloon, else
  the **whole figure** fallback).
- **Search a part number → a "PART NUMBER MATCH" card at the top of results** showing the **breakdown image**,
  the FLIS-validated nomenclature, NSN (→dossier), item/CAGEC/FIG, a **🎯 Zoom to item** (callout) / **🖼 Whole
  figure** toggle, and an inline **✎ Fix this match** for low-confidence rows.

### Tiers delivered (your call)
T1 RPSTL row parser ✓ · T2 FLIS cross-validate ✓ · T3 callout localization ✓ (gated + whole-figure fallback) ·
T4 part-number-first UX ✓. Low-confidence rows → review/override ✓.

### Verified
- Parser on real-shaped lines incl. your example: `7 PAOZZ 4720-01-234-5678 19207 12420572-010 HOSE,NONMETALLIC
  2` → item 7 / NSN / CAGEC 19207 / PN 12420572-010 / **HOSE,NONMETALLIC** (codes excluded from the name);
  variant `-010X` groups to base `12420572`. Full host build on a fixture: 2 rows, **FLIS repaired** `HOSE
  NONMET`→`HOSE,NONMETALLIC` and `WSHR`→`WASHER,LOCK`; `lookup` returns the breakdown **image_url**. Callout is
  gated (returns None → whole-figure fallback) when the balloon isn't found unambiguously. Routes added to
  `test_routes` (host-side run). Build the sidecar with `BUILD-RPSTL.bat`.

### Compatibility (R1)
Additive: a new module + host builder + four endpoints + a search card + two sidecars (rpstl.db,
rpstl_override.json). The index is never written; offline; RPS-safe (the part card is ES5; callout needs the
optional Tesseract, else it falls back to the whole figure).

---

## [0.77.0] — 2026-06-03 — Scanned-page caption tightening + experimental local image→3D scaffold

### Tightened — scanned-page figure crops (`figures_feature.py`)
The 0.76 crop fell back to "top 62%" on scanned manuals (no text layer). Now, for pages with little/no text
layer, it gets the figure boundary precisely:
- **OCR word-box caption anchor** — on-demand OCR (pytesseract, optional) finds the "FIGURE n" caption and
  crops the illustration **above** it. Gated by `VIEWER_FIGCROP_OCR` (default on); degrades silently if no
  Tesseract.
- **Row ink-density fallback** — if OCR isn't available, a numpy row-darkness profile finds where the dense
  parts-table band begins and crops above it.
- **top-62%** remains the final fallback. Verified: a synthetic image-only page cropped to **top 49%** via the
  OCR caption (vs the old loose 62%); born-digital pages unchanged.

### Added — EXPERIMENTAL local image→3D (`image3d_experiment.py`, opt-in, NOT authoritative)
A **scaffold** (off until you configure a backend) to turn a part's figure crop into a rough mesh using a
**local** model on **your GPU**, shown only in the *Approximation* tab, always watermarked "ARTISTIC
APPROXIMATION — NOT TO SCALE".
- Configurable backend (`VIEWER_IMG3D_CMD` env or `engine/image3d_backend.txt`, template with `{in}`/`{out}`);
  writes OBJ to the `mesh3d` sidecar; an OBJ→`{V,F}` parser feeds the WebGL viewer.
- Endpoints: `GET /api/image3d?nsn=` (status), `POST /api/image3d` (generate, gated), `GET
  /api/image3d_mesh?nsn=` (mesh for gl3d). UI: the Approximation tab loads a generated mesh, offers
  "⚙ Generate (experimental)" when a backend is configured, or points to setup when not.
- Setup guide: `docs/IMAGE3D-SETUP.md`. Verified end-to-end with a trivial cube backend (generate → OBJ →
  parsed V=4/F=2); unconfigured returns a clean setup pointer.

### Why experimental / honest scope
AI-generated geometry is an approximation and must never be treated as engineering-accurate. It's gated,
watermarked, off by default, and the authoritative image remains the **Manual illustration** (cited figure).

### Compatibility (R1)
Additive: tightening is internal to figure cropping (same outputs, just better boundaries); image→3D is a new
opt-in module + three endpoints + sidecar, disabled until configured. No index writes; RPS-safe (the legacy
build simply leaves image→3D off; figure crops still work via the page renderer it already uses).

---

## [0.76.0] — 2026-06-03 — Real part imagery: cited figure crops in 3D previews + "Manual illustration"
*(Replaces vague 3D blobs with the manual's OWN cited illustration of the exact part — accurate, legal, offline.)*

### Why (the hard caveats, decided with the user)
Real/AI CAD for military NSN parts isn't the path: CAD + repair/maintenance data is **ITAR-controlled
technical data** (not freely downloadable or bundleable), web CAD is license-restricted and rarely matches the
exact NSN, and AI-generated 3D is an approximation — unsafe to present as authoritative in a maintenance tool.
The authoritative, public-domain, exactly-correlative image already exists: **the manual's own exploded-view
figure**, which every part already cites. (Sources: pmddtc.state.gov, federalregister.gov — ITAR technical data.)

### Added — `engine/figures_feature.py`
- **`figure_for(nsn)`** → the best citing figure (doc/page/fig) from the parts index.
- **Figure-region crop** (`extract` / `get_crop`): PyMuPDF renders just the figure region of the cited page —
  caption-anchored ("FIGURE n" → crop above it), else the graphic-region union, else the top ~62% (RPSTL
  figures sit above the parts table), with a whole-page fallback. Cached as PNG in the **figcache sidecar**
  (index/figcache/); the index is never written (R1/R6).
- **Endpoints:** `GET /api/part_image?nsn=` (cited figure + crop URL), `GET /figcrop?doc=&page=&dpi=` (the
  cropped PNG, extract-on-demand + cached, 24 h browser cache).

### Added — 3D collection page (threed.html)
- **Preview boxes now show the part's REAL cited figure** when available (with a "📄 manual figure" badge),
  falling back to the labeled parametric thumbnail.
- **Modal tabs:** **Manual illustration** (the cited crop, default when present) · **Representative 3D** (the
  FLIS-dimension parametric mesh, kept and clearly labeled "not a CAD model") · **Approximation** (opt-in,
  **off by default**, watermarked "ARTISTIC APPROXIMATION — NOT TO SCALE").

### Added — host bulk prewarm
- **`extract_figures.py` + `EXTRACT-FIGURES.bat`** — pre-extract+cache every part's figure crop from the real
  corpus so previews are instant. GPU note: region detection is a fast CPU/PyMuPDF heuristic; the GPU's real
  wins are OCR (done) and an optional image-similarity match — not the page render (CPU/IO-bound). Stated honestly.

### Opt-in approximation — honest scope
The Approximation tab is a **gated, watermarked** view (off by default). It currently re-uses the parametric
mesh as its base; wiring a true local image→3D model on your GPU is a documented future hook, deliberately not
treated as authoritative. Recommended to keep off for maintenance-critical use.

### Verified
- Region heuristic on a synthetic page: found the "Figure 5" caption and cropped top→caption (excludes the
  parts table). Full path on a fixture index: NSN → cited figure (doc 1/p.1/fig 5) → extracted+cached crop,
  cache hit on repeat, unknown NSN handled. Routes added to `test_routes` (host-side run).

### Compatibility (R1)
Additive: a new module, two read endpoints, a figcache sidecar, and ES5 UI. Parametric 3D is unchanged (just
re-labeled and tabbed). No index writes; offline; RPS-safe.

---

## [0.75.1] — 2026-06-03 — Chapter-split review UI
*(Spot-check and correct the chapter routing from 0.75.0.)*

### Added
- **`GET /api/chapters_review`** — lists every combined manual with its detected sections, per-side landing
  pages, whether it fell back to whole-book (no chapters detected), and whether it's been pinned.
- **"Review chapter splits" panel** in the side chooser — lists combined manuals with their split status;
  "Open" jumps into one to inspect.
- **In-viewer pin controls** — while looking at a page of a combined manual, one-click **⚲ Operator start** /
  **⚲ Maintenance start** pins the current page as that side's section start (`POST /api/chapter_override`),
  and the banner refreshes immediately.

### Verified
- `chapters_feature.review()` on the fixture: the one combined `-12&P` shows 2 sections (op p.1 / mech p.5);
  the non-combined `-10` is excluded. Route added to `test_routes` (host-side run).

### Compatibility (R1)
Additive: one read endpoint + ES5 UI; uses the existing override sidecar. No index writes.

---

## [0.75.0] — 2026-06-03 — Phase 2: chapter-level routing inside combined manuals
*(A combined -12/-13/-14 opens to YOUR side's chapters, not page 1 of the whole book.)*

### Added — `engine/chapters_feature.py` (new DI module)
- **Chapter→side ranges.** For combined manuals only, scans the OCR'd page text for chapter/section headings
  ("CHAPTER 1 OPERATING INSTRUCTIONS", "CHAPTER 4 UNIT MAINTENANCE", "MAINTENANCE ALLOCATION CHART", "DIRECT/
  GENERAL SUPPORT", "REPAIR PARTS"…), classifies each to operator / mechanic / both via a vetted lexicon, and
  builds contiguous page ranges (consecutive same-side chapters merge).
- **Lazy + cached + persisted.** Ranges are computed on first open and cached per doc (keyed on page count),
  persisted to `chapter_sides.json`, so there's no repeated scan. **Falls back to whole-book** when no headings
  are found — never worse than the document-level split.
- **Override-able.** `chapter_override.json` pins a side's landing page in a given manual (`POST
  /api/chapter_override`).
- **Endpoints:** `GET /api/chapters?doc=` (ranges + per-side landing pages), `GET /api/chapter_jump?doc=&side=`.

### Added — viewer (index.html, ES5)
- Opening a **combined** manual with a side active jumps to that side's **first chapter** (only when opened
  generically — a specific search hit still lands on its exact page).
- A slim in-viewer banner shows the current section ("📖 Operator section · p.1–48 · combined manual") and a
  one-click **"This book also has a Maintenance section →"** that jumps to the other side's first chapter.

### Verified
- `chapters_feature` end-to-end on a fixture: combined -12 with operator (CH 1) + maintenance (CH 4/5)
  headings → ranges operator 1–4, mechanic 5–10; landing pages op=1 / mech=5; a non-combined -10 returns
  whole-book; a `chapter_override` to p.6 takes effect. Routes added to `test_routes` (run host-side).

### Compatibility (R1)
Additive: a new DI module, two read endpoints + one write endpoint, a sidecar cache + override JSON (index
never written, R1/R6), and ES5 viewer code. Non-combined manuals and the document-level split are unchanged;
combined manuals just open smarter.

---

## [0.74.0] — 2026-06-03 — Tighter sorting: side-map cache + manual overrides + cover/MAC corroboration
*(Complements the 0.73 split — higher accuracy at constant speed, all RPS-safe.)*

### Added — `engine/sides_feature.py` (new DI module; `core` injected like collections_feature)
- **Side-map cache (speed).** Every document is classified **once** and cached, keyed on a cheap signature
  (PDF doc count + max id + override-file mtime). `/api/by_side`, the counts, and side-filtered search reuse
  the cached map and rebuild only when documents or overrides change — so it's **O(1) after first build**
  instead of re-scanning each call.
- **Manual overrides (accuracy).** `sides_override.json` sidecar (append-only, keeps a log) lets you pin any
  document to `operator` / `mechanic` / `both`. Overrides always win, fixing the uncertain tail without
  guessing. New `POST /api/side_override`.
- **Cover/MAC corroboration (accuracy, no global cost).** For **low-confidence** docs only (no TM coverage
  code), the first OCR'd page is checked for tells — "OPERATOR'S MANUAL" → operator; "MAINTENANCE ALLOCATION
  CHART" / "UNIT MAINTENANCE" / "DIRECT/GENERAL SUPPORT" → mechanic. Runs only on the few unknowns.
- **`tm_side()` now returns `confidence`** — `high` (from the coverage code), `medium` (title/cover wording),
  `low` (defaulted). `override` once pinned.
- **`GET /api/side_uncertain`** — the low/medium-confidence docs, for the review UI.

### Added — UI (index.html, ES5/RPS-safe)
- **Review-uncertain panel** in the side chooser: lists uncertain docs with one-click **Operator / Mechanic /
  Both** pins (→ `POST /api/side_override`), with a live count.
- **`?side=` deep links** open straight to that side; **operator-side declutter** via a `body.viewer-operator`
  class (hides the parts-request CTA; fully reversible by switching sides).

### Planned (documented, not built)
- **Chapter-level routing** inside combined manuals — `docs/SIDE-CHAPTER-ROUTING-PLAN.md` (uses the OCR'd TOC
  to drop each side into its own chapters of a -12/-13/-14). Trigger after the real-corpus split is reviewed.

### Verified
- `tm_side` confidence 5/5 (high/medium/low). `sides_feature` end-to-end on a 6-doc fixture (incl. OCR cover
  pages + an override): counts 3 operator / 4 mechanic / 1 both / 1 uncertain; cover→operator, MAC→mechanic,
  override flips the doc and the cache rebuilds. Route added to `test_routes` (run host-side — the sandbox
  mount was serving stale reads at build time).

### Compatibility (R1)
Additive: a new DI module, two read endpoints + one write endpoint, sidecar JSON (index never written, R1/R6),
and ES5 UI. The 0.73 behaviour is unchanged when no overrides exist; faster because of the cache.

---

## [0.73.0] — 2026-06-03 — Two sides of the house: Operator (10) vs Mechanic (20)
*(Splits the whole repository by maintenance level, and opens with "Choose your side of the house".)*

### Added
- **Authoritative `tm_side()` classifier (`patterns.py`).** Divides every document into the **operator
  (10-level)** and/or **mechanic (20-level)** side using the Army TM *coverage indicator* — the trailing
  level field of the TM number: `10` → operator; `12/13/14/15` → **both** (combined manuals); `20/23/24/25/
  30/34/35/40` → mechanic; `…P`/`…&P` (RPSTL) and `LO` → mechanic. Deterministic from the TM number, with a
  title/wording fallback only when no code is present. Basis: Army Publishing Directorate TM product maps +
  the standard TM-numbering coverage table. (PUB LOG is NSN/parts data and does **not** classify TM levels,
  so the TM number itself is the correct authority here.)
  - Guards the commodity number (the `11` in `TM 11-…`) from being misread as a level — only the trailing
    2-digit field counts.
- **`/api/by_side?side=operator|mechanic`** — lists the documents on a side, with live counts
  (operator / mechanic / both / total). Classified **live**, so it's read-only on the index (R1/R6) and
  reflects new docs instantly. **`side=` filter added to `/api/search`** so results respect the chosen side.
- **"Choose your side of the house" modal** (first screen). **Operator** → goes straight to the browser and
  **skips the parts-request sheet**; **Mechanic** → opens the **parts-request sheet** onboarding. The choice
  is remembered (localStorage) and auto-applied next launch; a header **🏠 Side** button switches anytime.
- **`classify_sides.py` + `CLASSIFY-SIDES.bat`** — sorts EVERY document host-side and writes
  `index/sides.json` (per-doc side, counts, and an *uncertain* review list). The app classifies live with the
  same function; this gives the full sorted manifest + an audit of the split.
- Tests: `test_patterns.py` gains `tm_side` cases (incl. the commodity-number trap); `test_routes.py` covers
  `/api/by_side` (×3) and side-filtered search.

### Design notes
- **Combined manuals (-12/-13/-14) appear on BOTH sides** by design — a -12 is genuinely an operator book and
  a maintenance book. Pure -10 stays operator-only; pure -20+/RPSTL/LO stays mechanic-only.
- Undetermined docs (no code, no telltale wording) default to the **mechanic** side (the fuller set) and are
  listed in `sides.json` → `uncertain` for your review.

### Verified
- `tm_side` logic: 11/11 cases incl. `-10`, `-20`, `-24P`, `-12&P`, `-13&P`, `LO …-12`, `-34`, `-23&P`, and
  the `TM 11-…-10` / `TM 10-…-20` commodity-number edge cases. `classify_sides` tally verified on a 6-doc
  fixture (3 operator / 5 mechanic / 2 both / 1 uncertain). Server routes added; run host-side
  `RUN-ALL-TESTS.bat` to confirm `/api/by_side` in the live route suite (sandbox mount was serving stale
  reads at build time — see 0.72.x notes).

### Compatibility (R1)
Additive: a new classifier, two read-only endpoints, a new entry modal, and host tooling. No schema change;
the index is never written; the parts-request sheet and 104th export are unchanged (just reached via the
mechanic side). Old direct links still work.

---

## [0.72.3] — 2026-06-03 — Audit pass: preflight hang fix + connection-leak fixes + mutation harness
*(Triggered by "the program hangs on preflight" + a request for a top-to-bottom audit & mutation testing.)*

### Fixed
- **Preflight hang on startup.** `preflight.py`'s `index` check ran a full `PRAGMA quick_check`, which reads
  **every page of the 3.65 GB index** — instant when the DB was small, minutes once OCR filled it, so startup
  looked frozen. Now the default is a millisecond `_index_probe` (open + page header + catalog + sentinel
  read); databases over `VIEWER_LARGE_DB_MB` (512) auto-skip the full scan; the full scan is opt-in via
  `--deep` and is **time-budgeted** (`set_progress_handler`, 20 s) so it can never hang. Also speeds up
  `/healthz` and the watchdog, which share this code.
- **Connection leak in `procedure_full` (procedure_feature.py).** Opened `core.db()` and never closed it —
  one leaked SQLite connection per `/api/procedure_full` call. Now closed in a `finally`.
- **Connection leak in `threed_refs` (viewer_app.py).** Both the early-return and the normal-return paths
  left the connection open. Both now close.

### Recovered
- **`procedure_feature.py` infinite loop.** During this audit, a SIGKILL of the *old* mutation runner (whose
  restore ran only in a `finally`, which a hard kill skips) left a one-token mutant on disk: the tools-header
  line read `i -= 1` instead of `i += 1`, an infinite loop. Caught by the new `test_procedure.py` (the parser
  had **no** dedicated test before), root-caused, and restored. The harness was then hardened so this can't
  recur (see Added).

### Added
- **`engine/tests/mutate.py`** — a generic, dependency-free **mutation tester**. It auto-generates mutants for
  any module (comparator/arithmetic/boolean/constant/aug-assign swaps), runs your test command per mutant, and
  reports killed/survived/timeout + JSON. Safety: restores the original **after every run** (not just at the
  end), keeps a `.orig` sidecar, and verifies a SHA match at the end — so an interrupted run can't leave the
  source broken. RPS-safe (stdlib `tokenize`/`subprocess`/`hashlib`, py3.6+).
- **`engine/tests/test_procedure.py`** — the missing unit test for the procedure parser (kind, tools,
  classified warnings, steps, sub-steps, torque/FIG/NSN/part-number enrichment).
- **`RUN-MUTATION.bat`** — runs the existing curated suites (core_pillars + safeguard) plus `mutate.py` across
  the engine on your PC, and writes a results file.

### Measured (mutation)
- `patterns.py`: **100%** kill (13/13). `procedure_feature.py`: **20%** kill of the sampled sites — most
  survivors are in `procedure_full` (needs a DB-backed test) and in caps/continuation boundaries. Logged as a
  coverage gap to close, not a correctness bug.

### Compatibility (R1)
All fixes additive/rollbackable: a faster default preflight (full scan still available via `--deep`), two
`finally: con.close()` guards, and new test/tooling files. No schema/route/corpus change.

---

## [0.72.2] — 2026-06-03 — Fix: /api/threed_refs 500 (orphaned `_collections_defs` after modularization)
*(The one red line in VERIFY-ALL: `GET /api/threed_refs?nsn=… -> 5xx: 500`.)*

### Fixed
- **`/api/threed_refs` returned HTTP 500 whenever a valid NSN was passed.** When the 3D→manual hookup tried to
  list which Smart Collections a part falls into, it called `_collections_defs()` — a helper that **moved into
  `collections_feature.py` during the v0.70 modularization** but was never imported back into `viewer_app`'s
  namespace. At request time Python raised `NameError: name '_collections_defs' is not defined`, the route's
  `except Exception` turned it into a 500.
- **Fix:** added `_collections_defs` to the `from collections_feature import (...)` line in `viewer_app.py`.
  One name, one line. The injected-`core` dependency pattern still resolves it at call time.

### Why the other tests were green
The bug only fires on the *collection-membership* branch, which only runs when a real NSN produces an FTS phrase.
The page-search branch above it has its own `try/except`, so the rest of `threed_refs` — and every other route —
was unaffected. That's why it was exactly **one** failing line out of 86 checks.

### Verified
- Reproduced the mechanism in isolation: importing an underscore-prefixed name from the feature module **and**
  the injected-`core` call both resolve correctly. Grepped `viewer_app.py` for any *other* orphaned collections
  internals (`_collections_path`, `_seen_map`, `_scope_where`, `SEED_COLLECTIONS`, …) — **none**; this was the only one.
- Re-run `VERIFY-ALL.bat` host-side to confirm `test_routes.py` goes 34/34 (the sandbox mount can't run the
  server suite — see the same note in 0.72.1).

### Compatibility (R1)
Pure fix, fully rollbackable: one import line added, no behavior/schema/route/corpus change. Modularization
(v0.70) stays intact; this just reconnects a name it left behind.

---

## [0.72.1] — 2026-06-03 — Answer: most-common part nomenclature (host-side ranking)
*(Answers "which part comes up THE MOST?" — now that everything is OCR'd in.)*

### Added
- **`engine/top_nomenclature.py` upgraded** — now emits three views and **saves them to `index/MOST-COMMON-PART.txt`**:
  the headline most-common **nomenclature**, the most-common **exact NSN** (the single recurring part), and an
  optional **official FLIS item name** lookup (`--flis`) that resolves the top NSNs' INC → H6 item name from PUB LOG.
  Opens read-only (`mode=ro` + `query_only`, `immutable=1` fallback) so it's safe to run while OCR/the app is live.
- **`ANSWER-MOST-COMMON-PART.bat`** — one double-click: runs the ranking on the live index, prints the answer,
  saves the txt, and opens it in Notepad.

### Why host-side
The live index is **3.65 GB** (header says 891,556 × 4 KB pages). The dev sandbox mount only serves ~3.637 GB of it
(~14.5 MB / ~3,500 pages short), so SQLite reads it as *malformed* there. The file on the PC is fine — so this one
number must be produced on the machine that holds the whole file. Logic was fixture-verified in isolation.

### Verified
- Ranking SQL (headline nomenclature, NSN-frequency excluding nulls, COALESCE label fallback) confirmed on a
  synthetic `parts` fixture: top nomenclature, per-NSN counts, vehicle/NSN distinct counts all correct.

### Compatibility (R1)
Additive: a new bat + an enhanced read-only script. No schema, route, or existing-file behavior changed; corpus and
index untouched. Old invocation (`python top_nomenclature.py`) still works.

---

## [0.72.0] — 2026-06-03 — Reconstituted Fix/procedure pages (all 4 + both exports)
*(Turns a how-to buried in a scanned manual into a clean, checkable, exportable step-by-step page — verbatim, never invented.)*
### Added
- **`procedure_feature.py`** — a deepened parser + correlation engine (new module, DI-injected `core`, no
  import cycle). `parse_procedure()` extracts **tools**, **classified warnings** (NOTE / CAUTION / WARNING /
  DANGER), **numbered steps with sub-steps** (`a.`/`(1)`), and **per-step torque / figure / NSN / part-number**
  callouts. `procedure_full(query)` finds the best procedure in the OCR'd text and returns the structure + its
  **source page** + the **parts (NSNs) it involves** + the **fault terms**. Route `/api/procedure_full`.
- **Rebuilt `procedure.html`** (ES5-safe) delivering all four requested pieces:
  1. **Side-by-side verify** — rebuilt digital steps next to the **original scanned page** (click to open full
     size); figure chips jump to the cited figure on the source page.
  2. **Clean rebuild + export** — polished steps with warnings pinned, tools, and inline **torque / FIG / NSN**
     chips; a **🖨 Print sheet** (print-CSS) take-to-the-bay export.
  3. **Correlate to parts & fault** — a parts panel (each NSN → the dossier, with PUB LOG manufacturer /
     interchangeable) and the fault terms that found it.
  4. **Interactive checklist** — tick each step as you go; state persists in `localStorage`.
### Verified
- `procedure_feature` parser isolation-tested on a synthetic procedure: tools, WARNING+NOTE classified, 4 steps,
  **sub-steps** captured (after a regex fix), per-step **35 ft-lb** torque, **FIG 5 / 12-3**, NSNs
  `5305-01-674-1467` / `2920-01-449-2202`, and `procedure_full` returned the right **source page (42)** + parts.
  `procedure.html` confirmed **ES5-clean**; route + `_SUB_RE` fix confirmed on host; `/api/procedure_full` added
  to the `test_routes` congruence suite. **Caveat:** the sandbox mount is corrupting reads of multiple files, so
  the server-dependent suite is verified host-side via `RUN-ALL-TESTS.bat`. Diagram 86.

## [0.71.0] — 2026-06-03 — Schematic Highlighter (Phase 1) + end-to-end demo/test suite
### Added — schematic highlighter (Phase 1)
- **Clickable vector overlay** — on a vector schematic, the new **🖍 Highlight** toggle replaces the static
  image with an interactive SVG (the page + its real geometry from `/api/schempaths`): **hover outlines** an
  element, **click highlights the whole connected net/trace** (connected-group, the recommended default),
  with its own zoom. `schemhl.js` (ES5-safe) + `schem_overlay.py` (extracts paths/text via PyMuPDF on demand,
  normalized 0..1, no conversion). Routes `/api/schempaths` + `/schemhl.js`.
- **Raster fallback** — scanned sheets (no vector geometry) show the existing **callout chips** (NSN/part/figure
  → dossier/Look-Alike) instead, with an honest "this is a scan" note. (~45% of sheets are vector → clickable;
  flood-fill for the rest is Phase 2, deferred per choice.)
### Added — end-to-end demo / test suite (congruence)
- **`test_routes` expanded** into a full congruence check — starts the real server against the fixture and hits
  **every major route** (search, collections, callouts, 3D refs, **schempaths**, **tags**, **keywords**,
  dossier, procedure, healthz, the static bundles…), asserting no 5xx + valid JSON. Wired into
  `RUN-ALL-TESTS.bat`.
- **`docs/DEMO-SCRIPT.md`** — a green-before-you-demo gate (`RUN-ALL-TESTS.bat`) + a ~6-minute end-to-end
  demo flow (slang search → tag → page/loupe/callouts → schematic highlighter → detailed 3D → collections →
  solve→packet → PUB LOG dossier) + finishing touches and recovery notes.
### Verified
- Components verified in-sandbox: `schem_overlay` against **real corpus** schematics (alternator-gauge →
  607 line segments + 201 text boxes; raster → flagged non-vector), `schemhl.js` syntax + **ES5-clean**,
  the schematics.html toggle wiring + both routes + the expanded `test_routes` confirmed on host. **Honest
  caveat:** the sandbox mount is intermittently corrupting reads of the large `viewer_app.py` (and now other
  files), so the server-dependent suite couldn't be *run* here — the authoritative gate is `RUN-ALL-TESTS.bat`
  on Windows. The host files are intact (authoritative tools confirm).

## [0.70.1] — 2026-06-03 — Fix: app wouldn't start (circular import) + schematic path extractor
### Fixed (critical — "refused to connect")
- The 0.70.0 modularization made `collections_feature.py` do `import viewer_app as core`. That's fine when the
  app is imported as a module, but when it runs as **`python viewer_app.py` (`__main__`)** — the real launch —
  it re-imports the script as a *second* module and **dead-locks the import cycle**, crashing the server on
  startup (Edge then shows "refused to connect"). My `import viewer_app` sandbox test didn't catch it because
  that path uses a different module name. **Fix:** removed the import from `collections_feature` (now `core =
  None`) and `viewer_app` **injects itself** as `core` after importing it (`_cf.core = sys.modules[__name__]`)
  — no cycle, and `core.DB_PATH` correctly reflects the `--db` override. Verified: `collections_feature` works
  with an injected `core` (6 groups, eval returns the matching page); the cycle is gone by construction.
  *(Tip: run `run_app.bat` to START the server, then open the URL — it auto-opens; opening the URL without
  running the .bat also shows "refused to connect".)*
### Added (Phase 1 of the schematic highlighter — core extractor)
- **`schem_overlay.py`** — `schem_paths(pdf, page)` reads a vector schematic's drawing ops + word boxes via
  PyMuPDF on demand (no conversion) and returns them as **normalized 0..1** coords for a clickable SVG overlay;
  auto-detects vector vs raster. Verified on the real corpus: `Schematic - alternator gauge.pdf` → **607 line
  segments + 201 text boxes** (coords in range); raster `Schematic - boom.pdf` → 0 paths (flagged non-vector,
  uses callout-hotspot fallback). The route + interactive overlay UI wire in once the launch is confirmed and
  the mount is stable.

## [0.70.0] — 2026-06-03 — Engine modularization (begun) + truncation cleared
*(The 9p-mount truncation that motivated this has cleared — the sandbox now reads/compiles the full `viewer_app.py` and all suites pass — so this could finally be done with verification.)*
### Changed
- **Extracted Smart Collections into `collections_feature.py`** — the largest cohesive block now lives in its
  own module (229 lines). `viewer_app.py` dropped **2,251 → 2,020 lines**. The module imports `viewer_app as
  core` and uses `core.db` / `core.DB_PATH` at call time (import-cycle-safe); `viewer_app` pulls the five
  route-called names back into its namespace, so the handlers are unchanged.
- The engine was already multi-module (`rps`, `preflight`, `patterns`, `safeguard`, `sysprobe`,
  `viewer_ingest`, `parts_request_pdf`, `core_pillars`, `partgeo.js`, `gl3d.js`, …); this starts splitting the
  one remaining monolith. Remaining feature groups (callouts, threed_refs, keyword/tag writers) follow the
  **same proven, verified pattern**, extracted incrementally behind a snapshot.
### Verified
- After the extraction: `viewer_app` + `collections_feature` compile, `import viewer_app` OK,
  `collections_feature.smart_collections_list.__module__ == "collections_feature"`, **23/23 pillars + 21/21
  features + 20/20 route-smoke** (which hits `/api/collections` against the fixture server) — all green. The
  authoritative file tools confirm `viewer_app.py` is well-formed (the intermittent "null byte" reads were the
  flaky mount, not the file).

## [0.69.0] — 2026-06-03 — Inline part tagging (background pencil), not a foreground feature
*(Reworks the keyword/tag UX per request: tagging lives in the background while you browse — a small pencil on each part — instead of a prominent feature page.)*
### Added
- **`ui/tagger.js`** — a dependency-free, ES5-safe inline tagger. A quiet **pencil icon** marks a part as
  tag-able; clicking opens a small popover to **add/remove your own words (tags) for that part**. Served at
  `/tagger.js`.
- **Pencil on every part while browsing** — on search-result cards that carry an NSN, and on **every** 3D
  library card. (Same component drops onto the dossier / Look-Alike pages next.)
- **Per-part tags feed search** — `user_tags_add/for/remove` + `GET/POST /api/tags` store tags in the
  `keywords_user.json` sidecar keyed by NSN (else name); `_load_synonyms` folds each part's `name + NSN +
  tags` into the offline search expansion and **live-reloads**, so a tag you put on a part also finds it.
### Changed
- **De-emphasized the dedicated keyword page** — removed the prominent `🏷 Keywords` nav button; `/keywords`
  remains only as a quiet "manage all" link inside the tag popover. The tag system is background, surfaced via
  the pencil — exactly as requested.
### Verified
- `tagger.js` syntax-clean and **ES5-clean** (RPS gate updated to cover it). Tag logic isolation-tested:
  tagging NSN 6140-01-485-1472 ("battery, storage") with "juice box" makes "juice box" find the NSN **and** the
  name, and tags become mutually findable (power cell ↔ juice box ↔ name ↔ NSN). Server functions + `/api/tags`
  + `/tagger.js` routes confirmed on host. Diagram 83.

## [0.68.0] — 2026-06-03 — 3D viewer: detailed parametric part models (no more blocks)
*(The renderer was already glossy; the geometry was the weak point. Replaced the box/cylinder primitives with recognisable, family-specific meshes driven by the FLIS dimensions + characteristics.)*
### Added
- **`ui/partgeo.js`** — a dependency-free geometry library that builds **detailed part meshes**: a **bolt** with
  a real hex head + threaded shank, a **nut** as a chamfered hex with a bore, a **washer**/**gasket** as a ring
  (gasket with **bolt-holes**), a **bearing** with outer/inner **races + a ring of balls**, a **gear** with
  **teeth** + bore, a **spring** as a **helix**, a **tube/pipe** as a hollow cylinder, an **o-ring/seal** as a
  **torus**, a **pin/shaft** with chamfered ends, a **bracket** (L + holes), and a **battery** (body + terminal
  posts). 12 families + a smooth fallback; classified from the item name/characteristics.
- Wired into `threed.html`: the gallery thumbnails stay light (fast grid), and **opening a part upgrades it to
  the detailed mesh** — rendered by the existing WebGL shader (smooth normals, glossy) and the SVG fallback.
  Served at `/partgeo.js`.
### Invariants
- Honest: still **representative parametric models** (the TMs carry no CAD geometry), but now driven by the real
  measured dimensions + FLIS characteristics, so they look like the part, not a block. Detail benefits the
  WebGL **and** the SVG/legacy path. No new dependency.
### Verified
- `partgeo.js` node-validated: all **13 families** produce finite, non-degenerate meshes (no NaN, valid face
  indices, sensible vertex/face counts — bolt 399V/240F, bearing 1342V, spring 2120V, gear with teeth), and the
  **family classifier is 12/12** on real nomenclatures (BOLT→bolt, BEARING, BALL→bearing, GEAR, SPUR→gear, …).
  threed.html wiring + the `/partgeo.js` route confirmed on host. Diagram 82.

## [0.67.0] — 2026-06-03 — PUB LOG cross-reference, repository mode, and a keyword/tag layer
### Added — PUB LOG (publog) cross-reference
- **Extended `enrich_flis`** to tap data it ignored, matching every NSN in the index against the DLA FLIS
  tables: **manufacturer name + location** (from `P_CAGE` via the CAGE code), **colloquial/common name**
  (`V_COLLOQUIAL_NAME`), and **interchangeable/related NSNs** (`V_FLIS_STANDARDIZATION` → the existing
  `alt_parts` column, so **no schema change**). All **append-only** (`ref_nsn_log`, R6), cited to PUB LOG.
- **`ENRICH-PUBLOG.bat`** — one host-side button that runs the full-folder cross-reference
  (`viewer_ingest.py enrich --publog-dir`), defaulting to `Desktop\publog`, with a pre-snapshot.
### Added — repository / browse mode (onboarding)
- **🔎 Browse the repository** button in the onboarding window — skip the parts-request sheet and use THE
  VIEWER as a pure repository (a "Browse mode" chip shows the state).
- **📋 Parts session** header button — always visible; **reopens the onboarding window** to start/edit a
  104th-sheet session anytime.
### Added — keyword / fuzzy-search layer
- **`keywords.json`** — curated "strange but sensible" shop terms mapped to catalog nomenclature (battery →
  power cell / 12 volt; alternator → charger; grease fitting → zerk; turbocharger → turbo; …), loaded
  alongside `synonyms.json` so slang/functional searches find the right part. **47 groups; 309 terms active.**
- **`build_keywords.py`** — offline generator that folds the **PUB LOG colloquial names** (from enrichment)
  into the keyword groups, merge-only.
- **User keyword/tag manager** (`/keywords`, `keywords.html`, `GET/POST /api/keywords`) — add your own groups
  of equivalent words; they save to a **`keywords_user.json` sidecar** and **live-reload into search
  immediately** (no restart). Directly teaches search your shop's words; indirectly improves every later search.
### Invariants
- Running app stays **offline**; the curated seed was informed by shop-terminology research, enrichment reads
  local PUB LOG only. Append-only / cited (R6). `keywords.html` is **ES5-safe** (RPS gate updated to cover it).
- The onboarding/keyword UI changes keep RPS parity; `index.html` is modern-by-design (exempt).
### Verified
- Enrichment logic isolation-tested on synthetic FLIS CSVs (real headers): item name, part/CAGE, **manufacturer
  + location**, colloquial, **interchangeable → alt_parts**, composed cited description — PASS. Keyword expansion
  PASS (11 slang→nomenclature checks incl. zerk→grease fitting, turbo→turbocharger, lug→terminal). User
  keyword save/dedup/delete + live SYN reload PASS. `keywords.html` confirmed **ES5-clean**. All server
  functions + routes confirmed on host. Diagram 81.

## [0.66.0] — 2026-06-03 — OCR scan COMPLETE — finalize the full corpus
*(The scan finished. The text layer has been wiring itself in as it filled — this locks in the now-complete scan.)*
### Context — already live
- The `pages_fts` trigger means **search, find-in-manual, Smart Collections (auto-fill + "new" badges),
  page/schematic callouts, and 3D references** have read the OCR text **as it filled** — every page became
  searchable the moment it was OCR'd, with no rebuild.
### Added
- **`FINALIZE-OCR.bat`** — one host-side button that locks in the complete scan, in order: (1) re-extract the
  **structured parts index** from every now-readable RPSTL page (`viewer_ingest.py parts`); (2) **optimize the
  index** (`optimize_index.py` rebuilds `suggest_terms` from the **complete** vocabulary so predictive type-ahead
  finally covers the whole corpus, + ANALYZE + WAL + indexes); (3) **milestone backup** (`safeguard snapshot
  --with-db` — a consistent copy of the finished index); (4) **OCR completion report**; (5) **top nomenclatures**;
  (6) **health check** (`verify_all`).
- **`top_nomenclature.py`** — ranks the most common part nomenclatures across the corpus (answers the standing
  question: which part — a battery, a specific bolt, a gasket — comes up most), with an optional `--vehicle`
  scope. Read-only.
### Why host-side
- The multi-GB `viewer.db` can't be read or written coherently through a sandbox mount (`mode=ro` wants the WAL
  shm; `immutable=1` returns a torn/"malformed" image). Finalizing writes the index, so it runs on Windows.
### Verified
- `top_nomenclature.py` compiles and ran against the fixture (ranked BOLT, MACHINE over BRAKE CHAMBER, with the
  nomenclature→name→fig_title fallback). `FINALIZE-OCR.bat` + scripts confirmed on host. Diagram 80 (rendered via
  the new `_common.py`). RPS lint still green.

## [0.65.0] — 2026-06-03 — Foundation batch (part 2): shared code + route smoke test
*(De-duplication + a wider test net. The new diagram for this entry is itself rendered by the new shared helper — dogfooding the cleanup.)*
### Added
- **`patterns.py`** — one home for the NSN / FIG / labeled part-number regexes + `norm_nsn` / `digits` /
  `nsn_fts_phrase`, currently copied across search, callouts and `threed_refs`. `tests/test_patterns.py` pins
  the behavior (dashed + bare NSN canonicalize the same, FIG ranges, labeled P/N only, FTS phrase form) — **9/9
  pass**. The modularization (#36) will switch the `viewer_app` copies to `from patterns import …`.
- **`docs/diagrams/_common.py`** — shared diagram helpers (palette + `box`/`t`/`wrap`/`panel`/`svg_open`/`render`)
  that were re-declared in all 78 generators. New generators do `from _common import *`. **Diagram 79 is built
  with it**, so it's proven, not theoretical.
- **`tests/test_routes.py`** — route smoke test: starts the **real server** against the deterministic fixture
  index and hits every known endpoint, asserting **no 5xx** and valid JSON on `/api/*` + `/healthz`. Wired into
  `verify_all.py` (now runs pillars + features + **patterns** + **routes** + truncation).
### Verified
- `patterns.py` compiles, `test_patterns` 9/9. `_common.py` rendered this entry's diagram (proof). `test_routes`
  + `verify_all` compile; the route suite runs host-side (it imports `viewer_app`). RPS lint still green.
### Deferred (honest)
- The UI helper/CSS consolidation (`ui/shared.js`, `ui/base.css`, backlog #2-3) is **not** a quick win: the `$`
  helper means different things per page (`getElementById` vs `querySelector`), so a safe consolidation needs a
  careful dedicated pass — folded into the modularization / UI batch rather than rushed here.

## [0.64.0] — 2026-06-03 — Foundation batch (part 1): the test + RPS gate
*(First slice of the 90-item improvement backlog. Builds the harness that auto-verifies every later change — and caught a real legacy-parity bug on its first run.)*
### Added
- **RPS lint** (`tests/rps_lint.py`) — the "does legacy still work?" gate. Scans every `ui/*.html` + `*.js`
  for **ES6 syntax that polyfills can't fix** (arrow, `const`/`let`, template literals, spread, `for…of`,
  `class`, `async`/`await`). **ES5-required** pages (the mechanic-facing tools) **fail** the gate on any ES6;
  rich pages (3D/WebGL/loupe/circuit sim) are **modern-by-design** and exempt (reported for visibility).
- **`/healthz`** — new GET endpoint returning the preflight checks as JSON (python/disk/DB integrity/schema/GPU);
  `503` on a fatal check. Feeds the watchdog and a future ops status badge.
- **`RUN-ALL-TESTS.bat`** — one host-side command = regression suites + safeguard truncation/integrity verify
  **+ the RPS lint**. Exit 0 only when additives pass **and** legacy parity holds. This is the "test all
  additives and the retroactive" loop, automated.
### Fixed
- **`status.html` legacy-parity bug** (caught by the new gate) — the OCR/system dashboard, an ES5-required
  page, contained ES6 (arrow ×5, `const` ×13, `let` ×3, `async`/`await`) and would have thrown a SyntaxError
  on IE11 / Win7. **Rewritten in clean ES5** (`var` / `function` / XHR); re-verified ES5-clean.
### Verified
- `rps_lint.py` compiles and ran against the real 20 UI files: every ES5-tier page is clean except the
  `status.html` it flagged; modern pages correctly exempt. `status.html` re-checked **0** arrow/const/let/
  template/async/await. `/healthz` + `RUN-ALL-TESTS.bat` confirmed on the host. Diagram 78.
### Next (Foundation part 2)
- Backlog #2-4/#6/#8 (`ui/shared.js`, `ui/base.css`, `patterns.py`, `diagrams/_common.py`) + the route smoke
  test (#72), then the modularization (#36).

## [0.63.0] — 2026-06-02 — RPS-safe stability suite (health layer)
*(The safeguard "vault" protects files; this adds a thin **health/stability** layer that keeps the program running. All stdlib, no new dependencies, GPU never fatal — identical on modern / lite / legacy.)*
### Added
- **Preflight health gate** (`preflight.py`) — before the server or OCR start, checks **python / free disk /
  DB `quick_check` / schema-version-vs-migrations** and **fails fast with a clear message** instead of
  crash-looping. Schema drift is a WARN (→ `fix_schema_version.py`); **GPU is INFO only** (absent on
  lite/legacy is fine, never fatal). Wired into `run_ocr_auto.bat` (hard gate) and `run_app.bat` (informational).
- **Disk-space guard** (`disk_ok()` in `preflight.py`) — watches free space on the index drive (default 1 GB
  floor; env `VIEWER_MIN_FREE_MB`). OCR **pauses a pass cleanly** when low (the auto-runner retries) and the
  **page-render cache stops writing** (`rps.cache_write`). **Fail-open**: if free space can't be read, work
  continues, so a probe glitch never halts the app.
- **Off-disk backup mirror** (`safeguard.py mirror --to <dir>`, `BACKUP-OFFDISK.bat`) — copies the snapshot
  vault to a **second location** (USB / external / network), verifying every file by **SHA-256**, so one disk
  failure can't lose both the data and its backups. (The daily snapshot+verify task already exists.)
- **Watchdogs** — `watchdog_app.bat` supervises the web server and **auto-restarts** it if it crashes; OCR now
  writes a **heartbeat** each batch and `ocr_watchdog.py` flags a **hung pass** (stale heartbeat) vs a healthy
  one. (The auto-runner already restarts a pass that *ends* early; this catches one that *hangs*.)
### Invariants
- **RPS parity preserved:** stdlib-only, no new deps, modest thresholds, GPU never fatal, nothing assumes a
  modern OS — lite/legacy behave identically. All additive; the disk guard fails open.
### Verified
- `preflight.py` and `ocr_watchdog.py` compile and pass functional tests (gate goes no-go only on fatal
  checks; GPU stays INFO; watchdog flags a fresh vs a 2-hour-stale heartbeat). The off-disk mirror is
  SHA-256-verified in an isolation test (latest + all snapshots). The disk guard fails open. All server/OCR
  edits confirmed intact on the host via authoritative tools (the in-sandbox compile noise was the known
  truncation). Run `VERIFY-ALL.bat` host-side to compile-check the whole tree. Diagram 77.

## [0.62.0] — 2026-06-02 — 3D library wired to the manuals (Batch 3 of 3)
*(Final batch wiring the OCR text layer in. Read-only on the index; safe alongside the live scan.)*
### Added
- **3D part → manual references** (`threed_refs()` + `GET /api/threed_refs`, `viewer_app.py`) — opening a
  representative 3D part now queries the text layer for the **manual pages that mention its NSN** and shows them
  in the modal's side panel as clickable links (each opens the page with the NSN highlighted). The NSN is turned
  into an FTS **phrase of its number groups** (`"2540 01 123 4567"`) so it matches the dashed form regardless of
  how the tokenizer split the hyphens; the part number is also matched when present.
- **Collections membership** — for each Smart Collection, a cheap `EXISTS` asks whether any page matches **both**
  the part's NSN **and** the collection's query, so a part can show e.g. *"In collections: Torque specs."*
- **Dossier / Look-Alike jumps** — one-click from the 3D part to its **part dossier** and **Look-Alike Parts**
  (`threed.html` `loadRefs()`); `buildModel()` now carries `part_no`.
### Invariants
- **Read-only, no OCR contention (R1/R6):** one `/api/threed_refs` fetch per part (an FTS read + a few `EXISTS`);
  WAL means it never blocks the OCR writer. Nothing is written.
- **RPS:** the 3D view already degrades to SVG on old machines; the references panel is plain DOM + `fetch`, so it
  works on the fallback path too. References grow on their own as OCR makes more pages searchable.
### Verified
- Isolation test: the NSN phrase matched the dashed form on the correct page and ignored an unrelated page;
  collection membership returned *Torque specs*, and after an OCR page added a `WARNING` for the same NSN,
  *Warnings* appeared too (the live-growth property). `loadRefs` JS syntax-checks; server function + route confirmed
  on the host. **Completes the 3-batch OCR wiring** (search · page/schematic callouts · collections · 3D). Diagram 76.

## [0.61.0] — 2026-06-02 — Smart Collections: four add-ons
*(Requested enhancements to Batch 1. Still read-only on the index; all writes go to the `collections.db` sidecar, so nothing contends with the live OCR scan.)*
### Added
- **Scope a collection to a vehicle and/or manual-type** — a saved collection can be limited to one vehicle
  (e.g. `M1097`) and/or one kind of manual (Operator `-10`, Maintenance `-20/-24`, Parts/RPSTL, Lubrication,
  Schematics, Troubleshooting). Manual-type is matched with a **boundary `GLOB`** on the TM's level code so
  `-20` lands on the manual level, **not** on the stock-class digits inside a number like `9-2320` — a real
  over-match the test caught and the fix removed. Scope pickers populate from a live vehicle list
  (`/api/collections` now also returns `facets`).
- **"New since last visit" badge** — opening a collection records its current size in a `collection_seen`
  sidecar table; the grid then shows a green **`+N new`** badge for pages that appeared since — a passive
  "what just became searchable in my area" cue, powered by the ongoing OCR fill.
- **One-click Save-as-collection + pin** — a **📌 Save as collection** button on the main results bar turns the
  search you just ran into a collection; **★ pin** floats favourites to the top (works for built-ins too).
- **Group results + printable bay sheet** — group a collection's hits **by vehicle or by manual**, and
  **🖨 Print take-to-bay sheet** builds a clean grouped table (vehicle · manual · page · excerpt, up to 500 rows)
  in a new window for printing.
### Invariants
- **Sidecar-only writes (R1/R6):** scope, pins and seen-counts all live in `collections.db`; the main index is
  never written. Evaluation stays **read-only** (WAL → no contention with the OCR writer). `collections.html`
  remains **ES5-safe** for legacy parity.
### Verified
- Scope isolation test: operator `-10` manuals are correctly **excluded** from the Maintenance filter (the old
  `LIKE '%-23%'` wrongly matched `9-2320`; the boundary `GLOB` fixes it), Parts resolves to `-24P`, vehicle scope
  narrows as expected. "New" badge: opening set the baseline, then an OCR-filled page produced **+1**.
  `collections.html` JS is syntax-clean and **ES5-clean**; the main-page save button block syntax-checks. Server
  functions + the pin route confirmed on the host. Diagram 75.

## [0.60.0] — 2026-06-02 — OCR-driven page callouts (Batch 2 of 3)
*(Second batch wiring the text layer in. Read-only on the index; safe to run alongside the live OCR scan.)*
### Added
- **Page callouts** (`page_callouts()` + `GET /api/callouts`, `viewer_app.py`) — extracts the high-precision
  references in a single page's `body_text` and turns them into one-click jumps: **NSN → part dossier**,
  **labeled part number (`P/N:` …) → Look-Alike Parts**, **`FIG`/`FIGURE n(-n)` → find-in-manual** in that
  document. Works on **native-text and OCR'd pages alike** (OCR fills `body_text`). NSNs are deduped so a
  dashed NSN and its bare 13-digit twin collapse to one; capped at 60/page; tokens are verbatim, never invented.
- **Positioned hotspots + chip bar** (`index.html`) — a new **🏷 Callouts** toggle in the viewer. Where the page
  has a PDF text layer, each callout is matched to its word box and shown as a **numbered dot on the spot**
  (dots follow tilt/zoom and mirror with the page); a **chip bar** lists every callout and always works, including
  on OCR-only pages that have no word boxes.
- **Schematics gate** (`schematics.html`) — the open sheet shows the same callouts as a **clickable chip bar**.
### Invariants
- **Read-only, no OCR contention (R1/R6):** one `/api/callouts` fetch per page reads a single indexed row plus
  the page's word list; **WAL** means these reads never block the OCR writer. Nothing is written.
- **Honest placement:** a dot is drawn only for a token we can actually locate; everything else falls back to
  the chip bar. The shared `page_callouts()` extractor is what **Batch 3 (3D)** will reuse.
### Verified
- Extractor isolation test: on a native page a dashed NSN + its bare-digit twin collapsed to one dossier link,
  two labeled part numbers and two FIG refs were found, and the NSN anchored to its word box; on an OCR-only page
  the same NSN + FIG came through as chips with no coords (the intended fallback). Main-viewer callout JS and the
  Schematics chip loader both syntax-check and run. Server function + route confirmed on the host. Diagram 74.

## [0.59.0] — 2026-06-02 — OCR-driven Smart Collections (Batch 1 of 3)
*(First of three batches wiring the OCR text layer into the program — built to run safely alongside the live scan: read-only on the index, or writing only to its own sidecar.)*
### Added
- **Smart Collections** (`/collections`, `viewer_app.py`, `ui/collections.html`) — a collection is a **saved
  named query evaluated live against `pages_fts`**, so it **auto-fills as OCR turns image-only pages into
  text**: nothing is materialized and nothing re-scans. Six built-in seeds ship in code (Warnings & Cautions,
  Torque specs, Wiring & schematics, Hydraulics, Lubrication & PMCS, Removal & installation); you can **save
  your own** from any search terms and **hide** seeds or **delete** saved ones.
- **APIs** — `GET /api/collections` lists every collection with a **bounded live count** (`COUNT` over a
  `LIMIT 2000` subquery, shown as `2000+` when capped, so the list stays fast on the multi-GB index);
  `GET /api/collections?slug=…` evaluates one and returns page hits with highlighted snippets;
  `POST /api/collections` (`action:"save"|"delete"`) edits definitions.
- **Open-to-page** — clicking a hit opens that exact page with the term **highlighted**, reusing the existing
  `/page` `hl` render. Added to the main nav and the Ctrl-K palette.
### Invariants
- **No OCR contention (R1/R6):** definitions live in a separate **`collections.db`** sidecar (its own file +
  lock, like `correlations.db`/`reviews.db`). Listing and evaluating are **read-only** on the index (WAL → reads
  never block the OCR writer); saving/deleting writes **only the sidecar**, never the main index. If the sidecar
  is absent, the six seeds still work.
- **RPS parity:** `collections.html` is **ES5-safe** (XHR, `var`, no arrow/template syntax) + `rps.js`, so it
  runs on legacy browsers too.
### Verified
- Isolation test on a temp index with the **real FTS triggers**: a blank page was OCR-filled mid-test and the
  *Warnings* count went **1→2**, *Wiring* **0→1**, with no reindex, and the OCR'd page appeared in the live
  results — the intended auto-fill. Save / delete / seed-hide against the sidecar all pass. `collections.html`
  JS is syntax-clean and **ES5-clean** (0 arrow fns, 0 template literals). Server functions + GET/POST routes
  confirmed present on the host. Diagram 73.

## [0.58.0] — 2026-06-02 — Gap-closing optimization pass
*(Four gaps the speed passes hadn't touched — the OCR build, weak-PC startup, the live simulator, and the page/loupe round-trips. Each closed additively, with fallbacks intact.)*
### Added / Changed
- **OCR build — identical-page dedup + adaptive DPI** (`viewer_ingest.py`) — a density probe skips blank
  pages; identical *rendered* pages are md5-hashed so the OCR result is **reused** instead of re-inferred on
  the GPU (`dedup_reused` in the batch log). Sparse pages render at a lower **adaptive DPI** (160 floor),
  **opt-in via `--adaptive`** so accuracy is never silently traded. Corpus stays read-only; applies on the
  next pass.
- **Legacy memory + cold-start warmup** (`rps.py`, `viewer_app.py`) — the open-PDF LRU is now sized **per RPS
  mode** (`doc_cache`: modern 8 / lite 3 / legacy 2) so a low-RAM PC keeps a small footprint. After
  `rps_init`, `main()` **warms the path** (`SELECT 1` + `COUNT(documents)` + one page) so the first real
  request isn't the one paying for parse + cache fill. Reversible.
- **Circuit Lab MNA solver → Web Worker** (`circuitsim-worker.js`, `circuitlab.html`, route in `viewer_app.py`) —
  the continuous **Run loop's** matrix solve now runs **off the main thread**; the page renders from posted
  snapshots, so a heavy circuit can't stutter the UI on a weak CPU. A `WorkerSim` shim exposes
  `v()/i()/state()` from the latest snapshot, so `draw()` is unchanged. **Edit / DC / single-Step stay inline
  and synchronous.** If Workers are unavailable or error, it **falls back to the inline sim** (no breakage).
- **Loupe neighbour-prefetch + result hover-prefetch** (`index.html`) — hovering a search result **warms its
  page render** (debounced, de-duped) so the click opens from cache instantly. The loupe already upscaled
  locally with zero latency; it now also **prefetches the 4 neighbouring crisp crops** so a slow drag stays
  sharp instead of flashing soft-then-sharp. Pure client-side; no new API surface.
### Invariants
- **No overbuild (R1/R6):** no new page or API to learn. OCR + startup wins are server-side and reversible;
  the Worker and prefetch wins are client-side with the original synchronous/inline paths kept as guaranteed
  fallbacks. `--adaptive` defaults **off** so OCR accuracy is never compromised unless opted in.
### Verified
- Worker + `WorkerSim` shim validated in isolation: `node --check` on the worker and the extracted shim/run
  loop, plus a **mock-Worker run** (init/dc/step posted, snapshots drawn from `v(node)`, inline sim rebuilt on
  stop). Hover-prefetch **dedup + exact URL** asserted. Loupe block and `renderResults`+prefetch block syntax
  checked. **23/23 pillars** pass; `viewer_app` imports clean with the new route.

## [0.57.0] — 2026-06-02 — Speed pass, round 2 (each change measured)
*(Internal optimizations — every one verified to reduce work or bytes.)*
### Added / Changed
- **Compact JSON** — `_send` serializes with `separators=(",",":")` (no inter-token spaces). **Measured:
  ~8% smaller** JSON payloads (and the smaller text gzips slightly better). No behaviour change.
- **Pre-render page ETag** — the `/page` route computes a cheap **param-based ETag** and checks
  `If-None-Match` **before rendering**: a repeat view returns `304` without opening the PDF, rendering, or
  hashing the image. `_send` now trusts a caller-supplied ETag, so it no longer md5-hashes big PNGs.
  **Verified:** the 304 path returns with the renderer untouched.
- **Precomputed `suggest_terms` table** — `optimize_index.py` builds `suggest_terms(term PRIMARY KEY, freq)`
  (WITHOUT ROWID) from the FTS vocab once. `suggest()` prefers a **prefix lookup** on it over a `GROUP BY`
  of the whole FTS vocab every keystroke, with a small LRU of recent prefixes; it falls back to the vocab
  until the table is built. **Measured: ~46× faster** per keystroke on a synthetic corpus (0.18 ms →
  ~0.00 ms; larger on the real corpus), identical top results.
- **WAL journal mode** — `optimize_index.py` switches the DB to **Write-Ahead Logging**, so server reads no
  longer block on the OCR writer (concurrent readers + one writer). Reversible; local-disk only by design.
  **Verified:** `journal_mode=wal`.
### Invariants
- **Safe & additive (R1/R6):** all server-internal, RPS-safe. `suggest_terms` + WAL are applied by the
  one-time `optimize_index.py` maintenance step (run when OCR is paused), so they never contend with the
  live writer.
### Verified
- Compact JSON byte reduction, the 304-without-render path, the 46× suggest speedup (with matching results
  and an index-only `EXPLAIN`), and `journal_mode=wal` all measured directly. **23/23 pillars** (full module
  imports with all edits) + **21/21 feature** tests still pass; `suggest()` falls back cleanly when
  `suggest_terms` is absent.

## [0.56.0] — 2026-06-02 — Speed & efficiency pass (Tier 1 + Tier 2)
*(Internal optimizations only — no new pages, no new API surface, nothing to learn.)*
### Added / Changed
- **Open-PDF LRU cache** — `render_page_png` re-opened and re-parsed the whole PDF on every page render.
  It now reuses an **LRU of 8 open `fitz.Document` objects** (each with a render lock, since PyMuPDF isn't
  thread-safe). The highlight path still uses a fresh doc (it mutates the page). Big win for paging + loupe.
- **Thread-local DB connections** — `db()` opened a new SQLite connection and re-applied PRAGMAs on every
  request (the dossier alone fires 6+). It now **reuses a per-thread connection**; callers' `.close()` is a
  harmless no-op; it rebuilds if a cached connection goes bad. The relaxed/OCR path still gets a fresh
  connection (no shared locks).
- **Indexed Look-Alike** — `part_differences` matched `UPPER(name)=UPPER(?)` (a full table scan). Now it
  uses `name = ? COLLATE NOCASE` so the new NOCASE indexes apply — `EXPLAIN` shows **MULTI-INDEX OR** across
  `ix_parts_name` + `ix_parts_nomenclature` on real selective data.
- **ETag / 304** — `_send` now emits an `ETag` (md5 of the body, stable across gzip); a matching
  `If-None-Match` returns **304 Not Modified** with an empty body — repeat views of a page image, the JS, or
  JSON skip re-sending bytes.
- **`optimize_index.py` (+ `optimize-index.bat`)** — a one-time, **idempotent** maintenance pass:
  `CREATE INDEX IF NOT EXISTS` for `pages(document_id)` and `parts(name/nomenclature COLLATE NOCASE)`, then
  `ANALYZE`. `EXPLAIN` confirms find-in-manual now **SEARCHes via `ix_pages_document`** instead of scanning
  the biggest table.
### Invariants
- **Safe & additive (R1/R6):** all server-internal; **RPS-safe** (pure Python, ES-agnostic). The two index
  builds are the only DB writes — a one-time maintenance step kept **out of the live server** so they never
  contend with the running OCR (run when OCR is paused; 120 s busy-timeout).
### Verified
- fitz LRU (reuse + evict + close) and the connection wrapper (reuse, Row-factory, rebuild-on-bad,
  relaxed-mode, **5 threads × 20 queries / 0 errors**) tested in isolation. `EXPLAIN QUERY PLAN` confirms
  index use (pages + MULTI-INDEX-OR). ETag/304 confirmed by `curl`. `optimize_index.py` creates 3 indexes +
  ANALYZE and is idempotent. **23/23 pillars** still pass (proving the full module imports with all edits;
  the reuse-`db()` is exercised by them) and **21/21 feature** tests green.

## [0.55.0] — 2026-06-02 — UX consolidation: visual steps, torque, command palette, help
*(Four small additions grouped into one version — deliberately consolidating, not sprawling.)*
### Added
- **Visual steps (`/stepflow`)** — the parsed procedure rendered as a big follow-along **flow**: numbered
  nodes + connectors, WARNING/CAUTION/NOTE banners colour-coded, tools staged on top. The "simple" visual
  for junior mechanics (the detailed list remains the "advanced" view). Serves mission goal D. Client-side
  from `/api/procedure`; print-friendly. Linked from the procedure page.
- **Torque specs — integrated (`torque_specs()` + `/api/torque`)** — parses stated torque values
  (ft-lb / in-lb / N·m, including ranges) from procedure pages, each cited. Surfaced as a **panel inside the
  Part dossier** rather than a new standalone page — integration over sprawl.
- **Command palette (Ctrl+K, everywhere)** — `palette.js` injects a global launcher (loaded once by
  `rps.js`, so it's universal with a single include): jump to any feature, or look up a part/vehicle via
  `/api/suggest`. Tames the ~14-feature nav into one keystroke.
- **Help & guide (`/help`)** — a "what do you want to do?" map of every feature grouped by workshop
  workflow, plus a 30-second first-run tour. The home nav now keeps the essentials and points to Ctrl+K /
  Help for the rest.
### Invariants
- **Consolidating, not building heavy:** no new indexes or scans. Everything **ES5-safe + carries
  `rps.js`** — verified by audit — so the whole core workflow runs identically on modern, lite and legacy
  (down to IE11 via polyfills); only the rich-graphics pages (3-D / Circuit Lab / schematic tilt) remain
  modern-by-design. Modular & additive — each feature is one removable route (R1/R6).
### Verified
- `stepflow.html`, `palette.js`, `help.html`, dossier torque panel all lint clean and are **ES5-safe**
  (0 arrow functions / template literals / let-const). `torque_specs()` regex validated on 5 phrasings.
  `rps.js` added to `threed.html` + `status.html` (parity gap closed). **44/44 tests** (23 pillars + 21
  feature) still green.

## [0.54.0] — 2026-06-02 — Ops / health dashboard
### Added
- **`/ops` + `ops_summary()` + `file_audit()`** — one glance at engine health: runtime **RPS mode**,
  **document & vehicle counts**, **page-cache** size, **snapshot** count, **searchable coverage per
  vehicle** (bars), and the **recent ingest/OCR runs** (from the `runs` table). A **file-integrity audit**
  (`/api/audit`) flags indexed PDFs that are now **missing on disk** (e.g. an unplugged drive). Links to
  the live OCR Status page for the running percentage. Home nav: **📊 Ops**.
### Invariants
- **Read-only & cheap (R1/R6):** `ops_summary()` uses only light queries (no full OCR scan — that stays on
  the Status page); the audit just `os.path.exists`-checks. New `/ops` + 2 routes.
### Verified
- `ops_summary()`/`file_audit()` pass a synthetic test (3 docs / 2 vehicles / 1 run; audit catches 2 of 3
  missing). `ops.html` JS lints clean.

## [0.53.0] — 2026-06-02 — Find in manual (in-document Ctrl+F)
### Added
- **`find_in_doc()` + `/api/findindoc` + a viewer find box** — the in-document **Ctrl+F** the mission
  calls for. Type a term and jump between **every match across the whole open document**: per-page match
  count, snippets, **next/prev** (▲/▼ or Enter / Shift+Enter), with the match page opened and the term
  **highlighted** (reuses the page render `hl=`). **Ctrl+F** focuses the box; the search is **scoped to the
  one document** so it's fast.
### Invariants
- Read-only; resets when a new document opens. Additive to the viewer only (R1/R6).
### Verified
- `find_in_doc()` synthetic test: 3 hits across 2 pages, correctly **doc-scoped** (excludes other docs),
  snippet + counts correct; the find JS block lints clean.

## [0.52.0] — 2026-06-02 — Unified part dossier
### Added
- **The `/dossier` page** — one page per NSN that aggregates **everything we hold** about a part:
  reference data (`/api/reference`), catalog figures (`/api/part`), look-alike variants (`/api/partdiff`),
  the how-to procedure (`/api/procedure`), the schematic (`/api/schematics`) and the 3-D model
  (`/api/threed`) — each deep-linked. Jump-off buttons to the job packet, how-to, look-alike, and Solve-it.
  A single source of truth per part. Home nav: **📋 Part dossier**.
### Invariants
- **Read-only aggregation (R1/R6)** of endpoints that already exist; the manual stays the source of truth.
### Verified
- `dossier.html` JS lints clean; consumes the documented endpoint shapes.

## [0.51.0] — 2026-06-02 — Printable job packet (take-to-the-bay)
### Added
- **The `/packet` page** — turns a part + its procedure into a **print-optimised job sheet** a mechanic
  takes to the bay: the steps + tools + cautions, plus a **parts-to-order table** (NSN · UOC · CAGEC with
  check-boxes) and fillable bumper/vehicle/mechanic/WO fields. One **Print / Save-as-PDF** button; a print
  stylesheet hides the chrome. Built from `/api/procedure` + `/api/partdiff`. Linked from the procedure
  page and the Solve-it hub.
- **`engine/tests/test_features.py`** — a 21-test regression suite (procedure parser, `procedure_for`,
  `suggest`, `part_differences`, `ingest_preview`, RPS mode) over a synthetic index; all pass, alongside
  the 23 pillars.
### Invariants
- **Dependency-free** (browser print, no server PDF libs); read-only; the packet says to verify torque /
  sequence / cautions on the cited sheet (R1/R6). New `/packet` route only.
### Verified
- `packet.html` JS lints clean; `test_features.py` 21/21 + `test_pillars.py` 23/23 pass.

## [0.50.0] — 2026-06-02 — Add documents: index new TMs without the command line
### Added
- **The `/ingest` page + `ingest_preview()` / `ingest_start()` / `ingest_status()`** — point THE VIEWER at
  a folder of PDFs on the machine and it indexes the **new** ones, no command line (the mission's "any
  additional files added without a sweat" goal). **Preview** (read-only) reports total PDFs, how many are
  already indexed, and how many are new (with sample names); **Index now** takes a **safeguard snapshot**,
  then runs the tested `viewer_ingest.py crawl` in the background; **live progress** is read from the
  `runs` table (files seen · docs added · text pages · OCR queued) and polled every 2 s. Reachable from the
  home nav (**➕ Add documents**).
### Invariants
- **Additive & safe (R1/R6):** the crawl only **adds** documents + extracted text — it never deletes or
  overwrites the corpus or index; a snapshot is taken before any write (rollbackable); already-indexed
  files are skipped (dedup by path + fingerprint) and the crawl is resumable. The preview writes nothing.
  Reuses the proven ingest pipeline — no new unverified write code. New `/ingest` + 3 routes only.
- After adding, scanned pages are queued for OCR — run the GPU OCR to make them searchable.
### Verified
- `ingest_preview()` validated on a synthetic folder: 4 PDFs across sub-folders, 1 already indexed → 3 new;
  bad path rejected; `ingest_status()` idle when nothing is running. `ingest.html` JS and the server
  functions lint/compile clean.

## [0.49.0] — 2026-06-02 — Type-ahead predictive search (offline)
### Added
- **`suggest()` + `/api/suggest` + a search-box dropdown** — google-style suggestions as you type, fully
  offline (so it's instant). Sources, prefix-matched and ranked: **vehicles** (distinct, cached 5 min),
  **part names** previously requested, and **real manual words** from the FTS vocab table (`pages_vocab`,
  ranked by frequency). Deduped, 8 shown.
- **The dropdown** is debounced (120 ms), keyboard-navigable (↑/↓ to move, Enter to pick, Esc to close),
  closes on blur / outside click, and is screen-reader labelled (`role=combobox`/`listbox`). Picking a
  suggestion fills the box and runs the search.
### Invariants
- **Read-only & additive (R1/R6):** queries existing indexes only (the FTS vocab + distinct vehicles +
  request history) — no scan, no writes, no network. New `/api/suggest` route only; rollback = remove it
  and the dropdown.
### Verified
- `suggest()` validated on a synthetic FTS5-vocab database: `alt`→ALTERNATOR ASSEMBLY (part)+alternator
  (term), `hmmwv`→vehicle, `engin`→term; ranking vehicles → parts → words confirmed. The type-ahead block
  and server function lint/compile clean (`node --check` / `compile`).

## [0.48.0] — 2026-06-02 — Solve it: the workflow hub
### Added
- **The `/solve` workflow hub** — one screen that walks from a **symptom to a fix**: enter a problem
  ("no-start, not charging") or a part, and it stitches together (1) **likely parts** for the fault
  (`/api/faultparts`) + the **manual pages** that mention it (`/api/search`), then on a chosen part
  (2) the **how-to procedure** (steps, tools, cautions — `/api/procedure`), the **look-alike check**
  (`/api/partdiff` — "don't order the wrong NSN, the UOC is the tell"), and the **related schematic**
  (`/api/schematics`, openable in the viewer / Circuit Lab). Reachable from the home nav (**🛠 Solve it**).
### Invariants
- **Additive & grounded (R1/R6):** pure client-side orchestration of endpoints that are already tested —
  no new index work, nothing written back. Every panel deep-links to the real cited page; the UI reminds
  the mechanic to confirm torque, sequence and the exact NSN (UOC) on the sheet. New `/solve` route only.
- Benefits from **keep-alive (0.46)** — the multi-call orchestration reuses one connection.
### Verified
- `solve.html` JS lints clean (`node --check`); it consumes the documented response shapes
  (`/api/search` → `{results}`, `/api/faultparts` → `{parts}`, `/api/procedure` → `{procedures}`,
  `/api/partdiff` → `{variants,discriminators}`, `/api/schematics` → `{items}`).

## [0.47.0] — 2026-06-02 — How to do it: the procedure view
### Added
- **`procedure_for()` + `/api/procedure` + the `/procedure` page** — surfaces the **step-by-step
  instructional rundown** for a part (the mission's "complete instructional rundown" gap). Given a part
  name or NSN it FTS-matches the manual pages that describe the part *and* a procedure word
  (removal / installation / remove / install / disassembly / assembly / replace / adjustment / service),
  then **parses each page** into: the **section kind**, the **numbered steps** (in order), the
  **TOOLS REQUIRED** block, and the **WARNING / CAUTION / NOTE / DANGER** callouts.
- **The UI** shows kind-tagged cards (Removal/Installation/… colour-coded), tools as chips you can stage,
  safety callouts colour-coded so they can't be missed, the numbered steps, and a one-click link to the
  **real cited page**. Reachable from the home nav (**🔧 How to do it**).
### Invariants
- **Read-only & grounded (R1/R6):** the `procedures` table shipped empty, so this parses procedures from
  the page **text** at query time — nothing invented, nothing written back to the index. Every card cites
  the real page and the UI tells the mechanic to verify torque/sequence/cautions on the sheet. It's a fast
  on-ramp to the page, not a replacement. New routes only.
- **Improves with OCR:** scanned procedure pages become searchable (and thus parseable) as the scan
  completes.
### Verified
- `_parse_procedure()` validated on a representative work-package page: `kind=Removal`, numbered steps,
  TOOLS-REQUIRED list, and WARNING/CAUTION/NOTE callouts all extracted; tightened so a group title like
  "ENGINE ASSEMBLY" doesn't get mislabelled as the kind. FTS query mirrors the proven `search()` path;
  `procedure.html` JS and the server functions lint/compile clean.

## [0.46.0] — 2026-06-02 — Faster transport (gzip + keep-alive) + a Performance toggle in Settings
### Added
- **gzip + HTTP/1.1 keep-alive** in the server (`_send`): the TCP connection is reused across requests,
  and text-ish responses (**JSON / HTML / JS / SVG**) are gzip-compressed when the browser advertises it.
  Skips payloads under 512 B (compression overhead) and already-compressed **PNG / PDF**, and sets
  `Vary: Accept-Encoding`. Biggest win for the large home page and JSON results on a slow link or old box;
  zero UI change.
- **Performance (RPS) toggle in ⚙ Settings:** **Auto / Modern / Lite / Legacy**, saved per-browser
  (`localStorage 'rps.mode'`). `rps.js` reads it and re-applies live (no reload) — asking `/api/rps?mode=…`
  for that mode's flags and toggling lite-effects + default DPI. A live status line explains the active
  mode. `RPS.setMode()` / `RPS.getOverride()` exposed.
### Invariants
- **Additive & safe (R1/R6):** gzip/keep-alive are pure transport; the UI toggle is presentation/perf only.
  Critically, the **server's** mode (SQLite tuning + page cache) stays **auto-picked from the real
  hardware** — a UI choice can't mis-tune the database. Force the whole server at launch with
  `viewer_app.py --mode legacy` (or `?mode=` in the URL) when you want server-side too.
- **RPS (R7):** both finishers benefit the legacy track (smaller transfers on slow connections; one-tap
  Legacy mode) — recorded as `0.46.0-legacy`, full parity.
### Verified
- gzip/keep-alive validated with `curl`: 2 KB JSON → 45 B gzipped (`Content-Encoding: gzip`), two requests
  served on one connection (keep-alive), <512 B JSON and `image/png` left uncompressed, no-`Accept-Encoding`
  → full body. `rps.js` toggle block and `index.html` inline JS lint clean (`node --check`).

## [0.45.0] — 2026-06-02 — Retroactive Post-Support (RPS): comparable speed on older/slower PCs
### Added
- **`engine/rps.py` — the RPS runtime layer.** Picks a mode (**modern / lite / legacy**) from the
  hardware probe (`sysprobe.py`), overridable via `--mode` or `?mode=`. `mode_for()`, `feature_flags()`,
  and the page-cache helpers are pure logic (**13/13 unit tests**).
- **Page-render disk cache** (`index/pagecache/`): a full-page PNG is rendered once then served from
  disk — the biggest win on a slow HDD. **Pre-bake** hot pages with `viewer_app.py --prebake N`, and
  **warm-on-view** renders the next page(s) in a background thread. Loupe/highlight renders bypass it.
- **Per-mode SQLite tuning** on every connection (big `mmap` + MEMORY temp on modern; tiny cache,
  `mmap=0`, FILE temp on legacy/low-RAM) — connection-local PRAGMAs only, the index is never rewritten.
- **`engine/ui/rps.js`** — feature-detected **ES5 polyfills** (fetch, Promise, Object.assign, Array/String
  helpers, URLSearchParams) so the modern UI runs on old Firefox ESR / IE11, plus a **lite-effects**
  bootstrap (adds `body.rps-lite/legacy`, disables animations/transitions, keeps the loupe local). Loaded
  by the home, schematics, and Look-Alike pages; no-ops on modern browsers.
- **New endpoints:** `/api/rps` (mode + flags + page-cache stats) and `/rps.js`. Render DPI is capped per
  mode (400 / 220 / 150).
### Invariants
- **COMPLETE compatibility, not a cut-down build (R1/R6):** RPS keeps the full feature set working back to
  Win7/Vista by **engine substitution + adaptation** — it changes *how* things run, never *what* the
  manual says. Everything is additive and read-only (the cache is a regenerable sidecar; PRAGMAs are
  connection-local; polyfills are client-side). Rollback = delete `index/pagecache/` and ignore `rps.py`.
- **RPS (R7):** this is the modern-side infrastructure that powers the legacy track; see `0.45.0-legacy`.
### Verified
- `rps.py`: **13/13** unit tests — mode decision (Nitro 5→modern, Win7/Poppler→legacy, 6 GB→lite, override
  wins / bad-override ignored), feature flags, cache keys distinct by dpi/flags, cache read/write
  round-trip, prebake renders then skips already-cached. Server-side cache/tuning/warm blocks compile and
  run; `rps.js` lints clean (`node --check`).

## [0.44.0] — 2026-06-02 — Circuit Lab, deepened: active devices + save/load/export + part links
### Added
- **Four new active devices in the MNA engine** (`circuitsim.js`), each unit-tested: **AC source**
  (time-varying `A·sin(2πft)` — real transient/ringing demos), **N-channel MOSFET** (square-law level-1,
  Newton-solved — switches & amplifies), **ideal op-amp** (high-gain VCVS — non-inverting ×2 = 2.000 V),
  and a **behavioral relay** (coil + contact; energizing the coil closes the contact). Engine now passes
  **10/10 unit tests** (the original 6 + these 4).
- **Generalised N-pin editor model:** components carry a pin-offset table instead of fixed 2 leads, so
  **3-pin (MOSFET, op-amp)** and **4-pin (relay)** devices place, rotate, and wire correctly; union-find
  node assignment and `netlist()` emit each device in the engine's pin order.
- **Save / load / export:** 💾 Save & 📂 Load (browser `localStorage`), ⬇ download/⬆ import as
  `.circuit.json`, and ⬇ **SPICE-style netlist** (`.cir`).
- **Parts link to the catalog:** tag any component with a **TM part # / NSN**; it shows on the symbol and
  is a one-click jump to the **Look-Alike Parts** recognizer (`/partdiff`).
- **8 demo circuits** now (added AC+RC, MOSFET switch, relay-driven lamp, op-amp ×2).
### Invariants
- **Grounded & additive (R1/R6):** same validated MNA core; the simulator never rewrites the TM and the
  cited sheet stays behind the overlay; save/export are local files. Same routes — a richer editor.
- **RPS (R7):** still a modern-browser feature; the Win7/Vista legacy build keeps the static-overlay
  fallback (`0.44.0-legacy`).
### Verified
- Engine: **10/10** unit tests pass (divider 2.5 V, RC τ, diode 0.574 V, RLC overshoot, AC peak 10 V,
  MOSFET on→0.017 V / off→5 V, op-amp ×2 = 2.000 V, relay energize→lamp 5 V / de-energize→0 V).
- Editor logic replayed in Node for the new multi-pin samples: MOSFET drain pulls LOW, relay contact
  closes to power the lamp, op-amp out = 2.000 V. `circuitlab.html` inline JS lints clean (`node --check`).

## [0.43.0] — 2026-06-02 — Look-Alike Parts recognizer
### Added
- **`part_differences()` + `/api/partdiff` + the `/partdiff` page** — a recognizer for parts that
  **look identical in the manual but are functionally different**. Given an NSN or a part name it finds
  every catalogued part sharing that name, collapses them to distinct stock numbers, and reports the
  **discriminators** that set them apart: **NSN, FSC (supply class), UOC (Usable-On-Code), CAGEC
  (manufacturer), SMR, and part number**.
- **Four colour-coded verdicts** per variant: `reference` (what you searched), `different variant`
  (same name, different NSN — usually a different vehicle configuration; **the UOC is the tell** — the
  dangerous look-alike), `same item (format drift)` (same NIIN, just a different NSN format —
  interchangeable), and `different item class` (different FSC — merely shares a figure title, **not a
  substitute**).
- **Grounded "how to tell apart" cues** and **cited figure/page links** on every variant, plus
  cross-platform interchangeability pulled from the optional correlations sidecar. Reachable from the home
  nav and the Schematics header (**🔍 Look-Alike Parts**).
### Invariants
- **Read-only & additive (R1/R6):** queries the existing parts index + the optional correlations sidecar;
  invents no data and writes nothing to the index. Every comparison cites the real figure so the mechanic
  confirms on the sheet; confirmed-same items and interchangeable NSNs are labelled as substitutes, not
  differences. The previously-empty `part_variants` table is now meaningfully populated on demand at query
  time. New routes only; rollback = remove `/partdiff` + `/api/partdiff`.
- **Improves with OCR:** as coverage climbs, item names sharpen and the look-alike groups get finer.
### Verified
- `part_differences()` logic validated end-to-end on a synthetic dataset mirroring the real schema:
  correctly grouped distinct NSNs under a shared name, surfaced the discriminators (NSN/FSC/UOC/CAGEC/SMR),
  flagged the UOC-distinguished look-alike as `different variant`, and classified a different-FSC item as
  `different item class` (not a substitute). `partdiff.html` is self-contained; `viewer_app.py` compiles.

## [0.42.0] — 2026-06-02 — Circuit Lab: overlay editor + real-time circuit simulator
### Added
- **`engine/ui/circuitsim.js` — a dependency-free analog circuit engine (Modified Nodal Analysis).**
  No SPICE, no library, fully offline. Assembles `G·v = i` from a netlist, **backward-Euler companion
  models** for capacitors/inductors, **Newton–Raphson with SPICE-style voltage limiting (pnjlim)** for
  diodes/LEDs so series junctions converge, Gaussian elimination with partial pivoting. Runs both as a
  **browser global** (`window.CircuitSim`) and as a **Node module** (how it's unit-tested). Served at
  `/circuitsim.js`.
- **`engine/ui/circuitlab.html` — the Circuit Lab** (`/circuitlab`): a **schematic-overlay editor + live
  simulator** and learning/advanced-display tool. Snap-grid canvas; place **Source / R / C / L / Diode /
  LED / Switch / Ground**; **draw wires** pin-to-pin; **tune values** with log sliders. Press **▶ Run** for
  an animated transient, **DC** for the operating point, or **Step**. Live feedback: **node colours by
  voltage**, **current as moving dots**, a **per-node scope**, an **Analog⇄Logic (HIGH/LOW)** view, and a
  lit LED. Ships with **6 demo circuits** (divider, RC, RLC, rectifier, switch→lamp, logic).
- **Overlay on a real TM schematic:** open any sheet from the `/schematics` viewer with the new
  **⚡ Circuit Lab** button (passes `?doc=&page=`), or paste a `/page?doc=…&page=…` URL — the real rendered
  sheet sits behind the grid at a dialable opacity so you can **build or trace a circuit on top of it**.
- Header links to **⚡ Circuit Lab** added to the Schematics Library.
### Invariants
- **Grounded & additive (R1/R6):** the circuit is grounded in what *you* build or trace — the simulator
  never rewrites the TM, and the cited sheet stays visible behind the overlay. Auto-extracting a netlist
  from a raster TM is **deliberately deferred** to the desktop/RTX 5070 and would be labelled
  "auto-extracted — verify against the TM." New routes only; nothing existing changed; rollback = remove
  the two routes + link buttons.
- **RPS (R7):** the live sim is a modern-browser feature (effortless on the 4050). On the Win7/Vista
  legacy build it degrades gracefully to **static-overlay only (no live sim)** — the editor still draws and
  the schematic still opens. Logged on the modern track here; the legacy track records the degraded form.
### Verified
- **MNA engine — all unit tests pass (Node):** voltage divider 2.500 V (exact), Ohm's law 5.00 mA (exact),
  RC at t=τ 3.159 V (<1% vs 3.161), diode 0.574 V at 4.4 mA (exact for Is=1e-12), **series diode+LED 3.34 mA**
  (converges via pnjlim — the prior hard-clamp model stalled near 0), underdamped RLC overshoots then
  settles to 5 V. Editor graph logic (union-find → netlist) replayed in Node for the divider/RC/rectifier
  samples and matches. `circuitlab.html` inline JS and `circuitsim.js` lint clean (`node --check`).

## [0.41.0] — 2026-06-02 — Schematics: explore from every angle + related-sheets rail
### Added
- **Tilt to any angle + mirror** in the dedicated `/schematics` viewer: tilt X and tilt Y sliders
  (−70°…+70°, CSS perspective) let you examine a sheet from the **left, right, above, below, and every
  angle in between**, and a **↔ Mirror** flips to the back side. Composes with pan/zoom (one transform).
- **Related-sheets rail:** a filmstrip of the **same vehicle's other schematic / wiring sheets**
  (left-side, right-side, power, lighting…), each a page-1 thumbnail — one click to switch, so the whole
  system's views are reachable without leaving the viewer. (`/api/schematics?q=<vehicle>`.)
- **⟲ Reset** now clears zoom, pan, tilt, and mirror together; ←/→ still page through.
### Invariants
- Grounded & presentation-only (R1/R6): the tilt is an honest flat-sheet rotation, the mirror is a flip,
  and the rendered page is never altered. A 2D schematic has no true hidden 3D, so none is fabricated —
  you explore the real sheet and its real companions fully.
### Verified
- Schematics viewer JS (tilt/mirror/rail/reset) lints clean (node --check); rail queries
  `/api/schematics` (1,093 docs) by vehicle.

## [0.40.0] — 2026-06-02 — Make it pop: real-time WebGL 3D + dynamic schematics (current-specs)
### Added
- **`engine/ui/gl3d.js` — a dependency-free WebGL 3D renderer** (no Three.js, no CDN → fully offline).
  It draws the FLIS-scaled shapes lit in real 3D with **glossy multi-light shading** (key + fill +
  rim/fresnel + sharp specular + soft tonemap), **antialiasing**, **smooth normals for round families**
  (cylinders look round, boxes stay crisp), and an **idle turntable** that gently auto-spins and pauses
  when you grab it. Orbit (drag), zoom (wheel), reset (dbl-click). Served at `/gl3d.js`; the **3D Library**
  uses it with the SVG renderer as a fallback (WebGL missing → Win7/Vista / RPS still works).
- **Dynamic schematics viewer:** **buttery pan** (drag) + **cursor-centered wheel zoom** (transform-
  origin follows the pointer, no reload), a one-tap **🟦 Blueprint mode** (white-lines-on-blue), **fade
  page transitions**, plus the existing 🧹 Clean; ⟲ Reset clears zoom+pan, ←/→ page through.
### Invariants
- Presentation-only and grounded (R1/R6): the 3D is the same parametric geometry from real FLIS
  dimensions (lit, not invented); the schematic is the same real rendered page (themed/navigated, not
  altered). Offline-first — the WebGL renderer is ~120 lines we own.
### Verified
- `gl3d.js` and the schematics viewer JS lint clean (node --check); smooth/flat normals, turntable, and
  cursor-zoom math reviewed. Interactive demos shown.
### Next (proposal 55)
- On the 4050: parametric template library (thread helix / gear teeth), schematic vectorisation +
  per-wire hover. Photogrammetry + schematic net-extraction await the desktop/RTX 5070 (reminder set).

## [0.39.0] — 2026-06-02 — 3D Library + Schematics Library + Reset on every moveable view
### Added
- **Reset buttons (the missing control).** Every moveable/interactive view now has a clearly-labelled
  reset: the schematic page viewer's **⟲ Reset** clears tilt X/Y, zoom, and mirror (and resets the
  sliders/buttons); the representative 3D viewer gets **⟲ Reset + double-click**. Prompted by demoing
  tilt with no way back to default.
- **🧊 3D Library (`/3d`, `/api/threed`).** A dedicated, searchable, paginated gallery of **all 20,869
  parts** with enough FLIS dimensions to render a representative 3D shape. Each card is a live mini 3D
  thumbnail; click to drag-rotate / scroll-zoom / reset. Self-contained renderer (family shape +
  material/colour tint + depth shading); grounded — not a CAD model.
- **📐 Schematics Library (`/schematics`, `/api/schematics`).** A gallery of **all 1,093 schematic /
  wiring-diagram documents**, searchable by vehicle / TM / title / NSN, with a rendered page-1
  thumbnail. Click opens a **built-in page viewer** (prev/next + arrow keys, 🧹 clean, zoom ±, ⟲ reset),
  rendering pages on demand via `/page`. (Exploded-view RPSTL figures remain in the vehicle hub.)
- Both libraries are linked from the home header (alongside 📊 Status).
### Invariants
- All additive and presentation-only (R1/R6): new read-only endpoints + standalone pages; the dataset,
  search, and 104th sheet are untouched.
### Verified
- `/api/threed` (20,869) and `/api/schematics` (1,093) counts confirmed on the live index; threed.html,
  schematics.html, and the reset JS all lint clean (node --check).

## [0.38.0] — 2026-06-02 — Dual-track changelog scaffolding (legacy track, rule R7)
### Added
- **Rule R7 — dual-track changelog.** Legacy (Retroactive Post-Support) builds get their own changelog
  that **branches at the version it was created** and shows backports against the modern track.
  Scaffolding built now (per the user's call):
  - **`docs/CHANGELOG-LEGACY.md`** — starts at **`0.37.0-legacy`** (the complete-compat branch point),
    versioned `<modern-base>-legacy`, with a **parity line** per entry (✓ same · ~ adapted · – N/A GPU).
  - **`docs/diagrams/_make_changelog_dualtrack.py`** → **`CHANGELOG-DUALTRACK.pdf`**, a data-driven
    **branched timeline** (modern lane + legacy lane forking at 0.37.0 + dashed backport links). Extend
    by adding to `MODERN` / `LEGACY` / `BACKPORTS` and re-running.
- Concept mockup: `docs/diagrams/53-dualtrack-changelog-mockup.pdf` (the approved format).
### Notes
- The legacy track fills in as the Retroactive Post-Support build lands (ES5 UI, page cache, lite mode,
  SQLite tuning) — targeted `0.38.0-legacy`. Modern history stays in this file.
### Verified
- Branched-timeline generator renders; `CHANGELOG-LEGACY.md` branch-point entry written with parity tags.

## [0.37.0] — 2026-06-02 — COMPLETE backward compatibility: Windows 11 → Vista
### Changed (corrects 0.36.0's framing)
- Reframed from "incomplete/best-effort" to **complete feature compatibility from Windows 11 down to
  Windows 7 and Vista**. Every user-facing feature — search, vehicle hub, document viewer, 104th sheet,
  and OCR — works on all of them; the engine **substitutes the right tool per OS** rather than dropping
  features.
### Added
- **Poppler render fallback** in `viewer_app.py`: when PyMuPDF can't be installed (legacy OS), the
  viewer renders pages via Poppler's `pdftoppm`/`pdftocairo`. Core viewing works without PyMuPDF.
- **`sysprobe.py` now reports engines + compatibility:** detects PyMuPDF/Poppler and RapidOCR/Tesseract,
  sets `render_backend` (pymupdf|poppler) and `ocr_backend` (gpu-rapidocr|cpu-rapidocr|tesseract), marks
  every core feature available on all OSes, and gives precise legacy-toolchain guidance (Python 3.8 for
  Win7 / 3.4 + portable index for Vista; install Poppler + Tesseract).
### Honest scope
- The **only** Win10+ exclusive is **NVIDIA GPU acceleration** (CUDA/onnxruntime don't exist for
  Vista/7) — a *speed booster, not a feature*. OCR still completes on Vista/7 via Tesseract and the
  searchable index is identical. Nothing a user can do is missing on the older OSes.
### Verified
- `sysprobe.py` parses and (simulated legacy Win7: no PyMuPDF, Poppler+Tesseract present) reports
  render_backend=poppler, ocr_backend=tesseract, all core features available. Viewer Poppler fallback +
  `_clean_png` apply; `pdftoppm`/`pdftocairo` auto-selected.

## [0.36.0] — 2026-06-02 — Hardware probe + autonomous adaptive GPU OCR (Win11-first, back to Win7)
### Added
- **Capability probe** (`engine\sysprobe.py`): detects OS+build (Windows 7→11), Python, CPU cores, RAM,
  NVIDIA GPU/CUDA, free disk, and **laptop/battery**, then writes `index\hardware_profile.json` with a
  resource profile (tier, `use_gpu`, `ocr_workers`, `ocr_dpi`, `hd_render_cap`, feature availability).
  Launchers read it via `sysprobe.py --get KEY`. **Win11-first with best-effort/incomplete backward
  support to Win7** — GPU OCR on Win10+; older OS / weaker PCs get a scaled-down CPU profile; gaming
  laptops (e.g. **Acer Nitro 5**) get GPU OCR with **thermal headroom** (fewer feeder workers) and a
  plug-in/ventilate note; on battery, workers throttle. **Strong discrete GPUs** (RTX / ≥4 GB VRAM) raise
  the worker ceiling since the GPU is the bottleneck; a **`/max` full-throughput mode** uses most cores.
  Tuned to the user's confirmed **RTX 4050 Laptop (6 GB) + Intel Alder Lake**: 8 workers @ 220 dpi
  default, **12 @ 240 dpi with `run_ocr_auto.bat /max`**, throttled to 3 on battery (all verified by
  simulation).
- **Autonomous adaptive OCR runner** (`engine\run_ocr_auto.bat`): probes → installs the right stack
  (onnxruntime-gpu + RapidOCR **PP-OCRv5**, with PP-OCRv4 fallback) → `gpu_check` → snapshot → runs
  `ocrall` in a **self-restarting loop to 100%** (auto-resumes if a pass crashes) → writes & opens a
  **detailed report**. `/auto` registers a logon task to resume after reboots (safe no-op once 100%).
- **PP-OCRv5 engine path** in `viewer_ingest.py` (≈13 pts more accurate than v4), preferred when the
  modern `rapidocr` package is present and **guarded by a self-test** that auto-falls back to the proven
  PP-OCRv4 if the newer API differs — never silently breaks extraction. Clear provider (GPU/CPU) logging.
- **`engine\ocr_report.py`** — detailed completion report (progress, coverage, per-vehicle table, sample
  recovered NSNs, failures, engine/provider); `--full` for a thorough per-vehicle coverage scan. Plus
  `engine\gpu_check.py` (GPU readiness verdict) and `engine\ocr_pending.py` (loop helper).
### Honest scope
- The OCR **compute runs on the user's GPU** — the assistant has no GPU and can't run a multi-day job.
  This makes that run the fastest, most accurate, and most autonomous it can be, and reports when done.
### Verified
- Probe runs and emits a correct profile + `--get` values (sandbox: legacy/CPU tier); the v4/v5 adapter
  + self-test were validated against real RapidOCR (extracted `BOLT 5305-01-674` cleanly); report queries
  fast in quick mode on the live index; `ocr_pending` reads 119,239. Researched engines:
  RapidOCR/PP-OCRv5 chosen for best speed+accuracy.

## [0.35.0] — 2026-06-02 — Page zoom: slider + scroll-to-cursor
### Added
- **Zoom slider** (100%–400%) in the viewer toolbar, alongside the tilt X/Y sliders — slide the
  schematic closer; scales about the page centre with a smooth `.1s` ease. The % readout combines the
  render DPI and the slider so it always reads true.
- **Scroll-to-zoom toward the cursor** when the **loupe is off**: hover a spot and scroll to zoom in/out
  centered on that point (transform-origin follows the pointer). **Double-click resets to fit.** When the
  loupe is on, the wheel still drives the loupe — no conflict.
- Zoom is one more term in the viewer's CSS transform, so it **composes cleanly with tilt and mirror**
  and stays GPU-smooth; the stage scrolls (`overflow:auto`) to pan a zoomed page, and HD + the loupe
  keep fine detail crisp. Zoom **resets per page**.
### Invariants
- Presentation-only and reversible (R1/R6): page data, the index, search, and the 104th sheet are
  untouched.
### Verified
- Viewer zoom JS lints clean (slider + cursor-centered wheel + dbl-click reset, integrated into
  `applyTilt`).

## [0.34.0] — 2026-06-02 — Tight, seamless loupe + cohesive accessibility controls
### Changed
- **Loupe responsiveness reworked.** The magnifier now tracks the cursor with **zero latency**: an
  instant local CSS magnification follows every frame via `requestAnimationFrame`, and the high-DPI
  server crop (`/page?clip=…`) **sharpens in only when you pause** (60 ms debounce) — no lag, no blank
  frames, no jumpiness. Crops are **cached** by region+zoom so revisiting a spot is instant, the **mouse
  wheel changes magnification** (1.8×–6× live), and the pointer hides so the loupe *is* the cursor.
- **Cohesive control feel.** All viewer toggles (Clean, contrast, tilt Y/X, Mirror, HD, Loupe) share one
  responsive style: accent border + subtle glow when active, smooth `.12s` transitions, and press
  feedback. They compose cleanly (the loupe reflects Clean/contrast; HD raises full-page DPI; tilt/mirror
  are CSS overlays).
### Invariants
- Presentation-only and reversible (R1/R6): nothing here touches the page data, index, search, or 104th
  sheet. The loupe shows the same real drawing re-rasterised sharper — nothing invented.
### Verified
- Viewer loupe JS lints clean (rAF + debounce + cache + wheel). Active-state CSS added for `.ghost.on`.

## [0.33.0] — 2026-06-02 — Interchangeable-NSN alias map in search + GPU readiness + queue prioritized
### Added
- **Confirmed-interchangeable alias map.** When you mark a NIIN-drift group **interchangeable** on the
  status page, search now treats those NSNs as equivalents: a full-NSN lookup expands its FTS phrase to
  `"…" OR "…"` over the confirmed-equivalent NSNs (and an optional canonical), and the cover-NSN match
  covers all of them. `nsn_aliases(nsn)` reads the append-only `reviews.db` decision + the correlations
  variants. Grounded: aliases come **only** from your confirmed decisions — never auto-merged; no
  decision means search is unchanged. Reversible (latest decision wins; delete `reviews.db` to undo).
  Results carry an `aliases` list so the UI can show why an equivalent surfaced.
- **`engine/gpu_check.py`** — one-command GPU readiness verdict (driver, onnxruntime providers, RapidOCR)
  printing **GPU READY ✓** or **CPU ONLY** with the exact fix. Linked from `docs/SETUP-GPU.md`.
### Done (live index)
- **Prioritized the OCR queue and recovered stuck pages** on `viewer.db`: requeued the **275** pages
  stuck in `running`, and refreshed priorities so **parts catalogs (25,516) come first**, then
  troubleshooting (373), maintenance (26,504), operator (7,606), rest (59,240). OCR is **1.6%** done
  (1,896 / 121,135 scanned pages); **93.5%** of all pages already searchable. The run itself is GPU time
  on the user's box (`run_ocr_gpu.bat`, resumable).
### Verified
- 23/23 pillar tests pass (added `nsn_aliases` + alias-expansion search tests); decision-driven aliasing
  is grounded and reversible; `gpu_check.py` runs (correctly reports CPU-only in a no-GPU environment).

## [0.32.0] — 2026-06-02 — NIIN-review confirm/reject workflow + OCR run guide
### Added
- **NIIN-drift review workflow (actionable).** The 884 drift groups are now a working queue on the
  status page: each can be marked **distinct / interchangeable / error / dismiss** (with optional
  canonical NSN + note). Decisions persist to a new **append-only** sidecar `index/reviews.db`
  (`/api/niin_review_decision`, POST) — inserts only, latest-per-NIIN wins, full history retained for
  audit (R6). `niin_review` now returns each group's latest decision plus **decided/pending counts**,
  with a pending-only filter. The main index is never auto-changed (R1) — decisions are curation, not
  edits.
- **OCR run guide** (`docs/OCR-RUN-GUIDE.md`): preflight checklist, step-by-step `run_ocr_gpu.bat` run,
  how to watch progress on `/status`, a rough time estimate (GPU hours vs CPU days), troubleshooting,
  and the honest note that the ~119k-page run is compute time on the user's machine (resumable; OCR is
  append-only so it's outside any rollback).
### Verified
- Decision roundtrip tested standalone: input validation (9-digit NIIN + known decision), append-only
  history retained, latest-wins. status.html review JS lints clean. No change to existing pillar/
  truncation suites (21/21, 11/11 still green).

## [0.31.0] — 2026-06-02 — System Status page, automatic snapshots, OCR finishing, recall/curation features
### Added
- **System Status page** (`/status`, `/api/status`). One-glance health: document/page/parts/NSN counts,
  searchable coverage %, OCR progress, last snapshot, correlations summary, the NIIN-drift review queue,
  and a fault→parts lookup. Uses indexed columns only, so it stays fast on the 3.6 GB index (the slow
  `source='ocr'` scan is avoided; OCR progress comes from the indexed `ocr_status`).
- **Automatic snapshots.** `register_snapshot_task.bat` registers a daily Windows Scheduled Task
  (snapshot + verify at 06:00). A **snapshot-before** hook was added to `run_ocr_gpu.bat` (`pre-ocr`) and
  `run_enrich.bat` (`pre-enrich`) so a restore point is taken before any data-mutating run. Runs on
  Windows (correct reads); additive (R6); main index never modified (R1).
- **OCR finishing.** The existing `ocrall` already prioritizes then loops to `pending=0` (resumable);
  it now snapshots first and surfaces live progress on the status page. 118,964 scanned pages remain
  (~6.5%); the run executes on the user's GPU via `run_ocr_gpu.bat`.
- **Suggestions developed:** (1) **nomenclature normalization** — `BOLT, MACHINE`↔`machine bolt` and
  abbreviation expansion (`gskt→gasket`), used to widen keyword recall only when a query is sparse
  (additive); (2) **fault→parts** (`/api/faultparts`) — parts most requested for similar faults, from
  the logged history; (3) **NIIN-drift review queue** (`/api/niin_review`) — 884 groups with FSC-conflict
  flags surfaced for review.
### Honest gaps
- **Tool-list roll-up deferred** — the `procedures.tools_required` data is empty; it needs structured
  extraction (OCR-gated), so it isn't built yet. Fault→parts grows as requests are logged.
### Verified
- 21/21 pillar tests pass (added nomenclature helper + recall-widening tests); 11/11 truncation tests;
  status/niin/fault endpoint logic checked on the live DBs (coverage 93.5%, 884 drift groups, top NIIN
  carries 3 FSCs). status.html JS lints clean.

## [0.30.0] — 2026-06-02 — Schematic orientation: dual-axis tilt, mirror with readable labels, on-demand HD
### Added
- **Dual-axis tilt.** The viewer now tilts the page on **both axes** — tilt Y (left/right) and tilt X
  (up/down), −60°…+60° each, via CSS `perspective` + `rotateX/rotateY`. Honest flat-sheet rotation, not
  reconstructed depth.
- **Mirror (↔) with readable labels.** A horizontal flip to orient from the opposite side of the
  vehicle. On pages with a text layer, each word box (new `/api/pagewords`, from PyMuPDF
  `get_text('words')`, normalized) is **re-drawn un-mirrored at its mirrored position** so labels stay
  readable while the drawing is flipped. Honest: a mirror is an orientation aid, **not** a true rear
  view (that needs a different figure); image-only pages show no overlay until OCR provides boxes.
- **On-demand HD (✦).** Renders the full page from the lossless source at up to **400 DPI** (raised from
  300) when toggled — full fidelity with no pre-baked duplicate files (which would explode storage on
  the 85 GB corpus for no quality gain). The loupe still goes to 700 DPI on the cursor region.
### Invariants (R1 · R6)
- All four controls are presentation-only and reversible: page bytes, the index, FTS search, and 104th
  sheet generation are untouched. Mirror labels are read-only overlays; HD changes only resolution.
### Verified
- `/api/pagewords` returns normalized word boxes on a real corpus page (mirror maps x0→1−x1); viewer JS
  (tilt/mirror/labels/HD) lints clean; full-page DPI ceiling raised to 400.

## [0.29.0] — 2026-06-02 — Data protection: integrity safeguard, snapshot vault, recovery + hardened tests
### Root cause (the "truncation")
- Reproduced and characterised: the truncation was a **sandbox read-cache artifact** at the host→guest
  boundary (the editor rewrites a file on Windows; the Linux sandbox's page cache serves a stale,
  shorter length until it revalidates). The **Windows file is never damaged** — proven because an edit
  matching the file's last line succeeded. Guest-side writes/reads are always coherent.
### Added
- **`engine/safeguard.py` — integrity + recovery ("the treasure vault").** Atomic writes
  (temp→fsync→`os.replace`), SHA-256-verified **snapshots** into `backups/vault/SNAP_<ts>/`, a
  **verify** that classifies damage (OK / TRUNCATED / CORRUPTED / EMPTY / SHRUNK / MISSING / MODIFIED)
  against the last good snapshot, and **recover** (restore + re-hash). The heavy `viewer.db` gets a
  SQLite `integrity_check` always and a consistent online-backup copy only on demand (`/withdb`).
  Launcher: `engine/run_safeguard.bat`. Additive (R6); the main index is never modified (R1).
- **`engine/tests/test_truncation.py`** — deliberately damages files at light/medium/hard severity
  (last line, 50%, 10 bytes, empty, partial-UTF-8, byte-flip, deleted, multi-file, corrupted vault
  relic, corrupted DB header) and proves each is **detected and recovered byte-for-byte** (11/11 pass).
- **`engine/tests/mutation_xl.py` — two expanded mutation rounds.** Round 1 injects 26 faults into the
  engine logic (25 killed, 96%); round 2 injects 12 faults into the safeguard itself (11 killed, 92%).
  Overall **36/38 killed (95%)**; the 2 survivors are equivalent mutants. Pillar suite grew to 19 tests
  (added empty-query, predictive-prefix, size-prefix). `run_tests.bat` now runs all three suites.
### Verified
- Root cause reproduced in-sandbox; 19 pillar + 11 truncation tests green; 36/38 mutants killed.
  Full write-up: `docs/DATA-PROTECTION.md`. Note: run the safeguard **on Windows** so it snapshots the
  real, intact files (a sandbox would capture the stale read).

## [0.28.0] — 2026-06-02 — Hi-fi loupe + dataset correlations + pillar & mutation tests
### Added
- **High-fidelity loupe.** `/page` now accepts a `clip=x0,y0,x1,y1` sub-rectangle and renders just
  that region at high DPI (up to 700). The loupe requests a crisp 1:1 crop of the real page under the
  cursor instead of CSS-stretching the low-res page — measured **~21× more pixels** for the magnified
  region, so fidelity *increases* as you zoom. Grounded: the same drawing re-rasterised at higher
  resolution (vector pages gain true detail; scans get best honest interpolation — nothing invented).
- **Correlations sidecar (`index/correlations.db`).** A new, fully additive read-only DB derived from
  `viewer.db` connects links the flat tables implied but never surfaced: cross-platform
  interchangeability (**19,511 NSNs span >1 vehicle**; top part fits 33 platforms), **884 NIIN
  format-drift** review groups, and **311 supersession pairs** we hold both sides of. Surfaced via
  `/api/correlations?nsn=` (active only when the sidecar exists). `viewer.db` is never touched (R1);
  delete the sidecar to roll back (R6).
- **Pillar test suite + mutation testing** (`engine/tests/`, `engine/run_tests.bat`). 17/17 pillar
  tests pass against a deterministic fixture; mutation testing injects 15 realistic faults and **kills
  100%** of them. Two equivalent mutants were identified and replaced. Logic under test lives in
  `engine/core_pillars.py`, a verbatim mirror of `viewer_app.py`.
- `engine/tools/congruency_probe.py` — read-only congruency audit (0 malformed NSNs, no orphans).
### Invariants (R1 · R6)
- All three additions are non-destructive: the loupe is a new query param, the correlations are a
  separate deletable file, and the tests run on a fixture. The dataset, FTS search, and 104th sheet
  generation are unchanged.
### Verified
- 21× pixel gain measured on a real corpus page (`docs/diagrams/loupe-fidelity-demo.png`); sidecar
  spot-checked (bolt `5305-01-674-1467` → 33 platforms); 17 pillar tests green; 15/15 mutants killed.
  Full write-up: `docs/CONGRUENCY-AND-TESTS.md`.

## [0.27.0] — 2026-06-02 — Schematic legibility viewer: Clean + contrast, 3D tilt, hover loupe
### Added
- **Clean toggle + contrast slider** in the page viewer. Server-side, the real page is re-rendered hi-DPI
  and run through a grounded enhancement pipeline (`_clean_png`): grayscale → auto-contrast → median
  de-speckle → unsharp sharpen → optional extra contrast / high-contrast binarize. It is the **same
  drawing**, just more legible — no strokes or detail are invented. (Conservative enhance + optional
  high-contrast mode, as selected.)
- **3D tilt** of the flat schematic — a CSS `perspective rotateY` on the page image (−45°…+45°), to read a
  page at an angle. This is an honest **flat-sheet tilt**, not reconstructed depth.
- **Hover loupe** (🔎) — a client-side 2.6× magnifier that follows the cursor over the page, built from the
  same rendered PNG (no extra fetch, fully offline).
- `run_app.bat` now also ensures **Pillow** is installed (used by the cleanup pipeline); if Pillow is
  missing the server falls back to the original page bytes, so nothing breaks.
### Invariants (R1 · R6)
- Every control is **off by default and presentation-only**: the dataset, FTS search, and 104th sheet
  generation are untouched and the end-to-end process is unchanged. All effects are instantly reversible.
### Verified
- Cleanup produces valid PNGs on a real scanned corpus page (clean, clean+contrast, binarize modes); UI JS
  lint clean; `/page?clean=1&contrast=N` route wired. Offline; grounding rule unchanged.
### Next (proposed, not yet built)
- Deep-zoom tiles (OpenSeadragon), drag spotlight / box-highlight, callout-number → part hotspots
  (OCR-gated), and optional line-art vectorization. See diagram 41 (built) / 40 (proposal).

## [0.26.0] — 2026-06-02 — 3D viewer upgrade: family shapes, material/colour, expanded dimensions
### Changed
- The representative 3D viewer now renders **family shapes** (cylinder · hex · disc · box) chosen from the
  item name, with **depth-sorted filled faces** instead of a bare wireframe.
- **Material / colour / finish appearance**, grounded in FLIS: the solid is tinted to the **stated colour**
  when FLIS gives one (cited), otherwise a **material-based representative tint** (steel→grey, aluminium→
  silver, copper/brass→bronze, plastic→dark, rubber→near-black), clearly labelled "material tint — not a
  stated colour". Finish (anodize, cad-plate, etc.) shown as a label. (~19k parts have material, ~8.3k a
  finish, ~1.8k an explicit colour.)
- **Expanded dimension parsing**: prefers "overall"/"body" dimensions and reads more FLIS fields → more
  accurate sizing. The "View representative 3D" button is now **gated to parts that actually have a
  bounding dimension** (~20,869), not just any characteristics.
### Verified
- Cylinder (steel, with bore), hex nut (bronze, bore), and aluminium plate render correctly with material
  colour + depth shading. UI JS lint clean. Offline, no library; grounding rule unchanged (representative,
  cited; nothing invented).

## [0.25.0] — 2026-06-02 — Overnight: full-catalog parts + FLIS enrichment, supersession/vintage, 2D→3D, rollback
### Done (executed on the live full index `viewer.db`)
- **Structured parts on the full index:** extracted **227,908** records / **45,068 distinct part NSNs**
  from 40,793 RPSTL pages (one streaming pass).
- **FLIS enrichment of the whole catalog:** **41,701 NSNs** filled from the DLA FLIS Reading Room
  (NIIN-keyed): 44k item names, 41k part #/CAGE, 31k decoded characteristics (real dimensions), 40k AAC +
  unit price + **vintage date**, 25.7k with **multiple part-number choices**, 9.4k with **supersession
  cross-references**. Append-only (R6), cited. Index verified intact (39,683 docs · 1,848,465 pages).
### Added (features)
- **Supersession / vintage / multiple-choice** (migration `0008`): each enriched NSN now carries a FLIS
  **data_date** (UI shows the year, e.g. `FLIS 2013` vs `FLIS 2025`), a **superseded / current-NSN
  cross-reference**, and **alt_parts** (additional reference part numbers). Surfaced on the cart's
  external-reference line ("⚠ also P/N (verify which applies)", "↪ status … cross-ref NSN …", "FLIS YYYY").
- **2D→3D representative viewer**: an offline, library-free rotatable solid (SVG-projected, drag to rotate,
  scroll to zoom) **scaled to the dimensions FLIS states**, with the distinguishing features listed
  verbatim & cited and a clear "representative — not a CAD model" label. "🧊 View representative 3D" button
  on cart items that have FLIS characteristics. Projection verified by render.
- **Rollback (R1):** `rollback` command + `engine\run_rollback.bat` (dry-run by default; `/yes` to apply) +
  `docs/ROLLBACK.md`. Removes the enrichment + extracted parts; never touches documents/pages/OCR text.
### Search speed
- Refreshed indexes (`parts.nsn`, `ref_nsn.nsn`) + `ANALYZE`. Full-text search measured at **~45 ms** over
  the 1.85M-page corpus.
### OCR — honest status (NOT complete)
- A 100% OCR pass of the remaining scanned pages is a multi-day **GPU** job and cannot be truthfully
  completed in this build environment. The pipeline is ready: `engine\run_ocr_gpu.bat` (applies migrations,
  prioritizes, loops `ocrall`). Task remains open until it finishes on your hardware; OCR only *adds* text
  to blank pages (R6), and after each pass the parts/enrichment can be re-run to cover newly-readable NSNs.
### Notes
- Background processes do not persist between calls in the build environment, so all heavy work was done in
  bounded, verified passes (not unattended). Everything additive (R1) and rollbackable.

## [0.24.0] — 2026-06-02 — PUB LOG enrichment RUN on the live index (NIIN-keyed FLIS ingest)
### Done (actually executed on `viewer.db`)
- Ingested the user's downloaded **DLA FLIS Reading Room** catalog (~16 GB of table extracts) into the
  live index. **468 index NSNs enriched** from authoritative data — 406 item names, 463 part numbers,
  451 AACs, 421 with decoded characteristics (real dimensions), plus unit prices and cancellation status.
  Append-only (R6); the 39,683-doc index verified intact afterward.
- Real examples now offline & cited: `6115-01-036-6374` → GENERATOR SET, DIESEL ENGINE · P/N MEP007B ·
  CAGE 30554 · AAC V · $35,140.51 · "frequency 50–60 Hz, three-phase…"; `5985-00-933-2197` → MAST ·
  nested height 72.000 in, base dia 4.250 in.
### Added (productized so it's reproducible monthly)
- **`enrich_flis()`** in `viewer_ingest.py` — pure-Python (Windows-friendly, no `grep`) NIIN-keyed ingest
  of the real FLIS table layouts: `V_FLIS_IDENTIFICATION`+`P_H6_PICK` (INC→item name), `V_FLIS_PART`
  (part#/CAGE), `V_FLIS_MANAGEMENT` (AAC + unit price), `V_CHARACTERISTICS` (aggregated size/thread),
  `V_FLIS_CANCELLED_NIIN` (status/replacement, kept per R6). Matches the middle-9-digit NIIN of each
  index NSN, filters to in-index NIINs, merges fields without clobbering, append-only log.
- `enrich --publog-dir <folder>` now auto-detects FLIS Reading Room files and routes to `enrich_flis`.
### Notes
- Coverage is 468 because the index currently holds ~505 cover/end-item NSNs; the thousands of individual
  RPSTL part NSNs aren't extracted on `viewer.db` yet. Run `parts` on the full index, then re-run
  `enrich --publog-dir`, to fill those too (offered as the next step).
### Verified
- The exact ingest logic was run live (counts above) and the index re-reads cleanly; `enrich_flis` parses
  and mirrors that proven logic. Dark diagram `docs/diagrams/36-flis-enrichment-run`.

## [0.23.0] — 2026-06-01 — PUB LOG via the FLIS Reading Room (direct CSVs, no Windows app)
### Added
- **`enrich --publog-dir <folder>`** ingests the DLA **FLIS Data Electronic Reading Room** files directly:
  Identification, Reference (part#/CAGE), Characteristics (size/thread), Management (AAC/I&S), CAGE,
  History (inactive NSNs), H-Series. These are **plain monthly CSVs** — no PUB LOG Windows app / Batch/SQL
  export needed (a correction to the 0.22.x guidance).
- The ingester reads every CSV/XLSX in the folder, keeps only **in-index NSNs**, composes the NSN from
  `FSC`+`NIIN` when needed, and **merges each NSN's fields across files without clobbering** (Identification
  → name, Reference → part#/CAGE, Characteristics → size, Management → AAC/substitutes). Append-only log (R6).
### Notes
- **History.zip retains inactive/cancelled NSNs** — directly serves R6 (keep outdated info).
- Updated `docs/PUBLOG-EXPORT-QUICKSTART.md` and `docs/REFERENCE-SOURCING.md` to the direct-CSV workflow.
  The big files are large (full federal catalog) so the download is the only heavy part; the ingest is fast.
### Verified
- Folder ingest of three Reading-Room-style files (Identification + Reference + Characteristics) for one
  in-index NSN → a single merged record (name + part# + CAGE + characteristics), with **3 versions retained**
  in `ref_nsn_log` (non-clobbering UPSERT + append-only, R6). Dark diagram `docs/diagrams/35-flis-reading-room`.

## [0.22.1] — 2026-06-01 — One-click enrichment launcher + PUB LOG export quickstart
### Added
- `engine/run_enrich.bat` — drag a PUB LOG export (CSV/XLSX) onto it (or pass a path) to run the one-time
  enrichment: upgrades pip, ensures `openpyxl`, migrates, and runs `enrich --publog`. With no file it loads
  just the public-domain hardware reference. Stays offline; append-only (R6).
- `docs/PUBLOG-EXPORT-QUICKSTART.md` — exact steps to download PUB LOG (free, no CAC), export the right
  fields (NSN / item name / part# / CAGE / characteristics / AAC / substitutes) to CSV, and load it. Lists
  the header variants the ingester accepts. Reuses diagram `34`.
### Note
- The PUB LOG download (~GB `.ZIP`) and DLA's Windows export tool run on a **connected machine** — they
  can't be driven from the build environment. Once you have the export CSV, the ingest is one step (or drop
  the file in the project folder and I'll map/run it).

## [0.22.0] — 2026-06-01 — PUB LOG reference ingest (proof of concept)
### Added
- **`enrich --publog <csv|xlsx>`** ingests a PUB LOG (DLA) export — the authoritative, publicly-releasable
  federal catalog. Matched **only to NSNs already in your index**, it fills **item name, part # + CAGE
  (MCRD), characteristics (CHAR), AAC and substitutes (MDI&S)**. Append-only/versioned (R6) and cited;
  `ref_nsn` is UPSERTed so GSA and PUB LOG fields don't clobber each other.
- Migration `0007`: `ref_nsn` / `ref_nsn_log` gain `part_no`, `cagec`, `characteristics`, `aac`,
  `substitutes` (additive, R1). `/api/reference` returns them.
- **Cart auto-fills the authoritative part # (MCRD) and AAC (MDI&S)** onto the 104th when PUB LOG has
  them, and the "📚 External reference (cited, offline)" line now shows P/N · CAGE · AAC · characteristics
  · substitutes.
### Why this matters (closes several gaps at once)
- **Part # + CAGE** = the authoritative part number we deferred in the structured-parts work (RPSTL OCR
  was noisy) — now from data.
- **Characteristics** (e.g. `1/2-13 UNC`) = the **size parameter Tier 2.5 needs** for parametric 3D
  (matches `ref_hardware`).
- **AAC** fills the 104th's AAC block; **substitutes** ground look-alike/variant warnings.
### Notes — honest scope
- This is a **proof of concept**: the ingester, schema, and UI are proven on synthetic PUB-LOG-shaped rows
  against real in-index NSNs. The actual fill requires the one-time PUB LOG download + Batch/SQL export on
  a **connected machine** (the ~GB `.ZIP` / IMD product format isn't fetched here); column-name variants
  are handled and easily mapped. Append-only & cited (R6); the engine never goes online. Sourcing write-up:
  `docs/REFERENCE-SOURCING.md`.
### Verified
- Migration `0007` applies; PUB LOG ingest filtered to in-index NSNs (bogus NSN excluded); all fields
  landed and are returned by `/api/reference` (NSN `6115-00-118-1241` → P/N `MS90726-60`, CAGE `96906`,
  AAC `D`, char `1/2-13 UNC; GR5; STEEL`, subs `5305-01-310-1234`). UI JS lint clean. Dark diagram
  `docs/diagrams/34-publog-poc-built` (+ PDF).

## [0.21.1] — 2026-06-01 — One-time enrichment reads the real GSA file format (XLSX)
### Added
- `enrich --gsa` now reads the official GSA extract **directly as `.xlsx`** (streaming via openpyxl) as
  well as `.csv`, so the one-time fill points straight at the downloaded data.gov file — no conversion.
### Notes
- Confirms the intended posture: the **running engine never goes online**; `enrich` is a one-shot,
  hand-run filler (ideally on a connected machine, then copy the DB back). Source confirmed: the GSA NSN
  Extract is **public-domain (CC0)** but is the **GSA Advantage subset, last updated 2017** — it fills the
  commercially-listed NSNs (dated), not the full military catalog (that needs FLIS/WebFLIS). Whatever it
  provides is kept append-only and clearly dated/cited (R6). Reuses diagrams `31`/`32` (flow unchanged).
### Verified
- The reader yields correct rows from both `.xlsx` (GSA layout) and `.csv`; column-name variants handled.

## [0.21.0] — 2026-06-01 — Append-only NSN enrichment (rule R6) + dataset-growth scope
### Added
- **Standing rule R6 — append-only data:** you may always ADD to the search engine, but never take away,
  even if the information is outdated. (Memory + `DECISIONS`/this changelog.)
- **Append-only NSN reference log** (migration `0006`, `ref_nsn_log`): every GSA enrichment pass now
  **appends** a timestamped version per NSN and keeps them all; `ref_nsn` is just a convenience "current"
  (latest) pointer, with full history preserved in the log. Re-running `enrich` never overwrites-without-
  trace. `enrich` reports how many distinct index NSNs it's matching.
- `/api/reference` now returns a **`versions`** count; the cart's external-reference line shows
  "… · N versions on file" so superseded/outdated NSN data stays visible and searchable.
### Notes — answering "add more NSNs / TMs; space & scope?"
- **NSNs for everything in your dataset = cheap.** Pure text (~0.5 KB/row); even 100k NSNs ≈ tens of MB.
  Run `enrich --gsa <official GSA extract.csv>` to append current name/desc/price for every NSN already in
  the index (the bulk GSA CSV download is a few hundred MB, but only your matches are kept).
- **Standards/hardware = trivial** (kilobytes).
- **Whole TM documents = heavy** (PDFs MB–tens of MB each + OCR/index; hundreds of TMs = GB–tens of GB +
  OCR time) and use a different sourcing path (public TM repositories, not data.gov). Best added
  deliberately, with version/authority checks — separate from the NSN text enrichment.
### Verified
- Two enrichment passes on one NSN (changed price/name) → **both versions retained** in `ref_nsn_log`,
  `ref_nsn` points at the latest (R6 honored). Migration `0006` applies; `/api/reference` returns the
  version count. UI JS lint clean. Dark diagram `docs/diagrams/32-append-only-and-scope` (+ PDF).

## [0.20.0] — 2026-06-01 — Online → offline reference enrichment (cited, official-only)
### Added
- **`viewer_ingest.py enrich`** — a one-time **online** enrichment that the engine then uses **offline**:
  - **Public-domain standard-hardware reference** (FED-STD-H28): a seeded `ref_hardware` table of common
    UNC/UNF/metric threads with major diameter, TPI/pitch, tap drill, and a *general* reference torque.
  - **Official GSA NSN Extract** (data.gov) ingest via `--gsa <csv>`, **filtered to NSNs already in your
    index** → `ref_nsn` (item name / description / GSA list price). Targeted and relevant, not a bulk dump.
- **`GET /api/reference?nsn=&size=`** and a **cart line**: "📚 External reference (cited, offline): …"
  showing the NSN's name/GSA-list-price and the thread's dimensions — clearly marked external.
- Migration `0005`: `ref_hardware` + `ref_nsn`, each with full provenance (`source`, `source_url`,
  `fetched_at`). Additive (R1).
### Notes — provenance & separation (grounding)
- External data lives in **separate tables** and is **never merged into manual citations**, so it can't
  pose as TM-sourced. Every row carries its source + URL + date and is labeled "External reference."
- **Official / public-domain only** (FED-STD-H28, GSA/data.gov); third-party NSN scrapers excluded.
- The displayed **torque is a general reference — the TM's stated torque governs.** FEDLOG price/AAC/ARC
  still come from your AMDF; the GSA figure is shown as a "list" price, labeled.
- This fills missing **nomenclature** on the request sheet and supplies cited **dimensions** for standard
  hardware (the Tier 2.5 key). Full parametric 3D still needs each part's specific **size** — from RPSTL
  text, fuller NSN characteristics (FLIS) where available, or SME-confirmed; model only when size is
  certain (decisions recorded in `docs/SCHEMATIC-3D-PLAN.md` §4b).
### Verified
- On the live sample index: migration `0005` applies; the 22-row hardware seed loads; the GSA ingest
  keeps **only** in-index NSNs (a bogus NSN was correctly excluded); `/api/reference` returns cited
  NSN and thread data (size prefix-match, e.g. `1/2-13` → `1/2-13 UNC`, `M12` → `M12x1.75`). UI JS lint clean.
- Dark diagram `docs/diagrams/31-reference-enrichment-built` (+ PDF).

## [0.19.0] — 2026-06-01 — Structured parts index (Phase 1) + coverage meter + quick wins
### Added
- **RPSTL parts extractor** (`viewer_ingest.py parts`): scans parts catalogs ("Usable On Code" pages)
  and builds a structured, **cited** index — each **NSN → figure number + figure title + document +
  page + vehicle**. Idempotent full rebuild; auto-refreshes after `run` / `ocrall`. Migration `0004`
  extends the reserved `parts` table (+ `sessions.tech_status_suggested/basis`). Additive (R1).
- **`GET /api/part?nsn=`** — cited catalog references for an NSN (which figures/pages/vehicles it
  appears in, with cross-references). **In the parts cart**, adding a part with an NSN now shows
  "📐 In parts catalog: FIG 3 Cooling System (p.372) — verify" (click opens the page) and **auto-fills
  the FIG number** from the catalog.
- **`GET /api/coverage`** + a **"% searchable" badge** in the vehicle hub (per-vehicle share of pages
  with text/OCR) — makes OCR progress visible (e.g., Buffalo 99%, M998 97%, generators 91%).
- **Multi-sheet 104th:** requests over 6 items now paginate across multiple sheets ("Sheet 2 of 2")
  instead of capping at 6.
- **Suggestion capture:** the tech-status suggestion + basis are saved next to the confirmed status,
  improving the history signal over time.
- Dark diagrams `docs/diagrams/24-structured-grounding-proposal` (design) and `27-structured-parts-built`.
### Notes — grounded, and explicit about the limit
- **Reliable & shipped:** the NSN→figure→page citation index. Every record points at a real page to
  verify; the cart auto-fills only the FIG number and shows the cited figure title — it never fabricates
  a part number or nomenclature.
- **Deliberately deferred (Phase 2):** exact NSN↔part#↔nomenclature row alignment and automatic
  look-alike-variant warnings. OCR de-interleaves RPSTL columns, so asserting those now could put a wrong
  part on a request sheet — that precise table parser comes next, strengthened by the ongoing OCR pass.
### Verified
- On the live sample index: migration `0004` applies; extractor → 28,330 NSN records / 10,521 distinct
  NSNs across 3,748 RPSTL pages; `/api/part` and `/api/coverage` return cited data; 8-item request →
  2-sheet PDF ("Sheet 2 of 2"). UI JS lint clean.

## [0.18.0] — 2026-06-01 — Switchable layouts behind a Settings panel (presentation only)
### Added
- **⚙ Settings panel** (header) that consolidates the previously scattered toggles into one place:
  text size (Normal/Large/X-Large), density (Comfortable/Compact), fields (Simple/Advanced), default
  search match (All/Any), and viewer defaults (thumbnails, highlight).
- **Named layout presets** that bundle those settings: **Simple/Junior**, **Advanced/SME**,
  **Shop floor/Touch**, **Compact/Desktop** (+ Default and an auto-detected "Custom"). Picking a preset
  applies the whole bundle; individual fine-tuning is still available.
- **Per-device persistence + Reset to default.** Saved as `viewer_settings`; legacy single-toggle keys
  (`viewer_big` / `viewer_simple` / `viewer_any`) are migrated forward. Reset restores the default layout.
- Dark diagrams `docs/diagrams/25-layouts-settings-proposal` and `26-settings-presets-built` (+ PDF).
### Notes
- **Presentation only — the core is invariant.** A layout is nothing but CSS classes on `<body>` plus two
  JS defaults; it never changes `/api/search`, `/api/request`, the index, or the request payload. The
  end-to-end flow (modal → search → cart → tech-status gate → 104th PDF) runs identically under every
  preset. Unknown/missing settings fall back to default; a startup self-check warns if core controls are
  ever missing after a layout apply. Client-only — **no server or schema change** (R1).
### Changed
- The old standalone "A+" and "Advanced view" header buttons are replaced by the ⚙ Settings panel
  (same capabilities, now grouped). The inline All/Any search toggle stays and is kept in sync.
### Verified
- Presets flip only CSS classes; search and sheet generation are unaffected; legacy-key migration and
  Reset confirmed; UI JS lint clean (`node --check`).

## [0.17.0] — 2026-06-01 — Tech Status derived from the fault + part (PMCS-cited), mandatory at export
### Added
- **`GET /api/techstatus`** suggests an equipment status from the fault and requested parts:
  - **(A) PMCS-grounded, cited:** searches the vehicle's pages for the fault terms within the TM's
    "**Not Fully Mission Capable If**" / "mission capable" PMCS criteria and returns the matched lines
    with TM + page citations. A match = a deadlining fault → suggests **NMCS** (parts on order → supply).
  - **(B) Learned history:** if no PMCS criterion matches, falls back to the status a mechanic confirmed
    for similar faults before (`sessions.tech_status` + `faults`).
  - Returns nothing to "auto-decide" when neither matches — the mechanic sets it.
- **Mandatory confirm gate at export.** "Export Parts Request Sheet" now opens a gate that shows the
  suggestion, the **cited PMCS criteria** (click to open the actual manual page), any history, and a
  status dropdown (**FMC / PMCM / PMCS / NMCM / NMCS**). The sheet cannot generate until a status is
  chosen — and `POST /api/request` also rejects a blank tech status as a safety net.
- Modal **Tech status** field is now a dropdown of the five doctrinal codes (default "set at export").
- Dark diagrams `docs/diagrams/20-tech-status-proposal` (proposal) and `21-tech-status-built` (+ PDF).
### Notes
- The app **proposes and cites; the human confirms** — it never silently makes a readiness call or
  invents a deadline (the project's safety stance). Tech status is therefore always present by the end,
  but always human-verified. Additive (R1): no schema change.
### Verified
- On the live sample index: Buffalo "steering hard / will not steer" and "headlight inoperative" → cited
  NMCS criteria (TM 9-2320-327-10 PMCS pages); a cosmetic fault → no auto-suggestion (manual). Result
  de-duplication, history fallback, and the blank-status rejection all confirmed. UI JS lint clean.

## [0.16.0] — 2026-06-01 — Self-learning search + calmer modal/search
### Added
- **Learns from successful sheets.** A new `GET /api/popular` aggregates `request_items` (every part that
  made it end-to-end onto a generated 104th) by NSN / nomenclature, ranked by **frequency + recency** —
  the label is taken from the most recent request. No schema change; the log already existed.
- **Rotating example.** The search box and modal field now show a **single, real example** that rotates
  each time (a random common part, e.g. `BATTERY, STORAGE · 6140-01-485-1472`) instead of four static
  ones. A built-in seed list (battery, gasket, alternator, fuel/oil filters, V-belt) covers a fresh
  install, then it shifts to the shop's own common parts as they accumulate.
- **"Commonly requested" quick-picks.** A thin row of ★ chips on the Home screen (top 6 learned parts) —
  tap to search instantly.
- **Popularity-ranked results.** Keyword results whose NSN you've requested before float to the top
  (stable sort) and show a small `★ requested` badge. Backed by a 60-second-cached `popular_nsns()`.
### Changed
- Trimmed the modal subtitle and the search hint to one line each — the rotating example now does the
  teaching (calmer, less hand-holding). *(Fault was already a required field; unchanged.)*
- Dark diagram `docs/diagrams/18-learning-search-proposal` (proposal) and `19-learning-search-built`
  (built data flow) — both + PDF.
### Notes
- Fully additive (R1): no migration; new `/api/popular` and the learned ranking are derived live from
  existing data. Offline and private — everything stays in the local index.
### Verified
- On a seeded `request_items` sample: grouping by NSN/nomenclature with the newest label, frequency+recency
  ordering, nomenclature-only items, and the stable popularity boost all behaved correctly. UI JS lint
  clean (`node --check`).

## [0.15.0] — 2026-06-01 — Onboarding modal aligned to the 104th sheet header
### Changed
- The onboarding modal now **mirrors the 104th ECC Parts Request Sheet header 1:1** — same field
  order and the sheet's exact labels: `MECHANIC'S NAME (PRINT/SIGN)` → `BUMPER#` | `FAULT` →
  `TM` | `UOC` | `TECH STATUS` → `MOTOR SERGEANT / SENIOR MECHANIC`. The header fields are grouped
  under "Parts request sheet header," and the search/express field is set apart ("search only — does
  not print on the sheet").
- **Header fields are always visible.** Previously "Simple view" hid UOC / Tech status / Motor sergeant,
  which contradicted the sheet's "FILL OUT ALL BLOCKS." Simple view now only hides the per-item FEDLOG
  fields (Unit price / AAC / ARC) in the parts cart.
### Added
- **Live sheet-header preview** inside the modal: a paper-style replica of the 104th header that fills
  in as you type, so what you enter is exactly what prints (mirrors `parts_request_pdf.py`).
- Dark diagram `docs/diagrams/16-modal-sheet-alignment` (proposal/markup) and
  `docs/diagrams/17-modal-header-aligned` (built + field→SESSION→block data flow) — both + PDF.
### Notes
- Verified against the user's original scanned sheet (`104TH PARTS REQUEST SHEET PDF.pdf`): the header
  blocks are Mechanic, Bumper#, Fault, TM, UOC, Tech status, and the Motor sergeant footer — no Date/
  Unit/DODAAC blocks, so none were invented (faithful replica, R1).
- Fully additive: field IDs and `SESSION` keys are unchanged, so the generated 104th PDF is identical.
  Required fields remain Bumper# + Fault. UI JS lint clean (`node --check`).

## [0.14.0] — 2026-06-01 — Search upgrades: "Last-4" NSN lookup + smarter key terms
### Added
- **"Last 4" lookup:** typing exactly **4 digits** (e.g. `2202`) now finds every manual whose
  **cover / end-item NSN** ends in those digits — the bench shorthand for NSN/NIIN. Auto-detected, with
  a `LAST-4 •2202` banner and a one-click **"Search all manuals for 2202"** escape hatch that falls back
  to a full-text search (reaching part NSNs printed inside the manuals). *Scope is cover-NSN-only by
  design (your call) to keep false positives low.*
- **Synonym / alias expansion:** an extensible `engine/synonyms.json` (32 starter groups) means one term
  also searches its equivalents — `gasket↔seal↔packing↔o-ring`, `alternator↔generator`, `fig↔figure`,
  `niin↔nsn`, etc. Edit the file and restart to grow it.
- **Offline typo tolerance (fuzzy):** an `fts5vocab` view over the index lets a misspelled word match
  indexed terms within edit-distance 1 (`altenator`→`alternator`) — bounded prefix scan, fully offline.
- **Part # / FIG / callout precision:** hyphenated codes (e.g. `5330-01-186`) are matched as an adjacent
  phrase for precision; `fig`/`callout`/`item` map to their manual wording via the synonym groups.
- **All ↔ Any toggle:** a Match control by the search box switches between requiring **all** words
  (default, precise) and **any** word (OR, broader). Persists across launches.
- Dark diagram `docs/diagrams/15-search-upgrades` (+ PDF).
### Notes
- Fully additive (R1): no schema migration; the `fts5vocab` view is a read-only index over `pages_fts`.
  Full-NSN search, vehicle hub, and all existing behavior are unchanged. New `/api/search` params
  (`any`, `mode`, `fuzzy`) all default to prior behavior when omitted.
### Verified
- On a live FTS5 sample: synonym (`gasket`→seal/packing pages), fuzzy (`altenator`→alternator),
  `fig 7`→figure, part-number phrase precision, ANY vs strict-AND, and Last-4 cover-NSN matching (parts
  in body text correctly excluded unless the escape hatch is used). UI JS lint clean (`node --check`).

## [0.13.0] — 2026-06-01 — Dynamic front-end: home, smart results, viewer zoom/thumbnails/highlight, responsive
### Added
- **Home / browse-by-vehicle:** the search column now shows a home screen when the box is empty — a
  filterable grid of every vehicle in the index (name · #manuals · NSN), **recent searches** (saved in
  the browser), and **recent parts requests**. New endpoints `GET /api/vehicles` and `GET /api/sessions`.
- **Smart results:** results gain a filter bar with live counts ("N of M · K vehicles") and clickable
  chips to filter by **vehicle**, **manual type** (Operator/Maintenance/Parts/Troubleshooting/Schematics/…
  derived client-side), and **Text vs OCR** source. Cards now show a manual-type badge. NSN bypass and
  the NSN banner are unchanged.
- **Viewer upgrades:** **zoom** (−/100%/+ re-renders the page sharp via `/page?dpi=`), a **thumbnail
  strip** (±8-page window, lazy `dpi=24` images, click to jump, current page highlighted), and
  **highlight-the-hit** — `/page?hl=` uses PyMuPDF `search_for()` to draw yellow boxes over the search
  term on the page's text layer (no-op on scanned/image pages, which have no text layer).
- **Shop-floor ergonomics:** responsive layout (columns stack, viewer panel moves below on phones/tablets),
  larger touch targets on touch devices, an **A+ large-text** toggle, and a **Simple ↔ Advanced** field
  toggle (hides FEDLOG/AAC/ARC + extra header fields in Simple). Both toggles persist across launches.
- Dark diagram `docs/diagrams/14-ux-dynamic-frontend` (+ PDF).
### Notes
- Fully additive (R1): no schema change; `/api/search`, `/api/vehicle`, `/api/request` unchanged. The
  schematics-on-every-page panel is preserved. Highlight precision on scanned pages grows as OCR adds text.
### Verified
- New SQL (`/api/vehicles`, `/api/sessions`) returns correct shapes on a schema sample (image-type and
  vehicle-less docs excluded; NSN + fault + item count joined). UI JS lint clean (`node --check`).
  Highlight render path uses standard PyMuPDF `search_for`/`add_highlight_annot`.

## [0.12.0] — 2026-06-01 — OCR speedup: skip-the-junk + prioritized queue
### Added
- **Skip-the-junk:** `ocr_one` now checks each page for blankness (render @50dpi, ink ratio) and
  **skips blank pages with no OCR inference** (~0.01s vs ~1–3s). New `prefilter` command marks blank
  pending pages `skipped` to shrink the queue upfront.
- **Prioritized OCR queue:** new `prioritize` command (auto-run by `ocrall`) orders OCR — parts
  catalogs (RPSTL/-24P) first, then maintenance/troubleshooting, then operator, then the rest — so
  the most useful pages become searchable first. OCR query now `ORDER BY ocr_priority, id`.
- Migration `0003_ocr_priority.sql`: `pages.ocr_priority` + index, and narrows the FTS sync trigger
  to fire only on `body_text` changes (status/priority updates no longer reindex → faster requeues/cleanup).
- Dark diagram `docs/diagrams/12-ocr-speedup` (+ PDF).
### Verified
- Blank page → skipped in 0.013s (no inference); text page → OCR'd. Priority distribution: 1,875
  parts pages ranked first, then maintenance/operator. Schema upgraded 2→3, data intact.
### Note
- Active on the next OCR launch (`run_ocr.bat` / `run_ocr_gpu.bat` apply migration 0003 and auto-prioritize).

## [0.11.0] — 2026-06-01 — Express modal + Schematics on every page
### Added
- **Modal express search / bypass:** an always-on "What do you need?" field (part name / part # / NSN)
  in the onboarding modal. On Start, an exact NSN/part# jumps straight to the page (or vehicle hub for
  a vehicle NSN); anything else becomes the first search. Blank = behaves as before.
- **Always-on "Schematics & install" panel** in the document viewer (fallback chain, never empty):
  cited figure (FIG # detected in the matched line) → the manual page itself → the vehicle's schematic
  set (from the hub). Shows install/location text **verbatim** from the manual; nothing invented.
- Design diagram `docs/diagrams/11-schematics-express-proposal` (dark + PDF).
### Notes
- Server unchanged (reuses `/api/vehicle`); all UI. Guarantee is "a relevant graphic always appears,"
  with the part-specific figure surfaced & cited when the manual provides it (precision grows with OCR).
### Verified
- Express field + side panel render; hub still groups schematics; UI JS lint clean.

## [0.10.0] — 2026-06-01 — NSN search + Vehicle breakdown hub
### Added
- **Full-NSN search (part + vehicle):** the server detects a full NSN in the query, exact-matches it
  against page text *and* the document cover NSN, and classifies it Part vs Vehicle/End-item by
  Federal Supply Class (2320/2350/… = vehicle). A blue NSN banner shows the classification.
- **Vehicle breakdown hub** (`GET /api/vehicle?key=`): a vehicle NSN (or clicking a vehicle name)
  opens a full-screen hub grouping that vehicle's whole manual set — Operator (-10), Maintenance
  (-20/-24), Troubleshooting, Parts (RPSTL), Schematics/wiring, Lubrication, MWO — each opening the
  real manual page in the viewer. Grouping derives from TM suffix / filename (works even when a
  scanned doc has no extracted TM number).
- Dark diagram `docs/diagrams/10-nsn-vehicle-hub` (+ PDF).
### Notes
- Safety stance (your call): everything stays anchored to the actual manual page; the future
  procedure/tool/troubleshooting panel (Phase 3) will show **verbatim** text with page citations —
  never AI-invented steps, torque values, or tool sizes.
- Also: OCR engine GPU path made version-proof (config-based CUDA request, CPU fallback). True GPU
  needs the CUDA runtime; see `docs/SETUP-GPU.md`.
### Verified
- NSN `2320-01-529-2251` → Buffalo (TM 9-2320-327-10), classified vehicle; hub grouped 21 Buffalo
  docs and 119 generator docs; UI JS lint clean.

## [0.9.4] — 2026-06-01 — Part nomenclature carries to the sheet
### Fixed
- The cart's **Item Name** started blank, so a part's nomenclature didn't reach the 104th sheet
  unless typed by hand. Added `deriveName()` in the UI: adding a part now auto-fills the Item Name
  from the matched manual line (markers/ellipses stripped), falling back to the search term — still
  fully editable. Applies to both "Add to request" and the viewer's "Add this part".
- Verified end-to-end: derived names (e.g. "OVERHAUL GASKET SET") now appear in the ITEM NAME blocks
  of the generated PDF.

## [0.9.3] — 2026-06-01 — Launcher pip self-upgrade
### Fixed
- Every setup/launch file now runs `%PY% -m pip install --upgrade pip` before installing packages,
  so an old pip can't cause a missing/failed dependency and the app launches cleanly.
- Affected: `run_indexing.bat`, `run_ocr.bat`, `run_ocr_gpu.bat`, `run_app.bat`, and the Lite
  portable's generated `SETUP.bat` + `run_ocr_lite.bat` (via `make_portable.py`).
### Added
- `docs/diagrams/_make_changelog_visual.py` — reproducible generator for the visual changelog (R5).

## [0.9.2] — 2026-06-01 — Visual changelog standard (R5)
### Added
- **Standing rule R5:** every changelog entry also gets a detailed graphical explanation and a
  functioning diagram in PDF form.
- **`docs/diagrams/CHANGELOG-VISUAL.svg` + `.pdf`** — a dark, retroactive visual changelog with a
  functioning data-flow panel for every version (0.1.0 → 0.9.2).

## [0.9.1] — 2026-06-01 — Changelog standard (R4)
### Added
- **Standing rule R4:** a changelog entry accompanies every change.
- This `docs/CHANGELOG.md`, retroactively covering all prior builds.

## [0.9.0] — 2026-06-01 — Forked: GPU production + Lite portable
### Added
- Engine flags `--gpu` (RapidOCR on CUDA via `onnxruntime-gpu`, automatic CPU fallback) and `--dpi`
  (render DPI). Additive; defaults unchanged.
- **Advanced/GPU production build** (master): `engine/run_ocr_gpu.bat`, `docs/SETUP-GPU.md`.
- **Lite/portable build**: `engine/make_portable.py` + `make_portable.bat` → self-contained
  `THE VIEWER PORTABLE` folder (engine + finished index + one-click `SETUP.bat` + `START.bat` +
  `run_ocr_lite.bat`, both-mode). `docs/SETUP-LITE.md`.
- `docs/FORKS.md` overview; dark fork diagram `docs/diagrams/09-forks` (+ PDF).
### Notes
- One shared codebase / index schema; profiles selected by flags (R1 safe).
- Priority going forward: the GPU/production build.

## [0.8.1] — 2026-06-01 — OCR reliability fixes
### Fixed
- OCR was failing 100% on the PC: the queue's first rows were leftover sandbox-path docs
  (`/tmp/...`, `/sessions/...`) that don't exist on Windows. Added `cleanup` command that drops
  non-Windows-path rows (and clears non-cascading `request_items`/`figures` refs to avoid FK errors)
  and requeues wrongly-failed pages.
### Changed
- OCR parallelism switched from `ProcessPoolExecutor` to `ThreadPoolExecutor` (shared engine; PyMuPDF
  render under a lock) — reliable on Windows, no process-spawn issues.
- Added `ocrall` command (internal resumable loop) and live per-batch progress logging.

## [0.8.0] — 2026-06-01 — Search GUI: document viewer
### Added
- `GET /page?doc=&page=&dpi=` renders any PDF page to PNG on demand (PyMuPDF); `GET /api/doc` metadata.
- UI document viewer: click a result → full-screen real manual page, prev/next + arrow/Esc keys,
  "Add this part"; OCR-sourced results tagged with an `OCR` badge.
- Dark diagram `docs/diagrams/08-search-gui-viewer` (+ PDF).

## [0.7.0] — 2026-06-01 — Dark diagram standard (R3)
### Added
- **Standing rule R3:** all diagrams use a professional dark theme and ship a PDF.
- Dark palette + cairosvg SVG→PDF export. Converted `06`/`07` to dark + PDF; consolidated
  `00-architecture-darkset` (+ PDF); `viewer.html` switched to Mermaid dark theme.

## [0.6.1] — 2026-06-01 — OCR detail + example
### Added
- Detailed OCR diagram `docs/diagrams/07-ocr-detailed`; OCR before/after example PDF
  (scanned page → recovered text, ~99% confidence on a parts page).
- OCR build/feature map `docs/diagrams/06-ocr-build-featureset`.

## [0.6.0] — 2026-06-01 — RapidOCR engine; full index run on PC
### Changed
- OCR engine switched to **RapidOCR** (`rapidocr-onnxruntime`, pip, no admin, bundled models),
  replacing Tesseract (kept as fallback). Page rasterized via PyMuPDF.
### Added
- Full text-first crawl launched and **completed on the Windows PC**: 40,291 documents,
  ~1.87M searchable text pages, ~133k scanned pages queued for OCR.
- Windows launcher reworked to need only Python (auto-installs pip deps); Tesseract optional.

## [0.5.0] — 2026-06-01 — PyMuPDF text backend
### Changed
- PDF text extraction switched to **PyMuPDF** (`pymupdf`, pip) with Poppler `pdftotext` fallback —
  faster and removes the Poppler hard dependency. (PyMuPDF later also used for OCR rasterization.)

## [0.4.0] — 2026-06-01 — Full-corpus extraction + durability
### Added
- Resumable, time-boxed batch crawling (`--max-files`, `--max-seconds`); cheap skip (size+mtime
  before hashing) so re-walks are fast.
### Fixed
- Index corruption when a write was interrupted on the bridge filesystem: `VIEWER_RELAXED` mode
  switched from in-memory journal to `locking_mode=EXCLUSIVE` + `journal_mode=TRUNCATE` (durable
  rollback journal). Known-good sample index kept as the rollback point.

## [0.3.0] — 2026-06-01 — Onboarding + 104th parts request
### Added
- Migration `0002_sessions.sql`: `sessions`, `faults`, `request_items` (additive; schema v2).
- Offline web app `engine/viewer_app.py` (`/api/search`, `/api/request`) + dark single-page UI
  (`engine/ui/index.html`): onboarding modal → predictive search → editable parts cart → export.
- `engine/parts_request_pdf.py`: clean PDF replica of the **104th ECC Parts Request Sheet**, header
  auto-filled from the modal. `engine/run_app.bat`.
- Diagram for onboarding + parts-request flow (R2).

## [0.2.0] — 2026-06-01 — Indexing engine + OCR pipeline
### Added
- `engine/viewer_ingest.py`: crawl / extract / OCR / status / search; text-first, resumable,
  idempotent; durable OCR job queue.
- Migration `0001_init.sql`: versioned schema — `documents`, `pages`, FTS5 `pages_fts` (+ sync
  triggers), `jobs`, `runs`, `schema_meta`, plus forward-compat `parts`/`part_variants`/
  `procedures`/`figures`.
- `engine/run_indexing.bat`; OCR-indexing data-flow diagram (R2). Sample index built from a
  representative subset to prove search end-to-end (incl. OCR-recovered text).

## [0.1.0] — 2026-06-01 — Architecture & diagrams (Milestone M1)
### Added
- Master architecture (`docs/ARCHITECTURE.md`), decision log (`docs/DECISIONS.md`).
- Architecture & data-flow diagrams (system, ingestion queue, search, data model) as Mermaid sources
  + offline `docs/diagrams/viewer.html`.
- Decisions locked: local web app · SQLite + FTS5 · text-first (OCR deferred).
- **Standing rules R1** (backwards compatibility) and **R2** (diagram with every addition) established.
