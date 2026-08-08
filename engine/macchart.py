"""macchart.py -- parse a Maintenance Allocation Chart (MAC) into structured rows (roadmap Vol.2 #56). The
MAC is the central maintenance-planning table in a TM: for each group number / component it lists a
maintenance FUNCTION (inspect, test, service, replace, repair, overhaul, ...), the LEVEL authorized to do it
(C crew / O unit / F field / H sustainment / D depot), the man-hour time, and tool/remark references. This
turns those rows into structured records so the app can answer 'at what level do I replace the water pump,
and how long does it take?'.

R13 discipline: this is EXTRACTIVE. A row is only emitted when it actually contains a recognised MAC function
keyword; the maintenance function is named from the fixed MAC vocabulary; the level, man-hours and references
are best-effort from the same line and are left NULL when the columnar layout can't be read reliably (never
guessed). Every row carries the raw source line so a mechanic can verify it against the TM. Pure regex;
extract_mac() is unit-testable."""

from __future__ import annotations
import re

# The standard MAC maintenance functions (fixed vocabulary) -> canonical label.
_FUNCTIONS = [
    ("inspect", "Inspect"), ("test", "Test"), ("service", "Service"), ("adjust", "Adjust"),
    ("aline", "Aline/Align"), ("align", "Aline/Align"), ("calibrate", "Calibrate"),
    ("remove/install", "Remove/Install"), ("remove and install", "Remove/Install"),
    ("remove", "Remove/Install"), ("install", "Remove/Install"),
    ("replace", "Replace"), ("repair", "Repair"), ("overhaul", "Overhaul"), ("rebuild", "Rebuild"),
]
_FUNC_RX = re.compile(r"\b(remove\s*/\s*install|remove and install|inspect|test|service|adjust|aline|align|"
                      r"calibrate|remove|install|replace|repair|overhaul|rebuild)\b", re.I)

_LEVELS = {"C": "Crew/Operator", "O": "Unit/Organizational", "F": "Field/Direct-Support",
           "H": "General-Support/Sustainment", "D": "Depot"}

_GROUP_RX = re.compile(r"^\s*(\d{2,4})\b")
_TIME_RX = re.compile(r"\b(\d{1,3}\.\d)\b")                 # man-hour time, e.g. 0.3, 12.0
_LEVEL_TOK_RX = re.compile(r"(?<![A-Za-z])([COFHD])(?![A-Za-z])")


def _canon_func(tok):
    t = tok.lower().replace(" ", "")
    for key, label in _FUNCTIONS:
        if t == key.replace(" ", ""):
            return label
    if "remove" in t or "install" in t:
        return "Remove/Install"
    return tok.title()


def parse_row(line, carry_component=""):
    """Parse one line. Returns a MAC-row dict if it carries a maintenance function, else None.
    carry_component is the last seen component name (MAC groups several function rows under one component)."""
    if not line or not line.strip():
        return None
    fm = _FUNC_RX.search(line)
    if not fm:
        return None
    func = _canon_func(fm.group(1))

    gm = _GROUP_RX.match(line)
    group = gm.group(1) if gm else None

    # component = text between the group number and the function keyword (else carry the previous one)
    lead = line[(gm.end() if gm else 0):fm.start()].strip(" .:-\t")
    component = lead if len(lead) >= 2 else (carry_component or None)

    tail = line[fm.end():]
    tm = _TIME_RX.search(tail)
    man_hours = tm.group(1) if tm else None
    lm = _LEVEL_TOK_RX.search(tail)
    level = lm.group(1) if lm else None

    return {
        "group": group,
        "component": component,
        "function": func,
        "level": level,
        "level_name": _LEVELS.get(level) if level else None,
        "man_hours": man_hours,
        "raw": line.strip(),
        "basis": "extracted from the TM MAC line (verify against the chart)",
    }


def extract_mac(text, cap=200):
    """Parse MAC rows from text -> list of parse_row() dicts. Carries the component name down function rows."""
    rows, carry = [], ""
    for ln in (text or "").split("\n"):
        r = parse_row(ln, carry)
        if r:
            if r["component"]:
                carry = r["component"]
            rows.append(r)
            if len(rows) >= cap:
                break
    return rows


def for_component(text, name):
    """All MAC rows whose component matches (case-insensitive substring) -> quick 'how do I service X' view."""
    n = (name or "").strip().lower()
    if not n:
        return []
    return [r for r in extract_mac(text) if r["component"] and n in r["component"].lower()]


# --------------------------------------------------------------------------- #
# self-test: `python macchart.py`                                             #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    mac = ("0601  Water Pump  Inspect  0.2  C\n"
           "               Replace  1.5  F\n"
           "               Repair   3.0  H\n"
           "0602  Fan Belt  Replace  0.5  O\n"
           "This is just prose, not a MAC row at all.\n")
    rows = extract_mac(mac)
    assert len(rows) == 4, rows
    r0 = rows[0]
    assert r0["group"] == "0601" and r0["component"] == "Water Pump" and r0["function"] == "Inspect", r0
    assert r0["level"] == "C" and r0["level_name"].startswith("Crew") and r0["man_hours"] == "0.2", r0
    print("row0 OK -> %s / %s @ %s (%s) %s hr" % (r0["group"], r0["component"], r0["level"], r0["level_name"], r0["man_hours"]))

    # component carries down to the Replace/Repair rows that have no group/name of their own
    assert rows[1]["component"] == "Water Pump" and rows[1]["function"] == "Replace" and rows[1]["level"] == "F", rows[1]
    assert rows[2]["function"] == "Repair" and rows[2]["level"] == "H", rows[2]
    print("carry-down OK -> Replace@F, Repair@H under Water Pump")

    assert rows[3]["group"] == "0602" and rows[3]["component"] == "Fan Belt" and rows[3]["function"] == "Replace", rows[3]
    print("row3 OK -> %s / %s" % (rows[3]["group"], rows[3]["component"]))

    # a row with a function but unreadable level/time -> null, not guessed
    one = parse_row("0603  Alternator  Overhaul")
    assert one["function"] == "Overhaul" and one["level"] is None and one["man_hours"] is None, one
    print("R13 OK -> unreadable level/time left NULL (not guessed)")

    # prose without a function keyword is not a MAC row
    assert parse_row("Torque the bolts to 30 ft-lb in sequence.") is None
    print("non-MAC prose ignored OK")

    fc = for_component(mac, "water pump")
    assert len(fc) == 3 and {r["function"] for r in fc} == {"Inspect", "Replace", "Repair"}, fc
    print("for_component('water pump') OK -> %d functions" % len(fc))
    print("macchart self-test PASS")

# END OF FILE
