#!/usr/bin/env python3
"""A1 -- home nav pop-out links on engine/ui/index.html (multi-window support, PR 12 of
docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md, stage 4).

WHAT THIS COVERS, and why it is worth having: every entry in index.html's Tools nav is now a row
carrying its original <a> plus an adjacent "open in its own window" button wired to [1.53.0]'s
VW.windows.open(). All of that is *markup*, which the design spec's own Testing section lists under
"fully automatable" -- so it is tested here structurally, against the real shipped file, rather than
asserted in a PR description:

  - every real nav link sits in a .mrow next to exactly one pop-out button (and no nav link was
    missed -- checked by removing the rows and confirming no stray link is left behind);
  - the pop-out is a real <button> (so it is keyboard-focusable and in the tab order) carrying a
    non-empty aria-label that names its OWN row's destination -- an icon-only unlabeled ↗, or one
    whose label drifted onto a neighbour's page by copy-paste, both fail here;
  - the original links are untouched: same href, still a real <a>, every href a currently-registered
    route (cross-checked against features/routes/*.py, the same technique test_uiux_fixes.py already
    uses for the ES5 fallback's links);
  - the documented window-naming rule produces a UNIQUE name per row and the SAME name whatever
    "?q=..." threadQuery() has appended -- which is the entire mechanism behind "click it twice, get
    one window", so a collision here would silently make one row steal another's window;
  - the wiring really calls VW.windows.open with a name (not a bare window.open), /shared.js is
    really loaded on this page and really loads before the script that uses it, and #pnReviewBtn --
    a modal opener, not a link -- deliberately has no pop-out.

WHAT THIS CANNOT COVER, stated plainly rather than implied away (the same framing every prior PR in
this initiative has used): whether clicking ↗ in a real browser genuinely opens a window, and whether
clicking it a second time re-uses that same window instead of opening another. That is browser
behavior driven by window.open's name argument, there is no in-browser JS test runner in this
project's suite, and PR 5's own test_windows_node.js says the same thing about the layer underneath
this one. It is a MANUAL check, called out as manual in the PR body.

Self-contained; no corpus, no server. Run:  python engine/tests/test_home_nav_popout.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
INDEX_HTML = os.path.join(ENGINE, "ui", "index.html")

passed, failed = [], []


def ok(name, cond):
    (passed if cond else failed).append(name)


def say(msg):
    """ASCII-only diagnostic print. The nav labels this file inspects are full of emoji, and a plain
    print() of one on a cp1252 Windows console raises UnicodeEncodeError -- which, inside the big
    try/except below, would turn an ordinary FAIL into a swallowed exception AND skip every
    assertion after it. Caught for real while mutation-testing this file, not theorised. Matches the
    'ASCII output (cp1252-safe console)' convention engine/tools/check_onboarding_menu.py states."""
    print(str(msg).encode("ascii", "backslashreplace").decode("ascii"))


_ATTR_RE = re.compile(r'([A-Za-z-]+)\s*=\s*"([^"]*)"')


def attrs(tag_text):
    """name -> value for one start tag's attributes. Order-independent on purpose: asserting an
    exact attribute ORDER would fail on a harmless reformat while proving nothing extra."""
    return dict(_ATTR_RE.findall(tag_text))


def plain_label(inner_html):
    """The link's visible label with its leading emoji/space stripped: '📋 Part dossier' ->
    'Part dossier'. Everything before the first ASCII letter/digit/'(' is decoration."""
    return re.sub(r"^[^A-Za-z0-9(]+", "", inner_html).strip()


def popout_name(href):
    """Python mirror of index.html's own popoutName(): strip the query/fragment and the leading and
    trailing slashes, then prefix 'vw-'.

    Being a mirror, this proves the naming RULE is sound over the real hrefs -- unique per row, and
    unchanged by whatever '?q=...' threadQuery() appends -- but it cannot prove index.html implements
    that rule, since breaking the JS leaves this Python untouched (confirmed by mutation: gutting the
    real popoutName's query strip flipped only the source-text check below, not these). The
    index_html_strips_query_before_naming / index_html_derives_the_name_in_one_place assertions are
    what actually pin the implementation; these pin the rule it implements."""
    base = href.split("?")[0].split("#")[0].strip("/")
    return "vw-" + (re.sub(r"[^A-Za-z0-9_-]+", "-", base) if base else "home")


try:
    html = open(INDEX_HTML, encoding="utf-8").read()

    # ---- isolate the nav list itself (the Tools menu popup), so nothing below can accidentally be
    #      satisfied by markup elsewhere on this 2,300-line page.
    pop = html.split('<div class="menupop" id="toolsPop"', 1)[1].split("</div>\n    </div>", 1)[0]
    ok("toolspop_block_isolated", len(pop) > 1000 and "mgrouplbl" in pop)

    rows = re.findall(r'<div class="mrow">(.*?)</div>', pop, re.S)
    # vacuousness guard: every assertion below iterates these rows, so a regex that matched nothing
    # would make the whole file pass while proving nothing at all.
    ok("nav_rows_found_at_least_25", len(rows) >= 25)

    # ---- no nav link was skipped: with the rows removed, no <a href> may remain in the menu.
    leftovers = re.findall(r"<a\s[^>]*href=", re.sub(r'<div class="mrow">.*?</div>', "", pop, flags=re.S))
    ok("every_nav_link_is_inside_a_popout_row", not leftovers)

    parsed = []
    for row in rows:
        a_tags = re.findall(r"<a\s([^>]*)>(.*?)</a>", row, re.S)
        b_tags = re.findall(r"<button\s([^>]*)>(.*?)</button>", row, re.S)
        parsed.append((a_tags, b_tags))

    ok("every_row_has_exactly_one_link", all(len(a) == 1 for a, _ in parsed))
    ok("every_row_has_exactly_one_popout_control", all(len(b) == 1 for _, b in parsed))

    links = [attrs(a[0][0]) for a, _ in parsed]
    labels = [a[0][1] for a, _ in parsed]
    btns = [attrs(b[0][0]) for _, b in parsed]
    glyphs = [b[0][1] for _, b in parsed]

    # ---- the pop-out control itself: a REAL button (focusable, in the tab order by default), with a
    #      real accessible name. This project has fixed unlabeled controls for real before
    #      ([1.46.0]/[1.47.0]); an icon-only ↗ would put one straight back.
    ok("every_popout_is_class_popout", all(b.get("class") == "popout" for b in btns))
    ok("every_popout_is_type_button", all(b.get("type") == "button" for b in btns))
    ok("every_popout_has_nonempty_aria_label", all((b.get("aria-label") or "").strip() for b in btns))
    ok("every_popout_has_a_hover_title", all((b.get("title") or "").strip() for b in btns))
    ok("every_popout_aria_label_says_new_window",
       all("new window" in (b.get("aria-label") or "") for b in btns))
    ok("every_popout_glyph_is_the_popout_arrow", all(g.strip() == "↗" for g in glyphs))

    # ---- the label must name THIS row's destination, not a neighbour's. This is the check that
    #      catches the realistic failure mode for 30 hand-written labels: a copy-paste that leaves
    #      "Open Ops in a new window" sitting next to the Coverage link.
    mismatched = [(labels[i], btns[i].get("aria-label", ""))
                  for i in range(len(links))
                  if plain_label(labels[i]) not in (btns[i].get("aria-label") or "")]
    ok("every_popout_aria_label_names_its_own_row", not mismatched)
    if mismatched:
        say("  aria-label/link mismatches: %r" % (mismatched[:5],))

    # ---- the original links are untouched: still real <a href="/...">, still going somewhere real.
    hrefs = [l.get("href", "") for l in links]
    ok("every_row_link_is_a_real_root_path", all(h.startswith("/") and " " not in h for h in hrefs))
    ok("every_row_link_kept_its_title_tooltip", all((l.get("title") or "").strip() for l in links))

    routes_dir = os.path.join(ENGINE, "features", "routes")
    routes_py = "\n".join(open(os.path.join(routes_dir, fn), encoding="utf-8").read()
                          for fn in sorted(os.listdir(routes_dir)) if fn.endswith(".py"))
    dead = [h for h in hrefs if ('"%s"' % h) not in routes_py]
    ok("every_popout_target_is_a_registered_route", not dead)
    if dead:
        say("  unregistered hrefs: %r" % (dead,))

    # ---- window naming: unique per row, and stable across the "?q=..." threadQuery() appends on
    #      every menu open. Both are load-bearing -- the name IS the reuse mechanism.
    names = [popout_name(h) for h in hrefs]
    ok("window_names_are_unique_per_row", len(set(names)) == len(names))
    ok("window_names_survive_a_threaded_query",
       all(popout_name(h + "?q=gasket%20kit") == popout_name(h) for h in hrefs))
    ok("window_names_survive_a_replaced_query",
       all(popout_name(h + "?q=a") == popout_name(h + "?q=b") for h in hrefs))
    ok("window_names_are_prefixed_and_safe",
       all(re.match(r"^vw-[A-Za-z0-9_-]+$", n) for n in names))
    ok("window_name_matches_the_documented_example", popout_name("/torque?q=bolt") == "vw-torque")

    # ---- the wiring itself.
    ok("index_html_derives_the_name_in_one_place", "function popoutName(href){" in html)
    ok("index_html_strips_query_before_naming", 'split("?")[0].split("#")[0]' in html)
    ok("index_html_wires_every_popout_button", 'p.querySelectorAll("button.popout")' in html)
    ok("index_html_reads_the_href_off_the_sibling_link_at_click_time",
       'this.parentNode.querySelector("a[href]")' in html)
    ok("index_html_opens_through_vw_windows",
       "VW.windows.open(href,{name:popoutName(href)})" in html)
    ok("index_html_falls_back_to_a_named_window_open_if_shared_js_is_missing",
       "window.open(href, popoutName(href))" in html)

    # ---- VW.windows has to actually be on this page for any of the above to work.
    ok("index_html_loads_shared_js", '<script src="/shared.js">' in html)
    ok("index_html_loads_shared_js_before_the_tools_menu_script",
       0 <= html.find('src="/shared.js"') < html.find("v0.98.0: Tools menu"))
    shared_js = open(os.path.join(ENGINE, "ui", "shared.js"), encoding="utf-8").read()
    ok("shared_js_really_exports_vw_windows_open", "windows: { open: windowsOpen" in shared_js)

    # ---- the pop-out buttons must NOT trip the menu's existing "a button closes this popup" rule:
    #      popping several sections out in a row is the whole point, and closing after each one would
    #      force a re-open per pop-out and throw away the focus the user just placed.
    ok("popout_buttons_are_exempt_from_the_menu_autoclose",
       '/(^|\\s)popout(\\s|$)/.test(hit.className||"")' in html)
    ok("other_menu_buttons_still_close_the_menu",
       "close();\n  });" in html and 'id="pnReviewBtn"' in html)

    # ---- #pnReviewBtn opens a modal on this page; there is nothing to pop out, and it must not have
    #      been swept into a row by a careless bulk edit.
    ok("pnreviewbtn_has_no_popout_row",
       'id="pnReviewBtn"' in pop and not any('id="pnReviewBtn"' in r for r in rows))
except Exception as e:
    failed.append("home_nav_popout_markup(%s)" % e)


# ---- house convention: the page's inline scripts must still parse. Skips cleanly without node.
try:
    import subprocess
    import tempfile

    if subprocess.run(["node", "--version"], capture_output=True).returncode == 0:
        src = open(INDEX_HTML, encoding="utf-8").read()
        blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", src, re.S)
        ok("index_html_has_inline_scripts_to_check", len(blocks) >= 3)
        all_clean = True
        for b in blocks:
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
                f.write(b)
                tmp_path = f.name
            r = subprocess.run(["node", "--check", tmp_path], capture_output=True, text=True)
            if r.returncode != 0:
                all_clean = False
                print("  node --check:", r.stderr.strip()[:400])
            os.unlink(tmp_path)
        ok("index_html_inline_scripts_parse_with_node", all_clean)
    else:
        ok("node_unavailable_skip_syntax_check", True)
except Exception as e:
    failed.append("index_html_node_syntax(%s)" % e)


# ---- the ES5 fallback shell must be untouched by this change: #legacyHome and its two scripts are
#      the only thing a true ES5 engine ever runs on this page, and the markers this project's own
#      gate keys off must still bracket them.
try:
    sys.path.insert(0, os.path.join(ENGINE, "tools"))
    import check_es5_fallback as cef

    ok("es5_fallback_span_still_present",
       cef.extract_fallback_span(open(INDEX_HTML, encoding="utf-8").read()) is not None)
    ok("es5_fallback_still_clean_after_the_nav_change", cef.main() == 0)
except Exception as e:
    failed.append("es5_fallback_untouched(%s)" % e)


for n in passed:
    print("PASS", n)
for n in failed:
    print("FAIL", n)
print("\n%d passed, %d failed (A1 home-nav pop-out links, multi-window PR 12)" % (len(passed), len(failed)))
sys.exit(1 if failed else 0)

# END OF FILE
