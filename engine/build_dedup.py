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

Comparisons are bucketed by dedup.block_key(tm_number) (same base TM family, e.g. "TM 9-2320-280-24"
and "TM 9-2320-280-10" both bucket to "TM 9-2320-280"), so the O(n^2) pass runs per bucket instead of
across the whole corpus -- at real corpus scale (~40k documents) an unbucketed pass is ~787M
comparisons and an estimated 8-10GB+ of shingle-set memory upfront, against this app's documented
<8GB "legacy" hardware tier. --max-docs-per-bucket is a defense-in-depth cap on any single oversized
bucket (chiefly documents with a blank/missing tm_number, which all land in one "" bucket).

USAGE (host):
    python build_dedup.py                                  # defaults below
    python build_dedup.py --sample-pages 8 --threshold 0.75
    python build_dedup.py --max-chars 30000
    python build_dedup.py --max-docs-per-bucket 2000
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
DEFAULT_MAX_DOCS_PER_BUCKET = 4000   # dedup-scale fix (annex #4): defense-in-depth cap on any single
                                      # block_key() bucket (chiefly the "" blank-tm_number bucket) --
                                      # dedup.build() already blocks by TM family, but a bucket this
                                      # large would still be an O(n^2) pass over 4000^2/2 ~= 8M pairs;
                                      # anything bigger gets truncated with a printed warning rather
                                      # than silently taking however long it takes.


def main(sample_pages=None, max_chars=None, threshold=None, max_docs_per_bucket=None):
    sample_pages = DEFAULT_SAMPLE_PAGES if sample_pages is None else sample_pages
    max_chars = DEFAULT_MAX_CHARS if max_chars is None else max_chars
    threshold = DEFAULT_THRESHOLD if threshold is None else threshold
    max_docs_per_bucket = DEFAULT_MAX_DOCS_PER_BUCKET if max_docs_per_bucket is None else max_docs_per_bucket
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

    # dedup-scale fix (annex #4): dedup.build() blocks by dedup.block_key(tm_number) internally, so
    # the real cost is per-bucket, not corpus-wide -- but cap any one oversized bucket (typically
    # blank/missing tm_number) instead of trusting it'll always be small. Truncation is explicit and
    # printed, never silent.
    buckets = {}
    for d in docs:
        buckets.setdefault(dedup.block_key(d[2]), []).append(d)
    capped_docs = []
    truncated = []
    for key, group in buckets.items():
        if len(group) > max_docs_per_bucket:
            truncated.append((key or "(blank tm_number)", len(group), max_docs_per_bucket))
            group = group[:max_docs_per_bucket]
        capped_docs.extend(group)
    docs = capped_docs
    for key, had, kept in truncated:
        print("  WARNING: bucket %r had %d documents, truncated to %d (--max-docs-per-bucket) -- "
              "some real duplicates in this bucket may be missed this run." % (key, had, kept))

    print("Building edition/duplicate clusters over %d documents (sample_pages=%d, max_chars=%d, "
          "threshold=%.2f, %d TM-family buckets, max_docs_per_bucket=%d)..." %
          (len(docs), sample_pages, max_chars, threshold, len(buckets), max_docs_per_bucket))
    print("  O(n^2) comparison PER TM-family bucket, not corpus-wide -- see dedup.block_key().")
    r = dedup.build(DEDUP_DB, docs, threshold=threshold,
                     meta={"sample_pages": str(sample_pages), "max_chars": str(max_chars),
                           "threshold": str(threshold), "documents_scanned": str(len(docs)),
                           "buckets": str(len(buckets)), "buckets_truncated": str(len(truncated))})
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
    _max_docs = int(_cli_float("--max-docs-per-bucket", sys.argv[1:], DEFAULT_MAX_DOCS_PER_BUCKET))
    raise SystemExit(main(sample_pages=_sample_pages, max_chars=_max_chars, threshold=_threshold,
                           max_docs_per_bucket=_max_docs))
# END OF FILE
