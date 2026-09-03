#!/usr/bin/env python3
"""VW.channel (shared.js) -- cross-window/cross-tab publish/subscribe, stage 1 of
docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md (PR 1).

Two layers, both real:
  1. `node --check` on shared.js -- syntax only, same convention test_uiux_fixes.py already uses
     for gl3d.js/deepzoom.js/circuitlab.html's inline scripts.
  2. tests/js/test_channel_node.js -- NOT a syntax check. Two independent vm.createContext()
     sandboxes stand in for two real browser tabs (see that file's own header comment for exactly
     why this is production code exercising a real BroadcastChannel, not a reimplementation of the
     logic under test), covering: real cross-tab delivery/ordering over BroadcastChannel, the
     self-echo exclusion, the storage-event fallback path, gap detection on a coalesced write,
     silent version-mismatch handling, the oversized-payload guard, and malformed-JSON safety.

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
NODE_TEST = os.path.join(HERE, "js", "test_channel_node.js")


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
    tests.append(("vw_channel_real_cross_tab_logic (see indented PASS/FAIL lines above)",
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
