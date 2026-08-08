#!/usr/bin/env python3
"""THE VIEWER -- UNIT NORMALIZATION (v1.1.7). Pure, dependency-free conversions so every measured value can be shown in
BOTH measurement systems (a mechanic gets `180 in (4572 mm)` / `30 ft-lb (40.7 N-m)` without reaching for a calculator).
Used at READ time by the Masterfile (masterfile.for_subject) and the /measures & dossier views -- no rebuild, no schema
change. Never mutates the stored value; it only adds an `alt` display string. Corpus stays authoritative.

canonical units match measures.py: length in/ft/yd/mm/cm/m/mil · torque ft-lb/in-lb/N-m · pressure psi/kPa/MPa/bar/inHg ·
capacity gal/qt/pt/fl-oz/L/mL · weight lb/oz/kg/g/ton · force lbf/N/kN · temperature degF/degC · speed mph/km/h ·
flow gpm/cfm · area sq-in/sq-ft."""

# factor to a per-type BASE unit, and the preferred "other-system" partner for display.
# base: length->mm, torque->N-m, pressure->kPa, capacity->L, weight->kg, force->N, speed->km/h, flow->L/min, area->sq-cm
_TO_BASE = {
    # length -> mm
    "in": 25.4, "ft": 304.8, "yd": 914.4, "mm": 1.0, "cm": 10.0, "m": 1000.0, "mil": 0.0254,
    # torque -> N-m
    "ft-lb": 1.3558179, "in-lb": 0.11298483, "N-m": 1.0,
    # pressure -> kPa
    "psi": 6.8947573, "kPa": 1.0, "MPa": 1000.0, "bar": 100.0, "inHg": 3.3863886,
    # capacity -> L
    "gal": 3.7854118, "qt": 0.9463529, "pt": 0.4731765, "fl-oz": 0.0295735, "L": 1.0, "mL": 0.001,
    # weight/mass -> kg
    "lb": 0.45359237, "oz": 0.02834952, "kg": 1.0, "g": 0.001, "ton": 907.18474,
    # force -> N
    "lbf": 4.4482216, "N": 1.0, "kN": 1000.0,
    # speed -> km/h
    "mph": 1.609344, "km/h": 1.0,
    # flow -> L/min
    "gpm": 3.7854118, "cfm": 28.316847, "L/min": 1.0,
    # area -> sq-cm
    "sq-in": 6.4516, "sq-ft": 929.0304, "sq-cm": 1.0,
}
# for each unit, the partner unit to display in the OTHER system
_PARTNER = {
    "in": "mm", "ft": "m", "yd": "m", "mm": "in", "cm": "in", "m": "ft", "mil": "mm",
    "ft-lb": "N-m", "in-lb": "N-m", "N-m": "ft-lb",
    "psi": "kPa", "kPa": "psi", "MPa": "psi", "bar": "psi", "inHg": "kPa",
    "gal": "L", "qt": "L", "pt": "L", "fl-oz": "mL", "L": "gal", "mL": "fl-oz",
    "lb": "kg", "oz": "g", "kg": "lb", "g": "oz", "ton": "kg",
    "lbf": "N", "N": "lbf", "kN": "lbf",
    "mph": "km/h", "km/h": "mph",
    "gpm": "L/min", "cfm": "L/min", "L/min": "gpm",
    "sq-in": "sq-cm", "sq-ft": "sq-m" if False else "sq-cm", "sq-cm": "sq-in",
}


def _to_float(v):
    try:
        return float(str(v).replace(",", "").strip())
    except Exception:
        return None


def convert(value, from_unit, to_unit):
    """Convert a numeric value between two units of the SAME dimension. Returns float or None if not convertible."""
    a = _TO_BASE.get(from_unit); b = _TO_BASE.get(to_unit); x = _to_float(value)
    if a is None or b is None or x is None:
        return None
    # temperature handled separately (affine, not a simple factor)
    return x * a / b


def convert_temp(value, from_unit):
    x = _to_float(value)
    if x is None:
        return None, None
    if from_unit == "degF":
        return round((x - 32) * 5.0 / 9.0, 1), "degC"
    if from_unit == "degC":
        return round(x * 9.0 / 5.0 + 32, 1), "degF"
    return None, None


def _fmt(n):
    if n is None:
        return None
    r = round(n, 2)
    return ("%g" % (round(r) if abs(r - round(r)) < 1e-9 else r))


def dual(value, unit):
    """Return the value converted into the OTHER measurement system as a display string, e.g. dual('180','in')='4572 mm'.
    Returns '' if the unit isn't convertible. Never raises."""
    try:
        if unit in ("degF", "degC"):
            v, u = convert_temp(value, unit)
            return ("%s %s" % (_fmt(v), u)) if v is not None else ""
        partner = _PARTNER.get(unit)
        if not partner:
            return ""
        out = convert(value, unit, partner)
        return ("%s %s" % (_fmt(out), partner)) if out is not None else ""
    except Exception:
        return ""


def system_of(unit):
    """'imperial' | 'metric' | '' -- which measurement system a unit belongs to (for labelling)."""
    imperial = {"in", "ft", "yd", "mil", "ft-lb", "in-lb", "psi", "inHg", "gal", "qt", "pt", "fl-oz",
                "lb", "oz", "ton", "lbf", "mph", "gpm", "cfm", "sq-in", "sq-ft", "degF"}
    metric = {"mm", "cm", "m", "N-m", "kPa", "MPa", "bar", "L", "mL", "kg", "g", "N", "kN", "km/h",
              "L/min", "sq-cm", "degC"}
    return "imperial" if unit in imperial else ("metric" if unit in metric else "")


if __name__ == "__main__":
    # exact / near-exact conversions
    assert abs(convert(180, "in", "mm") - 4572.0) < 1e-6, convert(180, "in", "mm")
    assert abs(convert(1, "ft", "m") - 0.3048) < 1e-6
    assert abs(convert(30, "ft-lb", "N-m") - 40.674537) < 1e-4, convert(30, "ft-lb", "N-m")
    assert abs(convert(32, "psi", "kPa") - 220.63223) < 1e-3
    assert abs(convert(25, "gal", "L") - 94.635295) < 1e-3
    assert abs(convert(7700, "lb", "kg") - 3492.66) < 1e-1
    assert abs(convert(55, "mph", "km/h") - 88.51392) < 1e-3
    assert convert_temp(120, "degF") == (48.9, "degC"), convert_temp(120, "degF")
    # dual display strings
    assert dual("180", "in") == "4572 mm", dual("180", "in")
    assert dual("30", "ft-lb").startswith("40.67"), dual("30", "ft-lb")
    assert dual("25", "gal") == "94.64 L", dual("25", "gal")
    assert dual("-25", "degF") == "-31.7 degC", dual("-25", "degF")
    assert dual("5", "each") == "" and dual("5", "") == ""   # non-convertible -> empty, no crash
    assert system_of("in") == "imperial" and system_of("mm") == "metric" and system_of("each") == ""
    print("units self-test OK  (length/torque/pressure/capacity/weight/speed/temp conversions + dual display)")
# END OF FILE
