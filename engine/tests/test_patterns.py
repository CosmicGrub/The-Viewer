#!/usr/bin/env python3
"""Unit tests for engine/patterns.py (the shared NSN/FIG/part-number extractors). Pure stdlib runner."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import patterns as P

def run():
    passed, failed = [], []
    def check(name, cond):
        (passed if cond else failed).append(name)

    # norm_nsn: dashed, bare, and embedded all canonicalize the same; junk -> None
    check("norm dashed", P.norm_nsn("NSN 2540-01-123-4567 here") == "2540-01-123-4567")
    check("norm bare",   P.norm_nsn("pn 2540011234567 x")       == "2540-01-123-4567")
    check("norm none",   P.norm_nsn("no stock number") is None)

    # digits dedup: dashed and bare share the same digit string
    check("digits eq", P.digits("2540-01-123-4567") == P.digits("2540011234567") == "2540011234567")

    # FIG_RE: plain, dotted, and ranged
    figs = P.FIG_RE.findall("see FIG 5 and FIGURE 12-3, also FIG. 4")
    check("fig set", sorted(figs) == ["12-3", "4", "5"])

    # PN_RE: labeled part numbers only (not arbitrary tokens)
    pns = [m.group(1).upper() for m in P.PN_RE.finditer("Use P/N: MS35338-44 and PART NO. 12345-AB; bolt xyz")]
    check("pn labeled", "MS35338-44" in pns and "12345-AB" in pns)
    check("pn no false", not P.PN_RE.search("the alternator assembly bolt"))

    # nsn_fts_phrase: groups joined for an FTS phrase that matches the dashed form
    check("fts phrase", P.nsn_fts_phrase("2540-01-123-4567") == '"2540 01 123 4567"')
    check("fts none",   P.nsn_fts_phrase("nope") is None)

    # tm_side: operator (10) vs mechanic (20) "side of the house"
    op10 = P.tm_side("TM 9-2320-280-10")
    check("side -10 operator", op10["operator"] and not op10["mechanic"] and op10["coverage"] == "10")
    m20 = P.tm_side("TM 9-2320-280-20")
    check("side -20 mechanic", m20["mechanic"] and not m20["operator"])
    parts = P.tm_side("TM 9-2320-280-24P")
    check("side -24P mechanic", parts["mechanic"] and not parts["operator"])
    combo = P.tm_side("TM 9-2320-280-13&P")
    check("side -13&P both", combo["operator"] and combo["mechanic"])
    combo12 = P.tm_side("TM 11-5805-201-12&P")
    check("side -12 both", combo12["operator"] and combo12["mechanic"])
    lo = P.tm_side("LO 9-2320-280-12")
    check("side LO mechanic", lo["mechanic"])
    # the 3-digit equipment designator (280) must NOT be read as a coverage code
    check("side no false from designator", P.tm_side("TM 9-2320-280-10")["mechanic"] is False)
    # title fallback when no code present
    fb = P.tm_side("", title="Operator Manual for Widget")
    check("side title fallback op", fb["operator"])

    # confidence: code=high, title=medium, defaulted=low
    check("conf high", P.tm_side("TM 9-2320-280-10")["confidence"] == "high")
    check("conf medium", P.tm_side("", title="Operator Manual")["confidence"] == "medium")
    check("conf low", P.tm_side("SOMEDOC", title="Mystery Book")["confidence"] == "low")

    return passed, failed

if __name__ == "__main__":
    p, f = run()
    for n in p: print("PASS", n)
    for n in f: print("FAIL", n)
    print("\n%d passed, %d failed" % (len(p), len(f)))
    sys.exit(1 if f else 0)
