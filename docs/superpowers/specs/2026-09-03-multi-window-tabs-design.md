# Multi-window / multi-tab support — design spec

**Date:** 2026-09-03 (revised three times: foundation layer added; widened+deepened to near-full
scope; then extended with bleeding-edge platform capabilities + a future-proofing architecture pass)
**Status:** approved for planning — a large, multi-stage initiative. PR 1 (`VW.channel`) is merged;
PR 2 (`VW.workspace` CRUD) and PR 5 (`VW.windows` core) are in progress as this revision lands.

## Motivation

THE VIEWER is a 46-page, single-server, single-origin app — every page already opens in a new tab
for free via ctrl/middle-click, since navigation is real `<a href>` links throughout, not JS-driven
in-place routing. What's missing isn't the *capability*, it's making it **discoverable, coordinated,
fast, genuinely well-built, and durable** for a technician working at a bench with two (or more)
monitors, on hardware that has to keep working for years, not just this quarter.

This spec has gone through three expansions: first to add real, reusable foundation components
instead of one-off code; then to build those components **deep** and pull most of the
originally-deferred advanced directions into **active** scope; then — explicitly, on request — to
add a set of forward-looking platform capabilities and a future-proofing architecture pass, with the
honest counterweight of naming where restraint matters (a low-spec-hardware guard, a shared-machine
security limitation) alongside the ambition. Only **E** (in-window split view) and two declined ideas
(cross-window notifications, a window/tab manager overview page) stay fully out of scope; everything
else either ships in the current 18-PR plan or is documented here as a real, named future direction.

## Design priorities (govern every decision below)

1. **Real-time sync speed** — `BroadcastChannel` primary transport, `storage`-event fallback.
2. **Snappy UI/interaction** — one window-opening path, named-window reuse, instant toast feedback.
3. **Adaptive layout** — a real, verified responsive baseline (zero width-based breakpoints exist in
   `base.css` today), audited across **all 46 pages**.
4. **Long-term durability** (added this revision) — every new capability added here is expected to
   still be readable, still degrade gracefully, and still make sense five years from now, on
   hardware that may not have changed. Concretely: schema-versioned data wherever anything gets
   *saved* (not just live messages), and every advanced browser API gated behind the capability
   ladder below rather than assumed present.

## Platform capability ladder (new architectural principle — governs every advanced feature below)

THE VIEWER already has a real, working three-tier hardware ladder: `rps.py`/`rps.js` classify the
running machine as **modern**, **lite**, or **legacy**, and the whole UI already adapts to that
(RPS/ES5 compatibility mode exists specifically for older, lower-spec field hardware). Rather than
inventing a parallel concept, every bleeding-edge capability this revision adds — Document
Picture-in-Picture, the Web Locks API, the File System Access API, screen-aware placement (C),
IndexedDB — is gated through that **same existing tier**, computed once and exposed as
`VW.capabilities` (see Architecture below):

- **modern tier**: every capability offered where the browser also supports it (tier and raw
  browser feature-detection are independent checks — both must pass).
- **lite tier**: the safe, broadly-supported layer only (`VW.channel`, `VW.workspace`,
  `VW.windows` core, A1/A2/D/B/F) — the newer placement/PiP/File-System-Access capabilities are not
  offered even if the browser happens to support them, since a "lite" classification already means
  this machine is resource-constrained and opening extra always-on-top windows or holding extra
  storage handles works against it.
- **legacy tier**: the RPS/ES5 baseline only — `storage`-event fallback, no advanced capability
  affordances shown in the UI at all.

This is the same reasoning already behind B needing a real guard: a curated multi-window launch that
helps a technician on modern hardware could be the thing that makes an older field laptop crawl.
Rather than B inventing its own check, B (and everything after it) just reads `VW.capabilities.tier`.

## Scope

### Foundation (deep, not minimal)

1. **`VW.channel`** *(PR 1 — merged)* — cross-window pub/sub, `BroadcastChannel` primary +
   `storage`-event fallback, with ordering (per-channel sequence numbers), an explicit size guard on
   the fallback path, and schema versioning (a `v` field on every envelope) — the model the newer
   "schema-version anything saved, not just sent" principle below extends.
2. **Responsive baseline — all 46 pages.** Shared breakpoints from `base.css` plus a real by-hand
   verification pass at roughly half a 1080p monitor's width, batched by the app's existing 6
   home-nav section groupings.
3. **`VW.workspace`** *(PR 2 — in progress: CRUD only; export/import + templates are PR 3/PR 4)* —
   data model + API: export/import (a URL query-string for a quick hand-off, a downloadable `.json`
   for a durable one) and a small built-in template library (a "PMCS" preset opening `pmcs.html` +
   `readiness.html`; an "NSN lookup" preset opening `decode.html` + `locate.html` + `partdiff.html`).
4. **`VW.windows`** *(PR 5 — in progress: open/reuse/toast core; layout capture/restore is PR 6)* —
   window-management helper: layout capture (`screenX`/`screenY`/`outerWidth`/`outerHeight` per
   tracked window) and a **user-triggered, not automatic** restore — a web page cannot run code "on
   app launch" unprompted, so "restore my layout" is a button, not silent magic.

### Active features (moved from deferred into this plan)

5. **A1 — home nav pop-out links** (unchanged from the original slice).
6. **D — live-synced Bench across tabs** (unchanged from the original slice, the first real consumer
   of `VW.channel`).
7. **A2 — per-page pop-out control.** Incremental adoption via a `shared.js` `popoutControl()`
   helper, starting with `part.html`/`procedure.html`/`torque.html`/`jobcard.html`/`bench.html`.
   **Addition this revision**: `popoutControl()` also registers itself as a command-palette entry
   through the existing `window.cmdkOpen` hook (`shared.js`'s footer nav already wires up Ctrl+K on
   every page) — "open in new window" becomes a keyboard-reachable action from day one, not a
   mouse-only affordance bolted on as an accessibility afterthought later. This directly continues
   this project's own accessibility work (the `[1.46.0]`/`[1.47.0]` contrast/focus-trap passes).
8. **B — curated workspace launcher.** Two real launch sets to start: **Work Order**
   (`jobcard.html`) → `procedure.html` + `torque.html` + `part.html`; **Solve It** (`solve.html`) →
   `troubleshoot.html` + `procedure.html` + `locate.html`. **Addition this revision**: B checks
   `VW.capabilities.tier` before launching — on the `lite`/`legacy` tier it either warns before
   opening multiple real windows, or defaults to suggesting E (in-window split view, once that
   exists) instead. This is a requirement, not a nice-to-have: the whole point of this feature is
   helping a technician, and it must not be the thing that makes their actual field machine crawl.
9. **F — save & reopen named workspaces.** A UI over `VW.workspace`, using the export/import from
   item 3 to hand a workspace to the next shift through the existing `/handover` page. **Addition
   this revision**: an **auto-checkpoint**, distinct from a deliberately named/saved workspace — the
   current open-window set is periodically (or on window-close) silently persisted as a recoverable
   "last session," so an unplanned restart (a real, not hypothetical, risk in this app's actual
   environment — a browser or OS crash mid-shift) can offer "restore your last N windows?" without
   the technician having had to think to save first.
10. **C — screen-aware placement.** Feature-detected via the Window Management API
    (`getScreenDetails()`) — Chromium-only, requires an explicit user permission grant, gated behind
    the capability ladder (modern tier only) — degrades silently and correctly everywhere else.
11. **G — "send to second screen" kiosk/reference view.** **Revised this pass**: the *primary*
    mechanism is now **Document Picture-in-Picture** where available (modern tier) — a genuinely
    cutting-edge (2023+), still-underused browser API that keeps a small floating window visible
    *above every other window and app*, not just above other browser tabs. For a torque spec or the
    current procedure step that needs to stay visible while a technician's hands are busy, that is a
    materially better fit than an ordinary second window, which can get buried under other
    applications. Falls back to a plain `VW.windows.open()` second window on any tier/browser
    without PiP support — the reference content itself is identical either way, only the window
    behavior differs. **Also added**: the Screen Wake Lock API (`navigator.wakeLock`) keeps that
    screen from sleeping mid-task, feature-detected and silently absent where unsupported — the same
    progressive-enhancement shape as everything else here.

### New this revision — **H — compare view**

Not on the original A–G list. This is a parts-catalog tool whose own stated purpose includes telling
apart parts that look identical but aren't (`partdiff.html`, "Look-Alike Parts") — the most
domain-specific use of multi-window support here isn't "open two things," it's **two near-identical
parts or two procedure revisions open side by side with scroll position genuinely synchronized
between them**, so a mismatch is visible instead of needing to be held in memory across two separate
windows. Built on `VW.channel` (a lightweight `scroll` sync topic between two windows opted into
comparison mode) and `VW.windows` (opening the pair together, similar in spirit to B's curated
launch but exactly two windows, explicitly paired). Documented here as a real, well-specified
direction — **not built in the current 18-PR plan**, a strong candidate for the next one.

### Still deferred (explicitly, not by omission)

- **E — in-window split view.** Benefits directly from the all-46-page responsive baseline whenever
  it's picked up.
- **Cross-window notifications** and **a window/tab manager overview page** — both raised and
  explicitly declined during scoping. Both would ride `VW.channel`/`VW.windows` cleanly later.

## Bleeding-edge capabilities & future-proofing architecture (new this revision)

Added on explicit request to keep this app from looking dated in a few years, weighed against the
same honesty this whole spec has tried to hold throughout: every item below is a **real, currently
shipping (if newer) browser capability**, not speculative technology, and every one is gated by the
capability ladder above rather than assumed universal. These are **additive PRs appended to the plan
(Stage 6)** — they do not change the scope or timeline of the already-in-progress PR 1/2/5.

- **`VW.capabilities`** — a single, centralized feature-detection registry computed once at load
  (`{tier, broadcastChannel, windowPlacement, wakeLock, pictureInPicture, fileSystemAccess,
  webLocks, indexedDB}`), combining the RPS tier with raw `typeof`/`"x" in window` checks. Every
  feature above reads this ONE source of truth instead of each reimplementing its own detection —
  the practical argument: as more of these get added across an 18+ PR plan, inconsistent ad-hoc
  detection is exactly the kind of thing that quietly rots. Logically this belongs alongside `VW.
  channel` in the foundation; added now as its own PR since `VW.channel`/`VW.workspace`/`VW.windows`
  are already in flight — later cleanup can have them read it too, without changing their contracts.
- **`VW.locks`** — a thin wrapper over the Web Locks API (`navigator.locks`), a genuinely elegant
  and still under-known piece of browser platform maturity: a real cross-tab mutex that doesn't need
  a `VW.channel` round-trip for simple "only one tab should do X right now" coordination. This is the
  client-side mirror of a pattern already in this codebase server-side (`_INGEST_LOCK` in
  `features/ingest_feature.py` — one job at a time, serialized under a lock) — not a foreign concept,
  just the same idea moved to the browser. First real consumer: guarding F's "save" action so two
  tabs editing the same named workspace at once don't race each other.
- **IndexedDB for `VW.workspace`/Bench storage** — `localStorage` is synchronous, string-only, and
  shares one hard ~5-10MB origin-wide quota with everything else already stored there. As saved
  workspaces (with export/import payloads) and Bench history accumulate over years of real use, that
  ceiling is a real, not hypothetical, future failure mode. IndexedDB is not itself bleeding-edge
  (it's old and stable) — it's the more *durable* foundation, which is exactly the point: migrate the
  storage backing, keep the public `VW.workspace`/Bench API surface identical, so nothing above this
  layer needs to change.
- **File System Access API for workspace export/import** — where available (modern tier,
  Chromium-only), a real native Save/Open dialog for exported workspace files, including
  write-back-in-place — a saved workspace file could live on a shared shop network folder that a
  whole team re-saves into directly, not just a one-shot download. The existing blob/`<a download>`
  approach stays as the universal fallback; this is a strictly-better *option* layered on top, never
  a replacement that narrows what already works.
- **Schema-versioned saved data, not just live messages.** `VW.channel`'s `v` field already protects
  a *live* message from being misread by a tab on different code. The same discipline now explicitly
  extends to anything actually **saved** — every stored workspace gets its own `schemaVersion` field,
  so a workspace saved by today's code stays safely readable (or cleanly migratable) by whatever this
  app looks like several rewrites from now, the same way `viewer.db`'s own migration system already
  treats the database.
- **Mirror workspaces into the existing server-side backup vault.** This project already has a
  standing rule that everything critical is always recoverable (`safeguard.py`'s snapshot/restore
  system, drilled for real in `[1.44.0]`) — but that guarantee has only ever covered server-side
  files. A corrupted browser profile can still lose a technician's real, named, in-progress
  workspaces, which this feature now treats as real data worth protecting the same way. Opt-in: a
  small new server route accepts the current workspace list and folds it into the *next* regular
  `safeguard.snapshot()` call, closing the loop between browser-side and server-side state for the
  first time.

## Future-facing direction, documented but not scheduled: an installable PWA app shell

The single largest architectural fork raised this revision, and treated accordingly — **named as a
real future direction, not built or scheduled into the current plan.** THE VIEWER could become an
installable Progressive Web App: its own taskbar icon and window chrome instead of living inside
ordinary browser tabs, which is a more native fit for "multiple windows of one app" than a browser's
own tab strip ever fully is. The genuinely interesting part for *this specific feature area*: a
Service Worker is a single, longer-lived background context every tab can already talk to — a
potentially stronger foundation for cross-window coordination than `BroadcastChannel`, which only
exists for as long as at least one tab keeps a channel open. If this is ever picked up, `VW.channel`'s
public contract (`publish`/`subscribe`) is designed to stay the same regardless of what sits
underneath it — a Service-Worker-backed transport could slot in as a third option alongside
`BroadcastChannel`/`storage` without any caller needing to change.

## Known limitations (new section this revision)

- **Shared-machine, no-user-accounts scope.** This app has no login system, and `BroadcastChannel`/
  `localStorage`/IndexedDB are all origin-wide — every open tab on this machine sees every
  workspace and the whole Bench list, regardless of who is physically at the keyboard. This is
  consistent with how the app already works today (no isolation exists anywhere else in it either),
  but it is a real limitation of everything in this spec, stated plainly rather than glossed over —
  the same honesty this project's own release notes already apply elsewhere ("no independent SME
  review," "offsite backup still manual"). Nothing here is designed to change that; a future
  per-user layer would be a much larger, separate initiative.
- **C and G's real placement/PiP behavior is only verifiable by a human on real multi-monitor
  hardware** — this project's CI runners are not multi-monitor. Rather than leaving that as an
  easy-to-forget note buried in one PR description, it becomes a short, real, standing checklist
  document (see Testing below) that gets run once per release, matching this project's existing
  `VERIFY.bat`-style verification culture instead of sitting outside it.

## Architecture

### `VW.channel` *(merged)*
```
VW.channel.publish(name, data)         // data may include any JSON-serializable payload
VW.channel.subscribe(name, fn)         // fn(data, meta) -- meta: {seq, v}
```

### `VW.workspace` *(CRUD + export/import landed; built-in templates next; IndexedDB + schemaVersion +
backup-vault mirroring are Stage 6 additions on top of the same public surface)*
```
{ id, name, items: [{page, params}], created, lastOpened, source: "manual"|"template",
  schemaVersion }
VW.workspace.create(name, items) -> id
VW.workspace.list() / .get(id) / .touch(id)
VW.workspace.exportUrl(id) -> string      // shareable query-string form
VW.workspace.exportFile(id) -> Blob       // downloadable .json; File System Access API used
                                           // in place of a plain download where available
VW.workspace.importUrl(qs) -> id
VW.workspace.importFile(blob) -> id
VW.workspace.templates() -> [{name, items}, ...]
```

### `VW.windows` *(open/reuse/toast core in progress; layout capture/restore next)*
```
VW.windows.open(url, opts)   // opts: {name, screen?} -- name enables reuse; screen is a hint,
                              // ignored gracefully wherever C's placement API isn't available
VW.windows.registry() -> [{name, url, screenX, screenY, outerWidth, outerHeight}, ...]
VW.windows.restoreLayout(entries)   // user-triggered only
```

### `VW.capabilities` (Stage 6, new)
```
VW.capabilities.tier         // "modern" | "lite" | "legacy", read from the existing rps.js tier
VW.capabilities.broadcastChannel / windowPlacement / wakeLock / pictureInPicture /
  fileSystemAccess / webLocks / indexedDB   // booleans, raw feature-detection AND-ed with tier
```

### `VW.locks` (Stage 6, new)
```
VW.locks.withLock(name, fn)   // wraps navigator.locks.request; on lite/legacy tier or where the
                               // API is absent, falls back to a best-effort in-memory lock scoped
                               // to just this tab (not a real cross-tab guarantee, but never blocks)
```

### C's extension to `VW.windows`
Feature-detected via `VW.capabilities.windowPlacement`, permission requested only when a placement
is actually attempted, any denial or absence falls back to `VW.windows.open()`'s normal behavior.

### G's kiosk/reference route
A new server route rendering a minimal, large-text template built from the existing `viewer_kiosk`
styling primitives, opened via `VW.windows.open()` — through `documentPictureInPicture.requestWindow()`
where `VW.capabilities.pictureInPicture` is true, an ordinary popped-out window otherwise — with
`navigator.wakeLock` requested for that window's lifetime where `VW.capabilities.wakeLock` is true.

## Edge cases

- **`VW.channel` schema mismatch:** silently ignored, never throws.
- **Oversized payload on the `storage` fallback path:** fails loudly at the publish call site.
- **Workspace import of a malformed/tampered file:** validated before being written, rejected with a
  clear message on any mismatch.
- **A saved workspace's `schemaVersion` is older than the running code understands:** migrated on
  read where a safe migration path exists, refused with a clear message (never silently
  misinterpreted) where it doesn't.
- **Layout restore where a saved window's recorded screen no longer exists:** falls back to the
  browser's own default placement for that window.
- **`VW.locks` on a tier/browser without the Web Locks API:** falls back to an in-memory,
  single-tab-only lock — correctness within one tab is unaffected; cross-tab races that the real API
  would have prevented become possible again, which is an acceptable, explicitly-known regression on
  older hardware rather than a silent one.
- **Document Picture-in-Picture unsupported or denied:** `VW.windows.open()`'s normal path is used
  instead, with no error surfaced — the reference content is identical, only the window behavior
  differs.
- **C's permission denied or API absent:** behaves like `VW.windows.open()` without a screen hint.
- Everything already named in earlier revisions (popup-blocker non-issue, kiosk tap-target sizing,
  last-write-wins Bench conflicts, discarded background tabs) still applies unchanged.

## Testing

- **Fully automatable:** every markup-level change; every pure data-shape/logic function
  (`VW.workspace` CRUD + export/import round-trips, `VW.channel`'s envelope/sequence/version logic,
  `VW.capabilities`'s detection-and-tier-AND-ing logic given a mocked tier + mocked feature
  presence); `rps_lint`/ES5 compliance on every touched file.
- **Manual, called out explicitly per PR, never glossed over:** live cross-tab delivery, named-window
  reuse, layout capture/restore, B's curated launches, the all-46-page responsive resize pass, and —
  new this revision — **a short, real, standing checklist document** (not code: a markdown file a
  human runs through once per release) covering exactly the things this project's CI genuinely cannot
  verify itself: C's placement and G's Picture-in-Picture/Wake-Lock behavior on real multi-monitor
  hardware, and the RPS-tier capability gating actually suppressing the right features on a real
  lite/legacy-classified machine, not just in a mocked test.

## Files touched

- `engine/ui/shared.js` — `VW.channel`, `VW.workspace`, `VW.windows`, `VW.capabilities`, `VW.locks`,
  all under the existing strict ES5/RPS-lint constraint.
- `engine/ui/base.css` — responsive baseline breakpoints.
- All 46 `engine/ui/*.html` pages — responsive verification pass (batched).
- `engine/ui/index.html` — A1. `engine/ui/bench.html` — D.
- `engine/ui/part.html`, `procedure.html`, `torque.html`, `jobcard.html`, `bench.html` — A2 adoption.
- `engine/ui/jobcard.html`, `solve.html` — B's launch buttons.
- New `engine/ui/workspaces.html` (or a `bench.html` section) — F's UI.
- `engine/ui/handover.html` — F's handoff hook.
- New server route + template for G; a new small server route for backup-vault workspace mirroring.
- New `docs/MULTI-WINDOW-MANUAL-QA.md` — the standing manual-check document referenced in Testing.
- `engine/tests/test_*.py` — new/extended coverage for every automatable piece above.

## Rollout order

See the companion plan document
(`docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md`) for the full PR-by-PR sequencing,
including the new Stage 6 this revision adds.
