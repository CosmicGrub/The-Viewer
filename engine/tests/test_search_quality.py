#!/usr/bin/env python3
"""v0.97.0 search-quality acceptance (backlog C18/C20/C22/C23) on the deterministic fixture:

  C22  build_match passes explicit operators through: "quoted phrase" stays a phrase; a NEAR b
       becomes NEAR("a" "b", 10); plain queries build the same expression shape as before.
  C18  exact-match boost: a verbatim whole-query hit carries exact=True and sorts above
       non-exact rows (stable within bands).
  C20  did_you_mean: a one-letter typo of an indexed term suggests the real term; multi-word
       zero-hit queries fall back to the strongest single token.
  C23  /api/search LRU: an identical repeat query within the TTL is served from the cache
       (observable via features.routes._SEARCH_LRU) and matches byte-for-byte.
  v1.14 an operator-only zero-result query (e.g. "vehicle:brakee") never falls back to the raw,
       un-parsed q for did_you_mean (would otherwise leak the operator keyword into the suggestion).
  v1.14 /api/analytics_log -> /api/analytics_top round trip (schema agreement between analytics.log
       and analytics.summary/top, previously exercised on neither side).
  v1.14 /api/visualmatch: real base64 image decode + phash.match ranking against a built phash.tsv,
       plus the malformed-data-URI-without-a-comma edge case (clean 400, not a crash).

Pure stdlib (PIL/numpy used only for the optional visualmatch block, guarded by phash.available()).
RUN ON WINDOWS / a coherent env (imports viewer_app)."""
import json
import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)
import fixture                                            # noqa: E402

PORT = 8895
PASS = 0; FAIL = 0


def ok(name, cond):
    global PASS, FAIL
    print(("PASS " if cond else "FAIL ") + name)
    if cond: PASS += 1
    else: FAIL += 1


def _get(path):
    with urllib.request.urlopen("http://127.0.0.1:%d%s" % (PORT, path), timeout=10) as r:
        return r.status, r.read()


def _post(path, data):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path),
                                 data=json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def main():
    tmp = tempfile.mkdtemp()
    db, _corr = fixture.build(tmp)
    import viewer_app as V
    V.DB_PATH = db; V.INDEX_DIR = os.path.dirname(db)
    V._VOCAB_READY = False

    con = V.db()

    # ---- C22: operators ----
    m = V.build_match(con, "brake NEAR line")
    ok("NEAR operator builds NEAR()", m is not None and m.startswith('NEAR("brake" "line"'))
    m = V.build_match(con, '"brake line"')
    ok("quoted phrase kept as phrase", m is not None and '"brake line"' in m)
    m = V.build_match(con, '"brake line" valve')
    ok("phrase AND'd with loose terms", m is not None and '"brake line"' in m and "valve" in m)
    m_plain = V.build_match(con, "brake valve")
    ok("plain query unchanged shape", m_plain is not None and '"brake"' in m_plain and " AND " in m_plain)
    m_any = V.build_match(con, "brake valve", match_any=True)
    ok("ANY mode still ORs", m_any is not None and " OR " in m_any)

    # ---- C18: exact boost ----
    rows = V.search("brake", limit=20)
    ok("search returns rows", bool(rows))
    if rows:
        ex = [r for r in rows if r.get("exact")]
        ok("verbatim hit flagged exact", bool(ex))
        first_band = [r.get("exact", False) for r in rows]
        ok("exact rows sort first (stable bands)",
           first_band == sorted(first_band, reverse=True))

    # ---- recommendations annex #13 (fuzzy-match-badge): a synonym-only hit is flagged approx,
    # a literal hit is not, and the two don't cross-contaminate each other's rows ----
    import features.search_feature as _SF
    orig_syn = dict(_SF.SYN)
    con2 = V.db()
    con2.execute("INSERT INTO pages(id,document_id,page_number,body_text,char_count,source) VALUES"
                "(8,1,8,'Replace the door seal before the winter season begins.',53,'text')")
    con2.execute("INSERT INTO pages_fts(rowid,body_text) SELECT id,body_text FROM pages WHERE id=8")
    con2.commit(); con2.close()
    try:
        _SF.SYN = dict(orig_syn); _SF.SYN["gasket"] = ["seal"]
        rows_g = V.search("gasket", limit=20)
        by_page = {r["page_number"]: r for r in rows_g}
        ok("fuzzy_match_badge_literal_gasket_page_is_exact_not_approx",
           7 in by_page and by_page[7].get("exact") is True and not by_page[7].get("approx"))
        ok("fuzzy_match_badge_synonym_only_seal_page_is_flagged_approx",
           8 in by_page and by_page[8].get("approx") is True and not by_page[8].get("exact"))
        ok("fuzzy_match_badge_approx_row_names_the_matched_synonym",
           8 in by_page and by_page[8].get("matched_via") == "synonym"
           and by_page[8].get("matched_term") == "seal")
        idx_of = {r["page_number"]: i for i, r in enumerate(rows_g)}
        ok("fuzzy_match_badge_approx_row_sorts_below_the_exact_row",
           7 in idx_of and 8 in idx_of and idx_of[7] < idx_of[8])
    finally:
        _SF.SYN = orig_syn   # restore -- other tests in this same process must see the real table

    # ---- C20: did-you-mean ----
    V._VOCAB_READY = False
    dym = V.did_you_mean("brale")               # one substitution from 'brake' (indexed)
    ok("typo suggests indexed term", any("brake" in s for s in dym))
    dym2 = V.did_you_mean("zzqqx brake")        # multi-word zero-hit -> strongest-token fallback
    ok("multi-word fallback offered", "brake" in dym2 or any("brake" in s for s in dym2))
    ok("did_you_mean bounded", len(V.did_you_mean("brale washer gasket")) <= 3)

    # ---- v1.13 (#11/#15): fielded search operators ----
    import features.search_feature as SF
    free, ops = SF.parse_operators('vehicle:"M915 Truck" tm:363 brake side:operator')
    ok("operators parsed out of query",
       free == "brake" and ops.get("vehicle") == "M915 Truck" and ops.get("tm") == "363"
       and ops.get("side") == "operator")
    free2, ops2 = SF.parse_operators("system: check customtm:x")
    ok("non-operator colons untouched", ops2 == {} and "system" in free2 and "customtm:x" in free2)
    free3, ops3 = SF.parse_operators("side:bogus bolt")
    ok("invalid side: dropped, free text kept", "side" not in ops3 and free3 == "bolt")

    rows_all = V.search("bolt", limit=20)
    rows_fork = V.search("bolt", limit=20, vehicle="Forklift")
    ok("vehicle: filter narrows to that vehicle",
       bool(rows_all) and bool(rows_fork)
       and {r["doc_id"] for r in rows_fork} == {3}
       and len({r["doc_id"] for r in rows_all}) > 1)
    rows_tm = V.search("bolt", limit=20, tm="3930")
    ok("tm: filter narrows to that TM", bool(rows_tm) and all("3930" in (r["tm_number"] or "") for r in rows_tm))
    rows_bare_nsn = V.search("", limit=20, nsn="5029")
    ok("bare nsn: routes through the NSN path (last-4)",
       bool(rows_bare_nsn) and rows_bare_nsn[0]["nsn"] == "2320-01-272-5029")
    ok("plain query unchanged by operator kwargs defaults",
       [r["doc_id"] for r in V.search("bolt", limit=20)] == [r["doc_id"] for r in rows_all])
    con.close()

    # ---- C23: route LRU (live server) ----
    from http.server import ThreadingHTTPServer
    import features.routes as R
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), V.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); time.sleep(0.4)
    R._SEARCH_LRU.clear(); R._SEARCH_LRU_ORDER[:] = []
    c1, b1 = _get("/api/search?q=brake&limit=5")
    n_after_first = len(R._SEARCH_LRU)
    c2, b2 = _get("/api/search?q=brake&limit=5")
    ok("search 200 twice", c1 == 200 and c2 == 200)
    ok("LRU populated once", n_after_first == 1 and len(R._SEARCH_LRU) == 1)
    ok("cached repeat identical", b1 == b2)
    c3, b3 = _get("/api/search?q=zzqqxnotaword")
    body = json.loads(b3)
    ok("zero-result carries did_you_mean key shape", c3 == 200 and "results" in body)
    # v1.13 (#11/#15): operators live end-to-end through the route
    import urllib.parse as _up
    # v1.14 fix: an operator-only zero-result query ("vehicle:brakee" -- no such vehicle) must NOT
    # fall back to the RAW un-parsed q for did_you_mean. "brakee" is one edit from the well-attested
    # corpus term "brake" (3 pages), so the old code (did_you_mean(q_free or q)) tokenized the raw
    # string and returned did_you_mean=["vehicle brake"] -- a nonsensical mash of the operator
    # keyword "vehicle" and a fuzzy match of the operator's VALUE. Fixed: q_free is "" here (the
    # whole query was operator syntax), so did_you_mean("") is a no-op and the key is absent.
    c3b, b3b = _get("/api/search?q=" + _up.quote("vehicle:brakee"))
    j3b = json.loads(b3b)
    ok("operator-only zero-result query returns no results",
       c3b == 200 and j3b.get("results") == [])
    ok("operator-only zero-result: did_you_mean does not leak the operator keyword",
       "did_you_mean" not in j3b)
    c4, b4 = _get("/api/search?q=" + _up.quote("vehicle:Forklift bolt"))
    j4 = json.loads(b4)
    ok("route applies vehicle: operator",
       c4 == 200 and (j4.get("operators") or {}).get("vehicle") == "Forklift"
       and j4.get("results") and all(r["doc_id"] == 3 for r in j4["results"]))

    # ---- v1.14: /api/analytics_log -> /api/analytics_top round trip -------------------------
    # Neither side was ever exercised together: a schema drift between what analytics.log() writes
    # and what analytics.summary()/top() read back would go unnoticed. V.INDEX_DIR is the isolated
    # fixture tmp dir (set above), so this never touches the real repo's index/analytics.jsonl.
    import analytics as _an
    _an_path = os.path.join(V.INDEX_DIR, _an.FNAME)
    if os.path.exists(_an_path):
        os.remove(_an_path)              # isolate from any earlier run against this same INDEX_DIR
    c5, b5 = _post("/api/analytics_log", {"kind": "search", "key": "torque wrench"})
    c6, b6 = _post("/api/analytics_log", {"kind": "part", "key": "5305-01-674-1467", "doc": 2, "page": 13})
    ok("analytics_log 200 + ok:true (search)", c5 == 200 and json.loads(b5).get("ok") is True)
    ok("analytics_log 200 + ok:true (part)", c6 == 200 and json.loads(b6).get("ok") is True)
    c7, b7 = _get("/api/analytics_top")
    top = json.loads(b7)
    ok("analytics_top reflects both logged events", c7 == 200 and top.get("events", 0) >= 2)
    ok("analytics_top by_kind carries what was just logged",
       top.get("by_kind", {}).get("search", 0) >= 1 and top.get("by_kind", {}).get("part", 0) >= 1)
    ok("analytics_top top_searches round-trips the logged key",
       any(t.get("key") == "torque wrench" for t in top.get("top_searches") or []))
    ok("analytics_top top_parts round-trips the logged key",
       any(t.get("key") == "5305-01-674-1467" for t in top.get("top_parts") or []))

    # ---- v1.14: /api/visualmatch -- real image decode + phash.match ranking -----------------
    # Previously neither phash nor this route had ANY coverage; only the "no image at all" 400
    # branch was incidentally hit by test_routes.py's blanket empty-body POST sweep. This exercises
    # the actual decode + Hamming-distance ranking against a real phash.tsv, plus the malformed
    # data-URI-without-a-comma edge case that would previously fail decode indistinguishably from
    # "no image at all".
    import phash as _ph
    if _ph.available():
        from PIL import Image as _PILImage, ImageDraw as _PILDraw
        import base64 as _b64, io as _io
        figcache = os.path.join(tmp, "figcache"); os.makedirs(figcache, exist_ok=True)

        def _mk_crop(name, fill):
            im = _PILImage.new("RGB", (64, 64), "white")
            _PILDraw.Draw(im).rectangle([8, 8, 56, 56], fill=fill)
            im.save(os.path.join(figcache, name))
            return im

        near_im = _mk_crop("nearcrop.png", "black")
        _mk_crop("farcrop.png", "white")           # plain white square -- visually far from a black one
        n_indexed = _ph.build_index(figcache, os.path.join(V.INDEX_DIR, _ph.HASH_TSV))
        ok("phash index built for both crops", n_indexed == 2)

        buf = _io.BytesIO(); near_im.resize((50, 50)).save(buf, format="PNG")   # resized copy of "near"
        b64 = _b64.b64encode(buf.getvalue()).decode()
        c8, b8 = _post("/api/visualmatch", {"image": "data:image/png;base64," + b64})
        vm = json.loads(b8)
        ok("visualmatch 200 + ready", c8 == 200 and vm.get("ready") is True)
        ok("visualmatch finds real results", bool(vm.get("results")))
        if vm.get("results"):
            ok("visualmatch ranks the near-identical crop first",
               vm["results"][0]["name"] == "nearcrop.png")

        c9, b9 = _post("/api/visualmatch", {"image": "data:image/png;base64garbage-no-comma-here"})
        ok("visualmatch: malformed data URI (no comma) -> clean 400, not a crash",
           c9 == 400 and "error" in json.loads(b9))
        os.remove(os.path.join(V.INDEX_DIR, _ph.HASH_TSV))
    else:
        ok("visualmatch block skipped (PIL/numpy unavailable in this env)", True)

    srv.shutdown()

    print("\n%d passed, %d failed" % (PASS, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
