"""commonality.py -- FLEET COMMONALITY finder (roadmap #61, logistics). Which parts are shared across the
vehicles in the corpus? A part used on many platforms is worth stocking deep and is a safe substitution
candidate; a one-platform part is not. Given a part it lists the vehicles that use it; given the fleet it
finds the most-shared parts.

analyze() is pure and unit-testable; for_part()/most_shared() query the parts index. Read-only."""

from __future__ import annotations
import sqlite3


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
    return {"query": q, "vehicles": vehicles, "n": len(vehicles),
            "commonality": ("fleet-common" if len(vehicles) >= 3 else ("shared" if len(vehicles) == 2 else "single-platform"))}


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
    print("commonality self-test PASS")

# END OF FILE
