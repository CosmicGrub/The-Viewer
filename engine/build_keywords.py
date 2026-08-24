#!/usr/bin/env python3
"""THE VIEWER -- build/extend keywords.json so mechanics' alternate words map to catalog nomenclature.

The running app NEVER goes online. This one-time tool MERGES (never drops) the authoritative PUB LOG
colloquial names that ENRICH-PUBLOG already folded into ref_nsn ('Also called: X') with the curated seed
keyword groups, linking each part's nomenclature to its colloquial/common name. The curated seed itself was
informed by shop-terminology research; this step grounds it in YOUR corpus + the DLA colloquial table.

  python build_keywords.py [--db PATH] [--out keywords.json]

Offline-safe: if there's no index it just rewrites the curated seed. Append-only in spirit (merges).
"""
import os, sqlite3, json, sys, re

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(HERE, "..", "index", "viewer.db")
KW = os.path.join(HERE, "keywords.json")

def _norm(s): return re.sub(r"\s+", " ", (s or "").strip().lower())

def run(db=DEFAULT_DB, out=KW):
    """Merge ref_nsn's PUB LOG 'Also called: X' colloquial names (populated by enrich_flis()) into
    out's synonym groups, never dropping an existing group/term. Offline-safe: a missing/unbuilt
    index just rewrites the curated seed unchanged. Returns (n_groups, n_added, n_linked) --
    n_added is new colloquial-name groups created, n_linked is terms added to an existing group.
    Shared by main() (the standalone build_keywords.py / VERIFY.bat CLI usage) and
    viewer_ingest.py's enrich_flis(), which calls this live right after populating the colloquial
    names this function reads, so search_feature.py's _load_synonyms() (the live consumer -- it
    reads `out` fresh on every restart) stays in sync without a manual build_keywords.py run.
    Seeds from `out` itself when it already exists, else falls back to the curated KW seed --
    a fix made alongside this refactor: the original main() always read from KW regardless of a
    --out override, so a custom --out never round-tripped (each run re-merged against the
    untouched KW file and silently discarded whatever a previous custom-output run had written).
    A fresh custom --out still bootstraps from the curated seed, same as before."""
    try:
        doc = json.load(open(out if os.path.exists(out) else KW, encoding="utf-8"))
    except Exception:
        doc = {"groups": []}
    groups = doc.get("groups", [])
    term2idx = {}
    for gi, g in enumerate(groups):
        for t in g: term2idx[_norm(t)] = gi

    added = linked = 0
    db = os.path.abspath(db)
    db_existed = os.path.exists(db)
    if db_existed:
        con = sqlite3.connect(db, timeout=60); con.row_factory = sqlite3.Row
        rows = []
        try:
            rows = con.execute("SELECT item_name, description FROM ref_nsn "
                               "WHERE COALESCE(item_name,'')<>'' AND description LIKE '%Also called:%'").fetchall()
        except Exception:
            pass
        con.close()
        for r in rows:
            nom = (r["item_name"] or "").strip()
            m = re.search(r"Also called:\s*([^;]+)", r["description"] or "")
            coll = (m.group(1).strip() if m else "")
            if not nom or not coll or _norm(nom) == _norm(coll): continue
            gi = term2idx.get(_norm(nom), term2idx.get(_norm(coll)))
            if gi is None:
                groups.append([nom.lower(), coll.lower()]); gi = len(groups) - 1
                term2idx[_norm(nom)] = gi; term2idx[_norm(coll)] = gi; added += 1
            else:
                g = groups[gi]; have = {_norm(x) for x in g}
                for tt in (nom.lower(), coll.lower()):
                    if _norm(tt) not in have:
                        g.append(tt); term2idx[_norm(tt)] = gi; have.add(_norm(tt)); linked += 1

    doc["groups"] = groups
    doc["_generated"] = "build_keywords.py merged PUB LOG colloquial names into the curated seed (offline, append-only)."
    json.dump(doc, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    return len(groups), added, linked, db_existed

def main():
    db = DEFAULT_DB; out = KW; args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--db" and i + 1 < len(args): db = args[i + 1]
        if a == "--out" and i + 1 < len(args): out = args[i + 1]
    n_groups, added, linked, db_existed = run(db, out)
    if not db_existed:
        print("(no index at %s -- rewriting the curated seed only)" % os.path.abspath(db))
    print("keywords.json: %d groups  (+%d new from colloquial, +%d terms linked)  -> %s"
          % (n_groups, added, linked, out))
    print("Restart the app to load the new keyword sets into search.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
