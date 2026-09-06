#!/usr/bin/env python3
"""VW.workspace -- IndexedDB storage migration (shared.js). PR 21 of
docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md (stage 6): "Swaps the storage backing
PR 2 built (localStorage under viewer_workspaces) for IndexedDB, keeping create/list/get/touch's
public contract byte-for-byte identical -- nothing above this layer changes." Depends on PR 2
(CRUD, already merged) and PR 19 (VW.capabilities.indexedDB gates whether this backing is used at
all -- lite/legacy tier keeps the original localStorage path).

Four layers:
  1. `node --check` on shared.js -- syntax only.
  2. Static, source-level guarantees the node sandbox layer cannot see from inside a vm context (see
     below).
  3. tests/js/test_vw_workspace_indexeddb_node.js -- NOT a syntax check. Loads the real shared.js
     into vm.createContext() sandboxes and proves, against the actual production code: the
     synchronous bootstrap-from-localStorage guarantee (even with the mock IndexedDB's open()
     deliberately deferred), the one-time migration once IndexedDB reads back empty, wholesale cache
     replacement once IndexedDB already holds different records, that mutations are both instantly
     synchronous AND eventually durably persisted, that lite/legacy tier (or the raw API simply
     absent) never touches indexedDB.open() at all and behaves identically to before this PR, that
     IndexedDB failures (a synchronous throw, or every operation erroring) never break a synchronous
     caller, the one-time repeated-failure toast, and the large-payload case this whole migration
     exists for (succeeds via IndexedDB where a quota-constrained localStorage-only mock fails
     exactly as the pre-PR-21 code would have).
  4. PR 2's and PR 3's OWN original test suites (test_shared_workspace.py / test_workspace_node.js
     and test_workspace_export_import.py / test_workspace_export_import_node.js) are run UNMODIFIED
     against this same new code by their own existing wrapper scripts -- not duplicated here. Their
     sandboxes never define window.indexedDB, so VW.capabilities.indexedDB reads false there and
     every assertion exercises the untouched localStorage path, proving the public contract really
     did not change. See this repo's own verification notes for the real pass counts.

Static, source-level guarantees checked here directly against shared.js's text (no node dependency,
always run):
  a. The new IndexedDB-backing code sits BEFORE popoutControl()'s own section (and after PR 2's
     original CRUD) -- per test_a2_popout.py's own documented cross-PR coupling hazard: that test
     slices popoutControl()'s body up to the next "var VW = {" marker, so anything landing between
     popoutControl() and that marker would be silently swallowed into what it inspects. Modifying
     the EXISTING workspaceCreate/List/Get/Touch/Delete in place (never duplicating them) keeps this
     automatically true; this test still asserts it directly rather than assuming it.
  b. Every one of create/list/get/touch/delete genuinely routes through the new
     _wsAllForRead()/_wsAllForMutation()/_wsCommit() indirection -- not a second, parallel
     implementation living alongside the untouched originals.
  c. The backing decision reads VW.capabilities.indexedDB (via _wsUsingIndexedDB()) -- never a
     second, independently-typed `typeof window.indexedDB !== "undefined" && ...` check of its own,
     the exact drift PR 19 exists to rule out (the same technique test_vw_locks.py already uses for
     VW.locks.withLock's own gate).
  d. _wsCoerceAll() is the ONE shared shape-validation function -- _wsRead() (localStorage) and the
     IndexedDB read path both call it, so "what counts as a valid stored workspace" cannot drift
     between the two backings.
  e. VW.channel / VW.workspace / VW.windows / VW.capabilities / VW.locks's own export shape in the
     final VW assembly is exactly what it was before this PR.
  f. No ES6 syntax (arrow functions, const/let) in the new code, belt-and-suspenders alongside
     rps_lint.py itself.

Gracefully skips (never false-fails) the node-dependent layers in an environment without node, same
as the rest of this codebase's node-dependent checks. The static checks have no node dependency and
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
NODE_TEST = os.path.join(HERE, "js", "test_vw_workspace_indexeddb_node.js")


def read(path):
    return open(path, encoding="utf-8").read()


def main():
    tests = []
    shared_js = read(SHARED_JS)

    # ============================================================================================
    # Layer 2a: placement -- after PR 2's original CRUD, before popoutControl()'s own section,
    # never between popoutControl() and the final "var VW = {" marker.
    # ============================================================================================
    notify_idx = shared_js.find("function _wsNotify(action, ws)")
    idb_idx = shared_js.find("var _wsCache = null;")
    create_idx = shared_js.find("function workspaceCreate(name, items, source)")
    popout_idx = shared_js.find("function popoutControl(opts)")
    vw_assign_idx = shared_js.find("\n  var VW = {")
    tests.append(("ws_indexeddb_code_lands_after_ws_notify_and_before_workspace_create",
                  notify_idx != -1 and idb_idx != -1 and create_idx != -1 and
                  notify_idx < idb_idx < create_idx))
    tests.append(("ws_indexeddb_code_lands_well_before_popout_control_and_vw_assembly",
                  idb_idx != -1 and popout_idx != -1 and vw_assign_idx != -1 and
                  idb_idx < popout_idx < vw_assign_idx))

    # ============================================================================================
    # Layer 2b: create/list/get/touch/delete all route through the new indirection -- never a
    # second, parallel implementation living alongside the untouched originals.
    # ============================================================================================
    tests.append(("workspace_create_uses_all_for_mutation_and_commit",
                  "var all = _wsAllForMutation();" in shared_js and
                  "if (!_wsCommit(all)) return null;" in shared_js))
    tests.append(("workspace_list_uses_all_for_read",
                  "function workspaceList() { return _wsAllForRead(); }" in shared_js))
    tests.append(("workspace_get_uses_all_for_read",
                  re.search(r"function workspaceGet\(id\) \{[^}]*var all = _wsAllForRead\(\);",
                             shared_js, re.S) is not None))
    tests.append(("workspace_touch_uses_all_for_mutation_and_commit",
                  re.search(r"function workspaceTouch\(id\) \{.*?_wsAllForMutation\(\).*?_wsCommit\(all\)",
                             shared_js, re.S) is not None))
    tests.append(("workspace_delete_uses_all_for_mutation_and_commit",
                  re.search(r"function workspaceDelete\(id\) \{.*?_wsAllForMutation\(\).*?_wsCommit\(kept\)",
                             shared_js, re.S) is not None))
    def body_of(fn_marker, next_marker):
        start = shared_js.find(fn_marker)
        if start == -1:
            return None
        end = shared_js.find(next_marker, start)
        return shared_js[start:end] if end != -1 else None

    crud_bodies = {
        "workspaceCreate": body_of("function workspaceCreate(name, items, source)",
                                    "function workspaceList()"),
        "workspaceList": body_of("function workspaceList()", "function workspaceGet(id)"),
        "workspaceGet": body_of("function workspaceGet(id)", "function workspaceTouch(id)"),
        "workspaceTouch": body_of("function workspaceTouch(id)", "function workspaceDelete(id)"),
        "workspaceDelete": body_of("function workspaceDelete(id)", "/* v1.65.0"),
    }
    tests.append(("all_five_crud_function_bodies_were_located",
                  all(v is not None for v in crud_bodies.values())))
    tests.append(("no_leftover_direct_ws_read_or_ws_write_calls_in_the_five_crud_functions",
                  # _wsRead()/_wsWrite() are still called -- but only from INSIDE
                  # _wsAllForRead()/_wsAllForMutation()/_wsCommit(), never inlined a second time
                  # directly as an assignment/argument in the five CRUD bodies themselves. (A
                  # docstring mentioning "_wsRead()" in prose is fine -- only a real call matters.)
                  all(re.search(r"[=(]\s*_ws(Read|Write)\(", body or "") is None
                      for body in crud_bodies.values())))

    # ============================================================================================
    # Layer 2c: the backing decision reads VW.capabilities.indexedDB, never a second, independently
    # -typed raw-feature-plus-tier check of its own.
    # ============================================================================================
    gate_start = shared_js.find("function _wsUsingIndexedDB()")
    gate_end = shared_js.find("\n  }", gate_start) + 4 if gate_start != -1 else -1
    gate_body = shared_js[gate_start:gate_end] if gate_start != -1 else ""
    tests.append(("ws_using_indexeddb_gates_on_capabilities_indexeddb_directly",
                  gate_start != -1 and "_capabilities.indexedDB" in gate_body))
    tests.append(("ws_using_indexeddb_has_no_second_raw_indexeddb_typeof_check_of_its_own",
                  gate_start != -1 and "typeof window.indexedDB" not in gate_body))
    tests.append(("ws_using_indexeddb_has_no_second_independent_tier_check_of_its_own",
                  gate_start != -1 and "_capIsModernTier" not in gate_body and
                  "RPS.mode" not in gate_body))

    # ============================================================================================
    # Layer 2d: _wsCoerceAll() is the one shared shape-validator -- both _wsRead() and the
    # IndexedDB read path (_wsIdbReadAll) call it.
    # ============================================================================================
    tests.append(("ws_coerce_all_declared_once", shared_js.count("function _wsCoerceAll(parsed)") == 1))
    tests.append(("ws_read_calls_ws_coerce_all",
                  re.search(r"function _wsRead\(\) \{.*?_wsCoerceAll\(parsed\)", shared_js, re.S)
                  is not None))
    tests.append(("ws_idb_read_all_calls_ws_coerce_all",
                  re.search(r"function _wsIdbReadAll\(db, cb\) \{.*?_wsCoerceAll\(req\.result\)",
                             shared_js, re.S) is not None))

    # ============================================================================================
    # Layer 2e: VW.channel / VW.workspace / VW.windows / VW.capabilities / VW.locks export shape is
    # exactly what it was before this PR.
    # ============================================================================================
    tests.append(("vw_channel_export_unchanged",
                  "channel: { publish: channelPublish, subscribe: channelSubscribe }," in shared_js))
    # v1.76.0 (PR 22): the original 8 documented members must still appear verbatim, in the same
    # relative order -- but PR 22 legitimately interleaves a real explanatory comment plus 4 new
    # leading-underscore debug/introspection members (the same non-public convention
    # VW.locks._debugPendingCount already established) before the closing brace. Matching the
    # ORIGINAL prefix literally (never weakened) plus a separate check for the new members (by
    # name, not by brittle exact comment text) is more robust than one giant literal that breaks
    # every time the comment's wording changes without the actual export shape changing at all.
    tests.append(("vw_workspace_export_unchanged",
                  "workspace: { create: workspaceCreate, list: workspaceList,\n"
                  "                          get: workspaceGet, touch: workspaceTouch, "
                  "delete: workspaceDelete,\n"
                  "                          exportUrl: workspaceExportUrl, "
                  "exportFile: workspaceExportFile,\n"
                  "                          importUrl: workspaceImportUrl, "
                  "importFile: workspaceImportFile,\n" in shared_js))
    tests.append(("vw_workspace_schema_debug_members_added",
                  re.search(r"workspace:\s*\{.*?_schemaVersion:\s*_WS_SCHEMA_VERSION,"
                             r".*?_classifySchemaVersion:\s*_wsClassifyRecordSchema,"
                             r".*?_lastGetSchemaRefusal:\s*function\s*\(\)",
                             shared_js, re.S) is not None))
    tests.append(("vw_windows_export_unchanged",
                  "windows: { open: windowsOpen, registry: windowsRegistry," in shared_js))
    tests.append(("vw_capabilities_export_unchanged", "capabilities: _capabilities," in shared_js))
    tests.append(("vw_locks_export_unchanged",
                  "locks: { withLock: locksWithLock, _debugPendingCount: _locksDebugPendingCount } };"
                  in shared_js))

    # ============================================================================================
    # Layer 2f: no ES6 syntax in the new code (belt-and-suspenders alongside rps_lint.py).
    # ============================================================================================
    idb_section = shared_js[idb_idx:popout_idx] if idb_idx != -1 and popout_idx != -1 else ""
    tests.append(("no_arrow_functions_in_new_indexeddb_code", "=>" not in idb_section))
    tests.append(("no_const_or_let_in_new_indexeddb_code",
                  re.search(r"(?<![\w.])(const|let)\s+\w", idb_section) is None))
    tests.append(("no_template_literals_in_new_indexeddb_code", "`" not in idb_section))
    tests.append(("no_async_await_in_new_indexeddb_code",
                  re.search(r"(?<![\w.])async\s", idb_section) is None and
                  re.search(r"(?<![\w.])await\s", idb_section) is None))

    # ============================================================================================
    # Layers 1/3: node --check + the real vm.createContext behavioral suite.
    # ============================================================================================
    if subprocess.run(["node", "--version"], capture_output=True).returncode != 0:
        tests.append(("node_unavailable_skip_behavioral_layer (no node in this environment)", True))
    else:
        r1 = subprocess.run(["node", "--check", SHARED_JS], capture_output=True, text=True)
        tests.append(("shared_js_parses_with_node", r1.returncode == 0))
        if r1.returncode != 0:
            print("  node --check stderr:", r1.stderr.strip()[:500])

        r2 = subprocess.run(["node", NODE_TEST], capture_output=True, text=True, timeout=60)
        for line in r2.stdout.splitlines():
            if line.startswith("PASS ") or line.startswith("FAIL "):
                print("  " + line)
        tests.append(("vw_workspace_indexeddb_behavior (see indented PASS/FAIL lines above)",
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
