"""crossmethod.py -- CROSS-METHOD agreement (R13 idea #81; defense-in-depth accuracy). The same fact can be
obtained several independent ways: the free-text measurement extractor (measures), the spec-table extractor
(tables), and the PUBLOG characteristics. If they AGREE, trust rises; if they DISAGREE, that is surfaced,
never silently resolved. This is distinct from conflicts.py (which compares MANUALS): here we compare
EXTRACTION METHODS for corroboration of a single value.

reconcile() is pure and unit-testable; the route feeds it observations gathered from each method. Read-only."""

from __future__ import annotations
import re

_NUM = re.compile(r"[-+]?(?:\d{1,7}(?:,\d{3})*(?:\.\d+)?|\.\d+)")


def _f(v):
    if v is None:
        return None
    m = _NUM.search(str(v))
    try:
        return float(m.group(0).replace(",", "")) if m else None
    except Exception:
        return None


def reconcile(observations, rel_tol=0.03):
    """observations: [{method, type, value, unit, source?}]. Group by (type, unit) and judge concurrence.
    -> a list of {type, unit, status, consensus, methods list, n_methods, spread_pct}.
    status: confirmed (>=2 methods agree) | single (one method) | conflict (methods disagree)."""
    groups = {}
    for o in observations or []:
        t = (o.get("type") or "").strip().lower()
        u = (o.get("unit") or "").strip().lower()
        fv = _f(o.get("value"))
        if not t or fv is None:
            continue
        groups.setdefault((t, u), []).append({
            "method": o.get("method") or "?", "f": fv, "value": o.get("value"), "source": o.get("source")})
    out = []
    for (t, u), obs in groups.items():
        methods = sorted({o["method"] for o in obs})
        vals = [o["f"] for o in obs]
        lo, hi = min(vals), max(vals)
        spread = (hi - lo) / abs(hi) if hi else 0.0
        n_methods = len(methods)
        if n_methods < 2:
            status = "single"
        elif spread <= rel_tol:
            status = "confirmed"
        else:
            status = "conflict"
        # consensus = the modal / median value
        vals_sorted = sorted(vals)
        consensus = vals_sorted[len(vals_sorted) // 2]
        rep = next((o for o in obs if abs(o["f"] - consensus) < 1e-9), obs[0])
        out.append({"type": t, "unit": u, "status": status, "consensus": rep["value"],
                    "methods": methods, "n_methods": n_methods, "spread_pct": round(spread * 100, 1),
                    "observations": [{"method": o["method"], "value": o["value"], "source": o["source"]} for o in obs]})
    # conflicts first, then confirmed, then single
    order = {"conflict": 0, "confirmed": 1, "single": 2}
    out.sort(key=lambda x: (order.get(x["status"], 3), -x["n_methods"]))
    return out


def summary(reconciled):
    c = {"confirmed": 0, "single": 0, "conflict": 0}
    for r in reconciled or []:
        c[r["status"]] = c.get(r["status"], 0) + 1
    return {"counts": c, "trust": ("high" if c["conflict"] == 0 and c["confirmed"] > 0 else
                                   ("review" if c["conflict"] else "low"))}


# --------------------------------------------------------------------------- #
# self-test: `python crossmethod.py`                                          #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    obs = [
        {"method": "measures", "type": "torque", "value": "35 ft-lb", "unit": "ft-lb", "source": "TM p.4-12"},
        {"method": "tables",   "type": "torque", "value": "35",       "unit": "ft-lb", "source": "TM p.4-12 tbl"},
        {"method": "measures", "type": "pressure", "value": "35 psi", "unit": "psi"},   # single method
        {"method": "measures", "type": "length", "value": "7.50 in", "unit": "in"},
        {"method": "publog",   "type": "length", "value": "8.10 in", "unit": "in"},     # disagree
    ]
    r = reconcile(obs)
    by = {x["type"]: x for x in r}
    assert by["torque"]["status"] == "confirmed" and by["torque"]["n_methods"] == 2, by["torque"]
    assert by["pressure"]["status"] == "single", by["pressure"]
    assert by["length"]["status"] == "conflict", by["length"]
    print("reconcile OK -> torque=%s, pressure=%s, length=%s"
          % (by["torque"]["status"], by["pressure"]["status"], by["length"]["status"]))
    s = summary(r)
    assert s["counts"]["confirmed"] == 1 and s["counts"]["conflict"] == 1, s
    assert s["trust"] == "review", s
    print("summary OK -> %s trust=%s" % (s["counts"], s["trust"]))
    print("crossmethod self-test PASS")

# END OF FILE
