#!/usr/bin/env python3
"""THE VIEWER -- LEADING-PARTICULARS / KEY:VALUE EXTRACTOR (v1.2.0, catalog §3.6). TM 'leading particulars' and spec
blocks list data as `Label: value unit` (Length: 180 in / Curb weight: 5,200 lb / Fuel type: Diesel). This pulls those
NAMED pairs -- so a value is tied to WHAT it measures, not just floating in prose -- and classifies the numeric ones by
dimension type via the measures engine. Non-numeric specs (Fuel type: Diesel) are captured too. Pure/stdlib; the
measurement extractor is injectable so it self-tests without importing the (possibly mount-truncated) measures module.
Feeds the measures sidecar + the Masterfile. Corpus authoritative; read-only."""
import re

# 'Label: rest-of-line'  — label is 2..48 chars of letters/space/()/-/./slash, then a colon
_KV = re.compile(r"^[ \t>*|]*(?P<label>[A-Za-z][A-Za-z0-9 ()/.\-]{1,47}?)\s*[:\-–]\s+(?P<val>\S.*\S|\S)\s*$")
# labels that are clearly not spec keys (drop noise)
_SKIP = re.compile(r"^(see|note|warning|caution|figure|table|http|www|page|section|chapter|para)\b", re.I)


def extract(text, page=None, cap=200, measure_fn=None):
    """Return [{label, value, unit, type, value_text, context, [page]}] for each 'Label: value' line in `text`.
    Numeric specs carry unit/type/value (via `measure_fn`, default measures.extract); text specs carry value_text."""
    if not text:
        return []
    if measure_fn is None:
        import measures  # lazy so this module imports even if measures is momentarily unreadable
        measure_fn = measures.extract
    out = []; seen = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or len(line) > 240 or ":" not in line and "–" not in line and " - " not in line:
            continue
        m = _KV.match(line)
        if not m:
            continue
        label = re.sub(r"\s+", " ", m.group("label")).strip(" .-")
        val = m.group("val").strip()
        if not label or _SKIP.match(label) or len(val) > 160:
            continue
        key = (label.lower(), val.lower()[:40])
        if key in seen:
            continue
        seen.add(key)
        rec = {"label": label, "value_text": val[:120], "context": line[:180]}
        meas = measure_fn(val, cap=3)
        if meas:
            mm = meas[0]
            rec.update({"value": mm.get("value"), "value2": mm.get("value2"),
                        "tolerance": mm.get("tolerance"), "unit": mm.get("unit"), "type": mm.get("type")})
        else:
            rec.update({"value": None, "unit": None, "type": "text"})
        if page is not None:
            rec["page"] = page
        out.append(rec)
        if len(out) >= cap:
            break
    return out


def as_measurements(text, page=None, measure_fn=None):
    """Just the NUMERIC leading-particulars as measurement-style dicts (for the measures sidecar / Masterfile)."""
    rows = []
    for r in extract(text, page=page, measure_fn=measure_fn):
        if r.get("type") not in (None, "text") and r.get("value") is not None:
            rows.append({"type": r["type"], "unit": r["unit"], "value": r["value"], "value2": r.get("value2"),
                         "tolerance": r.get("tolerance"), "raw": (r["label"] + ": " + (r.get("value_text") or ""))[:60],
                         "context": r["context"], "page": r.get("page")})
    return rows


if __name__ == "__main__":
    sample = (
        "LEADING PARTICULARS\n"
        "Length: 180 in\n"
        "Curb weight: 5,200 lb\n"
        "Fuel capacity: 25 gallons\n"
        "Charging voltage: 28 VDC\n"
        "Fuel type: Diesel, DF-2\n"
        "Fording depth: 30 in without kit\n"
        "Tire pressure: 32 psi cold\n"
        "NOTE: this line must be skipped\n"
        "See figure 4-2 for details\n")

    def fake_measure(v, cap=3):
        import re as _re
        m = _re.match(r"([\d,\.]+)\s*(in|lb|gallons?|psi|vdc)", v, _re.I)
        if not m:
            return []
        u = m.group(2).lower()
        typ = {"in": "length", "lb": "weight", "gallons": "capacity", "gallon": "capacity",
               "psi": "pressure", "vdc": "electrical"}.get(u, "other")
        canon = {"in": "in", "lb": "lb", "gallons": "gal", "gallon": "gal", "psi": "psi", "vdc": "V"}.get(u, u)
        return [{"value": m.group(1).replace(",", ""), "value2": None, "tolerance": None, "unit": canon, "type": typ}]

    rows = extract(sample, page=3, measure_fn=fake_measure)
    labels = {r["label"] for r in rows}
    assert "Length" in labels and "Curb weight" in labels and "Fuel capacity" in labels, labels
    assert "Fuel type" in labels, "non-numeric spec should be captured"
    assert "NOTE" not in labels and not any("figure" in l.lower() for l in labels), "noise not skipped"
    lengths = [r for r in rows if r.get("type") == "length"]
    assert lengths and lengths[0]["value"] == "180", lengths
    nums = as_measurements(sample, page=3, measure_fn=fake_measure)
    assert any(n["type"] == "weight" and n["value"] == "5200" for n in nums), nums
    assert all("page" in n for n in nums)
    print("leadingspecs self-test OK  (named key:value pairs, numeric + text, noise skipped, %d pairs)" % len(rows))
# END OF FILE
