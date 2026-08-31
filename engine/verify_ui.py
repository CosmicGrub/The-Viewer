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

# --- WCAG text-contrast guard (v1.29, roadmap Now-tier item 5): base.css's --grn/--red are correct
#     as decorative accents (3:1 non-text floor) but measured BELOW the 4.5:1 AA floor as actual TEXT
#     against the two backgrounds the app's live confirmation/warning copy renders on (--panel,
#     --panel2) -- --grn-tx/--red-tx are the lightened, text-safe siblings added alongside them for
#     exactly that use. This locks the fix in: if either --panel/--panel2 or the -tx pair's hex ever
#     drifts, this catches the regression instead of it silently shipping unreadable text again
#     (which is exactly how the original 2.98:1/4.02:1 failures went unnoticed in the first place).
def _hex_tokens(path):
    txt = open(path, encoding="utf-8").read()
    i = txt.find(":root{")
    if i < 0:
        return {}
    j = txt.find("}", i)
    block = txt[i:j]
    return dict(re.findall(r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{6})", block))


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
# (foreground token, background token, real call site) -- every pair this app actually renders as
# live text today. Through v1.29, index.html carried its own separate token copy (didn't load
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
sys.exit(rc)
