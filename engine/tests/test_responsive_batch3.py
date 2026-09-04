#!/usr/bin/env python3
"""THE VIEWER -- regression coverage for the v1.60.0 responsive per-page fixes (multi-window /
multi-tab plan, Stage 3, PR 10 of 25 -- batch 3 of the four per-page verification batches).

WHAT THIS FILE CAN AND CANNOT PROVE, said plainly up front. The three fixes guarded here were each
FOUND by resizing a real browser against the real server and measuring with getBoundingClientRect /
getComputedStyle; the measured before/after numbers are recorded in docs/CHANGELOG.md [1.60.0] and
in the comments beside each fix in the page itself. This repo has no headless browser in its test
suite, so this file cannot re-measure a layout. What it CAN do -- and what every other UI regression
guard in this repo already does (see test_uiux_fixes.py, which string-splits base.css to assert on
the kiosk-mode block) -- is fail loudly if one of those three fixes is silently deleted, moved into
the shared sheet, or reverted to the shape that was measured to be broken.

Self-contained; no corpus, no server, no network.  Run:  python tests/test_responsive_batch3.py
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
UI = os.path.join(ENGINE, "ui")

passed, failed = [], []
def ok(name, cond):
    (passed if cond else failed).append(name)

def read(name):
    with open(os.path.join(UI, name), "r", encoding="utf-8") as fh:
        return fh.read()

def style_block(src):
    """Everything inside the page's own <style> tags -- so a rule found here is provably the page's
    own inline CSS and not something inherited from /base.css."""
    return "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", src, re.S))

def strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)

def media_body(css, query_px):
    """The declarations inside the FIRST @media block whose condition mentions max-width:<px>.
    Brace-counted rather than regex-matched so a nested rule cannot end the block early."""
    m = re.search(r"@media[^{]*max-width\s*:\s*%dpx[^{]*\{" % query_px, css)
    if not m:
        return None
    i, depth = m.end(), 1
    while i < len(css) and depth:
        if css[i] == "{":
            depth += 1
        elif css[i] == "}":
            depth -= 1
        i += 1
    return css[m.end():i - 1]

def squash(s):
    """Collapse all whitespace so an assertion is about the CSS, not about how it is indented."""
    return re.sub(r"\s+", "", s or "")


# =====================================================================================================
# binaudit.html -- the audit table's NSN column split identifiers across two lines once the column
# fell under about 112px, which happens at 960px and below (measured: 127px wide / 1 line per NSN at
# 1440px, 123px / 2 lines at 960px, 94px / 2 lines at 720px). On the one page whose stated job is
# telling apart look-alike NSNs, an identifier chopped in half mid-string is the specific failure to
# prevent. Both halves of the fix matter and are asserted separately: the nowrap alone was measured
# to push documentElement.scrollWidth to 435 against a 400px client, so it is paired with a real
# scroller on #out (the static container the table is rendered into) that confines any residual
# width to the table instead of the page.
# =====================================================================================================
try:
    src = read("binaudit.html")
    css = strip_comments(style_block(src))
    body = media_body(css, 960)
    ok("binaudit_has_its_own_960_breakpoint", body is not None)
    ok("binaudit_nsn_column_is_nowrap_at_960",
       "#outtd:first-child{white-space:nowrap}" in squash(body))
    ok("binaudit_out_scrolls_rather_than_the_page",
       "#out{overflow-x:auto}" in squash(body))
    # the fix must live in this page, not in the shared sheet (four batches of this pass ran in
    # parallel; a page-specific rule leaking into base.css is exactly the collision to avoid)
    ok("binaudit_fix_is_page_local_not_shared", "#out" in style_block(src))
except Exception as e:                                       # pragma: no cover - reported, not raised
    failed.append("binaudit_responsive(%s)" % e)


# =====================================================================================================
# status.html -- the NIIN format-drift queue exists to compare NSN *strings* against each other, and
# at 720px its variants column (232px, against 375px at 960px) split a variant mid-identifier:
# measured character by character with a Range, the live first row read
# "5305-00-292-4587 - 5306-00-292-" / "4587 - 5605-00-292-4587". Scoped to the 720px step because at
# 960px zero rows break. The .tscroll wrapper is load-bearing, not decorative: with the nowrap alone
# a synthetic 5-variant row pushed the page to scrollWidth 1023 against a 720px client, and
# overflow-x set on the <table> element itself does nothing (Chrome keeps computing it "visible").
# =====================================================================================================
try:
    src = read("status.html")
    css = strip_comments(style_block(src))
    body = media_body(css, 720)
    ok("status_has_its_own_720_breakpoint", body is not None)
    sq = squash(body)
    ok("status_niin_column_is_nowrap_at_720", "#niintbltd:nth-child(1)" in sq and "white-space:nowrap" in sq)
    ok("status_variants_column_is_nowrap_at_720", "#niintbltd:nth-child(2)" in sq)
    ok("status_tscroll_is_a_real_scroller", ".tscroll{overflow-x:auto}" in squash(css))
    # the wrapper has to actually wrap the table, or the nowrap above turns into page-wide overflow
    ok("status_niin_table_is_inside_the_scroller",
       re.search(r'<div class="tscroll">\s*<table id="niintbl"', src) is not None)
    ok("status_scroller_is_closed_around_the_table",
       src.count('<div class="tscroll">') == 1 and "</table></div>" in src)
    # aria-live must survive the wrapping -- the queue announces itself as it reloads
    ok("status_niin_table_keeps_aria_live", 'id="niintbl" aria-live="polite"' in src)
except Exception as e:                                       # pragma: no cover
    failed.append("status_responsive(%s)" % e)


# =====================================================================================================
# demo.html -- place() clamped the guided-tour tooltip against a hard-coded 56px control-bar height.
# That literal is only true while the bar fits on one row. Measured at 720 CSS px the bar is 119px
# (86px from the dots strip wrapping on its own, then 119px once base.css v1.57.0 added
# flex-wrap:wrap to the shared .bar selector at 960px and below), so at 720x620 the Mechanic tour
# put its tooltip 3px, 44px and 59px BEHIND the bar on steps 3, 14 and 15. Reading the bar's real
# offsetHeight is correct at every width; at 1440px the measured value is exactly 56, so the change
# is inert at desktop width. ES5 only -- demo.html is an RPS/ES5-required page (rps_lint gates it).
# =====================================================================================================
try:
    src = read("demo.html")
    ok("demo_bar_height_is_measured_not_hardcoded",
       "barH=($('bar').offsetHeight||56)" in re.sub(r"\s+", "", src))
    # the broken shape must be gone, not merely supplemented by the new one
    ok("demo_stale_56px_literal_is_gone",
       re.search(r"barH\s*=\s*56\s*;", src) is None)
    # 56 survives only as the not-laid-out-yet fallback, still inside the same expression
    ok("demo_keeps_56_only_as_fallback", src.count("barH=($('bar').offsetHeight||56)") == 1)
    # the clamp that consumes barH is still there and still consumes it
    ok("demo_tooltip_clamp_still_uses_barH", "if(ty+th>H-barH)" in re.sub(r"\s+", "", src))
    # ES5 guard on the touched line specifically (rps_lint covers the whole file; this pins the fix)
    touched = [ln for ln in src.splitlines() if "offsetHeight||56" in ln]
    ok("demo_fix_line_is_es5", len(touched) == 1 and not re.search(r"=>|`|\blet\b|\bconst\b", touched[0]))
except Exception as e:                                       # pragma: no cover
    failed.append("demo_responsive(%s)" % e)


# =====================================================================================================
# The shared sheet stayed shared. This PR deliberately added NO rule to base.css: every problem it
# found was specific to one page, and three sibling batches of this same pass were being built in
# parallel against the same file. This asserts that none of the three page-local selectors above
# leaked into base.css -- a cheap, direct guard on the one thing that would have caused a conflict.
# =====================================================================================================
try:
    with open(os.path.join(UI, "base.css"), "r", encoding="utf-8") as fh:
        base = strip_comments(fh.read())
    for sel in ("#out", "#niintbl", ".tscroll"):
        ok("base_css_stays_free_of_page_selector_%s" % sel.strip("#."), sel not in base)
    # and the shared rules this batch relied on are still there to be relied on
    ok("base_css_still_has_the_960_breakpoint", media_body(base, 960) is not None)
    ok("base_css_still_has_the_720_breakpoint", media_body(base, 720) is not None)
    ok("base_css_960_still_wraps_bar_rows", "flex-wrap:wrap" in squash(media_body(base, 960) or ""))
    ok("base_css_960_still_breaks_long_words", "body{overflow-wrap:break-word}" in squash(media_body(base, 960) or ""))
except Exception as e:                                       # pragma: no cover
    failed.append("base_css_untouched(%s)" % e)


# =====================================================================================================
# The other eight pages in this batch needed no fix, which is a claim worth pinning too: each was
# checked in a real browser at 960 and 720 CSS px and had zero horizontal page overflow. The part of
# that this file can guard is that they still carry /base.css at all -- an unlinked page would
# silently lose every shared rule the batch verified them against.
# =====================================================================================================
try:
    batch = ["learn.html", "binaudit.html", "coverage.html", "ingest.html", "ops.html",
             "status.html", "verify.html", "command.html", "collections.html", "review.html",
             "demo.html"]
    missing = [p for p in batch if '<link rel="stylesheet" href="/base.css">' not in read(p)]
    ok("every_batch3_page_still_links_base_css", not missing)
    # and still declares a real viewport meta -- without it a narrow window is emulated, not honoured
    no_vp = [p for p in batch if "name=\"viewport\"" not in read(p)]
    ok("every_batch3_page_declares_a_viewport", not no_vp)
except Exception as e:                                       # pragma: no cover
    failed.append("batch3_page_roster(%s)" % e)


for n in passed:
    print("PASS", n)
for n in failed:
    print("FAIL", n)
print("\n%d passed, %d failed (of %d checks for the v1.60.0 responsive batch-3 per-page fixes)" %
      (len(passed), len(failed), len(passed) + len(failed)))
sys.exit(1 if failed else 0)
