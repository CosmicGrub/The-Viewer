#!/usr/bin/env python3
"""B -- curated workspace launcher (multi-window support, PR 15 of
docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md, stage 5).

WHAT THIS COVERS, structurally, against the real shipped files (this suite has no in-browser runner,
same limitation every prior PR in this initiative states plainly rather than glosses over):

  - jobcard.html's "Launch Work Order" button exists (a real <button>, not a div+click handler), calls
    VW.workspace.create() with items that unambiguously encode /procedure, /torque, /part IN THAT
    ORDER, then opens each of those 3 pages via VW.windows.open() -- create happens BEFORE any window
    opens, matching the plan's own "persist a real workspace record before opening anything" order.
  - solve.html's "Launch Solve It" button does the same for /troubleshoot, /procedure, /locate.
  - BOTH buttons reuse shared.js's OWN window-naming transform (VW.popoutWindowName, the exact
    function A1's popoutName()/A2's popoutControl() already use) rather than a third,
    independently-drifting copy -- proved by SOURCE-TEXT comparison, the same technique
    test_a2_popout.py already used to compare A1 vs A2's own naming transforms: neither page contains
    the naming regex's own literal fragments, and the exact call-site text
    "VW.windows.open(url, {name: VW.popoutWindowName(url)});" is byte-for-byte identical in both
    files.
  - shared.js exports the SAME _popoutWindowName function used internally by popoutControl -- not a
    wrapper, not a second copy -- as VW.popoutWindowName, so external callers (this PR) and the
    existing per-page pop-out control (PR 14) can never drift against each other.
  - the VW.capabilities.tier guard (docs/superpowers/specs/2026-09-03-multi-window-tabs-design.md,
    item 8's "Addition this revision") is written defensively in both launch functions: VW.capabilities
    is Stage 6 (PR 19-25) and does not exist on main yet, so every access to it is guarded so a missing
    VW.capabilities can never throw -- checked here by requiring the short-circuited access pattern and
    by requiring ".capabilities" appear EXACTLY ONCE per function (the one guarded assignment; a
    second, unguarded occurrence would be a real "throws when VW.capabilities is absent" bug).
  - both pages thread the CURRENT #q value (read at click time, not page load) onto every launched
    URL as "?q=..." -- the same convention index.html's threadQuery()/A1 already established for
    every menu link.

WHAT THIS CANNOT COVER, stated plainly: whether clicking "Launch Work Order"/"Launch Solve It" in a
real browser actually opens 3 windows without a popup-blocker intervening on the 2nd/3rd, and whether
a previously-opened /procedure window is genuinely reused rather than duplicated. That is real
window.open()/browser behavior with no in-browser runner in this suite -- called out as a manual check
in the PR body, the same way test_a2_popout.py and test_shared_windows.py already treat their own
real-browser-only behavior.

Self-contained; no corpus, no server. Run:  python engine/tests/test_b_workspace_launcher.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
UI = os.path.join(ENGINE, "ui")
SHARED_JS = os.path.join(UI, "shared.js")
JOBCARD_HTML = os.path.join(UI, "jobcard.html")
SOLVE_HTML = os.path.join(UI, "solve.html")

# The exact call-site text both pages must share, byte-for-byte -- proves both route through the SAME
# shared.js helper instead of two independently-drifting copies (the technique test_a2_popout.py
# already used for A1 vs A2's naming transforms, applied here to this PR's own reuse point).
SHARED_OPEN_CALL = "VW.windows.open(url, {name: VW.popoutWindowName(url)});"

# Fragments of shared.js's OWN naming regex -- if either page contains these, it has re-implemented
# the transform instead of calling through VW.popoutWindowName.
NAMING_REGEX_FRAGMENTS = [r"[^A-Za-z0-9_-]+", r"replace(/^\/+/"]

# Each page: (path, button id, launch fn name, expected pages IN ORDER, the quote char that page's own
# inline script uses for string literals, workspace-name prefix, the EXACT onclick-wiring text that
# follows the function -- used only as the end-of-body slice marker, since the two pages wire their
# buttons differently (jobcard chains directly, solve guards the lookup first) and this test must not
# assume either style is the other's).
PAGES = [
    dict(path=JOBCARD_HTML, btn_id="launchWO", fn_name="launchWorkOrder",
         pages=["/procedure", "/torque", "/part"], q="'", ws_name="Work Order",
         onclick_marker="$('#launchWO').onclick=launchWorkOrder;"),
    dict(path=SOLVE_HTML, btn_id="launchSI", fn_name="launchSolveIt",
         pages=["/troubleshoot", "/procedure", "/locate"], q='"', ws_name="Solve It",
         onclick_marker='var launchSIBtn=$("#launchSI"); if(launchSIBtn) launchSIBtn.onclick=launchSolveIt;'),
]

passed, failed = [], []


def ok(name, cond):
    (passed if cond else failed).append(name)


def say(msg):
    """ASCII-only diagnostic print -- see test_a2_popout.py's identical helper/rationale: a plain
    print() of non-ASCII page content can UnicodeEncodeError on a cp1252 console and, inside a broad
    try/except, silently swallow every assertion after it."""
    print(str(msg).encode("ascii", "backslashreplace").decode("ascii"))


def read(path):
    return open(path, encoding="utf-8").read()


def strip_line_comments(text):
    """Drops everything from '//' to end of line, so a check that must look only at real CODE (never
    at a comment's own PROSE mention of the thing being checked -- both launch functions' comments
    talk about "VW.capabilities.tier" in plain English) can't be fooled by the prose. Both functions
    here use only '//' line comments, never a '/* */' block, and neither contains a '//' inside a
    string literal, so this simple per-line split is exact for this input -- not a general-purpose JS
    comment stripper."""
    return "\n".join(line[:line.find("//")] if "//" in line else line for line in text.split("\n"))


def function_body(src, fn_marker, end_marker):
    """Slices out one function's source text, from its declaration through the given end marker (the
    onclick-wiring line right after each launch function, in both pages) -- narrow enough that a
    lookalike string elsewhere in a multi-hundred-line file can never be mistaken for part of it."""
    if fn_marker not in src:
        raise AssertionError("marker not found: %r" % fn_marker)
    start = src.index(fn_marker)
    if end_marker not in src[start:]:
        raise AssertionError("end marker not found after %r: %r" % (fn_marker, end_marker))
    end = src.index(end_marker, start) + len(end_marker)
    return src[start:end]


try:
    shared_js = read(SHARED_JS)
    jobcard_html = read(JOBCARD_HTML)
    solve_html = read(SOLVE_HTML)
    html_by_path = {JOBCARD_HTML: jobcard_html, SOLVE_HTML: solve_html}

    # ============================================================================================
    # shared.js: VW.popoutWindowName is exported and IS _popoutWindowName -- not a wrapper, not a
    # second copy. (PR 14's own naming-helper declaration and A1-identity are re-verified by
    # test_a2_popout.py; not re-checked here, only that THIS PR's export reuses the SAME function.)
    # ============================================================================================
    ok("shared_js_declares_the_naming_helper",
       "function _popoutWindowName(pathOrHref)" in shared_js)
    ok("shared_js_exports_popoutWindowName_as_the_same_function_not_a_wrapper",
       re.search(r"popoutControl:\s*popoutControl,\s*popoutWindowName:\s*_popoutWindowName",
                 shared_js) is not None)

    # ============================================================================================
    # Both launch functions, in both pages.
    # ============================================================================================
    for spec in PAGES:
        path = spec["path"]; btn_id = spec["btn_id"]; fn_name = spec["fn_name"]
        pages = spec["pages"]; q = spec["q"]; ws_name = spec["ws_name"]
        html = html_by_path[path]
        tag = os.path.basename(path)
        q_ = re.escape(q)

        # ---- a real, keyboard-focusable <button>, never a div+click handler (this project's own
        #      [1.46.0]/[1.47.0] accessibility convention, the same one test_a2_popout.py checks for
        #      A2's own pop-out pill).
        ok("%s_launch_button_exists" % tag, ('id="%s"' % btn_id) in html)
        ok("%s_launch_control_is_a_real_button_element" % tag,
           re.search(r'<button[^>]*id="%s"' % re.escape(btn_id), html) is not None)

        # ---- the launch function itself, narrowed to its own body (through the onclick-wiring line
        #      right after it), so every check below can never accidentally match some OTHER function
        #      in the same file.
        fn_marker = "function %s(){" % fn_name
        ok("%s_declares_the_launch_function" % tag, fn_marker in html)
        ok("%s_wires_the_button_to_the_launch_function" % tag, spec["onclick_marker"] in html)
        body = function_body(html, fn_marker, spec["onclick_marker"])

        # ---- the items array unambiguously encodes the 3 pages IN ORDER: same "pages" array literal
        #      feeds both the items-building loop and the window-opening loop, so proving the literal
        #      is right proves BOTH consumers are right, and proves they cannot drift from each other.
        pages_literal = "[" + ",".join(q + p + q for p in pages) + "]"
        ok("%s_pages_array_matches_the_spec_order_exactly" % tag,
           ("var pages=" + pages_literal) in body)
        # items must be built from that SAME pages array (not a second, independent literal) --
        # {page:pages[i], ...} inside a loop bounded by pages.length.
        ok("%s_items_are_built_from_the_pages_array_not_a_second_copy" % tag,
           re.search(r"items\.push\(\{page:pages\[i\],\s*params:", body) is not None)
        ok("%s_items_loop_is_bounded_by_the_pages_array_length" % tag,
           "for(var i=0;i<pages.length;i++)" in body)

        # ---- VW.workspace.create() is called exactly once, with (name, items, 'template'/"template"),
        #      and it happens BEFORE any VW.windows.open() call -- the plan's own required order
        #      ("persist a real workspace record before opening anything").
        create_matches = list(re.finditer(r"VW\.workspace\.create\(", body))
        ok("%s_calls_workspace_create_exactly_once" % tag, len(create_matches) == 1)
        ok("%s_workspace_create_uses_template_source" % tag,
           re.search(r"VW\.workspace\.create\(name,\s*items,\s*%stemplate%s\)" % (q_, q_), body)
           is not None)
        ok("%s_workspace_name_reflects_the_launch_set" % tag, (q + ws_name) in body)
        open_matches = list(re.finditer(r"VW\.windows\.open\(", body))
        ok("%s_calls_windows_open" % tag, len(open_matches) >= 1)
        if create_matches and open_matches:
            ok("%s_workspace_create_happens_before_any_window_opens" % tag,
               create_matches[0].start() < open_matches[0].start())

        # ---- the window-opening loop runs over the SAME pages array (so all 3, and only those 3,
        #      pages actually open) and reuses shared.js's OWN naming helper -- never a re-implemented
        #      regex -- via the EXACT shared call-site text (byte-for-byte, checked against the other
        #      page below).
        ok("%s_open_loop_is_bounded_by_the_pages_array_length" % tag,
           "for(var j=0;j<pages.length;j++)" in body)
        ok("%s_reuses_the_shared_windows_open_call_site" % tag, SHARED_OPEN_CALL in body)
        for frag in NAMING_REGEX_FRAGMENTS:
            ok("%s_does_not_reimplement_the_naming_regex(%s)" % (tag, frag), frag not in html)

        # ---- current #q value read at CLICK time (inside the function body, not hoisted to page-load
        #      / outer scope) and threaded onto every launched URL as "?q=..." -- A1's own
        #      threadQuery() convention, applied here.
        ok("%s_reads_hash_q_value_inside_the_launch_function" % tag,
           ("$(%s#q%s).value" % (q, q)) in body)
        ok("%s_threads_q_onto_the_launched_url" % tag, (q + "?q=" + q) in body)

        # ---- VW.capabilities.tier guard: feature-detected, never throws when VW.capabilities is
        #      absent. Proved three ways, against CODE ONLY (comments here talk ABOUT
        #      "VW.capabilities.tier" in plain English, so the count/substring checks below strip
        #      comments first or they would be fooled by the prose describing the very thing they
        #      check): the short-circuited access pattern is present; ".capabilities" appears EXACTLY
        #      ONCE in the real code (the one guarded assignment -- a second, unguarded occurrence
        #      would be a real "throws when VW.capabilities is absent" bug); and the bare,
        #      would-throw-if-undefined chain "VW.capabilities.tier" never appears in code at all --
        #      only the guarded "caps.tier" does.
        code_only = strip_line_comments(body)
        ok("%s_capabilities_access_is_short_circuit_guarded" % tag,
           "window.VW && VW.capabilities" in code_only)
        ok("%s_tier_read_is_guarded_by_the_caps_variable" % tag,
           re.search(r"caps\s*&&\s*typeof\s+caps\.tier\s*===\s*%sstring%s" % (q_, q_), code_only)
           is not None)
        ok("%s_capabilities_is_referenced_exactly_once_in_code_ie_never_unguarded_elsewhere" % tag,
           code_only.count(".capabilities") == 1)
        ok("%s_never_accesses_capabilities_tier_directly_unguarded" % tag,
           "VW.capabilities.tier" not in code_only)
        ok("%s_tier_check_never_hard_fails_only_confirms" % tag, "window.confirm(" in code_only)

    # ============================================================================================
    # Cross-file reuse: the shared call-site text is IDENTICAL in both pages -- not just "present in
    # both", but the exact same characters, which is what makes it one shared mechanism rather than
    # two that happen to agree today and can drift tomorrow.
    # ============================================================================================
    ok("jobcard_and_solve_share_the_identical_windows_open_call_site",
       SHARED_OPEN_CALL in jobcard_html and SHARED_OPEN_CALL in solve_html)

except Exception as e:
    failed.append("b_workspace_launcher_source_checks(%s)" % e)


# ---- house convention: node --check on shared.js, plus the inline script blocks of both pages.
#      Gracefully skips (never false-fails) without node, same as every other node-dependent check in
#      this suite.
try:
    import subprocess
    import tempfile

    if subprocess.run(["node", "--version"], capture_output=True).returncode == 0:
        r = subprocess.run(["node", "--check", SHARED_JS], capture_output=True, text=True)
        ok("shared_js_parses_with_node", r.returncode == 0)
        if r.returncode != 0:
            say("  node --check shared.js: %s" % r.stderr.strip()[:400])

        for spec in PAGES:
            path = spec["path"]
            tag = os.path.basename(path)
            src = read(path)
            blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", src, re.S)
            all_clean = True
            for b in blocks:
                with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
                    f.write(b)
                    tmp_path = f.name
                r = subprocess.run(["node", "--check", tmp_path], capture_output=True, text=True)
                if r.returncode != 0:
                    all_clean = False
                    say("  node --check %s inline script: %s" % (tag, r.stderr.strip()[:400]))
                os.unlink(tmp_path)
            ok("%s_inline_scripts_parse_with_node" % tag, all_clean)
    else:
        ok("node_unavailable_skip_syntax_check", True)
except Exception as e:
    failed.append("b_workspace_launcher_node_syntax(%s)" % e)


for n in passed:
    print("PASS", n)
for n in failed:
    print("FAIL", n)
print("\n%d passed, %d failed (B curated workspace launcher, multi-window PR 15)" % (len(passed), len(failed)))
sys.exit(1 if failed else 0)

# END OF FILE
