"""rpstl.py -- structured import of the REPAIR PARTS & SPECIAL TOOLS LIST (R13 idea #1; completeness). An
RPSTL is the authoritative parts breakdown of a manual: for each figure, an ordered list of items, each with
an item number, an SMR code (source/maintenance/recoverability), a CAGEC, a part number, a quantity, and a
nomenclature -- and usually an NSN. Turning that free/tabular text into structured rows lets the app answer
'what's item 7 on figure 4?', build accurate kits, and reconcile against PUBLOG.

parse_line() and parse() are pure and unit-testable. Read-only; every parsed row keeps enough to cite back."""

from __future__ import annotations
import re

_NSN = re.compile(r"\b(\d{4}-\d{2}-\d{3}-\d{4}|\d{4}-\d{3}-\d{4})\b")
_SMR = re.compile(r"\b([A-Z]{1}[A-Z0-9]{4,5})\b")            # e.g. PAOZZ, PAFZZ, XAOZZ, PBOZZ
_SMR_OK = re.compile(r"^[PXKMAF][A-Z0-9]{4,5}$")
_CAGEC = re.compile(r"\b([0-9A-Z]{5})\b")
_FIG = re.compile(r"\b(?:FIG(?:URE)?\.?)\s*([0-9]{1,3}[A-Z]?)\b", re.I)
_ITEM = re.compile(r"\b(?:ITEM|IND(?:EX)?)\s*(?:NO\.?)?\s*([0-9]{1,3})\b", re.I)
_QTY = re.compile(r"\b(?:QTY|QUANTITY|Q/?A|REQD)\s*[:.]?\s*([0-9]{1,3})\b", re.I)


def parse_line(line, default_fig=None):
    """Best-effort parse of one RPSTL row -> dict or None. Keeps only rows that carry an NSN or a
    (part number + item) so prose lines are ignored."""
    if not line or len(line.strip()) < 6:
        return None
    t = re.sub(r"\s+", " ", line).strip()
    nsn = _NSN.search(t)
    fig = _FIG.search(t)
    item = _ITEM.search(t)
    qty = _QTY.search(t)
    # SMR: a 5-6 char code that looks like a maintenance code
    smr = None
    for m in _SMR.finditer(t):
        if _SMR_OK.match(m.group(1)):
            smr = m.group(1); break
    # CAGEC: a 5-char alnum that isn't the SMR and isn't part of the NSN
    cagec = None
    for m in _CAGEC.finditer(t):
        c = m.group(1)
        if c == smr or (nsn and c in nsn.group(0)):
            continue
        if c.isdigit() and len(c) == 5:            # cagec is often all digits
            cagec = c; break
        if not c.isdigit():
            cagec = c; break
    # part number: a token with a digit and a dash/slash, OR a 6+ char alnum code; not the NSN/CAGEC/SMR
    part = None
    for m in re.finditer(r"\b([0-9A-Z][0-9A-Z\-/]{4,})\b", t):
        tok = m.group(1)
        if (nsn and tok in nsn.group(0)) or tok == cagec or tok == smr or not re.search(r"\d", tok):
            continue
        if re.search(r"[\-/]", tok) or len(tok) >= 6:
            part = tok; break
    if not (nsn or (part and item)):
        return None
    # nomenclature: the longest run of letters/commas (often the trailing description)
    words = re.findall(r"[A-Z][A-Z ,()./\-]{3,}", t.upper())
    nomen = max((w.strip() for w in words), key=len, default="") if words else ""
    return {
        "figure": (fig.group(1) if fig else default_fig),
        "item": (item.group(1) if item else None),
        "smr": smr, "cagec": cagec, "part_number": part,
        "nsn": (nsn.group(1) if nsn else None),
        "qty": (int(qty.group(1)) if qty else None),
        "nomenclature": nomen[:60],
    }


def parse(text, cap=2000):
    """Parse RPSTL text -> {figures grouped by fig, a rows list, count}. Figure carries forward across rows."""
    rows, cur_fig = [], None
    for ln in (text or "").split("\n"):
        f = _FIG.search(ln)
        if f:
            cur_fig = f.group(1)
        r = parse_line(ln, default_fig=cur_fig)
        if r:
            rows.append(r)
        if len(rows) >= cap:
            break
    figs = {}
    for r in rows:
        figs.setdefault(r.get("figure") or "?", []).append(r)
    return {"figures": figs, "rows": rows, "count": len(rows)}


# --------------------------------------------------------------------------- #
# self-test: `python rpstl.py`                                                #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    text = (
        "FIGURE 4. ENGINE MOUNTING\n"
        "ITEM 7  PAOZZ  19207  12420572-010  NSN 5305-01-674-1467  QTY 4  BOLT, MACHINE\n"
        "ITEM 8  PAFZZ  81349  MS35338-46  NSN 5310-00-045-3299  QTY 4  WASHER, LOCK\n"
        "Some prose describing installation that should be ignored entirely.\n"
        "ITEM 9  XBOZZ  19207  12420999  QTY 1  BRACKET, MOUNTING\n")
    p = parse(text)
    assert p["count"] == 3, p["count"]
    r7 = p["rows"][0]
    assert r7["item"] == "7" and r7["nsn"] == "5305-01-674-1467" and r7["qty"] == 4, r7
    assert r7["smr"] == "PAOZZ" and r7["cagec"] == "19207", r7
    assert "BOLT" in (r7["nomenclature"] or ""), r7
    assert r7["figure"] == "4", r7
    print("parse row-7 OK ->", {k: r7[k] for k in ("item", "smr", "cagec", "part_number", "nsn", "qty")})
    assert "4" in p["figures"] and len(p["figures"]["4"]) == 3, p["figures"].keys()
    # a row with no NSN but part+item still parses (item 9)
    assert any(r["item"] == "9" and r["nsn"] is None and r["part_number"] for r in p["rows"]), p["rows"]
    print("parse OK -> %d rows on figure 4" % len(p["figures"]["4"]))
    assert parse_line("This is just a sentence with no part data.") is None
    print("prose-ignored OK")
    print("rpstl self-test PASS")

# END OF FILE
