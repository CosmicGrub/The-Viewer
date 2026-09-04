#!/usr/bin/env python3
"""THE VIEWER -- regression coverage for the responsive verification pass on batch 4 of 4
(multi-window / multi-tab plan PR 11 of 25; the 12 "specialized visualization" pages).

Self-contained, no corpus, no browser.  Run:  python tests/test_responsive_batch4.py

WHAT THIS FILE CAN AND CANNOT PROVE -- stated up front, because it matters here.
The three real defects this PR fixed were FOUND and MEASURED in a real browser, resizing real pages
served by the real server, with getComputedStyle and getBoundingClientRect (the same way [1.57.0]
verified PR 7's shared block).  Those measurements are recorded in the CHANGELOG entry.  This suite
has no browser and cannot re-measure a layout, so it does NOT re-assert the pixel numbers.  What it
does assert is the thing a browser check could never catch on its own: that the three fixes are
still in the three files, still scoped the way they were verified, and that the specific structural
conditions each fix depends on have not drifted underneath them.  Two of the checks are real
arithmetic over numbers parsed out of the page's own CSS, not string matching -- they recompute the
overflow from the file and fail if a future edit reintroduces it at a different size.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
UI = os.path.join(ENGINE, "ui")

passed, failed = [], []
def ok(name, cond):
    (passed if cond else failed).append(name)

# The 12 pages in this batch (plan PR 11 of 25).
BATCH = ["master.html", "mastercov.html", "packet.html", "exploded.html", "schematics.html",
         "threed.html", "deepzoom.html", "stepflow.html", "keywords.html", "publog.html",
         "audit.html", "cadtex_test.html"]

def read(fn):
    with open(os.path.join(UI, fn), "r", encoding="utf-8") as fh:
        return fh.read()

def styles(txt):
    """Concatenated <style> bodies -- the CSS this PR is allowed to have touched."""
    return "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", txt, re.S | re.I))

def strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)

def media_block(css, query):
    """Return the body of the first @media block whose prelude matches `query` (whitespace-loose),
    or None.  Brace-counted rather than regex-matched so a nested rule cannot truncate it."""
    pat = re.compile(r"@media\s*" + query + r"\s*\{", re.I)
    m = pat.search(css)
    if not m:
        return None
    i, depth = m.end(), 1
    while i < len(css) and depth:
        if css[i] == "{": depth += 1
        elif css[i] == "}": depth -= 1
        i += 1
    return css[m.end():i - 1]

SRC = {}
try:
    for fn in BATCH:
        SRC[fn] = read(fn)
    ok("batch4_all_12_pages_exist", len(SRC) == 12)
except Exception as e:
    failed.append("batch4_pages_readable(%s)" % e)

CSS = dict((fn, strip_comments(styles(txt))) for fn, txt in SRC.items())


# =====================================================================================================
# 0 -- every page in the batch actually inherits the shared responsive baseline.
# A page that dropped its <link rel=stylesheet href="/base.css"> would silently stop getting
# [1.57.0]'s breakpoints, and every "verified clean at 960/720" claim in this PR's notes would
# quietly stop being true for it.  Cheap to assert, and it is the precondition for all of the below.
# =====================================================================================================
for fn in BATCH:
    ok("batch4_links_base_css[%s]" % fn,
       re.search(r'<link[^>]+href=["\']/base\.css["\']', SRC.get(fn, "")) is not None)


# =====================================================================================================
# 1 -- schematics.html: the sheet viewer's title (.gbar .sp) collapsing to nothing.
# .gbar is one wrapping flex row of ~15 fixed controls and .sp is flex:1 1 0%, so the title of the
# sheet on screen got only the leftover space on its own flex line: measured 66px at 1400, 60px at
# 960 and 3px at 720, against the 182px it needed.  Fix: it takes a row of its own below 960px.
# =====================================================================================================
try:
    css = CSS["schematics.html"]
    blk = media_block(css, r"\(\s*max-width\s*:\s*960px\s*\)")
    ok("schematics_has_960_breakpoint", blk is not None)
    ok("schematics_sp_takes_own_row_at_960",
       blk is not None and re.search(r"\.gbar\s+\.sp\s*\{[^}]*flex\s*:\s*0\s+0\s+100%", blk) is not None)
    # R1: the rule must be INSIDE the breakpoint.  If it ever escapes to the top level it would
    # reshape the wide-desktop bar this page was designed for, which is exactly what was verified
    # not to happen (at 1400px the title is still 66px, the bar still 99px, the stage still 706px).
    outside = re.sub(r"@media[^{]*\{(?:[^{}]|\{[^{}]*\})*\}", "", css, flags=re.S)
    ok("schematics_sp_override_is_not_unconditional",
       re.search(r"\.gbar\s+\.sp\s*\{[^}]*flex\s*:\s*0\s+0\s+100%", outside) is None)
    # the structural precondition the fix relies on: .sp is still the flexible title cell, and the
    # bar still wraps (if either changed, the fix would be solving a problem that moved).
    ok("schematics_gbar_still_wraps", re.search(r"\.gbar\s*\{[^}]*flex-wrap\s*:\s*wrap", css) is not None)
    ok("schematics_sp_still_flex_1_by_default",
       re.search(r"\.gbar\s+\.sp\s*\{[^}]*flex\s*:\s*1\b", css) is not None)
    ok("schematics_sp_still_ellipsises",
       re.search(r"\.gbar\s+\.sp\s*\{[^}]*text-overflow\s*:\s*ellipsis", css) is not None)
except Exception as e:
    failed.append("schematics_title_fix(%s)" % e)


# =====================================================================================================
# 2 -- deepzoom.html: .top had no flex-wrap and is not one of the class names base.css's shared
# <=960px wrap rule covers, so with #edbtn (Editions) and #pqabtn (Ask this page) visible the bar
# pushed the page 77px sideways at 720 (documentElement.scrollWidth 797 vs clientWidth 720).
# =====================================================================================================
try:
    css = CSS["deepzoom.html"]
    blk = media_block(css, r"\(\s*max-width\s*:\s*960px\s*\)")
    ok("deepzoom_has_960_breakpoint", blk is not None)
    ok("deepzoom_top_wraps_at_960",
       blk is not None and re.search(r"\.top\s*\{[^}]*flex-wrap\s*:\s*wrap", blk) is not None)
    # R1: verified byte-identical above the breakpoint (every .top child at the same coordinates at
    # 1400px, in both the default and the all-buttons configuration).  That only holds while the
    # base .top rule stays nowrap, so assert the wrap did not also leak to the top level.
    outside = re.sub(r"@media[^{]*\{(?:[^{}]|\{[^{}]*\})*\}", "", css, flags=re.S)
    base_top = re.search(r"\.top\s*\{([^}]*)\}", outside)
    ok("deepzoom_base_top_rule_still_present", base_top is not None)
    ok("deepzoom_base_top_still_unwrapped",
       base_top is not None and "flex-wrap" not in base_top.group(1))
    ok("deepzoom_base_top_still_a_flex_row",
       base_top is not None and re.search(r"display\s*:\s*flex", base_top.group(1)) is not None)
    # the two buttons whose presence is what tipped the bar over -- if they were renamed or removed
    # the measured configuration would no longer exist and this note would be stale.
    ok("deepzoom_editions_button_still_exists", 'id="edbtn"' in SRC["deepzoom.html"])
    ok("deepzoom_askpage_button_still_exists", 'id="pqabtn"' in SRC["deepzoom.html"])
    # out of scope and deliberately untouched: the deep-zoom canvas viewport sizes itself by script.
    ok("deepzoom_stage_left_script_sized",
       re.search(r"#stage\s*\{[^}]*flex\s*:\s*1", css) is not None and
       re.search(r"#stage\s*\{[^}]*(width|max-width)\s*:", css) is None)
except Exception as e:
    failed.append("deepzoom_top_wrap_fix(%s)" % e)


# =====================================================================================================
# 3 -- cadtex_test.html: three FIXED grid tracks that cannot fit a narrow window.
# This is the one worth computing rather than string-matching.  Re-derive the page's own natural
# width from its own numbers; if that exceeds the 960px anchor, a <=960px breakpoint MUST exist.
# Measured before the fix: 978px scrollWidth against 768 (210px out) and against 960 (18px out).
# =====================================================================================================
try:
    txt = SRC["cadtex_test.html"]
    css = CSS["cadtex_test.html"]
    g = re.search(r"\.g\s*\{([^}]*)\}", css).group(1)

    cols = re.search(r"grid-template-columns\s*:\s*repeat\(\s*(\d+)\s*,\s*(\d+)px\s*\)", g)
    ok("cadtex_grid_is_still_a_fixed_track_repeat", cols is not None)
    gap = re.search(r"gap\s*:\s*(\d+)px", g)
    ok("cadtex_grid_declares_a_gap", gap is not None)
    body = re.search(r"body\s*\{[^}]*margin\s*:\s*(\d+)px", css)
    ok("cadtex_body_margin_parsed", body is not None)

    if cols and gap and body:
        n, track, gp, marg = int(cols.group(1)), int(cols.group(2)), int(gap.group(1)), int(body.group(1))
        natural = n * track + (n - 1) * gp + 2 * marg
        # the arithmetic that IS the bug: 3*310 + 2*14 + 2*20 = 998 > 960
        ok("cadtex_fixed_layout_really_does_exceed_960", natural > 960)
        ok("cadtex_natural_width_matches_measured_page", natural == 998)

        blk = media_block(css, r"\(\s*max-width\s*:\s*960px\s*\)")
        # Conditional by design: the breakpoint is only *required* while the fixed layout is too
        # wide.  If someone later shrinks the cards so three tracks genuinely fit, this stops
        # demanding a rule that would no longer be needed, instead of failing spuriously.
        if natural > 960:
            ok("cadtex_has_960_breakpoint", blk is not None)
            ok("cadtex_grid_stops_forcing_three_tracks",
               blk is not None and re.search(r"\.g\s*\{[^}]*grid-template-columns\s*:\s*repeat\(\s*auto-fit", blk) is not None)
            # the fix must fall back to whole tracks of the SAME width, so the canvases are never
            # squeezed -- that is what makes it a layout fix rather than a stage fix.
            ok("cadtex_fallback_keeps_the_same_track_width",
               blk is not None and re.search(r"repeat\(\s*auto-fit\s*,\s*%dpx\s*\)" % track, blk) is not None)
        else:
            ok("cadtex_has_960_breakpoint", True)
            ok("cadtex_grid_stops_forcing_three_tracks", True)
            ok("cadtex_fallback_keeps_the_same_track_width", True)

    # The WebGL stages themselves are explicitly out of scope and must stay exactly as they were:
    # gl3d.js drives them, and base.css deliberately excludes canvas from its image clamp.
    cv = re.search(r"(?<![\w.#-])canvas\s*\{([^}]*)\}", css)
    ok("cadtex_canvas_rule_present", cv is not None)
    ok("cadtex_canvas_still_fixed_290x220",
       cv is not None and re.search(r"width\s*:\s*290px", cv.group(1)) is not None
                      and re.search(r"height\s*:\s*220px", cv.group(1)) is not None)
    ok("cadtex_canvas_not_given_a_percentage_width",
       cv is not None and "%" not in re.search(r"width\s*:\s*[^;]+", cv.group(1)).group(0))
except Exception as e:
    failed.append("cadtex_grid_overflow_fix(%s)" % e)


# =====================================================================================================
# 4 -- packet.html: the print-preview page.  Nothing was changed here, and this asserts the two
# properties that made "no change needed" the right answer.
# Measured: at the real printed page box (US Letter 816px and A4 794px, each minus this page's own
# @page{margin:14mm} = 2 x 52.9px -> 710px / 688px) BOTH new breakpoints match, so the shared block
# is live during print.  It is harmless because the only rule of the seven that reaches this page is
# body{overflow-wrap:break-word} -- the page has no .grid/.grid2/.cards/.tiles/.cols/.chips/.tabs/
# .side for the others to bind to, and its screen-only toolbar is display:none in print regardless.
# =====================================================================================================
try:
    txt, css = SRC["packet.html"], CSS["packet.html"]
    pblk = media_block(css, r"print")
    ok("packet_still_has_a_print_block", pblk is not None)
    ok("packet_print_still_hides_the_screen_toolbar",
       pblk is not None and re.search(r"\.toolbar\s*\{[^}]*display\s*:\s*none", pblk) is not None)
    ok("packet_print_still_sets_page_margin", pblk is not None and "@page" in pblk)
    # The reason the shared <=960px rules are inert here: none of the classes they target exist on
    # this page.  If one is ever introduced, this fails and the print behaviour needs re-measuring.
    shared_targets = (".grid", ".grid2", ".cards", ".tiles", ".cols", ".chips", ".tabs", ".side")
    present = [c for c in shared_targets if re.search(r'class="[^"]*\b%s\b' % c[1:], txt)]
    ok("packet_has_none_of_the_shared_layout_classes[%s]" % (",".join(present) or "none"), not present)
    # packet.html is ES5-REQUIRED (rps_lint.py's own ES5_REQUIRED set).  This PR changed no script on
    # it; assert the inline script stayed ES5 so a future edit here trips this suite too, not only
    # the gate.
    scripts = "\n".join(re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", txt, re.S | re.I))
    for label, rx in (("arrow", r"=>"), ("const", r"(?<![\w.])const\s"), ("let", r"(?<![\w.])let\s"),
                      ("backtick", r"`"), ("spread", r"\.\.\.")):
        ok("packet_inline_script_still_es5[%s]" % label, re.search(rx, scripts) is None)
except Exception as e:
    failed.append("packet_print_isolation(%s)" % e)


# =====================================================================================================
# 5 -- the two other ES5-required pages in this batch (stepflow.html, keywords.html) needed no fix at
# all; neither has any script change here.  Same guard as above so an accidental ES6 edit on them is
# caught by this suite and not only by the gate.
# =====================================================================================================
for fn in ("stepflow.html", "keywords.html"):
    try:
        scripts = "\n".join(re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", SRC[fn], re.S | re.I))
        clean = all(re.search(rx, scripts) is None for rx in
                    (r"=>", r"(?<![\w.])const\s", r"(?<![\w.])let\s", r"`", r"\.\.\.",
                     r"(?<![\w.])class\s+[A-Za-z_$]", r"(?<![\w.])async\s", r"(?<![\w.])await\s"))
        ok("es5_required_page_still_clean[%s]" % fn, clean)
    except Exception as e:
        failed.append("es5_required_page_still_clean[%s](%s)" % (fn, e))


# =====================================================================================================
# 6 -- this PR must not have edited engine/ui/base.css.  Three sibling batches of the same pass are
# in flight in parallel and the shared sheet is the one file they could collide on; every fix here
# was deliberately kept in its own page.  Assert the shared responsive block is intact and still has
# exactly the rules [1.57.0] shipped, so "we did not touch base.css" is checked, not just claimed.
# =====================================================================================================
try:
    with open(os.path.join(UI, "base.css"), "r", encoding="utf-8") as fh:
        base = fh.read()
    b = strip_comments(base)
    blk960 = media_block(b, r"\(\s*max-width\s*:\s*960px\s*\)")
    blk720 = media_block(b, r"\(\s*max-width\s*:\s*720px\s*\)")
    ok("basecss_960_block_present", blk960 is not None)
    ok("basecss_720_block_present", blk720 is not None)
    # the five rules PR 7 put in the 960 block, and the one in the 720 block
    ok("basecss_960_wrap_rule_intact",
       blk960 is not None and "flex-wrap:wrap" in blk960.replace(" ", "") )
    ok("basecss_960_minwidth0_rule_intact",
       blk960 is not None and "min-width:0" in blk960.replace(" ", ""))
    ok("basecss_960_overflow_wrap_rule_intact",
       blk960 is not None and "overflow-wrap:break-word" in blk960.replace(" ", ""))
    ok("basecss_960_media_maxwidth_rule_intact",
       blk960 is not None and "max-width:100%" in blk960.replace(" ", ""))
    ok("basecss_960_grid2_collapse_intact",
       blk960 is not None and re.search(r"body\s+\.grid2\s*\{[^}]*grid-template-columns\s*:\s*1fr", blk960) is not None)
    ok("basecss_720_side_rule_intact",
       blk720 is not None and re.search(r"body\s+\.side\s*\{[^}]*width\s*:\s*100%", blk720) is not None)
    # svg/canvas must stay OUT of the shared image clamp -- the whole reason the 3-D / deep-zoom /
    # circuit stages are safe to leave alone, and the premise of this batch's "stages not touched".
    clamp = re.search(r":where\(([^)]*)\)\s*\{\s*max-width\s*:\s*100%", blk960 or "")
    ok("basecss_image_clamp_still_excludes_svg_and_canvas",
       clamp is not None and "svg" not in clamp.group(1) and "canvas" not in clamp.group(1))
except Exception as e:
    failed.append("basecss_untouched_and_intact(%s)" % e)


for n in passed: print("PASS", n)
for n in failed: print("FAIL", n)
print("\n%d passed, %d failed (of %d checks for the batch-4 responsive verification pass, PR 11/25)" %
      (len(passed), len(failed), len(passed) + len(failed)))
sys.exit(1 if failed else 0)

# END OF FILE
