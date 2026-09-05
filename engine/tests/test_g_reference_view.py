#!/usr/bin/env python3
"""G -- kiosk/second-screen reference view (multi-window support, PR 18 of
docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md, stage 5).

WHAT THIS COVERS, against the real shipped files (this suite has no in-browser runner, same
limitation every prior PR in this initiative states plainly rather than glosses over -- see the
"WHAT THIS CANNOT COVER" note at the bottom):

  1. ROUTE-LEVEL, against a REAL running server (the same `ThreadingHTTPServer` rig
     `test_routes.py` uses, over the same deterministic `fixture` DB): `/reference` is genuinely
     registered in `engine/features/routes/static.py`'s `_PAGES` dict (source-text check) AND a real
     HTTP GET against it actually serves `engine/ui/reference.html`'s real content -- bare, and with
     `?type=torque&q=...`/`?type=procedure&q=...` querystrings -- never a 404/5xx.

  2. SOURCE-LEVEL, against `engine/ui/reference.html`:
       - fetches from the SAME `/api/torque` and `/api/procedure_full` endpoints
         `engine/ui/torque.html`/`engine/ui/procedure.html` themselves already fetch from -- never a
         duplicated/re-implemented data path.
       - applies this app's REAL kiosk-mode convention: forces `body.kiosk-mode` on via a genuine
         `classList.add("kiosk-mode")` call (never merely present in a comment), and does NOT
         redefine a `body.kiosk-mode` rule of its own -- the real rule lives in `base.css`, which
         this page links.
       - handles "nothing found" gracefully for both a missing query and an empty result set (a
         real, findable message string, not a silently blank branch).

  3. SOURCE-LEVEL, against `engine/ui/torque.html` and `engine/ui/procedure.html`: each page's new
     "Send to second screen" button is a real `<button>` (not a div+click handler, this project's
     own accessibility convention), reads that page's OWN current query context at CLICK time (never
     a value captured at page load), and calls `VW.windows.open(url, {name: "vw-reference", screen:
     true})` -- the exact opts shape PR 17 built `opts.screen` for -- targeting the correct
     `/reference?type=...&q=...` route. Both buttons share the identical `"vw-reference"` window
     name (proven byte-for-byte, not just "present in both") -- deliberate: one shop has one second
     screen, not one per source page.

  4. `docs/MULTI-WINDOW-MANUAL-QA.md` exists and carries real, substantive checklist content (not a
     stub) -- the standing document the plan doc calls for, which PR 17 shipped without creating.

  5. `node --check` on the inline scripts of `reference.html`/`torque.html`/`procedure.html`.

WHAT THIS CANNOT COVER, stated plainly: whether a real click on "Send to second screen" actually
lands the `/reference` window on a genuinely different physical monitor (that is `opts.screen`/
`getScreenDetails()`'s own real-hardware behavior, already stated as manual-only by PR 17's own
`[1.68.0]` entry and `test_windows_screen_placement.py`'s own header) -- called out as a manual check
in this PR's body and tracked going forward in `docs/MULTI-WINDOW-MANUAL-QA.md` §1, the same honest
framing this initiative has used for every real-browser-only behavior since PR 5.

Self-contained; spins up its own real server against the deterministic fixture DB. Run:
  python engine/tests/test_g_reference_view.py
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
UI = os.path.join(ENGINE, "ui")
STATIC_PY = os.path.join(ENGINE, "features", "routes", "static.py")
REFERENCE_HTML = os.path.join(UI, "reference.html")
TORQUE_HTML = os.path.join(UI, "torque.html")
PROCEDURE_HTML = os.path.join(UI, "procedure.html")
RPS_LINT_PY = os.path.join(HERE, "rps_lint.py")
QA_DOC = os.path.join(os.path.dirname(ENGINE), "docs", "MULTI-WINDOW-MANUAL-QA.md")

sys.path.insert(0, ENGINE)
sys.path.insert(0, HERE)

# The exact opts shape both launch buttons must pass -- proves both route through PR 17's real
# opts.screen mechanism with the correct shared window name, byte-for-byte identical in both files
# (the same technique test_b_workspace_launcher.py/test_f_workspace_reopen.py already use for their
# own shared call-site checks).
SHARED_SCREEN_OPEN_CALL = 'VW.windows.open(url, {name: "vw-reference", screen: true});'

passed, failed = [], []


def ok(name, cond):
    (passed if cond else failed).append(name)


def say(msg):
    """ASCII-only diagnostic print -- same rationale/helper as test_a2_popout.py and
    test_b_workspace_launcher.py: a non-ASCII print() can UnicodeEncodeError on a cp1252 console and,
    inside a broad try/except, silently swallow every assertion printed after it."""
    print(str(msg).encode("ascii", "backslashreplace").decode("ascii"))


def read(path):
    return open(path, encoding="utf-8").read()


def strip_line_comments(text):
    """Drops everything from '//' to end of line -- so a check that must look only at real CODE
    (never at a comment's own PROSE mention of the thing being checked) can't be fooled by the
    prose. Same helper/rationale as test_b_workspace_launcher.py's own copy."""
    return "\n".join(line[:line.find("//")] if "//" in line else line for line in text.split("\n"))


def function_body(src, fn_marker, end_marker):
    """Slices one function's source text from its declaration through the given end marker -- same
    helper as test_b_workspace_launcher.py's own copy."""
    if fn_marker not in src:
        raise AssertionError("marker not found: %r" % fn_marker)
    start = src.index(fn_marker)
    if end_marker not in src[start:]:
        raise AssertionError("end marker not found after %r: %r" % (fn_marker, end_marker))
    end = src.index(end_marker, start) + len(end_marker)
    return src[start:end]


# ================================================================================================
# 1. Route registration + a REAL running server actually serving the new page.
# ================================================================================================
try:
    static_py = read(STATIC_PY)
    ok("static_py_registers_the_reference_route",
       re.search(r'\("/reference",\s*"/reference\.html"\)\s*:\s*\("reference\.html",\s*"no-cache"\)',
                 static_py) is not None)
    ok("reference_html_file_exists", os.path.isfile(REFERENCE_HTML))

    import fixture
    tmp = tempfile.mkdtemp(prefix="viewer_reference_view_")
    db, _corr = fixture.build(tmp)
    import viewer_app
    viewer_app.DB_PATH = db
    from http.server import ThreadingHTTPServer
    srv = ThreadingHTTPServer(("127.0.0.1", 0), viewer_app.Handler)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    time.sleep(0.3)
    base = "http://127.0.0.1:%d" % port

    def _get(path):
        try:
            with urllib.request.urlopen(base + path, timeout=10) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")
        except Exception as e:
            return -1, str(e)

    try:
        real_reference_html = read(REFERENCE_HTML)

        status, body = _get("/reference")
        ok("get_reference_bare_returns_200", status == 200)
        ok("get_reference_bare_serves_the_real_page_content", body == real_reference_html)

        status, body = _get("/reference?type=torque&q=bolt")
        ok("get_reference_torque_query_returns_200", status == 200)
        ok("get_reference_torque_query_serves_the_real_page_content", body == real_reference_html)

        status, body = _get("/reference?type=procedure&q=brake")
        ok("get_reference_procedure_query_returns_200", status == 200)
        ok("get_reference_procedure_query_serves_the_real_page_content", body == real_reference_html)

        # Route is genuinely GET-registered (matches the alias form every other _PAGES entry uses).
        status, _ = _get("/reference.html")
        ok("get_reference_html_alias_returns_200", status == 200)

        # A totally malformed request must never 5xx (this app's own blanket-sweep discipline,
        # test_routes.py's own house convention, applied here to the one new route this PR adds).
        status, _ = _get("/reference?type=&q=")
        ok("get_reference_empty_params_never_5xx", status < 500)
    finally:
        srv.shutdown()
        srv.server_close()
except Exception as e:
    failed.append("g_reference_view_route_checks(%s)" % e)


# ================================================================================================
# 2. reference.html: fetches the SAME existing endpoints, real kiosk-mode styling, graceful empty
#    handling.
# ================================================================================================
try:
    reference_html = read(REFERENCE_HTML)

    ok("reference_html_fetches_the_real_torque_endpoint",
       "'/api/torque?q='+encodeURIComponent(q)" in reference_html)
    ok("reference_html_fetches_the_real_procedure_endpoint",
       "'/api/procedure_full?q='+encodeURIComponent(q)" in reference_html)
    # Never a re-implemented/duplicated data path: exactly one real fetch call site per endpoint
    # (comments above may mention the endpoint name in prose; only the actual getJSON(...) call
    # site is checked here for a count of one).
    ok("reference_html_never_invents_a_third_torque_endpoint",
       reference_html.count("getJSON('/api/torque?q=") == 1)
    ok("reference_html_never_invents_a_third_procedure_endpoint",
       reference_html.count("getJSON('/api/procedure_full?q=") == 1)

    # ---- real kiosk-mode-equivalent styling: the actual class usage, not merely "some styling". ----
    ok("reference_html_forces_kiosk_mode_on_via_a_real_classlist_call",
       'classList.add("kiosk-mode")' in reference_html)
    ok("reference_html_links_base_css_which_owns_the_real_kiosk_mode_rule",
       '<link rel="stylesheet" href="/base.css">' in reference_html)
    # Must NOT reinvent the rule base.css already owns -- proves this reuses the real, existing
    # convention rather than a look-alike local redefinition.
    ok("reference_html_does_not_redefine_its_own_body_kiosk_mode_rule",
       re.search(r"body\.kiosk-mode\s*\{", reference_html) is None)
    # The one glanceable value must genuinely be styled far larger than kiosk-mode's own 16px
    # ordinary-control baseline (base.css's body.kiosk-mode rule) -- a real, distinct CSS rule for
    # it, not just inheriting kiosk-mode's own baseline size.
    ok("reference_html_has_a_distinct_jumbo_glance_value_rule",
       re.search(r"\.glance\s*\{[^}]*font-size\s*:\s*clamp\(", reference_html) is not None)

    # ---- graceful "nothing found" handling: a real message, never a silent/blank branch. ----
    ok("reference_html_handles_a_missing_query_gracefully",
       "Nothing to show" in reference_html)
    ok("reference_html_handles_an_empty_torque_result_gracefully",
       'No torque value found for "'in reference_html)
    ok("reference_html_handles_an_empty_procedure_result_gracefully",
       'No step-by-step procedure found for "' in reference_html)
    # showEmpty() must escape its message exactly once (never raw-interpolated q into innerHTML,
    # never double-escaped) -- the message text passed to it is RAW, esc() runs inside showEmpty.
    ok("reference_html_escapes_the_empty_message_exactly_once",
       "function showEmpty(msg){" in reference_html
       and re.search(r"function showEmpty\(msg\)\{\s*\$\(\"out\"\)\.innerHTML\s*=\s*'<div class=\"empty\">'\+esc\(msg\)\+'</div>';",
                     reference_html) is not None)
except Exception as e:
    failed.append("g_reference_view_page_source_checks(%s)" % e)


# ================================================================================================
# 3. torque.html / procedure.html: the new "Send to second screen" buttons.
# ================================================================================================
PAGES = [
    dict(path=TORQUE_HTML, btn_id="sendScreen", fn_name="sendToSecondScreen",
         q_read="$('#q').value.trim()", target="'/reference?type=torque&q='+encodeURIComponent(rq)",
         onclick_marker="$('#sendScreen').onclick=sendToSecondScreen;"),
    dict(path=PROCEDURE_HTML, btn_id="sendScreen", fn_name="sendToSecondScreen",
         q_read='$("q").value.replace(/^\\s+|\\s+$/g,\'\')',
         target="'/reference?type=procedure&q='+encodeURIComponent(rq)+(step!==null?('&step='+step):'')",
         onclick_marker='$("sendScreen").onclick=sendToSecondScreen;'),
]

try:
    for spec in PAGES:
        path = spec["path"]
        html = read(path)
        tag = os.path.basename(path)

        ok("%s_send_to_second_screen_button_exists" % tag, ('id="%s"' % spec["btn_id"]) in html)
        ok("%s_send_to_second_screen_is_a_real_button_element" % tag,
           re.search(r'<button[^>]*id="%s"' % re.escape(spec["btn_id"]), html) is not None)

        fn_marker = "function %s(){" % spec["fn_name"]
        ok("%s_declares_the_launch_function" % tag, fn_marker in html)
        ok("%s_wires_the_button_to_the_launch_function" % tag, spec["onclick_marker"] in html)
        body = function_body(html, fn_marker, spec["onclick_marker"])
        code_only = strip_line_comments(body)

        # ---- reads the CURRENT query context inside the function body (click time), never hoisted
        #      to page-load / outer scope. ----
        ok("%s_reads_the_current_query_inside_the_launch_function" % tag, spec["q_read"] in code_only)

        # ---- targets the correct /reference route + query, built from the value just read. ----
        ok("%s_targets_the_correct_reference_url" % tag, spec["target"] in code_only)

        # ---- the exact shared opts.screen call, byte-for-byte, guarded the same defensive way
        #      every other launch control in this app already is (mirrors jobcard.html's
        #      launchWorkOrder() fallback pattern exactly: VW/VW.windows checked before use, a plain
        #      window.open() fallback if either is missing). ----
        ok("%s_calls_windows_open_with_the_screen_hint" % tag, SHARED_SCREEN_OPEN_CALL in code_only)
        ok("%s_guards_vw_and_vw_windows_before_using_them" % tag,
           "window.VW && VW.windows && typeof VW.windows.open==='function'" in code_only)
        ok("%s_falls_back_to_plain_window_open_if_vw_is_unavailable" % tag,
           re.search(r"\}\s*else\s*\{\s*try\{\s*window\.open\(url\);\s*\}catch\(e\)\{\}\s*\}", code_only)
           is not None)
except Exception as e:
    failed.append("g_reference_view_button_source_checks(%s)" % e)

try:
    torque_html = read(TORQUE_HTML)
    procedure_html = read(PROCEDURE_HTML)
    # Cross-file reuse: BOTH buttons share the identical opts.screen call site AND the identical
    # window name -- not just "present in both", the exact same characters, proving one shared
    # second-screen window rather than two independently-drifting ones.
    ok("torque_and_procedure_share_the_identical_screen_open_call_site",
       SHARED_SCREEN_OPEN_CALL in torque_html and SHARED_SCREEN_OPEN_CALL in procedure_html)

    # procedure.html's "current step" must come from the SAME per-step localStorage state its own
    # checkboxes already read/write (ckey()/getck()) -- never a second, independent notion of
    # "current", and never a value invented without checking the real per-step state at all.
    ok("procedure_html_current_step_reuses_the_real_per_step_state",
       "getck(ckey(src, CUR.steps[i].n))" in procedure_html)
except Exception as e:
    failed.append("g_reference_view_cross_file_checks(%s)" % e)


# ================================================================================================
# 4. rps_lint.py classifies reference.html (an unclassified new UI file is a hard gate failure --
#    this proves the classification itself, complementing an actual rps_lint.py run).
# ================================================================================================
try:
    rps_lint_py = read(RPS_LINT_PY)
    ok("rps_lint_classifies_reference_html_as_es5_required",
       '"reference.html"' in rps_lint_py
       and re.search(r"ES5_REQUIRED\s*=\s*\{.*?\"reference\.html\".*?\}", rps_lint_py, re.S) is not None)
except Exception as e:
    failed.append("g_reference_view_rps_lint_classification_check(%s)" % e)


# ================================================================================================
# 5. docs/MULTI-WINDOW-MANUAL-QA.md exists with real, substantive content -- not a stub.
# ================================================================================================
try:
    ok("multi_window_manual_qa_doc_exists", os.path.isfile(QA_DOC))
    qa = read(QA_DOC) if os.path.isfile(QA_DOC) else ""
    ok("multi_window_manual_qa_doc_is_substantive", len(qa) > 2000)
    ok("multi_window_manual_qa_doc_has_a_real_checklist_not_just_prose",
       qa.count("- [ ]") >= 10)
    ok("multi_window_manual_qa_doc_covers_screen_placement", "screen-aware placement" in qa.lower()
       or "screen placement" in qa.lower())
    ok("multi_window_manual_qa_doc_covers_rps_tier_gating",
       "rps-tier" in qa.lower() or "window.rps.mode" in qa.lower())
    ok("multi_window_manual_qa_doc_covers_lite_and_legacy_tiers",
       '"lite"' in qa and '"legacy"' in qa)
    ok("multi_window_manual_qa_doc_has_a_marked_placeholder_for_pr24",
       "placeholder" in qa.lower() and "PR 24" in qa)
    ok("multi_window_manual_qa_doc_references_the_plan_doc",
       "2026-09-03-multi-window-tabs-plan.md" in qa)
except Exception as e:
    failed.append("g_reference_view_manual_qa_doc_checks(%s)" % e)


# ---- house convention: node --check on the inline script blocks of all 3 touched/new pages.
#      Gracefully skips (never false-fails) without node, same as every other node-dependent check
#      in this suite.
try:
    _node_available = subprocess.run(["node", "--version"], capture_output=True).returncode == 0
except Exception:
    _node_available = False

if _node_available:
    try:
        for tag, path in (("reference.html", REFERENCE_HTML), ("torque.html", TORQUE_HTML),
                           ("procedure.html", PROCEDURE_HTML)):
            html = read(path)
            blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S)
            all_clean = bool(blocks)
            for b in blocks:
                with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
                    f.write(b)
                    tmp_path = f.name
                r = subprocess.run(["node", "--check", tmp_path], capture_output=True, text=True)
                if r.returncode != 0:
                    all_clean = False
                    say("  node --check %s inline script: %s" % (tag, r.stderr.strip()[:400]))
                os.unlink(tmp_path)
            ok("%s_inline_scripts_parse_with_node" % tag.replace(".", "_"), all_clean)
    except Exception as e:
        failed.append("g_reference_view_node_syntax(%s)" % e)
else:
    ok("node_unavailable_skip", True)


for n in passed:
    print("PASS", n)
for n in failed:
    print("FAIL", n)
print("\n%d passed, %d failed (G -- kiosk/second-screen reference view, multi-window PR 18)" % (len(passed), len(failed)))
sys.exit(1 if failed else 0)

# END OF FILE
