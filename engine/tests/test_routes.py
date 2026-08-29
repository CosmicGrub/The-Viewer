#!/usr/bin/env python3
"""Route smoke test: start the real server against the deterministic fixture index and hit every known
endpoint, asserting NO 5xx (the server never crashes on a normal request) and valid JSON on /api/* + /healthz.

Three passes: (1) a CURATED list with realistic params, asserting status/JSON shape; (2) a BLANKET SWEEP that
auto-discovers every registered GET route from registry.GET and hits it bare, asserting no 5xx; (3) a BLANKET
POST SWEEP (v1.13.0) that hits every registered POST route with an empty JSON body, asserting no 5xx. The
sweeps exist because a deep audit found 68 of 133 API routes had zero coverage -- auto-discovery from the
registry makes that impossible to repeat for GET *and* POST.

RUN ON WINDOWS / a coherent env -- it imports viewer_app, which a sandbox mount may serve truncated.
Pure stdlib runner."""
import os, sys, json, time, threading, tempfile, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)
import fixture

def _get(url, data=None):
    req = urllib.request.Request(url, data=(json.dumps(data).encode() if data is not None else None),
                                 headers={"Content-Type": "application/json"} if data is not None else {})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return -1, str(e).encode()

# (method, path, expect_json, must_200)
ROUTES = [
    ("GET",  "/",                                            False, True),
    ("GET",  "/healthz",                                     True,  False),  # 200 or 503 (both valid JSON)
    ("GET",  "/api/status",                                  True,  True),
    ("GET",  "/api/collections",                             True,  True),
    ("GET",  "/api/collections?slug=warnings",               True,  True),
    ("GET",  "/api/schematics",                              True,  True),
    ("GET",  "/api/threed",                                  True,  True),
    ("GET",  "/api/threed_refs?nsn=5305-01-674-1467",        True,  True),
    ("GET",  "/api/callouts?doc=2&page=12",                  True,  True),
    ("GET",  "/api/pagewords?doc=2&page=12",                 True,  True),
    ("GET",  "/api/doc?id=1",                                True,  True),
    ("GET",  "/api/vehicle?key=M915%20Truck",                True,  True),
    ("GET",  "/api/niin_review",                             True,  True),
    ("GET",  "/api/findindoc?doc=1&q=brake",                 True,  True),
    ("GET",  "/api/schempaths?doc=2&page=1",                 True,  True),   # schematic highlighter geometry
    ("GET",  "/api/procedure_full?q=brake",                  True,  True),   # reconstituted Fix/procedure
    ("GET",  "/api/by_side?side=operator",                   True,  True),   # operator (10) side of the house
    ("GET",  "/api/by_side?side=mechanic",                   True,  True),   # mechanic (20) side of the house
    ("GET",  "/api/by_side",                                 True,  True),   # side counts (no filter)
    ("GET",  "/api/side_uncertain",                          True,  True),   # low-confidence docs for review
    ("GET",  "/api/chapters?doc=1",                          True,  True),   # chapter->side ranges (combined manuals)
    ("GET",  "/api/chapter_jump?doc=1&side=operator",        True,  True),   # land on a side's first chapter
    ("GET",  "/api/chapters_review",                         True,  True),   # combined-manual chapter-split review
    ("GET",  "/api/part_image?nsn=5305-01-674-1467",         True,  True),   # a part's cited figure (JSON; found or not)
    ("GET",  "/figcrop?doc=1&page=1",                        False, False),  # PNG or 404 (no real PDF in fixture) -> no 5xx
    ("GET",  "/api/image3d?nsn=5305-01-674-1467",            True,  True),   # experimental image->3D status (unconfigured ok)
    ("GET",  "/api/image3d_mesh?nsn=5305-01-674-1467",       True,  False),  # 404 JSON when no generated mesh -> no 5xx
    ("GET",  "/api/part_by_number?pn=12420572-010",          True,  True),   # PN -> row + breakdown image (found or not)
    ("GET",  "/api/rpstl_review",                            True,  True),   # low-confidence rows (note when no sidecar)
    ("GET",  "/api/part_record?pn=12420572-010",            True,  True),   # unified cross-referenced record
    ("GET",  "/api/part_record?nsn=5305-01-674-1467",       True,  True),   # resolve by NSN too
    ("GET",  "/api/xref_coverage",                           True,  True),   # corpus resolution coverage
    ("GET",  "/api/xref_online",                             True,  True),   # X4 status (off by default)
    ("GET",  "/api/part_material?chars=MATERIAL:%20RUBBER;%20COLOR:%20BLACK", True, True),  # scan->material
    ("GET",  "/api/part_material?nsn=5305-01-674-1467",      True,  True),   # material from FLIS by NSN
    ("GET",  "/api/callout_crop?doc=1&page=1&item=7",        False, False),  # PNG or 404 -> no 5xx
    ("GET",  "/api/search?q=brake&side=mechanic",            True,  True),   # side-filtered search
    ("GET",  "/api/tags?nsn=5305-01-674-1467",               True,  True),   # per-part tags
    ("GET",  "/api/keywords",                                True,  True),   # user keyword groups
    ("GET",  "/healthz",                                     True,  False),
    ("GET",  "/collections",                                 False, True),
    ("GET",  "/keywords",                                    False, True),
    ("GET",  "/schematics",                                  False, True),
    ("GET",  "/3d",                                          False, True),
    ("GET",  "/dossier",                                     False, True),
    ("GET",  "/procedure",                                   False, True),
    ("GET",  "/solve",                                       False, True),
    ("GET",  "/status",                                      False, True),
    ("GET",  "/partgeo.js",                                  False, True),
    ("GET",  "/schemhl.js",                                  False, True),
    ("GET",  "/tagger.js",                                   False, True),
    ("POST", "/api/collections",                             True,  True),   # save (payload below)
    ("POST", "/api/tags",                                    True,  True),   # tag a part
    ("POST", "/api/keywords",                                True,  True),   # add a keyword group
    ("POST", "/api/niin_review_decision",                   True,  False),  # may 400 w/o sidecar fields -> still JSON, no 5xx
    ("POST", "/api/side_override",                           True,  True),   # pin a doc to a side of the house
    ("POST", "/api/chapter_override",                        True,  True),   # pin a side's landing page in a manual
    ("POST", "/api/image3d",                                 True,  False),  # generate (unconfigured -> 400 JSON, no 5xx)
    ("POST", "/api/rpstl_override",                          True,  True),   # correct a part-number row
    # ---- v1.4-1.7 endpoints (each degrades gracefully; asserts no 5xx, valid JSON on /api/*) ----
    ("GET",  "/api/partsummary?q=brake",                    True,  True),
    ("GET",  "/api/conflicts?q=brake",                      True,  True),
    ("GET",  "/api/faulttree?q=brake",                      True,  True),
    ("GET",  "/api/ask?q=how%20to%20remove%20the%20brake",  True,  True),
    ("GET",  "/api/search_hybrid?q=brake",                  True,  True),
    ("GET",  "/api/command_status",                         True,  True),
    ("GET",  "/api/dimscad?q=bolt",                         True,  True),
    ("GET",  "/api/publog?nsn=5305-01-674-1467",            True,  True),
    ("GET",  "/api/publog?pn=12420572-010",                 True,  True),
    ("GET",  "/api/publog_stats",                           True,  True),
    ("GET",  "/api/publog_intel?nsn=5305-01-674-1467",      True,  True),
    ("GET",  "/api/publogdiff?a=5305-01-674-1467&b=5305-01-674-1468", True, True),
    ("GET",  "/api/callout_numbers?doc=2&page=12",          True,  True),
    ("GET",  "/api/dimscan?doc=2&page=12",                  True,  True),
    ("GET",  "/api/layout?doc=2&page=12",                   True,  True),   # heuristic layout regions (catalog §2.4/§2.5)
    ("GET",  "/api/figureparts?doc=2&page=1",               True,  True),
    ("GET",  "/api/pageqa?doc=2&page=12&q=torque",          True,  True),   # vision-language page QA (catalog §10.1)
    ("GET",  "/api/jobpack?q=brake",                        False, False),
    ("GET",  "/api/specsheet?q=brake",                      False, False),
    ("GET",  "/part",                                       False, True),
    ("GET",  "/troubleshoot",                               False, True),
    ("GET",  "/ask",                                        False, True),
    ("GET",  "/command",                                    False, True),
    ("GET",  "/publog",                                     False, True),
    ("GET",  "/scan",                                       False, True),
    ("GET",  "/exploded",                                   False, True),
    ("GET",  "/binaudit",                                   False, True),
    ("GET",  "/mastercov",                                  False, True),
    ("GET",  "/scanner.js",                                 False, True),
    ("GET",  "/readaloud.js",                               False, True),
    # --- v1.12 reference decoders + tools (deep audit: these routes had NO coverage at all) ---
    ("GET",  "/api/standards?q=MS35338-46",                 True,  True),
    ("GET",  "/api/standards",                              True,  False),  # no q -> 400 JSON, never 5xx
    ("GET",  "/api/nsndecode?q=2320-01-565-4055",           True,  True),
    ("GET",  "/api/nsndecode?q=not-an-nsn",                 True,  True),   # graceful: decoded=None
    ("GET",  "/api/nsndecode",                              True,  False),  # 400
    ("GET",  "/api/smr?q=PAOZZ",                            True,  True),
    ("GET",  "/api/smr?q=NOTANSMRCODE",                     True,  True),   # graceful: decoded=None
    ("GET",  "/api/smr",                                    True,  False),  # 400
    ("GET",  "/api/cage?q=19207",                           True,  True),
    ("GET",  "/api/cage?q=1IO34",                           True,  True),   # invalid -> reasons, still 200
    ("GET",  "/api/cage",                                   True,  False),  # 400
    ("GET",  "/api/mac?text=0601%20Water%20Pump%20Inspect%200.2%20C",   True, True),
    ("GET",  "/api/mac?text=0601%20Water%20Pump%20Inspect%200.2%20C&component=pump", True, True),
    ("GET",  "/api/mac",                                    True,  False),  # 400
    ("GET",  "/api/harnesstrace?text=Connector%20J5%0APin%20A%20RED%20%2B24%20VDC%0AConnector%20J7%0A1%20RED%20%2B24%20VDC", True, True),
    ("GET",  "/api/harnesstrace",                           True,  False),  # 400
    ("GET",  "/api/form_2404",                              False, False),  # PDF, or 503 without reportlab
    ("GET",  "/api/form_2407",                              False, False),
    ("GET",  "/decode",                                False, True),
]
POST_BODY = {
    "/api/collections": {"action": "save", "name": "Smoke Test", "query": "brake OR gasket"},
    "/api/tags": {"action": "save", "nsn": "5305-01-674-1467", "name": "BOLT, MACHINE", "tag": "test tag"},
    "/api/keywords": {"action": "save", "terms": ["smoke", "test", "alias"]},
    "/api/niin_review_decision": {"niin": "016741467", "decision": "interchangeable", "by": "smoke"},
    "/api/side_override": {"doc_id": 1, "side": "operator", "by": "smoke"},
    "/api/chapter_override": {"doc_id": 1, "side": "operator", "page": 1},
    "/api/image3d": {"nsn": "5305-01-674-1467"},
    "/api/rpstl_override": {"pn": "12420572-010", "fields": {"nomenclature": "HOSE, NONMETALLIC"}},
}

def run():
    passed, failed = [], []
    tmp = tempfile.mkdtemp(prefix="viewer_routes_")
    db, _corr = fixture.build(tmp)
    import viewer_app
    viewer_app.DB_PATH = db                      # point the server at the fixture
    from features import search_feature as SF    # v1.13.6: keep the /api/tags & /api/keywords POST_BODY
    SF.KEYWORDS_USER_PATH = os.path.join(tmp, "keywords_user.json")  # writes out of the real tracked sidecar
    SF._load_synonyms()   # reset SYN against the override now, rather than relying on the first write's own
    # live-reload -- see test_hardening.py's identical fix for why.
    from http.server import ThreadingHTTPServer
    srv = ThreadingHTTPServer(("127.0.0.1", 0), viewer_app.Handler)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True); th.start()
    time.sleep(0.3)
    base = "http://127.0.0.1:%d" % port
    try:
        for method, path, expect_json, must_200 in ROUTES:
            body = POST_BODY.get(path) if method == "POST" else None
            status, raw = _get(base + path, body)
            label = "%s %s" % (method, path)
            if status == -1:
                failed.append((label, "request error: %s" % raw[:120].decode("utf-8", "ignore"))); continue
            if status >= 500:
                failed.append((label, "5xx: %d" % status)); continue
            if must_200 and status != 200:
                failed.append((label, "expected 200, got %d" % status)); continue
            if expect_json:
                try: json.loads(raw.decode("utf-8"))
                except Exception as e:
                    failed.append((label, "invalid JSON: %s" % e)); continue
            passed.append("%s -> %d" % (label, status))

        # --- blanket crash-sweep (deep audit v1.12.9) --------------------------------------------
        # Every registered GET route NOT curated above is hit BARE (no params). A 400/404/503 is a
        # correct answer to a bare request; only a 5xx is a bug. This means a newly added route can
        # never again ship with zero smoke coverage -- the sweep discovers it automatically.
        from features import registry
        covered = set()
        for _m, _p, _j, _o in ROUTES:
            covered.add(_p.split("?")[0])
        for path in sorted(registry.GET.keys()):
            if path in covered:
                continue
            status, raw = _get(base + path)
            label = "GET %s (bare sweep)" % path
            if status == -1:
                failed.append((label, "request error: %s" % raw[:80].decode("utf-8", "ignore"))); continue
            if status >= 500:
                failed.append((label, "5xx on a bare request: %d" % status)); continue
            passed.append("%s -> %d" % (label, status))

        # --- blanket POST crash-sweep (v1.13.0) --------------------------------------------------
        # Same principle as the GET sweep: every registered POST route NOT curated above gets an
        # EMPTY JSON body ({}). A handler must answer a bad/empty payload with 400/404/200 -- never
        # a 5xx crash. New POST routes are auto-covered the moment they are registered.
        covered_post = set()
        for _m, _p, _j, _o in ROUTES:
            if _m == "POST":
                covered_post.add(_p.split("?")[0])
        for path in sorted(registry.POST.keys()):
            if path in covered_post:
                continue
            status, raw = _get(base + path, {})
            label = "POST %s (empty-body sweep)" % path
            if status == -1:
                failed.append((label, "request error: %s" % raw[:80].decode("utf-8", "ignore"))); continue
            if status >= 500:
                failed.append((label, "5xx on an empty JSON body: %d" % status)); continue
            passed.append("%s -> %d" % (label, status))

        # --- /api/pageqa degrade-cleanly content check (vision-language page QA, catalog §10.1; design
        # doc 2026-08-24-vision-language-page-qa-design.md plan item 7) -- the curated hit above only
        # proves 200 + valid JSON, same as every other curated route. This repo's CI has neither a GPU
        # nor transformers/torch installed, so pageqa.ask() must ALWAYS degrade to available:false here --
        # confirm the actual body content, not just the status, so a future change that silently starts
        # claiming success with no real backend would fail this test loudly.
        status, raw = _get(base + "/api/pageqa?doc=2&page=12&q=torque")
        label = "GET /api/pageqa content (no VLM backend installed -> available:false)"
        if status != 200:
            failed.append((label, "expected 200, got %d" % status))
        else:
            try:
                body = json.loads(raw.decode("utf-8"))
            except Exception as e:
                failed.append((label, "invalid JSON: %s" % e))
            else:
                if body.get("available") is not False:
                    failed.append((label, "expected available:false with no VLM backend, got %r" % (body.get("available"),)))
                elif not body.get("note"):
                    failed.append((label, "expected a non-empty 'note' explaining why unavailable, got %r" % (body.get("note"),)))
                else:
                    passed.append("%s -> %d (available:false, note=%r)" % (label, status, body.get("note")))
    finally:
        srv.shutdown()
    return passed, failed

if __name__ == "__main__":
    p, f = run()
    for n in p: print("PASS", n)
    for n, why in f: print("FAIL", n, "->", why)
    print("\n%d passed, %d failed" % (len(p), len(f)))
    sys.exit(1 if f else 0)
