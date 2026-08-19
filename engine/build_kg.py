#!/usr/bin/env python3
"""THE VIEWER -- KNOWLEDGE-GRAPH BUILDER (v1.4.0). Assembles the graph triples from viewer.db + the sidecars and writes
index/kg.db (via kg.build). Read-only on every source; append-only sidecar (R1/R6). Each source is guarded so a missing
table/sidecar just contributes fewer edges. Run host-side (BUILD-KG.bat) after the other builders. Sources:
  documents            -> vehicle nodes + (doc)-in_vehicle->(vehicle)
  masterfile.db        -> (vehicle)-has_dimension->(type value unit)   [authoritative dims]
  figureparts (sample) -> (part)-on_figure->(figure) + (part)-in_vehicle->(vehicle) + (part)-has_nsn->(nsn)

USAGE (host):
    python build_kg.py                                # defaults below
    python build_kg.py --sample-docs 8000              # override the figureparts doc sample
    python build_kg.py --parts-cap 100000              # override the figureparts parts cap
    python build_kg.py --sample-docs 8000 --parts-cap 100000
Same "--flag N" / "--flag=N" CLI pattern as build_publog.py's `--sample N` (see that file's usage
comment) -- a host operator who wants a bigger (or, for a quick test build, smaller) figureparts
sample doesn't have to edit source. Every non-default value used still round-trips into kg_meta /
kg.stats()["meta"] (finding #27) exactly like the defaults do, so /api/kg's sample-size disclosure
stays accurate whatever sample size was actually used.
"""
import os, sys, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kg  # noqa: E402

ROOT = os.path.dirname(HERE)
DB = os.environ.get("VIEWER_DB", os.path.join(ROOT, "index", "viewer.db"))
MASTER = os.environ.get("MASTER_DB", os.path.join(ROOT, "index", "masterfile.db"))
KG = os.environ.get("KG_DB", os.path.join(ROOT, "index", "kg.db"))

# v1.4.0: raised 10x from the original 400 docs / 5000 parts (audit finding: that covered only
# ~1% of the ~39,700-document corpus). Each doc costs one cheap read-only single-page `parts_on()`
# probe (indexed by (document_id, page), LIMIT 40) -- 4000 of those is still a low-single-digit-minute
# host job, in line with the other Tier-1 builders' documented runtime budget (BUILD-KG.bat runs
# after BUILD-MASTERFILE.bat, itself a multi-minute job). Override via --sample-docs / --parts-cap
# below for a quicker test build or a deliberately larger one.
DEFAULT_SAMPLE_DOCS = 4000
DEFAULT_PARTS_CAP = 50000


def main(sample_docs=None, parts_cap=None):
    sample_docs = DEFAULT_SAMPLE_DOCS if sample_docs is None else sample_docs
    parts_cap = DEFAULT_PARTS_CAP if parts_cap is None else parts_cap
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
    # Medium finding #27: this deliberately samples only the first `sample_docs` docs' page 1,
    # capped at `parts_cap` parts -- cheap, but nothing downstream could previously tell "this edge
    # doesn't exist" apart from "this edge exists but is outside the sample." kg_meta below records
    # the actual sample size (and the caps actually used, which may differ from the defaults via
    # --sample-docs/--parts-cap) against the corpus total so kg.stats()/`  /api/kg` can disclose it.
    kg_meta = {}
    try:
        import figureparts, partlocate
        con = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
        total_docs = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        docs = [r[0] for r in con.execute("SELECT id FROM documents LIMIT ?", (sample_docs,))]
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
            if seen > parts_cap:
                break
        kg_meta = {
            "figureparts_docs_sampled": str(len(docs)), "figureparts_docs_total": str(total_docs),
            "figureparts_pages_per_doc": "1 (page 1 only)", "figureparts_parts_cap": str(parts_cap),
            "figureparts_parts_seen": str(seen),
        }
        print("  figureparts coverage: %d/%d docs sampled, page 1 only, %d parts (cap %d)"
              % (len(docs), total_docs, seen, parts_cap))
    except Exception as e:
        print("figureparts source skipped:", e)

    r = kg.build(KG, triples, meta=kg_meta)
    print("Knowledge graph built -> %s" % KG)
    print("  %d nodes, %d edges from %d triples" % (r["nodes"], r["edges"], len(triples)))
    print("  by type:", kg.stats(KG)["by_type"])
    print("Read-only on sources; append-only sidecar. /kg + /api/kg query it offline.")
    return 0


def _cli_int(flag, argv, default):
    """Same "--flag N" / "--flag=N" parsing style as build_publog.py's `--sample N`."""
    for a in argv:
        if a.startswith(flag):
            try:
                return int(a.split("=", 1)[1]) if "=" in a else int(argv[argv.index(a) + 1])
            except Exception:
                return default
    return default


if __name__ == "__main__":
    _sample_docs = _cli_int("--sample-docs", sys.argv[1:], DEFAULT_SAMPLE_DOCS)
    _parts_cap = _cli_int("--parts-cap", sys.argv[1:], DEFAULT_PARTS_CAP)
    raise SystemExit(main(sample_docs=_sample_docs, parts_cap=_parts_cap))
# END OF FILE
