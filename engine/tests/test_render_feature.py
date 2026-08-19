#!/usr/bin/env python3
"""Unit tests for engine/features/render_feature.py's _locate_box() -- the word-box locator that
anchors OCR-driven page callouts (NSN / P/N / FIG) to their on-page coordinates. Pure stdlib runner,
no PDF/DB required since _locate_box() only operates on already-extracted word dicts."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "features"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import render_feature as RF


def run():
    passed, failed = [], []
    def check(name, cond):
        (passed if cond else failed).append(name)

    words = [
        {"x0": 0.10, "y0": 0.20, "x1": 0.15, "y1": 0.23, "t": "FIG"},
        {"x0": 0.30, "y0": 0.40, "x1": 0.34, "y1": 0.43, "t": "PAGE"},
        {"x0": 0.50, "y0": 0.60, "x1": 0.60, "y1": 0.63, "t": "MS35338-44"},
    ]

    # Regression for the confirmed finding: page_callouts() always calls _locate_box(words, "FIG")
    # for figure-reference callouts. "FIG" is exactly 3 chars, so the old `len(tok) >= 4` guard on
    # the substring-match branch could never be satisfied -- box was unconditionally None.
    box = RF._locate_box(words, "FIG")
    check("FIG token (3 chars) now locates its word box", box == [0.10, 0.20, 0.15, 0.23])

    # FIG_RE-style callouts also need to match when the PDF word layer spells it out as "FIGURE"
    # (tok="FIG" is a substring of wt="FIGURE").
    box2 = RF._locate_box([{"x0": 0.1, "y0": 0.1, "x1": 0.2, "y1": 0.12, "t": "FIGURE"}], "FIG")
    check("FIG token matches FIGURE word", box2 == [0.1, 0.1, 0.2, 0.12])

    # No match at all -> None (not an empty list, not an exception)
    check("no match -> None", RF._locate_box(words, "ZZZZZ") is None)
    check("empty words -> None", RF._locate_box([], "FIG") is None)

    # Existing callers are unaffected by lowering the guard from 4 to 3: labeled part numbers
    # (always >=4 chars by the page_callouts() caller check) still match by substring.
    pn_box = RF._locate_box(words, "MS35338-44")
    check("PN substring match unaffected", pn_box == [0.50, 0.60, 0.60, 0.63])

    # NSN digit-run matching (the other branch of _locate_box) is untouched by the guard change.
    nsn_words = [{"x0": 0.2, "y0": 0.2, "x1": 0.3, "y1": 0.22, "t": "2540-01-123-4567"}]
    nsn_box = RF._locate_box(nsn_words, "2540-01-123-4567")
    check("NSN digit match unaffected", nsn_box == [0.2, 0.2, 0.3, 0.22])

    # A too-short, non-digit token (2 chars) still correctly fails to match -- the guard change
    # only opened the door to 3-char tokens like "FIG", not arbitrarily short ones.
    check("2-char token still guarded off", RF._locate_box(words, "5G") is None)

    return passed, failed


if __name__ == "__main__":
    p, f = run()
    for n in p: print("PASS", n)
    for n in f: print("FAIL", n)
    print("\n%d passed, %d failed" % (len(p), len(f)))
    sys.exit(1 if f else 0)
