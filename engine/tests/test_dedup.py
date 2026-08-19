#!/usr/bin/env python3
"""Unit tests for engine/dedup.py's build()/editions_for()/stats() -- the persistence layer added
while picking up dedup.py as a deferred item from the flags audit. dedup.py's own shingle/Jaccard
math (shingles/jaccard/similarity/find_duplicates) already had a self-test; this covers the NEW
sidecar round-trip (build_dedup.py's real job, mirrored here without needing a real corpus DB).
Pure stdlib test runner."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dedup as D


BASE = ("The alternator is mounted on the front of the engine and is driven by the serpentine belt. "
        "Remove the two mounting bolts and disconnect the wiring harness before extraction. Torque to 30 foot pounds.")
EDITION = BASE.replace("30 foot pounds", "35 foot pounds") + " Change 3 Page 12."
OTHER = ("The transmission fluid should be checked with the vehicle on level ground and the engine at operating "
         "temperature. Use only the specified lubricant grade and do not overfill the reservoir under any condition.")


def run():
    passed, failed = [], []
    def check(name, cond):
        (passed if cond else failed).append(name)

    d = tempfile.mkdtemp(prefix="dedup_test_")
    ddb = os.path.join(d, "dedup.db")

    docs = [
        (1, BASE, "TM 9-2320-280-24", "HMMWV", "Alternator Manual (Change 2)", 40),
        (2, EDITION, "TM 9-2320-280-24", "HMMWV", "Alternator Manual (Change 3)", 42),
        (3, OTHER, "TM 9-2320-280-10", "HMMWV", "Operator Manual", 120),
    ]
    r = D.build(ddb, docs, threshold=0.6, meta={"sample_pages": "5", "documents_scanned": "3"})
    check("build(): exactly one cluster found (docs 1+2, not 3)", r["clusters"] == 1)
    check("build(): exactly 2 documents grouped into that cluster", r["documents_in_clusters"] == 2)
    check("build(): the sidecar file was actually written", os.path.exists(ddb))

    ed1 = D.editions_for(ddb, 1)
    check("editions_for(): doc 1's only sibling is doc 2", len(ed1) == 1 and ed1[0]["document_id"] == 2)
    check("editions_for(): sibling's real metadata comes through", ed1[0]["tm_number"] == "TM 9-2320-280-24"
          and ed1[0]["title"] == "Alternator Manual (Change 3)" and ed1[0]["page_count"] == 42)
    check("editions_for(): similarity is a real, high value (near-identical text)", ed1[0]["similarity"] >= 0.8)

    ed2 = D.editions_for(ddb, 2)
    check("editions_for(): symmetric -- doc 2's sibling is doc 1", len(ed2) == 1 and ed2[0]["document_id"] == 1)

    ed3 = D.editions_for(ddb, 3)
    check("editions_for(): a document with no near-duplicate returns [] cleanly (not an error)", ed3 == [])

    ed_missing = D.editions_for(ddb, 99999)
    check("editions_for(): an unknown document_id returns [] (never crashes)", ed_missing == [])

    ed_no_db = D.editions_for(os.path.join(d, "never_built.db"), 1)
    check("editions_for(): a dedup.db that was never built returns [] (never crashes)", ed_no_db == [])

    ed_no_id = D.editions_for(ddb, 0)
    check("editions_for(): document_id=0 (falsy) returns [] rather than querying garbage", ed_no_id == [])

    st = D.stats(ddb)
    check("stats(): reports the right cluster/document counts", st["clusters"] == 1 and st["documents_in_clusters"] == 2)
    check("stats(): build-provenance meta round-trips", st["meta"].get("documents_scanned") == "3"
          and st["meta"].get("sample_pages") == "5")

    st_missing = D.stats(os.path.join(d, "also_never_built.db"))
    check("stats(): a never-built dedup.db degrades to zeros, not a crash",
          st_missing == {"clusters": 0, "documents_in_clusters": 0, "meta": {}})

    # --- idempotent rebuild: running build() again against the SAME sidecar path must not corrupt
    # or duplicate anything (atomic_sqlite_build swaps the whole file, so this is really testing
    # that a second build cleanly replaces the first, not that it merges with it). ---
    r2 = D.build(ddb, docs, threshold=0.6)
    check("build(): a second build against the same path is clean (same cluster count, not doubled)",
          r2["clusters"] == 1 and r2["documents_in_clusters"] == 2)
    ed1b = D.editions_for(ddb, 1)
    check("build(): re-running doesn't duplicate rows in editions_for()'s result", len(ed1b) == 1)

    # --- a genuinely unique corpus (no two documents alike) -> zero clusters, not an error ---
    unique_docs = [(10, BASE, "TM A", "V1", "A", 5), (11, OTHER, "TM B", "V2", "B", 5)]
    udb = os.path.join(d, "unique_dedup.db")
    ru = D.build(udb, unique_docs, threshold=0.8)
    check("build(): a corpus with no duplicates produces zero clusters cleanly", ru == {"clusters": 0, "documents_in_clusters": 0})
    check("editions_for(): correctly empty for every doc in a duplicate-free corpus", D.editions_for(udb, 10) == [])

    return passed, failed


if __name__ == "__main__":
    p, f = run()
    for n in p: print("PASS", n)
    for n in f: print("FAIL", n)
    print("\n%d passed, %d failed" % (len(p), len(f)))
    sys.exit(1 if f else 0)

# END OF FILE
