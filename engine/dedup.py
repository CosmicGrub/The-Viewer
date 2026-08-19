#!/usr/bin/env python3
"""THE VIEWER -- EDITION / DUPLICATE DETECTION (v1.3.2, catalog §7.1). The corpus holds many editions of the same TM
(same content, different change number / print date) and outright duplicates. This fingerprints a document's text with
word-shingles and measures Jaccard similarity, so near-identical editions cluster together -- letting the app prefer the
latest edition, de-duplicate search hits, and correlate change history. Pure stdlib; read-only. Corpus authoritative
(nothing is deleted -- duplicates are just linked).

Persistence (build()/editions_for() below, added when this was finally wired in): find_duplicates()
is genuinely O(n^2) and needs the WHOLE corpus to answer "is document X a duplicate of anything" --
the same reason kg.py/conflicts.py stay separate, host-run batch builders rather than inline
per-scan pipeline stages (a newly-scanned document has to be compared against every EXISTING
document, not just the ones a given scan run touched). build_dedup.py is the batch driver
(index/dedup.db, run via DEDUP.bat); /api/editions reads it live, read-only, same
missing-sidecar-degrades-to-empty contract kg.py/conflicts.py already have."""
import os
import re
import sqlite3
import zlib

SCHEMA = """
CREATE TABLE IF NOT EXISTS clusters(
  id INTEGER PRIMARY KEY, cluster_key INTEGER, document_id INTEGER,
  tm_number TEXT, vehicle TEXT, title TEXT, page_count INTEGER, similarity REAL);
CREATE INDEX IF NOT EXISTS ix_clusters_doc ON clusters(document_id);
CREATE INDEX IF NOT EXISTS ix_clusters_key ON clusters(cluster_key);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
"""

_WORD = re.compile(r"[a-z]{3,}")


def _tokens(text):
    # lowercase words >=3 letters; drop pure numbers so a page-number change doesn't look like new content
    return _WORD.findall((text or "").lower())


def _stable_hash(s):
    # zlib.crc32, not the builtin hash() -- str hash() is PYTHONHASHSEED-randomized per process
    # by default (medium finding #22, same bug already fixed in embed.py's HASH_ALGO_VERSION
    # path). Currently latent since find_duplicates() has no caller yet, but a shingle set
    # computed in one process and compared/persisted from another would otherwise never agree.
    return zlib.crc32(s.encode("utf-8"))


def shingles(text, k=4):
    """Set of k-word shingles (as hashes) -- the document fingerprint."""
    toks = _tokens(text)
    if len(toks) < k:
        return frozenset(_stable_hash(t) for t in toks)
    return frozenset(_stable_hash(" ".join(toks[i:i + k])) for i in range(len(toks) - k + 1))


def jaccard(a, b):
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / float(len(a) + len(b) - inter)


def similarity(t1, t2, k=4):
    return round(jaccard(shingles(t1, k), shingles(t2, k)), 3)


def find_duplicates(docs, threshold=0.8, k=4):
    """`docs` = [(id, text)]. Returns clusters [[id,...]] of near-duplicate / same-edition documents (similarity >=
    threshold). Singletons are omitted. O(n^2) -- fine for a sidecar builder over the corpus."""
    sigs = [(i, shingles(t, k)) for i, t in docs]
    n = len(sigs)
    parent = {i: i for i, _ in sigs}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    for a in range(n):
        ia, sa = sigs[a]
        for b in range(a + 1, n):
            ib, sb = sigs[b]
            if jaccard(sa, sb) >= threshold:
                union(ia, ib)
    groups = {}
    for i, _ in sigs:
        groups.setdefault(find(i), []).append(i)
    return [sorted(g) for g in groups.values() if len(g) > 1]


def build(dedup_db, docs, threshold=0.8, k=4, meta=None):
    """`docs` = [(document_id, text, tm_number, vehicle, title, page_count)]. Clusters near-
    duplicate/same-edition documents via find_duplicates() and writes them to dedup_db. Build-to-
    temp-then-atomic-swap (safeguard.atomic_sqlite_build), same crash-safety contract kg.build()/
    build_publog.py already use -- dedup_db is never touched until every row is written and
    committed. Each cluster's first (lowest document_id) member is used as the similarity-comparison
    anchor purely for a stable, deterministic reference point -- NOT a claim about which edition is
    "latest"; this module has no reliable signal for that (no universal change-number/date field
    across every TM), so it never asserts one. Returns {clusters, documents_in_clusters}."""
    import safeguard
    id_text = [(d[0], d[1]) for d in docs]
    groups = find_duplicates(id_text, threshold=threshold, k=k)
    by_id = {d[0]: d for d in docs}
    with safeguard.atomic_sqlite_build(dedup_db) as (con, _tmp):
        con.executescript(SCHEMA)   # CREATE TABLE IF NOT EXISTS -- no DROP needed, the temp file starts empty
        n_docs = 0
        for cluster_key, group in enumerate(groups):
            anchor_text = by_id[group[0]][1]
            for document_id in group:
                sim = 1.0 if document_id == group[0] else similarity(anchor_text, by_id[document_id][1], k)
                _did, _text, tm_number, vehicle, title, page_count = by_id[document_id]
                con.execute(
                    "INSERT INTO clusters(cluster_key,document_id,tm_number,vehicle,title,page_count,similarity) "
                    "VALUES(?,?,?,?,?,?,?)", (cluster_key, document_id, tm_number, vehicle, title, page_count, sim))
                n_docs += 1
        if meta:
            con.executemany("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", list(meta.items()))
        con.commit()
    return {"clusters": len(groups), "documents_in_clusters": n_docs}


def editions_for(dedup_db, document_id):
    """Other documents in the SAME cluster as document_id (its sibling editions) -- read-only, [] if
    dedup_db doesn't exist yet (never built) or this document isn't in any cluster (no near-
    duplicate found for it, the common case). Sorted by similarity to the cluster's anchor,
    descending, so the closest match shows first."""
    if not dedup_db or not os.path.exists(dedup_db) or not document_id:
        return []
    con = sqlite3.connect("file:%s?mode=ro" % dedup_db, uri=True); con.row_factory = sqlite3.Row
    try:
        row = con.execute("SELECT cluster_key FROM clusters WHERE document_id=?", (document_id,)).fetchone()
        if not row:
            return []
        rows = con.execute(
            "SELECT document_id, tm_number, vehicle, title, page_count, similarity FROM clusters "
            "WHERE cluster_key=? AND document_id<>? ORDER BY similarity DESC",
            (row["cluster_key"], document_id)).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []   # a dedup.db from before this schema existed, or mid-build -- degrade, never 500
    finally:
        con.close()


def stats(dedup_db):
    """Corpus-wide summary for /api/editions' own status display -- {clusters, documents_in_clusters,
    meta}, or zeros if dedup_db hasn't been built yet."""
    if not dedup_db or not os.path.exists(dedup_db):
        return {"clusters": 0, "documents_in_clusters": 0, "meta": {}}
    con = sqlite3.connect("file:%s?mode=ro" % dedup_db, uri=True)
    try:
        n_clusters = con.execute("SELECT COUNT(DISTINCT cluster_key) FROM clusters").fetchone()[0]
        n_docs = con.execute("SELECT COUNT(*) FROM clusters").fetchone()[0]
        try:
            m = {r[0]: r[1] for r in con.execute("SELECT key, value FROM meta")}
        except sqlite3.OperationalError:
            m = {}
    except sqlite3.OperationalError:
        return {"clusters": 0, "documents_in_clusters": 0, "meta": {}}
    finally:
        con.close()
    return {"clusters": n_clusters, "documents_in_clusters": n_docs, "meta": m}


if __name__ == "__main__":
    base = ("The alternator is mounted on the front of the engine and is driven by the serpentine belt. "
            "Remove the two mounting bolts and disconnect the wiring harness before extraction. Torque to 30 foot pounds.")
    edition = base.replace("30 foot pounds", "35 foot pounds") + " Change 3 Page 12."   # tiny edit + page banner
    other = ("The transmission fluid should be checked with the vehicle on level ground and the engine at operating "
             "temperature. Use only the specified lubricant grade and do not overfill the reservoir under any condition.")
    s_edit = similarity(base, edition); s_other = similarity(base, other)
    assert s_edit >= 0.7, ("editions should be similar", s_edit)
    assert s_other < 0.2, ("different docs should be dissimilar", s_other)
    groups = find_duplicates([(1, base), (2, edition), (3, other)], threshold=0.6)
    assert groups == [[1, 2]], ("edition cluster wrong", groups)

    import tempfile
    ddb = os.path.join(tempfile.mkdtemp(), "dedup.db")
    docs = [(1, base, "TM 9-2320-280-24", "HMMWV", "Alternator Manual Ch2", 40),
            (2, edition, "TM 9-2320-280-24", "HMMWV", "Alternator Manual Ch3", 42),
            (3, other, "TM 9-2320-280-10", "HMMWV", "Operator Manual", 120)]
    r = build(ddb, docs, threshold=0.6, meta={"sample_pages": "5", "documents_scanned": "3"})
    assert r == {"clusters": 1, "documents_in_clusters": 2}, r
    ed2 = editions_for(ddb, 2)
    assert len(ed2) == 1 and ed2[0]["document_id"] == 1, ed2
    assert ed2[0]["tm_number"] == "TM 9-2320-280-24" and ed2[0]["title"] == "Alternator Manual Ch2", ed2
    ed3 = editions_for(ddb, 3)
    assert ed3 == [], ("doc 3 has no near-duplicate, must return empty, not crash", ed3)
    ed_missing = editions_for(ddb, 999)
    assert ed_missing == [], ("an unknown document_id must degrade to empty, not crash", ed_missing)
    st = stats(ddb)
    assert st["clusters"] == 1 and st["documents_in_clusters"] == 2, st
    assert st["meta"].get("documents_scanned") == "3", st
    st_missing = stats(os.path.join(tempfile.mkdtemp(), "never_built.db"))
    assert st_missing == {"clusters": 0, "documents_in_clusters": 0, "meta": {}}, st_missing

    print("dedup self-test OK  (edition sim=%.2f, unrelated sim=%.2f, cluster=%s; build/editions_for/"
          "stats round-trip through a real sidecar OK)" % (s_edit, s_other, groups))
# END OF FILE
