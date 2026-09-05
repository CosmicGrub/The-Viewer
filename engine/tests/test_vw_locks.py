#!/usr/bin/env python3
"""VW.locks -- Web Locks API wrapper (shared.js). PR 20 of
docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md (stage 6): "VW.locks.withLock(name, fn);
falls back to a best-effort in-memory single-tab lock on lite/legacy tier or where navigator.locks is
absent." Depends on PR 19 (VW.capabilities.webLocks, already merged and real as of [1.73.0]) -- this
is the FIRST real consumer of VW.capabilities anywhere in this codebase, gating directly on the live
_capabilities.webLocks getter rather than re-deriving a second, independently-typed
`"locks" in navigator && tier === "modern"` check of its own.

Two layers, same convention test_vw_capabilities.py (PR 19) already established:
  1. `node --check` on shared.js -- syntax only.
  2. tests/js/test_vw_locks_node.js -- NOT a syntax check. Loads the real shared.js into a
     vm.createContext() sandbox and proves, against the real production VW.locks code:
       - REAL-API PATH: webLocks true -> withLock() genuinely delegates to navigator.locks.request()
         with the right name, fn()'s plain-value and Promise-value resolution/rejection round-trips.
       - RAW API ABSENT: the fallback runs, never touching navigator.locks (proven by the absence of
         the synchronous throw a real access against undefined would cause).
       - THE SINGLE MOST IMPORTANT TEST: raw API present but tier "lite"/"legacy"/"premium" -> the
         fallback STILL runs, proven via a canary wired to navigator.locks.request that is asserted to
         have NEVER been invoked in any of the three cases -- proof the gate is genuinely
         capability-driven, not raw-feature-driven, mirroring PR 19's own most-important live-read
         test.
       - fallback mutual exclusion (same name serializes, in call order), independence (different
         names run concurrently), resilience (a rejecting/throwing fn() does not jam the next queued
         call for that name, and the original rejection still reaches its own caller), and the
         queue-cleanup guarantee (the internal pending-lock map returns to empty once a name's queue
         drains, proven via a debug-only introspection hook, not a source-text guess).

This file also runs static, source-level guarantees the node layer cannot see from inside the sandbox:
  3. VW.locks is placed BEFORE popoutControl()'s own section in shared.js (and after VW.capabilities)
     -- per PR 6/PR 17/PR 19's own documented test_a2_popout.py cross-PR coupling hazard: that test
     slices popoutControl()'s body up to the next "var VW = {" marker, so anything inserted between
     them gets silently swallowed into what it inspects.
  4. The real-API path is a straight delegation to navigator.locks.request() -- no reimplementation of
     acquisition/release/serialization logic of its own.
  5. The gate reads _capabilities.webLocks directly (the exact PR 19 property), never a second,
     re-typed raw "locks" in navigator / tier check of its own -- the same technique
     test_vw_capabilities.py already uses to prove windowPlacement reuses _screenPlacementAvailable().
  6. VW.channel/VW.workspace/VW.windows/VW.capabilities's own key lists in the final VW assembly are
     untouched by this diff.

Gracefully skips (never false-fails) the node-dependent layer in an environment without node, same as
the rest of this codebase's node-dependent checks. The source-level checks have no node dependency and
always run.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
UI = os.path.join(ENGINE, "ui")
SHARED_JS = os.path.join(UI, "shared.js")
NODE_TEST = os.path.join(HERE, "js", "test_vw_locks_node.js")


def read(path):
    return open(path, encoding="utf-8").read()


def main():
    tests = []
    shared_js = read(SHARED_JS)

    # ============================================================================================
    # Layer 3 (static, no node dependency): VW.locks is declared, exported off VW, and lands AFTER
    # VW.capabilities but BEFORE popoutControl()'s own section -- never between popoutControl() and
    # the final "var VW = {" marker.
    # ============================================================================================
    tests.append(("shared_js_declares_lock_queues_map", "var _lockQueues = {};" in shared_js))
    tests.append(("shared_js_declares_locks_fallback_function",
                  "function _locksFallback(name, fn)" in shared_js))
    tests.append(("shared_js_declares_locks_with_lock_function",
                  "function locksWithLock(name, fn)" in shared_js))
    tests.append(("shared_js_exports_locks_off_vw_with_with_lock_member",
                  re.search(r"capabilities:\s*_capabilities,\s*locks:\s*\{\s*withLock:\s*locksWithLock",
                             shared_js) is not None))

    caps_idx = shared_js.find("var _capabilities = {};")
    locks_idx = shared_js.find("var _lockQueues = {};")
    popout_idx = shared_js.find("function popoutControl(opts)")
    vw_assign_idx = shared_js.find("\n  var VW = {")
    tests.append(("vw_locks_declared_after_vw_capabilities_and_before_popout_control",
                  caps_idx != -1 and locks_idx != -1 and popout_idx != -1 and vw_assign_idx != -1 and
                  caps_idx < locks_idx < popout_idx < vw_assign_idx))

    # ============================================================================================
    # Layer 4: the real-API path is a straight delegation -- no reimplementation of acquisition/
    # release/serialization logic. Checked by isolating locksWithLock()'s own body and asserting it
    # calls navigator.locks.request() exactly once and contains none of the fallback's own machinery.
    # ============================================================================================
    wl_start = shared_js.find("function locksWithLock(name, fn)")
    wl_end = shared_js.find("\n  }", wl_start) + 4 if wl_start != -1 else -1
    wl_body = shared_js[wl_start:wl_end] if wl_start != -1 else ""
    tests.append(("locks_with_lock_delegates_to_navigator_locks_request",
                  wl_start != -1 and "navigator.locks.request(name" in wl_body))
    tests.append(("locks_with_lock_does_not_reimplement_fallback_machinery_inline",
                  wl_start != -1 and "_lockQueues" not in wl_body and "priorTail" not in wl_body))

    # ============================================================================================
    # Layer 5: the gate reads _capabilities.webLocks directly -- never a second, re-typed raw
    # "locks" in navigator / tier check of its own (the same drift PR 19 exists to rule out).
    # ============================================================================================
    tests.append(("locks_with_lock_gates_on_capabilities_web_locks_directly",
                  wl_start != -1 and "_capabilities.webLocks" in wl_body))
    tests.append(("locks_with_lock_has_no_second_raw_locks_in_navigator_check_of_its_own",
                  wl_start != -1 and '"locks" in navigator' not in wl_body))
    tests.append(("locks_with_lock_has_no_second_independent_tier_check_of_its_own",
                  wl_start != -1 and "_capIsModernTier" not in wl_body and
                  "RPS.mode" not in wl_body))

    # ============================================================================================
    # Layer 6: VW.channel / VW.workspace / VW.windows / VW.capabilities export shape is exactly what
    # it was before this PR.
    # ============================================================================================
    tests.append(("vw_channel_export_unchanged",
                  "channel: { publish: channelPublish, subscribe: channelSubscribe }," in shared_js))
    tests.append(("vw_workspace_export_unchanged",
                  "workspace: { create: workspaceCreate, list: workspaceList," in shared_js))
    tests.append(("vw_windows_export_unchanged",
                  "windows: { open: windowsOpen, registry: windowsRegistry," in shared_js))
    tests.append(("vw_capabilities_export_unchanged", "capabilities: _capabilities," in shared_js))

    # No ES6 getter/setter shorthand or other ES6 syntax introduced by this PR's own code (belt-and-
    # suspenders alongside rps_lint.py itself, same convention test_vw_capabilities.py established).
    locks_section = shared_js[caps_idx + len("var _capabilities = {};"):popout_idx] \
        if caps_idx != -1 and popout_idx != -1 else ""
    tests.append(("no_arrow_functions_in_new_locks_code", "=>" not in locks_section))
    tests.append(("no_const_or_let_in_new_locks_code",
                  re.search(r"\b(const|let)\s+\w", locks_section) is None))

    # ============================================================================================
    # Layers 1-2: node --check + the real vm.createContext behavioral suite.
    # ============================================================================================
    if subprocess.run(["node", "--version"], capture_output=True).returncode != 0:
        tests.append(("node_unavailable_skip_behavioral_layers (no node in this environment)", True))
    else:
        r1 = subprocess.run(["node", "--check", SHARED_JS], capture_output=True, text=True)
        tests.append(("shared_js_parses_with_node", r1.returncode == 0))
        if r1.returncode != 0:
            print("  node --check stderr:", r1.stderr.strip()[:500])

        r2 = subprocess.run(["node", NODE_TEST], capture_output=True, text=True)
        for line in r2.stdout.splitlines():
            if line.startswith("PASS ") or line.startswith("FAIL "):
                print("  " + line)
        tests.append(("vw_locks_behavior (see indented PASS/FAIL lines above)",
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
