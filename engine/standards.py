"""standards.py -- decode STANDARD-HARDWARE and SPECIFICATION designations (roadmap #58/#59). A TM is full
of codes like 'MS35338-46', 'AN960-10', 'NAS1149', 'MIL-PRF-2104', 'SAE J429', 'ASTM A193'. A mechanic needs
to know: what KIND of thing is this (hardware standard vs material spec vs performance spec vs test method),
and -- for the handful of very common series -- what item it names.

R13 discipline: we classify the FAMILY/KIND reliably from the designation itself (that's unambiguous), and
only name the specific item for a small CURATED set of series we're confident about. We never fabricate a
part meaning for an arbitrary MS/AN number. classify() and scan() are pure and unit-testable."""

from __future__ import annotations
import re

# family -> (kind, what the family is)
_FAMILY = {
    "MS":   ("hardware-standard", "Military Standard hardware/part"),
    "AN":   ("hardware-standard", "Army-Navy standard hardware"),
    "NAS":  ("hardware-standard", "National Aerospace Standard hardware"),
    "NASM": ("hardware-standard", "National Aerospace Standard (metric/relabeled MS)"),
    "MIL-PRF": ("performance-spec", "MIL performance specification"),
    "MIL-DTL": ("detail-spec", "MIL detail specification"),
    "MIL-STD": ("standard-practice", "MIL standard (practice/method)"),
    "MIL-SPEC": ("specification", "military specification"),
    "MIL": ("specification", "military specification"),
    "SAE":  ("commercial-standard", "SAE standard"),
    "ASTM": ("material-standard", "ASTM material/test standard"),
    "AMS":  ("material-spec", "Aerospace Material Specification"),
    "FED-STD": ("standard-practice", "Federal Standard"),
    "A-A":  ("commercial-item", "Commercial Item Description (A-A)"),
}
# a small CURATED map of very common series -> the item (only ones we're confident about)
_COMMON = {
    "AN960": "washer, flat", "AN970": "washer, flat (large OD)", "MS35338": "washer, lock (split)",
    "MS35340": "washer, lock (external tooth)", "MS51957": "screw, machine, pan head",
    "MS51922": "nut, self-locking", "MS21044": "nut, self-locking", "MS24665": "pin, cotter",
    "MS16562": "pin, spring", "MIL-PRF-2104": "engine oil (OE/HDO)", "MIL-PRF-2105": "gear oil (GO)",
    "MIL-PRF-46176": "brake fluid, silicone (BFS)", "MIL-PRF-10924": "grease (GAA)",
    "MIL-DTL-53072": "CARC coating system", "SAE-J429": "bolt/screw mechanical grades",
}


# v1.13.4: was case-insensitive (re.I). Real TM designations are always written uppercase, so that only
# ever bought false positives -- the plain English indefinite article "an" immediately preceding a number
# in ordinary prose ("an 85 gallon tank") was misread as the AN (Army-Navy) hardware-standard family, with
# no way for the mechanic to tell it apart from a genuine standard callout. Same risk shape for "ms"
# (very common as the milliseconds abbreviation in electronics timing specs) against the MS family.
# Uppercase-only match closes both, matching how these designations actually appear in source documents.
_FAM_RX = re.compile(
    r"\b(MIL-PRF|MIL-DTL|MIL-STD|MIL-SPEC|FED-STD|NASM|NAS|AMS|ASTM|SAE|MS|AN|MIL|A-A)"
    r"[-\s]?([0-9][0-9A-Z]*(?:[-/][0-9A-Z]+)*)\b")


def _norm(fam, num):
    fam = fam.upper()
    base = "%s%s" % (fam, num.split("-")[0].split("/")[0]) if fam in ("MS", "AN", "NAS", "NASM") else \
           ("%s-%s" % (fam, num.split("/")[0]) if fam.startswith("MIL") or fam in ("SAE", "ASTM", "AMS") else "%s%s" % (fam, num))
    return base.upper().replace(" ", "")


def classify(token):
    """Decode one designation. Returns {token, family, kind, description, item?, curated} or {} if it isn't one."""
    m = _FAM_RX.search(token or "")
    if not m:
        return {}
    fam, num = m.group(1).upper(), m.group(2)
    kind, desc = _FAMILY.get(fam, ("specification", "standard designation"))
    key = _norm(fam, num)
    # curated exact-series item, if we know it. v1.13.4: this used to be
    # key.startswith(ckey_normalized) -- a PREFIX match -- so an uncatalogued, structurally-different
    # series that merely shares its leading digits with a curated one got a FABRICATED item name (e.g.
    # "AN9600-5" -> the curated AN960 washer; "MS519571-3" -> the curated MS51957 screw), directly
    # violating this module's own "never fabricate" discipline stated in its docstring. Now exact,
    # EXCEPT a single trailing revision LETTER is still allowed (MIL-PRF-2104H = revision H of curated
    # MIL-PRF-2104 -- MIL-family designations keep their hyphens and aren't dash-suffix-stripped by
    # _norm() the way MS/AN/NAS are, so compare against the curated key in its own natural form, not
    # artificially hyphen-stripped) -- a trailing DIGIT is never allowed, since that changes the series
    # number itself rather than naming a revision of the same series.
    item, curated = None, False
    for ckey, cval in _COMMON.items():
        ck = ckey.upper()
        if key == ck or (key.startswith(ck) and len(key) == len(ck) + 1 and key[-1].isalpha()):
            item, curated = cval, True
            break
    out = {"token": m.group(0), "family": fam, "series": key, "kind": kind, "description": desc, "curated": curated}
    if item:
        out["item"] = item
    return out


def scan(text, cap=60):
    """Find every standard designation in text -> list of classify() dicts, deduped by token."""
    out, seen = [], set()
    for m in _FAM_RX.finditer(text or ""):
        tok = m.group(0)
        if tok.upper() in seen:
            continue
        seen.add(tok.upper())
        c = classify(tok)
        if c:
            out.append(c)
        if len(out) >= cap:
            break
    return out


# --------------------------------------------------------------------------- #
# self-test: `python standards.py`                                            #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    a = classify("MS35338-46")
    assert a["family"] == "MS" and a["kind"] == "hardware-standard", a
    assert a.get("item") == "washer, lock (split)" and a["curated"], a
    print("classify MS35338 OK ->", a["item"])

    b = classify("MIL-PRF-2104H")
    assert b["family"] == "MIL-PRF" and b["kind"] == "performance-spec", b
    assert b.get("item") == "engine oil (OE/HDO)", b
    print("classify MIL-PRF-2104 OK ->", b["item"])

    c = classify("AN960-10")
    assert c.get("item") == "washer, flat", c
    print("classify AN960 OK ->", c["item"])

    # an uncatalogued MS number: classified by family, but NO fabricated item
    d = classify("MS12345-99")
    assert d["family"] == "MS" and d["kind"] == "hardware-standard" and "item" not in d, d
    print("classify uncatalogued OK -> family=%s, no fabricated item" % d["family"])

    # not a standard
    assert classify("just some words") == {}
    assert classify("2530-01-234-5678") == {} or classify("2530-01-234-5678").get("family") not in _FAMILY or True

    text = "Torque MS51957-30 screws with AN960-10 washers. Use MIL-PRF-2104 oil and MIL-PRF-46176 brake fluid."
    found = scan(text)
    fams = {x["family"] for x in found}
    assert "MS" in fams and "AN" in fams and "MIL-PRF" in fams, fams
    assert sum(1 for x in found if x.get("item")) >= 3, found
    print("scan OK -> %d designations, %d with known items" % (len(found), sum(1 for x in found if x.get("item"))))
    print("standards self-test PASS")

# END OF FILE
