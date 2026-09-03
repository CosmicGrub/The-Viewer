# Multi-window / multi-tab support — implementation plan

**Spec:** `docs/superpowers/specs/2026-09-03-multi-window-tabs-design.md`
**Status:** proposed, awaiting approval before any code changes

**Scale note:** this plan grew from an original 6-PR slice to 18 PRs across 5 stages (deepen every
foundation piece; widen into B/C/F/G as active work), and now to **25 PRs across 6 stages** after a
third expansion adding bleeding-edge platform capabilities and a future-proofing architecture pass.
That's a real, multi-month-scale initiative in engineering time — worth having in view. Stage 6 is
purely additive: it does not change PR 1-18's scope, and PRs 2/5 (in progress when this stage was
added) are unaffected. Nothing below is padding: every PR maps directly to something named in the
design spec. **PR 1 is merged; PR 2 and PR 5 are complete pending independent re-verification and
merge.**

Each PR: own branch, own CHANGELOG entry + VERSION bump, own CI pass, merged before the next
dependent PR starts. Grouped into stages by real dependency, not arbitrarily.

## Stage 1 — `VW.channel` (nothing else can start before this merges)

### PR 1: `VW.channel` — cross-window sync layer, built deep from the start
- `BroadcastChannel` primary transport, `storage`-event fallback.
- Per-channel monotonic sequence numbers (ordering); a `v` schema-version field on every envelope;
  an explicit size guard on the fallback path that throws rather than silently truncating.
- Tests: envelope construction / sequence-number / version-mismatch logic — pure functions, fully
  automatable. `rps_lint` on `shared.js`. Manual PR note: two tabs, `publish`/`subscribe`, with and
  without `BroadcastChannel` forced off, to prove both transport paths.

## Stage 2 — pieces that only need `VW.channel` (can proceed in parallel once PR 1 merges)

### PR 2: `VW.workspace` — data model + CRUD (no export/templates yet)
- `{id, name, items, created, lastOpened, source}`; `create/list/get/touch`, riding `VW.channel` for
  automatic cross-tab consistency.
- Tests: full automated coverage — pure data-shape logic, no live cross-tab behavior involved here.

### PR 3: `VW.workspace` — export/import
- `exportUrl`/`exportFile`/`importUrl`/`importFile`, with the malformed-import rejection behavior
  named in the spec's edge cases.
- Tests: round-trip serialize→deserialize assertions (export a workspace, import it back, assert
  equality) — fully automatable, no browser context needed. A deliberately-corrupted import case
  asserting clean rejection.
- Depends on PR 2 only.

### PR 4: `VW.workspace` — built-in templates
- The "PMCS" and "NSN lookup" presets from the spec, plus `templates()`.
- Tests: automated (static data + the same CRUD path PR 2 already tests).
- Depends on PR 2 only — can land in parallel with PR 3.

### PR 5: `VW.windows` — open/reuse/toast (core, no layout persistence yet)
- `open(url, opts)` with named-window reuse, open-window registry broadcast via `VW.channel`,
  `shared.js` toast on open/refocus.
- Tests: signature/shape assertions automatable; manual PR note for actual dedup behavior (click a
  pop-out link twice, confirm one window).
- Depends on PR 1 only — can be developed in parallel with PR 2/3/4.

### PR 6: `VW.windows` — layout capture + user-triggered restore
- Records `screenX/screenY/outerWidth/outerHeight` per open window; `restoreLayout(entries)` as an
  explicit button-triggered action (not automatic — see the spec's honest note on why that's not
  possible for a web page).
- Tests: capture/restore round-trip on recorded bounds (automatable, no real second monitor needed
  for the data-shape logic); manual PR note for the "monitor unplugged since save" fallback case.
- Depends on PR 5.

## Stage 3 — responsive baseline (parallel with Stage 2, no code dependency on any of it)

### PR 7: shared breakpoints in `base.css`
- The rules themselves; no per-page verification yet.
- Tests: `rps_lint`/existing suites stay green (CSS-only).

### PR 8-11: per-page verification, batched by the app's existing 6 home-nav section groupings
- Four PRs (roughly 11-12 pages each, following the nav's own existing groupings rather than an
  arbitrary split), each resizing every page in its batch to ~half a 1080p monitor's width and fixing
  any real overflow/collision found — not just re-asserting the shared CSS applies.
- `part.html`/`procedure.html`/`torque.html`/`jobcard.html`/`bench.html` go in whichever batch they
  naturally fall into, but land **first** within their batch since A2 (Stage 4) depends on them being
  done.
- Tests: manual resize check per page, called out per PR (not automatable in this test suite).
- Depends on PR 7 only.

## Stage 4 — the original phase-1 slice + A2 (depend on Stage 1-3 pieces, not each other)

### PR 12: A1 — home nav pop-out links
- Depends on PR 5 (`VW.windows`).

### PR 13: D — live-synced Bench across tabs
- Promotes `bench.html`'s local `get()`/`put()` into `shared.js`, wires through `VW.channel`.
- Depends on PR 1 only.

### PR 14: A2 — per-page pop-out control
- `popoutControl()` helper in `shared.js`; adopted first on `part.html`/`procedure.html`/
  `torque.html`/`jobcard.html`/`bench.html` (whichever of PRs 8-11 covers them must be merged first).
- Depends on PR 5 (`VW.windows`) and the relevant page(s) already having their responsive pass.

## Stage 5 — B, F, C, G (each depends on specific Stage 1-4 pieces, mostly independent of each other)

### PR 15: B — curated workspace launcher
- Launch buttons on `jobcard.html` (→ procedure+torque+part) and `solve.html` (→
  troubleshoot+procedure+locate), each calling `VW.workspace.create()` + `VW.windows.open()` in
  sequence with shared part/vehicle context.
- Tests: automated assertion that each button's item list matches the spec; manual PR note for the
  actual multi-window launch behavior end-to-end.
- Depends on PR 2 (`VW.workspace` CRUD), PR 5 (`VW.windows`), PR 14 (A2 — the launching pages need
  their own pop-out context first).

### PR 16: F — save & reopen named workspaces
- New `workspaces.html` (or a `bench.html` section): list/save/name/reopen, using PR 3's
  export/import for the `/handover` hand-off.
- Tests: automated for the list/save/reopen data flow (built on PR 2/3's already-tested primitives);
  manual PR note for the actual `/handover` hand-off round-trip.
- Depends on PR 3 (export/import) and PR 15 (B — needs something worth naming/saving to exist first).

### PR 17: C — screen-aware placement
- Feature-detected `getScreenDetails()` extension to `VW.windows.open()`; permission requested only
  at the moment a placement is attempted; silent, correct fallback everywhere unsupported/denied.
- Tests: automated for the feature-detection/fallback branch (runs correctly on this project's
  non-multi-monitor CI); the actual placement behavior is **only** verifiable by a human on a real
  multi-monitor machine — stated plainly in the PR, not glossed over.
- Depends on PR 6 (`VW.windows` layout handling).

### PR 18: G — kiosk/second-screen reference view
- New minimal server route + template, reusing existing `viewer_kiosk` styling primitives; opened via
  `VW.windows.open()`, preferring a different screen than the request's origin when PR 17's placement
  is available.
- Tests: automated route/markup assertion for the new page; manual PR note for the actual
  second-screen placement behavior (same real-hardware caveat as PR 17).
- Depends on PR 5 (`VW.windows`) at minimum, PR 17 for the placement preference (degrades cleanly
  without it — can land before PR 17 if sequencing needs it to).

## Stage 6 — bleeding-edge capabilities & future-proofing (additive; does not change PRs 1-18)

Each PR here layers onto an already-planned or already-built piece rather than replacing it — the
public API surface of `VW.channel`/`VW.workspace`/`VW.windows` stays exactly what PRs 1/2/5
established.

### PR 19: `VW.capabilities` — centralized feature-detection + tier registry
- `{tier, broadcastChannel, windowPlacement, wakeLock, pictureInPicture, fileSystemAccess,
  webLocks, indexedDB}`, computed once, reading the existing `rps.js` tier plus raw
  `typeof`/`"x" in window` checks, AND-ed together.
- Tests: automated — given a mocked tier and mocked global presence/absence of each API, assert the
  resulting object shape. No real browser capability needed to test the *logic*.
- Depends on nothing (could have been built alongside PR 1; built now since PR 1 already shipped).
  PRs 20-24 depend on this; PRs 1/2/5 are NOT retrofitted to depend on it (their existing contracts
  stay stable — a later cleanup PR, not part of this plan, could have them read it too).

### PR 20: `VW.locks` — Web Locks API wrapper
- `VW.locks.withLock(name, fn)`; falls back to a best-effort in-memory single-tab lock on
  `lite`/`legacy` tier or where `navigator.locks` is absent.
- Tests: automated for both the real-API and fallback code paths (mockable — `navigator.locks` can
  be stubbed in the same vm-context style PR 1's tests already use).
- Depends on PR 19 (`VW.capabilities.webLocks`).

### PR 21: `VW.workspace` — IndexedDB storage migration
- Swaps the storage backing PR 2 built (`localStorage` under `viewer_workspaces`) for IndexedDB,
  keeping `create/list/get/touch`'s public contract byte-for-byte identical — nothing above this
  layer changes.
- Tests: the exact same test suite PR 2 wrote against the new backing (proves the contract really
  didn't change), plus a new large-payload case that would have failed against the old
  `localStorage` quota.
- Depends on PR 2 (already complete) and PR 19 (`VW.capabilities.indexedDB` gates whether this
  backing is used at all — `lite`/`legacy` tier keeps the original `localStorage` path, since
  IndexedDB's async overhead isn't worth it on already-constrained hardware).

### PR 22: `VW.workspace` — schema-versioned saved data
- Adds `schemaVersion` to the stored record shape; a migration-or-clean-refusal path for a version
  the running code doesn't recognize (see the spec's edge cases).
- Tests: automated — a deliberately old-shaped fixture record, assert clean migration or clean
  refusal, never silent misinterpretation.
- Depends on PR 2 (already complete).

### PR 23: `VW.workspace` — File System Access API for export/import
- A real native Save/Open dialog (and write-back-in-place) where `VW.capabilities.fileSystemAccess`
  is true; the existing blob/`<a download>` path (built in the original PR 3) stays as the universal
  fallback, never removed.
- Tests: automated for the fallback path (already covered by PR 3's tests); manual PR note for the
  real native-dialog path, since a file picker cannot be driven headlessly in this test suite.
- Depends on PR 3 (export/import — not yet built as of this stage's authoring) and PR 19.

### PR 24: G — Document Picture-in-Picture + Wake Lock
- `documentPictureInPicture.requestWindow()` as G's primary mechanism where
  `VW.capabilities.pictureInPicture` is true; `VW.windows.open()`'s plain second-window path
  otherwise (built in the original PR 18). `navigator.wakeLock` requested for that window's lifetime
  where `VW.capabilities.wakeLock` is true.
- Tests: automated for capability-gating/fallback logic; manual PR note for real PiP/wake-lock
  behavior (added to the new manual QA checklist below).
- Depends on PR 18 (G's original build — not yet built as of this stage's authoring) and PR 19.

### PR 25: mirror workspaces into the server-side backup vault
- A new, opt-in server route (Python, alongside the existing `features/`) accepting the current
  workspace list and folding it into the next regular `safeguard.snapshot()` call.
- Tests: automated — a real snapshot call, assert the mirrored workspace data is present in the
  resulting manifest, matching how `test_backupdb.py`/the restore-drill tests already verify
  `safeguard.py` behavior.
- Depends on PR 2 (already complete) for something real to mirror.

### New standing document: `docs/MULTI-WINDOW-MANUAL-QA.md`
Written once (as part of PR 17 or PR 24, whichever lands first) and kept current after: the short,
real checklist for exactly what this project's CI cannot verify itself — C's placement and PR 24's
Picture-in-Picture/Wake-Lock behavior on real multi-monitor hardware, and the RPS-tier capability
gating actually suppressing the right features on a real lite/legacy-classified machine. Run once per
release, the same standing-ritual way `VERIFY.bat` already is.

## What's still not in this plan

**E** (in-window split view), **cross-window notifications**, and **a window/tab manager overview
page** — all explicitly discussed and declined. **H** (compare view — two near-identical parts or
procedure revisions open side by side with synchronized scroll) is documented in the design spec as a
real, well-specified direction and a strong candidate for the *next* plan, but is not part of this
one. An **installable PWA app shell** is documented in the design spec as an endorsed future
direction — deliberately not scheduled here; if it's ever picked up, `VW.channel`'s public contract
is designed to accept a Service-Worker-backed transport as a third option without any caller change.

## Verification discipline (applies to every PR above, unchanged from the original plan)

- Branch per PR, never commit to `main` directly.
- Real CHANGELOG.md entry + VERSION bump per PR.
- HANDOFF-NOTE.md / PROJECT-SUMMARY.md / MASTER-RECONCILIATION.md kept in sync.
- `ITERATION-SNAPSHOTS.md`/`ITERATION-DASHBOARD.html` regenerated after each merge.
- CI green (ubuntu 3.12/3.13/3.14 + windows) before merge.
- Every "tested" claim backed by a real command's real output; every manual-only check (there are
  many more of them at this scope — live sync, window dedup, layout restore, C/G's real-hardware
  placement, 46 pages' worth of resize checks) stated as manual explicitly, never implied as
  automated when it isn't.
