#!/usr/bin/env python3
"""THE VIEWER -- EDITION/DUPLICATE-CLUSTER BUILDER. Runs dedup.py's word-shingle Jaccard similarity
across the WHOLE corpus and writes index/dedup.db, so /api/editions can answer "does this document
have other editions in the corpus" without recomputing anything live. Read-only on every source;
append-only sidecar (R1/R6). Same "genuinely needs the whole corpus, not just what a scan touched"
reasoning that keeps build_kg.py/build_conflicts.py separate, host-run batch builders rather than
inline per-scan pipeline stages -- a newly-scanned document has to be compared against every
EXISTING document to tell whether it's a duplicate, not just the ones that scan run touched.

Samples the first `sample_pages` pages of each document (capped at `max_chars` total), not the
whole document -- editions of the same manual are near-identical throughout, so a prefix sample is
a cheap, reliable signal without the O(n) memory/CPU cost of hashing every page of every document.

USAGE (host):
    python build_dedup.py                                  # defaults below
    python build_dedup.py --sample-pages 8 --threshold 0.75
    python build_dedup.py --max-chars 30000
"""
import os
import sys
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dedup  # noqa: E402

ROOT = os.path.dirname(HERE)
DB = os.environ.get("VIEWER_DB", os.path.join(ROOT, "index", "viewer.db"))
DEDUP_DB = os.environ.get("DEDUP_DB", os.path.join(ROOT, "index", "dedup.db"))

DEFAULT_SAMPLE_PAGES = 5      # first N pages per document -- plenty of signal for edition detection
DEFAULT_MAX_CHARS = 20000     # hard cap on each document's sampled text (bounds shingle-set size)
DEFAULT_THRESHOLD = 0.8       # dedup.find_duplicates()'s own documented default


def main(sample_pages=None, max_chars=None, threshold=None):
    sample_pages = DEFAULT_SAMPLE_PAGES if sample_pages is None else sample_pages
    max_chars = DEFAULT_MAX_CHARS if max_chars is None else max_chars
    threshold = DEFAULT_THRESHOLD if threshold is None else threshold
    if not os.path.exists(DB):
        print("viewer.db not found at", DB); return 2

    con = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
    try:
        doc_rows = con.execute(
            "SELECT id, tm_number, vehicle, title, page_count FROM documents WHERE page_count > 0").fetchall()
        docs = []
        for did, tm, veh, title, pc in doc_rows:
            pages = con.execute(
                "SELECT body_text FROM pages WHERE document_id=? AND page_number<=? ORDER BY page_number",
                (did, sample_pages)).fetchall()
            text = " ".join((p[0] or "") for p in pages)[:max_chars]
            if text.strip():
                docs.append((did, text, tm, veh, title, pc))
    finally:
        con.close()

    print("Building edition/duplicate clusters over %d documents (sample_pages=%d, max_chars=%d, "
          "threshold=%.2f)..." % (len(docs), sample_pages, max_chars, threshold))
    print("  O(n^2) comparison -- a large corpus can take a while.")
    r = dedup.build(DEDUP_DB, docs, threshold=threshold,
                     meta={"sample_pages": str(sample_pages), "max_chars": str(max_chars),
                           "threshold": str(threshold), "documents_scanned": str(len(docs))})
    print("Done: %d cluster(s), %d document(s) grouped -> %s" %
          (r["clusters"], r["documents_in_clusters"], DEDUP_DB))
    print("Read-only on sources; append-only sidecar. /api/editions queries it offline.")
    return 0


def _cli_float(flag, argv, default):
    """Same "--flag N" / "--flag=N" parsing style as build_kg.py's --sample-docs / --parts-cap."""
    for a in argv:
        if a.startswith(flag):
            try:
                return float(a.split("=", 1)[1]) if "=" in a else float(argv[argv.index(a) + 1])
            except Exception:
                return default
    return default


if __name__ == "__main__":
    _sample_pages = int(_cli_float("--sample-pages", sys.argv[1:], DEFAULT_SAMPLE_PAGES))
    _max_chars = int(_cli_float("--max-chars", sys.argv[1:], DEFAULT_MAX_CHARS))
    _threshold = _cli_float("--threshold", sys.argv[1:], DEFAULT_THRESHOLD)
    raise SystemExit(main(sample_pages=_sample_pages, max_chars=_max_chars, threshold=_threshold))
# END OF FILE
