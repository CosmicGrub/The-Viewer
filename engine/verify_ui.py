#!/usr/bin/env python3
"""Syntax-check the inline <script> of the UI pages host-side (the sandbox mount truncates grown files)."""
import os, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = ["ui/threed.html", "ui/schematics.html", "ui/circuitlab.html", "ui/deepzoom.html",
         "ui/coverage.html", "ui/locate.html", "ui/jobcard.html", "ui/torque.html",
         "ui/bench.html", "ui/fastener.html", "ui/pmcs.html",
         "ui/semantic.html", "ui/related.html", "ui/visual.html",
         "ui/decode.html", "ui/kg.html"]
# external scripts to syntax-check directly (host-authoritative; sandbox mount truncates grown files)
SCRIPTS = ["ui/palette.js", "ui/deepzoom.js"]
rc = 0
for rel in PAGES:
    p = os.path.join(HERE, rel)
    h = open(p, encoding="utf-8").read()
    i = h.rfind("<script>")            # the inline (attribute-less) script block
    j = h.find("</script>", i)
    if i < 0 or j < 0:
        print(rel, "— no inline <script> found"); rc = 1; continue
    body = h[i+8:j]
    tmp = os.path.join(HERE, "_uicheck.js"); open(tmp, "w", encoding="utf-8").write(body)
    r = subprocess.run(["node", "--check", tmp])
    print(rel, "inline JS:", "OK" if r.returncode == 0 else "FAILED")
    rc = rc or r.returncode
    try: os.remove(tmp)
    except Exception: pass
for rel in SCRIPTS:
    p = os.path.join(HERE, rel)
    if not os.path.exists(p):
        print(rel, "— missing"); rc = 1; continue
    r = subprocess.run(["node", "--check", p])
    print(rel, ":", "OK" if r.returncode == 0 else "FAILED")
    rc = rc or r.returncode

# --- [hidden] guard (never let a menu/popover get stuck open again) --------------------------------
# A page that toggles elements via the `hidden` attribute MUST have `[hidden]{display:none}` in effect
# (inline, or via base.css). Otherwise a `display:` class overrides `hidden` and the element stays on
# screen -- the Tools-dropdown-stuck-open bug. base.css carries the global rule; index.html has it inline.
import glob, re
_base = os.path.join(HERE, "ui", "base.css")
if os.path.exists(_base):
    if "[hidden]" in open(_base, encoding="utf-8").read():
        print("ui/base.css : [hidden]{display:none} guard present  OK")
    else:
        print("ui/base.css : MISSING [hidden]{display:none} guard -- menus can get stuck open"); rc = 1
for p in sorted(glob.glob(os.path.join(HERE, "ui", "*.html"))):
    txt = open(p, encoding="utf-8").read()
    if not (re.search(r"\.hidden\s*=", txt) or "menupop" in txt):
        continue                                  # page doesn't toggle via `hidden` -> no guard needed
    rel = "ui/" + os.path.basename(p)
    if ("[hidden]" in txt) or ("base.css" in txt):
        print(rel, ": [hidden] guard OK")
    else:
        print(rel, ": FAIL -- toggles `hidden` but has NO [hidden]{display:none} guard (menu can stick open)")
        rc = 1

# --- shared.js dedup guard (v1.13.0 UI coherence): a page that loads /shared.js must NOT also
#     declare an inline `function esc(` / `function toast(` -- the inline copy (usually weaker:
#     fewer escaped chars, or a blocking pattern) would shadow the canonical shared helper.
#     Standalone injected scripts (palette.js, tagger.js) keep their own private copies by design.
_dup = []
for p in sorted(glob.glob(os.path.join(HERE, "ui", "*.html"))):
    txt = open(p, encoding="utf-8").read()
    if "/shared.js" not in txt:
        continue
    for fn in ("function esc(", "function toast("):
        if fn in txt:
            _dup.append("ui/%s declares inline `%s...` but loads /shared.js" % (os.path.basename(p), fn))
if _dup:
    for d in _dup:
        print("shared.js dedup : FAIL --", d)
    rc = 1
else:
    print("shared.js dedup : no page that loads /shared.js re-declares esc()/toast()  OK")

# --- console-crash guard: a print() line with a char the Windows console (cp1252) can't encode
#     crashes the whole diagnostic mid-run (e.g. the arrow -> or a check-mark). Keep console output cp1252-safe. ---
_bad = []
for pf in sorted(glob.glob(os.path.join(HERE, "*.py"))) + sorted(glob.glob(os.path.join(HERE, "tools", "notrunc", "*.py"))):
    try:
        src = open(pf, encoding="utf-8").read().splitlines()
    except Exception:
        continue
    for ln_no, ln in enumerate(src, 1):
        if "print(" not in ln:
            continue
        for ch in ln:
            if ord(ch) > 127:
                try:
                    ch.encode("cp1252")
                except Exception:
                    _bad.append("%s:%d %r" % (os.path.basename(pf), ln_no, ch))
if _bad:
    for b in _bad[:25]:
        print("console-crash risk (non-cp1252 char in print):", b)
    rc = 1
else:
    print("console charset : all print() lines are cp1252-safe  OK")

# --- WCAG text-contrast guard (v1.29, roadmap Now-tier item 5; generalized v1.45 -- a11y extension
#     pass). base.css's --grn/--red are correct as decorative accents (3:1 non-text floor) but measured
#     BELOW the 4.5:1 AA floor as actual TEXT against the two backgrounds the app's live confirmation/
#     warning copy renders on (--panel, --panel2) -- --grn-tx/--red-tx are the lightened, text-safe
#     siblings added alongside them for exactly that use.
#
#     v1.45 correction: the ORIGINAL form of this guard (still present just below, as _TEXT_PAIRS)
#     only ever opened ui/base.css's and ui/index.html's own :root{} blocks -- it never opened any of
#     the other 47 pages' CSS at all, and even for those two files it checked base.css's tokens in
#     isolation rather than simulating what a page's OWN local :root{} override does to the cascade.
#     That gap is exactly how status.html shipped a real .tag.bad failure (--red on --p2, 4.18:1)
#     invisible to CI, while its neighboring .tag.ok looked identical on paper but was actually FINE
#     (status.html's own :root override brightens --grn to something that clears 4.5:1) -- the guard
#     had no way to tell either apart because it never looked at status.html at all.
#     _scan_page_contrast() below fixes both gaps: (a) it opens all 48 ui/*.html pages, not just two,
#     and (b) for each page it resolves --tokens through that PAGE's own :root{} override layered on
#     top of base.css (cascade-aware), not base.css read in isolation. It parses each page's <style>
#     block(s) for CSS rules built from plain class selectors -- a single class (.tag), a compound
#     class chain with no combinator (.tag.bad), or a 2-level descendant pair (.warn .n) -- and for any
#     such rule carrying `color:var(--X)`, resolves the nearest OPAQUE background token it can find
#     (the rule's own background, else its constituent single-class rules, else -- for a demo.html
#     `.warn .n`-shaped case where the ancestor's own background is a translucent rgba() overlay --
#     the real class combinations the page's own HTML actually uses together, e.g. `class="step warn"`,
#     so `.step`'s opaque var(--panel) is found as the effective backdrop).
#     This is deliberately NOT a full CSS cascade/specificity engine -- it is a conservative static
#     scanner that only resolves selectors it can be confident about (plain classes, at most 2 levels)
#     and SKIPS (never guesses, never silently passes) anything it can't -- most notably the several
#     real color:var(--X) usages that are set via inline `style="..."` on JS-generated markup (e.g.
#     index.html's grn-tx/red-tx spans) with no co-located background in the same string; those have no
#     resolvable ancestor background without a real DOM+cascade simulation, which is out of scope for
#     a static text scanner. The small hand-verified _TEXT_PAIRS list below is kept, now explicitly
#     scoped to exactly that residual case, rather than silently dropping that coverage.
def _hex_tokens(path):
    txt = open(path, encoding="utf-8").read()
    i = txt.find(":root{")
    if i < 0:
        return {}
    j = txt.find("}", i)
    block = txt[i:j]
    return dict(re.findall(r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{6})", block))


# v1.47: was `^\.[A-Za-z0-9_-]+$` -- the character class had no `.` in it, so a compound-class
# token like `.tag.bad` (a SECOND `.` before "bad") could never match at all. Since _parse_css_rules()
# gates BOTH the single- and compound-selector branches behind this one check, every compound-selector
# rule on every page was silently discarded before parsing -- `compound` was provably always empty and
# that whole code path was dead, directly contradicting this scanner's own stated purpose of catching
# a regression to a real compound-selector failure like status.html's `.tag.bad`. Fixed: match one OR
# MORE `.class` segments concatenated with no separator (`(\.[A-Za-z0-9_-]+)+`), which still matches a
# lone `.tag` (one repetition) and now also matches `.tag.bad` (two repetitions) -- `_classes_in()`
# already knows how to pull every class out of either shape via `_CLASS_FIND_RE.findall()`.
_CLASS_TOKEN_RE = re.compile(r"^(?:\.[A-Za-z0-9_-]+)+$")
_CLASS_FIND_RE = re.compile(r"\.[A-Za-z0-9_-]+")
_VAR_RE = re.compile(r"var\(\s*--([\w-]+)")
_STYLE_BLOCK_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.S)
_RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")
_DECL_RE = re.compile(r"([a-zA-Z-]+)\s*:\s*([^;]+)")
_CLASS_ATTR_RE = re.compile(r'class="([^"]+)"')


def _is_pure_class_selector(token):
    return bool(_CLASS_TOKEN_RE.match(token.strip()))


def _classes_in(token):
    return tuple(c[1:] for c in _CLASS_FIND_RE.findall(token))


def _page_tokens(html_path, base_tokens):
    """Cascade-aware token resolution: base.css's tokens, overridden by THIS page's own :root{}
    block if it has one -- the exact simulation missing before v1.45 (see comment above)."""
    toks = dict(base_tokens)
    toks.update(_hex_tokens(html_path))
    return toks


def _parse_css_rules(css_text):
    """Extract only plain-class selectors this scanner can be confident resolving: a single class,
    a no-combinator compound chain (.a.b), or a one-space 2-level descendant pair (.a .b). Anything
    else (IDs, tags, pseudo-classes, attribute selectors, >/~/+ combinators, 3+ levels) is skipped."""
    single, compound = {}, {}
    descendant = []
    for m in _RULE_RE.finditer(css_text):
        sel_group, decl_text = m.group(1), m.group(2)
        props = {}
        for pm in _DECL_RE.finditer(decl_text):
            props[pm.group(1).strip().lower()] = pm.group(2).strip()
        if not props:
            continue
        for sel in sel_group.split(","):
            sel = sel.strip()
            if not sel:
                continue
            parts = sel.split()
            if len(parts) == 1:
                if not _is_pure_class_selector(parts[0]):
                    continue
                classes = _classes_in(parts[0])
                if len(classes) == 1:
                    single.setdefault(classes[0], {}).update(props)
                else:
                    compound.setdefault(frozenset(classes), {}).update(props)
            elif len(parts) == 2:
                a, b = parts
                if not (_is_pure_class_selector(a) and _is_pure_class_selector(b)):
                    continue
                descendant.append((_classes_in(a), _classes_in(b), props))
    return single, compound, descendant


def _token_from_value(val, tokens):
    m = _VAR_RE.search(val)
    if m:
        return tokens.get(m.group(1))
    m2 = re.match(r"#([0-9a-fA-F]{6})\b", val.strip())
    return ("#" + m2.group(1)) if m2 else None


def _is_opaque_solid(val):
    v = val.strip().lower()
    return not (v.startswith("rgba(") or v.startswith("hsla(")
                or v.startswith("linear-gradient") or v.startswith("radial-gradient") or v.startswith("url("))


def _bg_from_props(props, tokens):
    for key in ("background-color", "background"):
        if key in props and _is_opaque_solid(props[key]):
            hexv = _token_from_value(props[key], tokens)
            if hexv:
                return hexv
    return None


def _is_large_text(props):
    """3:1 floor applies at >=18pt (~24px) or >=14pt-bold (~18.66px + bold); default to the stricter
    4.5:1 floor whenever font-size can't be determined from this rule (safer than assuming large)."""
    m = re.search(r"([\d.]+)px", props.get("font-size", ""))
    if not m:
        return False
    size_px = float(m.group(1))
    bold = props.get("font-weight", "").strip() in ("700", "800", "900", "bold")
    return size_px >= 24 or (size_px >= 18.66 and bold)


def _html_class_combos(html_text):
    """Real class co-occurrences from the page's own markup (e.g. `class="step warn"`) -- used as a
    fallback when a selector's own background is translucent/unresolvable, so the ancestor's real
    sibling class in actual usage (e.g. .step's opaque background under .warn's rgba() tint) is found
    instead of giving up. This is reading real HTML, not guessing."""
    return [m.group(1).split() for m in _CLASS_ATTR_RE.finditer(html_text) if len(m.group(1).split()) >= 2]


def _resolve_bg_for_classes(classes, single, compound, combos, tokens):
    fs = frozenset(classes)
    if fs in compound:
        bg = _bg_from_props(compound[fs], tokens)
        if bg:
            return bg
    for cn in classes:
        if cn in single:
            bg = _bg_from_props(single[cn], tokens)
            if bg:
                return bg
    for combo in combos:
        if any(cn in combo for cn in classes):
            for cn in combo:
                if cn in single:
                    bg = _bg_from_props(single[cn], tokens)
                    if bg:
                        return bg
    return None


def _scan_page_contrast(html_path, base_tokens, contrast_fn):
    html_text = open(html_path, encoding="utf-8").read()
    tokens = _page_tokens(html_path, base_tokens)
    css = "".join(m.group(1) for m in _STYLE_BLOCK_RE.finditer(html_text))
    single, compound, descendant = _parse_css_rules(css)
    combos = _html_class_combos(html_text)
    out = []  # (label, ratio_or_None, floor_or_None, "OK"|"FAIL"|"SKIP")

    def _check(label, classes_for_bg, props):
        if "color" not in props:
            return
        fg = _token_from_value(props["color"], tokens)
        if not fg:
            return
        # A descendant rule can set its OWN background right alongside color (e.g.
        # `.res .pill{color:#06223f;background:var(--acc)}` -- a self-contained badge, not relying
        # on its ancestor's background at all). That always wins over the ancestor-based fallback --
        # skipping this check was a real bug caught while validating this scanner against the actual
        # 48 pages (it was resolving such badges against their ANCESTOR's background instead, e.g.
        # .res's dark panel, producing bogus near-1:1 "failures" for badges that are actually fine).
        bg = _bg_from_props(props, tokens) or _resolve_bg_for_classes(classes_for_bg, single, compound, combos, tokens)
        if not bg:
            out.append((label, None, None, "SKIP"))
            return
        r = contrast_fn(fg, bg)
        floor = _AA_UI_FLOOR if _is_large_text(props) else _AA_TEXT_FLOOR
        out.append((label, r, floor, "FAIL" if r < floor else "OK"))

    for classes, props in compound.items():
        _check("." + ".".join(sorted(classes)), classes, props)
    for anc, chi, props in descendant:
        _check("." + ".".join(anc) + " ." + ".".join(chi), anc, props)
    return out


def _contrast(hex_a, hex_b):
    def lin(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    def lum(h):
        h = h.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)

    l1, l2 = lum(hex_a), lum(hex_b)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


_AA_TEXT_FLOOR = 4.5
# (foreground token, background token, real call site) -- v1.45: NOW SCOPED to exactly the residual
# case _scan_page_contrast() (above) can't reach -- inline `style="color:var(--X)"` set on JS-built
# markup with no background declared in the same string, so there's no CSS rule for the scanner to
# resolve an ancestor background from without a real DOM+cascade simulation (out of scope for a static
# text scanner; see the long comment above _scan_page_contrast). Every pair below is a real render
# call site, hand-verified. Through v1.29, index.html carried its own separate token copy (didn't load
# base.css) so both sources needed checking to catch either one drifting out of sync -- as of v1.30
# (roadmap Next-tier item 11) index.html loads base.css directly and no longer has its own :root at
# all, so checking it below now correctly SKIPs (no token block to check) rather than failing; kept
# in the loop rather than dropped so a FUTURE local :root re-added to index.html gets caught again.
_TEXT_PAIRS = [
    ("grn-tx", "panel2", "index.html part-match 'Saved' confirmation"),
    ("grn-tx", "panel", "index.html side-chooser operator badge / chapter-count status"),
    ("red-tx", "panel2", "index.html barcode-vs-OCR NSN mismatch warning"),
]
_AA_UI_FLOOR = 3.0
# (border token, background token, real call site) -- v1.30 (roadmap Next-tier item 12): --line is
# 1.05-1.45:1 everywhere (fine for a decorative divider, no floor applies) but was ALSO the visible
# border of every real <input>/<select>/<textarea> in index.html -- a UI component, 3:1 floor, which
# --line badly fails. --line-ctl is the lightened sibling for control borders only; --line is
# untouched for its decorative uses (so it is deliberately NOT checked against the 3:1 floor here).
_UI_BORDER_PAIRS = [
    ("line-ctl", "panel2", "index.html .searchbar/.modal/.pgctl/#legacyHome input borders"),
    ("line-ctl", "panel", "index.html .item input borders"),
]
for src_name in ("ui/base.css", "ui/index.html"):
    toks = _hex_tokens(os.path.join(HERE, src_name))
    if not toks:
        print("wcag text-contrast : SKIP -- %s has no :root{} token block" % src_name)
        continue
    for fg, bg, where in _TEXT_PAIRS:
        if fg not in toks or bg not in toks:
            print("wcag text-contrast : SKIP -- %s missing --%s or --%s" % (src_name, fg, bg))
            continue
        r = _contrast(toks[fg], toks[bg])
        if r < _AA_TEXT_FLOOR:
            print("wcag text-contrast : FAIL -- %s: --%s on --%s (%s) is %.2f:1, below the %.1f:1 AA floor"
                  % (src_name, fg, bg, where, r, _AA_TEXT_FLOOR))
            rc = 1
        else:
            print("wcag text-contrast : %s --%s on --%s = %.2f:1  OK (%s)" % (src_name, fg, bg, r, where))
    for fg, bg, where in _UI_BORDER_PAIRS:
        if fg not in toks or bg not in toks:
            print("wcag ui-contrast : SKIP -- %s missing --%s or --%s" % (src_name, fg, bg))
            continue
        r = _contrast(toks[fg], toks[bg])
        if r < _AA_UI_FLOOR:
            print("wcag ui-contrast : FAIL -- %s: --%s on --%s (%s) is %.2f:1, below the %.1f:1 UI floor"
                  % (src_name, fg, bg, where, r, _AA_UI_FLOOR))
            rc = 1
        else:
            print("wcag ui-contrast : %s --%s on --%s = %.2f:1  OK (%s)" % (src_name, fg, bg, r, where))

# --- WCAG text-contrast guard, generalized (v1.45, a11y extension pass): scans every ui/*.html page's
#     own <style> block(s) -- not just base.css/index.html -- for class-selector color+background
#     pairs, with cascade-aware token resolution per page (see _scan_page_contrast above for the full
#     rationale). This is what actually catches the bug class that let status.html's real .tag.bad
#     failure ship invisibly to CI before v1.45: a page-local :root override drifting a token's
#     effective color away from what base.css's own comments assume.
_base_tokens = _hex_tokens(os.path.join(HERE, "ui", "base.css"))
_scan_ok = _scan_fail = _scan_skip = 0
for p in sorted(glob.glob(os.path.join(HERE, "ui", "*.html"))):
    rel = "ui/" + os.path.basename(p)
    for label, r, floor, status in _scan_page_contrast(p, _base_tokens, _contrast):
        if status == "FAIL":
            print("wcag text-contrast (scan) : FAIL -- %s %s is %.2f:1, below the %.1f:1 floor"
                  % (rel, label, r, floor))
            rc = 1
            _scan_fail += 1
        elif status == "OK":
            _scan_ok += 1
        else:
            _scan_skip += 1
print("wcag text-contrast (scan) : checked %d class/descendant color+background pairs across all "
      "48 ui/*.html pages -- %d OK, %d FAIL, %d SKIP (no resolvable opaque background found -- e.g. a "
      "translucent rgba() overlay, or an inline style with no co-located background; this is a "
      "conservative static scanner, not a full CSS cascade simulator -- see the comment above "
      "_scan_page_contrast)" % (_scan_ok + _scan_fail + _scan_skip, _scan_ok, _scan_fail, _scan_skip))
sys.exit(rc)
