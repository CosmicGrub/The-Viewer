#!/usr/bin/env python3
"""THE VIEWER -- search / suggest / hybrid+semantic search / analytics routes (v1.14 routes/ split).
Moved verbatim out of the former monolithic engine/features/routes.py. DI via `core`."""
import time
import threading as _threading

from features.registry import get, post, qstr, qint, qflag, safe_header_token

core = None          # injected by viewer_app at startup

# v0.97.0 (C23): small TTL'd LRU of identical query+filter result sets. The index only changes as
# OCR/ingest add pages, so a 60-second window is safe and absorbs repeat queries (paging back and
# forth, the palette re-running the last search) without touching SQLite.
_SEARCH_LRU = {}
_SEARCH_LRU_ORDER = []
_SEARCH_LRU_TTL = 60.0
_SEARCH_LRU_MAX = 200
_SEARCH_LRU_LOCK = _threading.Lock()          # v1.13: guard the read-modify-write under ThreadingHTTPServer


@get("/api/search")
def r_search(h, qs):
    mode = (qs.get("mode") or [None])[0]
    match_any = qflag(qs, "any")
    use_fuzzy = qstr(qs, "fuzzy", "1") != "0"
    q = qstr(qs, "q"); limit = qint(qs, "limit", 25, 1, 200)
    side = qstr(qs, "side")      # operator|mechanic -> keep only hits on that side of the house
    # v1.13 (#11/#15): fielded operators tm:/nsn:/vehicle:/side: parsed OUT of the query text; the
    # remaining free text goes through the normal pipeline. side: feeds the existing side filter
    # (an explicit ?side= param wins); tm:/vehicle:/nsn: become parameterized document filters.
    from features import search_feature as _sf
    q_free, ops = _sf.parse_operators(q)
    if ops.get("side") and side not in ("operator", "mechanic"):
        side = ops["side"]
    key = (q, limit, mode, match_any, use_fuzzy, side)
    now = time.time()
    with _SEARCH_LRU_LOCK:
        ent = _SEARCH_LRU.get(key)
    if ent is not None and (now - ent[0]) < _SEARCH_LRU_TTL:
        h._send(200, ent[1]); return
    # v1.13.4: side filtering happens AFTER the SQL LIMIT, so a naive `search(..., limit)` starves it --
    # operator-side docs are a minority of the corpus (~29%), so the top `limit` relevance-ranked hits can
    # easily contain zero of them even when plenty exist deeper in the corpus (confirmed live: "brake" /
    # "gasket" / "filter" returned 0 operator results despite being common, well-indexed terms). Over-fetch
    # a larger candidate pool whenever a side filter is active, then truncate back to the requested limit
    # after filtering -- the caller never sees fetch_limit, just a correctly-populated `limit`-sized page.
    fetch_limit = min(max(limit * 10, 200), 500) if side in ("operator", "mechanic") else limit
    results = core.search(q_free, fetch_limit, mode, match_any, use_fuzzy,
                          tm=ops.get("tm"), vehicle=ops.get("vehicle"), nsn=ops.get("nsn"))
    if side in ("operator", "mechanic"):
        results = [r for r in results
                   if core._side_classify(r.get("doc_id"), r.get("tm_number") or "", r.get("title") or "").get(side)][:limit]
    resp = {"results": results, "side": side or None}
    if ops:
        resp["operators"] = ops
    if not results and (q or "").strip():
        dym = core.did_you_mean(q_free or q)       # v0.97.0 (C20): offline zero-result suggestions
        if dym: resp["did_you_mean"] = dym
    # v1.13 (#19): zero-result GAP LOG -- remember what the corpus could NOT answer (append-only
    # sidecar via analytics.jsonl; kind='gap'). Best-effort: never lets logging break search.
    if not results and len((q or "").strip()) >= 3:
        try:
            import analytics
            analytics.log(core.INDEX_DIR, "gap", (q or "").strip())
        except Exception:
            try: core.log_exception("searchgap-log")
            except Exception: pass
    # v1.5: cheap, non-breaking search enrichers -- acronym glossary hints + fuzzy NSN 'did you mean'
    # (grounded in PUBLOG). Never alters ranking; just annotates. Fully guarded so search can't regress.
    if (q or "").strip():
        try:
            import hybrid
            ac = hybrid.expand_query(q, core.DB_PATH).get("acronyms") or []
            if ac: resp["acronyms"] = ac
            nsn_dym = hybrid.nsn_did_you_mean(q)
            if nsn_dym: resp["nsn_did_you_mean"] = nsn_dym
        except Exception:
            pass
    with _SEARCH_LRU_LOCK:                     # v1.13: atomic insert + eviction
        _SEARCH_LRU[key] = (now, resp); _SEARCH_LRU_ORDER.append(key)
        while len(_SEARCH_LRU_ORDER) > _SEARCH_LRU_MAX:
            old = _SEARCH_LRU_ORDER.pop(0); _SEARCH_LRU.pop(old, None)
    h._send(200, resp)


@get("/api/suggest")
def r_suggest(h, qs):
    h._send(200, core.suggest(qstr(qs, "q"), qint(qs, "limit", 8, 1, 40)))


@get("/api/findindoc")
def r_findindoc(h, qs):
    h._send(200, core.find_in_doc(qstr(qs, "doc", "0"), qstr(qs, "q")))


@get("/api/search_hybrid")
def r_search_hybrid(h, qs):
    # Glossary-expanded keyword search fused (RRF) with semantic search + fuzzy NSN 'did you mean'.
    # Degrades to keyword-only when embeddings aren't built; always returns keyword hits at minimum.
    import hybrid
    q = qstr(qs, "q"); limit = qint(qs, "limit", 25, 1, 200)
    h._send(200, hybrid.hybrid_search(q, core, core.INDEX_DIR, limit))


@get("/api/semantic")
def r_semantic(h, qs):
    import embed
    h._send(200, embed.search(qstr(qs, "q", ""), core.INDEX_DIR, qint(qs, "n", 15, 1, 100)))


@get("/api/analytics_top")
def r_analytics_top(h, qs):
    import analytics
    h._send(200, analytics.summary(core.INDEX_DIR))


@get("/api/searchgaps")
def r_searchgaps(h, qs):
    # v1.13 (#19): zero-result GAP LOG -- the queries the corpus could NOT answer, ranked by how
    # often they were asked. Fed automatically by r_search; read-only here (append-only sidecar).
    import analytics
    h._send(200, analytics.gaps(core.INDEX_DIR, qint(qs, "limit", 12, 1, 100)))


@post("/api/visualmatch")
def r_visualmatch(h, qs, payload):
    import phash, base64, io
    p = payload if isinstance(payload, dict) else {}
    data = p.get("image", "")
    if "," in data:
        data = data.split(",", 1)[1]   # strip data:image/...;base64,
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(base64.b64decode(data)))
    except Exception:
        h._send(400, {"error": "could not decode image"}); return
    h._send(200, phash.match(img, core.INDEX_DIR, top=qint(qs, "n", 12, 1, 40)))


@post("/api/analytics_log")
def r_analytics_log(h, qs, payload):
    import analytics
    p = payload if isinstance(payload, dict) else {}
    ok = analytics.log(core.INDEX_DIR, p.get("kind", "tool"), p.get("key", ""),
                       {k: p.get(k) for k in ("doc", "page", "nsn") if p.get(k) is not None})
    h._send(200, {"ok": bool(ok)})
