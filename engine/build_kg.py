#!/usr/bin/env python3
"""THE VIEWER -- KNOWLEDGE-GRAPH BUILDER (v1.3.0). Assembles the graph triples from viewer.db + the sidecars and writes
index/kg.db (via kg.build). Read-only on every source; append-only sidecar (R1/R6). Each source is guarded so a missing
table/sidecar just contributes fewer edges. Run host-side (BUILD-KG.bat) after the other builders. Sources:
  documents            -> vehicle nodes + (doc)-in_vehicle->(vehicle)
  masterfile.db        -> (vehicle)-has_dimension->(type value unit)   [authoritative dims]
  figureparts (sample) -> (part)-on_figure->(figure) + (part)-in_vehicle->(vehicle) + (part)-has_nsn->(nsn)
"""
import os, sys, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kg  # noqa: E402

ROOT = os.path.dirname(HERE)
DB = os.environ.get("VIEWER_DB", os.path.join(ROOT, "index", "viewer.db"))
MASTER = os.environ.get("MASTER_DB", os.path.join(ROOT, "index", "masterfile.db"))
KG = os.environ.get("KG_DB", os.path.join(ROOT, "index", "kg.db"))


def main():
    if not os.path.exists(DB):
        print("viewer.db not found at", DB); return 2
    triples = []

    # documents -> vehicles
    try:
        con = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
        for did, veh, tm in con.execute("SELECT id, COALESCE(vehicle,''), COALESCE(tm_number,'') FROM documents"):
            if veh:
                triples.append(("document", tm or ("doc %s" % did), "in_vehicle", "vehicle", veh))
        con.close()
    except Exception as e:
        print("documents source skipped:", e)

    # masterfile -> vehicle has_dimension (authoritative filtered rows only)
    if os.path.exists(MASTER):
        try:
            con = sqlite3.connect("file:%s?mode=ro" % MASTER, uri=True)
            for subj, ty, unit, val in con.execute(
                    "SELECT subject_label, type, unit, value FROM master_filtered WHERE authoritative=1"):
                if subj and val:
                    triples.append(("vehicle", subj, "has_dimension", "spec", "%s %s %s" % (ty, val, unit)))
            con.close()
        except Exception as e:
            print("masterfile source skipped:", e)
    else:
        print("masterfile.db absent — run BUILD-MASTERFILE.bat for dimension edges.")

    # figureparts sample -> part/figure/nsn/vehicle (best-effort; needs the parts index)
    # Medium finding #27: this deliberately samples the first 400 docs' page 1 only, capped at
    # 5000 parts -- cheap, but nothing downstream could previously tell "this edge doesn't exist"
    # apart from "this edge exists but is outside the sample." kg_meta below records the actual
    # sample size against the corpus total so kg.stats()/`  /api/kg` can disclose it.
    kg_meta = {}
    try:
        import figureparts, partlocate
        con = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
        total_docs = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        docs = [r[0] for r in con.execute("SELECT id FROM documents LIMIT 400")]
        con.close()
        seen = 0
        for did in docs:
            try:
                # a light probe: figureparts wants doc+page; sample page 1 (cheap). Real coverage grows host-side.
                fp = figureparts.parts_on(DB, did, 1, limit=40)
            except Exception:
                continue
            for pt in (fp.get("parts") or []):
                nm = pt.get("name") or pt.get("part_number") or pt.get("nsn")
                if not nm:
                    continue
                triples.append(("part", nm, "on_figure", "figure", "doc%s p1" % did))
                if pt.get("nsn"):
                    triples.append(("part", nm, "has_nsn", "nsn", pt["nsn"]))
                seen += 1
            if seen > 5000:
                break
        kg_meta = {
            "figureparts_docs_sampled": str(len(docs)), "figureparts_docs_total": str(total_docs),
            "figureparts_pages_per_doc": "1 (page 1 only)", "figureparts_parts_cap": "5000",
            "figureparts_parts_seen": str(seen),
        }
        print("  figureparts coverage: %d/%d docs sampled, page 1 only, %d parts (cap 5000)"
              % (len(docs), total_docs, seen))
    except Exception as e:
        print("figureparts source skipped:", e)

    r = kg.build(KG, triples, meta=kg_meta)
    print("Knowledge graph built -> %s" % KG)
    print("  %d nodes, %d edges from %d triples" % (r["nodes"], r["edges"], len(triples)))
    print("  by type:", kg.stats(KG)["by_type"])
    print("Read-only on sources; append-only sidecar. /kg + /api/kg query it offline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# END OF FILE
