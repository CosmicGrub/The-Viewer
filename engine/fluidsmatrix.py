"""fluidsmatrix.py -- per-system FLUIDS & CAPACITIES matrix (roadmap #51, readiness). A mechanic servicing a
vehicle needs one table: which fluid goes where, to what spec, and how much. Manuals scatter this across the
LO and servicing sections. This pulls it into {system -> fluid, spec, capacity} so the app can show a clean
fluids matrix and feed the kit/BOM. Pure and unit-testable. Read-only."""

from __future__ import annotations
import re

_SYSTEMS = [
    ("engine oil", "engine"), ("crankcase", "engine"), ("engine", "engine"),
    ("transmission", "transmission"), ("transfer case", "transfer"), ("transfer", "transfer"),
    ("differential", "differential"), ("axle", "differential"),
    ("cooling system", "cooling"), ("coolant", "cooling"), ("radiator", "cooling"),
    ("brake", "brake"), ("hydraulic", "hydraulic"), ("power steering", "power-steering"),
    ("fuel tank", "fuel"), ("fuel", "fuel"),
]
# fluid specs / types (MIL-spec + common designations)
_FLUID = re.compile(r"\b(MIL-[A-Z]+-\d+[A-Z0-9/\-]*|OE[AW]?/?H?D?O?|OEA|HDO|GAA|GO\s*\d+|DEXRON[\s-]?[IVX]*|"
                    r"\d+W-\d+|SAE\s*\d+[W]?(?:-\d+)?|BFS|GAA|ANTIFREEZE|ETHYLENE\s+GLYCOL|DOT\s*[3-5])\b", re.I)
# v1.13.4: the bare "l" (liter) alternative used to allow zero whitespace before it, so an RPSTL item-
# number Left/Right suffix like "12L" parsed as "12 liters" -- and since search() returns the LEFTMOST
# match in the scan window, a real capacity later in the same text ("2.5 pints") was never reached.
# Requiring a space before the bare-letter form (only "l" -- the word-form units below aren't ambiguous
# with a fused item-number suffix the same way) closes that without touching genuinely space-separated
# capacities, which is how they overwhelmingly appear in TM prose.
_CAP = re.compile(r"(\d+(?:\.\d+)?)(?:\s*(quarts?|qts?|gallons?|gal|liters?|litres?|pints?|pt|ounces?|oz)|"
                  r"\s+(l))\b", re.I)
_UNITMAP = {"quart": "qt", "quarts": "qt", "qt": "qt", "qts": "qt", "gallon": "gal", "gallons": "gal",
            "gal": "gal", "liter": "L", "liters": "L", "litre": "L", "litres": "L", "l": "L",
            "pint": "pt", "pints": "pt", "pt": "pt", "ounce": "oz", "ounces": "oz", "oz": "oz"}


def _norm_unit(u):
    return _UNITMAP.get(u.lower(), u.lower())


def extract_fluids(text, cap=30):
    """-> [{system, fluid, capacity, unit, context}] (one per system, best-effort). Scans for a system
    keyword and grabs the nearest fluid spec + capacity in its vicinity."""
    if not text:
        return []
    t = re.sub(r"\s+", " ", text)
    tl = t.lower()
    found, seen = [], set()
    for phrase, system in _SYSTEMS:
        if system in seen:
            continue
        # v1.13.4: try EVERY occurrence of the phrase, not just the first. Previously the system was
        # marked "seen" (permanently skipped) the moment its first literal occurrence was found, even
        # if that occurrence had no fluid/capacity nearby -- an earlier unrelated mention (a section
        # heading, an inspection paragraph) permanently blocked a real LO/servicing entry located later
        # in the exact same document, with the system's data silently dropped and no error raised.
        entry = None
        start = 0
        while True:
            idx = tl.find(phrase, start)
            if idx < 0:
                break
            window = t[idx: idx + 110]              # look FORWARD from the system name (fluid/qty follow it)
            fm = _FLUID.search(window)
            cm = _CAP.search(window)
            if fm or cm:
                cap_unit = (cm.group(2) or cm.group(3)) if cm else None   # group 2 = word-form, 3 = bare "l"
                entry = {"system": system, "fluid": (fm.group(1).upper() if fm else None),
                         "capacity": (float(cm.group(1)) if cm else None),
                         "unit": (_norm_unit(cap_unit) if cap_unit else None),
                         "context": window.strip()}
                break
            start = idx + len(phrase)
        seen.add(system)
        if entry:
            found.append(entry)
        if len(found) >= cap:
            break
    return found


def matrix(text):
    """A tidy {system: {fluid, capacity, unit}} dict for display."""
    return {e["system"]: {"fluid": e["fluid"], "capacity": e["capacity"], "unit": e["unit"]}
            for e in extract_fluids(text)}


# --------------------------------------------------------------------------- #
# self-test: `python fluidsmatrix.py`                                         #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    text = ("SERVICING. Engine oil: use OE/HDO 15W-40, capacity 6 quarts. Cooling system coolant "
            "(ethylene glycol antifreeze) capacity 20 quarts. Transmission fluid DEXRON III, 8 qt. "
            "Brake system uses MIL-PRF-46176 fluid. Differential GO 80/90, 2.5 pints.")
    fl = extract_fluids(text)
    by = {e["system"]: e for e in fl}
    assert by["engine"]["capacity"] == 6.0 and by["engine"]["unit"] == "qt", by.get("engine")
    assert by["cooling"]["capacity"] == 20.0, by.get("cooling")
    assert by["transmission"]["fluid"] and "DEXRON" in by["transmission"]["fluid"], by.get("transmission")
    assert by["brake"]["fluid"] and "MIL-PRF" in by["brake"]["fluid"], by.get("brake")
    assert by["differential"]["capacity"] == 2.5 and by["differential"]["unit"] == "pt", by.get("differential")
    print("extract_fluids OK -> %d systems: %s" % (len(fl), sorted(by)))
    m = matrix(text)
    assert m["engine"]["fluid"].startswith("OE") and m["engine"]["capacity"] == 6.0, m["engine"]
    print("matrix OK -> engine=%s %s%s" % (m["engine"]["fluid"], m["engine"]["capacity"], m["engine"]["unit"]))
    print("fluidsmatrix self-test PASS")

# END OF FILE
