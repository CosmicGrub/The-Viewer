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
_CAP = re.compile(r"(\d+(?:\.\d+)?)\s*(quarts?|qts?|gallons?|gal|liters?|litres?|l|pints?|pt|ounces?|oz)\b", re.I)
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
        idx = tl.find(phrase)
        if idx < 0 or system in seen:
            continue
        seen.add(system)
        window = t[idx: idx + 110]                 # look FORWARD from the system name (fluid/qty follow it)
        fm = _FLUID.search(window)
        cm = _CAP.search(window)
        entry = {"system": system, "fluid": (fm.group(1).upper() if fm else None),
                 "capacity": (float(cm.group(1)) if cm else None),
                 "unit": (_norm_unit(cm.group(2)) if cm else None),
                 "context": window.strip()}
        if entry["fluid"] or entry["capacity"]:
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
