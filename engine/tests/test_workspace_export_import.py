#!/usr/bin/env python3
"""VW.workspace export/import (shared.js) -- exportUrl/exportFile/importUrl/importFile. PR 3 of
docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md (stage 2), landed after PR 15/16's
launcher work because PR 16 (F -- save & reopen named workspaces) depends on this existing first.

Two layers, both real, same convention as test_shared_workspace.py (PR 2):
  1. `node --check` on shared.js -- syntax only.
  2. tests/js/test_workspace_export_import_node.js -- NOT a syntax check and NOT a re-assertion of
     source text. Every assertion goes through the real exported VW.workspace.exportUrl/exportFile/
     importUrl/importFile functions loaded from the real engine/ui/shared.js, using two SEPARATE
     localStorage stores per round trip (one per "browser") so the round trip genuinely exercises
     the exported payload rather than two tabs quietly sharing one store. Covers:
       - exportUrl -> importUrl and exportFile -> importFile round trips (name/items preserved,
         id/timestamps deliberately NOT carried across, a fresh id always minted)
       - exportUrl/exportFile's not-found convention (null, not a throw)
       - malformed/tampered import rejection (bad JSON, wrong top-level shape, an item missing
         "page", a missing "ws=" key) via BOTH importUrl and importFile, asserting a specific
         Error message AND that storage is left byte-for-byte unchanged (including when a real
         workspace already existed in that store)
       - importUrl/importFile never trusting an id-shaped field smuggled into the payload, proven
         against two separate imports of the identical crafted payload

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
NODE_TEST = os.path.join(HERE, "js", "test_workspace_export_import_node.js")


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
    tests.append(("vw_workspace_export_import_real_roundtrips (see indented PASS/FAIL lines above)",
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
