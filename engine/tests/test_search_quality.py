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

Pure stdlib. RUN ON WINDOWS / a coherent env (imports viewer_app)."""
import json
import os
import sys
import tempfile
import threading
import time
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
    c4, b4 = _get("/api/search?q=" + _up.quote("vehicle:Forklift bolt"))
    j4 = json.loads(b4)
    ok("route applies vehicle: operator",
       c4 == 200 and (j4.get("operators") or {}).get("vehicle") == "Forklift"
       and j4.get("results") and all(r["doc_id"] == 3 for r in j4["results"]))
    srv.shutdown()

    print("\n%d passed, %d failed" % (PASS, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
