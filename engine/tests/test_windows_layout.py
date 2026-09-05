#!/usr/bin/env python3
"""VW.windows -- layout capture + user-triggered restore (shared.js). PR 6 of
docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md (stage 2), inserted out of the plan doc's
own stage order because PR 17 (C -- screen-aware placement, next in the queue) depends on it existing
first -- same "landed out of order, for a real downstream dependency" shape PR 3 already established.

Three layers:
  1. `node --check` on shared.js -- syntax only, same convention every other node-dependent check in
     this suite uses.
  2. tests/js/test_windows_layout_node.js -- NOT a syntax check. Loads the real shared.js into a
     vm.createContext() sandbox (the same approach test_windows_node.js/PR 5 already uses) and proves,
     against the real production VW.windows.registry()/open()/restoreLayout() code: live (not
     cached-at-open-time) bounds reads, per-FIELD-independent degradation to null on a throwing/
     unreadable property (never taking down another window's entry in the same call), a sane bounds
     hint threading a real window.open() features string on a genuinely NEW open, an implausible hint
     (or an unreadable/non-positive window.screen) being dropped gracefully -- never a throw, always a
     normal open -- a reuse NEVER threading bounds even when the reusing call itself offers them, and
     restoreLayout() calling THROUGH windowsOpen() (proven by the identical broadcast envelope shape,
     not a re-implemented parallel path) once per well-formed entry, skipping a malformed one without
     aborting the rest of the batch.
  3. A static, source-level guarantee that cannot be exercised in a sandbox at all: restoreLayout() is
     NEVER invoked from anywhere in this codebase, load/init handler or otherwise -- checked two ways
     (see below), because the one thing worse than this PR's API not existing yet is it existing and
     something silently auto-restoring a technician's windows on page load, which is exactly the
     "a web page cannot run code 'on app launch' unprompted" case the design doc's own honest note
     names. This is a real behavioral guarantee, not a style preference: an accidental auto-restore
     would pop windows on every page load with no user action behind it.

WHAT THIS CANNOT PROVE, stated plainly rather than glossed over: whether a real browser genuinely
honors window.open()'s position/size features on a brand-new window, and whether it genuinely ignores
them on a later reuse of an already-named one. Both are named, honestly, as real browser/window-manager
behavior in shared.js's own comment and in the PR body -- Node has no window.open to be right or wrong
about either, and confirming the actual on-screen placement (including the "monitor unplugged since
the position was saved" fallback actually landing somewhere reachable) needs a human with a real,
possibly multi-monitor, machine. That manual check is called out as manual in the PR, the same honest
framing every other real-hardware-only behavior in this initiative already uses.

Gracefully skips (never false-fails) the node-dependent layers in an environment without node, same as
the rest of this codebase's node-dependent checks. The source-level restoreLayout-never-auto-invoked
check has no node dependency and always runs.
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
NODE_TEST = os.path.join(HERE, "js", "test_windows_layout_node.js")

DECL = "function windowsRestoreLayout(entries)"


def read(path):
    return open(path, encoding="utf-8").read()


def strip_block_comments(src):
    """Removes every /* ... */ block comment from a JS source string. shared.js is real, valid,
    node --check-verified JS with no "/*"/"*/ " inside string or regex literals near the code this
    checks, so a straightforward non-greedy regex is safe here -- the same assumption
    test_workspace_export_import.py's own reconciliation note about avoiding false-positive lint
    hits already relies on implicitly."""
    return re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)


def real_call_sites(code_only_src):
    """Every 'restoreLayout(' occurrence in COMMENT-STRIPPED source that is NOT the
    'function windowsRestoreLayout(entries)' declaration itself -- i.e. an actual invocation. Matches
    both the internal name (windowsRestoreLayout) and any external-style call
    (....restoreLayout(...))."""
    hits = []
    for m in re.finditer(r"[A-Za-z_][A-Za-z0-9_.]*restoreLayout\(", code_only_src):
        start = m.start()
        prefix = code_only_src[:start].rstrip()
        if prefix.endswith("function windowsRestoreLayout".rstrip("(")) or \
           prefix.endswith("function windowsRestoreLayout"):
            continue
        hits.append(start)
    return hits


def comment_spans(src):
    return [(m.start(), m.end()) for m in re.finditer(r"/\*.*?\*/", src, re.DOTALL)]


def range_overlaps_any_span(start, end, spans):
    """Whether [start, end) intersects any comment span at all -- used with a whole LINE's range
    rather than a single offset, because the line as extracted from the diff carries its own leading
    indentation, so the position `find()` reports for the line is a few characters BEFORE the actual
    "/*" that opens its comment (an exact single-offset containment check gets this wrong for exactly
    the opening line of a block comment, which is the common case here)."""
    return any(not (end <= s or start >= e) for s, e in spans)


def git_added_lines(rel_path):
    """Best-effort: the lines this PR's own diff actually ADDS to rel_path, against the merge-base
    with origin/main -- diffed against the WORKING TREE (`git diff <base> -- path`, not `<base>..HEAD`)
    so this is correct whether this PR's changes are already committed or still sitting uncommitted in
    the working tree, which is exactly the state this test is meant to run in during development, right
    before the one commit this PR makes. Returns None (never raises) when git/the remote ref is
    unavailable, so this check degrades to being skipped rather than false-failing in an environment
    without that history -- the comment-stripped full-file scan above is the check that always runs
    regardless."""
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
        out = []
        for line in diff.stdout.splitlines():
            if line.startswith("+++") or line.startswith("---"):
                continue
            if line.startswith("+"):
                out.append(line[1:])
        return out
    except Exception:
        return None


def declaration_already_merged(rel_path):
    """Best-effort: whether DECL is already present in origin/main's OWN tree for rel_path (i.e. this
    PR has since been merged), via `git show origin/main:<rel_path>`. Returns None (never raises) when
    git/the remote ref is unavailable, same degrade-to-skip shape as git_added_lines above."""
    try:
        show = subprocess.run(["git", "show", "origin/main:" + rel_path],
                               cwd=REPO, capture_output=True, text=True, encoding="utf-8", timeout=15)
        if show.returncode != 0:
            return None
        return DECL in show.stdout
    except Exception:
        return None


def main():
    tests = []

    # ============================================================================================
    # Layer 3: restoreLayout() is never invoked anywhere in this codebase, load/init handler or
    # otherwise. No node dependency -- always runs.
    # ============================================================================================
    shared_js = read(SHARED_JS)
    tests.append(("shared_js_declares_windows_restore_layout", DECL in shared_js))

    code_only = strip_block_comments(shared_js)
    hits = real_call_sites(code_only)
    tests.append(("restore_layout_has_no_real_call_site_anywhere_in_shared_js_itself", len(hits) == 0))
    if hits:
        for h in hits:
            print("  unexpected call-site-shaped text near offset %d: %r" %
                  (h, code_only[max(0, h - 60):h + 30]))

    # No OTHER file this app ships (every *.html/*.js under engine/ui) calls VW.windows.restoreLayout
    # or .restoreLayout( at all -- nothing wires this PR's new function into any page in this diff,
    # load handler or button, since that UI is explicitly a later PR's job (see the PR body).
    other_hits = []
    for fn in sorted(os.listdir(UI)):
        if not (fn.endswith(".html") or fn.endswith(".js")):
            continue
        full = os.path.join(UI, fn)
        if os.path.abspath(full) == os.path.abspath(SHARED_JS):
            continue
        text = strip_block_comments(read(full))
        for m in re.finditer(r"[A-Za-z_][A-Za-z0-9_.]*restoreLayout\(", text):
            other_hits.append((fn, m.start()))
    tests.append(("no_other_ui_page_calls_restore_layout_at_all", len(other_hits) == 0))
    if other_hits:
        for fn, off in other_hits:
            print("  unexpected restoreLayout( call site in %s near offset %d" % (fn, off))

    # Corroborating, diff-scoped check (best-effort -- see git_added_lines' own docstring): every
    # ADDED line in this PR's own diff of shared.js that mentions "restoreLayout(" is either the
    # declaration itself, or -- cross-referenced against the CURRENT file's own comment spans --
    # falls inside a /* ... */ block, i.e. prose, never executable call syntax.
    added = git_added_lines("engine/ui/shared.js")
    if added is None:
        tests.append(("git_diff_added_lines_check_skipped (git/origin-main unavailable here)", True))
    else:
        spans = comment_spans(shared_js)
        bad = []
        for line in added:
            if "restoreLayout(" not in line:
                continue
            stripped = line.strip()
            if stripped.startswith(DECL):
                continue
            idx = shared_js.find(line)
            if idx == -1 or not range_overlaps_any_span(idx, idx + len(line), spans):
                bad.append(line)
        tests.append(("every_added_diff_line_mentioning_restore_layout_is_either_the_declaration_"
                       "or_inside_a_comment", len(bad) == 0))
        if bad:
            for b in bad:
                print("  suspicious added line: %r" % b)
        # Sanity: proves the check above is exercising something real, not vacuously passing because
        # the diff is empty. Two ways this is legitimately real, not vacuous:
        #   (a) the diff actually DOES add the function -- true while this PR's own changes are still
        #       uncommitted/unmerged, sitting as a live diff against origin/main; or
        #   (b) origin/main's OWN tree already declares it -- true once this PR has been merged, at
        #       which point the merge-base diff against origin/main is naturally empty for this file
        #       (there's nothing left to add), which is what makes (a) go quiet, not a sign the
        #       declaration never landed.
        # Only actually vacuous -- and left failing -- if NEITHER holds: the declaration is added by
        # neither the diff nor origin/main, i.e. genuinely missing everywhere reachable from here.
        already_merged = declaration_already_merged("engine/ui/shared.js")
        tests.append(("the_diff_genuinely_adds_the_restore_layout_declaration_"
                       "or_it_is_already_merged_into_origin_main",
                       any(DECL in l for l in added) or bool(already_merged)))

    # Also: no load/init-style wiring token anywhere near "restoreLayout" text in the raw (uncommented
    # AND commented) source -- belt-and-suspenders beyond the call-site checks above, catching even a
    # hypothetical FUTURE mis-edit that adds a real call inside a comment-adjacent block this pass
    # might mis-scope. Any addEventListener("DOMContentLoaded"/"load", ...) call in shared.js must not
    # have "restoreLayout" as a substring of its own callback body.
    for evt in ("DOMContentLoaded", "load", "pagehide"):
        for m in re.finditer(r'addEventListener\(\s*["\']' + evt + r'["\']\s*,\s*([A-Za-z_$][\w$]*)',
                              shared_js):
            handler_name = m.group(1)
            fn_marker = "function " + handler_name + "("
            if fn_marker in shared_js:
                fn_start = shared_js.index(fn_marker)
                fn_end = shared_js.find("\n  }", fn_start)
                body = shared_js[fn_start:fn_end if fn_end != -1 else fn_start + 2000]
                tests.append(("load_init_handler_%s_never_mentions_restoreLayout" % handler_name,
                               "restoreLayout" not in body))

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
        tests.append(("vw_windows_layout_capture_and_restore_behavior (see indented PASS/FAIL lines "
                       "above)", r2.returncode == 0))
        if r2.returncode != 0:
            print("  node test stderr:", r2.stderr.strip()[:1500])

    fails = [n for n, ok in tests if not ok]
    for n, ok in tests:
        print(("PASS " if ok else "FAIL ") + n)
    print("\n%d passed, %d failed" % (len(tests) - len(fails), len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
