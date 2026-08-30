"""conflicts.py -- cross-manual CONFLICT checker. Two manuals (or two editions) sometimes state different
values for the SAME thing on the same part -- a different torque, pressure, clearance, or dimension. That
is exactly the kind of discrepancy that gets a fastener over- or under-torqued. This module gathers the
measured values for a part across the corpus, groups them by dimension type + unit, and flags any group
where documents DISAGREE beyond a tolerance -- with every competing value cited to its manual + page so a
human can adjudicate.

v1.25.x history (two passes, second one fixing a safety regression the first introduced):
  Pass 1 tried grouping by (type, unit, vehicle) instead of (type, unit): a generic FTS-matched subject
  pools numeric readings from whatever documents happen to match it, and unrelated vehicles routinely
  share a subject string -- confirmed on the real corpus, a "WINCH INSTALLATION" sweep pooled 4 documents
  from 3 different vehicles into one group (doc 983 vehicle="5 TON", doc 13781/14105 vehicle="TM,S
  HUMMERS,ALL", doc 870 vehicle="2.5 Ton Truck"). Hard-splitting by vehicle correctly separated the 3
  unrelated vehicles.
  Adversarial review then caught a serious safety regression in that design: "vehicle" is a raw
  ingest-folder name (see viewer_ingest.py's `vehicle = rel.split(os.sep)[0]`), not a canonical vehicle
  ID. The SAME real vehicle is sometimes filed under two different folder spellings (e.g. "HMMWV" vs
  "TM,S HUMMERS,ALL"), and hard-splitting silently DROPPED a genuine cross-manual disagreement whenever
  that happened -- confirmed directly: detect() on a real 35-vs-50-ft-lb torque disagreement returned []
  once the two rows were tagged with those two different (real-same-vehicle) folder names, because they
  landed in separate groups of 1 and never got compared. For a module whose whole purpose is catching
  exactly this class of disagreement, a silent false negative is worse than the false positive it
  replaced -- "fail loud, never fabricate" (R13) means never silently dropping a candidate conflict.
  Also confirmed against the real corpus: ~86% of this corpus's 39,683 documents sit under generic
  ingest-staging folder names ("WORK" 65%, "ALL EMS VEIWER FILES" 17.6%, "Additional IMG Info" 2.9%) that
  mix genuinely unrelated real vehicles -- so hard-splitting by vehicle barely narrowed the original
  false-positive problem for most of the corpus anyway (e.g. an "ALTERNATOR" query still pooled an HMMWV
  torque spec against an unrelated MRAP-family torque spec, both tagged vehicle="WORK").

  Pass 2 (this version) restores the ORIGINAL (type, unit)-only grouping -- identical recall to the
  pre-vehicle-scoping code, so nothing that would have been flagged before is ever silently dropped --
  and instead ANNOTATES each flagged group with whether its values share one vehicle label or several:
  "vehicle" (the single label when unambiguous, else ""), "vehicles" (sorted distinct labels seen),
  "cross_vehicle" (bool). Nothing is ever hidden because of a vehicle mismatch; a caller/UI can choose to
  show cross_vehicle=True conflicts with a "confirm these are really the same vehicle" caveat instead of
  presenting them with the same confidence as a single-vehicle hit. This does NOT eliminate the original
  WINCH INSTALLATION false positive -- it still gets flagged, just now marked cross_vehicle=True with its
  distinct vehicle labels listed, so a human can dismiss it quickly instead of it being silently absent
  OR silently indistinguishable from a confirmed same-vehicle conflict.

KNOWN REMAINING LIMITATIONS (disclosed, not fixed here):
  - "vehicle" is a raw ingest-folder name (viewer_ingest.py), not a curated identity -- cross_vehicle=False
    ("looks like one vehicle") can still, in principle, mean "two different real vehicles both happen to
    be filed under the exact same broad folder" (e.g. two unrelated trucks both under "WORK"). See
    xref_feature.py's _clean_vehicles() for the closest existing precedent to a real fix; not reused here
    to keep this change narrowly scoped to the grouping/annotation logic.
  - Same-vehicle-different-part over-pooling (many different bolts on ONE HMMWV sharing "BOLT" as their
    FTS-matched subject) still applies, unchanged from before either pass.
  - index/conflicts.db's precomputed sweep rows carry no code-version stamp, only a wall-clock freshness
    window (precomputed_for()'s max_age_days) -- a sidecar row built by an older version of detect() will
    keep being served as-is until it ages out or a fresh sweep overwrites it. Re-sweep (build_conflicts.py)
    after any change to this module's grouping/annotation logic; don't rely on the age window alone.
  - Citation completeness: "values" keeps one representative citation per DISTINCT NUMERIC VALUE
    (pre-existing dedup, unrelated to vehicle-scoping) -- if two different-vehicle rows happen to report
    the identical value, only one gets a citation. A vehicle named in "vehicles" can therefore have zero
    backing doc/page anywhere in "values". Not a new bug, but worth knowing before treating "vehicles"
    as fully citation-traceable.
  - As shipped, NOTHING in engine/ui/part.html's conflict rendering reads "vehicle"/"vehicles"/
    "cross_vehicle" yet -- the annotation is computed and available via the API but not yet surfaced to
    a technician. detect()'s own sort (severity, then cross_vehicle, then spread) at least keeps a
    confirmed single-vehicle conflict from being outranked by an ambiguous multi-vehicle one of the same
    severity, but wiring the UI to actually show the distinction (not just order by it) is a separate,
    still-open follow-up.

detect(rows) is pure and unit-testable; the route feeds it measures.find_for_query results (which sets
"vehicle" on every row -- see measures.find_for_query()). Read-only."""

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
    """rows: iterable of {type, unit, value, doc, tm, vehicle, page, page_url}. Returns a list of
    conflicts, each:
        {type, unit, vehicle, vehicles, cross_vehicle, min, max, spread_pct, severity, n_docs,
         values:[{value, doc, tm, page, page_url, vehicle}], trust}
    A conflict = one (type, unit) group whose values span more than rel_tol AND come from >= min_docs
    DISTINCT documents with distinct values -- this is the ORIGINAL, full-recall grouping (unchanged
    from before either vehicle-scoping pass): nothing that would have been flagged before is silently
    dropped now. Each flagged group is additionally annotated with whether its values share one vehicle
    label or several ("vehicle"/"vehicles"/"cross_vehicle") -- see the module docstring for why a HARD
    split by vehicle was tried and reverted (it silently dropped a real cross-manual disagreement
    whenever the same real vehicle was filed under two different ingest-folder spellings). Vehicle
    strings are normalized via whitespace-collapse + uppercase (`" ".join(s.split()).upper()`) before
    comparison; rows with a missing/blank vehicle contribute no vehicle label at all (rather than a
    literal "" label) and never make an otherwise-single-vehicle group look cross-vehicle.
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
        veh = " ".join(str(r.get("vehicle") or "").split()).upper()   # collapse internal whitespace too
        groups.setdefault((t, u), []).append({
            "f": fv, "value": r.get("value"), "doc": r.get("doc"), "tm": r.get("tm") or r.get("vehicle") or "",
            "page": r.get("page"), "page_url": r.get("page_url"), "vehicle": veh})
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
        # Vehicle annotation (never a filter): blank/missing vehicles contribute nothing to the
        # identity set, so a group with one real vehicle label + some unlabeled rows still reads as
        # single-vehicle, not ambiguous.
        distinct_vehicles = sorted({v["vehicle"] for v in vals if v["vehicle"]})
        cross_vehicle = len(distinct_vehicles) > 1
        vehicle_label = distinct_vehicles[0] if len(distinct_vehicles) == 1 else ""
        # keep one representative citation per distinct value
        reps, seen = [], set()
        for v in sorted(vals, key=lambda x: x["f"]):
            key = round(v["f"], 6)
            if key not in seen:
                seen.add(key)
                reps.append({"value": v["value"], "doc": v["doc"], "tm": v["tm"],
                             "page": v["page"], "page_url": v["page_url"], "vehicle": v["vehicle"]})
        out.append({"type": t, "unit": u, "vehicle": vehicle_label, "vehicles": distinct_vehicles,
                    "cross_vehicle": cross_vehicle, "min": lo, "max": hi,
                    "spread_pct": round(spread * 100, 1),
                    "severity": "high" if t in _HIGH else "medium",
                    "n_docs": len(all_docs), "values": reps})
    # Sort: severity first (unchanged), THEN vehicle-confirmed before cross-vehicle-ambiguous (a
    # human should see a confirmed same-vehicle disagreement before an ambiguous multi-vehicle one of
    # the same severity), THEN spread. Without this, an ambiguous cross_vehicle=True false-positive-
    # shaped hit can outrank and crowd out a confirmed real conflict in a UI that only shows the top N
    # (adversarial review caught this: a spurious 75%-spread 3-vehicle pooling sorted above a genuine
    # 30%-spread single-vehicle conflict before this tiebreak was added).
    out.sort(key=lambda c: (0 if c["severity"] == "high" else 1, 1 if c["cross_vehicle"] else 0, -c["spread_pct"]))
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
    # all six rows share vehicle="HMMWV" -- these are meant to represent two manuals for the SAME
    # vehicle, so the torque disagreement below is the real, intended positive case (same equipment,
    # disagreeing values), not a cross-vehicle false positive.
    rows = [
        {"type": "torque", "unit": "ft-lb", "value": "35 ft-lb", "doc": "10", "tm": "TM-A", "vehicle": "HMMWV", "page": 12},
        {"type": "torque", "unit": "ft-lb", "value": "50 ft-lb", "doc": "22", "tm": "TM-B", "vehicle": "HMMWV", "page": 4},
        {"type": "torque", "unit": "ft-lb", "value": "35 ft-lb", "doc": "10", "tm": "TM-A", "vehicle": "HMMWV", "page": 12},  # dup, same doc
        {"type": "length", "unit": "in", "value": "7.50 in", "doc": "10", "tm": "TM-A", "vehicle": "HMMWV", "page": 3},
        {"type": "length", "unit": "in", "value": "7.51 in", "doc": "22", "tm": "TM-B", "vehicle": "HMMWV", "page": 9},        # within tol
        {"type": "pressure", "unit": "psi", "value": "30 psi", "doc": "10", "tm": "TM-A", "vehicle": "HMMWV", "page": 1},      # single doc
    ]
    cs = detect(rows)
    assert len(cs) == 1, cs                                  # only the torque disagreement qualifies
    c = cs[0]
    assert c["type"] == "torque" and c["severity"] == "high", c
    assert c["vehicle"] == "HMMWV" and c["vehicles"] == ["HMMWV"] and c["cross_vehicle"] is False, c
    assert c["min"] == 35 and c["max"] == 50 and c["n_docs"] == 2, c
    assert len(c["values"]) == 2, c
    print("conflicts detect OK -> %s %s (%s): %s vs %s across %d docs (%.0f%% apart, %s)"
          % (c["type"], c["unit"], c["vehicle"], c["values"][0]["value"], c["values"][1]["value"],
             c["n_docs"], c["spread_pct"], c["severity"]))

    # no conflict when everyone agrees
    agree = [{"type": "torque", "unit": "ft-lb", "value": "35", "doc": "1", "vehicle": "HMMWV", "page": 1},
             {"type": "torque", "unit": "ft-lb", "value": "35", "doc": "2", "vehicle": "HMMWV", "page": 2}]
    assert detect(agree) == [], "false positive"
    print("conflicts no-false-positive OK")

    # Pass-1 regression guard: a genuinely different-vehicle pooling (e.g. the real WINCH INSTALLATION
    # case) must still be SURFACED (never silently dropped), but marked cross_vehicle so a human knows
    # to double-check it before trusting it like a confirmed single-vehicle hit.
    cross_vehicle_rows = [
        {"type": "torque", "unit": "ft-lb", "value": "35 ft-lb", "doc": "100", "tm": "TM-X", "vehicle": "HMMWV", "page": 1},
        {"type": "torque", "unit": "ft-lb", "value": "60 ft-lb", "doc": "200", "tm": "TM-Y", "vehicle": "M35A2", "page": 1},
    ]
    cv_cs = detect(cross_vehicle_rows)
    assert len(cv_cs) == 1, cv_cs                             # surfaced, not dropped
    assert cv_cs[0]["cross_vehicle"] is True, cv_cs[0]
    assert cv_cs[0]["vehicles"] == ["HMMWV", "M35A2"] and cv_cs[0]["vehicle"] == "", cv_cs[0]
    print("conflicts cross-vehicle-surfaced-not-dropped OK")

    # THE SAFETY REGRESSION THIS PASS FIXES: the SAME real vehicle filed under two different ingest-
    # folder spellings (exactly "HMMWV" vs "TM,S HUMMERS,ALL" -- both real folder names in this corpus)
    # must NOT be silently missed just because the spellings differ. Pass-1's hard vehicle split
    # returned [] for this (confirmed live against the real corpus before reverting); this pass must
    # return the conflict, annotated cross_vehicle=True since the code can't know these are the same
    # real vehicle -- surfaced for a human to confirm, never invisible.
    same_real_vehicle_different_spelling = [
        {"type": "torque", "unit": "ft-lb", "value": "35 ft-lb", "doc": "1", "tm": "TM-A", "vehicle": "HMMWV", "page": 10},
        {"type": "torque", "unit": "ft-lb", "value": "50 ft-lb", "doc": "2", "tm": "TM-B", "vehicle": "TM,S HUMMERS,ALL", "page": 20},
    ]
    srv_cs = detect(same_real_vehicle_different_spelling)
    assert len(srv_cs) == 1, "a genuine cross-manual disagreement must never be silently dropped: " + repr(srv_cs)
    assert srv_cs[0]["cross_vehicle"] is True, srv_cs[0]
    print("conflicts same-real-vehicle-different-spelling-not-silently-dropped OK")

    # same-vehicle positive case must keep working with a different type too: same vehicle, 2 distinct
    # docs, values spanning past rel_tol -> still flagged, cross_vehicle False.
    same_vehicle_positive = [
        {"type": "pressure", "unit": "psi", "value": "30 psi", "doc": "300", "tm": "TM-P1", "vehicle": "M35A2", "page": 1},
        {"type": "pressure", "unit": "psi", "value": "45 psi", "doc": "400", "tm": "TM-P2", "vehicle": "M35A2", "page": 2},
    ]
    same_cs = detect(same_vehicle_positive)
    assert len(same_cs) == 1, same_cs
    assert same_cs[0]["vehicle"] == "M35A2" and same_cs[0]["cross_vehicle"] is False and same_cs[0]["n_docs"] == 2, same_cs[0]
    print("conflicts same-vehicle-still-flagged OK")

    # internal-whitespace normalization: repeated internal spaces (e.g. from an OCR'd or hand-typed
    # folder name) must collapse to the same label -- "M35A2  DUMP TRUCK" (double space) and
    # "M35A2 DUMP TRUCK" (single space) are the same vehicle label, not two different ones. NOTE: this
    # only collapses REPEATED whitespace; a token-boundary difference like "HUMMERS,ALL" (no space)
    # vs "HUMMERS, ALL" (one space) is a different, harder normalization problem this does NOT solve --
    # but per this pass's design that's now a "cross_vehicle=True, needs a human to confirm" outcome,
    # never a silent drop (see same-real-vehicle-different-spelling case above, which uses exactly that
    # harder case and is still correctly surfaced).
    whitespace_variant = [
        {"type": "torque", "unit": "ft-lb", "value": "35 ft-lb", "doc": "1", "vehicle": "M35A2  DUMP TRUCK", "page": 1},
        {"type": "torque", "unit": "ft-lb", "value": "50 ft-lb", "doc": "2", "vehicle": "M35A2 DUMP TRUCK", "page": 2},
    ]
    ws_cs = detect(whitespace_variant)
    assert len(ws_cs) == 1 and ws_cs[0]["cross_vehicle"] is False, ws_cs
    print("conflicts internal-whitespace-normalized OK")

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
