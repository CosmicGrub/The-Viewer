#!/usr/bin/env python3
"""THE VIEWER -- EXTERNAL ENRICHMENT CRAWLER (v1.1.2). OPT-IN, HOST-RUN, ONLINE.

Fills BLANKS in the corpus's dimensional data by cross-referencing the open internet -- the corpus stays authoritative.
For each vehicle/subject that is MISSING a dimension type (per find_gaps), it searches the Internet Archive full-text
corpus, pulls the item's text layer, extracts measurements with the SAME measures engine, and records ONLY the missing
types into the append-only enrich.db sidecar with full provenance (source, URL, Wayback timestamp, fetched time).

This is the ONLY component that touches the network, and it is never run by the server -- the running app only READS
enrich.db offline. Resumable (skips subjects already done). Polite: rate-limited. Nothing in the corpus is modified
(R1/R6).

  python build_enrich.py [--limit N] [--rows R] [--sleep S] [--subject "NAME"]
"""
import os, sys, time, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import enrich  # noqa: E402

DB = os.environ.get("VIEWER_DB", os.path.join(os.path.dirname(HERE), "index", "viewer.db"))
MEAS = os.environ.get("MEASURES_DB", os.path.join(os.path.dirname(HERE), "index", "measures.db"))
ENR = os.environ.get("ENRICH_DB", os.path.join(os.path.dirname(HERE), "index", "enrich.db"))


def already_done(subject):
    import sqlite3
    if not os.path.exists(ENR):
        return set()
    try:
        con = sqlite3.connect("file:%s?mode=ro" % ENR, uri=True)
        s = {r[0] for r in con.execute("SELECT subject FROM ext_done")}
        con.close(); return s
    except Exception:
        return set()


SEEDS = os.environ.get("ENRICH_SEEDS", os.path.join(os.path.dirname(HERE), "index", "enrich_seeds.txt"))


def _load_search_fn():
    """Optional web-search provider so the crawler can discover MANY links per subject. Host-pluggable and
    offline-by-default: if `engine/enrich_search.py` exists with `search(query, limit) -> [url,...]`, use it; else None.
    (Keeps the app itself free of any bundled search dependency.)"""
    try:
        import enrich_search  # user-supplied, optional
        return enrich_search.search
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=80)
    ap.add_argument("--rows", type=int, default=4)
    ap.add_argument("--sleep", type=float, default=2.0)
    ap.add_argument("--subject", default=None)
    ap.add_argument("--save", action="store_true", help="Save Page Now for links lacking a Wayback snapshot")
    ap.add_argument("--maxlinks", type=int, default=12, help="max candidate links routed through Wayback per subject")
    a = ap.parse_args()
    search_fn = _load_search_fn()

    if not os.path.exists(DB):
        print("viewer.db not found at", DB); return 2
    try:
        import measures  # noqa: F401  (make sure the extractor is importable before we go online)
    except Exception as e:
        print("measures.py not importable (%s) -- cannot extract external data." % e); return 2

    print("Finding gaps in the corpus's dimensional data (corpus is authoritative)...")
    gaps = enrich.find_gaps(DB, MEAS if os.path.exists(MEAS) else None, limit=10000)
    if a.subject:
        gaps = [g for g in gaps if a.subject.lower() in g["subject"]]
    done = already_done(a.subject)
    todo = [g for g in gaps if g["subject"] not in done][:a.limit]
    print("subjects with gaps: %d  |  to crawl this run: %d" % (len(gaps), len(todo)))
    if not todo:
        print("Nothing to do (all gap-subjects already enriched, or none found)."); return 0

    total_fills = 0; total_links = 0
    for i, g in enumerate(todo, 1):
        want = set(g["gaps"]) | set(g["inconclusive"])
        label = g["label"]
        print("[%d/%d] %s  -- filling: %s" % (i, len(todo), label, ", ".join(sorted(want)) or "(none)"))
        query = "%s technical manual specifications dimensions" % label
        found_here = 0

        # (A) HIGH-YIELD: Internet Archive full-text items (text pulled directly)
        for ident in enrich.ia_search(query, rows=a.rows):
            txt = enrich.ia_fulltext(ident)
            if txt:
                rows = enrich.extract_external(txt)
                prov = {"source": "internet_archive", "source_url": "https://archive.org/details/%s" % ident,
                        "orig_url": "https://archive.org/details/%s" % ident, "wayback_ts": "", "confidence": 0.55}
                n = enrich.record(ENR, g["subject"], label, rows, prov, only_types=want)
                found_here += n; total_fills += n
            time.sleep(a.sleep)

        # (B) MANY LINKS routed through the WAYBACK MACHINE: web-search results + subject-scoped seeds.
        # Every link is pinned to an archived snapshot (created via Save Page Now if --save and none exists).
        links = enrich.web_links(query, search_fn, limit=a.maxlinks) + enrich.seed_links(SEEDS, subject=label)
        seen_links = set()
        for url in links:
            if not url or url in seen_links:
                continue
            seen_links.add(url); total_links += 1
            text, wb_url, wb_ts = enrich.fetch_via_wayback(url, save=a.save)
            if not text:
                time.sleep(a.sleep); continue
            rows = enrich.extract_external(text)
            prov = {"source": "wayback", "source_url": wb_url or url, "orig_url": url,
                    "wayback_ts": wb_ts, "confidence": 0.5}
            n = enrich.record(ENR, g["subject"], label, rows, prov, only_types=want)
            found_here += n; total_fills += n
            time.sleep(a.sleep)

        # mark subject done even if nothing found (so it's skipped next run)
        enrich.record(ENR, g["subject"], label, [], {"source": "", "source_url": "", "orig_url": ""}, only_types=want)
        print("    +%d external fills  (%d links routed through Wayback)" % (found_here, len(seen_links)))
    print("DONE: %d subjects, %d links routed through Wayback, +%d external gap-fills -> %s"
          % (len(todo), total_links, total_fills, ENR))
    print("All external values are badged 'external-unconfirmed' with provenance (archived Wayback URL + timestamp);")
    print("the corpus remains authoritative and untouched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# END OF FILE
