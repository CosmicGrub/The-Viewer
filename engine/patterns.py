#!/usr/bin/env python3
"""THE VIEWER -- shared text patterns (NSN / FIG / part-number) + helpers.

Single source of truth so search, page callouts, threed_refs, and the dossier all extract identically.
Today these regexes are copied in a few places in viewer_app.py; the modularization (#36) will switch
those call sites to `from patterns import ...`. Stdlib-only, RPS-safe.
"""
import re

# National Stock Number: FSC(4)-NCB(2)-(3)-(4); the dashes are optional in real text.
# \b-anchored on both ends -- without it, this "canonical" NSN pattern (imported as the single
# source of truth by render_feature.py/procedure_feature.py, which finditer() it over raw page/
# procedure text) happily grabs the first 13 digits out of any longer contiguous digit run and
# misreads it as an NSN: an invoice number, tracking number, or PO number. Every other NSN regex
# in this codebase (viewer_ingest.py, ocr_report.py, nsndecode.py, xref_feature.py,
# rpstl_feature.py) is already \b-anchored -- this was the one straggler.
NSN_RE = re.compile(r"\b(\d{4})-?(\d{2})-?(\d{3})-?(\d{4})\b")
# Figure reference: "FIG 5", "FIGURE 12-3", "FIG. 4".
FIG_RE = re.compile(r"\bFIG(?:URE)?\.?\s*([0-9]+(?:-[0-9]+)?)", re.I)
# Labeled part number: "P/N: MS35338-44", "PART NO. 12345-AB".
PN_RE = re.compile(r"\b(?:P/N|PART\s*N[O0]\.?|PART\s*NUMBER)\.?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-]{3,16})", re.I)

def digits(s):
    """Just the digits of a string (for NSN dedup across dashed / bare forms)."""
    return re.sub(r"\D", "", s or "")

def norm_nsn(s):
    """Canonical dashed NSN ('2540-01-123-4567') from any form, or None."""
    m = NSN_RE.search((s or "").strip())
    return ("%s-%s-%s-%s" % (m.group(1), m.group(2), m.group(3), m.group(4))) if m else None

def niin_of(s):
    """Canonical NIIN (digits 5-13 of the NSN) from ANY NSN/NIIN string -- THE one implementation
    (v1.13). Rules (R13: never guess):
      * 13 digits (full NSN, dashed or bare)  -> digits[4:13] (the NIIN; FSC is digits[0:4])
      * 9 digits (bare NIIN)                  -> as-is
      * 10-12 digits, <9 digits, >13 digits   -> '' (ambiguous fragment; REFUSED, not zero-padded
        or truncated -- a fabricated key silently returns the WRONG part)
    publog.norm_niin / publogdiff._niin / xref_feature._niin / build_publog._niin all delegate here."""
    d = re.sub(r"\D", "", s or "")
    if len(d) == 13:
        return d[4:13]
    if len(d) == 9:
        return d
    return ""

def nsn_fts_phrase(nsn):
    """FTS5 phrase of an NSN's number groups ('"2540 01 123 4567"') so it matches the dashed form in the
    text regardless of how the tokenizer split the hyphens."""
    m = NSN_RE.search(nsn or "")
    return ('"%s %s %s %s"' % (m.group(1), m.group(2), m.group(3), m.group(4))) if m else None

# ---- "Side of the house": operator (10-level) vs mechanic (20-level) -------------------------------
# Authoritative basis: the Army TM "indicator of coverage" -- the level field after the equipment
# designator (e.g. TM 9-2320-280-*XX*). Per Army Publishing Directorate + the standard TM-numbering spec:
#   10            Operator's manual                         -> OPERATOR
#   12 13 14 15   Operator + maintenance (combined)         -> BOTH (operator chapters AND maintenance)
#   20 23 24 25   Unit/field maintenance                    -> MECHANIC
#   30 34 35 40   Direct/General Support maintenance        -> MECHANIC
#   *P / *&P      Repair Parts & Special Tools List (RPSTL) -> MECHANIC (parts)
#   LO            Lubrication Order                          -> MECHANIC (servicing)
# Combined manuals deliberately land on BOTH sides (a -12 is genuinely an operator book too).
# Sources: armypubs.army.mil TM product maps; radionerds.com TM Numbering Specification (coverage table).

# the level/coverage field: 1-3 digits, optionally followed by P or &P, bounded by start/dash/space/end
_COVER_RE = re.compile(r"(?:^|[-\s])(\d{2,3})(&?P)?(?=$|[-\s&])", re.I)
_LO_RE = re.compile(r"\bLO\b|\bLUBRICATION\s+ORDER\b", re.I)
_OPER_TXT = re.compile(r"\bOPERATOR(?:'?S)?\b", re.I)
_MAINT_TXT = re.compile(r"\b(MAINTENANCE|UNIT|ORGANIZATIONAL|DIRECT\s+SUPPORT|GENERAL\s+SUPPORT|RPSTL|REPAIR\s+PARTS)\b", re.I)

def _coverage_codes(blob):
    """All 2-3 digit coverage indicators found in a TM-number-bearing string (e.g. '10','20','24','13')."""
    return [m.group(1) for m in _COVER_RE.finditer(blob or "")]

def tm_side(tm_number, title="", path=""):
    """Classify a document to the operator (10) and/or mechanic (20) side of the house.
    Returns {operator: bool, mechanic: bool, coverage: <best code or ''>, basis: <reason>, confidence: <h/m/l>}.
    Deterministic from the TM coverage indicator (confidence='high'); falls back to title/path wording
    ('medium') only when no code is present; if nothing is determinable it defaults to mechanic ('low')."""
    blob = " ".join(x for x in (tm_number or "", title or "", path or "") if x)
    codes = _coverage_codes(tm_number or "") or _coverage_codes(blob)
    operator = mechanic = False
    coverage = ""; reasons = []; confidence = "low"
    # The coverage indicator is the TRAILING 2-digit field (TM C-CCCC-DDD-LL[&P]); earlier 2-digit
    # fields are the commodity/category (e.g. the '11' in 'TM 11-...') and must NOT be read as a level.
    two_digit = [c for c in codes if len(c) == 2 and c[0] in "1234"]
    if two_digit:
        c = two_digit[-1]
        if c[0] == "1":
            operator = True
            if c != "10": mechanic = True            # 12/13/14/15 are combined -> also mechanic
        else:                                         # 20/23/24/25/30/34/35/40
            mechanic = True
        coverage = c
        reasons.append("coverage %s" % c); confidence = "high"
    # parts list (RPSTL): "...P" or "...&P" -> mechanic
    if re.search(r"\d(?:&?P)\b", tm_number or "", re.I) or re.search(r"\bRPSTL\b", blob, re.I):
        mechanic = True; reasons.append("parts/RPSTL")
        coverage = coverage or "P"; confidence = "high"
    # Lubrication Order -> mechanic (servicing)
    if _LO_RE.search(tm_number or "") or _LO_RE.search(blob):
        mechanic = True; reasons.append("lubrication order")
        coverage = coverage or "LO"; confidence = "high"
    # fallback to wording only if the number gave us nothing
    if not operator and not mechanic:
        if _OPER_TXT.search(blob): operator = True; reasons.append("title: operator"); confidence = "medium"
        if _MAINT_TXT.search(blob): mechanic = True; reasons.append("title: maintenance"); confidence = "medium"
    if not operator and not mechanic:                 # truly unknown -> show to mechanics (fuller set) but flag
        mechanic = True; reasons.append("undetermined (defaulted to mechanic)"); confidence = "low"
    return {"operator": operator, "mechanic": mechanic, "coverage": coverage,
            "basis": ", ".join(reasons) or "n/a", "confidence": confidence}
