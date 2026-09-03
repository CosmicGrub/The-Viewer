# Multi-window / multi-tab support — design spec

**Date:** 2026-09-03
**Status:** approved for planning (phase 1 only — see Scope)

## Motivation

THE VIEWER is a 46-page, single-server, single-origin app — every page already opens in a new tab
for free via ctrl/middle-click, since navigation is real `<a href>` links throughout, not JS-driven
in-place routing. What's missing isn't the *capability*, it's making it **discoverable and
coordinated**: a technician working at a bench with two monitors has no obvious, deliberate way to
say "open this section on my other screen" or have state (like a saved-parts list) stay in sync
between windows without a manual refresh.

This spec covers **phase 1 only**, arrived at through a brainstorming session that surfaced seven
candidate directions (see "Deferred" below). Phase 1 is deliberately the cheapest, lowest-risk
slice: two pieces that need no new UI paradigm and no browser capability this project can't already
rely on.

## Scope

**In scope (phase 1), in build order:**

1. **A1 — pop-out links on the home page nav.** Every section link in `index.html`'s nav list gets
   an appended ↗ that opens that section in a new tab/window.
2. **D — live-synced "My Bench" across tabs.** An item added to the Bench in one tab appears in any
   other open tab immediately, no reload.
3. **A2 — pop-out control on individual pages.** A per-page affordance (not just the home nav) to
   keep the *current* page open in its own window while continuing to navigate elsewhere.

A1 and D ship together as the first, smallest slice; A2 follows as a second, larger slice (it
touches per-page markup incrementally rather than one file). **The implementation plan that follows
this spec covers A1 + D only** — A2 is designed here for continuity but gets its own plan once A1 +
D have shipped, since "which pages adopt it, in what order" is itself a decision worth revisiting
after the first slice is live.

**Explicitly deferred, not in this spec** (from the same brainstorming session — none of this is
foreclosed by phase 1; A1's pop-out link is a building block B will reuse later):

- **B — curated workspace launcher** (one button opens a related set of pages together, e.g. job
  card + procedure + torque, same part/vehicle context threaded through each).
- **C — screen-aware placement** (auto-snapping sections to specific monitors). Gated on the browser
  Window Management API, which is Chromium-only and permission-gated — this app deliberately still
  supports older/low-spec browsers (the RPS/ES5 compatibility mode most pages already run under), so
  this must land as a progressive enhancement later, never a requirement.
- **E — in-window split view** (two panes in one window, no second monitor needed).
- **F — save & reopen a named workspace**, including handoff through the existing `/handover` page.
  Builds on B.
- **G — "send to second screen" kiosk/reference view**, reusing the existing glove/kiosk mode
  (`viewer_kiosk` in `localStorage`) for a stripped-down, large-text read-only page.

## Design

### A1 — home nav pop-out links

Pure HTML, no JS. Every `<a href="/...">` in `index.html`'s section list gets an adjacent ↗
appended with `target="_blank" rel="noopener"` (matching the `rel="noopener"` convention already
used elsewhere in this file for search-result links). No behavior change to the existing link
itself — the ↗ is an additional, explicit affordance alongside it, not a replacement.

Works identically in every browser, including RPS/ES5-mode ones, since it's static markup.

### D — live-synced Bench across tabs

`viewer_bench` already lives in `localStorage` (currently owned by `bench.html`'s own `get()`/
`put()`), already shared across every tab on the origin. The missing piece is notifying other open
tabs when it changes.

- **Promote** `bench.html`'s `get()`/`put()` helpers into `shared.js` as the one canonical
  Bench accessor (currently `bench.html` is the only place that knows the key name and shape).
- **Add** `VW.onBenchChange(fn)` to `shared.js`, wrapping the native `storage` event, filtered to
  `event.key === "viewer_bench"`. The `storage` event fires natively on every *other* tab when
  `localStorage` changes (never on the tab that made the change, so there's no echo to guard
  against), and it's supported by every browser this project targets — no `BroadcastChannel`, no
  polling.
- `bench.html` (the only page rendering the Bench list today) re-renders from the new value the
  moment the event fires, no reload. `VW.onBenchChange()` is written as a general-purpose
  subscription, so a future Bench-count badge elsewhere could use it too, but no such badge exists
  yet and adding one is not part of this phase.
- **Conflict handling:** last-write-wins, no merge — matches how `localStorage` already behaves
  today. Explicitly not solving concurrent-edit conflicts in phase 1.

### A2 — per-page pop-out control

There is no shared header/toolbar markup across the 46 pages today (each hand-rolls its own), so
this can't be a single template edit. Implemented as a small `shared.js`-provided helper (e.g.
`VW.popoutControl()`) that an adopting page calls once to render a "keep this page open" control —
pages opt in incrementally as they already do with `shared.js`'s other helpers (~14+ pages have
adopted it so far), rather than all 46 changing at once.

**Kiosk/glove mode requirement:** the tap target must be the full control row, not just the ↗
glyph's own tiny bounding box — kiosk mode exists specifically for larger touch targets, and an
icon-sized-only hit area would undercut that.

## Testing

This project's test suite (`verify_all.py`, `rps_lint.py`) is entirely Python-stdlib hitting HTTP
routes or doing static ES5 scans — there is no real in-browser JS test runner anywhere in this repo.

- **A1** is fully covered by automation: it's static markup, so a route/HTML assertion (e.g. every
  home-nav `<a>` has an adjacent `target="_blank" rel="noopener"` pop-out link) is a real,
  meaningful automated test.
- **D**'s *shape* is covered by automation: `shared.js` still passes `rps_lint` (strict ES5), and
  `VW.onBenchChange`/promoted `get()`/`put()` exist with the right signatures.
- **D**'s actual live cross-tab behavior is **not** something this test suite can honestly exercise
  without adding real browser automation, which is out of scope for what this feature justifies.
  Verified manually instead: open `bench.html` in two tabs, add an item in one, confirm the other
  updates without a reload — called out explicitly in the PR rather than claimed as automated when
  it isn't.
- **A2** gets the same treatment as A1 per adopting page (a markup/route assertion), plus a manual
  kiosk-mode tap-target check on at least one adopting page.

## Files touched

- `engine/ui/index.html` — A1 (nav link markup).
- `engine/ui/shared.js` — D (promoted Bench accessor + `onBenchChange`), A2 (`popoutControl()`
  helper), both under the existing strict-ES5/RPS-lint constraint this file is already held to.
- `engine/ui/bench.html` — D (switches to the promoted `shared.js` accessor instead of its own
  local `get()`/`put()`).
- Whichever pages adopt A2's `popoutControl()` — incremental, not a single commit.
- A new or extended `engine/tests/test_*.py` covering A1's markup and D's `shared.js` shape.

## Rollout order

1. A1 (home nav pop-out links) + D (live Bench sync) — ship together, smallest slice.
2. A2 (per-page pop-out control) — second slice, rolled out incrementally per adopting page.
3. B/C/E/F/G remain open for a future brainstorming pass, not committed to here.
