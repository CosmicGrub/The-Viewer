# Multi-window / multi-tab support — design spec

**Date:** 2026-09-03 (revised twice: foundation layer added, then widened+deepened to near-full scope)
**Status:** approved for planning — this is now a large, multi-stage initiative, not a quick feature

## Motivation

THE VIEWER is a 46-page, single-server, single-origin app — every page already opens in a new tab
for free via ctrl/middle-click, since navigation is real `<a href>` links throughout, not JS-driven
in-place routing. What's missing isn't the *capability*, it's making it **discoverable, coordinated,
fast, and genuinely well-built** for a technician working at a bench with two (or more) monitors.

This spec went through two expansions after the initial minimal slice: first to add real,
reusable foundation components instead of one-off code; then, explicitly, to build those components
**deep** (not minimally) and pull most of the originally-deferred advanced directions into **active**
scope rather than leaving them for later. Only two directions stay out of this plan: **E** (in-window
split view) and two brand-new ideas raised and declined during scoping (cross-window notifications, a
window/tab manager overview page) — all three remain available for a future pass, not ruled out.

## Design priorities (govern every decision below, unchanged from the first expansion)

1. **Real-time sync speed** — `BroadcastChannel` primary transport, `storage`-event fallback.
2. **Snappy UI/interaction** — one window-opening path, named-window reuse, instant toast feedback.
3. **Adaptive layout** — a real, verified responsive baseline (zero width-based breakpoints exist in
   `base.css` today), now audited across **all 46 pages**, not a sample of five.

## Scope

### Foundation (deep, not minimal)

1. **`VW.channel`** — cross-window pub/sub, `BroadcastChannel` primary + `storage`-event fallback,
   now built with:
   - **Ordering:** every published message carries a monotonic per-channel sequence number, so a
     subscriber can detect and discard an out-of-order delivery (matters most on the `storage`
     fallback path, where delivery order across tabs isn't otherwise guaranteed).
   - **Larger payloads:** `BroadcastChannel` has no meaningful size limit; the `storage` fallback
     does (bound by `localStorage`'s ~5-10MB origin quota, shared with everything else already
     stored there) — the fallback path gets an explicit size guard that fails loudly (a clear error,
     not silent truncation) rather than letting a large payload corrupt a shared key.
   - **Schema versioning:** every envelope carries a `v` field; a subscriber on an older/newer
     version of the code can detect a mismatch and ignore the message cleanly instead of crashing
     on an unexpected shape — protects a future feature from ever needing every open tab to be on
     identical code just to interoperate.
2. **Responsive baseline — all 46 pages.** Every page gets the shared breakpoints from `base.css`
   plus a real by-hand verification pass at roughly half a 1080p monitor's width, batched into
   several PRs (see Plan) rather than one large one, using the app's own existing 6 home-nav section
   groupings as the natural batch boundary.
3. **`VW.workspace`** — data model + API, now with:
   - **Export/import.** A workspace serializes to a shareable form — a URL query-string for a quick
     hand-off, and a downloadable `.json` for a durable one — and deserializes back via a paste-URL
     or file-upload path. This is what makes **F** (below) actually useful across a shift change,
     not just within one browser session.
   - **Templates.** A small built-in library of preset workspace shapes for common tasks (e.g. a
     "PMCS" preset opening `pmcs.html` + `readiness.html`; an "NSN lookup" preset opening
     `decode.html` + `locate.html` + `partdiff.html`) — a starting point a technician can launch
     from immediately, not just an empty ad-hoc list.
4. **`VW.windows`** — window-management helper, now with:
   - **Layout capture.** Each window `VW.windows.open()` tracks records its `screenX`/`screenY`/
     `outerWidth`/`outerHeight` (readable cross-window since everything is same-origin) into the
     open-window registry.
   - **Layout restore — explicitly a user-triggered action, not automatic.** A real constraint
     surfaced while deepening this: a web page cannot run code "on app launch" unprompted — there is
     no hook for that. "Restore my layout" is a button (on the home page, or wherever a saved
     workspace lives) that reopens each tracked window via `window.open(url, name,
     "left=…,top=…,width=…,height=…")`, not something that happens silently when the browser starts.
     Documenting this now so it's never oversold later: the feature is "one click restores where
     everything was," not "it remembers automatically."

### Active features (moved from deferred into this plan)

5. **A1 — home nav pop-out links** (unchanged from the original slice).
6. **D — live-synced Bench across tabs** (unchanged from the original slice, now the first real
   consumer of the deepened `VW.channel`).
7. **A2 — per-page pop-out control.** Incremental per-page adoption via a `shared.js`
   `popoutControl()` helper, starting with `part.html`/`procedure.html`/`torque.html`/`jobcard.html`/
   `bench.html` — the same five pages already prioritized for the original responsive pass, and the
   direct prerequisite for B below (a task page needs its own pop-out affordance before it can
   sensibly launch a *set* of pages).
8. **B — curated workspace launcher.** A button on task-shaped pages calls `VW.workspace.create()`
   with a curated item list and opens them via `VW.windows.open()`. Two real launch sets to start:
   - **Work Order** (`jobcard.html`) → `procedure.html` + `torque.html` + `part.html`.
   - **Solve It** (`solve.html`) → `troubleshoot.html` + `procedure.html` + `locate.html`.
   Each pre-filled with the same part/vehicle context the launching page already has.
9. **F — save & reopen named workspaces.** A UI over `VW.workspace` — likely its own small page
   (`workspaces.html`) or a section of `bench.html` — listing saved workspaces, letting one be
   named/saved/reopened, and using the export/import from item 3 to hand a workspace to the next
   shift through the existing `/handover` page rather than re-explaining what was open.
10. **C — screen-aware placement.** Feature-detected via the Window Management API
    (`getScreenDetails()`), which is **Chromium-only and requires an explicit user permission
    grant** — this must degrade to normal (non-placed) window opening everywhere else, silently and
    correctly, not as a broken/half-working state. Where available and granted, `VW.windows.open()`
    accepts a target-screen hint and computes real `left`/`top` coordinates within that screen's
    reported bounds.
11. **G — "send to second screen" kiosk/reference view.** A new, lightweight route rendering a
    stripped-down, large-text, read-only version of a page's key content (reusing the existing
    glove/kiosk-mode styling primitives already in the codebase), opened via `VW.windows.open()` and,
    where C is available, preferentially placed on a *different* screen than the one the request came
    from.

### Still deferred (explicitly, not by omission)

- **E — in-window split view.** Benefits directly from the all-46-page responsive baseline whenever
  it's picked up; not part of this plan.
- **Cross-window notifications** (background job completions pushed to every open window) and **a
  window/tab manager overview page** — both raised during scoping and explicitly declined for this
  round. Both would ride `VW.channel`/`VW.windows` cleanly if picked up later.

## Architecture

### `VW.channel`
```
VW.channel.publish(name, data)         // data may include any JSON-serializable payload
VW.channel.subscribe(name, fn)         // fn(data, meta) -- meta: {seq, v}
```
`BroadcastChannel` primary; `storage`-event fallback with a size guard and the same `{seq, v, name,
data}` envelope shape either way, so a subscriber never needs to know which transport delivered a
message.

### `VW.workspace`
```
{ id, name, items: [{page, params}], created, lastOpened, source: "manual"|"template" }
VW.workspace.create(name, items) -> id
VW.workspace.list() / .get(id) / .touch(id)
VW.workspace.exportUrl(id) -> string      // shareable query-string form
VW.workspace.exportFile(id) -> Blob       // downloadable .json
VW.workspace.importUrl(qs) -> id
VW.workspace.importFile(blob) -> id
VW.workspace.templates() -> [{name, items}, ...]   // built-in presets, not user data
```
Stored under `viewer_workspaces`, synced automatically across tabs via `VW.channel`.

### `VW.windows`
```
VW.windows.open(url, opts)   // opts: {name, screen?} -- name enables reuse; screen is a hint,
                              // ignored gracefully wherever C's placement API isn't available
VW.windows.registry() -> [{name, url, screenX, screenY, outerWidth, outerHeight}, ...]
VW.windows.restoreLayout(entries)   // user-triggered only, reopens each entry at its recorded bounds
```

### C's extension to `VW.windows`
Feature-detected at call time (`"getScreenDetails" in window`), permission requested only when a
placement is actually attempted (never pre-emptively on page load), and any denial or absence falls
back to `VW.windows.open()`'s normal behavior with no error surfaced to the user — placement is a
bonus, never a requirement to open a window at all.

### G's kiosk/reference route
A new server route (e.g. `/kiosk?page=torque&…`) rendering a minimal, large-text template built from
the same styling primitives `viewer_kiosk` mode already uses elsewhere, read-only, no interactive
controls beyond what's needed to read the content from a few feet away.

## Edge cases (additions from the deepened scope)

- **`VW.channel` schema mismatch:** an older/newer tab silently ignores a message whose `v` it
  doesn't recognize, rather than throwing.
- **Oversized payload on the `storage` fallback path:** fails loudly at the publish call site (a
  thrown error the caller must handle), never silently truncated or dropped.
- **Workspace import of a malformed/tampered file:** validated against the expected shape before
  being written to `viewer_workspaces`; rejected with a clear message on any mismatch, not merged in
  partially.
- **Layout restore where a saved window's recorded screen no longer exists** (monitor unplugged
  since it was saved): falls back to the browser's own default placement for that window rather than
  failing the whole restore.
- **C's permission denied or API absent:** every call site already assumes this is the common case,
  not the exception — no separate "unsupported browser" messaging needed, it just behaves like
  `VW.windows.open()` without a screen hint.
- Everything already named in the first revision (popup-blocker non-issue, kiosk tap-target sizing,
  last-write-wins Bench conflicts, discarded background tabs) still applies unchanged.

## Testing

Same honest split as before, now larger in surface area:

- **Fully automatable:** every markup-level change (A1, A2 adoption, home-nav links); every pure
  data-shape/logic function (`VW.workspace` CRUD + export/import serialization round-trips —
  genuinely testable without a second browser context; `VW.channel`'s envelope construction and
  sequence-number/version logic in isolation); `rps_lint`/ES5 compliance on every touched file.
- **Manual, called out explicitly per PR, not glossed over:** live cross-tab delivery (`VW.channel`,
  D), named-window reuse (`VW.windows`), layout capture/restore round-tripping real window bounds,
  B's curated launches actually opening the right set with shared context, C's placement behavior on
  a real multi-monitor machine (this project's CI runners are not multi-monitor — this can only ever
  be a manual, human-run check), and the all-46-page responsive resize pass.

## Files touched (grows substantially with this scope)

- `engine/ui/shared.js` — `VW.channel`, `VW.workspace`, `VW.windows`, `VW.windows`'s C-extension,
  all under the existing strict ES5/RPS-lint constraint.
- `engine/ui/base.css` — responsive baseline breakpoints.
- All 46 `engine/ui/*.html` pages — responsive verification pass (batched).
- `engine/ui/index.html` — A1.
- `engine/ui/bench.html` — D.
- `engine/ui/part.html`, `procedure.html`, `torque.html`, `jobcard.html`, `bench.html` — A2 adoption
  (first wave).
- `engine/ui/jobcard.html`, `solve.html` — B's launch buttons.
- New `engine/ui/workspaces.html` (or a `bench.html` section) — F's UI.
- `engine/ui/handover.html` — F's handoff hook.
- New server route + template for G.
- `engine/tests/test_*.py` — new/extended coverage for every automatable piece above.

## Rollout order

See the companion plan document
(`docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md`) for the full PR-by-PR sequencing —
this spec defines *what*, the plan defines *in what order and how verified*.
