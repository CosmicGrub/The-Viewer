#!/usr/bin/env python3
"""VW.workspace -- schema-versioned saved data (shared.js). PR 22 of
docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md (stage 6): "Adds schemaVersion to the
stored record shape; a migration-or-clean-refusal path for a version the running code doesn't
recognize... Tests: automated -- a deliberately old-shaped fixture record, assert clean migration or
clean refusal, never silent misinterpretation." Depends on PR 2 (CRUD, already merged) only --
explicitly INDEPENDENT of PR 19-21's IndexedDB work: this logic applies identically regardless of
which backing (localStorage or IndexedDB) is actually live, since both ultimately store the same
record shape and both already funnel through the one shared _wsAllForRead()/_wsAllForMutation()/
_wsCommit() chokepoint PR 21 itself established.

Three layers:
  1. `node --check` on shared.js -- syntax only.
  2. Static, source-level guarantees the node sandbox layer cannot directly see (placement, and --
     the one this PR cares most about structurally -- that the migrate-or-refuse decision lives in
     exactly ONE function, reused (never duplicated) by both the read path and the import path).
  3. tests/js/test_vw_workspace_schema_version_node.js -- NOT a syntax check. Loads the real
     shared.js into vm.createContext() sandboxes (localStorage backing only -- deliberately, per
     this PR's own independence from PR 19-21) and proves, against the actual production code: a
     new create() stamps the current schemaVersion; a deliberately old-shaped (schemaVersion-less)
     fixture record reads back correctly via list()/get() AND is durably stamped into the backing
     store afterward (a real write-back, not just a correct in-memory read); a future-schemaVersion
     fixture record is excluded from list() while every other valid record still comes back
     correctly, is NEVER deleted or mutated in storage, and get() on it returns null distinguishable
     from a genuine not-found; export carries schemaVersion and import applies the identical
     migrate-or-refuse logic, refusing a future-schemaVersion payload with PR 3's own established
     specific-Error convention and writing nothing to storage.

  PR 2's, PR 3's, and PR 21's OWN original test suites (test_shared_workspace.py,
  test_workspace_export_import.py, test_vw_workspace_indexeddb.py) are run UNMODIFIED against this
  same new code by their own existing wrapper scripts -- not duplicated here. Two of their
  assertions are EXPECTED to fail, on purpose, because this PR genuinely changes the shape they
  check byte-for-byte (adding schemaVersion is the entire point of this PR):
    - test_workspace_node.js: "stored record has no extra fields beyond the spec's six" (a stored
      workspace now carries seven fields, schemaVersion being the seventh -- exactly what the
      design spec's own record shape names).
    - test_workspace_export_import_node.js: "exportUrl payload carries exactly {name, items}" (the
      export payload now also carries schemaVersion, per this PR's point 3).
    - test_vw_workspace_indexeddb.py: "vw_workspace_export_unchanged" (a structural check that
      VW.workspace's exported literal is byte-for-byte what PR 21 left it as -- this PR
      deliberately extends it with debug/introspection members; see this file's own Layer 2c).
  Every OTHER assertion in all three suites is expected to keep passing unchanged -- see this
  repo's own verification notes for the real, counted numbers from an actual run.

Static, source-level guarantees checked here directly against shared.js's text (no node dependency,
always run):
  a. _WS_SCHEMA_VERSION / _wsClassifyRecordSchema / _wsMigrateAll land after PR 21's IndexedDB
     section and before popoutControl()'s own section -- per test_a2_popout.py's own documented
     cross-PR coupling hazard (that test slices popoutControl()'s body up to the next "var VW = {"
     marker; anything landing between popoutControl() and that marker would be silently swallowed
     into what it inspects).
  b. THE STRUCTURAL "NOT DUPLICATED" GUARANTEE, this PR's own most specific requirement:
     _wsClassifyRecordSchema is declared exactly once, and is CALLED from within both
     _wsMigrateAll() (the read path) and _wsValidateImportShape() (the import path) -- never a
     second, independently-typed copy of the same schemaVersion comparison living in either place.
  c. workspaceCreate() stamps schemaVersion via the named constant (not a bare literal), so a real
     future version bump cannot silently miss this call site.
  d. _wsExportPayload() includes schemaVersion in its returned shape.
  e. No ES6 syntax in the new code (belt-and-suspenders alongside rps_lint.py itself).

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
NODE_TEST = os.path.join(HERE, "js", "test_vw_workspace_schema_version_node.js")


def read(path):
    return open(path, encoding="utf-8").read()


def main():
    tests = []
    shared_js = read(SHARED_JS)

    # ============================================================================================
    # Layer 2a: placement -- after PR 21's IndexedDB section, before popoutControl()'s own section,
    # never between popoutControl() and the final "var VW = {" marker.
    # ============================================================================================
    idb_idx = shared_js.find("var _wsCache = null;")
    schema_const_idx = shared_js.find("var _WS_SCHEMA_VERSION = 1;")
    classify_idx = shared_js.find("function _wsClassifyRecordSchema(rec)")
    migrate_all_idx = shared_js.find("function _wsMigrateAll(all)")
    popout_idx = shared_js.find("function popoutControl(opts)")
    vw_assign_idx = shared_js.find("\n  var VW = {")
    tests.append(("schema_version_code_lands_after_idb_section_and_before_workspace_create",
                  idb_idx != -1 and schema_const_idx != -1 and
                  idb_idx < schema_const_idx < shared_js.find("function workspaceCreate(name, items, source)")))
    tests.append(("schema_version_code_lands_well_before_popout_control_and_vw_assembly",
                  schema_const_idx != -1 and popout_idx != -1 and vw_assign_idx != -1 and
                  schema_const_idx < classify_idx < migrate_all_idx < popout_idx < vw_assign_idx))

    # ============================================================================================
    # Layer 2b: THE STRUCTURAL "NOT DUPLICATED" GUARANTEE -- _wsClassifyRecordSchema is declared
    # exactly once, and both the read-path migration and the import-path validation genuinely call
    # THIS function (not a second, independently-typed copy of the same comparison).
    # ============================================================================================
    tests.append(("classify_schema_version_declared_exactly_once",
                  shared_js.count("function _wsClassifyRecordSchema(rec)") == 1))
    tests.append(("migrate_all_calls_the_shared_classifier",
                  re.search(r"function _wsMigrateAll\(all\) \{.*?_wsClassifyRecordSchema\(rec\)",
                             shared_js, re.S) is not None))
    tests.append(("validate_import_shape_calls_the_shared_classifier",
                  re.search(r"function _wsValidateImportShape\(parsed\) \{.*?_wsClassifyRecordSchema\(parsed\)",
                             shared_js, re.S) is not None))
    # Negative check: _wsValidateImportShape's OWN body must not also hand-roll a second
    # "schemaVersion > _WS_SCHEMA_VERSION"-style comparison of its own alongside the shared call --
    # that would be exactly the "second, independently-typed copy" this PR's own plan explicitly
    # rules out.
    validate_start = shared_js.find("function _wsValidateImportShape(parsed)")
    validate_end = shared_js.find("\n  function _wsImportFromJson(raw)")
    validate_body = shared_js[validate_start:validate_end] if validate_start != -1 and validate_end != -1 else ""
    tests.append(("validate_import_shape_has_no_second_hand_rolled_schema_comparison",
                  validate_start != -1 and
                  re.search(r"schemaVersion\s*[<>]", validate_body.replace("_wsClassifyRecordSchema(parsed)", ""))
                  is None))

    # ============================================================================================
    # Layer 2c: workspaceCreate() stamps the named constant, not a bare numeric literal.
    # ============================================================================================
    create_start = shared_js.find("function workspaceCreate(name, items, source)")
    create_end = shared_js.find("\n  /* list()", create_start) if create_start != -1 else -1
    create_body = shared_js[create_start:create_end] if create_start != -1 and create_end != -1 else ""
    tests.append(("workspace_create_stamps_schema_version_via_the_named_constant",
                  create_start != -1 and "schemaVersion: _WS_SCHEMA_VERSION" in create_body))

    # ============================================================================================
    # Layer 2d: the export payload includes schemaVersion.
    # ============================================================================================
    tests.append(("export_payload_includes_schema_version",
                  "return { name: ws.name, items: ws.items, schemaVersion: _WS_SCHEMA_VERSION };"
                  in shared_js))

    # ============================================================================================
    # Layer 2e: no ES6 syntax in the new code (belt-and-suspenders alongside rps_lint.py).
    # ============================================================================================
    new_section = shared_js[schema_const_idx:popout_idx] if schema_const_idx != -1 and popout_idx != -1 else ""
    tests.append(("no_arrow_functions_in_new_schema_version_code", "=>" not in new_section))
    tests.append(("no_const_or_let_in_new_schema_version_code",
                  re.search(r"(?<![\w.])(const|let)\s+\w", new_section) is None))
    tests.append(("no_template_literals_in_new_schema_version_code", "`" not in new_section))
    tests.append(("no_async_await_in_new_schema_version_code",
                  re.search(r"(?<![\w.])async\s", new_section) is None and
                  re.search(r"(?<![\w.])await\s", new_section) is None))
    tests.append(("no_spread_or_rest_in_new_schema_version_code", "..." not in new_section))

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
        tests.append(("vw_workspace_schema_version_behavior (see indented PASS/FAIL lines above)",
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
