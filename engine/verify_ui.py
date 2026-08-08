#!/usr/bin/env python3
"""Syntax-check the inline <script> of the UI pages host-side (the sandbox mount truncates grown files)."""
import os, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = ["ui/threed.html", "ui/schematics.html", "ui/circuitlab.html", "ui/deepzoom.html",
         "ui/coverage.html", "ui/locate.html", "ui/jobcard.html", "ui/torque.html",
         "ui/bench.html", "ui/fastener.html", "ui/pmcs.html",
         "ui/semantic.html", "ui/related.html", "ui/visual.html",
         "ui/decode.html"]
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
sys.exit(rc)
