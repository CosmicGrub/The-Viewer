#!/usr/bin/env python3
"""VW.windows (shared.js) -- window open/reuse/toast, stage 2 of
docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md (PR 5).

Two layers, both real:
  1. `node --check` on shared.js -- syntax only, same convention test_shared_channel.py and
     test_uiux_fixes.py already use.
  2. tests/js/test_windows_node.js -- NOT a syntax check. It loads the real shared.js into a
     vm.createContext() sandbox with a MOCKED window.open that records every call it receives and
     hands back a fake window handle, then asserts on what the production VW.windows.open() /
     VW.windows.registry() code actually did with it: how many times window.open was called and with
     which arguments, what landed in the registry (same name twice -> ONE entry; different names ->
     separate entries; no name -> no entry at all), which toast text reached the DOM (counting real
     writes, not comparing values -- see that file's own note on why), the popup-blocked and
     window.open-throws paths, closed-window pruning, and the broadcast, which is delivered to a
     genuinely separate sandbox over Node's real global BroadcastChannel.

WHAT THIS CANNOT PROVE, stated plainly rather than glossed over: whether a real browser genuinely
reuses a window when the same name is passed twice. That is browser behavior, not this codebase's --
shared.js's whole reuse strategy is to hand the name to window.open and let the browser's own
named-window table do the work, and Node has no window.open to be right or wrong about it. Confirming
real reuse is a manual check (open a pop-out twice in a real browser, confirm ONE window), called out
as manual in the PR, the same way the design spec already treats every other real-hardware-only
behavior. Real popup-blocker and raise-to-front behavior are equally out of reach here.

ES5/RPS compliance itself is already covered by tests/rps_lint.py as its own gate -- not
re-implemented here.

Gracefully skips (never false-fails) in an environment without node, same as the rest of this
codebase's node-dependent checks."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
SHARED_JS = os.path.join(ENGINE, "ui", "shared.js")
NODE_TEST = os.path.join(HERE, "js", "test_windows_node.js")


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
    tests.append(("vw_windows_open_reuse_toast_behavior (see indented PASS/FAIL lines above)",
                   r2.returncode == 0))
    if r2.returncode != 0:
        print("  node test stderr:", r2.stderr.strip()[:1000])

    fails = [n for n, ok in tests if not ok]
    for n, ok in tests:
        print(("PASS " if ok else "FAIL ") + n)
    print("\n%d passed, %d failed" % (len(tests) - len(fails), len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
