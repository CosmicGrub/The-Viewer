#!/usr/bin/env python3
"""Build a SIDECAR correlations DB from viewer.db — additive & rollbackable (R1/R6).

It NEVER writes to viewer.db. It derives, from the read-only main index, the correlative
links the flat tables imply but don't surface:
  * nsn_platforms  : every NSN -> the distinct vehicles/docs it appears in (interchangeability)
  * niin_aliases   : same NIIN written as different NSN strings (format-drift unification)
  * supersession_held : superseded->current pairs where we actually hold the current item
Delete index/correlations.db to roll back. Re-run any time to rebuild.
Usage: python build_correlations.py [--db index/viewer.db] [--out index/correlations.db]"""
import sqlite3, sys, re, time, os

def norm(n): return re.sub(r"\D", "", n or "")
def niin(n):
    d = norm(n)
    return d[4:13] if len(d) >= 13 else (d if len(d) == 9 else d[-9:] if len(d) > 9 else d)

def main():
    db = "index/viewer.db"; out = "index/correlations.db"
    a = sys.argv[1:]
    for i, x in enumerate(a):
        if x == "--db" and i+1 < len(a): db = a[i+1]
        if x == "--out" and i+1 < len(a): out = a[i+1]
    src = sqlite3.connect("file:%s?mode=ro" % db, uri=True); src.row_factory = sqlite3.Row
    if os.path.exists(out): os.remove(out)
    dst = sqlite3.connect(out)
    dst.execute("PRAGMA journal_mode=TRUNCATE"); dst.execute("PRAGMA synchronous=OFF")
    dst.executescript("""
        CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT);
        CREATE TABLE nsn_platforms(nsn TEXT PRIMARY KEY, n_vehicles INT, vehicles TEXT, n_docs INT);
        CREATE TABLE niin_aliases(niin TEXT PRIMARY KEY, n INT, variants TEXT);
        CREATE TABLE supersession_held(old_nsn TEXT, current_token TEXT, current_niin TEXT);
        CREATE INDEX ix_sup_old ON supersession_held(old_nsn);
    """)

    t = time.time()
    # nsn -> vehicles + docs
    nsn_veh = {}; nsn_doc = {}
    for r in src.execute("select nsn,vehicle,document_id from parts where nsn is not null and nsn<>''"):
        nsn_veh.setdefault(r["nsn"], set()).add((r["vehicle"] or "").strip() or "?")
        nsn_doc.setdefault(r["nsn"], set()).add(r["document_id"])
    rows = []
    for nsn, vs in nsn_veh.items():
        vs2 = sorted(v for v in vs if v and v != "?")
        rows.append((nsn, len(vs2), " | ".join(vs2[:40]), len(nsn_doc.get(nsn, set()))))
    dst.executemany("INSERT INTO nsn_platforms VALUES(?,?,?,?)", rows)
    shared = sum(1 for r in rows if r[1] > 1)
    print("nsn_platforms       :", len(rows), "rows;", shared, "span >1 vehicle (%.1fs)" % (time.time()-t), flush=True)

    # niin -> distinct nsn variants
    t = time.time()
    by_niin = {}
    for nsn in nsn_veh.keys(): by_niin.setdefault(niin(nsn), set()).add(nsn)
    al = [(k, len(v), " | ".join(sorted(v))) for k, v in by_niin.items() if len(v) > 1]
    dst.executemany("INSERT INTO niin_aliases VALUES(?,?,?)", al)
    print("niin_aliases        :", len(al), "format-drift groups (%.1fs)" % (time.time()-t), flush=True)

    # supersession held in index (by NIIN)
    t = time.time()
    part_niin = set(by_niin.keys())
    sup_rows = []
    for r in src.execute("select nsn,superseded from ref_nsn where superseded is not null and superseded<>''"):
        for tok in re.split(r"[,;/ ]+", r["superseded"]):
            tok = tok.strip()
            if len(norm(tok)) >= 9 and niin(tok) in part_niin:
                sup_rows.append((r["nsn"], tok, niin(tok)))
    dst.executemany("INSERT INTO supersession_held VALUES(?,?,?)", sup_rows)
    print("supersession_held   :", len(sup_rows), "old->current pairs we hold (%.1fs)" % (time.time()-t), flush=True)

    src_fp = src.execute("select count(*) from parts").fetchone()[0]
    for k, v in [("built_at", time.strftime("%Y-%m-%d %H:%M:%S")), ("source_db", os.path.basename(db)),
                 ("source_parts_rows", str(src_fp)), ("schema", "1")]:
        dst.execute("INSERT INTO meta VALUES(?,?)", (k, v))
    dst.commit(); dst.execute("PRAGMA optimize"); dst.close()
    print("WROTE", out, os.path.getsize(out), "bytes", flush=True)

if __name__ == "__main__":
    main()
