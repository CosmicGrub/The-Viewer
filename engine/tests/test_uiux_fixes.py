#!/usr/bin/env python3
"""THE VIEWER -- regression coverage for the priority-5 UI/UX audit fixes (Viewer UX Sightline).
Self-contained; no real corpus. Run:  python tests/test_uiux_fixes.py"""
import os, sys, re

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
TOOLS = os.path.join(ENGINE, "tools")
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE); sys.path.insert(0, TOOLS)

passed, failed = [], []
def ok(name, cond):
    (passed if cond else failed).append(name)

INDEX_HTML = os.path.join(ENGINE, "ui", "index.html")


# =====================================================================================================
# UX #1 (priority 5) -- index.html's ES5-safe fallback shell for engines that can't parse the main
# (intentionally ES6, MODERN_BY_DESIGN) script at all.
# =====================================================================================================
try:
    import check_es5_fallback as cef

    # the checker's own logic, on synthetic spans (it has no embedded self-test of its own, matching
    # the check_crlf.py/rps_lint.py convention of pure gate tools -- this is that verification instead)
    ok("cef_clean_span_passes", cef.check_span("var x = 1;\nfunction f(a) { return a; }\n") == [])
    dirty = {
        "arrow function": "var f = (a) => a;",
        "const declaration": "const x = 1;",
        "let declaration": "let y = 2;",
        "template literal": "var s = `hi`;",
        "for...of": "for (var v of arr) { }",
        "spread/rest": "var a = [...b];",
        "class declaration": "class Foo {}",
        "async function": "async function f() {}",
        "await": "await x;",
    }
    all_caught = True
    for label, snippet in dirty.items():
        names = set(n for n, _, _ in cef.check_span(snippet))
        if label not in names:
            all_caught = False
    ok("cef_catches_every_es6_pattern", all_caught)

    doc_ok = ("<script>\n/* " + cef.START_MARKER + " */\nvar ok = 1;\n</script>\n"
              "<script>\n/* " + cef.END_MARKER + " */\nconst modernOnly = 1;\n</script>\n")
    span = cef.extract_fallback_span(doc_ok)
    ok("cef_extracts_only_the_fallback_span", span is not None and "ok = 1" in span and "modernOnly" not in span)
    ok("cef_extracted_span_is_clean", cef.check_span(span) == [])

    ok("cef_missing_markers_returns_none", cef.extract_fallback_span("<p>no fallback here</p>") is None)

    doc_regressed = ("<script>\n/* " + cef.START_MARKER + " */\nconst oops = (a) => a;\n</script>\n"
                      "<script>\n/* " + cef.END_MARKER + " */\n</script>\n")
    hits = cef.check_span(cef.extract_fallback_span(doc_regressed))
    names_found = set(n for n, _, _ in hits)
    ok("cef_catches_a_regressed_fallback", "const declaration" in names_found and "arrow function" in names_found)

    # a feature-detection probe legitimately builds ES6 syntax as a STRING for Function(...) to compile
    # at runtime inside try/catch -- that string's content must NOT false-positive the scanner (this is
    # exactly what index.html's own probe does), but a real backtick template literal in outer code must
    # still be caught even though it's nominally "inside quotes" in a loose sense.
    ok("cef_ignores_es6_syntax_inside_a_string_literal",
       cef.check_span('Function("(a) => a; const x = 1; let y; for (v of z){} ...b");') == [])
    ok("cef_still_catches_real_template_literal_outside_strings",
       any(n == "template literal" for n, _, _ in cef.check_span("var s = `hi ${1}`;")))

    # the real, live check against the actual shipped file -- exit 0 means the fallback markers exist
    # and the span between them (the actual #legacyHome scripts) is genuinely ES5-clean today.
    ok("cef_real_file_markers_present", cef.extract_fallback_span(open(INDEX_HTML, encoding="utf-8").read()) is not None)
    ok("cef_real_index_html_passes", cef.main() == 0)
except Exception as e:
    failed.append("check_es5_fallback(%s)" % e)

try:
    html = open(INDEX_HTML, encoding="utf-8").read()
    # the fallback UI's key elements are present and wired (id-level smoke check -- can't run real JS
    # here, but a missing id would mean the shown fallback has no working search/side-chooser at all)
    for needle in ("id=\"legacyHome\"", "id=\"lgSearchForm\"", "id=\"lgQ\"", "id=\"lgResults\"",
                   "id=\"lgOperator\"", "id=\"lgMechanic\"", "viewer-legacy-fallback"):
        ok("index_html_has_%s" % re.sub(r"\W+", "_", needle), needle in html)

    # every nav link the fallback offers must be a real, currently-registered route (avoid a dead-link
    # regression if a route is ever renamed) -- cross-checked against features/routes.py's own _PAGES map.
    routes_py = open(os.path.join(ENGINE, "features", "routes.py"), encoding="utf-8").read()
    fallback_links = re.findall(r'href="(/[a-z]+)"', html.split("id=\"legacyHome\"")[1].split("</div>\n<script>")[0])
    ok("index_html_fallback_has_nav_links", len(fallback_links) >= 5)
    all_registered = all(('"%s"' % link) in routes_py or ("(\"%s\"" % link) in routes_py for link in fallback_links)
    ok("index_html_fallback_links_are_real_routes", all_registered)

    # the probe must run BEFORE the main (ES6) script block, and the fallback's own two script blocks
    # must sit between the probe and the main script -- ordering is what makes this fix work at all.
    probe_pos = html.find("ES5-only capability probe")
    legacyhome_pos = html.find("id=\"legacyHome\"")
    main_script_pos = html.find("v0.98.0: Tools menu")
    giant_script_pos = html.find("MODERN_BY_DESIGN")  # comment inside the real giant-script region isn't required; use a stable later anchor instead
    ok("index_html_probe_precedes_legacyhome", 0 < probe_pos < legacyhome_pos)
    ok("index_html_legacyhome_precedes_main_script", legacyhome_pos < main_script_pos)
except Exception as e:
    failed.append("index_html_fallback_structure(%s)" % e)


# =====================================================================================================
# UX #2 (priority 5) -- gl3d.js + threed.html's SVG fallback gain touch (1-finger orbit, 2-finger
# pinch-zoom) support, plus an always-visible +/-/reset button row, matching cadview.js's proven pattern.
# =====================================================================================================
try:
    import subprocess

    gl3d_js = os.path.join(ENGINE, "ui", "gl3d.js")
    threed_html = os.path.join(ENGINE, "ui", "threed.html")
    gl3d_src = open(gl3d_js, encoding="utf-8").read()
    threed_src = open(threed_html, encoding="utf-8").read()

    for needle in ("addEventListener('touchstart'", "addEventListener('touchmove'", "addEventListener('touchend'",
                   "function touchDist", "zoomBy"):
        ok("gl3d_js_has_%s" % re.sub(r"\W+", "_", needle), needle in gl3d_src)
    # zoomBy must be part of the returned public API, not just a private helper
    ok("gl3d_js_zoomby_is_exported", re.search(r"return\s*\{[^}]*zoomBy[^}]*\}", gl3d_src) is not None)

    for needle in ("s.addEventListener('touchstart'", "s.addEventListener('touchmove'", "s.addEventListener('touchend'",
                   "function gTouchDist", "function addStageZoomBar", "function stageZoomIn", "function stageZoomOut",
                   "GLV.zoomBy"):
        ok("threed_html_has_%s" % re.sub(r"\W+", "_", needle), needle in threed_src)
    # the zoom bar must actually be invoked from render3D (a helper that's defined but never called is a no-op)
    ok("threed_html_render3d_calls_addstagezoombar",
       "addStageZoomBar(st)" in threed_src.split("function render3D")[1].split("\n}\n")[0])

    # real syntax verification via Node (both files must still parse cleanly after the edit)
    if subprocess.run(["node", "--version"], capture_output=True).returncode == 0:
        r1 = subprocess.run(["node", "--check", gl3d_js], capture_output=True, text=True)
        ok("gl3d_js_parses_with_node", r1.returncode == 0)
        # extract threed.html's inline <script> block(s) to a temp file for node --check (an HTML file
        # itself isn't valid JS input)
        import tempfile
        blocks = re.findall(r"<script>(.*?)</script>", threed_src, re.S)
        ok("threed_html_has_inline_script", len(blocks) >= 1)
        all_clean = True
        for b in blocks:
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
                f.write(b); tmp_path = f.name
            r2 = subprocess.run(["node", "--check", tmp_path], capture_output=True, text=True)
            if r2.returncode != 0:
                all_clean = False
            os.unlink(tmp_path)
        ok("threed_html_inline_script_parses_with_node", all_clean)
    else:
        ok("node_unavailable_skip_syntax_check", True)  # environment without node -- don't false-fail
except Exception as e:
    failed.append("gl3d_touch_support(%s)" % e)


# =====================================================================================================
# UX #3 (priority 5) -- the default "3d" tab shows an on-canvas AI-illustrative watermark, matching
# the "approx" tab's existing pattern, instead of relying solely on a sidebar box appended last.
# =====================================================================================================
try:
    threed_src = open(os.path.join(ENGINE, "ui", "threed.html"), encoding="utf-8").read()
    ok("threed_html_has_addLocalIllusWatermark", "function addLocalIllusWatermark" in threed_src)
    render3d_body = threed_src.split("function render3D()")[1].split("\n}\n")[0]
    ok("threed_html_render3d_calls_watermark_helper", "addLocalIllusWatermark(st)" in render3d_body)
    wm_body = threed_src.split("function addLocalIllusWatermark(st){")[1].split("\n}\n")[0]
    ok("threed_html_watermark_gated_on_localillus", "_localIllus" in wm_body)
    ok("threed_html_watermark_removes_stale_node", "old.parentNode.removeChild(old)" in wm_body)
    ok("threed_html_watermark_text_matches_sidebar_wording", "AI-GENERATED APPROXIMATION" in wm_body)
except Exception as e:
    failed.append("localillus_watermark(%s)" % e)


# =====================================================================================================
# UX #4 (priority 5) -- Circuit Lab wires get individual selection + deletion (a fat hit-path, matching
# schemhl.js's transparent-overlay technique), instead of only a full-canvas "Clear canvas" wipe.
# Verified live in the browser (real DOM click on the demo circuit's hit-path + real #btnDel click
# correctly removed exactly the selected wire, leaving the other wire and both components intact,
# and renderProps() no longer crashes on a wire selection) -- this is static structural coverage of
# the same code paths, since there's no Node-side SVG/DOM to drive circuitsim.js's MNA logic here.
# =====================================================================================================
try:
    cl_src = open(os.path.join(ENGINE, "ui", "circuitlab.html"), encoding="utf-8").read()
    ok("circuitlab_wires_get_ids_on_creation", "wires.push({id:nextId++" in cl_src)
    ok("circuitlab_demo_builder_assigns_wire_ids", 'function W(ax,ay,bx,by){wires.push({id:nextId++' in cl_src)
    ok("circuitlab_deserialize_backfills_missing_wire_ids", "if(w.id==null)w.id=nextId++" in cl_src)
    ok("circuitlab_draw_adds_wire_hit_path", 'stroke:"transparent","stroke-width":9' in cl_src)
    ok("circuitlab_wire_click_sets_wire_selection", 'selected={kind:"wire",id:w.id}' in cl_src)
    ok("circuitlab_wire_click_skipped_while_drawing_a_wire", "if(tool===\"wire\")return;\n        selected={kind:\"wire\"" in cl_src)

    delsel_body = cl_src.split("function delSelected(){")[1].split("\n  function rotSelected")[0]
    ok("circuitlab_delselected_branches_on_wire_kind", 'selected.kind==="wire"' in delsel_body)
    ok("circuitlab_delselected_filters_wires_by_id", "wires=wires.filter(function(w){return w.id!==selected.id;})" in delsel_body)

    ok("circuitlab_rotselected_guards_against_wire", 'if(!selected||selected.kind==="wire")return;' in cl_src)

    renderprops_body = cl_src.split("function renderProps(){")[1].split("\n  }\n")[0]
    ok("circuitlab_renderprops_has_wire_branch_before_parts_lookup",
       renderprops_body.find('selected.kind==="wire"') < renderprops_body.find("PARTS[selected.type]"))
    ok("circuitlab_renderprops_wire_branch_offers_delete", "Delete wire" in renderprops_body)

    # Node syntax check
    import subprocess, tempfile, re as _re
    if subprocess.run(["node", "--version"], capture_output=True).returncode == 0:
        blocks = _re.findall(r"<script>(.*?)</script>", cl_src, re.S)
        all_clean = True
        for b in blocks:
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
                f.write(b); tmp_path = f.name
            r = subprocess.run(["node", "--check", tmp_path], capture_output=True, text=True)
            if r.returncode != 0: all_clean = False
            os.unlink(tmp_path)
        ok("circuitlab_html_parses_with_node", all_clean)
except Exception as e:
    failed.append("circuitlab_wire_selection(%s)" % e)


# =====================================================================================================
# UX #5 (priority 5) -- Deep Zoom keeps unboxed callouts (OCR-only pages) instead of silently dropping
# them, rendering a chip bar and a message that distinguishes "nothing extracted" from "found some, no
# position data yet". Verified live against the real fixture: doc=2&page=12 (a "FIG 14" callout with
# box:null, since the fixture's fake PDF paths mean page_words() never finds a text layer) correctly
# shows the chip + the right message; doc=2&page=13 (zero callouts) shows the other message.
# =====================================================================================================
try:
    dz_js = open(os.path.join(ENGINE, "ui", "deepzoom.js"), encoding="utf-8").read()
    dz_html = open(os.path.join(ENGINE, "ui", "deepzoom.html"), encoding="utf-8").read()

    ok("deepzoom_js_keeps_unboxed_callouts", "unboxed.push(cs[i])" in dz_js)
    ok("deepzoom_js_no_longer_drops_unboxed_silently",
       "if(cs[i].box){ cs[i]._n=callouts.length+1; callouts.push(cs[i]); } }" not in dz_js)
    ok("deepzoom_js_has_chip_bar_renderer", "function renderChipBar" in dz_js)
    ok("deepzoom_js_chip_reuses_oncallout_contract", "function calloutClick(cc){ if(opts.onCallout)" in dz_js)
    ok("deepzoom_js_oninfo_reports_total_and_unboxed",
       "onInfo({callouts:callouts.length, unboxed:unboxed.length, total:cs.length" in dz_js)

    ok("deepzoom_html_distinguishes_zero_vs_unboxed", "o.total===0" in dz_html and "no OCR position data yet" in dz_html)

    import subprocess, tempfile, re as _re
    if subprocess.run(["node", "--version"], capture_output=True).returncode == 0:
        r1 = subprocess.run(["node", "--check", os.path.join(ENGINE, "ui", "deepzoom.js")], capture_output=True, text=True)
        ok("deepzoom_js_parses_with_node", r1.returncode == 0)
        blocks = _re.findall(r"<script>(.*?)</script>", dz_html, re.S)
        all_clean = True
        for b in blocks:
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
                f.write(b); tmp_path = f.name
            r2 = subprocess.run(["node", "--check", tmp_path], capture_output=True, text=True)
            if r2.returncode != 0: all_clean = False
            os.unlink(tmp_path)
        ok("deepzoom_html_inline_script_parses_with_node", all_clean)
except Exception as e:
    failed.append("deepzoom_unboxed_callouts(%s)" % e)


# =====================================================================================================
# UX #6 (priority 5, R13 safety-relevant) -- safety callouts surface their already-computed OCR-quality
# confidence instead of dropping it: dossier.html (which already had it in the /api/cautions response
# but never rendered it) and packet.html/solve.html/stepflow.html/jobpack.py (whose separate simpler
# extractor never computed it at all -- now additively annotated, same {kind,text} shape preserved).
# =====================================================================================================
try:
    import features.procedures_feature as PF

    clean_text = "REMOVAL\nWARNING: Battery acid can cause severe burns. Wear gloves.\n1. Disconnect the cable.\n"
    r1 = PF._parse_procedure(clean_text)
    ok("procfeature_caution_has_confidence_field", r1 and r1["cautions"] and "confidence" in r1["cautions"][0])
    ok("procfeature_clean_text_scores_clean", r1 and r1["cautions"][0]["confidence"] == "clean")
    ok("procfeature_caution_kind_shape_unchanged", r1 and r1["cautions"][0]["kind"] == "WARNING")
    ok("procfeature_caution_body_still_stops_at_sentence",
       r1 and "1. Disconnect" not in r1["cautions"][0]["text"])  # regression guard: an earlier draft of
       # this fix accidentally swapped in a different extractor whose body text bled into the next line

    garbled_text = "REMOVAL\nWARNING: B4tt3ry ac1d c8n c8use s3ver3 burn5. Wxyz zzzz mnbb kkkk vwx pqrs.\n1. Disconnect the cable.\n"
    r2 = PF._parse_procedure(garbled_text)
    ok("procfeature_garbled_text_scores_below_clean",
       r2 and r2["cautions"] and r2["cautions"][0]["confidence"] in ("suspect", "poor"))

    no_warning_text = "REMOVAL\n1. Disconnect the cable.\n2. Remove the bolts.\n"
    r3 = PF._parse_procedure(no_warning_text)
    ok("procfeature_no_cautions_no_crash", r3 is not None and r3["cautions"] == [])
except Exception as e:
    failed.append("procfeature_caution_confidence(%s)" % e)

try:
    import jobpack
    if jobpack.available():
        pkg_poor = {"title": "TEST", "procedures": [{"kind": "REMOVE", "cautions": [
            {"kind": "DANGER", "text": "Garbled text.", "confidence": "poor", "quality": 0.2}], "steps": ["Step one."]}]}
        pdf1 = jobpack.build(pkg_poor)
        ok("jobpack_builds_with_poor_confidence_caution", pdf1[:5] == b"%PDF-")
        pkg_old_shape = {"title": "TEST", "procedures": [{"kind": "REMOVE",
            "cautions": [{"kind": "WARNING", "text": "No confidence field (pre-fix shape)."}], "steps": ["Step one."]}]}
        pdf2 = jobpack.build(pkg_old_shape)
        ok("jobpack_backward_compatible_with_no_confidence_field", pdf2[:5] == b"%PDF-")
    else:
        ok("jobpack_reportlab_unavailable_skip", True)
except Exception as e:
    failed.append("jobpack_confidence_qualifier(%s)" % e)

try:
    for fname, needle in [("dossier.html", "OCR quality: '+esc(c.confidence)"),
                           ("packet.html", "OCR quality: '+esc(c.confidence)"),
                           ("solve.html", "OCR quality: '+esc(c.confidence)"),
                           ("stepflow.html", "OCR quality: '+esc(c.confidence)")]:
        src = open(os.path.join(ENGINE, "ui", fname), encoding="utf-8").read()
        ok("%s_renders_confidence_qualifier" % fname.replace(".html", ""), needle in src)
        # every qualifier must be gated on confidence!=='clean' -- a clean callout must not show a
        # spurious "verify on page" flag
        ok("%s_qualifier_gated_on_non_clean" % fname.replace(".html", ""),
           'c.confidence!=="clean"' in src)

    import subprocess, tempfile, re as _re
    if subprocess.run(["node", "--version"], capture_output=True).returncode == 0:
        all_clean = True
        for fname in ("dossier.html", "packet.html", "solve.html", "stepflow.html"):
            src = open(os.path.join(ENGINE, "ui", fname), encoding="utf-8").read()
            for b in _re.findall(r"<script>(.*?)</script>", src, re.S):
                with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
                    f.write(b); tmp_path = f.name
                r = subprocess.run(["node", "--check", tmp_path], capture_output=True, text=True)
                if r.returncode != 0: all_clean = False
                os.unlink(tmp_path)
        ok("caution_confidence_uis_parse_with_node", all_clean)
except Exception as e:
    failed.append("caution_confidence_ui_rendering(%s)" % e)


# =====================================================================================================
# UX #7 (priority 5) -- kiosk/glove-mode's touch-target minimum reaches the controls it used to miss:
# [role=button] (palette.js's #cmdk-pill/#bench-pill), #vw-footer a (shared.js's app-wide nav), and
# min-width alongside the existing min-height (deepzoom.js's circular callout badges, deepzoom/cadview's
# zoom-button rows) -- verified live: kiosk mode ON correctly measured 44x44 for #vw-footer a and
# #cmdk-pill (pure-CSS, reactive), and the deepzoom.js/cadview.js JS-side fix (which reads localStorage
# directly, NOT the --kiosk-min CSS var, after live testing caught a real script-order bug: these
# scripts mount before palette.js applies body.kiosk-mode on deepzoom.html) verified correct against
# the server's actual served file content and the real localStorage state in the browser.
# =====================================================================================================
try:
    base_css = open(os.path.join(ENGINE, "ui", "base.css"), encoding="utf-8").read()
    kiosk_block = base_css.split("KIOSK / GLOVE MODE")[1].split("body{margin:0")[0]
    for needle in ('[role="button"]', "#vw-footer a", "#cmdk-pill", "#bench-pill", "min-width:44px"):
        ok("base_css_kiosk_covers_%s" % re.sub(r"\W+", "_", needle), needle in kiosk_block)
    ok("base_css_defines_kiosk_min_var_default", ":root{--kiosk-min:30px}" in base_css)
    ok("base_css_kiosk_mode_overrides_kiosk_min_var", "--kiosk-min:44px" in base_css)

    dz_js = open(os.path.join(ENGINE, "ui", "deepzoom.js"), encoding="utf-8").read()
    cv_js = open(os.path.join(ENGINE, "ui", "cadview.js"), encoding="utf-8").read()
    threed_src = open(os.path.join(ENGINE, "ui", "threed.html"), encoding="utf-8").read()
    for label, src in (("deepzoom_js", dz_js), ("cadview_js", cv_js), ("threed_html", threed_src)):
        ok("%s_kioskmin_reads_localstorage_not_css_var" % label,
           "localStorage.getItem('viewer_kiosk')" in src and "getComputedStyle(document.body).getPropertyValue('--kiosk-min')" not in src)
    ok("deepzoom_js_callout_badge_width_height_move_together", "width:'+bd+'px;height:'+bd+'px" in dz_js)

    import subprocess
    if subprocess.run(["node", "--version"], capture_output=True).returncode == 0:
        r1 = subprocess.run(["node", "--check", os.path.join(ENGINE, "ui", "deepzoom.js")], capture_output=True, text=True)
        r2 = subprocess.run(["node", "--check", os.path.join(ENGINE, "ui", "cadview.js")], capture_output=True, text=True)
        ok("deepzoom_cadview_js_parse_with_node_after_kiosk_fix", r1.returncode == 0 and r2.returncode == 0)

    # cadview.js is ES5-required and gated by VERIFY.bat -- confirm it's still ES5-clean, matching
    # rps_lint.py's own PATTERNS (a real regression here would silently ship a broken legacy build)
    es6_markers = [r"=>", r"(?<![\w.])const\s", r"(?<![\w.])let\s", "`", r"(?<![\w.])async\s", r"(?<![\w.])await\s"]
    cv_es6_hits = [pat for pat in es6_markers if re.search(pat, cv_js)]
    ok("cadview_js_still_es5_clean_after_kiosk_fix", not cv_es6_hits)
except Exception as e:
    failed.append("kiosk_touch_targets(%s)" % e)


# =====================================================================================================
# UX #8 (priority 5, R13 "never fabricate") -- bin/shelf audit no longer coerces a non-NSN scan into a
# fabricated 9-digit NIIN. Verified live: 9- and 13-digit codes accepted; an 11-digit UPC-like code is
# rejected (no row added, input left in place so it's visible/editable, not silently discarded); and
# window.onScan returns add()'s real true/false so scanner.js's own fallback can distinguish them.
# =====================================================================================================
try:
    ba_src = open(os.path.join(ENGINE, "ui", "binaudit.html"), encoding="utf-8").read()
    niin_fn = ba_src.split("function niinOf(s){")[1].split("}\n")[0]
    ok("binaudit_niinof_rejects_short_padded_codes", "padStart" not in niin_fn)
    ok("binaudit_niinof_accepts_exactly_9_or_13plus", "d.length===9||d.length>=13" in niin_fn)

    onscan_body = ba_src.split("window.onScan=function(code){")[1].split("};")[0]
    ok("binaudit_onscan_returns_real_add_result", "return ok;" in onscan_body and "var ok=add(code);" in onscan_body)
    ok("binaudit_onscan_only_updates_indicator_on_success", "if(ok) $('#scanind')" in onscan_body)

    ok("binaudit_manual_add_gives_feedback_on_reject", "Not a recognizable NSN" in ba_src)
    ok("binaudit_manual_add_preserves_input_on_reject",
       "function addManual(){" in ba_src and "if(add(v)){ $('#q').value=''; }" in ba_src)

    import subprocess, tempfile, re as _re
    if subprocess.run(["node", "--version"], capture_output=True).returncode == 0:
        blocks = _re.findall(r"<script>(.*?)</script>", ba_src, re.S)
        all_clean = True
        for b in blocks:
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
                f.write(b); tmp_path = f.name
            r = subprocess.run(["node", "--check", tmp_path], capture_output=True, text=True)
            if r.returncode != 0: all_clean = False
            os.unlink(tmp_path)
        ok("binaudit_html_parses_with_node", all_clean)
except Exception as e:
    failed.append("binaudit_niin_fabrication(%s)" % e)


# =====================================================================================================
# UX #9 (priority 5) -- the QR job-packet deep-link now tells the caller when it's local-only (the app's
# own documented default deployment: loopback HOST, no VIEWER_ALLOWED_HOSTS) via X-QR-Local-Only, and
# packet.html shows an inline warning instead of an unqualified "scan this" claim. Verified live: the
# local_only string-matcher correctly flags 127.0.0.1/localhost/[::1] and does NOT false-positive on a
# lookalike domain (127.0.0.1.evil.com); packet.html's loadQr() renders the warning banner exactly when
# the header says 1 and renders nothing when it says 0 (mocked fetch, since qrgen/segno isn't installed
# in this sandbox to produce a real QR image -- the route's own 503-unavailable path was confirmed not
# to crash after this change via a live restart + curl).
# =====================================================================================================
try:
    routes_src = open(os.path.join(ENGINE, "features", "routes.py"), encoding="utf-8").read()
    r_qr_body = routes_src.split("def r_qr(h, qs):")[1].split("\n\n\n")[0]
    ok("r_qr_computes_local_only_flag", "local_only = base.lower().startswith" in r_qr_body)
    ok("r_qr_sends_x_qr_local_only_header", '"X-QR-Local-Only": "1" if local_only else "0"' in r_qr_body)
    ok("r_qr_local_only_check_covers_127_localhost_ipv6", all(
        s in r_qr_body for s in ("http://127.0.0.1:", "http://localhost:", "http://[::1]:")))

    def local_only_check(base):
        return base.lower().startswith(("http://127.0.0.1:", "http://localhost:", "http://[::1]:"))
    ok("local_only_flags_loopback", local_only_check("http://127.0.0.1:8765"))
    ok("local_only_flags_localhost", local_only_check("http://localhost:8765"))
    ok("local_only_flags_ipv6_loopback", local_only_check("http://[::1]:8765"))
    ok("local_only_clears_for_lan_address", not local_only_check("http://192.168.1.50:8765"))
    ok("local_only_no_false_positive_on_lookalike_domain", not local_only_check("http://127.0.0.1.evil.com:8765"))

    pk_src = open(os.path.join(ENGINE, "ui", "packet.html"), encoding="utf-8").read()
    ok("packet_html_no_longer_uses_plain_img_src_for_qr", 'src="/api/qr?q=' not in pk_src)
    ok("packet_html_has_loadqr_function", "function loadQr(q){" in pk_src)
    ok("packet_html_reads_x_qr_local_only_header", 'r.headers.get("X-QR-Local-Only")==="1"' in pk_src)
    ok("packet_html_shows_warning_text", "This code only opens on THIS computer" in pk_src)

    import subprocess, tempfile, re as _re
    if subprocess.run(["node", "--version"], capture_output=True).returncode == 0:
        all_clean = True
        for b in _re.findall(r"<script>(.*?)</script>", pk_src, re.S):
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
                f.write(b); tmp_path = f.name
            r = subprocess.run(["node", "--check", tmp_path], capture_output=True, text=True)
            if r.returncode != 0: all_clean = False
            os.unlink(tmp_path)
        ok("packet_html_parses_with_node", all_clean)

    import ast
    ast.parse(routes_src)
    ok("routes_py_syntax_valid_after_qr_fix", True)
except Exception as e:
    failed.append("qr_local_only_warning(%s)" % e)


# =====================================================================================================
# UX #10 (priority 5, completeness sweep) -- Look-Alike Parts renders an inline cited-figure thumbnail
# per variant (schematics.html's card() thumbnail pattern) instead of being 100% text/table. Verified
# live: render() with realistic API-shaped data (confirmed field names against
# features/parts_feature.py's part_differences()) produces exactly one thumbnail per variant, correct
# doc/page URLs, and a failed image load (the fixture's fake PDF paths 404) gracefully hides its
# container via onerror rather than showing a broken-image box.
# =====================================================================================================
try:
    pd_src = open(os.path.join(ENGINE, "ui", "partdiff.html"), encoding="utf-8").read()
    ok("partdiff_html_now_has_an_img_tag", "<img" in pd_src)
    ok("partdiff_html_thumb_uses_first_ref", "v.refs[0]" in pd_src)
    ok("partdiff_html_thumb_links_to_full_page", '<a class="thumb" href="\'+tpage+\'" target="_blank"' in pd_src)
    ok("partdiff_html_thumb_degrades_gracefully_onerror", "onerror=\"this.parentNode.style.display=\\'none\\'\"" in pd_src)
    ok("partdiff_html_thumb_uses_lazy_loading", 'loading="lazy"' in pd_src)
    # cross-check the field names used against the real backend response shape, so this doesn't silently
    # break if part_differences()'s refs[] shape ever changes without this page being updated
    pf_src = open(os.path.join(ENGINE, "features", "parts_feature.py"), encoding="utf-8").read()
    refs_build = pf_src.split('v["refs"].append({')[1].split("})")[0]
    ok("partdiff_thumb_field_names_match_backend_refs_shape",
       '"page"' in refs_build and '"document_id"' in refs_build)

    import subprocess, tempfile, re as _re
    if subprocess.run(["node", "--version"], capture_output=True).returncode == 0:
        all_clean = True
        for b in _re.findall(r"<script>(.*?)</script>", pd_src, re.S):
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
                f.write(b); tmp_path = f.name
            r = subprocess.run(["node", "--check", tmp_path], capture_output=True, text=True)
            if r.returncode != 0: all_clean = False
            os.unlink(tmp_path)
        ok("partdiff_html_parses_with_node", all_clean)
except Exception as e:
    failed.append("partdiff_thumbnail(%s)" % e)


for n in passed: print("PASS", n)
for n in failed: print("FAIL", n)
print("\n%d passed, %d failed (of %d checks for priority-5 UI/UX audit fixes)" %
      (len(passed), len(failed), len(passed) + len(failed)))
sys.exit(1 if failed else 0)

# END OF FILE
