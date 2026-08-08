"""validate.py -- data-integrity validation for extracted values (R13: above military grade). OCR and
parsing can produce garbage -- a merged '3 5' read as '35000', a negative torque, a letter fused into a
number. A mechanic must never be shown a plausible-looking WRONG value. This module range-checks and
sanity-checks every extracted measurement and classifies it:

    ok         -- within the physically plausible band for that dimension type
    suspect    -- outside the normal band but not impossible -> show, but flag for a second look
    quarantine -- impossible / clearly garbled -> DO NOT show as fact; hold for review

The bands are deliberately GENEROUS: the goal is to catch the egregious errors without ever crying wolf on
a legitimate value (a false quarantine erodes trust as much as a false pass). Pure and unit-testable."""

from __future__ import annotations
import re

_NUM = re.compile(r"[-+]?(?:\d{1,9}(?:,\d{3})*(?:\.\d+)?|\.\d+)")

# type -> (hard_min, hard_max, soft_min, soft_max, allow_negative)
# hard = impossible outside -> quarantine; soft = unusual outside -> suspect. Units are the measures.py
# canonical ones; bands are wide on purpose (catch garble, not legitimate outliers).
_BANDS = {
    "torque":      (0, 200000, 0.5, 3000, False),
    "pressure":    (0, 100000, 0, 12000, False),
    "length":      (0, 100000, 0.0005, 2000, False),
    "weight":      (0, 500000, 0, 120000, False),
    "force":       (0, 500000, 0, 100000, False),
    "electrical":  (0, 100000, 0, 1500, False),
    "temperature": (-150, 6000, -70, 1600, True),
    "capacity":    (0, 100000, 0, 20000, False),
    "flow":        (0, 100000, 0, 20000, False),
    "speed":       (0, 100000, 0, 20000, False),
    "rotation":    (0, 2000000, 0, 200000, False),
    "angle":       (-720, 720, 0, 360, True),
    "area":        (0, 1000000, 0, 100000, False),
}


def to_float(v):
    if v is None:
        return None
    m = _NUM.search(str(v))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except Exception:
        return None


def looks_garbled(value_str):
    """Heuristic OCR-garble detector for a value token: a letter fused into the digits, absurd digit runs,
    or multiple decimal points. Conservative -- only flags clear corruption."""
    s = str(value_str or "").strip()
    if not s:
        return False
    core = s.split()[0] if s.split() else s
    # a digit immediately glued to a letter that isn't a known unit char (O/l confusions etc.)
    if re.search(r"\d[A-Za-z]|[A-Za-z]\d", core) and not re.fullmatch(r"[-+.\d,]+[A-Za-z\"'/]*", core):
        # allow things like 12V, 35A (number+unit) -- only flag if letters are INSIDE the number
        if re.search(r"\d[A-Za-z]\d", core):
            return True
    if core.count(".") > 1:
        return True
    if re.search(r"\d{8,}", core.replace(",", "").replace(".", "")):   # 8+ unbroken digits = almost surely a merge
        return True
    return False


def validate_value(dim_type, value, unit=""):
    """Return {status, reason, value} for one extracted value. status in ok|suspect|quarantine."""
    t = (dim_type or "").strip().lower()
    raw = value
    if looks_garbled(value):
        return {"status": "quarantine", "reason": "looks OCR-garbled", "value": raw}
    f = to_float(value)
    if f is None:
        # non-numeric where a number is expected
        if t in _BANDS:
            return {"status": "quarantine", "reason": "no numeric value", "value": raw}
        return {"status": "ok", "reason": "", "value": raw}
    band = _BANDS.get(t)
    if not band:
        return {"status": "ok", "reason": "", "value": raw}   # unknown type -> don't judge
    hmin, hmax, smin, smax, allow_neg = band
    if not allow_neg and f < 0:
        return {"status": "quarantine", "reason": "negative value impossible for %s" % t, "value": raw}
    if f < hmin or f > hmax:
        return {"status": "quarantine", "reason": "%s out of physical range (%g)" % (t, f), "value": raw}
    if f < smin or f > smax:
        return {"status": "suspect", "reason": "%s outside the usual band (%g) -- verify" % (t, f), "value": raw}
    return {"status": "ok", "reason": "", "value": raw}


def validate_rows(rows):
    """Annotate a list of {type,value,unit,...} with a 'validation' dict + return summary counts."""
    out = []
    counts = {"ok": 0, "suspect": 0, "quarantine": 0}
    for r in rows or []:
        v = validate_value(r.get("type"), r.get("value"), r.get("unit"))
        rr = dict(r)
        rr["validation"] = v
        counts[v["status"]] = counts.get(v["status"], 0) + 1
        out.append(rr)
    return {"rows": out, "counts": counts,
            "clean": counts["quarantine"] == 0 and counts["suspect"] == 0}


# --------------------------------------------------------------------------- #
# self-test: `python validate.py`                                             #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    ok = validate_value("torque", "35 ft-lb")
    assert ok["status"] == "ok", ok
    neg = validate_value("pressure", "-5 psi")
    assert neg["status"] == "quarantine", neg
    garb = validate_value("torque", "35000000 ft-lb")
    assert garb["status"] == "quarantine", garb
    merge = validate_value("length", "1234567890 in")
    assert merge["status"] == "quarantine", merge
    fused = validate_value("torque", "3S5")
    assert fused["status"] == "quarantine", fused
    cold = validate_value("temperature", "-40 F")
    assert cold["status"] == "ok", cold                    # negative temp is legit
    big = validate_value("torque", "4500 ft-lb")
    assert big["status"] == "suspect", big                 # high but not impossible
    volts = validate_value("electrical", "24 V")
    assert volts["status"] == "ok", volts
    print("validate value checks OK")

    rows = [{"type": "torque", "value": "35 ft-lb"}, {"type": "pressure", "value": "-5 psi"},
            {"type": "length", "value": "7.5 in"}, {"type": "torque", "value": "99999999"}]
    res = validate_rows(rows)
    assert res["counts"]["quarantine"] == 2 and res["counts"]["ok"] == 2, res["counts"]
    assert not res["clean"], res
    print("validate rows OK -> %s" % res["counts"])
    print("validate self-test PASS")

# END OF FILE
