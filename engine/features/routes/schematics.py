#!/usr/bin/env python3
"""THE VIEWER -- collections / schematics / schem-graph / part-locate / figuresheet routes (v1.14
routes/ split). Moved verbatim out of the former monolithic engine/features/routes.py. DI via
`core`."""
import json
import os

from features.registry import get, post, qstr, qint, qflag, safe_header_token

core = None          # injected by viewer_app at startup


@get("/api/collections")
def r_collections(h, qs):
    slug = qstr(qs, "slug")
    if slug:
        h._send(200, core.smart_collection_eval(slug, qint(qs, "limit", 80, 1, 500), qint(qs, "offset", 0, 0)))
    else:
        h._send(200, core.smart_collections_list())


@get("/api/schematics")
def r_schematics(h, qs):
    h._send(200, core.schematics_list(qstr(qs, "q"), qint(qs, "limit", 60, 1, 200), qint(qs, "offset", 0, 0)))


@get("/api/schempaths")
def r_schempaths(h, qs):
    doc_i = qint(qs, "doc", 0); pg = qint(qs, "page", 1, 1)
    con = core.db(); r = con.execute("SELECT path FROM documents WHERE id=?", (doc_i,)).fetchone(); con.close()
    import schem_overlay
    h._send(200, schem_overlay.schem_paths((r["path"] if r else "") or "", pg))


@get("/api/schemgraph")
def r_schemgraph(h, qs):
    doc_i = qint(qs, "doc", 0); pg = qint(qs, "page", 1, 1)
    fresh = qstr(qs, "fresh", "0") in ("1", "true", "yes")
    con = core.db(); r = con.execute("SELECT path FROM documents WHERE id=?", (doc_i,)).fetchone(); con.close()
    pdf_path = (r["path"] if r else "") or ""
    import schemgraph
    cache_dir = os.path.join(core.INDEX_DIR, "schemcache")
    if fresh:
        g = schemgraph.graph_for(pdf_path, pg)
        try:
            os.makedirs(cache_dir, exist_ok=True)
            # safeguard.atomic_write, not a bare open(...,"w") + json.dump: same non-atomic-write
            # bug as schemgraph.ensure()'s own cache write (see the fix there) -- a crash mid-write
            # here left a truncated cache file that ensure()'s size>0 check then treated as valid
            # forever, on every subsequent non-fresh request for this page.
            import safeguard
            safeguard.atomic_write(schemgraph.cache_path(cache_dir, doc_i, pg), json.dumps(g))
        except Exception: pass
    else:
        g = schemgraph.ensure(cache_dir, doc_i, pg, pdf_path)
    # merge human review/overrides (step 2): manual component labels + verdict (append-only sidecar, R1/R6)
    try:
        import schemreview
        ov = schemreview.overrides_for(core.INDEX_DIR, doc_i, pg)
        if ov:
            g = dict(g); comps = list(g.get("comps") or [])
            for lb in ov.get("labels", []):
                comps.append({"ref": lb["ref"], "x": lb["x"], "y": lb["y"], "kind": "part", "source": "review"})
            g["comps"] = comps
            g["review"] = {"verdict": ov.get("verdict"), "by": ov.get("by"), "ts": ov.get("ts")}
            if ov.get("verdict") == "good":
                g["confidence"] = max(g.get("confidence", 0), 0.9)
    except Exception:
        pass
    h._send(200, g)


@get("/api/schemgraph_review")
def r_schemgraph_review(h, qs):
    import schemreview
    h._send(200, schemreview.queue(core.INDEX_DIR, qint(qs, "limit", 200, 1, 1000),
                                   qint(qs, "offset", 0, 0), qflag(qs, "all")))


@post("/api/schemgraph_review_decision")
def p_schemgraph_review(h, qs, payload):
    import schemreview
    r = schemreview.record(core.INDEX_DIR, payload.get("doc"), payload.get("page"),
            payload.get("verdict", ""), payload.get("labels") or [], payload.get("note", ""), payload.get("by", ""))
    h._send(200 if r.get("ok") else 400, r)


@get("/api/schemgraph_coverage")
def r_schemgraph_coverage(h, qs):
    import schemreview
    h._send(200, schemreview.coverage_summary(core.INDEX_DIR))


@get("/api/partlocate")
def r_partlocate(h, qs):
    import partlocate
    h._send(200, partlocate.locate(core.DB_PATH, qstr(qs, "q", ""), qint(qs, "limit", 250, 1, 1000)))


@get("/api/figureparts")
def r_figureparts(h, qs):
    # inverse of the locator: every part called out on a given doc/page (figure sheet)
    import figureparts
    h._send(200, figureparts.parts_on(core.DB_PATH, qint(qs, "doc", 0), qint(qs, "page", 0),
                                       qint(qs, "limit", 400, 1, 1000)))


@get("/api/figuresheet")
def r_figuresheet(h, qs):
    import figuresheet
    q = qstr(qs, "q", "").strip()
    if len(q) < 2:
        h._send(400, {"error": "q required (NSN, part number, or name)"}); return
    pdf = figuresheet.figuresheet(core.DB_PATH, core.INDEX_DIR, q, qint(qs, "dpi", 150, 72, 300), qint(qs, "n", 12, 1, 30))
    if pdf:
        fn = "figuresheet_" + (safe_header_token(q) or "part") + ".pdf"
        h._send(200, pdf, "application/pdf", {"Content-Disposition": "inline; filename=\"%s\"" % fn})
    else:
        h._send(404, {"error": "no figures found for that part"})


@post("/api/collections")
def p_collections(h, qs, payload):
    act = (payload.get("action") or "save").strip()
    if act == "delete":
        r = core.smart_collection_delete(payload.get("slug", ""))
    elif act == "pin":
        r = core.smart_collection_pin(payload.get("slug", ""), payload.get("pinned"))
    else:
        r = core.smart_collection_save(payload.get("name", ""), payload.get("query", ""),
                                       payload.get("vehicle", ""), payload.get("mtype", ""),
                                       payload.get("pinned"))
    h._send(200 if r.get("ok") else 400, r)
