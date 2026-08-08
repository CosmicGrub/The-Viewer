#!/usr/bin/env python3
"""End-to-end smoke test of THE VIEWER over HTTP, exercising every feature the demo promises.
Chains real ids (search -> doc/page; threed -> nsn/figure) through the pipeline and reports status + shape.
Read-only. Default base http://127.0.0.1:8766 (a CLEAN test server, so it never touches the 8765 instance).
Writes index/diag_e2e.txt. Exit code = number of FAILED checks.
"""
import os, sys, json, urllib.request, urllib.error
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8766"
HERE = os.path.dirname(os.path.abspath(__file__))
out = []; fails = [0]
def p(s=""):
    print(s); out.append(str(s))

def get(path):
    req = urllib.request.Request(BASE + path, headers={"Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, (e.headers.get("Content-Type", "") if e.headers else ""), (e.read() or b"")
    except Exception as e:
        return "ERR", str(e), b""

def js(body):
    try: return json.loads(body.decode("utf-8", "replace"))
    except Exception: return None

def check(label, path, want="json", contains=None, nonempty_key=None):
    st, ct, body = get(path)
    ok = (st == 200)
    detail = ""
    j = None
    if ok and want == "json":
        j = js(body)
        if j is None: ok = False; detail = "not JSON"
        else:
            if isinstance(j, dict) and j.get("error"): ok = False; detail = "error: " + str(j.get("error"))[:80]
            if nonempty_key is not None:
                v = j.get(nonempty_key) if isinstance(j, dict) else None
                n = len(v) if hasattr(v, "__len__") else (v or 0)
                detail = "%s=%s" % (nonempty_key, n if not hasattr(v, "__len__") else len(v))
    elif ok and want == "html":
        txt = body.decode("utf-8", "replace")
        if contains and contains not in txt: ok = False; detail = "missing %r" % contains
        else: detail = "%d bytes" % len(body)
    elif ok and want == "png":
        if body[:8] != b"\x89PNG\r\n\x1a\n": ok = False; detail = "not a PNG (%r)" % bytes(body[:12])
        else: detail = "PNG %d bytes" % len(body)
    if not ok and not detail: detail = "status=%s type=%s" % (st, ct)
    if not ok: fails[0] += 1
    p("  [%s] %-26s %s  %s" % ("OK " if ok else "XX ", label, path[:54], detail))
    return j

def main():
    p("=== THE VIEWER end-to-end smoke test ===  base=%s" % BASE)
    p("")
    p("-- shell pages --")
    check("home", "/", "html", contains="Choose your side")
    check("demo/onboarding", "/demo", "html", contains="THE VIEWER")
    for pg in ["/3d", "/procedure", "/solve", "/partdiff", "/collections", "/ingest", "/circuitlab", "/ops", "/dossier", "/packet", "/stepflow", "/help", "/schematics", "/keywords", "/status"]:
        check("page "+pg, pg, "html", contains="<")
    p("")
    p("-- static assets --")
    for a in ["/partgeo.js", "/gl3d.js", "/circuitsim.js", "/circuitsim-worker.js", "/schemhl.js", "/rps.js", "/palette.js", "/tagger.js"]:
        st, ct, body = get(a); ok = (st == 200 and len(body) > 0)
        if not ok: fails[0]+=1
        p("  [%s] asset %-22s %d bytes" % ("OK " if ok else "XX ", a, len(body)))
    p("")
    p("-- health / sides --")
    check("healthz", "/healthz")
    check("ops", "/api/ops")
    check("by_side (counts)", "/api/by_side", nonempty_key="counts")
    check("side_uncertain", "/api/side_uncertain?limit=5")
    check("xref_coverage", "/api/xref_coverage")
    p("")

    # ---- SEARCH (both sides) + chain a doc/page ----
    p("-- search + predictive --")
    check("suggest (predictive)", "/api/suggest?q=eng&limit=6")
    doc_id = page = None
    for side in ["operator", "mechanic", ""]:
        path = "/api/search?q=engine&limit=8" + (("&side="+side) if side else "")
        j = check("search side=%s" % (side or "all"), path)
        if j and doc_id is None:
            items = j.get("results") or j.get("items") or j.get("hits") or []
            for it in items:
                d = it.get("doc_id") or it.get("document_id") or it.get("doc")
                pg = it.get("page") or it.get("page_number")
                if d and pg: doc_id, page = d, pg; break
    p("  -> chained doc_id=%s page=%s" % (doc_id, page))
    p("")

    p("-- manual page + find-in-manual --")
    if doc_id and page:
        check("page render (PNG)", "/page?doc=%s&page=%s&dpi=120" % (doc_id, page), "png")
        check("findindoc", "/api/findindoc?doc=%s&q=the" % doc_id)
        check("doc meta", "/api/doc?id=%s" % doc_id)
        check("pagewords", "/api/pagewords?doc=%s&page=%s" % (doc_id, page))
        check("callouts", "/api/callouts?doc=%s&page=%s" % (doc_id, page))
    else:
        p("  (no doc/page chained from search — skipping page checks)"); fails[0]+=1
    p("")

    p("-- procedure / torque --")
    check("procedure", "/api/procedure?q=starter&limit=4")
    check("procedure_full", "/api/procedure_full?q=starter")
    check("torque", "/api/torque?q=bolt")
    check("faultparts", "/api/faultparts?fault=engine%20overheats&limit=5")
    p("")

    # ---- 3D + figure + part record + part-diff ----
    p("-- 3-D parts + figures --")
    j = check("threed (figures-first)", "/api/threed?limit=6")
    nsn = None; img = None
    if j:
        p("     mode=%s total=%s items=%s" % (j.get("mode"), j.get("total"), len(j.get("items", []))))
        if j.get("mode") != "figures": p("     !! expected mode=figures (figures-first front-load)"); fails[0]+=1
        for it in j.get("items", []):
            if it.get("nsn"): nsn = it["nsn"]; img = it.get("image_url"); break
    p("  -> chained nsn=%s" % nsn)
    if img: check("figcrop (real figure PNG)", img, "png")
    else: p("  (no image_url on first 3-D card)"); fails[0]+=1
    if nsn:
        check("threed_refs (OCR hookup)", "/api/threed_refs?nsn=%s" % nsn)
        check("part_record (xref)", "/api/part_record?nsn=%s" % nsn)
        check("part_image", "/api/part_image?nsn=%s" % nsn)
        check("part_material", "/api/part_material?nsn=%s" % nsn)
    check("partdiff (look-alike)", "/api/partdiff?q=bolt&limit=20")
    p("")

    p("-- solve hub + collections + circuit --")
    check("collections (list)", "/api/collections")
    check("schematics (list)", "/api/schematics?limit=5")
    check("coverage", "/api/coverage")
    p("")

    p("-- ingest (add documents) --")
    check("ingest_status", "/api/ingest_status")
    p("")

    p("=== RESULT: %d checks FAILED ===" % fails[0])
    try: open(os.path.join(HERE, "..", "index", "diag_e2e.txt"), "w", encoding="utf-8").write("\n".join(out))
    except Exception: pass
    return fails[0]

if __name__ == "__main__":
    sys.exit(min(main(), 120))
