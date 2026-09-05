#!/usr/bin/env python3
"""VW.windows -- C: screen-aware placement (shared.js). PR 17 of
docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md (stage 5), depending on PR 6 (VW.windows
layout capture/restore, merged).

Two layers, same convention test_shared_windows.py (PR 5) / test_windows_layout.py (PR 6) already
established:
  1. `node --check` on shared.js -- syntax only.
  2. tests/js/test_windows_screen_placement_node.js -- NOT a syntax check. Loads the real shared.js
     into a vm.createContext() sandbox and proves, against the real production windowsOpen()/
     _attemptScreenPlacement()/_screenPlacementAvailable()/_screenPlacementPick() code:
       - opts.screen ABSENT never calls window.getScreenDetails() at all (the single most important
         guarantee given this feature's own stated permission philosophy).
       - opts.screen present but the API absent (typeof window.getScreenDetails !== "function") is a
         silent no-op; the window still opens normally, no throw.
       - the window.RPS.mode tier gate: "lite"/"legacy" and window.RPS entirely undefined (not every
         page loads rps.js) are all skipped, never throw. This app's own real hardware-tier signal
         (rps.js's window.RPS.mode) stands in for the design doc's not-yet-built
         VW.capabilities.windowPlacement -- the same real doc/code gap PR 15 hit for
         VW.capabilities.tier, resolved here with a real fallback rather than an inert one, since one
         actually exists today.
       - a resolved getScreenDetails() with 2+ screens moves the already-open window (win.moveTo()) to
         a screen genuinely DIFFERENT from currentScreen, never currentScreen's own bounds.
       - a resolved getScreenDetails() with only 1 screen attempts no move at all.
       - a REJECTED getScreenDetails() (permission denied) is caught silently: no throw at the call
         site, no unhandled promise rejection anywhere in the process, and the window handle already
         returned synchronously is unaffected.
       - getScreenDetails() itself throwing SYNCHRONOUSLY (e.g. called outside an active user gesture)
         is also caught silently, same guarantees.
       - window.open() happens SYNCHRONOUSLY, strictly BEFORE any getScreenDetails() call -- proven by
         the ORDER of operations via a shared call-order log both mocks push into, checked immediately
         after windowsOpen() returns, with no wait -- the exact permission-timing property this whole
         PR's design exists to guarantee (getScreenDetails() must never be awaited before window.open,
         or a popup blocker could treat the open as not user-gesture-initiated).

WHAT THIS CANNOT PROVE, stated plainly rather than glossed over: whether a real Chromium browser's
actual permission prompt behaves this way, whether win.moveTo() actually lands the window on the
correct physical monitor in a real multi-monitor setup, and whether every OS/window-manager honors
moveTo() at all. Node has no getScreenDetails, no window.open, and no real screens to be right or wrong
about any of that -- confirming the actual on-screen placement needs a human on a real multi-monitor
Chromium machine. That manual check is called out as manual in the PR body, the same honest framing the
design spec already applies to PR 6's own real-hardware-only placement claims.

Gracefully skips (never false-fails) the node-dependent layer in an environment without node, same as
the rest of this codebase's node-dependent checks.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
SHARED_JS = os.path.join(ENGINE, "ui", "shared.js")
NODE_TEST = os.path.join(HERE, "js", "test_windows_screen_placement_node.js")


def main():
    tests = []

    if subprocess.run(["node", "--version"], capture_output=True).returncode != 0:
        print("PASS node_unavailable_skip (no node in this environment)")
        print("\n1 passed, 0 failed")
        return 0

    r1 = subprocess.run(["node", "--check", SHARED_JS], capture_output=True, text=True)
    tests.append(("shared_js_parses_with_node", r1.returncode == 0))
    if r1.returncode != 0:
        print("  node --check stderr:", r1.stderr.strip()[:500])

    r2 = subprocess.run(["node", NODE_TEST], capture_output=True, text=True)
    for line in r2.stdout.splitlines():
        if line.startswith("PASS ") or line.startswith("FAIL "):
            print("  " + line)
    tests.append(("vw_windows_screen_placement_behavior (see indented PASS/FAIL lines above)",
                   r2.returncode == 0))
    if r2.returncode != 0:
        print("  node test stderr:", r2.stderr.strip()[:1500])

    fails = [n for n, ok in tests if not ok]
    for n, ok in tests:
        print(("PASS " if ok else "FAIL ") + n)
    print("\n%d passed, %d failed" % (len(tests) - len(fails), len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
