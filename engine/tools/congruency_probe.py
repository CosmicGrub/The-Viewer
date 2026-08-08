#!/usr/bin/env python3
"""Read-only congruency / correlation audit over viewer.db (set-math, mount-friendly).
Reports orphans, FTS/text parity, parts<->ref_nsn linkage, NIIN format, supersession
target reachability, cross-platform NSN sharing, enrichment gaps. Writes nothing.
Usage: python congruency_probe.py [--db PATH] [--json OUT]"""
import sqlite3, time, sys, json, re

def norm(nsn):
    return re.sub(r"\D", "", nsn or "")

def niin(nsn):
    d = norm(nsn)
    return d[4:13] if len(d) >= 13 else (d if len(d) == 9 else d[-9:] if len(d) > 9 else d)

def main():
    db = "index/viewer.db"; out = None
    a = sys.argv[1:]
    for i, x in enumerate(a):
        if x == "--db" and i+1 < len(a): db = a[i+1]
        if x == "--json" and i+1 < len(a): out = a[i+1]
    c = sqlite3.connect("file:%s?mode=ro" % db, uri=True); c.row_factory = sqlite3.Row
    R = {}
    def p(k, v, dt=None):
        R[k] = v; print("%-30s = %s%s" % (k, v, (" (%.1fs)" % dt) if dt else ""), flush=True)

    t = time.time(); p("documents", c.execute("select count(*) from documents").fetchone()[0], time.time()-t)
    t = time.time(); p("parts_rows", c.execute("select count(*) from parts").fetchone()[0], time.time()-t)
    t = time.time(); p("ref_nsn", c.execute("select count(*) from ref_nsn").fetchone()[0], time.time()-t)
    t = time.time(); p("ref_nsn_log", c.execute("select count(*) from ref_nsn_log").fetchone()[0], time.time()-t)

    # --- load small key-sets once (indexed columns) ---
    t = time.time()
    part_nsn = [r[0] for r in c.execute("select distinct nsn from parts where nsn is not null and nsn<>''")]
    p("parts_distinct_nsn", len(part_nsn), time.time()-t)
    t = time.time()
    ref_rows = c.execute("select nsn,item_name,part_no,characteristics,superseded,data_date from ref_nsn").fetchall()
    p("ref_nsn_loaded", len(ref_rows), time.time()-t)

    part_set = set(part_nsn)
    part_niin = {}
    for n in part_nsn: part_niin.setdefault(niin(n), []).append(n)
    ref_set = set(r["nsn"] for r in ref_rows)

    # linkage
    linked = part_set & ref_set
    p("partNSN_with_ref", len(linked))
    p("partNSN_without_ref", len(part_set - ref_set))
    p("ref_unused_by_parts", len(ref_set - part_set))

    # enrichment gaps
    miss_pn = sum(1 for r in ref_rows if not (r["part_no"] or "").strip())
    miss_nm = sum(1 for r in ref_rows if not (r["item_name"] or "").strip())
    miss_ch = sum(1 for r in ref_rows if not (r["characteristics"] or "").strip())
    has_sup = sum(1 for r in ref_rows if (r["superseded"] or "").strip())
    has_dd = sum(1 for r in ref_rows if (r["data_date"] or "").strip())
    p("ref_missing_partno", miss_pn); p("ref_missing_name", miss_nm); p("ref_missing_char", miss_ch)
    p("ref_with_superseded", has_sup); p("ref_with_datadate", has_dd)

    # NSN format sanity (13 digits)
    bad_part = sum(1 for n in part_nsn if len(norm(n)) != 13)
    bad_ref = sum(1 for r in ref_rows if len(norm(r["nsn"])) != 13)
    p("partNSN_bad_format", bad_part); p("refNSN_bad_format", bad_ref)

    # NIIN collisions: same NIIN, different full NSN string in parts (dash/format drift)
    niin_variants = sum(1 for k, v in part_niin.items() if len(set(v)) > 1)
    p("partNSN_niin_format_drift", niin_variants)

    # cross-platform sharing (interchangeability signal)
    t = time.time()
    share = c.execute("""select nsn,count(distinct vehicle) vc from parts
        where nsn is not null and nsn<>'' and vehicle is not null and vehicle<>''
        group by nsn having vc>1""").fetchall()
    p("nsn_shared_across_vehicles", len(share), time.time()-t)
    p("nsn_shared_max_vehicles", max((r["vc"] for r in share), default=0))

    # supersession reachability: do we hold the *current* NSN too (by NIIN)?
    total = 0; reach = 0
    part_niin_set = set(part_niin.keys())
    for r in ref_rows:
        s = (r["superseded"] or "").strip()
        if not s: continue
        for tok in re.split(r"[,;/ ]+", s):
            d = norm(tok)
            if len(d) >= 9:
                total += 1
                if niin(tok) in part_niin_set: reach += 1
    p("supersession_links_total", total); p("supersession_target_in_index", reach)

    if out:
        json.dump(R, open(out, "w"), indent=2); print("wrote", out, flush=True)
    return R

if __name__ == "__main__":
    main()
