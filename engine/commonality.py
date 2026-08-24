"""commonality.py -- FLEET COMMONALITY finder (roadmap #61, logistics). Which parts are shared across the
vehicles in the corpus? A part used on many platforms is worth stocking deep and is a safe substitution
candidate; a one-platform part is not. Given a part it lists the vehicles that use it; given the fleet it
finds the most-shared parts.

analyze() is pure and unit-testable; for_part()/most_shared() query the parts index. Read-only."""

from __future__ import annotations
import os
import sqlite3
import tempfile


def analyze(occurrences):
    """occurrences: [{key, vehicle}] (key = NSN or part number, vehicle = platform/manual).
    -> {by_key: per-key {vehicles list, n}, shared: list of {key, vehicles, n}} sorted by breadth."""
    by_key = {}
    for o in occurrences or []:
        k = (o.get("key") or "").strip().upper()
        v = (o.get("vehicle") or "").strip()
        if not k or not v:
            continue
        by_key.setdefault(k, set()).add(v)
    out = {k: {"vehicles": sorted(vs), "n": len(vs)} for k, vs in by_key.items()}
    shared = sorted(({"key": k, "vehicles": d["vehicles"], "n": d["n"]} for k, d in out.items() if d["n"] >= 2),
                    key=lambda x: -x["n"])
    return {"by_key": out, "shared": shared, "n_keys": len(out), "n_shared": len(shared)}


def for_part(db_path, q, limit=60):
    """Vehicles/manuals that reference a given NSN or part number. Best-effort over the parts index."""
    q = (q or "").strip()
    if len(q) < 3:
        return {"query": q, "vehicles": []}
    occ = []
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True); con.row_factory = sqlite3.Row
        # try a parts table joined to documents; tolerate schema differences
        for sql in (
            "SELECT DISTINCT d.vehicle AS vehicle, d.tm_number AS tm FROM parts p JOIN documents d ON d.id=p.document_id "
            "WHERE p.nsn=? OR p.part_number=? LIMIT ?",
            "SELECT DISTINCT d.vehicle AS vehicle, d.tm_number AS tm FROM part_rows p JOIN documents d ON d.id=p.doc_id "
            "WHERE p.nsn=? OR p.pn=? LIMIT ?",
        ):
            try:
                rows = con.execute(sql, (q, q, limit)).fetchall()
                if rows:
                    occ = [{"vehicle": r["vehicle"] or r["tm"], "tm": r["tm"]} for r in rows if (r["vehicle"] or r["tm"])]
                    break
            except Exception:
                continue
        con.close()
    except Exception:
        pass
    vehicles = sorted({o["vehicle"] for o in occ if o["vehicle"]})
    n = len(vehicles)
    if n == 0:
        # no record of this NSN/part-number in the index at all -- a data-completeness gap, NOT
        # the same thing as "confirmed single-platform" (which requires an actual match). Keep
        # these distinguishable so a caller can't read n=0 as a fact about the part. See
        # serviceability.assess()'s "unknown"+"reason" pattern for the precedent this follows.
        commonality, reason = "unknown", "no match in parts index for this NSN/part number"
    elif n == 1:
        commonality, reason = "single-platform", None
    elif n == 2:
        commonality, reason = "shared", None
    else:
        commonality, reason = "fleet-common", None
    out = {"query": q, "vehicles": vehicles, "n": n, "commonality": commonality}
    if reason:
        out["reason"] = reason
    return out


# --------------------------------------------------------------------------- #
# self-test: `python commonality.py`                                          #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    occ = [
        {"key": "5305-01-674-1467", "vehicle": "HMMWV"},
        {"key": "5305-01-674-1467", "vehicle": "M35"},
        {"key": "5305-01-674-1467", "vehicle": "M915"},     # shared across 3 -> fleet-common
        {"key": "2920-01-111-2222", "vehicle": "HMMWV"},    # single platform
        {"key": "5310-00-045-3299", "vehicle": "M35"},
        {"key": "5310-00-045-3299", "vehicle": "M35"},      # dup vehicle -> still 1
    ]
    a = analyze(occ)
    assert a["by_key"]["5305-01-674-1467"]["n"] == 3, a["by_key"]["5305-01-674-1467"]
    assert a["by_key"]["2920-01-111-2222"]["n"] == 1, a
    assert a["by_key"]["5310-00-045-3299"]["n"] == 1, a     # dup collapsed
    assert a["n_shared"] == 1 and a["shared"][0]["key"] == "5305-01-674-1467", a["shared"]
    print("analyze OK -> %d keys, %d shared; top shared across %d vehicles"
          % (a["n_keys"], a["n_shared"], a["shared"][0]["n"]))
    print("   top:", a["shared"][0]["vehicles"])
    assert analyze([])["n_keys"] == 0

    # for_part(): the n=0 (not-in-index) case must NOT be labelled the same as the n=1
    # (confirmed single-platform) case -- that was the bug. Build a tiny throwaway index.
    fd, db = tempfile.mkstemp(suffix=".db"); os.close(fd)
    try:
        con = sqlite3.connect(db)
        con.executescript(
            "CREATE TABLE documents(id INTEGER PRIMARY KEY, vehicle TEXT, tm_number TEXT);"
            "CREATE TABLE parts(document_id INTEGER, nsn TEXT, part_number TEXT);"
            "INSERT INTO documents VALUES (1,'HMMWV','TM-1'), (2,'M35','TM-2');"
            "INSERT INTO parts VALUES (1,'5305-01-674-1467',NULL);"
        )
        con.commit(); con.close()

        zero = for_part(db, "9999-99-999-9999")
        assert zero["n"] == 0 and zero["vehicles"] == [], zero
        assert zero["commonality"] != "single-platform", zero      # the actual bug
        assert zero["commonality"] == "unknown" and zero.get("reason"), zero

        one = for_part(db, "5305-01-674-1467")
        assert one["n"] == 1 and one["vehicles"] == ["HMMWV"], one
        assert one["commonality"] == "single-platform", one
        assert "reason" not in one, one

        assert for_part(db, "xx")["vehicles"] == []                # too short, no DB hit at all
    finally:
        try:
            os.remove(db)
        except OSError:
            pass
    print("for_part OK -> n=0 -> %r (distinct from n=1 -> %r)" % (zero["commonality"], one["commonality"]))
    print("commonality self-test PASS")

# END OF FILE
