"""serviceability.py -- SERVICEABLE / WEAR LIMITS + a go/no-go tolerance checker (R13 safety). The nominal
size of a part ('shaft diameter 0.50 in') is not what keeps a soldier safe -- the SERVICEABLE LIMIT is
('replace if below 0.48 in'). TMs state these as wear limits, minimum/maximum serviceable dimensions,
reject-at gauges, and 'not to exceed' values. This module extracts those limits (as bounds, not nominals)
and answers the real question a mechanic asks with a caliper in hand: 'is my measured value still in spec?'

extract_limits() and assess() are pure and unit-testable. Read-only, offline. Nothing here is a substitute
for the TM -- every limit carries its context and should be confirmed on the cited page."""

from __future__ import annotations
import re

_NUM = r"[-+]?(?:\d{1,6}(?:,\d{3})*(?:\.\d+)?|\.\d+)"
_UNIT = r"(?:in(?:ch(?:es)?)?|mm|cm|ft|psi|lb|ft-?lb|in-?lb|V|A|deg|°|thou|mil)\b\.?"
_VAL = r"(?P<v>%s)\s*(?P<u>%s)?" % (_NUM, _UNIT)

# each pattern -> the BOUND it implies: 'min' (measured must be >= value) or 'max' (measured must be <= value)
_PATTERNS = [
    (re.compile(r"\b(?:minimum|min\.?)\s+(?:serviceable\s+)?(?:\w+\s+){0,3}?(?:is\s+|of\s+|:\s*)?" + _VAL, re.I), "min", "minimum"),
    (re.compile(r"\bshall\s+not\s+be\s+less\s+than\s+" + _VAL, re.I), "min", "min (shall not be less than)"),
    (re.compile(r"\breplace\s+(?:if\s+)?(?:\w+\s+){0,6}?(?:less\s+than|below|under)\s+" + _VAL, re.I), "min", "replace if below"),
    (re.compile(r"\b(?:maximum|max\.?)\s+(?:serviceable\s+)?(?:\w+\s+){0,3}?(?:is\s+|of\s+|:\s*)?" + _VAL, re.I), "max", "maximum"),
    (re.compile(r"\bnot\s+to\s+exceed\s+" + _VAL, re.I), "max", "not to exceed"),
    (re.compile(r"\bshall\s+not\s+exceed\s+" + _VAL, re.I), "max", "shall not exceed"),
    (re.compile(r"\breplace\s+(?:if\s+)?(?:\w+\s+){0,6}?(?:greater\s+than|more\s+than|over|above|exceeds)\s+" + _VAL, re.I), "max", "replace if above"),
    (re.compile(r"\b(?:wear\s+limit|serviceable\s+limit|reject\s+(?:at|if))\s*[:\-]?\s*" + _VAL, re.I), "limit", "wear/serviceable limit"),
]


def _f(s):
    try:
        return float(str(s).replace(",", ""))
    except Exception:
        return None


def extract_limits(text, cap=40):
    """Pull serviceable/wear limits (bounds) from text. Returns [{bound, value, unit, kind, context}].
    bound in min|max|limit (limit = stated wear limit, direction inferred by the reader)."""
    if not text:
        return []
    t = re.sub(r"\s+", " ", text)
    out, seen = [], set()
    for rx, bound, kind in _PATTERNS:
        for m in rx.finditer(t):
            v = _f(m.group("v"))
            if v is None:
                continue
            u = (m.group("u") or "").strip().rstrip(".")
            key = (bound, v, u, kind)
            if key in seen:
                continue
            seen.add(key)
            s = max(0, m.start() - 24)
            out.append({"bound": bound, "value": v, "unit": u, "kind": kind,
                        "context": t[s:m.end() + 8].strip()})
            if len(out) >= cap:
                return out
    return out


def assess(measured, limits, unit=None):
    """Given a MEASURED value and the extracted limits, return a verdict per applicable limit + an overall
    call: 'serviceable' | 'replace' | 'marginal' | 'unknown'. Pure comparison; unit match is best-effort."""
    mv = _f(measured)
    if mv is None:
        return {"overall": "unknown", "reason": "no measured value", "checks": []}
    checks, worst = [], "serviceable"
    for lim in limits or []:
        if unit and lim.get("unit") and lim["unit"].lower() != str(unit).lower():
            continue                                  # different unit -> don't compare
        lv = lim.get("value")
        if lv is None:
            continue
        bound = lim["bound"]
        if bound == "min":
            ok = mv >= lv
            margin = mv - lv
        elif bound == "max":
            ok = mv <= lv
            margin = lv - mv
        else:                                         # 'limit': can't be sure of direction -> flag as marginal near it
            ok = None
            margin = mv - lv
        verdict = ("serviceable" if ok else "replace") if ok is not None else "marginal"
        # near the boundary (within 3%) -> marginal even if technically ok
        if ok and lv and abs(margin) <= 0.03 * abs(lv):
            verdict = "marginal"
        checks.append({"bound": bound, "limit": lv, "unit": lim.get("unit"), "kind": lim.get("kind"),
                       "measured": mv, "verdict": verdict, "margin": round(margin, 4)})
        if verdict == "replace":
            worst = "replace"
        elif verdict == "marginal" and worst != "replace":
            worst = "marginal"
    if not checks:
        return {"overall": "unknown", "reason": "no comparable limit", "checks": []}
    return {"overall": worst, "checks": checks}


# --------------------------------------------------------------------------- #
# self-test: `python serviceability.py`                                       #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    text = ("The nominal shaft diameter is 0.500 in. Minimum serviceable diameter is 0.480 in. "
            "Replace if brake lining thickness is less than 0.06 in. Drum diameter not to exceed 12.06 in. "
            "Wear limit: 0.020 in.")
    lims = extract_limits(text)
    kinds = {l["kind"] for l in lims}
    assert any(l["bound"] == "min" and abs(l["value"] - 0.480) < 1e-6 for l in lims), lims
    assert any(l["bound"] == "min" and abs(l["value"] - 0.06) < 1e-6 for l in lims), lims
    assert any(l["bound"] == "max" and abs(l["value"] - 12.06) < 1e-6 for l in lims), lims
    assert any(l["bound"] == "limit" and abs(l["value"] - 0.020) < 1e-6 for l in lims), lims
    print("extract_limits OK -> %d limits: %s" % (len(lims), sorted(kinds)))

    # a shaft measured at 0.475 in is BELOW the 0.480 minimum -> replace
    a = assess(0.475, [l for l in lims if l["bound"] == "min" and l["value"] == 0.480], unit="in")
    assert a["overall"] == "replace", a
    print("assess OK -> 0.475 vs min 0.480 => %s" % a["overall"])

    # 0.500 is safely above min -> serviceable
    b = assess(0.500, [l for l in lims if l["bound"] == "min" and l["value"] == 0.480], unit="in")
    assert b["overall"] == "serviceable", b
    # 0.485 is within 3% of 0.480 -> marginal
    c = assess(0.485, [l for l in lims if l["bound"] == "min" and l["value"] == 0.480], unit="in")
    assert c["overall"] == "marginal", c
    print("assess serviceable/marginal OK")

    # a max bound: drum 12.10 exceeds 12.06 max -> replace
    d = assess(12.10, [l for l in lims if l["bound"] == "max"], unit="in")
    assert d["overall"] == "replace", d
    print("assess max-bound OK -> 12.10 vs max 12.06 => replace")
    print("serviceability self-test PASS")

# END OF FILE
