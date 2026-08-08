#!/usr/bin/env python3
"""THE VIEWER -- MULTI-METHOD CROSS-VALIDATION (v1.3.2, catalog §7.5). The same measurement can be found by several
independent extractors -- native text (measures), a spec table (tables/tables_plus), leading-particulars, or a
structured IETM module. When two or more of them agree on the SAME value for a subject, that value is far more
trustworthy; when they disagree, it needs review. This reconciles records from all methods into one confidence-scored
list and flags conflicts. Pure stdlib; feeds the Masterfile's confidence/anomaly layer. Corpus authoritative."""
from collections import defaultdict


def _key(rec):
    return (rec.get("type", ""), (rec.get("unit") or "").lower())


def _val(rec):
    return str(rec.get("value", "")).replace(",", "").strip()


def reconcile(records):
    """`records` = [{type, unit, value, method}]. Returns
    {agreed:[{type,unit,value,methods,confidence}], conflicts:[{type,unit,values:{value:[methods]}}]}.
    A value confirmed by N distinct methods gets confidence = min(1.0, 0.5 + 0.25*(N-1)); a lone value = 0.5.
    A (type,unit) with >1 distinct value across methods is a conflict (needs review)."""
    by_tu = defaultdict(lambda: defaultdict(set))   # (type,unit) -> value -> {methods}
    for r in records or []:
        v = _val(r)
        if not v:
            continue
        by_tu[_key(r)][v].add(r.get("method", "?"))
    agreed, conflicts = [], []
    for (ty, unit), values in by_tu.items():
        if len(values) > 1:
            conflicts.append({"type": ty, "unit": unit,
                              "values": {v: sorted(ms) for v, ms in values.items()}})
        for v, methods in values.items():
            n = len(methods)
            conf = min(1.0, 0.5 + 0.25 * (n - 1))
            agreed.append({"type": ty, "unit": unit, "value": v, "methods": sorted(methods),
                           "n_methods": n, "confidence": round(conf, 3),
                           "confirmed": n >= 2, "contested": len(values) > 1})
    agreed.sort(key=lambda r: (-r["n_methods"], r["type"]))
    return {"agreed": agreed, "conflicts": conflicts,
            "n_confirmed": sum(1 for a in agreed if a["confirmed"]),
            "n_conflicts": len(conflicts)}


if __name__ == "__main__":
    records = [
        {"type": "length", "unit": "in", "value": "180", "method": "measures"},
        {"type": "length", "unit": "in", "value": "180", "method": "tables_plus"},
        {"type": "length", "unit": "in", "value": "180", "method": "ietm"},        # 3-way agreement -> high conf
        {"type": "weight", "unit": "lb", "value": "5200", "method": "measures"},
        {"type": "weight", "unit": "lb", "value": "7700", "method": "leadingspecs"},  # conflict
        {"type": "torque", "unit": "ft-lb", "value": "30", "method": "measures"},     # lone value
    ]
    r = reconcile(records)
    length = [a for a in r["agreed"] if a["type"] == "length"][0]
    assert length["n_methods"] == 3 and length["confidence"] >= 0.99 and length["confirmed"], length
    torque = [a for a in r["agreed"] if a["type"] == "torque"][0]
    assert torque["confidence"] == 0.5 and not torque["confirmed"], torque
    assert r["n_conflicts"] == 1 and r["conflicts"][0]["type"] == "weight", r["conflicts"]
    weights = [a for a in r["agreed"] if a["type"] == "weight"]
    assert all(w["contested"] for w in weights), "weight values should be flagged contested"
    print("crossval self-test OK  (3-way length confirmed conf=%.2f, weight conflict flagged, lone torque=0.5)"
          % length["confidence"])
# END OF FILE
