"""intervals.py -- SERVICE-INTERVAL extraction (roadmap #62, readiness). Manuals state maintenance cadence
in text: 'every 3,000 miles', 'every 250 hours', 'lubricate every 6 months', 'annually', 'before operation'.
This normalizes those into a structured {value, unit, basis} so the app can build a 'what's due' view and a
grease-point checklist. Pure and unit-testable. Read-only."""

from __future__ import annotations
import re

_NUM = r"(\d{1,3}(?:,\d{3})*|\d+)"
# numeric intervals -> (basis)
_NUMERIC = [
    (re.compile(r"\bevery\s+" + _NUM + r"\s*(?:miles?|mi)\b", re.I), "miles"),
    (re.compile(r"\bevery\s+" + _NUM + r"\s*(?:kilomet(?:er|re)?s?|km)\b", re.I), "km"),
    (re.compile(r"\bevery\s+" + _NUM + r"\s*(?:hour|hr)s?\b", re.I), "hours"),
    (re.compile(r"\bevery\s+" + _NUM + r"\s*days?\b", re.I), "days"),
    (re.compile(r"\bevery\s+" + _NUM + r"\s*weeks?\b", re.I), "weeks"),
    (re.compile(r"\bevery\s+" + _NUM + r"\s*months?\b", re.I), "months"),
    (re.compile(r"\bevery\s+" + _NUM + r"\s*years?\b", re.I), "years"),
    (re.compile(r"\bat\s+" + _NUM + r"\s*(?:miles?|mi)\b[^.]{0,20}?interval", re.I), "miles"),
    (re.compile(r"\bat\s+" + _NUM + r"\s*(?:hour|hr)\b[^.]{0,20}?interval", re.I), "hours"),
]
# named cadences -> (value, unit)
_NAMED = {
    "before operation": (1, "before-op"), "before-operation": (1, "before-op"),
    "during operation": (1, "during-op"), "after operation": (1, "after-op"),
    "daily": (1, "days"), "weekly": (1, "weeks"), "biweekly": (2, "weeks"),
    "monthly": (1, "months"), "bimonthly": (2, "months"), "quarterly": (3, "months"),
    "semiannually": (6, "months"), "semi-annually": (6, "months"), "semiannual": (6, "months"),
    "annually": (12, "months"), "annual": (12, "months"), "yearly": (12, "months"),
}
_NAMED_RX = re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(_NAMED, key=len, reverse=True)) + r")\b", re.I)


def _to_int(s):
    try:
        return int(str(s).replace(",", ""))
    except Exception:
        return None


def extract_intervals(text, cap=40):
    """-> [{value, unit, basis, context}]. basis is 'usage' (miles/hours/km), 'calendar' (days..years),
    or 'event' (before/during/after-op). Deduped."""
    if not text:
        return []
    t = re.sub(r"\s+", " ", text)
    out, seen = [], set()

    def add(value, unit, m):
        basis = ("usage" if unit in ("miles", "km", "hours") else
                 ("event" if unit.endswith("-op") else "calendar"))
        key = (value, unit)
        if key in seen:
            return
        seen.add(key)
        s = max(0, m.start() - 26)
        out.append({"value": value, "unit": unit, "basis": basis, "context": t[s:m.end() + 30].strip()})

    for rx, unit in _NUMERIC:
        for m in rx.finditer(t):
            add(_to_int(m.group(1)), unit, m)
            if len(out) >= cap:
                return out
    for m in _NAMED_RX.finditer(t):
        v, u = _NAMED[m.group(1).lower()]
        add(v, u, m)
        if len(out) >= cap:
            break
    return out


def normalize_days(interval):
    """Approx calendar-days for sorting/'what's due' (usage-based -> None). before/during/after-op -> 0."""
    v, u = interval.get("value"), interval.get("unit")
    if v is None:
        return None
    return {"days": v, "weeks": v * 7, "months": v * 30, "years": v * 365,
            "before-op": 0, "during-op": 0, "after-op": 0}.get(u)


# --------------------------------------------------------------------------- #
# self-test: `python intervals.py`                                            #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    text = ("Change the engine oil every 3,000 miles or every 6 months, whichever comes first. "
            "Lubricate the chassis every 250 hours. Inspect the air filter weekly. Service the "
            "transmission annually. Perform checks before operation.")
    iv = extract_intervals(text)
    got = {(i["value"], i["unit"]) for i in iv}
    assert (3000, "miles") in got, iv
    assert (6, "months") in got, iv
    assert (250, "hours") in got, iv
    assert (1, "weeks") in got, iv
    assert (12, "months") in got, iv                       # annually
    assert (1, "before-op") in got, iv
    print("extract_intervals OK -> %d intervals" % len(iv))
    bases = {i["basis"] for i in iv}
    assert bases == {"usage", "calendar", "event"}, bases
    print("   bases:", sorted(bases))
    assert normalize_days({"value": 6, "unit": "months"}) == 180
    assert normalize_days({"value": 3000, "unit": "miles"}) is None   # usage-based
    print("normalize_days OK")
    print("intervals self-test PASS")

# END OF FILE
