"""conflicts.py -- cross-manual CONFLICT checker. Two manuals (or two editions) sometimes state different
values for the SAME thing on the same part -- a different torque, pressure, clearance, or dimension. That
is exactly the kind of discrepancy that gets a fastener over- or under-torqued. This module gathers the
measured values for a part across the corpus, groups them by dimension type + unit, and flags any group
where documents DISAGREE beyond a tolerance -- with every competing value cited to its manual + page so a
human can adjudicate.

detect(rows) is pure and unit-testable; the route feeds it measures.find_for_query results. Read-only."""

from __future__ import annotations
import re

_NUM = re.compile(r"[-+]?(?:\d{1,7}(?:,\d{3})*(?:\.\d+)?|\.\d+)")
# safety-critical types where a disagreement matters most
_HIGH = {"torque", "pressure", "electrical", "force"}


def _to_float(v):
    if v is None:
        return None
    m = _NUM.search(str(v))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except Exception:
        return None


def detect(rows, rel_tol=0.05, min_docs=2):
    """rows: iterable of {type, unit, value, doc, tm, page, page_url}. Returns a list of conflicts, each:
        {type, unit, min, max, spread_pct, severity, n_docs, values:[{value, doc, tm, page, page_url}], trust}
    A conflict = one (type,unit) group whose values span more than rel_tol AND come from >= min_docs
    DISTINCT documents with distinct values.
    v1.13 (R13): values that validate.py QUARANTINES (garbled OCR / physically impossible) are dropped
    BEFORE grouping, so a garble can never manufacture a false safety-critical conflict. Callers wanting
    the dropped count use check_query (reported as 'quarantined')."""
    import validate as _validate
    groups = {}
    for r in rows or []:
        t = (r.get("type") or "").strip()
        u = (r.get("unit") or "").strip()
        fv = _to_float(r.get("value"))
        if not t or fv is None:
            continue
        if _validate.validate_value(t, r.get("value"), u)["status"] == "quarantine":
            continue                                   # garbled/impossible value: never a conflict input
        groups.setdefault((t, u), []).append({
            "f": fv, "value": r.get("value"), "doc": r.get("doc"), "tm": r.get("tm") or r.get("vehicle") or "",
            "page": r.get("page"), "page_url": r.get("page_url")})
    out = []
    for (t, u), vals in groups.items():
        if len(vals) < 2:
            continue
        docs_by_val = {}
        for v in vals:
            docs_by_val.setdefault(round(v["f"], 6), set()).add(str(v["doc"]))
        distinct_vals = sorted(docs_by_val)
        if len(distinct_vals) < 2:
            continue
        lo, hi = distinct_vals[0], distinct_vals[-1]
        if hi <= 0:
            continue
        spread = (hi - lo) / abs(hi)
        # need the disagreement to be real AND span >= 2 distinct documents overall
        all_docs = set()
        for s in docs_by_val.values():
            all_docs |= s
        if spread <= rel_tol or len(all_docs) < min_docs:
            continue
        # keep one representative citation per distinct value
        reps, seen = [], set()
        for v in sorted(vals, key=lambda x: x["f"]):
            key = round(v["f"], 6)
            if key not in seen:
                seen.add(key)
                reps.append({"value": v["value"], "doc": v["doc"], "tm": v["tm"],
                             "page": v["page"], "page_url": v["page_url"]})
        out.append({"type": t, "unit": u, "min": lo, "max": hi,
                    "spread_pct": round(spread * 100, 1),
                    "severity": "high" if t in _HIGH else "medium",
                    "n_docs": len(all_docs), "values": reps})
    out.sort(key=lambda c: (0 if c["severity"] == "high" else 1, -c["spread_pct"]))
    # v1.13 trust badge (R13): a detected conflict is by definition a WIDE disagreement between
    # authoritative sources -> 'review' (a human must adjudicate; neither value is 'verified').
    try:
        import trust as _trust
        for c in out:
            c["trust"] = _trust.badge(source="corpus", spread="wide", n_samples=c["n_docs"])
    except Exception:
        pass
    return out


# ---- v1.13 (#88-lite): precomputed conflict sweep sidecar (index/conflicts.db) -------------------
_DEFAULT_TOL = 0.05


def _sidecar_path(db_path):
    import os
    return os.path.join(os.path.dirname(os.path.abspath(db_path)), "conflicts.db")


def precomputed_for(db_path, q, max_age_days=45):
    """Latest fresh sweep entry (build_conflicts.py) for this subject, or None. Exact subject match
    (lower/trim) only -- never a fuzzy guess. Read-only on the append-only sidecar; any problem
    (missing db, old schema, bad JSON) returns None so the live scan runs instead (degrade safe)."""
    import os, sqlite3, json
    p = _sidecar_path(db_path)
    subj = " ".join((q or "").strip().lower().split())
    if not subj or not os.path.exists(p):
        return None
    try:
        con = sqlite3.connect("file:%s?mode=ro" % p, uri=True)
        try:
            row = con.execute(
                "SELECT subject, n_values, quarantined, conflicts_json, ts FROM results "
                "WHERE LOWER(TRIM(subject))=? AND ts >= datetime('now', ?) "
                "ORDER BY id DESC LIMIT 1", (subj, "-%d days" % int(max_age_days))).fetchone()
        finally:
            con.close()
    except Exception:
        return None
    if not row:
        return None
    try:
        conflicts_list = json.loads(row[3] or "[]")
    except Exception:
        return None
    return {"query": q, "n_values": int(row[1] or 0), "quarantined": int(row[2] or 0),
            "conflicts": conflicts_list, "precomputed": True, "built": row[4]}


def check_query(db_path, q, limit=120, rel_tol=0.05, use_precomputed=True):
    """Gather measures for a query across the corpus, then detect conflicts. Returns
    {query, n_values, quarantined, conflicts as a list}. Best-effort; empty list if measures isn't
    importable. v1.13: 'quarantined' counts the values validate.py held back (measures withholds them
    upstream; detect() also refuses them defensively) so the response says WHY inputs were excluded.
    v1.13 (#88-lite): when index/conflicts.db has a FRESH precomputed sweep entry for this exact
    subject AND the caller uses the default tolerance, that stored result is returned instantly
    ('precomputed': true + build timestamp); otherwise the live scan runs unchanged."""
    if use_precomputed and abs(rel_tol - _DEFAULT_TOL) < 1e-9:
        pre = precomputed_for(db_path, q)
        if pre is not None:
            return pre
    try:
        import measures
        res = measures.find_for_query(db_path, q, limit=limit)
        rows = res.get("results", [])
        quarantined = int(res.get("quarantined_count") or 0)
    except Exception as e:
        return {"query": q, "n_values": 0, "quarantined": 0, "conflicts": [], "error": str(e)}
    return {"query": q, "n_values": len(rows), "quarantined": quarantined,
            "conflicts": detect(rows, rel_tol=rel_tol), "precomputed": False}


# --------------------------------------------------------------------------- #
# self-test: `python conflicts.py`                                            #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    rows = [
        {"type": "torque", "unit": "ft-lb", "value": "35 ft-lb", "doc": "10", "tm": "TM-A", "page": 12},
        {"type": "torque", "unit": "ft-lb", "value": "50 ft-lb", "doc": "22", "tm": "TM-B", "page": 4},
        {"type": "torque", "unit": "ft-lb", "value": "35 ft-lb", "doc": "10", "tm": "TM-A", "page": 12},  # dup, same doc
        {"type": "length", "unit": "in", "value": "7.50 in", "doc": "10", "tm": "TM-A", "page": 3},
        {"type": "length", "unit": "in", "value": "7.51 in", "doc": "22", "tm": "TM-B", "page": 9},        # within tol
        {"type": "pressure", "unit": "psi", "value": "30 psi", "doc": "10", "tm": "TM-A", "page": 1},       # single doc
    ]
    cs = detect(rows)
    assert len(cs) == 1, cs                                  # only the torque disagreement qualifies
    c = cs[0]
    assert c["type"] == "torque" and c["severity"] == "high", c
    assert c["min"] == 35 and c["max"] == 50 and c["n_docs"] == 2, c
    assert len(c["values"]) == 2, c
    print("conflicts detect OK -> %s %s: %s vs %s across %d docs (%.0f%% apart, %s)"
          % (c["type"], c["unit"], c["values"][0]["value"], c["values"][1]["value"],
             c["n_docs"], c["spread_pct"], c["severity"]))

    # no conflict when everyone agrees
    agree = [{"type": "torque", "unit": "ft-lb", "value": "35", "doc": "1", "page": 1},
             {"type": "torque", "unit": "ft-lb", "value": "35", "doc": "2", "page": 2}]
    assert detect(agree) == [], "false positive"
    print("conflicts no-false-positive OK")

    # v1.13 (#88-lite): precomputed sidecar round-trip -- fresh entry served instantly, stale/missing -> None
    import json as _json, os as _os, sqlite3 as _sq, tempfile as _tf
    _d = _tf.mkdtemp(); _db = _os.path.join(_d, "viewer.db")
    assert precomputed_for(_db, "BOLT, MACHINE") is None, "no sidecar -> None"
    _sc = _sq.connect(_os.path.join(_d, "conflicts.db"))
    _sc.executescript("CREATE TABLE runs(run_id INTEGER PRIMARY KEY, started TEXT, finished TEXT, "
                      "n_subjects INT, n_with_conflicts INT, rel_tol REAL, note TEXT);"
                      "CREATE TABLE results(id INTEGER PRIMARY KEY, run_id INT, subject TEXT, n_values INT, "
                      "quarantined INT, n_conflicts INT, conflicts_json TEXT, ts TEXT DEFAULT (datetime('now')));")
    _sc.execute("INSERT INTO results(run_id,subject,n_values,quarantined,n_conflicts,conflicts_json) "
                "VALUES(1,'BOLT, MACHINE',5,1,1,?)", (_json.dumps(cs),))
    _sc.execute("INSERT INTO results(run_id,subject,n_values,quarantined,n_conflicts,conflicts_json,ts) "
                "VALUES(1,'OLD SUBJECT',2,0,0,'[]',datetime('now','-90 days'))")
    _sc.commit(); _sc.close()
    pre = check_query(_db, "bolt, machine")                 # case-insensitive exact subject match
    assert pre and pre.get("precomputed") is True and pre.get("built"), pre
    assert pre["n_values"] == 5 and pre["quarantined"] == 1 and len(pre["conflicts"]) == 1, pre
    assert pre["conflicts"][0]["type"] == "torque", pre
    assert precomputed_for(_db, "OLD SUBJECT") is None, "stale entry must NOT be served"
    assert precomputed_for(_db, "NEVER SWEPT") is None
    live = check_query(_db, "bolt, machine", rel_tol=0.10)  # non-default tol -> precomputed skipped
    assert live.get("precomputed") is not True, live
    print("precomputed sidecar OK -> fresh served (built %s), stale/mismatched fall back live" % pre["built"])
    print("conflicts self-test PASS")

# END OF FILE
