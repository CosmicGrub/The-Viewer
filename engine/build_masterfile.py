#!/usr/bin/env python3
"""THE VIEWER -- MASTERFILE BUILDER (v1.1.4). Consolidates the corpus measurements (index/measures.db, authoritative)
and the external gap-fills (index/enrich.db, supplemental) into ONE congruent Masterfile: index/masterfile.db plus a
human-readable docs/MASTERFILE.md. Read-only on the sources; the Masterfile is an append-only rebuildable sidecar
(R1/R6). No external links are carried in -- corpus rows keep their authoritative page cite, external provenance stays
inside enrich.db. Run host-side (BUILD-MASTERFILE.bat) after BUILD-MEASURES (and optionally ENRICH)."""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import masterfile  # noqa: E402

ROOT = os.path.dirname(HERE)
DB = os.environ.get("VIEWER_DB", os.path.join(ROOT, "index", "viewer.db"))
MEAS = os.environ.get("MEASURES_DB", os.path.join(ROOT, "index", "measures.db"))
ENR = os.environ.get("ENRICH_DB", os.path.join(ROOT, "index", "enrich.db"))
MASTER = os.environ.get("MASTER_DB", os.path.join(ROOT, "index", "masterfile.db"))
MD = os.path.join(ROOT, "docs", "MASTERFILE.md")


def main():
    if not os.path.exists(DB):
        print("viewer.db not found at", DB); return 2
    have_m = os.path.exists(MEAS); have_e = os.path.exists(ENR)
    print("Sources: measures.db=%s  enrich.db=%s" % ("yes" if have_m else "MISSING (run BUILD-MEASURES.bat)",
                                                      "yes" if have_e else "none (run ENRICH.bat to add external fills)"))
    summ = masterfile.build(DB, MEAS if have_m else None, ENR if have_e else None, MASTER, md_path=MD)
    print("Masterfile built -> %s" % MASTER)
    print("  subjects: %d | raw values: %d (corpus %d / external %d) | filtered rows: %d" %
          (summ["subjects"], summ["raw"], summ["corpus"], summ["external"], summ["filtered"]))
    print("  human-readable export -> %s" % MD)
    print("Corpus stays authoritative; no external links surfaced. /master serves this consolidated view.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# END OF FILE
