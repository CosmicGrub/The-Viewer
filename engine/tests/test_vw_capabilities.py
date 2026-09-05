#!/usr/bin/env python3
"""VW.capabilities -- centralized feature-detection + tier registry (shared.js). PR 19 of
docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md (stage 6): "{tier, broadcastChannel,
windowPlacement, wakeLock, pictureInPicture, fileSystemAccess, webLocks, indexedDB}, computed once,
reading the existing rps.js tier plus raw typeof/"x" in window checks, AND-ed together." Depends on
nothing; PRs 20-24 read this instead of each reimplementing its own detection.

Two layers, same convention test_windows_layout.py (PR 6) already established:
  1. `node --check` on shared.js -- syntax only.
  2. tests/js/test_vw_capabilities_node.js -- NOT a syntax check. Loads the real shared.js into a
     vm.createContext() sandbox and proves, against the real production VW.capabilities code:
       - THE LIVE-READ GUARANTEE: window.RPS.mode mutated on an already-loaded sandbox (no reload)
         is reflected on the very next read -- these are live getters, never a value captured once
         when shared.js first ran. This is the single most important guarantee this PR makes: the
         plan doc's own "computed once" wording is easy to misread as "cached once," which would be
         actively wrong given how late rps.js's real tier signal actually arrives (see the PR body /
         shared.js's own comment above VW.capabilities for the full timing argument).
       - window.RPS entirely absent (most of this app's pages never load rps.js at all) -> tier reads
         the documented "modern" default, never throws.
       - each of the 7 AND-ed flags is true only when BOTH the raw browser feature is present AND
         tier is EXACTLY "modern" (a strict string match) -- including the "premium" edge case
         (an additive flag layered on an already-"modern" mode, never itself "modern").
       - a raw feature check that throws degrades ONLY that one flag to false, never any other.
       - windowPlacement's getter calls PR 17's existing _screenPlacementAvailable() directly (source-
         level: no second, re-typed copy of its raw check exists) and matches its behavior exactly.
       - VW.channel/VW.workspace/VW.windows still export exactly what they did before this PR.

This file also runs two static, source-level guarantees the node layer cannot see from inside the
sandbox:
  3. VW.capabilities is placed BEFORE popoutControl()'s own section in shared.js -- per PR 6/PR 17's
     own documented test_a2_popout.py cross-PR coupling hazard, that test slices popoutControl()'s
     body up to the next "var VW = {" marker; anything inserted between them gets silently swallowed
     into what it inspects (e.g. its exactly-one-VW.windows.open( count). Landing capabilities before
     popoutControl(), never between it and the final VW assembly, keeps that test meaningful.
  4. The plan's own "PRs 1/2/5 are NOT retrofitted to depend on it" requirement, checked precisely
     (NOT as "jobcard.html/solve.html must not mention VW.capabilities" -- they already do, on
     purpose: PR 15's launchWorkOrder()/launchSolveIt() were WRITTEN reading
     "window.VW && VW.capabilities" / "caps.tier" back when PR 15 shipped, deliberately inert
     ("VW.capabilities is Stage 6 (PR 19-25) and does not exist yet ... the day PR 19 ships a real
     VW.capabilities, this starts warning with no change needed here" -- their own comment, still
     there, unedited). This PR's job is to make that pre-wired check come ALIVE by making
     VW.capabilities real, with zero edits to either HTML file -- checked here via `git diff` against
     the merge-base with origin/main: both files carry NO added/removed lines in this PR's own diff.
     PR 17's _screenPlacementAvailable() is the other named gate -- confirmed still reading
     window.RPS.mode directly, never VW.capabilities, since IT was never rewritten to call the
     registry it now sits directly above.

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
REPO = os.path.dirname(ENGINE)
UI = os.path.join(ENGINE, "ui")
SHARED_JS = os.path.join(UI, "shared.js")
JOBCARD_HTML = os.path.join(UI, "jobcard.html")
SOLVE_HTML = os.path.join(UI, "solve.html")
NODE_TEST = os.path.join(HERE, "js", "test_vw_capabilities_node.js")


def read(path):
    return open(path, encoding="utf-8").read()


def main():
    tests = []
    shared_js = read(SHARED_JS)

    # ============================================================================================
    # Layer 3 (static, no node dependency): VW.capabilities is declared, exported off VW, and lands
    # BEFORE popoutControl()'s own section -- never between it and the final "var VW = {" marker.
    # ============================================================================================
    tests.append(("shared_js_declares_vw_capabilities_object", "var _capabilities = {};" in shared_js))
    # v1.74.0/PR 20 note: originally required capabilities: _capabilities to be the LAST key in the
    # final VW assembly (immediately followed by the object literal's closing "}"). PR 20 legitimately
    # appends a new "locks:" key straight after it (per the plan's own "PRs 20-24 read this" -- later
    # Stage 6 PRs are expected to extend this same object), so the closing delimiter is now EITHER "}"
    # (nothing appended yet) OR "," (a later PR's key follows) -- the actual guarantee this check
    # exists for ("capabilities: _capabilities appears right after checkpoint's own block, in that
    # position in the VW assembly") is unchanged either way.
    tests.append(("shared_js_exports_capabilities_off_vw",
                  re.search(r"checkpoint:\s*\{[^}]*\},\s*capabilities:\s*_capabilities\s*[,}]", shared_js,
                             re.S) is not None))

    caps_idx = shared_js.find("var _capabilities = {};")
    popout_idx = shared_js.find("function popoutControl(opts)")
    vw_assign_idx = shared_js.find("\n  var VW = {")
    tests.append(("vw_capabilities_declared_before_popout_control_never_between_it_and_var_vw",
                  caps_idx != -1 and popout_idx != -1 and vw_assign_idx != -1 and
                  caps_idx < popout_idx < vw_assign_idx))

    # All 8 documented fields defined via Object.defineProperty (plain ES5 accessor properties, never
    # the newer getter/setter shorthand syntax built into an object literal, which rps_lint's own
    # ES6-syntax scan would flag).
    fields = ["tier", "broadcastChannel", "windowPlacement", "wakeLock", "pictureInPicture",
              "fileSystemAccess", "webLocks", "indexedDB"]
    missing = [f for f in fields
               if ('Object.defineProperty(_capabilities, "%s"' % f) not in shared_js]
    tests.append(("all_8_capability_fields_defined_via_object_defineproperty (missing: %s)" % missing,
                  len(missing) == 0))
    # Never the ES6 getter shorthand for these fields (belt-and-suspenders alongside rps_lint itself).
    shorthand_hits = [f for f in fields if re.search(r"get\s+%s\s*\(\s*\)\s*\{" % re.escape(f), shared_js)]
    tests.append(("no_es6_getter_shorthand_used_for_any_capability_field (hits: %s)" % shorthand_hits,
                  len(shorthand_hits) == 0))

    # ============================================================================================
    # windowPlacement never diverges from PR 17's existing _screenPlacementAvailable() -- reused
    # directly, not re-typed. (The node layer also proves this behaviorally; this is the source-level
    # half, the same technique test_a2_popout.py already uses to compare two independently-typed
    # transforms.)
    # ============================================================================================
    wp_start = shared_js.find('Object.defineProperty(_capabilities, "windowPlacement"')
    wp_block = shared_js[wp_start:shared_js.find("});", wp_start) + 3] if wp_start != -1 else ""
    tests.append(("windowplacement_getter_calls_screenplacementavailable_directly",
                  wp_start != -1 and "_screenPlacementAvailable()" in wp_block))
    tests.append(("windowplacement_getter_has_no_second_gettscreendetails_copy_of_its_own",
                  wp_start != -1 and "getScreenDetails" not in wp_block))

    # ============================================================================================
    # Layer 4 (static, no node dependency): the plan's own "not retrofitted" requirement. PR 15's
    # jobcard.html tier check and PR 17's _screenPlacementAvailable() still gate directly on
    # window.RPS.mode -- neither reads VW.capabilities.* anywhere in this diff.
    # ============================================================================================
    sp_start = shared_js.find("function _screenPlacementAvailable()")
    sp_body = shared_js[sp_start:shared_js.find("\n  }", sp_start) + 4] if sp_start != -1 else ""
    tests.append(("screenplacementavailable_itself_still_untouched_reading_window_rps_directly",
                  sp_start != -1 and 'window.RPS && window.RPS.mode === "modern"' in sp_body and
                  "VW.capabilities" not in sp_body))

    # PR 15's jobcard.html/solve.html ALREADY reference VW.capabilities.tier -- deliberately, shipped
    # inert, waiting on this very PR (see their own "the day PR 19 ships ... no change needed here"
    # comment). The correct guarantee is therefore "this PR's own diff touches neither file at all,"
    # not "neither file mentions VW.capabilities" (they do, on purpose) -- verified via git diff
    # against the merge-base with origin/main, the same best-effort/degrade-to-skip technique
    # test_windows_layout.py's git_added_lines() already established.
    def _diff_is_empty(rel_path):
        """None (skip, never fail) when git/origin-main is unavailable here; True when this PR's own
        diff makes no change at all to rel_path; False when it does (and prints the diff)."""
        try:
            base = subprocess.run(["git", "merge-base", "origin/main", "HEAD"],
                                   cwd=REPO, capture_output=True, text=True, timeout=15)
            if base.returncode != 0 or not base.stdout.strip():
                return None
            base_sha = base.stdout.strip()
            diff = subprocess.run(["git", "diff", base_sha, "--", rel_path],
                                   cwd=REPO, capture_output=True, text=True, encoding="utf-8", timeout=15)
            if diff.returncode != 0:
                return None
            if diff.stdout.strip():
                print("  unexpected diff in %s:\n    %s" %
                      (rel_path, diff.stdout.strip().replace("\n", "\n    ")[:2000]))
                return False
            return True
        except Exception:
            return None

    for rel, disp in ((os.path.join("engine", "ui", "jobcard.html"), "jobcard_html"),
                       (os.path.join("engine", "ui", "solve.html"), "solve_html")):
        empty = _diff_is_empty(rel)
        if empty is None:
            tests.append(("%s_diff_check_skipped (git/origin-main unavailable here)" % disp, True))
        else:
            tests.append(("%s_untouched_by_this_prs_own_diff (this PR makes VW.capabilities.tier " %
                          disp + "real; jobcard/solve's own pre-wired check needs no edit to react)",
                          empty))

    if os.path.isfile(JOBCARD_HTML):
        jobcard_html = read(JOBCARD_HTML)
        tests.append(("jobcard_html_still_carries_pr15s_pre_wired_vw_capabilities_tier_check",
                      "window.VW && VW.capabilities" in jobcard_html and "caps.tier" in jobcard_html))
    else:
        tests.append(("jobcard_html_missing_skip (unexpected -- check UI dir)", False))

    if os.path.isfile(SOLVE_HTML):
        solve_html = read(SOLVE_HTML)
        tests.append(("solve_html_still_carries_pr15s_pre_wired_vw_capabilities_tier_check",
                      "window.VW && VW.capabilities" in solve_html and "caps.tier" in solve_html))
    else:
        tests.append(("solve_html_missing_skip (unexpected -- check UI dir)", False))

    # VW.channel / VW.workspace / VW.windows public export shape is exactly what it was before this
    # PR -- their own key lists in the final VW assembly are untouched by this diff (the node layer
    # additionally proves their functions still resolve and work at runtime).
    tests.append(("vw_channel_export_unchanged",
                  "channel: { publish: channelPublish, subscribe: channelSubscribe }," in shared_js))
    tests.append(("vw_workspace_export_unchanged",
                  "workspace: { create: workspaceCreate, list: workspaceList," in shared_js))
    tests.append(("vw_windows_export_unchanged",
                  "windows: { open: windowsOpen, registry: windowsRegistry," in shared_js))

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
        tests.append(("vw_capabilities_behavior (see indented PASS/FAIL lines above)",
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
