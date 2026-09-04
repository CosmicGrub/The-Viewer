#!/usr/bin/env python3
"""THE VIEWER -- regression coverage for the responsive verification pass, batch 2 of 4.

Multi-window / multi-tab support, PR 9 of 25 in
docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md (Stage 3, "PR 8-11: per-page
verification"). base.css's shared breakpoints landed in [1.54.0] / PR 7; this batch resized 12 real
pages in a real browser at 960 and 720 CSS px and fixed the two that needed something the shared
rules do not cover.

WHAT THIS FILE CAN AND CANNOT PROVE -- stated plainly, because the design spec's own Testing
section insists on it. The finding itself (a control label split MID-WORD, a table silently clipped
inside an overflow:hidden card) is a rendered-layout fact: it needs a browser with a real viewport,
a real font, and getComputedStyle, none of which exist in this suite. Those measurements were taken
by hand against the running server and are quoted in the PR body and the CHANGELOG entry.

What IS honestly automatable -- and is what this file does -- is the structural half the design
spec calls "every markup-level change": that each fix is still present, still declares the property
that actually fixes the bug, is still scoped to the breakpoint it was measured at, and has not
quietly displaced the page rules it was written to sit beside. That is a real regression guard: it
fails loudly the moment someone deletes, moves, or unscopes one of these two rules, which is the
realistic way a fix like this rots.

Self-contained; no server, no corpus, no browser. Run:  python tests/test_responsive_batch2.py
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
UI = os.path.join(ENGINE, "ui")

passed, failed = [], []


def ok(name, cond):
    (passed if cond else failed).append(name)


# The 12 pages this batch resized, in the order the PR reports them.
BATCH = ["solve.html", "troubleshoot.html", "ask.html", "handover.html", "circuitlab.html",
         "scan.html", "semantic.html", "visual.html", "kg.html", "related.html",
         "index.html", "help.html"]


def read(fn):
    with open(os.path.join(UI, fn), "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def styles(html):
    """Concatenated inline <style> bodies with CSS comments stripped.

    Stripping comments is not cosmetic here: both fixes carry long doc comments that NAME the
    properties they set ("body{overflow-wrap:break-word}", "overflow-x:auto still clips ..."), so a
    naive substring search over the raw file would pass even if the real declaration were deleted
    and only the prose left behind. Every assertion below runs on comment-free CSS.
    """
    css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html, re.S | re.I))
    return re.sub(r"/\*.*?\*/", " ", css, flags=re.S)


def media_block(css, query):
    """Body of the first `@media <query>` block, brace-matched (a regex cannot nest)."""
    m = re.search(r"@media\s*" + re.escape(query) + r"\s*\{", css)
    if not m:
        return None
    i = m.end()
    depth = 1
    while i < len(css) and depth:
        if css[i] == "{":
            depth += 1
        elif css[i] == "}":
            depth -= 1
        i += 1
    return css[m.end():i - 1] if depth == 0 else None


def decls(block, selector):
    """Declarations of every rule in `block` whose selector list contains `selector`."""
    out = []
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", block or ""):
        parts = [s.strip() for s in sel.split(",")]
        if selector in parts:
            out.append(re.sub(r"\s+", "", body))
    return out


def norm(css):
    return re.sub(r"\s+", "", css)


# =====================================================================================================
# Shared preconditions for the whole batch. The responsive baseline only reaches a page at all if the
# page links base.css, and a width breakpoint only means anything if the page declares a viewport --
# without <meta name="viewport"> a mobile/narrow browser lays the page out at ~980px and then scales
# it down, so every rule verified in this pass would silently never fire there. Both are invariants
# this pass depends on for all 12 pages, and neither is guarded anywhere else.
# =====================================================================================================
for fn in BATCH:
    try:
        html = read(fn)
        ok("batch2_links_base_css[%s]" % fn,
           re.search(r'<link[^>]+href="/base\.css"', html) is not None)
        ok("batch2_declares_viewport_meta[%s]" % fn,
           re.search(r'<meta[^>]+name="viewport"[^>]+width=device-width', html) is not None)
    except Exception as e:
        failed.append("batch2_preconditions[%s](%s)" % (fn, e))


# =====================================================================================================
# FIX 1 -- index.html, the in-app document viewer's control row.
#
# Measured at 720px with the viewer open: .vbar's fourth .pgctl group (Clean, four range sliders with
# their labels, then Mirror / HD / Loupe / Callouts / Reset) is a flex row with no wrap, so every
# control was shrunk narrower than its own label; with base.css's shared body{overflow-wrap:break-word}
# active at the same width, four labels then broke MID-WORD (heights 52 -> 71px; "contrast" and "zoom"
# 16 -> 32px). Letting the row wrap returns every button to its natural width at a uniform 33px.
# =====================================================================================================
try:
    idx = styles(read("index.html"))
    blk960 = media_block(idx, "(max-width:960px)")
    ok("index_has_960_breakpoint", blk960 is not None)
    ok("index_pgctl_wraps_at_960", any("flex-wrap:wrap" in d for d in decls(blk960, ".pgctl")))

    # Scoped, not global: an unscoped .pgctl{flex-wrap:wrap} would also change the desktop toolbar,
    # which was verified as correct and is deliberately left alone.
    outside = re.sub(r"@media[^{]*\{(?:[^{}]|\{[^{}]*\})*\}", " ", idx, flags=re.S)
    ok("index_pgctl_wrap_not_applied_globally",
       "flex-wrap:wrap" not in norm("".join(decls(outside, ".pgctl"))))
    ok("index_pgctl_base_rule_still_a_flex_row",
       any(d.startswith("display:flex") for d in decls(outside, ".pgctl")))

    # The fix sits BESIDE this file's own pre-existing 920px block (main + the .vside rail), which it
    # must not have absorbed or displaced -- that block is what collapses the viewer at narrow width
    # and it was verified working at 720px in this same pass.
    blk920 = media_block(idx, "(max-width:920px)")
    ok("index_920_block_still_present", blk920 is not None)
    ok("index_920_still_collapses_main",
       any("grid-template-columns:1fr" in d for d in decls(blk920, "main")))
    ok("index_920_still_widens_vside",
       any("width:100%" in d for d in decls(blk920, ".vside")))
    ok("index_920_still_hides_vthumbs",
       any("display:none" in d for d in decls(blk920, ".vthumbs")))

    # The two breakpoints stay distinct on purpose (960 is the shared pass anchor; 920 is this file's
    # own long-standing layout collapse). Merging them would silently change one of the two.
    ok("index_960_block_does_not_touch_main_or_vside",
       decls(blk960, "main") == [] and decls(blk960, ".vside") == [])
except Exception as e:
    failed.append("index_pgctl_wrap_fix(%s)" % e)


# =====================================================================================================
# FIX 2 -- handover.html, the digest cards.
#
# .card is overflow:hidden (for its rounded corners), so a table wider than the card is silently cut
# off: no scrollbar, no page-level overflow, just missing columns. Measured at 720px: a 1299px table
# clipped inside a 670px card. Latent rather than observed with today's data -- the two WIRED tables
# fit at 720px -- but the conflicts / due-services rows render raw JSON.stringify output, which
# overflow-wrap cannot break because it does not affect a table column's min-content width.
# =====================================================================================================
try:
    hv = styles(read("handover.html"))
    hblk = media_block(hv, "(max-width:960px)")
    ok("handover_has_960_breakpoint", hblk is not None)
    ok("handover_card_scrolls_x_at_960", any("overflow-x:auto" in d for d in decls(hblk, ".card")))

    # The base rule must keep overflow:hidden -- that is what clips the rounded corners, and the fix
    # is deliberately an override at one breakpoint, not a removal.
    houtside = re.sub(r"@media[^{]*\{(?:[^{}]|\{[^{}]*\})*\}", " ", hv, flags=re.S)
    ok("handover_card_base_still_overflow_hidden",
       any("overflow:hidden" in d for d in decls(houtside, ".card")))
    ok("handover_card_scroll_not_applied_globally",
       "overflow-x:auto" not in norm("".join(decls(houtside, ".card"))))

    # overflow-y must NOT be loosened: only the horizontal axis was the problem, and an auto y would
    # add a second scrollbar to every card on the page.
    ok("handover_fix_does_not_touch_overflow_y",
       all("overflow-y" not in d and not re.search(r"(?<!-)overflow:", d)
           for d in decls(hblk, ".card")))

    # The tables the fix protects are still rendered into these cards by the page's own script.
    hs = read("handover.html")
    ok("handover_still_renders_tables_into_cards",
       hs.count("<table>") >= 4 and 'class="card"' in hs)
except Exception as e:
    failed.append("handover_card_overflow_fix(%s)" % e)


# =====================================================================================================
# The other ten pages in this batch needed NO page-local fix: the shared base.css rules already
# covered them, verified by measuring each at 960 and 720. Assert that stays true in the only way a
# static check honestly can -- none of them has since grown a page-local width breakpoint that would
# quietly reopen the question this pass just closed. help.html is excluded: its own
# @media(max-width:720px) grid collapse predates this work ([1.54.0]'s base.css comment cites it as
# one of the four pages the 720 anchor was taken FROM), and it was re-verified working in this pass.
# =====================================================================================================
NO_LOCAL_BREAKPOINT = ["troubleshoot.html", "ask.html", "circuitlab.html", "scan.html",
                       "semantic.html", "visual.html", "kg.html", "related.html"]
for fn in NO_LOCAL_BREAKPOINT:
    try:
        found = re.findall(r"@media[^{]*max-width[^{]*\{", styles(read(fn)))
        ok("batch2_no_page_local_width_breakpoint[%s]" % fn, found == [])
    except Exception as e:
        failed.append("batch2_no_page_local_width_breakpoint[%s](%s)" % (fn, e))

# solve.html and help.html each keep exactly one long-standing local collapse, both re-verified in
# this pass and both deliberately left alone (solve at 760px, help at 720px).
try:
    ok("solve_keeps_its_own_760_grid_collapse",
       any("grid-template-columns:1fr" in d
           for d in decls(media_block(styles(read("solve.html")), "(max-width:760px)"), ".grid")))
    ok("help_keeps_its_own_720_grid_collapse",
       any("grid-template-columns:1fr" in d
           for d in decls(media_block(styles(read("help.html")), "(max-width:720px)"), ".grid")))
except Exception as e:
    failed.append("batch2_preexisting_local_collapses(%s)" % e)


for n in passed:
    print("PASS", n)
for n in failed:
    print("FAIL", n)
print("\n%d passed, %d failed (of %d checks for the responsive verification pass, batch 2 of 4)" %
      (len(passed), len(failed), len(passed) + len(failed)))
sys.exit(1 if failed else 0)

# END OF FILE
