#!/usr/bin/env python3
"""THE VIEWER -- sort EVERY document into its side of the house: operator (10) vs mechanic (20).

Reads the live index (read-only), classifies each document with patterns.tm_side() (the Army TM coverage
indicator), and writes index/sides.json: per-document side, the counts, and an 'uncertain' list (documents
with no recognizable coverage code, classified by title wording or defaulted) for your review.

The running app classifies LIVE via the same function, so this script is for the full sorted manifest + an
audit of how the split landed. Read-only; never writes the index (R1/R6). RUN ON WINDOWS (host) -- the
multi-GB index can't be read coherently through a sandbox mount.

  python classify_sides.py [--db PATH] [--json OUT]
"""
import os, sqlite3, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from patterns import tm_side

DEFAULT_DB = os.path.join(HERE, "..", "index", "viewer.db")
DEFAULT_OUT = os.path.join(HERE, "..", "index", "sides.json")


def _connect(db):
    try:
        c = sqlite3.connect("file:%s?mode=ro" % db, uri=True, timeout=60)
        c.execute("PRAGMA query_only=ON"); c.row_factory = sqlite3.Row
        c.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone()
        return c
    except sqlite3.OperationalError:
        c = sqlite3.connect("file:%s?immutable=1" % db, uri=True, timeout=60)
        c.row_factory = sqlite3.Row; return c


def main():
    db = DEFAULT_DB; out = DEFAULT_OUT; args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--db" and i + 1 < len(args): db = args[i + 1]
        if a == "--json" and i + 1 < len(args): out = args[i + 1]
    db = os.path.abspath(db)
    if not os.path.exists(db):
        print("[ERROR] index not found: %s" % db); return 1
    con = _connect(db)
    rows = con.execute("SELECT id, vehicle, tm_number, title, nsn, path FROM documents "
                       "WHERE type LIKE 'pdf%' ORDER BY COALESCE(vehicle,''), COALESCE(tm_number,''), id").fetchall()
    con.close()

    operator, mechanic, both, uncertain = [], [], [], []
    docs = []
    for r in rows:
        cls = tm_side(r["tm_number"] or "", r["title"] or "", r["path"] or "")
        rec = {"doc_id": r["id"], "vehicle": r["vehicle"], "tm": r["tm_number"], "title": r["title"],
               "coverage": cls["coverage"], "operator": cls["operator"], "mechanic": cls["mechanic"],
               "basis": cls["basis"]}
        docs.append(rec)
        if cls["operator"]: operator.append(r["id"])
        if cls["mechanic"]: mechanic.append(r["id"])
        if cls["operator"] and cls["mechanic"]: both.append(r["id"])
        if "undetermined" in cls["basis"] or cls["basis"].startswith("title"):
            uncertain.append({"doc_id": r["id"], "tm": r["tm_number"], "title": r["title"], "basis": cls["basis"]})

    summary = {"documents": len(rows), "operator_side": len(operator), "mechanic_side": len(mechanic),
               "combined_both": len(both), "uncertain": len(uncertain)}
    print("=== Side of the house — sorted %d documents ===" % len(rows))
    print("  operator (10-level): %d" % len(operator))
    print("  mechanic (20-level): %d" % len(mechanic))
    print("  combined (both):     %d" % len(both))
    print("  uncertain (review):  %d" % len(uncertain))
    if uncertain:
        print("\n  --- uncertain (no coverage code; classified by wording/default) ---")
        for u in uncertain[:25]:
            print("   doc %-5s %-26s %s" % (u["doc_id"], (u["tm"] or "")[:26], (u["title"] or "")[:40]))
        if len(uncertain) > 25: print("   ... and %d more (see %s)" % (len(uncertain) - 25, os.path.basename(out)))

    with open(out, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "operator_ids": operator, "mechanic_ids": mechanic,
                   "both_ids": both, "uncertain": uncertain, "documents": docs}, f, indent=2)
    print("\n[wrote %s]" % os.path.abspath(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
