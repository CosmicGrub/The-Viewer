#!/usr/bin/env python3
"""Unit tests for engine/build_keywords.py's run() -- extracted from main() during the full-codebase
audit that wired it into viewer_ingest.py's enrich_flis() (see test_ingest_routes.py's "e2e keywords
wiring" checks for the integration side of that). Never touches the real engine/keywords.json: every
call here passes an explicit `out=` under a temp dir. Pure stdlib runner."""
import json
import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_keywords as BK


def _mkdb(rows):
    """rows: list of (nsn, item_name, description). Returns the db path."""
    d = tempfile.mkdtemp(prefix="bk_test_db_")
    db = os.path.join(d, "viewer.db")
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE ref_nsn(nsn TEXT, item_name TEXT, description TEXT)")
    con.executemany("INSERT INTO ref_nsn(nsn,item_name,description) VALUES(?,?,?)", rows)
    con.commit(); con.close()
    return db


def run():
    passed, failed = [], []
    def check(name, cond):
        (passed if cond else failed).append(name)

    workdir = tempfile.mkdtemp(prefix="bk_test_out_")

    # --- a fresh custom `out` bootstraps from the curated seed (KW), not an empty groups list ---
    db1 = _mkdb([("5305-01-123-4567", "SCREW,MACHINE",
                  "Made by ACME (CAGE 12345); Also called: cap screw; Unit price $0.12")])
    out1 = os.path.join(workdir, "kw1.json")
    n_groups1, added1, linked1, existed1 = BK.run(db=db1, out=out1)
    check("run(): existed=True for a real db", existed1 is True)
    check("run(): a fresh custom `out` bootstraps from the curated seed (many groups, not just 1)",
          n_groups1 > 5)
    check("run(): one new colloquial group added ('screw,machine' <-> 'cap screw')", added1 == 1)
    check("run(): the new group actually contains both terms", any(
        set(g) >= {"screw,machine", "cap screw"} for g in json.load(open(out1))["groups"]))

    # --- idempotent: re-running against the SAME out must not re-add the same group ---
    n_groups2, added2, linked2, _ = BK.run(db=db1, out=out1)
    check("run(): re-run against the same out is idempotent (added=0, linked=0)",
          added2 == 0 and linked2 == 0)
    check("run(): group count unchanged on the idempotent re-run", n_groups2 == n_groups1)

    # --- a second, distinct colloquial name for the SAME nomenclature LINKS into the existing
    # group rather than creating a duplicate second group ---
    con = sqlite3.connect(db1)
    con.execute("INSERT INTO ref_nsn(nsn,item_name,description) VALUES(?,?,?)",
                ("5305-01-999-0000", "SCREW,MACHINE", "Also called: allen screw"))
    con.commit(); con.close()
    n_groups3, added3, linked3, _ = BK.run(db=db1, out=out1)
    check("run(): a new colloquial name for an EXISTING nomenclature links, doesn't add a new group",
          added3 == 0 and linked3 == 1)
    check("run(): group count still unchanged (linked into the existing group)", n_groups3 == n_groups1)
    grp = next(g for g in json.load(open(out1))["groups"] if "screw,machine" in g)
    check("run(): the existing group now has all three terms", set(grp) >= {"screw,machine", "cap screw", "allen screw"})

    # --- rows with item_name == colloquial name (case/whitespace-insensitive) are skipped: no
    # point grouping a term with itself ---
    db2 = _mkdb([("2540-01-000-0001", "BRACKET", "Also called: bracket")])
    out2 = os.path.join(workdir, "kw2.json")
    _, added4, linked4, _ = BK.run(db=db2, out=out2)
    check("run(): item_name == colloquial name is skipped (no self-referential group)",
          added4 == 0 and linked4 == 0)

    # --- a row missing item_name or with no 'Also called:' text contributes nothing ---
    db3 = _mkdb([("2540-01-000-0002", "", "Also called: whatever"),
                 ("2540-01-000-0003", "GASKET", "Made by ACME (CAGE 12345)")])   # no colloquial text
    out3 = os.path.join(workdir, "kw3.json")
    _, added5, linked5, _ = BK.run(db=db3, out=out3)
    check("run(): rows with no usable nomenclature/colloquial pair contribute nothing",
          added5 == 0 and linked5 == 0)

    # --- offline-safe: a nonexistent db just rewrites the curated seed, existed=False ---
    out4 = os.path.join(workdir, "kw4.json")
    n_groups6, added6, linked6, existed6 = BK.run(db=os.path.join(workdir, "does_not_exist.db"), out=out4)
    check("run(): a missing db is offline-safe (existed=False, no crash)", existed6 is False)
    check("run(): a missing db still rewrites the curated seed (out4 gets the full curated group count)",
          n_groups6 > 5 and added6 == 0 and linked6 == 0)
    check("run(): out4 was actually written to disk", os.path.exists(out4))

    # --- default `out` (module constant KW) is NEVER touched by any call above (every call in this
    # file passes an explicit out= under workdir) -- the real engine/keywords.json must be untouched.
    check("run(): the real engine/keywords.json was never written by this test file",
          not any(os.path.samefile(o, BK.KW) if os.path.exists(o) and os.path.exists(BK.KW) else False
                  for o in (out1, out2, out3, out4)))

    return passed, failed


if __name__ == "__main__":
    p, f = run()
    for n in p: print("PASS", n)
    for n in f: print("FAIL", n)
    print("\n%d passed, %d failed" % (len(p), len(f)))
    sys.exit(1 if f else 0)

# END OF FILE
