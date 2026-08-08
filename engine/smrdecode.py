"""smrdecode.py -- decode a Source, Maintenance, and Recoverability (SMR) code (roadmap Vol.2 #53). Every
RPSTL / repair-parts line carries a 5-character SMR code such as PAOZZ. It tells a mechanic four things at a
glance: how the item is sourced, the level authorized to remove/replace it, the level authorized to fully
repair it, and what to do with it when it fails (discard vs. send back for overhaul). This decoder splits the
code into its four fields and names each field from the published SMR code tables (AR 700-82 / TM RPSTL
convention).

R13 discipline: the split is deterministic; each field is named from a CURATED table of the standard codes.
For a code we don't carry we return the raw letters with a null meaning -- never an invented interpretation,
because a mechanic acting on a mis-decoded SMR could scrap a repairable part or vice-versa. decode() is pure
and unit-testable."""

from __future__ import annotations
import re

# Source code (positions 1-2) -- how the item is obtained. Curated standard set.
_SOURCE = {
    "PA": "Procured and stocked; stocked item, replace at the indicated maintenance level",
    "PB": "Procured and stocked; may be requisitioned",
    "PC": "Procured and stocked (deteriorative item)",
    "PD": "Support item; procured and stocked for initial issue/outfitting",
    "PE": "Procured and stocked (limited/special application)",
    "PF": "Procured and stocked (special tools / test equipment)",
    "PG": "Procured and stocked (major end-item component)",
    "PZ": "Procured and stocked (item nonreparable, discard on failure)",
    "KD": "Component of a repair kit; stocked in the kit at depot level",
    "KF": "Component of a repair kit; stocked in the kit at field level",
    "KB": "Component of a repair kit; stocked in the kit at both field and depot",
    "MO": "Manufactured or fabricated at unit / organizational level",
    "MF": "Manufactured or fabricated at field / direct-support level",
    "MH": "Manufactured or fabricated at general-support / sustainment level",
    "ML": "Manufactured or fabricated at a specialized repair activity (SRA)",
    "MD": "Manufactured or fabricated at depot level",
    "AO": "Assembled at unit / organizational level",
    "AF": "Assembled at field / direct-support level",
    "AH": "Assembled at general-support / sustainment level",
    "AL": "Assembled at a specialized repair activity (SRA)",
    "AD": "Assembled at depot level",
    "XA": "Not stocked; order the next higher assembly",
    "XB": "Not stocked; if not available, cannibalize or fabricate",
    "XC": "Not stocked; an installation drawing / diagram / instruction number is used",
    "XD": "Not stocked; obtain through normal supply channels",
}

# Maintenance level (positions 3 = USE, 4 = REPAIR) -- lowest level authorized. Shared table.
_LEVEL = {
    "C": "Operator / Crew",
    "O": "Unit / Organizational maintenance",
    "F": "Field / Direct-Support maintenance",
    "H": "General-Support / Sustainment (below depot)",
    "L": "Specialized Repair Activity (SRA)",
    "D": "Depot",
    "G": "General-Support (SRA located at general support)",
    "Z": "No maintenance authorized at any level (nonreparable)",
    "B": "No repair and no replacement authorized — see the next higher assembly",
}

# Recoverability (position 5) -- disposition when the item is unserviceable.
_RECOVER = {
    "Z": "Nonreparable; discard at the level shown in the repair (4th) position",
    "O": "Reparable; condemn and dispose at unit / organizational level",
    "F": "Reparable; condemn and dispose at field / direct-support level",
    "H": "Reparable; condemn and dispose at general-support level",
    "D": "Reparable; condemn and dispose at depot level",
    "L": "Reparable; condemn and dispose at a specialized repair activity (SRA)",
    "A": "Controlled item requiring special handling; recover / return to depot",
}

_SMR_RX = re.compile(r"\b([A-KM-Z]{2}[A-Z]{3})\b")   # 5 uppercase letters (I excluded from source alpha set)


def decode(code) -> dict:
    """Decode a 5-char SMR code. Returns {code, valid, source, source_meaning, use_level, use_meaning,
    repair_level, repair_meaning, recover, recover_meaning}. Unknown fields carry a null meaning (never
    fabricated). {'valid': False} for a non-SMR token."""
    c = (code or "").strip().upper()
    if not re.fullmatch(r"[A-Z]{5}", c):
        return {"code": code, "valid": False}
    src, use, rep, rec = c[:2], c[2], c[3], c[4]
    return {
        "code": c,
        "valid": True,
        "source": src, "source_meaning": _SOURCE.get(src),
        "use_level": use, "use_meaning": _LEVEL.get(use),
        "repair_level": rep, "repair_meaning": _LEVEL.get(rep),
        "recover": rec, "recover_meaning": _RECOVER.get(rec),
    }


def summary(code) -> str:
    """One-line plain-language gloss, or '' if not a valid SMR code. Only names fields we carry."""
    d = decode(code)
    if not d["valid"]:
        return ""
    parts = []
    if d["source_meaning"]:
        parts.append(d["source_meaning"].split(";")[0])
    if d["use_meaning"]:
        parts.append("R&R at %s" % d["use_meaning"])
    if d["repair_meaning"]:
        parts.append("repair at %s" % d["repair_meaning"])
    if d["recover_meaning"]:
        parts.append(d["recover_meaning"].split(";")[0])
    return " | ".join(parts)


def scan(text, cap=40):
    """Find candidate SMR codes in text -> list of decode() dicts we can actually name (source known),
    deduped. Requires a known source code so we don't misread arbitrary 5-letter words."""
    out, seen = [], set()
    for m in _SMR_RX.finditer((text or "").upper()):
        c = m.group(1)
        if c in seen or c[:2] not in _SOURCE:
            continue
        seen.add(c)
        out.append(decode(c))
        if len(out) >= cap:
            break
    return out


# --------------------------------------------------------------------------- #
# self-test: `python smrdecode.py`                                            #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    d = decode("PAOZZ")
    assert d["valid"] and d["source"] == "PA" and d["use_level"] == "O" and d["repair_level"] == "Z" and d["recover"] == "Z", d
    assert d["source_meaning"].startswith("Procured and stocked"), d
    assert d["use_meaning"].startswith("Unit"), d
    assert d["repair_meaning"].startswith("No maintenance"), d
    assert d["recover_meaning"].startswith("Nonreparable"), d
    print("decode PAOZZ OK ->", summary("PAOZZ")[:70])

    d2 = decode("PAFDD")
    assert d2["repair_level"] == "D" and d2["repair_meaning"] == "Depot", d2
    assert d2["recover"] == "D" and d2["recover_meaning"].startswith("Reparable"), d2
    print("decode PAFDD OK ->", "repair @ %s, %s" % (d2["repair_meaning"], d2["recover_meaning"][:24]))

    d3 = decode("XBFZZ")
    assert d3["source_meaning"].startswith("Not stocked; if not available"), d3
    print("decode XBFZZ OK -> cannibalize/fabricate source")

    # unknown source pair -> code returned, meaning None (never fabricated)
    d4 = decode("QQOZZ")
    assert d4["valid"] and d4["source"] == "QQ" and d4["source_meaning"] is None, "must not fabricate a source meaning"
    print("R13 OK -> unknown source QQ returns null meaning (no fabrication)")

    assert decode("PAO")["valid"] is False and decode("hello world")["valid"] is False
    found = scan("Filter is PAOZZ; bracket XBFZZ; the word HELLO is not a code.")
    assert len(found) == 2, found
    print("scan OK -> %d real SMR codes (ignored HELLO)" % len(found))
    print("smrdecode self-test PASS")

# END OF FILE
