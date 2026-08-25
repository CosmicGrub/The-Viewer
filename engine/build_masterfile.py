#!/usr/bin/env python3
"""THE VIEWER -- MASTERFILE BUILDER (v1.2.0). Consolidates the corpus measurements (index/measures.db, authoritative),
the external gap-fills (index/enrich.db, supplemental), and -- when present -- self-grounded/OCR-cross-checked
vision-language extractions (index/pageqa.db, plan item 13) into ONE congruent Masterfile: index/masterfile.db plus a
human-readable docs/MASTERFILE.md. Read-only on the sources; the Masterfile is an append-only rebuildable sidecar
(R1/R6). No external links are carried in -- corpus rows keep their authoritative page cite, external provenance stays
inside enrich.db. Run host-side (BUILD-MASTERFILE.bat) after BUILD-MEASURES (and optionally ENRICH / BUILD-PAGEQA)."""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import masterfile  # noqa: E402

ROOT = os.path.dirname(HERE)
DB = os.environ.get("VIEWER_DB", os.path.join(ROOT, "index", "viewer.db"))
MEAS = os.environ.get("MEASURES_DB", os.path.join(ROOT, "index", "measures.db"))
ENR = os.environ.get("ENRICH_DB", os.path.join(ROOT, "index", "enrich.db"))
PAGEQA = os.environ.get("PAGEQA_DB", os.path.join(ROOT, "index", "pageqa.db"))
MASTER = os.environ.get("MASTER_DB", os.path.join(ROOT, "index", "masterfile.db"))
MD = os.path.join(ROOT, "docs", "MASTERFILE.md")


def main():
    if not os.path.exists(DB):
        print("viewer.db not found at", DB); return 2
    have_m = os.path.exists(MEAS); have_e = os.path.exists(ENR); have_p = os.path.exists(PAGEQA)
    print("Sources: measures.db=%s  enrich.db=%s  pageqa.db=%s" % (
        "yes" if have_m else "MISSING (run BUILD-MEASURES.bat)",
        "yes" if have_e else "none (run ENRICH.bat to add external fills)",
        "yes" if have_p else "none (run BUILD-PAGEQA.bat to add vlm-verified corroboration)"))
    summ = masterfile.build(DB, MEAS if have_m else None, ENR if have_e else None, MASTER, md_path=MD,
                             pageqa_db=PAGEQA if have_p else None)
    # build()'s own return dict deliberately does NOT carry a vlm-verified count (masterfile.py's own
    # build() docstring/comment: test_medium_fixes.py's diff-oracle compares that exact dict via plain
    # `!=` against a from-scratch reference dict that predates pageqa.db) -- read it from master_meta
    # instead, same place any other caller would.
    vlmqa_raw = 0
    try:
        import sqlite3
        _c = sqlite3.connect("file:%s?mode=ro" % MASTER, uri=True)
        _r = _c.execute("SELECT v FROM master_meta WHERE k='vlmqa_raw'").fetchone()
        _c.close()
        vlmqa_raw = int(_r[0]) if _r else 0
    except Exception:
        pass
    print("Masterfile built -> %s" % MASTER)
    print("  subjects: %d | raw values: %d (corpus %d / external %d / vlm-verified %d) | filtered rows: %d" %
          (summ["subjects"], summ["raw"], summ["corpus"], summ["external"], vlmqa_raw, summ["filtered"]))
    print("  human-readable export -> %s" % MD)
    print("Corpus stays authoritative; no external links surfaced. /master serves this consolidated view.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# END OF FILE
