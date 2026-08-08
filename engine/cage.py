"""cage.py -- validate and structurally classify a CAGE / NCAGE code (roadmap Vol.2 #54). A CAGE
(Commercial and Government Entity) code is the 5-character identifier of the manufacturer or supplier of a
part; it appears throughout an RPSTL next to each part number. This module checks a code against the
published structural rules and says whether it looks like a domestic (US) CAGE or an NCAGE (NATO/foreign-
assigned) code. It deliberately does NOT return the company name -- that identity lives in PUBLOG's CAGE
table (build_publog loads CAGE status); the route may join it, but the pure module never invents a name.

R13 discipline: we assert only what the format rules guarantee (length, allowed characters, the no-I/O rule,
and the position-1/5 numeric rule for domestic CAGE). Anything outside those rules is reported as a reason,
not silently accepted, and we never fabricate an assignee. validate() is pure and unit-testable."""

from __future__ import annotations
import re

# The letters I and O are never used in a CAGE code (they are excluded to avoid confusion with 1 and 0).
_EXCLUDED = set("IO")
_ALNUM = re.compile(r"^[A-Z0-9]{5}$")
_LABELLED = re.compile(r"\bCAGEC?\b[:\s#]*([A-Z0-9]{5})\b", re.I)


def validate(code) -> dict:
    """Validate a CAGE code. Returns {code, normalized, valid, kind, reasons, excludes_io}.
    kind is 'US' (domestic), 'NCAGE' (NATO/foreign-assigned, alpha first position), or 'unknown'.
    reasons lists every rule the token fails (empty when valid). Never returns a company name."""
    raw = code or ""
    c = raw.strip().upper()
    reasons = []
    if len(c) != 5:
        reasons.append("must be exactly 5 characters (got %d)" % len(c))
    if not _ALNUM.match(c):
        reasons.append("must be alphanumeric A-Z/0-9 only")
    io = sorted(set(c) & _EXCLUDED)
    if io:
        reasons.append("contains excluded letter(s) %s (I and O are never used)" % "/".join(io))

    kind = "unknown"
    if not reasons:
        first_num, last_num = c[0].isdigit(), c[4].isdigit()
        if first_num and last_num:
            kind = "US"                                   # domestic CAGE: 1st and 5th are numeric
        elif c[0].isalpha():
            kind = "NCAGE"                                # NATO/foreign-assigned codes may begin with a letter
        else:
            # 1st numeric but 5th alpha (or vice-versa without alpha-lead) -> valid characters, atypical shape
            kind = "unknown"
            reasons.append("valid characters but not the domestic 1st/5th-numeric shape; verify as NCAGE")

    return {
        "code": raw,
        "normalized": c,
        "valid": len(reasons) == 0,
        "kind": kind,
        "reasons": reasons,
        "excludes_io": len(io) == 0,
    }


def is_valid(code) -> bool:
    return validate(code)["valid"]


def scan(text, cap=60):
    """Find CAGE codes that are explicitly LABELLED in text (CAGE: XXXXX / CAGEC 12345) and validate them.
    Requiring the label avoids matching arbitrary 5-character part-number fragments. Deduped."""
    out, seen = [], set()
    for m in _LABELLED.finditer(text or ""):
        tok = m.group(1).upper()
        if tok in seen:
            continue
        seen.add(tok)
        v = validate(tok)
        out.append(v)
        if len(out) >= cap:
            break
    return out


# --------------------------------------------------------------------------- #
# self-test: `python cage.py`                                                 #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    v = validate("19207")                                 # a real, well-known US Army CAGE shape (1st/5th numeric)
    assert v["valid"] and v["kind"] == "US" and not v["reasons"], v
    print("validate 19207 OK -> kind=%s" % v["kind"])

    v2 = validate("0VGN7")                                # 1st numeric, 5th numeric? no, 5th is '7' numeric; alpha inside
    assert v2["valid"] and v2["kind"] == "US", v2
    print("validate 0VGN7 OK -> kind=%s" % v2["kind"])

    # excluded letters I / O rejected
    vio = validate("1IO34")
    assert not vio["valid"] and any("excluded" in r for r in vio["reasons"]), vio
    print("reject I/O OK ->", vio["reasons"][0][:44])

    # wrong length rejected
    assert not validate("1234")["valid"] and not validate("123456")["valid"]
    # non-alphanumeric rejected
    assert not validate("12-34")["valid"]

    # NCAGE-style (alpha first char) classified, not fabricated
    vn = validate("U1234")
    assert vn["valid"] and vn["kind"] == "NCAGE", vn
    print("classify NCAGE U1234 OK -> kind=%s (no company name invented)" % vn["kind"])

    # labelled scan pulls only the tagged codes
    found = scan("Part 12345678 from CAGE 19207; alt CAGEC: 0VGN7. Random ABCDE not tagged.")
    got = {x["normalized"] for x in found}
    assert got == {"19207", "0VGN7"}, got
    print("scan OK -> %d labelled CAGE codes (%s)" % (len(found), ", ".join(sorted(got))))
    print("cage self-test PASS")

# END OF FILE
