#!/usr/bin/env python3
"""THE VIEWER -- KNOWLEDGE GRAPH (v1.3.0, catalog §3.11 + §7.4). Ties the separately-extracted entities together into
one graph -- part ↔ figure ↔ procedure ↔ spec/measurement ↔ NSN ↔ vehicle -- so 'everything about X' is a single hop
instead of five separate lookups. Stored as an append-only sidecar (index/kg.db); the running app only READS it. This
module is the graph library (build + query); build_kg.py assembles the triples from viewer.db + the sidecars host-side.
Corpus authoritative; read-only on the sources."""
import os
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes(key TEXT PRIMARY KEY, type TEXT, label TEXT);
CREATE TABLE IF NOT EXISTS edges(src TEXT, rel TEXT, dst TEXT, UNIQUE(src, rel, dst));
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE INDEX IF NOT EXISTS ix_edge_src ON edges(src);
CREATE INDEX IF NOT EXISTS ix_edge_dst ON edges(dst);
CREATE INDEX IF NOT EXISTS ix_node_label ON nodes(label COLLATE NOCASE);
"""


def _key(ntype, label):
    return "%s|%s" % (ntype, (label or "").strip().lower())


def build(kg_db, triples, meta=None):
    """Write a graph from `triples` = [(src_type, src_label, rel, dst_type, dst_label)]. Append-only
    sidecar semantics (never touches the corpus). Returns {nodes, edges}.

    `meta` (optional): a {str: str} dict of build-provenance facts persisted into the `meta` table
    (e.g. how much of the corpus a triple SOURCE actually sampled) -- finding #27: build_kg.py's
    figureparts pass only ever sampled the first 400 documents' page 1, capped at 5000 parts, with
    no way for a reader of kg.db (or /api/kg) to tell "this edge doesn't exist" apart from "this
    edge exists but is outside the sample." `meta` lets a builder record that fraction; `stats()`
    surfaces it back out. Purely additive -- omitting `meta` (every pre-existing caller) is a no-op.

    Builds into a temp file in the same directory and only replaces kg_db at the very end, once
    every table is populated and committed -- kg_db itself is never touched until the swap.
    Previously this ran DROP TABLE / CREATE TABLE / inserts directly against the live kg_db with a
    single commit() at the very end; con.executescript() issues an implicit COMMIT before running,
    so the DROP and each CREATE were individually autocommitted the instant they ran, not wrapped
    in one transaction -- a crash/kill anywhere in between left kg_db on disk mid-build (e.g. nodes
    table present, edges not yet re-created), permanently, in place. neighbors() below already had
    to grow defensive cleanup for exactly that failure mode; this fix removes the failure mode
    itself instead. Same build-to-temp-then-atomic_replace pattern as build_publog.py."""
    import safeguard
    tmp_path = kg_db + ".building-%d" % os.getpid()
    safeguard.remove_retry(tmp_path)   # stale leftover from a prior crashed run -- just scratch space
    con = None
    try:
        con = sqlite3.connect(tmp_path)
        con.executescript(SCHEMA)   # CREATE TABLE IF NOT EXISTS -- no DROP needed, the temp file starts empty
        nodes = {}
        for st, sl, rel, dt, dl in triples:
            if not sl or not dl:
                continue
            sk = _key(st, sl); dk = _key(dt, dl)
            nodes[sk] = (sk, st, sl.strip()); nodes[dk] = (dk, dt, dl.strip())
            con.execute("INSERT OR IGNORE INTO edges(src,rel,dst) VALUES(?,?,?)", (sk, rel, dk))
        con.executemany("INSERT OR REPLACE INTO nodes(key,type,label) VALUES(?,?,?)", list(nodes.values()))
        if meta:
            con.executemany("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", list(meta.items()))
        con.commit()
        ne = con.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        ee = con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        con.close()
    except BaseException:
        try: con.close()
        except Exception: pass
        try: safeguard.remove_retry(tmp_path)
        except OSError: pass
        raise

    safeguard.atomic_replace(tmp_path, kg_db)   # only now does the new build become "kg.db"
    return {"nodes": ne, "edges": ee}


def neighbors(kg_db, label, limit=200):
    """Everything one hop from a node matched by `label` (case-insensitive, exact then LIKE). Returns
    {query, matched:[labels], out:[{rel,type,label}], in:[{rel,type,label}]}. Read-only, no network."""
    label = (label or "").strip()
    if not kg_db or not os.path.exists(kg_db) or len(label) < 2:
        return {"query": label, "matched": [], "out": [], "in": []}
    # v1.13.4: no try/except/finally at all here previously -- any query exception (e.g. kg.db left
    # mid-build: nodes table present, edges not yet re-created, since build() DROPs-then-CREATEs each
    # table separately with no wrapping transaction) propagated past con.close(), leaking the handle
    # while relying on viewer_app's generic top-level 500 handler to avoid crashing the process. Kept
    # the propagation (still a real 500 on real corruption -- not swallowed) but guaranteed cleanup.
    con = sqlite3.connect("file:%s?mode=ro" % kg_db, uri=True); con.row_factory = sqlite3.Row
    try:
        # Two-tier lookup (finding #28): the old single OR query (exact OR leading-wildcard LIKE)
        # could never use ix_node_label at all -- SQLite's OR-optimization requires every branch to
        # be independently indexable, and a leading-wildcard LIKE never is, so EVERY /kg lookup did
        # a full table scan. Try exact + PREFIX match first (both servable from the NOCASE-collated
        # index); only fall back to the slow substring-anywhere scan when that finds nothing, so a
        # match in the middle of a label (e.g. "hmmwv" inside "M998 HMMWV") still works, it just
        # doesn't cost the common exact/prefix case a full scan.
        keys = [r["key"] for r in con.execute(
            "SELECT key FROM nodes WHERE label=? COLLATE NOCASE OR label LIKE ? LIMIT 20",
            (label, label + "%"))]
        if not keys:
            keys = [r["key"] for r in con.execute(
                "SELECT key FROM nodes WHERE label LIKE ? LIMIT 20", ("%" + label + "%",))]
        outs, ins, matched = [], [], []
        for k in keys:
            matched.append(con.execute("SELECT label FROM nodes WHERE key=?", (k,)).fetchone()[0])
            for e in con.execute("SELECT e.rel rel, n.type type, n.label label FROM edges e JOIN nodes n ON n.key=e.dst "
                                 "WHERE e.src=? LIMIT ?", (k, limit)):
                outs.append({"rel": e["rel"], "type": e["type"], "label": e["label"]})
            for e in con.execute("SELECT e.rel rel, n.type type, n.label label FROM edges e JOIN nodes n ON n.key=e.src "
                                 "WHERE e.dst=? LIMIT ?", (k, limit)):
                ins.append({"rel": e["rel"], "type": e["type"], "label": e["label"]})
    finally:
        con.close()
    # de-dup
    def dd(rows):
        seen = set(); out = []
        for r in rows:
            t = (r["rel"], r["type"], r["label"].lower())
            if t not in seen:
                seen.add(t); out.append(r)
        return out
    return {"query": label, "matched": matched, "out": dd(outs), "in": dd(ins)}


def stats(kg_db):
    if not kg_db or not os.path.exists(kg_db):
        return {"nodes": 0, "edges": 0, "by_type": {}}
    con = sqlite3.connect("file:%s?mode=ro" % kg_db, uri=True)
    try:
        n = con.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        e = con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        bt = {r[0]: r[1] for r in con.execute("SELECT type, COUNT(*) FROM nodes GROUP BY type")}
        try:
            m = {r[0]: r[1] for r in con.execute("SELECT key, value FROM meta")}
        except sqlite3.OperationalError:
            m = {}   # a kg.db built before finding #27's `meta` table existed
    finally:
        con.close()
    return {"nodes": n, "edges": e, "by_type": bt, "meta": m}


if __name__ == "__main__":
    import tempfile
    kg = os.path.join(tempfile.mkdtemp(), "kg.db")
    triples = [
        ("part", "Alternator", "on_figure", "figure", "FIG 4-2"),
        ("part", "Alternator", "in_vehicle", "vehicle", "HMMWV"),
        ("procedure", "Replace alternator", "for_part", "part", "Alternator"),
        ("part", "Alternator", "has_spec", "spec", "28 VDC"),
        ("part", "Alternator", "has_nsn", "nsn", "2920-01-371-9577"),
        ("part", "Bracket", "on_figure", "figure", "FIG 4-2"),
    ]
    r = build(kg, triples, meta={"figureparts_docs_sampled": "400", "figureparts_docs_total": "7300"})
    assert r["edges"] == 6 and r["nodes"] == 7, r   # 7 distinct: alternator, fig, hmmwv, procedure, spec, nsn, bracket
    nb = neighbors(kg, "alternator")
    outrels = {(o["rel"], o["label"]) for o in nb["out"]}
    assert ("on_figure", "FIG 4-2") in outrels and ("in_vehicle", "HMMWV") in outrels, outrels
    assert ("has_nsn", "2920-01-371-9577") in outrels and ("has_spec", "28 VDC") in outrels, outrels
    inrels = {(i["rel"], i["label"]) for i in nb["in"]}
    assert ("for_part", "Replace alternator") in inrels, ("incoming", inrels)
    # finding #28: a substring match in the MIDDLE of a label (not just exact/prefix) must still
    # resolve, via the slow-path fallback -- "hmmwv" only appears mid-string in "HMMWV" here since
    # the label IS "HMMWV", so use a real embedded-substring case instead.
    nb2 = neighbors(kg, "MMW")   # matches inside "HMMWV" (starts with H, "MMW" is not a prefix)
    assert any(m.lower() == "hmmwv" for m in nb2["matched"]), nb2
    st = stats(kg)
    assert st["by_type"]["part"] == 2 and st["edges"] == 6, st
    # finding #27: build-provenance meta round-trips through build() -> stats()
    assert st["meta"].get("figureparts_docs_sampled") == "400", st
    assert st["meta"].get("figureparts_docs_total") == "7300", st
    print("kg self-test OK  (%d nodes / %d edges; neighbors resolves part->figure/vehicle/nsn/spec + procedure->part; "
          "substring fallback + coverage meta OK)" % (st["nodes"], st["edges"]))
# END OF FILE
