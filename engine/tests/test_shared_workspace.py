#!/usr/bin/env python3
"""VW.workspace (shared.js) -- saved, named sets of pages: CRUD + the cross-tab change
notification. Stage 2 of docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md (PR 2).

Two layers, both real:
  1. `node --check` on shared.js -- syntax only, same convention test_uiux_fixes.py already uses
     for gl3d.js/deepzoom.js/circuitlab.html's inline scripts, and test_shared_channel.py for
     VW.channel.
  2. tests/js/test_workspace_node.js -- NOT a syntax check. Every assertion goes through the real
     exported VW.workspace functions; where a check needs to know what was actually persisted it
     reads the raw `viewer_workspaces` localStorage value directly rather than trusting the API to
     describe itself. Two vm.createContext() sandboxes stand in for two browser tabs SHARING one
     localStorage object (which is exactly what two tabs on one origin have), so the design's
     central claim -- storage is already shared for free, the VW.channel message is only a
     "repaint" hint -- is exercised end to end rather than asserted. Covers: the stored record
     shape, id uniqueness (including with a frozen clock and a constant Math.random), item/param
     normalization, name and source handling, list/get/touch semantics, corrupt-and-hostile stored
     values, storage that refuses reads or writes, and the change notification over BOTH channel
     transports (a real BroadcastChannel between the two contexts, and the storage-event fallback).

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
NODE_TEST = os.path.join(HERE, "js", "test_workspace_node.js")


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
    tests.append(("vw_workspace_real_crud_and_cross_tab_notify (see indented PASS/FAIL lines above)",
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
