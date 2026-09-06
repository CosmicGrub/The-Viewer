#!/usr/bin/env python3
"""VW.workspace.exportFileNative/importFileNative -- File System Access API for export/import
(shared.js + workspaces.html). PR 23 of docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md
(stage 6): "A real native Save/Open dialog (and write-back-in-place) where
VW.capabilities.fileSystemAccess is true; the existing blob/<a download> path (PR 3) stays as the
universal fallback, never removed. Tests: automated for the fallback path (already covered by PR 3's
tests); manual PR note for the real native-dialog path, since a file picker cannot be driven
headlessly in this test suite." Depends on PR 3 (exportFile/importFile/_wsExportPayload/
_wsImportFromJson, reused directly -- never a second, independently-typed copy) and PR 19
(_capabilities.fileSystemAccess, gated on directly -- the same "reuse, never re-derive" discipline
every Stage 6 PR since PR 20 has followed).

Two layers, same convention test_vw_locks.py (PR 20) and test_vw_workspace_schema_version.py (PR 22)
already established:
  1. `node --check` on shared.js -- syntax only.
  2. tests/js/test_vw_workspace_fsa_node.js -- NOT a syntax check. Loads the real shared.js into a
     vm.createContext() sandbox and proves, against the real production code:
       - FALLBACK PATH (fileSystemAccess false): the exact same Blob/URL.createObjectURL/
         <a download> pattern workspaces.html's own downloadFile() already uses.
       - NATIVE PATH, fresh handle: showSaveFilePicker() called once with a JSON filter + a
         suggested filename; the correct JSON payload written via createWritable()/write()/close();
         the handle remembered.
       - WRITE-BACK-IN-PLACE: a second call for the same id reuses the remembered handle without
         calling showSaveFilePicker() again.
       - PERMISSION RE-VERIFICATION: a revoked/denied permission on a previously-granted handle is
         re-checked before reuse and falls back to a fresh picker, never a silent failure or a
         write to a handle that just failed its own check.
       - CANCEL IS NOT AN ERROR in both directions, while a genuine (non-abort) failure still
         propagates as a real rejection.
       - importFileNative() routes through the EXISTING _wsImportFromJson() -- proven by a
         schemaVersion PR 22's own classifier genuinely refuses producing the SAME specific-Error
         convention, not a second, independently-typed check.
       - a successful import remembers the handle keyed by the newly created id, proven by a
         subsequent exportFileNative() call reusing it without re-prompting.
       - importFileNative() rejects clearly (never silently no-ops) when fileSystemAccess is false.

This file also runs static, source-level guarantees the node sandbox layer cannot see directly:
  3. exportFileNative/importFileNative/_wsFileHandles land after PR 3's workspaceImportFile and well
     before popoutControl()'s own section -- per test_a2_popout.py's own documented cross-PR coupling
     hazard (that test slices popoutControl()'s body up to the next "var VW = {" marker; anything
     inserted between them gets silently swallowed into what it inspects).
  4. exportFileNative() calls the EXISTING _wsExportPayload()/exportFile()/workspaceGet() -- never a
     second, independently-typed JSON-shape copy; importFileNative() calls the EXISTING
     _wsImportFromJson() -- never a second, independently-typed validation copy.
  5. Both functions gate on _capabilities.fileSystemAccess directly -- never a second, re-typed raw
     `typeof window.showSaveFilePicker` check of their own (the same drift PR 19 exists to rule out).
  6. VW.channel/VW.workspace's original 10 members/VW.windows/VW.capabilities/VW.locks export shape
     is exactly what PR 22 left it as, plus the two new members added by this PR.
  7. workspaces.html: the existing downloadFile()/<input type="file"> UI is completely untouched
     (same call-site text PR 16's own test_f_workspace_reopen.py already checks), and the new
     "Save to file.../Open from file..." UI is genuinely wired to real buttons that call the new
     functions, feature-detected on VW.capabilities.fileSystemAccess -- not an orphaned API addition.
  8. No ES6 syntax in the new shared.js code (belt-and-suspenders alongside rps_lint.py itself).

PR 3's, PR 19's, PR 21's, PR 22's own original test suites (test_workspace_export_import.py,
test_vw_capabilities.py, test_vw_workspace_indexeddb.py, test_vw_workspace_schema_version.py,
test_shared_workspace.py, test_f_workspace_reopen.py, test_vw_locks.py, test_a2_popout.py) are run
UNMODIFIED against this new code by their own existing wrapper scripts (auto-discovered by
verify_all.py, not duplicated here) -- every one of them was re-run by hand while building this PR
and stayed fully green with no assertion needing to change, since this PR adds new members/functions
only and touches no existing record/export/UI shape those suites check byte-for-byte.

Gracefully skips (never false-fails) the node-dependent layer in an environment without node, same as
the rest of this codebase's node-dependent checks. The source-level checks have no node dependency
and always run.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
UI = os.path.join(ENGINE, "ui")
SHARED_JS = os.path.join(UI, "shared.js")
WORKSPACES_HTML = os.path.join(UI, "workspaces.html")
NODE_TEST = os.path.join(HERE, "js", "test_vw_workspace_fsa_node.js")


def read(path):
    return open(path, encoding="utf-8").read()


def main():
    tests = []
    shared_js = read(SHARED_JS)
    workspaces_html = read(WORKSPACES_HTML)

    # ============================================================================================
    # Layer 3 (static, no node dependency): the new code is declared, exported off VW.workspace,
    # and lands after PR 3's workspaceImportFile but BEFORE popoutControl()'s own section -- never
    # between popoutControl() and the final "var VW = {" marker.
    # ============================================================================================
    tests.append(("shared_js_declares_file_handles_map", "var _wsFileHandles = {};" in shared_js))
    tests.append(("shared_js_declares_export_file_native_function",
                  "function workspaceExportFileNative(id)" in shared_js))
    tests.append(("shared_js_declares_import_file_native_function",
                  "function workspaceImportFileNative()" in shared_js))
    tests.append(("shared_js_exports_export_file_native_off_vw_workspace",
                  "exportFileNative: workspaceExportFileNative," in shared_js))
    tests.append(("shared_js_exports_import_file_native_off_vw_workspace",
                  "importFileNative: workspaceImportFileNative," in shared_js))

    import_file_idx = shared_js.find("function workspaceImportFile(blob)")
    file_handles_idx = shared_js.find("var _wsFileHandles = {};")
    export_native_idx = shared_js.find("function workspaceExportFileNative(id)")
    import_native_idx = shared_js.find("function workspaceImportFileNative()")
    popout_idx = shared_js.find("function popoutControl(opts)")
    vw_assign_idx = shared_js.find("\n  var VW = {")
    tests.append(("new_fsa_code_declared_after_pr3_import_file_and_before_popout_control",
                  import_file_idx != -1 and file_handles_idx != -1 and export_native_idx != -1 and
                  import_native_idx != -1 and popout_idx != -1 and vw_assign_idx != -1 and
                  import_file_idx < file_handles_idx < export_native_idx < import_native_idx <
                  popout_idx < vw_assign_idx))

    # ============================================================================================
    # Layer 4: exportFileNative()/importFileNative() reuse PR 3's own JSON-shape/validation
    # functions directly -- never a second, independently-typed copy of either.
    # ============================================================================================
    ef_end = shared_js.find("\n  function workspaceImportFileNative()", export_native_idx)
    export_native_body = shared_js[export_native_idx:ef_end] if export_native_idx != -1 and ef_end != -1 else ""
    tests.append(("export_file_native_reuses_ws_export_payload_directly",
                  "_wsExportPayload(ws)" in export_native_body))
    tests.append(("export_file_native_reuses_ws_export_file_for_the_fallback_blob",
                  "workspaceExportFile(id)" in export_native_body))
    tests.append(("export_file_native_reuses_workspace_get_directly",
                  "workspaceGet(id)" in export_native_body))
    tests.append(("export_file_native_has_no_hand_rolled_second_json_shape",
                  "JSON.stringify({ name:" not in export_native_body and
                  '"name":' not in export_native_body))

    if_end = shared_js.find("\n  /* v1.53.0: VW.windows", import_native_idx)
    import_native_body = shared_js[import_native_idx:if_end] if import_native_idx != -1 and if_end != -1 else ""
    tests.append(("import_file_native_reuses_ws_import_from_json_directly",
                  "_wsImportFromJson(text)" in import_native_body))
    tests.append(("import_file_native_has_no_second_independently_typed_validation_of_its_own",
                  "_wsValidateImportShape" not in import_native_body and
                  "_wsClassifyRecordSchema" not in import_native_body))

    # ============================================================================================
    # Layer 5: both functions gate on _capabilities.fileSystemAccess directly -- never a second,
    # re-typed raw "typeof window.showSaveFilePicker" check of their own.
    # ============================================================================================
    tests.append(("export_file_native_gates_on_capabilities_file_system_access_directly",
                  "_capabilities.fileSystemAccess" in export_native_body))
    tests.append(("export_file_native_has_no_second_raw_feature_check_of_its_own",
                  "typeof window.showSaveFilePicker" not in export_native_body))
    tests.append(("import_file_native_gates_on_capabilities_file_system_access_directly",
                  "_capabilities.fileSystemAccess" in import_native_body))
    tests.append(("import_file_native_has_no_second_raw_feature_check_of_its_own",
                  "typeof window.showSaveFilePicker" not in import_native_body))

    # ---- cancel handling: AbortError is special-cased in both directions ----
    tests.append(("export_file_native_special_cases_abort_error",
                  'err.name === "AbortError"' in export_native_body or
                  "_wsPickSaveHandleAndWrite" in export_native_body))
    pick_start = shared_js.find("function _wsPickSaveHandleAndWrite(")
    pick_end = shared_js.find("\n  }", pick_start) + 4 if pick_start != -1 else -1
    pick_body = shared_js[pick_start:pick_end] if pick_start != -1 else ""
    tests.append(("pick_save_handle_special_cases_abort_error_as_a_non_rejection",
                  pick_start != -1 and 'err.name === "AbortError"' in pick_body and "return false;" in pick_body))
    tests.append(("import_file_native_special_cases_abort_error_as_a_non_rejection",
                  'err.name === "AbortError"' in import_native_body and "return null;" in import_native_body))

    # ---- permission re-verification: a stale handle is dropped, never assumed still-writable ----
    can_write_start = shared_js.find("function _wsHandleCanWrite(")
    can_write_end = shared_js.find("\n  }", can_write_start) + 4 if can_write_start != -1 else -1
    can_write_body = shared_js[can_write_start:can_write_end] if can_write_start != -1 else ""
    tests.append(("handle_can_write_calls_query_permission",
                  can_write_start != -1 and "queryPermission" in can_write_body))
    tests.append(("handle_can_write_calls_request_permission_when_not_already_granted",
                  can_write_start != -1 and "requestPermission" in can_write_body))
    tests.append(("export_file_native_drops_a_stale_handle_before_falling_back",
                  "delete _wsFileHandles[id];" in export_native_body))

    # ============================================================================================
    # Layer 6: VW.channel / VW.workspace (original 10 members, unchanged) / VW.windows /
    # VW.capabilities / VW.locks export shape is exactly what PR 22 left it as, plus this PR's two
    # new members.
    # ============================================================================================
    tests.append(("vw_channel_export_unchanged",
                  "channel: { publish: channelPublish, subscribe: channelSubscribe }," in shared_js))
    tests.append(("vw_workspace_export_unchanged_prefix",
                  "workspace: { create: workspaceCreate, list: workspaceList,\n"
                  "                          get: workspaceGet, touch: workspaceTouch, "
                  "delete: workspaceDelete,\n"
                  "                          exportUrl: workspaceExportUrl, "
                  "exportFile: workspaceExportFile,\n"
                  "                          importUrl: workspaceImportUrl, "
                  "importFile: workspaceImportFile,\n" in shared_js))
    tests.append(("vw_workspace_schema_debug_members_still_present",
                  re.search(r"workspace:\s*\{.*?_schemaVersion:\s*_WS_SCHEMA_VERSION,"
                             r".*?_classifySchemaVersion:\s*_wsClassifyRecordSchema,"
                             r".*?_lastGetSchemaRefusal:\s*function\s*\(\)",
                             shared_js, re.S) is not None))
    tests.append(("vw_workspace_fsa_members_added",
                  re.search(r"workspace:\s*\{.*?exportFileNative:\s*workspaceExportFileNative,"
                             r"\s*importFileNative:\s*workspaceImportFileNative,",
                             shared_js, re.S) is not None))
    tests.append(("vw_windows_export_unchanged",
                  "windows: { open: windowsOpen, registry: windowsRegistry," in shared_js))
    tests.append(("vw_capabilities_export_unchanged", "capabilities: _capabilities," in shared_js))
    tests.append(("vw_locks_export_unchanged",
                  "locks: { withLock: locksWithLock, _debugPendingCount: _locksDebugPendingCount } };"
                  in shared_js))

    # ============================================================================================
    # Layer 7: workspaces.html -- the existing blob/<a download> and <input type="file"> UI is
    # completely untouched, and the new native-dialog UI is genuinely wired (not an orphaned API).
    # ============================================================================================
    tests.append(("workspaces_html_downloadfile_function_untouched",
                  "function downloadFile(id){" in workspaces_html and
                  "URL.createObjectURL(blob)" in workspaces_html and
                  "a.download=name+'.json'" in workspaces_html))
    tests.append(("workspaces_html_dlfile_button_untouched",
                  "class=\"dlfile\"" in workspaces_html and
                  "downloadFile(b.getAttribute('data-id'))" in workspaces_html))
    tests.append(("workspaces_html_import_file_input_pair_untouched",
                  "id=\"importFileBtn\"" in workspaces_html and
                  'id="importFile"' in workspaces_html and
                  "VW.workspace.importFile(f)" in workspaces_html))
    tests.append(("workspaces_html_declares_fsa_availability_check",
                  "function fsaAvailable(){" in workspaces_html and
                  "VW.capabilities.fileSystemAccess" in workspaces_html))
    tests.append(("workspaces_html_save_to_file_button_is_feature_detected_and_wired",
                  "class=\"savenative\"" in workspaces_html and
                  "fsaOn?" in workspaces_html and
                  "saveFileNative(b.getAttribute('data-id'))" in workspaces_html))
    tests.append(("workspaces_html_save_file_native_calls_export_file_native",
                  "function saveFileNative(id){" in workspaces_html and
                  "VW.workspace.exportFileNative(id)" in workspaces_html))
    tests.append(("workspaces_html_open_from_file_button_is_feature_detected_and_wired",
                  'id="importFileNativeBtn"' in workspaces_html and
                  "if(fsaAvailable()){" in workspaces_html and
                  "VW.workspace.importFileNative()" in workspaces_html))
    tests.append(("workspaces_html_open_from_file_button_starts_hidden",
                  re.search(r'<button id="importFileNativeBtn" hidden>', workspaces_html) is not None))
    tests.append(("workspaces_html_import_file_native_treats_null_as_cancel_not_error",
                  re.search(r"VW\.workspace\.importFileNative\(\)\.then\(function\s*\(id\)\{\s*"
                             r"if\(!id\)\s*return;", workspaces_html) is not None))

    # ============================================================================================
    # Layer 8: no ES6 syntax in the new code (belt-and-suspenders alongside rps_lint.py itself).
    # ============================================================================================
    new_section = shared_js[import_file_idx:popout_idx] if import_file_idx != -1 and popout_idx != -1 else ""
    fsa_section = new_section[new_section.find("v1.77.0"):] if "v1.77.0" in new_section else new_section
    tests.append(("no_arrow_functions_in_new_fsa_code", "=>" not in fsa_section))
    tests.append(("no_const_or_let_in_new_fsa_code",
                  re.search(r"(?<![\w.])(const|let)\s+\w", fsa_section) is None))
    tests.append(("no_template_literals_in_new_fsa_code", "`" not in fsa_section))
    tests.append(("no_async_await_in_new_fsa_code",
                  re.search(r"(?<![\w.])(async|await)\s", fsa_section) is None))
    tests.append(("no_spread_or_rest_in_new_fsa_code", "..." not in fsa_section))

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

        r1b = subprocess.run(["node", "--check", NODE_TEST], capture_output=True, text=True)
        tests.append(("fsa_node_test_itself_parses_with_node", r1b.returncode == 0))
        if r1b.returncode != 0:
            print("  node --check (test file) stderr:", r1b.stderr.strip()[:500])

        r2 = subprocess.run(["node", NODE_TEST], capture_output=True, text=True)
        for line in r2.stdout.splitlines():
            if line.startswith("PASS ") or line.startswith("FAIL "):
                print("  " + line)
        tests.append(("vw_workspace_fsa_behavior (see indented PASS/FAIL lines above)",
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
