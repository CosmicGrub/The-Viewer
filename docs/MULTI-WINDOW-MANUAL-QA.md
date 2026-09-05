# Multi-Window Manual QA — THE VIEWER

Real, dated records of the multi-window/multi-tab initiative's checks that **cannot be run in CI or
proven by any test file in `engine/tests/`** — screen placement on genuinely separate monitors, and
hardware-tier capability gating on genuinely constrained hardware. Named and scoped by
`docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md`'s own "New standing document" note
(search that file for `MULTI-WINDOW-MANUAL-QA.md`):

> the short, real checklist for exactly what this project's CI cannot verify itself — C's placement
> and PR 24's Picture-in-Picture/Wake-Lock behavior on real multi-monitor hardware, and the RPS-tier
> capability gating actually suppressing the right features on a real lite/legacy-classified
> machine. Run once per release, the same standing-ritual way `VERIFY.bat` already is.

**Why this exists as its own document, not another `CHANGELOG.md` entry.** Every PR in this
initiative already states its own real-hardware caveat plainly in its own PR body and `CHANGELOG.md`
entry (see `[1.68.0]`/PR 17, and this PR itself) — that per-PR honesty is not new. What was missing
is a single, standing, run-it-again-next-release checklist, the same role `VERIFY.bat` plays for
everything that IS automatable. This document is that checklist. It is not itself a substitute for
either — automated coverage stays in `engine/tests/`, and honest per-PR limitations stay in
`CHANGELOG.md` — this is where a human records having actually walked through the parts neither of
those can reach.

**A real, dated gap, stated plainly:** this document was supposed to land with PR 17 (`[1.68.0]`,
C — screen-aware placement) or this PR (PR 18, G — kiosk/second-screen reference view), whichever
shipped first, per the plan doc's own note above. PR 17 merged without creating it. This PR closes
that gap and adds its own section to the same checklist, rather than opening a second document.

Newest run at top. Each run gets its own dated section; do not overwrite a prior run's findings —
append.

---

## How to run this checklist

You need:
- **A genuinely multi-monitor machine** (two or more physical displays, OS-level "extend" — not
  mirrored — desktop). A single-monitor machine, a VM with one virtual display, or a browser's own
  device-emulation panel cannot exercise any of §1 — they can only prove the *fallback* path (which
  `engine/tests/test_windows_screen_placement.py` and `test_g_reference_view.py` already prove
  automatically, in every CI run, on every machine). Confirm the display count once at the top of
  each run (`Settings → System → Display` on Windows, or `xrandr`/`System Settings → Displays`
  elsewhere) and record it.
- **Chromium-based browser(s)** for §1 — the Window Management API (`getScreenDetails()`) this
  initiative's screen-aware placement depends on is Chromium-only (Chrome, Edge, Brave). Firefox and
  Safari are expected, honest, silent-fallback cases, not failures — record them as such if tested.
- **A real "lite" or "legacy"-classified machine** for §2 — an actual older/slower PC `rps.py`'s own
  probe would classify that way (see `engine/rps.py`'s own header: `lite` = "modern OS but weak
  hardware", `legacy` = "older OS / Poppler render path / old Python"), OR the running app's own
  Settings page forcing Retroactive Post-Support mode on a normal machine (a real, supported way to
  exercise the SAME `window.RPS.mode` code path the placement/reference features gate on, without
  owning literal period hardware — record which of the two you used).
- The app running and reachable from every machine/browser under test (LAN + `--tls`, or each
  machine hitting `localhost` against its own copy — record which).

---

## §1 — Screen-aware placement (PR 17, C) and the "send to second screen" buttons (PR 18, G)

Covers: `VW.windows.open(url, {screen: true})` (the mechanism, first shipped inert with no caller in
`[1.68.0]`/PR 17) and its first two real callers — torque.html's and procedure.html's "Send to second
screen" buttons (`[1.72.0]`/PR 18), which open `/reference` via that exact same opt-in.

What automated coverage already proves, so this checklist does not need to re-prove it: the
feature-detection/tier gate and the fallback branch (`test_windows_screen_placement.py`, run against
a mocked `getScreenDetails()` in a `vm.createContext()` sandbox — no real screens involved); that
`torque.html`/`procedure.html`'s buttons genuinely call `VW.windows.open()` with `{screen: true}` and
the correct `/reference?type=...&q=...` target (`test_g_reference_view.py`, source-level); that
`/reference` itself is served correctly and renders sensibly (same file, against a real but
single-process test server). None of that can prove a window actually LANDS on a different physical
screen — only a human, on real hardware, can.

For each browser tested, on the real multi-monitor machine:

- [ ] **Permission prompt appears exactly once per browser profile**, only at the moment a "Send to
      second screen" button is FIRST clicked (never on page load, never before). Record whether it
      appeared, and what it said.
- [ ] **Granted:** clicking "Send to second screen" on `/torque` (with a real query typed first, e.g.
      "alternator") opens `/reference?type=torque&q=alternator` on a screen OTHER than the one the
      click happened on. Record which screen (by position: left/right/above/below) it landed on.
- [ ] **Granted, repeat click:** clicking the SAME page's button again reuses the same
      `/reference` window (does not open a second one) — confirm via the OS window list / taskbar,
      not just visually.
- [ ] **Granted, the OTHER page's button:** with the `/reference` window from `/torque` still open,
      click `/procedure`'s "Send to second screen" instead. Confirm it reuses the SAME window (same
      `"vw-reference"` name, both buttons deliberately share it — see `procedure.html`'s/
      `torque.html`'s own comment on the button) and now shows the procedure content, not two windows
      competing for the second screen.
- [ ] **Denied:** deny the permission prompt (or revoke it in browser site settings and retry).
      Confirm the window still opens — just on the SAME screen as the click, no error, no console
      exception, no broken UI. This is the contract `_attemptScreenPlacement`'s own header comment
      states: any denial degrades silently.
- [ ] **`/reference` itself, once open on the second screen, from across the room (or at least
      arm's length):** confirm the glanceable value (torque number + units, or the current procedure
      step's text) is actually legible at a real, sensible reading distance — not just "renders",
      genuinely readable. Note the approximate distance you tested from.
- [ ] **A non-Chromium browser** (Firefox/Safari, if available): confirm "Send to second screen"
      still opens `/reference` — on the SAME screen, no prompt, no error — since
      `getScreenDetails` doesn't exist there at all.
- [ ] **Single-monitor fallback, still on the multi-monitor machine:** unplug/disable the second
      display (or use a genuinely single-monitor machine if easier), confirm the button still works,
      landing on the one screen that exists, no error.

Record browser + version, OS, display count/arrangement, and PASS/FAIL (with what actually happened)
for each box above.

---

## §2 — RPS-tier capability gating on real lite/legacy hardware

Covers: every place this initiative's code reads `window.RPS.mode` to decide whether to attempt a
placement at all (`shared.js`'s `_attemptScreenPlacement`, gating on an EXACT
`window.RPS.mode === "modern"` string match) or, once `VW.capabilities` lands (Stage 6, PR 19+),
whatever replaces that direct read.

- [ ] On the real (or Retroactive-Post-Support-forced) lite/legacy machine, confirm `window.RPS.mode`
      in the browser console actually reads `"lite"` or `"legacy"` as expected — record which, and
      how it was produced (real weak hardware the auto-probe classified that way, vs. the Settings
      page's own compatibility-mode override).
- [ ] Click "Send to second screen" on `/torque` or `/procedure`. Confirm `getScreenDetails()` is
      NEVER called at all on this tier (no permission prompt appears, ever) — the window still opens,
      just always on the same screen as the click. This is the tier gate working, not a bug.
- [ ] Confirm the rest of `/reference` itself still renders correctly and legibly on this tier — it
      does not depend on `window.RPS` at all (it is not in `rps_lint.py`'s `MODERN_BY_DESIGN` list;
      it is ES5-required, same class as `torque.html`/`procedure.html`), so this is mostly a sanity
      check that nothing ELSE on a weak/old machine silently breaks it (slow network, small SQLite
      cache changing `/api/torque`/`/api/procedure_full`'s response time in a way that changes what
      the technician sees while waiting).
- [ ] If PR 15/B's own tier-based warning (`VW.capabilities.tier` — currently inert until Stage 6
      ships a real `VW.capabilities`, see that PR's own comment) has since gone live by the time you
      run this: confirm it actually appears on this tier for multi-window launches, and that it is a
      `confirm()`, never a hard block.

Record OS/hardware (or which forced-compatibility setting), browser, and PASS/FAIL for each box.

---

## §3 — Document Picture-in-Picture + Wake Lock (PR 24) — placeholder, not yet applicable

**PR 24 has not shipped yet.** This section is a marked placeholder, filled in with real checklist
items only once PR 24 (`VW.capabilities`-gated `documentPictureInPicture.requestWindow()` as G's
*primary* mechanism where supported, falling back to this PR's plain `VW.windows.open()` path
otherwise; `navigator.wakeLock` keeping that window's screen from sleeping) actually lands. Per the
plan doc's own Stage 6 description, expect this section to eventually cover at minimum:

- [ ] *(PR 24)* Document Picture-in-Picture window genuinely floats above OTHER APPLICATIONS, not
      just other browser tabs, on real desktop hardware (Chromium's own PiP contract — cannot be
      verified any other way; the whole reason PR 24 picks this API over an ordinary window).
- [ ] *(PR 24)* Falls back to this PR's plain `/reference` second-window path, unchanged, on any
      browser/tier without PiP support — confirm the reference CONTENT is identical either way, only
      the window behavior differs (the design doc's own stated invariant).
- [ ] *(PR 24)* `navigator.wakeLock` actually keeps the second screen from sleeping/locking during a
      real, timed idle period (test with the OS's own screen-timeout set short, e.g. 1 minute, and
      wait past it) — on a tier/browser where `VW.capabilities.wakeLock` is true.
- [ ] *(PR 24)* Wake Lock absence on an unsupported browser/tier degrades silently — screen still
      sleeps on its normal OS timeout, no error surfaced.

Do not check any box in this section until PR 24 has actually merged and real code exists to test —
a checked box here before then would be recording nothing.

---
