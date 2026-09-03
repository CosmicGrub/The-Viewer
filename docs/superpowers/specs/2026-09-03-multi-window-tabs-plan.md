# Multi-window / multi-tab support — implementation plan

**Spec:** `docs/superpowers/specs/2026-09-03-multi-window-tabs-design.md`
**Status:** proposed, awaiting approval before any code changes

Six PRs, each independently branched/tested/merged per this project's established convention (own
CHANGELOG entry, own VERSION bump, own CI pass before merge). Grouped into three stages by real
dependency — not everything is strictly sequential.

## Stage 1 — foundation primitives (can start in parallel)

### PR 1: `VW.channel` — cross-window sync layer
- Add to `shared.js`: `VW.channel.publish(name, data)` / `.subscribe(name, fn)`.
- `BroadcastChannel` primary transport; automatic `storage`-event fallback when `BroadcastChannel`
  is undefined.
- Tests: `rps_lint` still passes on `shared.js`; a new/extended `test_*.py` asserts the exported
  function signatures exist. Manual verification note in the PR: two tabs, `publish` in one,
  confirm `subscribe`'s callback fires in the other, with and without `BroadcastChannel` forced off
  (simulate via deleting `window.BroadcastChannel` before load) to prove the fallback path too.
- No dependencies. Nothing else in this plan can land before this merges.

### PR 2: responsive baseline
- Add shared breakpoints to `base.css` (no width-based rules exist there today).
- Verify by hand on `part.html`, `procedure.html`, `torque.html`, `jobcard.html`, `bench.html` at
  roughly half a 1080p monitor's width — fix any real overflow/collision found, don't just add the
  CSS and assume.
- Tests: `rps_lint`/existing UI test suites stay green (CSS-only change, no new behavioral test
  needed) — call out the manual resize check explicitly in the PR since it's not automatable here.
- No code dependency on PR 1 — can be done in parallel, but merges after PR 1 in sequence to keep
  the branch history simple (avoids two unrelated open PRs racing on `main`).

## Stage 2 — components built on `VW.channel` (parallel once PR 1 is merged)

### PR 3: `VW.workspace` — data model + API
- Add to `shared.js`: `{id, name, items, created, lastOpened}` shape; `create()`, `list()`, `get()`,
  `touch()`, stored under `viewer_workspaces`, riding `VW.channel` for automatic cross-tab
  consistency.
- No UI consumer yet — this is pure data-layer infrastructure.
- Tests: real unit-style assertions on the CRUD functions themselves (pure data shape/logic, no
  cross-tab behavior involved, so this is fully automatable unlike PR 1's live-sync claim).
- Depends on PR 1 (`VW.channel`) only.

### PR 4: `VW.windows` — window-management helper
- Add to `shared.js`: `VW.windows.open(url, opts)` — named-window reuse via `window.open(url, name)`,
  an in-memory open-window registry broadcast via `VW.channel`, instant `shared.js` toast on
  open/refocus.
- Tests: signature/shape assertions (automatable); manual note in the PR for the actual dedup
  behavior (click the same pop-out link twice, confirm one window not two — genuinely not
  observable by this project's HTTP-route-based test suite).
- Depends on PR 1 (`VW.channel`) only — can be developed in parallel with PR 3.

## Stage 3 — the features that actually ship visibly

### PR 5: A1 — home nav pop-out links
- `index.html`'s nav list: every section `<a>` gets an adjacent ↗ wired through `VW.windows.open()`.
- Tests: automated route/markup assertion (every home-nav link has a corresponding pop-out control).
- Depends on PR 4 (`VW.windows`).

### PR 6: D — live-synced Bench across tabs
- `bench.html` and `shared.js`: promote the existing local `get()`/`put()` Bench helpers into
  `shared.js` as the canonical accessor; wire live updates through `VW.channel.subscribe("bench", ...)`
  instead of a bespoke listener.
- Tests: `shared.js` shape assertions (automatable); manual two-tab check called out explicitly in
  the PR (open `bench.html` twice, add an item in one, confirm the other updates with no reload).
- Depends on PR 1 (`VW.channel`) only — could ship before PR 5 if useful, but grouping A1+D as "the
  phase-1 slice" per the spec, so proposing PR 5 then PR 6 as the last two in sequence.

## What happens after this plan

A2, B, C, E, F, G stay exactly as scoped/deferred in the design spec — none of them are part of this
plan. Once PRs 1-6 are merged, each of those becomes a smaller, faster follow-up plan on its own,
since the components they need already exist.

## Verification discipline (applies to every PR above, matching this project's established convention)

- Branch per PR, never commit to `main` directly.
- Real CHANGELOG.md entry + VERSION bump per PR.
- HANDOFF-NOTE.md / PROJECT-SUMMARY.md / MASTER-RECONCILIATION.md kept in sync.
- `ITERATION-SNAPSHOTS.md`/`ITERATION-DASHBOARD.html` regenerated via
  `python engine/build_iteration_snapshot.py` after each merge.
- CI green (GitHub Actions: ubuntu 3.12/3.13/3.14 + windows) before merge.
- Every claim of "tested" backed by an actually-run command's real output — and every claim that
  can't be automated (this plan has several — live cross-tab behavior, window-dedup, responsive
  resize) said honestly as a manual check, not glossed over as covered when it isn't.
