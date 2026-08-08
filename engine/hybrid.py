"""hybrid.py -- smarter offline retrieval, layered on top of the existing keyword search. Three additions,
each degrades gracefully so the base search is never worse:

  1. GLOSSARY / ACRONYM query expansion -- a corpus-wide acronym glossary (aggregated once from the manuals'
     own abbreviation lists) so a query that mentions a short form (e.g. 'CTIS', 'GVWR') also matches the
     spelled-out phrase. No glossary built yet -> no expansion.
  2. HYBRID ranking -- Reciprocal-Rank Fusion of the keyword (FTS) hits with the semantic (embeddings) hits,
     so meaning-matches and exact-matches reinforce each other. No embeddings index -> keyword-only.
  3. Fuzzy 'DID YOU MEAN' for a mistyped NSN -- grounded in the PUBLOG catalog (real NSNs that share the
     leading digits). No PUBLOG -> nothing suggested.

Pure read-only over the index + sidecars. The running app calls hybrid_search(); everything else is helpers.
"""

from __future__ import annotations
import re, sqlite3, threading, time

_GLOSS = {"data": None, "ts": 0.0}
_GLOSS_LOCK = threading.Lock()   # v1.13: ThreadingHTTPServer -> concurrent first-hits must not race the build
_TTL = 3600
_TOKEN = re.compile(r"[A-Za-z0-9]+")


def _db_ro(db_path):
    return sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)


def global_glossary(db_path, cap_pages=500) -> dict:
    """Aggregate a corpus-wide {ABBR: full-form} from pages that carry an abbreviations/acronyms list.
    Cached for an hour. Bounded (cap_pages) so it stays cheap. Read-only; best-effort."""
    if _GLOSS["data"] is not None and (time.time() - _GLOSS["ts"]) < _TTL:
        return _GLOSS["data"]
    with _GLOSS_LOCK:                      # v1.13: double-checked -- one thread builds, the rest reuse
        if _GLOSS["data"] is not None and (time.time() - _GLOSS["ts"]) < _TTL:
            return _GLOSS["data"]
        gl = {}
        try:
            import acronyms
            con = _db_ro(db_path)
            try:
                rows = con.execute(
                    "SELECT body_text FROM pages WHERE body_text LIKE '%ABBREVIATION%' OR body_text LIKE '%ACRONYM%' "
                    "LIMIT ?", (cap_pages,)).fetchall()
            finally:
                con.close()
            for (t,) in rows:
                for a, f in acronyms.extract_glossary(t or "").items():
                    gl.setdefault(a, f)
        except Exception:
            gl = gl or {}
        _GLOSS["data"] = gl
        _GLOSS["ts"] = time.time()
        return gl


def expand_query(q, db_path) -> dict:
    """Return {query, expanded, acronyms:[{abbr,full}]}. `expanded` appends the spelled-out forms of any
    glossary acronyms present so the keyword search also matches them."""
    gl = global_glossary(db_path)
    used, seen = [], set()
    for t in _TOKEN.findall(q or ""):
        u = t.upper()
        if 2 <= len(u) <= 8 and u in gl and u not in seen:
            seen.add(u)
            used.append({"abbr": u, "full": gl[u]})
    expanded = q if not used else (q + " " + " ".join(x["full"] for x in used))
    return {"query": q, "expanded": expanded, "acronyms": used}


def nsn_did_you_mean(q, limit=5) -> list:
    """Fuzzy NSN correction grounded in PUBLOG. Only fires for near-NSN digit strings; [] otherwise."""
    digits = re.sub(r"\D", "", q or "")
    if len(digits) < 7 or len(digits) > 13:
        return []
    try:
        import publog
        if publog.available():
            return publog.suggest_nsn(digits, limit=limit)
    except Exception:
        pass
    return []


def _key(r):
    return (str(r.get("doc_id") or r.get("doc") or ""), str(r.get("page") or ""))


def fuse(lists, k=60):
    """Reciprocal-Rank Fusion across result lists. Each item keyed by (doc, page); score = sum 1/(k+rank).
    Returns the merged list, best first, each tagged with `_rrf` and `_signals`."""
    score, keep, sig = {}, {}, {}
    for name, lst in lists:
        for rank, r in enumerate(lst or []):
            kk = _key(r)
            if kk == ("", ""):
                continue
            score[kk] = score.get(kk, 0.0) + 1.0 / (k + rank + 1)
            sig.setdefault(kk, set()).add(name)
            if kk not in keep:
                keep[kk] = r
    ordered = sorted(keep.values(), key=lambda r: -score[_key(r)])
    for r in ordered:
        r["_rrf"] = round(score[_key(r)], 5)
        r["_signals"] = sorted(sig[_key(r)])
    return ordered


def hybrid_search(q, core, index_dir, limit=25) -> dict:
    """Glossary-expanded keyword search fused with semantic search. `core` is viewer_app (has .search &
    .DB_PATH); `index_dir` is where the embeddings live. Always returns keyword hits at minimum."""
    q = (q or "").strip()
    exp = expand_query(q, getattr(core, "DB_PATH", ""))
    try:
        fts = core.search(exp["expanded"], limit * 2) or []
    except Exception:
        fts = []
    sem = []
    try:
        import embed
        s = embed.search(q, index_dir, top=limit * 2)
        sem = (s.get("results") if isinstance(s, dict) else s) or []
        for r in sem:                          # normalize semantic keys to the FTS shape
            r.setdefault("doc_id", r.get("doc"))
            r.setdefault("page_url", r.get("page_url"))
    except Exception:
        sem = []
    fused = fuse([("keyword", fts), ("semantic", sem)]) if sem else fts
    return {
        "query": q,
        "expanded": exp["expanded"] if exp["expanded"] != q else None,
        "acronyms": exp["acronyms"],
        "results": fused[:limit],
        "signals": {"keyword": len(fts), "semantic": len(sem), "fused": len(fused)},
        "nsn_did_you_mean": nsn_did_you_mean(q),
    }


# --------------------------------------------------------------------------- #
# self-test: `python hybrid.py`  (pure helpers; no DB needed)                  #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    # fuse: RRF ordering + signal union
    a = [{"doc_id": "1", "page": "5"}, {"doc_id": "2", "page": "9"}]
    b = [{"doc": "2", "page": "9"}, {"doc": "3", "page": "1"}]
    f = fuse([("keyword", a), ("semantic", b)])
    top = f[0]
    assert (top.get("doc_id") or top.get("doc")) == "2", top          # in both lists -> ranked first
    assert top["_signals"] == ["keyword", "semantic"], top
    assert len(f) == 3, f
    print("hybrid fuse OK -> top=(doc 2, both signals), %d merged" % len(f))

    # expand_query with a tiny in-memory glossary DB
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE pages(document_id TEXT, page_number INT, body_text TEXT)")
    con.execute("INSERT INTO pages VALUES('d1',1,?)",
                ("LIST OF ABBREVIATIONS\nCTIS    Central Tire Inflation System\nGVWR - Gross Vehicle Weight Rating\n",))
    con.commit()
    import tempfile, os
    tmp = os.path.join(tempfile.gettempdir(), "hybrid_gloss.db")
    con.backup(sqlite3.connect(tmp)); con.close()
    _GLOSS["data"] = None
    ex = expand_query("bleed the CTIS lines", tmp)
    assert any(x["abbr"] == "CTIS" for x in ex["acronyms"]), ex
    assert "Central Tire Inflation System" in ex["expanded"], ex
    print("hybrid expand_query OK -> %r + %d acronym(s)" % (ex["query"], len(ex["acronyms"])))

    # nsn_did_you_mean is graceful without PUBLOG
    assert isinstance(nsn_did_you_mean("2530-01-234-567"), list)
    assert nsn_did_you_mean("bad") == []
    print("hybrid nsn_did_you_mean OK (graceful)")
    print("hybrid self-test PASS")

# END OF FILE
