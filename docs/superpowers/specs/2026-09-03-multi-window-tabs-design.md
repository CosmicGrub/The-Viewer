# Multi-window / multi-tab support — design spec

**Date:** 2026-09-03 (revised: scope expanded to a real foundation layer)
**Status:** approved for planning (foundation + phase-1 features — see Scope)

## Motivation

THE VIEWER is a 46-page, single-server, single-origin app — every page already opens in a new tab
for free via ctrl/middle-click, since navigation is real `<a href>` links throughout, not JS-driven
in-place routing. What's missing isn't the *capability*, it's making it **discoverable, coordinated,
and fast** for a technician working at a bench with two (or more) monitors.

This spec was expanded from an initial minimal-slice plan after a scope review: rather than bolting
one-off code onto each individual feature as it's requested, this phase builds **real, reusable
components now** — a cross-window sync layer, a formal Workspace model, a window-management helper,
and a responsive layout baseline — so that every advanced direction from the original brainstorm
becomes a fast follow-on instead of a fresh design problem each time. Only two user-visible features
ship in this phase (A1, D); everything else in "Foundation" below is infrastructure with no UI yet.

## Design priorities (govern every decision below)

Three things, all requested as equally non-negotiable — not aspirations, each has a concrete
technical commitment:

1. **Real-time sync speed.** Cross-window state changes should feel instant, not "eventually
   consistent." Commitment: the sync layer uses `BroadcastChannel` as its primary transport
   (sub-millisecond, purpose-built for this, no serialization round-trip through `localStorage`)
   with the `storage` event as an automatic fallback only where `BroadcastChannel` isn't available
   (older/RPS-mode browsers). Every consumer (Bench sync today, workspaces/kiosk-push later) rides
   the same fast path without knowing which transport is under it.
2. **Snappy UI/interaction.** Opening, arranging, and switching windows must never feel janky or
   duplicate-spawn. Commitment: all window-opening goes through one helper that (a) reuses an
   already-open named window instead of spawning a duplicate on a repeat click, and (b) gives
   immediate visual confirmation (a toast, already a pattern this codebase has via `shared.js`) the
   instant a window opens — no waiting to *see* the new window to know the click registered.
3. **Adaptive layout.** Popped-out pages are often resized to a fraction of a screen (half a
   monitor, a corner), not full-screen — they need to hold up there. Reality check: `base.css` has
   exactly **zero** width-based responsive breakpoints today (its four `@media` rules are
   `pointer:coarse`, `print`, and `prefers-reduced-motion` — nothing about narrow windows), and of
   the five pages most likely to get popped out first, three have one basic breakpoint and two have
   none. Commitment: a small, shared set of real breakpoints goes into `base.css` as part of the
   foundation, verified first on exactly those five pages (see Scope) rather than promised across
   all 46 at once.

## Scope

### Foundation (this phase, infrastructure only — no new UI beyond A1 + D)

1. **Cross-window sync layer** (`VW.channel`) — a generalized publish/subscribe mechanism, not a
   one-off Bench listener. `BroadcastChannel` primary, `storage`-event fallback (design priority 1).
2. **Workspace data model + minimal API** (`VW.workspace`) — the formal shape a future curated
   launcher (B) and saved/named workspaces (F) will both need, built and unit-testable now even
   though no UI calls it yet.
3. **Window-management helper** (`VW.windows.open()`) — named-window reuse, an open-window registry,
   instant toast feedback (design priority 2). A1 and D's own launch points are the first real
   callers; A2/B build on it directly rather than reinventing `window.open()` handling.
4. **Responsive baseline** — shared breakpoints in `base.css`, verified on `part.html`,
   `procedure.html`, `torque.html`, `jobcard.html`, `bench.html` (design priority 3).

### Phase-1 features (ship this phase, built on the foundation above)

5. **A1 — pop-out links on the home page nav.** Every section link in `index.html`'s nav list gets
   an appended ↗ that opens that section in a new tab/window via `VW.windows.open()`.
6. **D — live-synced "My Bench" across tabs.** An item added to the Bench in one tab appears in any
   other open tab immediately, no reload — implemented as the first real consumer of `VW.channel`,
   not a bespoke `storage`-event listener.

**A1 and D still ship together as the first working slice.** The difference from the original,
narrower version of this spec is *what they're built on*, not what they visibly do.

### Deferred — not built this phase, but the foundation is aimed squarely at them

- **A2 — per-page pop-out control**, using `VW.windows.open()` + a `popoutControl()` helper,
  incrementally adopted per page (no shared header markup exists across the 46 pages today, so this
  can't be a single template edit).
- **B — curated workspace launcher**, built directly on `VW.workspace` + `VW.windows.open()` once it
  exists — this is the direction the foundation most obviously accelerates.
- **C — screen-aware placement.** Still gated on the browser Window Management API (Chromium-only,
  permission-gated) — this app deliberately still supports older/low-spec browsers (RPS/ES5 mode
  most pages run under), so this stays a progressive enhancement layered onto `VW.windows.open()`
  later, never a requirement.
- **E — in-window split view**, benefits directly from the responsive baseline (a two-pane layout is
  just two narrow viewports side by side).
- **F — save & reopen a named workspace**, including handoff through the existing `/handover` page —
  a thin UI layer over `VW.workspace`, once B exists to launch from.
- **G — "send to second screen" kiosk/reference view**, reusing the existing glove/kiosk mode
  (`viewer_kiosk` in `localStorage`) — becomes a `VW.channel`-pushed page once the sync layer exists.

## Architecture — the foundation components

### `VW.channel` — cross-window sync layer

```
VW.channel.publish(name, data)     // broadcast to every OTHER tab/window on this origin
VW.channel.subscribe(name, fn)     // fn(data) called whenever `name` is published elsewhere
```

Internally: tries `new BroadcastChannel("viewer:" + name)` first; if `BroadcastChannel` is
undefined (older/RPS-mode browsers), falls back to writing a small envelope
(`{name, data, ts}`) to a single `localStorage` key and listening for the native `storage` event,
filtered by `name` — the exact mechanism the original D design used, now generalized instead of
Bench-specific. Callers never know or care which transport is active.

### `VW.workspace` — data model + API (no UI consumer yet)

```
{ id, name, items: [{page, params}], created, lastOpened }
```

```
VW.workspace.create(name, items) -> id
VW.workspace.list() -> [workspace, ...]
VW.workspace.get(id) -> workspace | null
VW.workspace.touch(id)             // updates lastOpened
```

Stored under a new `viewer_workspaces` key, kept in sync across tabs automatically by riding
`VW.channel` — a workspace created in one tab is immediately visible to `VW.workspace.list()` in
another, for free, once B's UI exists to call it.

### `VW.windows` — window-management helper

```
VW.windows.open(url, opts)   // opts: {name, ...} -- opts.name makes repeat calls REUSE the
                              // same window instead of spawning a new one each click
```

Internally a thin wrapper over `window.open(url, name)` — passing the same `name` twice is already
how browsers reuse a window natively; this helper's job is making that the *default*, tracking what
it has opened (an in-memory registry per tab, broadcast via `VW.channel` so other tabs can eventually
show "3 windows open from this workspace"), and firing the existing `shared.js` toast the instant a
window opens or is refocused.

### Responsive baseline (`base.css`)

A small number of real, shared breakpoints (not per-page bespoke CSS) covering the layout patterns
already common across `part.html`/`procedure.html`/`torque.html`/`jobcard.html`/`bench.html` —
multi-column grids collapsing to single-column, sidebars stacking below content — verified by
actually resizing each of those five pages to roughly half a 1080p monitor's width, not just added
and assumed.

## Edge cases

- **`BroadcastChannel` unavailable:** falls back to the `storage`-event path automatically — same
  correctness, slightly higher latency, no functional gap.
- **Two tabs edit the same Bench item near-simultaneously:** last-write-wins, no merge — unchanged
  from the original D design, still the right call for phase 1.
- **Repeat-clicking a pop-out link:** `VW.windows.open()`'s named-window reuse means this refocuses
  the existing window rather than spawning a pile of duplicates.
- **Kiosk/glove mode tap targets:** the pop-out control's hit area is the full row, not just the ↗
  glyph — kiosk mode exists specifically for larger touch targets.
- **A backgrounded tab the browser has fully discarded** won't see a sync event until it's reloaded —
  true of both transports, not worth engineering around this phase.

## Testing

This project's test suite (`verify_all.py`, `rps_lint.py`) is entirely Python-stdlib hitting HTTP
routes or doing static ES5 scans — there is no real in-browser JS test runner anywhere in this repo.
That shapes what "tested" honestly means here:

- **Fully automatable:** A1's markup (every home-nav `<a>` has a pop-out link); `shared.js`/its new
  `VW.channel`, `VW.workspace`, `VW.windows` code still passes `rps_lint` (strict ES5) and exports
  the right function signatures; `VW.workspace`'s CRUD functions themselves (pure data-shape logic,
  no real cross-tab behavior) can get real unit-style assertions since they don't depend on a second
  browser context.
- **Not automatable without new infrastructure, so verified manually instead and called out as such
  in the PR:** actual live cross-tab behavior for `VW.channel`/D (open two tabs, change one, confirm
  the other updates with no reload) and `VW.windows.open()`'s named-window reuse (click a pop-out
  link twice, confirm one window, not two).
- **Responsive baseline:** verified by hand on the five named pages at roughly half-monitor width —
  not something the current test suite can screenshot-diff.

## Files touched

- `engine/ui/shared.js` — `VW.channel`, `VW.workspace`, `VW.windows`, all under the existing strict
  ES5/RPS-lint constraint this file is already held to.
- `engine/ui/base.css` — responsive baseline breakpoints.
- `engine/ui/index.html` — A1 (nav link markup, now calling `VW.windows.open()`).
- `engine/ui/bench.html` — D (switches to `VW.channel`-backed sync instead of a bespoke `storage`
  listener).
- `engine/ui/part.html`, `procedure.html`, `torque.html`, `jobcard.html` — responsive-baseline
  verification pass (CSS only, no behavior change).
- A new or extended `engine/tests/test_*.py` covering A1's markup, and the new `shared.js` exports'
  shape/signatures.

## Rollout order

1. **Foundation:** `VW.channel` → `VW.workspace` (data model only) → `VW.windows` → responsive
   baseline. Built in that order since each later piece can lean on the one before it (`VW.workspace`
   rides `VW.channel`; nothing here has a UI yet).
2. **A1 + D**, now built on top of the foundation — still the first user-visible slice.
3. **A2** (per-page pop-out control) — second slice, rolled out incrementally per adopting page.
4. **B, F** — curated workspace launcher and saved/named workspaces, the most direct beneficiaries
   of `VW.workspace` existing.
5. **C, G** — screen-aware placement and the kiosk/second-screen reference view, both progressive
   enhancements layered onto `VW.windows`/`VW.channel` once 1-4 are live.
6. **E** — in-window split view, whenever it's prioritized; benefits from the responsive baseline
   whenever it lands.
