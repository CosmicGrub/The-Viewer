#!/usr/bin/env python3
"""Regression coverage for readaloud.js's step-by-step navigation (recommendations annex #8:
readaloud-navigation). No browser/DOM available in this environment, so this follows the
established convention for JS-only fixes in this repo: read the real shipped source and assert on
it, run `node --check` for real syntax validation, and confirm rps_lint.py still reports it
ES5-clean -- matching test_uiux_fixes.py's own pattern for pure-JS changes. Pure stdlib runner."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE)

READALOUD_JS = os.path.join(ENGINE, "ui", "readaloud.js")
PROCEDURE_HTML = os.path.join(ENGINE, "ui", "procedure.html")


def run():
    passed, failed = [], []

    def check(name, cond):
        (passed if cond else failed).append(name)

    src = open(READALOUD_JS, encoding="utf-8").read()

    # the core navigation primitives exist and are wired into init()
    for fn in ("function stepNodes(", "function stepText(", "function gotoStep(",
               "function nextStep(", "function prevStep(", "function repeatStep(",
               "function mountStepNav(", "function mountStepMic(", "function watchSteps("):
        check("readaloud_js_defines_%s" % fn.split("(")[0].replace("function ", ""), fn in src)
    check("readaloud_js_init_calls_mountStepNav", "mountStepNav()" in src)
    check("readaloud_js_init_calls_watchSteps", "watchSteps()" in src)

    # stepNodes() looks in the real container procedure.html actually renders into
    check("stepNodes_targets_stepwrap_or_out", '"stepwrap"' in src and '"out"' in src)
    check("stepNodes_selects_dot_step", ".step" in src)

    # stepText() strips chips/checkbox before reading -- otherwise a torque/fig/NSN chip's text
    # would be read twice (once as prose inside .body, once as the chip's own label)
    check("stepText_strips_input_and_chip_elements", 'querySelectorAll("input, .chip")' in src)
    check("stepText_reads_the_dot_n_and_dot_body_elements", '".n"' in src and '".body"' in src)

    # nextStep/prevStep/repeatStep dispatch through gotoStep() with the right offsets, not
    # duplicated logic each -- a cheap textual proxy for "these three are consistent with each other"
    check("nextStep_increments_via_gotoStep", "function nextStep(){ gotoStep(stepIdx<0?0:stepIdx+1); }" in src)
    check("prevStep_decrements_via_gotoStep", "function prevStep(){ gotoStep(stepIdx<0?0:stepIdx-1); }" in src)
    check("repeatStep_reuses_current_index_via_gotoStep", "function repeatStep(){ gotoStep(stepIdx<0?0:stepIdx); }" in src)

    # voice commands: a SEPARATE recognizer from the existing search-dictation mic (mountMic()),
    # not repurposing it -- conflating the two would make one mic press do something unintended
    check("mountStepMic_is_a_distinct_function_from_mountMic", "function mountStepMic(" in src and "function mountMic(" in src)
    check("mountStepMic_never_touches_the_search_box", 'getElementById("q")' not in src.split("function mountStepMic(")[1].split("function ")[0])
    for phrase in (r"\bnext\b", r"\bprevious\b|\bback\b", r"\brepeat\b|\bagain\b", r"\bstop\b"):
        check("voice_command_regex_present_%s" % phrase, phrase in src)
    check("voice_recognizer_is_continuous_not_single_shot", "rec.continuous=true" in src)

    # the nav bar is hidden by default and only shown when real step nodes exist -- guards against
    # showing controls on the dozens of OTHER pages that load this same global script
    check("stepnav_css_starts_hidden", "display:none;gap:6px" in src)
    check("paintStepNav_hides_when_no_steps", "if(!ns.length){ wrap.style.display=" in src)

    # touch sizing: the nav buttons opt into the same pointer:coarse pattern the rest of the app uses
    check("stepnav_has_pointer_coarse_touch_sizing", "@media (pointer:coarse)" in src and "#vw-stepnav button{min-height:44px" in src)

    # public API surface for anything that wants to trigger navigation programmatically (matches the
    # existing window.viewerSpeak/window.viewerStopSpeak convention already in this file)
    check("readaloud_js_exposes_viewerNextStep", "window.viewerNextStep=nextStep" in src)
    check("readaloud_js_exposes_viewerPrevStep", "window.viewerPrevStep=prevStep" in src)
    check("readaloud_js_exposes_viewerRepeatStep", "window.viewerRepeatStep=repeatStep" in src)

    # real syntax validation
    try:
        r = subprocess.run(["node", "--check", READALOUD_JS], capture_output=True, text=True, timeout=30)
        check("readaloud_js_passes_node_check", r.returncode == 0)
    except FileNotFoundError:
        check("readaloud_js_passes_node_check (node not on PATH -- skipped, not a failure)", True)

    # ES5-clean gate (this file is ES5-required -- loaded on every page, including MODERN_BY_DESIGN
    # exemptions don't apply to it)
    import rps_lint
    hits = rps_lint.scan_file(READALOUD_JS)
    check("readaloud_js_es5_clean", not hits)

    # procedure.html's markup shape still matches what stepNodes()/stepText() expect -- if this ever
    # changes independently, this test (not just a live click-through) should catch the drift
    proc_src = open(PROCEDURE_HTML, encoding="utf-8").read()
    check("procedure_html_still_uses_stepwrap_id", 'id="stepwrap"' in proc_src)
    check("procedure_html_still_uses_step_class", 'class="step' in proc_src)
    check("procedure_html_still_uses_dot_n_and_dot_body_classes", 'class="n"' in proc_src and 'class="body"' in proc_src)
    check("procedure_html_still_uses_chip_class_for_torque_fig_nsn",
          'class="chip' in proc_src)

    return passed, failed


if __name__ == "__main__":
    p, f = run()
    for n in p:
        print("PASS", n)
    for n in f:
        print("FAIL", n)
    print("\n%d passed, %d failed" % (len(p), len(f)))
    sys.exit(1 if f else 0)

# END OF FILE
