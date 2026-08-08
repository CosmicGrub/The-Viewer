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
CREATE INDEX IF NOT EXISTS ix_edge_src ON edges(src);
CREATE INDEX IF NOT EXISTS ix_edge_dst ON edges(dst);
CREATE INDEX IF NOT EXISTS ix_node_label ON nodes(label);
"""


def _key(ntype, label):
    return "%s|%s" % (ntype, (label or "").strip().lower())


def build(kg_db, triples):
    """Write a graph from `triples` = [(src_type, src_label, rel, dst_type, dst_label)]. Rebuilds cleanly. Append-only
    sidecar semantics (never touches the corpus). Returns {nodes, edges}."""
    con = sqlite3.connect(kg_db)
    con.executescript("DROP TABLE IF EXISTS nodes; DROP TABLE IF EXISTS edges;")
    con.executescript(SCHEMA)
    nodes = {}
    for st, sl, rel, dt, dl in triples:
        if not sl or not dl:
            continue
        sk = _key(st, sl); dk = _key(dt, dl)
        nodes[sk] = (sk, st, sl.strip()); nodes[dk] = (dk, dt, dl.strip())
        con.execute("INSERT OR IGNORE INTO edges(src,rel,dst) VALUES(?,?,?)", (sk, rel, dk))
    con.executemany("INSERT OR REPLACE INTO nodes(key,type,label) VALUES(?,?,?)", list(nodes.values()))
    con.commit()
    ne = con.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    ee = con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    con.close()
    return {"nodes": ne, "edges": ee}


def neighbors(kg_db, label, limit=200):
    """Everything one hop from a node matched by `label` (case-insensitive, exact then LIKE). Returns
    {query, matched:[labels], out:[{rel,type,label}], in:[{rel,type,label}]}. Read-only, no network."""
    label = (label or "").strip()
    if not kg_db or not os.path.exists(kg_db) or len(label) < 2:
        return {"query": label, "matched": [], "out": [], "in": []}
    con = sqlite3.connect("file:%s?mode=ro" % kg_db, uri=True); con.row_factory = sqlite3.Row
    keys = [r["key"] for r in con.execute(
        "SELECT key FROM nodes WHERE label=? COLLATE NOCASE OR label LIKE ? LIMIT 20",
        (label, "%" + label + "%"))]
    outs, ins, matched = [], [], []
    for k in keys:
        matched.append(con.execute("SELECT label FROM nodes WHERE key=?", (k,)).fetchone()[0])
        for e in con.execute("SELECT e.rel rel, n.type type, n.label label FROM edges e JOIN nodes n ON n.key=e.dst "
                             "WHERE e.src=? LIMIT ?", (k, limit)):
            outs.append({"rel": e["rel"], "type": e["type"], "label": e["label"]})
        for e in con.execute("SELECT e.rel rel, n.type type, n.label label FROM edges e JOIN nodes n ON n.key=e.src "
                             "WHERE e.dst=? LIMIT ?", (k, limit)):
            ins.append({"rel": e["rel"], "type": e["type"], "label": e["label"]})
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
    n = con.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    e = con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    bt = {r[0]: r[1] for r in con.execute("SELECT type, COUNT(*) FROM nodes GROUP BY type")}
    con.close()
    return {"nodes": n, "edges": e, "by_type": bt}


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
    r = build(kg, triples)
    assert r["edges"] == 6 and r["nodes"] == 7, r   # 7 distinct: alternator, fig, hmmwv, procedure, spec, nsn, bracket
    nb = neighbors(kg, "alternator")
    outrels = {(o["rel"], o["label"]) for o in nb["out"]}
    assert ("on_figure", "FIG 4-2") in outrels and ("in_vehicle", "HMMWV") in outrels, outrels
    assert ("has_nsn", "2920-01-371-9577") in outrels and ("has_spec", "28 VDC") in outrels, outrels
    inrels = {(i["rel"], i["label"]) for i in nb["in"]}
    assert ("for_part", "Replace alternator") in inrels, ("incoming", inrels)
    st = stats(kg)
    assert st["by_type"]["part"] == 2 and st["edges"] == 6, st
    print("kg self-test OK  (%d nodes / %d edges; neighbors resolves part->figure/vehicle/nsn/spec + procedure->part)"
          % (st["nodes"], st["edges"]))
# END OF FILE
