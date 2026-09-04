#!/usr/bin/env python3
"""A2 -- per-page pop-out control (multi-window support, PR 14 of
docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md, stage 4).

WHAT THIS COVERS, structurally, against the real shipped files (this suite has no in-browser runner,
same limitation every prior PR in this initiative states plainly rather than glosses over):

  - shared.js defines VW.popoutControl(), a real function reachable off the VW export object -- not
    just declared and forgotten.
  - shared.js's window-naming transform is the SAME regex/string-transform logic as A1's popoutName()
    in index.html (~line 592) -- extracted and compared as source text, not eyeballed -- because that
    sameness is the ENTIRE mechanism by which a page popped out via A1's home-nav link and the same
    page popped out via ITS OWN A2 control land on ONE window instead of two. A Python mirror of the
    shared transform is also exercised against real paths to prove the RULE itself (unique per page,
    stable across a changed "?q=..."), the same two-layer proof test_home_nav_popout.py already
    established for A1's own copy.
  - palette.js's window.__paletteQueue drain is genuinely wired into COMMANDS, and wired at BOTH of
    the two points that make it order-independent: once right after COMMANDS is built (covers a page
    whose own inline script -- and therefore its popoutControl() call -- runs BEFORE palette.js, the
    normal order on all 5 adopting pages today) and again at the top of open() (covers a hypothetical
    future page where that order is reversed). Both are asserted separately, not just "the function
    exists somewhere", specifically so a regression that keeps one drain site and drops the other
    still fails a test.
  - each of the 5 adopting pages (part.html, procedure.html, torque.html, jobcard.html, bench.html)
    actually calls VW.popoutControl(), and does so AFTER /shared.js and BEFORE /palette.js in the
    page's own source order -- the load-order fact this PR was built around, checked on the real
    files rather than assumed.
  - the button shared.js injects is a real <button> (createElement("button")), not a div+click
    handler -- this project's own [1.46.0]/[1.47.0] accessibility passes are the reason that
    distinction matters here, the same reason test_home_nav_popout.py checks it for A1's buttons.
  - the SAME action (VW.windows.open, or the plain window.open fallback) backs both the visible
    button and the palette entry -- counted, not assumed, so a future edit that duplicates the open
    call into two independent copies fails here.

WHAT THIS CANNOT COVER, stated plainly: whether clicking the pop-out button (or its Ctrl+K palette
entry) in a real browser actually opens a window, and whether a second click genuinely refocuses the
first instead of opening a second. That is real window.open()/BroadcastChannel browser behavior with
no in-browser test runner in this suite -- test_shared_windows.py's own node-sandbox layer already
covers VW.windows.open()'s reuse/toast/registry logic in isolation; whether THIS PR's button reaches
that call correctly is what is tested here, on the actual page source. The real end-to-end behavior
(pop out from /torque, confirm A1's home-nav ↗ for Torque reuses the SAME window) is a manual check,
called out as manual in the PR body.

Self-contained; no corpus, no server. Run:  python engine/tests/test_a2_popout.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
UI = os.path.join(ENGINE, "ui")
SHARED_JS = os.path.join(UI, "shared.js")
PALETTE_JS = os.path.join(UI, "palette.js")
INDEX_HTML = os.path.join(UI, "index.html")
BASE_CSS = os.path.join(UI, "base.css")
TARGET_PAGES = ["part.html", "procedure.html", "torque.html", "jobcard.html", "bench.html"]

passed, failed = [], []


def ok(name, cond):
    (passed if cond else failed).append(name)


def say(msg):
    """ASCII-only diagnostic print -- see test_home_nav_popout.py's identical helper/rationale:
    a plain print() of non-ASCII page content can UnicodeEncodeError on a cp1252 console and, inside
    a broad try/except, silently swallow every assertion after it."""
    print(str(msg).encode("ascii", "backslashreplace").decode("ascii"))


def read(path):
    return open(path, encoding="utf-8").read()


def popout_name_py(href):
    """Python mirror of the shared window-naming rule (identical in index.html's popoutName() and
    shared.js's _popoutWindowName()): strip query/fragment, strip leading/trailing slashes, replace
    every run of anything outside [A-Za-z0-9_-] with '-', prefix 'vw-', fall back to 'home' for the
    empty/root path. Proves the RULE's properties over real paths; the source-text comparison below
    proves the two files actually implement the SAME rule rather than two rules that happen to agree
    on the handful of paths exercised here."""
    base = href.split("?")[0].split("#")[0].strip("/")
    return "vw-" + (re.sub(r"[^A-Za-z0-9_-]+", "-", base) if base else "home")


def normalized_name_transform(src, fn_marker, body_start_marker, end_marker):
    """Extracts the naming function's core transform (from its first real statement -- deliberately
    NOT from 'function <name>(<param>)', since the function/parameter names legitimately differ
    between the two files, popoutName/href vs _popoutWindowName/pathOrHref -- through the 'home'
    fallback) and strips ALL whitespace, so index.html's 'replace(/^\\/+/,"")' and shared.js's
    'replace(/^\\/+/, "")' -- differing only in a space rps_lint/eslint would treat as insignificant
    -- compare as identical. fn_marker is only used to confirm the function itself still exists at
    all near this point in the source (a real, load-bearing check on its own: see the
    *_declares_the_naming_helper / *_still_declares_popoutName assertions above), not as the slice
    start."""
    if fn_marker not in src:
        raise AssertionError("marker not found: %r" % fn_marker)
    fn_idx = src.index(fn_marker)
    window = src[fn_idx:fn_idx + 600]   # search for the body-start marker near THIS function only,
                                         # never a lookalike statement elsewhere in a 2,300-line file
    m = re.search(body_start_marker, window)
    if not m:
        raise AssertionError("body-start marker not found near %r: %r" % (fn_marker, body_start_marker))
    chunk = window[m.start():]
    j = chunk.index(end_marker) + len(end_marker)
    body = chunk[:j]
    body = re.sub(r"\s+", "", body)
    # normalize the one real, legitimate difference: the parameter identifier used inside
    # String(...||"") -- href in index.html, pathOrHref in shared.js.
    return re.sub(r'String\([A-Za-z_]+\|\|""\)', 'String(P||"")', body)


try:
    shared_js = read(SHARED_JS)
    palette_js = read(PALETTE_JS)
    index_html = read(INDEX_HTML)
    base_css = read(BASE_CSS)

    # ============================================================================================
    # shared.js: VW.popoutControl() exists, is reachable off VW, and is a real function.
    # ============================================================================================
    ok("shared_js_declares_popout_control_function",
       "function popoutControl(opts)" in shared_js)
    ok("shared_js_exports_popout_control_off_vw",
       re.search(r"trapFocus:\s*trapFocus,\s*popoutControl:\s*popoutControl", shared_js) is not None)

    # ---- the visible control is a real, keyboard-focusable <button>, never a div+click handler.
    popout_fn_start = shared_js.index("function popoutControl(opts)")
    popout_fn_body = shared_js[popout_fn_start:shared_js.index("\n  var VW = {", popout_fn_start)]
    ok("popout_control_creates_a_real_button_element",
       'document.createElement("button")' in popout_fn_body)
    ok("popout_control_sets_type_button",
       'b.type = "button"' in popout_fn_body)
    ok("popout_control_gives_it_a_nonempty_aria_label",
       'b.setAttribute("aria-label", label)' in popout_fn_body)
    ok("popout_control_aria_label_says_new_window", "a new window" in popout_fn_body)
    ok("popout_control_mirrors_a1_open_x_phrasing",
       re.sub(r"\s+", "", '"Open " + title + " in a new window"') in re.sub(r"\s+", "", popout_fn_body))

    # ---- the ONE shared action: exactly one VW.windows.open( call site inside this whole helper,
    #      reused by both the button's onclick and the palette descriptor's act -- never duplicated.
    open_call_count = popout_fn_body.count("VW.windows.open(")
    ok("popout_control_calls_vw_windows_open_exactly_once", open_call_count == 1)
    ok("popout_control_button_click_uses_the_shared_doPopout_fn", "b.onclick = doPopout" in popout_fn_body)
    ok("popout_control_palette_entry_uses_the_same_shared_doPopout_fn", "act: doPopout" in popout_fn_body)
    ok("popout_control_falls_back_to_plain_named_window_open",
       "g.open(url, name)" in popout_fn_body)

    # ---- the queue handoff: never reaches into palette.js's COMMANDS directly (there is no such
    #      access anywhere in this whole file), always goes through window.__paletteQueue.
    ok("shared_js_never_touches_a_commands_array_directly",
       "COMMANDS.push" not in shared_js and "COMMANDS[" not in shared_js)
    ok("popout_control_pushes_onto_the_shared_palette_queue",
       "g.__paletteQueue" in popout_fn_body and ".push(" in popout_fn_body)
    ok("popout_control_creates_the_queue_array_lazily",
       "if (!g.__paletteQueue) g.__paletteQueue = [];" in popout_fn_body)

    # ============================================================================================
    # Window naming: shared.js's _popoutWindowName must implement the IDENTICAL transform as
    # index.html's popoutName -- extracted and compared as source text, not eyeballed.
    # ============================================================================================
    ok("shared_js_declares_the_naming_helper",
       "function _popoutWindowName(pathOrHref)" in shared_js)
    ok("index_html_still_declares_popoutName", "function popoutName(href){" in index_html)

    shared_chain = normalized_name_transform(
        shared_js, "function _popoutWindowName(pathOrHref)", r"var\s+base\s*=", '"home");')
    index_chain = normalized_name_transform(
        index_html, "function popoutName(href){", r"var\s+base\s*=", '"home");')
    ok("naming_transform_source_text_matches_a1_byte_for_byte", shared_chain == index_chain)
    if shared_chain != index_chain:
        say("  shared.js chain: %r" % shared_chain)
        say("  index.html chain: %r" % index_chain)

    # ---- functional properties of the rule (Python mirror), same checks test_home_nav_popout.py
    #      already runs for A1's copy -- proving the RULE, complementing the source-identity proof
    #      above which proves shared.js and index.html implement that same rule.
    ok("naming_rule_matches_the_documented_example", popout_name_py("/torque") == "vw-torque")
    ok("naming_rule_strips_query_before_naming",
       popout_name_py("/torque?q=bolt") == popout_name_py("/torque"))
    ok("naming_rule_survives_a_replaced_query",
       popout_name_py("/torque?q=a") == popout_name_py("/torque?q=b"))
    ok("naming_rule_is_prefixed_and_safe",
       re.match(r"^vw-[A-Za-z0-9_-]+$", popout_name_py("/torque")) is not None)
    # ---- THE headline property this whole PR exists for: A2's control on /torque must compute the
    #      SAME window name A1's home-nav ↗ computes for the /torque row, so the second click reuses
    #      the first window rather than stacking a second one.
    ok("a2_and_a1_name_the_same_page_identically", popout_name_py("/torque") == "vw-torque"
       and popout_name_py("/bench") == "vw-bench")

    # ============================================================================================
    # palette.js: the queue-drain mechanism is genuinely wired into COMMANDS, order-independently.
    # ============================================================================================
    ok("palette_js_declares_the_drain_function", "function _drainPaletteQueue(){" in palette_js)
    ok("palette_js_drain_reads_the_shared_queue", "window.__paletteQueue" in palette_js)
    ok("palette_js_drain_pushes_into_commands", "COMMANDS.push(" in palette_js)
    ok("palette_js_drain_clears_the_queue_after_draining", "q.length=0" in palette_js)
    ok("palette_js_drain_validates_each_entry_defensively",
       'typeof c.act==="function"' in palette_js and 'typeof c.label==="string"' in palette_js)

    commands_idx = palette_js.index("var COMMANDS=[")
    commands_close_idx = palette_js.index("\n  ];", commands_idx) + len("\n  ];")
    open_fn_idx = palette_js.index("function open(){")
    drain_call_indices = [m.start() for m in re.finditer(r"_drainPaletteQueue\(\);", palette_js)]
    ok("drain_is_called_at_least_twice_order_independently", len(drain_call_indices) >= 2)
    ok("drain_is_called_right_after_commands_is_built_and_before_open_is_defined",
       any(commands_close_idx <= idx < open_fn_idx for idx in drain_call_indices))
    ok("drain_is_called_as_the_first_statement_inside_open",
       "function open(){ _drainPaletteQueue();" in palette_js)

    # ============================================================================================
    # The 5 target pages actually adopt the helper, in the right order relative to /shared.js and
    # /palette.js (the exact load-order fact this PR depends on -- checked, not assumed).
    # ============================================================================================
    for page in TARGET_PAGES:
        html = read(os.path.join(UI, page))
        ok("%s_calls_vw_popout_control" % page, "VW.popoutControl()" in html)
        ok("%s_loads_shared_js" % page, '<script src="/shared.js">' in html)
        ok("%s_loads_palette_js" % page, '<script src="/palette.js">' in html)
        shared_idx = html.find('src="/shared.js"')
        call_idx = html.find("VW.popoutControl()")
        palette_idx = html.find('src="/palette.js"')
        ok("%s_calls_popout_control_between_shared_and_palette_scripts" % page,
           0 <= shared_idx < call_idx < palette_idx)

    # ============================================================================================
    # base.css: #vw-popout-pill exists, joins the same fixed bottom:12px pill family as
    # #cmdk-pill/#bench-pill, and does not reuse either's right offset (which would make the
    # KNOWN pre-existing #vw-footer/#cmdk-pill/#bench-pill overlap worse rather than leaving it as
    # a separate, already-filed issue).
    # ============================================================================================
    ok("base_css_declares_vw_popout_pill", "#vw-popout-pill{" in base_css)
    ok("base_css_vw_popout_pill_is_bottom_right_fixed",
       re.search(r"#vw-popout-pill\{[^}]*position:fixed[^}]*right:288px[^}]*bottom:12px",
                 base_css) is not None
       or re.search(r"#vw-popout-pill\{[^}]*position:fixed[^}]*bottom:12px[^}]*right:288px",
                     base_css) is not None)
    # #cmdk-pill/#bench-pill are NOT in base.css -- palette.js injects its own inline <style> for
    # them (var pcss). This has to read the real numeric right-offset each one actually uses, not
    # base.css, or this check would vacuously pass no matter what right-offset shared.js/base.css
    # picked for #vw-popout-pill.
    cmdk_right = int(re.search(r"#cmdk-pill\{right:(\d+)px\}", palette_js).group(1))
    bench_right = int(re.search(r"#bench-pill\{right:(\d+)px\}", palette_js).group(1))
    popout_right = int(re.search(r"#vw-popout-pill\{[^}]*right:(\d+)px", base_css).group(1))
    ok("base_css_vw_popout_pill_reuses_neither_cmdk_nor_bench_offset",
       popout_right not in (cmdk_right, bench_right))
    # measured in a real browser (see the PR body/comment above the CSS rule): bench-pill's own
    # rendered LEFT edge sits at right-distance ~217px on every viewport width tested. Requiring a
    # real margin catches a future edit that nudges either pill's text/right offset close enough to
    # collide again, not just an exact-value duplicate.
    ok("base_css_vw_popout_pill_clears_bench_pill_with_a_real_margin", popout_right >= bench_right + 60)
    ok("base_css_kiosk_mode_keeps_the_new_pill_in_the_same_compact_family",
       "#vw-popout-pill{padding:11px 16px;font-size:13px}" in base_css.replace(" ", "")
       or re.search(r"body\.kiosk-mode[^{]*#vw-popout-pill[^{]*\{[^}]*padding:11px 16px", base_css)
       is not None)
except Exception as e:
    failed.append("a2_popout_source_checks(%s)" % e)


# ---- house convention: node --check on every touched file, plus the inline script blocks of the
#      5 adopted pages. Gracefully skips (never false-fails) without node, same as every other
#      node-dependent check in this suite.
try:
    import subprocess
    import tempfile

    if subprocess.run(["node", "--version"], capture_output=True).returncode == 0:
        for fn, path in (("shared.js", SHARED_JS), ("palette.js", PALETTE_JS)):
            r = subprocess.run(["node", "--check", path], capture_output=True, text=True)
            ok("%s_parses_with_node" % fn, r.returncode == 0)
            if r.returncode != 0:
                say("  node --check %s: %s" % (fn, r.stderr.strip()[:400]))

        for page in TARGET_PAGES:
            src = read(os.path.join(UI, page))
            blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", src, re.S)
            all_clean = True
            for b in blocks:
                with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
                    f.write(b)
                    tmp_path = f.name
                r = subprocess.run(["node", "--check", tmp_path], capture_output=True, text=True)
                if r.returncode != 0:
                    all_clean = False
                    say("  node --check %s inline script: %s" % (page, r.stderr.strip()[:400]))
                os.unlink(tmp_path)
            ok("%s_inline_scripts_parse_with_node" % page, all_clean)
    else:
        ok("node_unavailable_skip_syntax_check", True)
except Exception as e:
    failed.append("a2_popout_node_syntax(%s)" % e)


for n in passed:
    print("PASS", n)
for n in failed:
    print("FAIL", n)
print("\n%d passed, %d failed (A2 per-page pop-out control, multi-window PR 14)" % (len(passed), len(failed)))
sys.exit(1 if failed else 0)

# END OF FILE
