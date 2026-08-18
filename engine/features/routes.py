#!/usr/bin/env python3
"""THE VIEWER -- every HTTP route, declared in one place (backlog A5/A7, v0.96.0).

Each handler is `fn(h, qs)` for GET or `fn(h, qs, payload)` for POST, where `h` is the live
Handler (use h._send) and qs is the parse_qs dict. Handlers run inside viewer_app's single
error boundary (B9): raise registry.ParamError -> 400; FileNotFoundError -> 404; anything
else -> logged 500 with a generic body (J69). Param parsing goes through registry.qint/qstr/
qflag (B11) so malformed input never 500s. Behavior is otherwise IDENTICAL to the monolith's
if/elif chains (moved verbatim). DI via `core`."""
import json
import os
import re
import sys
import tempfile
import time

from features.registry import get, post, qstr, qint, qflag

core = None          # injected by viewer_app at startup
ENGINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI_DIR = os.path.join(ENGINE_DIR, "ui")


# ---- static pages + scripts (declarative; was ~30 separate if-blocks) ---------------------------

_PAGES = {  # route(+aliases) -> ui file
    ("/", "/index.html"): ("index.html", None),
    ("/ops", "/ops.html"): ("ops.html", None),
    ("/ingest", "/ingest.html"): ("ingest.html", None),
    ("/status",): ("status.html", None),
    ("/3d", "/3d.html"): ("threed.html", "no-cache"),
    ("/demo", "/demo.html", "/onboarding"): ("demo.html", "no-cache"),
    ("/circuitlab", "/circuitlab.html"): ("circuitlab.html", None),
    ("/keywords", "/keywords.html"): ("keywords.html", None),
    ("/schematics", "/schematics.html"): ("schematics.html", None),
    ("/collections", "/collections.html"): ("collections.html", None),
    ("/partdiff", "/partdiff.html"): ("partdiff.html", None),
    ("/procedure", "/procedure.html"): ("procedure.html", None),
    ("/solve", "/solve.html"): ("solve.html", None),
    ("/packet", "/packet.html"): ("packet.html", None),
    ("/dossier", "/dossier.html"): ("dossier.html", None),
    ("/stepflow", "/stepflow.html"): ("stepflow.html", None),
    ("/help", "/help.html"): ("help.html", None),
    ("/deepzoom", "/deepzoom.html"): ("deepzoom.html", "no-cache"),
    ("/coverage", "/coverage.html"): ("coverage.html", "no-cache"),
    ("/locate", "/locate.html"): ("locate.html", "no-cache"),
    ("/jobcard", "/jobcard.html"): ("jobcard.html", "no-cache"),
    ("/torque", "/torque.html"): ("torque.html", "no-cache"),
    ("/decode", "/decode.html", "/reference-codes"): ("decode.html", "no-cache"),
    ("/bench", "/bench.html"): ("bench.html", "no-cache"),
    ("/fastener", "/fastener.html"): ("fastener.html", "no-cache"),
    ("/pmcs", "/pmcs.html"): ("pmcs.html", "no-cache"),
    ("/semantic", "/semantic.html"): ("semantic.html", "no-cache"),
    ("/related", "/related.html"): ("related.html", "no-cache"),
    ("/visual", "/visual.html"): ("visual.html", "no-cache"),
    ("/measures", "/measures.html"): ("measures.html", "no-cache"),
    ("/master", "/master.html"): ("master.html", "no-cache"),
    ("/mastercov", "/mastercov.html"): ("mastercov.html", "no-cache"),
    ("/audit", "/audit.html"): ("audit.html", "no-cache"),
    ("/publog", "/publog.html"): ("publog.html", "no-cache"),
    ("/scan", "/scan.html"): ("scan.html", "no-cache"),
    ("/exploded", "/exploded.html", "/assembly"): ("exploded.html", "no-cache"),
    ("/binaudit", "/binaudit.html"): ("binaudit.html", "no-cache"),
    ("/part", "/part.html"): ("part.html", "no-cache"),
    ("/troubleshoot", "/troubleshoot.html", "/faulttree"): ("troubleshoot.html", "no-cache"),
    ("/ask", "/ask.html"): ("ask.html", "no-cache"),
    ("/command", "/command.html"): ("command.html", "no-cache"),
    ("/verify", "/verify.html"): ("verify.html", "no-cache"),
    ("/review", "/review.html", "/signoff"): ("review.html", "no-cache"),
    ("/learn", "/learn.html", "/quiz"): ("learn.html", "no-cache"),
    ("/readiness", "/readiness.html", "/fluids"): ("readiness.html", "no-cache"),
}

_SCRIPTS = {  # route -> (ui file, Cache-Control)
    "/tagger.js": ("tagger.js", "max-age=3600"),
    "/partgeo.js": ("partgeo.js", "no-cache"),
    "/partview.js": ("partview.js", "no-cache"),
    "/cadview.js": ("cadview.js", "max-age=3600"),
    "/loupe.js": ("loupe.js", "no-cache"),
    "/schemhl.js": ("schemhl.js", "max-age=3600"),
    "/schemflow.js": ("schemflow.js", "max-age=3600"),
    "/gl3d.js": ("gl3d.js", "no-cache"),
    "/circuitsim.js": ("circuitsim.js", "max-age=3600"),
    "/circuitsim-worker.js": ("circuitsim-worker.js", "max-age=3600"),
    "/rps.js": ("rps.js", "max-age=600"),
    "/palette.js": ("palette.js", "max-age=600"),
    "/shared.js": ("shared.js", "max-age=600"),       # v0.96.0 (A2): the one copy of the page helpers
    "/deepzoom.js": ("deepzoom.js", "max-age=3600"),  # v0.99.3: offline deep-zoom + callout hotspots
    "/scanner.js": ("scanner.js", "max-age=600"),     # v1.5: global hand-scanner (keyboard-wedge) listener
    "/readaloud.js": ("readaloud.js", "max-age=600"), # v1.7: offline read-aloud (TTS) + voice input
}


def _serve_ui(h, fname, ctype, cache=None):
    try:
        body = open(os.path.join(UI_DIR, fname), "r", encoding="utf-8").read()
    except FileNotFoundError:
        h._send(404, fname + " not found"); return
    extra = {"Cache-Control": cache} if cache else None
    h._send(200, body, ctype, extra)


def _mk_page(fname, cache):
    def handler(h, qs):
        _serve_ui(h, fname, "text/html; charset=utf-8", cache)
    return handler


def _mk_script(fname, cache):
    def handler(h, qs):
        _serve_ui(h, fname, "application/javascript; charset=utf-8", cache)
    return handler


def register_static():
    from features import registry
    for paths, (fname, cache) in _PAGES.items():
        fn = _mk_page(fname, cache)
        for p in paths:
            registry.GET[p] = fn
    for p, (fname, cache) in _SCRIPTS.items():
        registry.GET[p] = _mk_script(fname, cache)
    registry.GET["/base.css"] = lambda h, qs: _serve_ui(h, "base.css", "text/css; charset=utf-8", "max-age=600")


register_static()


# ---- search & suggest ---------------------------------------------------------------------------

# v0.97.0 (C23): small TTL'd LRU of identical query+filter result sets. The index only changes as
# OCR/ingest add pages, so a 60-second window is safe and absorbs repeat queries (paging back and
# forth, the palette re-running the last search) without touching SQLite.
_SEARCH_LRU = {}
_SEARCH_LRU_ORDER = []
_SEARCH_LRU_TTL = 60.0
_SEARCH_LRU_MAX = 200
import threading as _threading
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


# ---- sides / chapters ----------------------------------------------------------------------------

@get("/api/by_side")
def r_by_side(h, qs):
    h._send(200, core._side_browse(qstr(qs, "side") or None, qstr(qs, "q"),
                                   qint(qs, "limit", 400, 1, 1000), qint(qs, "offset", 0, 0)))


@get("/api/side_uncertain")
def r_side_uncertain(h, qs):
    h._send(200, core._side_uncertain(qint(qs, "limit", 200, 1, 1000)))


@get("/api/chapters")
def r_chapters(h, qs):
    h._send(200, core._chapters(qint(qs, "doc", 0)))


@get("/api/chapter_jump")
def r_chapter_jump(h, qs):
    h._send(200, core._chapter_jump(qint(qs, "doc", 0), qstr(qs, "side")))


@get("/api/chapters_review")
def r_chapters_review(h, qs):
    h._send(200, core._chapters_review(qint(qs, "limit", 300, 1, 1000)))


# ---- part imagery / 3-D / CAD --------------------------------------------------------------------

@get("/api/part_image")
def r_part_image(h, qs):
    h._send(200, core._part_image(qstr(qs, "nsn"), qint(qs, "dpi", 150, 24, 400)))


@get("/api/image3d")
def r_image3d(h, qs):
    h._send(200, core._i3d.status(qstr(qs, "nsn")))


@get("/api/image3d_mesh")
def r_image3d_mesh(h, qs):
    vf = core._i3d.mesh_vf(qstr(qs, "nsn"))
    h._send(200 if vf else 404, vf or {"error": "no generated mesh"})


@get("/api/localmodel")
def r_localmodel(h, qs):
    h._send(200, core._lm.status(qstr(qs, "nsn")))


@get("/api/localmodel_mesh")
def r_localmodel_mesh(h, qs):
    vf = core._lm.mesh_vf(qstr(qs, "nsn"))
    h._send(200 if vf else 404, vf or {"error": "no local model"})


@get("/api/part_by_number")
def r_part_by_number(h, qs):
    h._send(200, core._pn_lookup(qstr(qs, "pn"), (qs.get("cagec") or [None])[0]))


@get("/api/part_record")
def r_part_record(h, qs):
    h._send(200, core._part_record((qs.get("pn") or qs.get("nsn") or [""])[0]))


@get("/api/xref_coverage")
def r_xref_coverage(h, qs):
    h._send(200, core._xref_coverage())


@get("/api/xref_online")
def r_xref_online(h, qs):
    h._send(200, core._xo.status())


@get("/api/part_material")
def r_part_material(h, qs):
    h._send(200, core._part_material(qstr(qs, "nsn"), qstr(qs, "chars"), qstr(qs, "name")))


@get("/api/rpstl_review")
def r_rpstl_review(h, qs):
    h._send(200, core._rpstl_review(qint(qs, "limit", 200, 1, 1000)))


@get("/api/callout_crop")
def r_callout_crop(h, qs):
    doc = qstr(qs, "doc", "0"); page = qstr(qs, "page", "1"); item = qstr(qs, "item")
    pth = core._callout_crop(doc, page, item) or core._fig_get_crop(doc, page)
    if pth: h._send(200, open(pth, "rb").read(), "image/png", {"Cache-Control": "max-age=86400"})
    else: h._send(404, {"error": "no crop"})


@get("/figcrop")
def r_figcrop(h, qs):
    # ONE handler for both callers (was a duplicate-route collision): ?name= -> figcache file (visual search);
    # otherwise ?doc=&page= -> the doc/page figure crop used by deepzoom / rpstl / xref / figures / dossier.
    import os
    name = os.path.basename(qstr(qs, "name", ""))
    if name:
        p = os.path.join(core.INDEX_DIR, "figcache", name)
        if not os.path.exists(p) or not name.lower().endswith((".png", ".jpg", ".jpeg")):
            h._send(404, {"error": "not found"}); return
        ctype = "image/png" if name.lower().endswith(".png") else "image/jpeg"
        try:
            with open(p, "rb") as f:
                h._send(200, f.read(), ctype, {"Cache-Control": "max-age=3600"})
        except Exception:
            h._send(404, {"error": "not found"})
        return
    pth = core._fig_get_crop(qstr(qs, "doc", "0"), qstr(qs, "page", "1"), qint(qs, "dpi", 150, 24, 400))
    if pth:
        h._send(200, open(pth, "rb").read(), "image/png", {"Cache-Control": "max-age=86400"})
    else:
        h._send(404, {"error": "no figure crop available"})


def _cad_row(nsn):
    row = None
    try:
        con = core.db(); row = con.execute("SELECT item_name, characteristics FROM ref_nsn WHERE nsn=? LIMIT 1", (nsn,)).fetchone(); con.close()
    except Exception: row = None
    return row


def _cad_name_chars(qs, row):
    name = (qs.get("name") or [(row["item_name"] if row else "") or ""])[0]
    chars = (qs.get("chars") or [(row["characteristics"] if row else "") or ""])[0]
    return name, chars


def _cad_style(qs, cad_render):
    style = qstr(qs, "style").strip().lower()
    if style not in ("v1", "v2", "v3"):
        tier = qstr(qs, "tier").strip().lower() or core.RPS_MODE
        style = cad_render.TIER_STYLE.get(tier, "v3")
    return style


@get("/cadimg")
def r_cadimg(h, qs):
    nsn = qstr(qs, "nsn").strip()
    if not nsn: h._send(404, {"error": "nsn required"}); return
    import cad_render
    row = _cad_row(nsn); name, chars = _cad_name_chars(qs, row)
    style = _cad_style(qs, cad_render)
    cdir = os.path.join(os.path.dirname(os.path.abspath(core.DB_PATH)), "cadcache")
    pth = cad_render.ensure(nsn, name, chars, cdir, style=style)
    if pth: h._send(200, open(pth, "rb").read(), "image/png", {"Cache-Control": "max-age=86400", "X-CAD-Style": style})
    else: h._send(404, {"error": "cad render unavailable"})


@get("/vectorize")
def r_vectorize(h, qs):
    doc_i = qint(qs, "doc", 0, 1); pg = qint(qs, "page", 1, 1); dpi = qint(qs, "dpi", 200, 72, 600)
    import vectorize
    if not vectorize.available():
        h._send(503, {"error": "vectorizer needs OpenCV (cv2) + numpy on the host"}); return
    con = core.db(); r = con.execute("SELECT path FROM documents WHERE id=?", (doc_i,)).fetchone(); con.close()
    pdf_path = (r["path"] if r else "") or ""
    cache_dir = os.path.join(core.INDEX_DIR, "veccache")
    p = vectorize.ensure(cache_dir, doc_i, pg, pdf_path, dpi)
    if p:
        h._send(200, open(p, "r", encoding="utf-8").read(), "image/svg+xml; charset=utf-8", {"Cache-Control": "max-age=86400"})
    else:
        h._send(404, {"error": "could not vectorize (not a page, or no ink found)"})


@get("/api/cadmaterial")
def r_cadmaterial(h, qs):
    nsn = qstr(qs, "nsn").strip()
    import cad_render
    row = _cad_row(nsn); name, chars = _cad_name_chars(qs, row)
    h._send(200, cad_render.material_for(name, chars, nsn))


@get("/cadspin")
def r_cadspin(h, qs):
    nsn = qstr(qs, "nsn").strip()
    if not nsn: h._send(404, {"error": "nsn required"}); return
    import cad_render
    row = _cad_row(nsn); name, chars = _cad_name_chars(qs, row)
    style = _cad_style(qs, cad_render)
    try: n = int(qstr(qs, "n"))
    except Exception: n = cad_render.SPIN_FRAMES.get(style, 24)
    cdir = os.path.join(os.path.dirname(os.path.abspath(core.DB_PATH)), "cadcache")
    pth, frames = cad_render.ensure_spin(nsn, name, chars, cdir, n=n, style=style)
    if pth:
        h._send(200, open(pth, "rb").read(), "image/png",
                {"Cache-Control": "max-age=86400", "X-CAD-Style": style, "X-CAD-Frames": str(frames), "X-CAD-FrameW": "440"})
    else: h._send(404, {"error": "cad spin unavailable"})


@get("/cadstl", "/cadobj")
def r_cadmesh(h, qs):
    nsn = qstr(qs, "nsn").strip()
    if not nsn: h._send(404, {"error": "nsn required"}); return
    import cad_render
    row = _cad_row(nsn); name, chars = _cad_name_chars(qs, row)
    V, F, fam = cad_render.mesh_for(name, chars, nsn)
    safe = re.sub(r"[^0-9A-Za-z]", "", nsn) or "part"
    if h._route_path == "/cadstl":
        body = cad_render.to_stl(V, F, name or nsn).encode("utf-8"); ext, ct = "stl", "model/stl"
    else:
        body = cad_render.to_obj(V, F).encode("utf-8"); ext, ct = "obj", "text/plain; charset=utf-8"
    h._send(200, body, ct, {"Content-Disposition": 'attachment; filename="%s.%s"' % (safe, ext)})


@get("/api/threed")
def r_threed(h, qs):
    figs_only = qstr(qs, "all", "0") != "1"   # default: front-load parts with real figures
    h._send(200, core.threed_list(qstr(qs, "q"), qint(qs, "limit", 60, 1, 200),
                                  qint(qs, "offset", 0, 0), figures_only=figs_only))


@get("/api/threed_refs")
def r_threed_refs(h, qs):
    h._send(200, core.threed_refs(qstr(qs, "nsn"), qstr(qs, "part"), qint(qs, "limit", 40, 1, 100)))


# ---- documents / vehicles / sessions --------------------------------------------------------------

@get("/api/doc")
def r_doc(h, qs):
    m = core.doc_meta(qint(qs, "id", 0))
    h._send(200 if m else 404, m or {"error": "not found"})


@get("/api/vehicles")
def r_vehicles(h, qs):
    h._send(200, {"vehicles": core.list_vehicles(qint(qs, "limit", 400, 1, 1000))})


@get("/api/vehicle")
def r_vehicle(h, qs):
    v = core.vehicle_hub(qstr(qs, "key"))
    h._send(200 if v else 404, v or {"error": "no vehicle found"})


@get("/api/sessions")
def r_sessions(h, qs):
    h._send(200, {"sessions": core.recent_sessions(qint(qs, "limit", 12, 1, 200))})


@get("/api/popular")
def r_popular(h, qs):
    h._send(200, {"items": core.popular_items(qint(qs, "limit", 12, 1, 100))})


@get("/api/techstatus")
def r_techstatus(h, qs):
    h._send(200, core.tech_status_suggest(qstr(qs, "vehicle"), qstr(qs, "fault"), qstr(qs, "parts")))


@get("/api/torque")
def r_torque(h, qs):
    h._send(200, core.torque_specs(qstr(qs, "q")))


@get("/api/pmcs")
def r_pmcs(h, qs):
    import pmcs
    h._send(200, pmcs.find(core.DB_PATH, qstr(qs, "vehicle", ""), qint(qs, "limit", 40, 1, 200)))


@get("/api/xref")
def r_xref(h, qs):
    import xref
    h._send(200, xref.related(core.DB_PATH, qstr(qs, "q", ""), qint(qs, "limit", 60, 1, 200)))


@get("/api/measures")
def r_measures(h, qs):
    # every measured quantity (dimensions/torque/pressure/capacity/electrical/…) for a part/vehicle, cited
    import measures
    h._send(200, measures.find_for_query(core.DB_PATH, qstr(qs, "q", ""), qint(qs, "limit", 40, 1, 120)))


def _page_gray(path, page, dpi=150):
    import fitz, numpy as np, os
    if not path or not os.path.exists(path):
        return None
    d = fitz.open(path); pix = d[page - 1].get_pixmap(dpi=dpi)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    d.close()
    return arr[:, :, :3] if arr.shape[2] >= 3 else arr


@get("/api/callout_numbers")
def r_callout_numbers(h, qs):
    # numeric callout labels on a figure page + optional link to leader lines (catalog §4.5).
    # NOTE: distinct from the older /api/callouts (page/schematic callout hotspots via core.page_callouts).
    import callouts, dimscan, sqlite3
    doc = qint(qs, "doc", 0); page = qint(qs, "page", 1); path = None
    path = core.doc_path(doc)          # v1.13: pooled + leak-free (was raw mode=ro connect closed inside try)
    cs = []
    if path and callouts.available():
        try:
            arr = _page_gray(path, page)
            cs = callouts.detect_callouts(arr) if arr is not None else []
            if cs and dimscan.available():
                cs = callouts.link_to_lines(cs, dimscan.detect_dimension_lines(arr))
        except Exception:
            cs = []
    iw = ih = 0
    try:
        if 'arr' in dir() and arr is not None:
            ih, iw = int(arr.shape[0]), int(arr.shape[1])   # so clients can scale hotspots exactly
    except Exception:
        iw = ih = 0
    h._send(200, {"doc": doc, "page": page, "available": callouts.available(),
                  "iw": iw, "ih": ih, "n": len(cs), "callouts": cs})


@get("/api/vlm")
def r_vlm(h, qs):
    # ask a page image a question via a pluggable vision-language backend (catalog §10.1). Degrades if none installed.
    import vlm, sqlite3
    doc = qint(qs, "doc", 0); page = qint(qs, "page", 1); q = qstr(qs, "q", "")
    if not vlm.available():
        h._send(200, {"doc": doc, "available": False,
                      "note": "No vision-language backend installed (needs a GPU + local model). Catalog §10.1."}); return
    path = None
    path = core.doc_path(doc)          # v1.13: pooled + leak-free (was raw mode=ro connect closed inside try)
    try:
        arr = _page_gray(path, page) if path else None
        res = vlm.ask(arr, q) if q else vlm.describe(arr)
    except Exception as e:
        res = {"available": True, "answer": None, "note": "error: %s" % e}
    h._send(200, {"doc": doc, "page": page, **res})


@get("/api/layout")
def r_layout(h, qs):
    # heuristic page layout: title/heading/paragraph/caption/header/footer/figure regions (catalog §2.4)
    import layout, sqlite3
    doc = qint(qs, "doc", 0); page = qint(qs, "page", 1, hi=100000)
    path = core.doc_path(doc)          # v1.13: pooled + leak-free (was raw mode=ro connect closed inside try)
    regions = []
    if path:
        try: regions = layout.analyze(path, page)          # v1.13: degrade to empty on a bad page, don't 500
        except Exception: regions = []
    h._send(200, {"doc": doc, "page": page, "available": layout.available(),
                  "summary": layout.summarize(regions), "regions": regions})


@get("/api/dimscan")
def r_dimscan(h, qs):
    # detect dimension/leader-line geometry (any angle) on a drawing page (catalog §4.6). Number-OCR is host-side.
    import dimscan, sqlite3
    doc = qint(qs, "doc", 0); page = qint(qs, "page", 1); path = None
    path = core.doc_path(doc)          # v1.13: pooled + leak-free (was raw mode=ro connect closed inside try)
    if not path or not dimscan.available():
        h._send(200, {"doc": doc, "page": page, "available": dimscan.available(), "lines": [], "summary": {}}); return
    lines = []
    try:
        import fitz, numpy as np, os
        if os.path.exists(path):
            d = fitz.open(path); pix = d[page - 1].get_pixmap(dpi=150)
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if arr.shape[2] >= 3:
                arr = arr[:, :, :3]
            d.close()
            lines = dimscan.detect_dimension_lines(arr)
    except Exception:
        lines = []
    h._send(200, {"doc": doc, "page": page, "available": True,
                  "summary": dimscan.summarize(lines), "lines": lines[:200]})


@get("/api/kg")
def r_kg(h, qs):
    # knowledge graph: everything one hop from a part/vehicle/spec (catalog §3.11/§7.4). Read-only on index/kg.db.
    import kg, os
    kgp = os.path.join(os.path.dirname(core.DB_PATH), "kg.db")
    h._send(200, {"available": os.path.exists(kgp), "stats": kg.stats(kgp),
                  **kg.neighbors(kgp, qstr(qs, "q", ""))})


@get("/api/ietm")
def r_ietm(h, qs):
    # parse a document as S1000D/IETM XML if its file is XML (catalog §6.2)
    import ietm, sqlite3
    doc = qint(qs, "doc", 0); path = None
    path = core.doc_path(doc)          # v1.13: pooled + leak-free (was raw mode=ro connect closed inside try)
    if not path or not ietm.is_ietm(path):
        h._send(200, {"doc": doc, "is_ietm": False, "note": "not an IETM/S1000D XML document"}); return
    d = ietm.parse(path)
    h._send(200, {"doc": doc, "is_ietm": True, "title": d["title"], "n_warnings": len(d["warnings"]),
                  "n_cautions": len(d["cautions"]), "n_steps": len(d["steps"]),
                  "n_measurements": len(d["measurements"]), **d})


@get("/api/acronyms")
def r_acronyms(h, qs):
    # per-document acronym glossary + the abbreviations actually used, expanded (catalog §3.10)
    import acronyms
    h._send(200, acronyms.find_for_doc(core.DB_PATH, qint(qs, "doc", 0)))


@get("/api/tables_plus")
def r_tables_plus(h, qs):
    # borderless (text-aligned) table extraction for a doc's page (catalog §2.2)
    import tables_plus, sqlite3
    doc = qint(qs, "doc", 0); page = qint(qs, "page", 0, hi=100000)
    path = core.doc_path(doc)          # v1.13: pooled + leak-free (was raw mode=ro connect closed inside try)
    tbls = []
    if path:
        try: tbls = tables_plus.borderless_tables(path, page)   # v1.13: degrade to empty on a bad page, don't 500
        except Exception: tbls = []
    h._send(200, {"doc": doc, "page": page, "available": tables_plus.available(), "tables": tbls})


@get("/api/cautions")
def r_cautions(h, qs):
    # every WARNING/CAUTION/NOTE/DANGER for a part/vehicle/task, severity-ranked + cited (catalog §3.9)
    import cautions
    h._send(200, cautions.find_for_query(core.DB_PATH, qstr(qs, "q", ""), qint(qs, "limit", 40, 1, 120)))


@get("/api/specs")
def r_specs(h, qs):
    # thread / fit-class / diameter / MIL-STD / fluid specs for a part/vehicle, cited (catalog §3.7/§3.8)
    import specparse
    h._send(200, specparse.find_for_query(core.DB_PATH, qstr(qs, "q", ""), qint(qs, "limit", 40, 1, 120)))


@get("/api/pdfmeta")
def r_pdfmeta(h, qs):
    # PDF-native objects: outline (chapter tree) + metadata for a document (catalog §5.1/§5.2)
    import pdfmeta, sqlite3
    doc = qint(qs, "doc", 0); path = None
    path = core.doc_path(doc)          # v1.13: pooled + leak-free (was raw mode=ro connect closed inside try)
    h._send(200, {"doc": doc, "available": pdfmeta.available(),
                  **(pdfmeta.summary(path) if path else {"metadata": {}, "n_outline": 0, "outline": []})})


@get("/api/provenance")
def r_provenance(h, qs):
    # INTERNAL AUDIT (operator, not mechanic): external gap-fills WITH their archived Wayback + original URLs, for
    # spot-checking sources. The only endpoint that surfaces links on purpose; mechanic views stay linkless (R11).
    if not _exposed_read_guard(h): return
    import enrich, os
    enr = os.path.join(os.path.dirname(core.DB_PATH), "enrich.db")
    subj = qstr(qs, "q", "") or None
    h._send(200, enrich.provenance_rows(enr, subject=subj, limit=qint(qs, "limit", 500, 1, 2000)))


@get("/api/master_coverage")
def r_master_coverage(h, qs):
    # Masterfile gap dashboard: per-subject dimension coverage + which of the 13 types are still missing
    import masterfile, os
    mp = os.path.join(os.path.dirname(core.DB_PATH), "masterfile.db")
    h._send(200, {"available": os.path.exists(mp), "subjects": masterfile.coverage(mp)})


@get("/api/specsheet")
def r_specsheet(h, qs):
    # one-page printable spec sheet (leading particulars) for a subject, from the Masterfile (no links)
    import specsheet, os
    if not specsheet.available():
        h._send(503, {"error": "reportlab not installed"}); return
    mp = os.path.join(os.path.dirname(core.DB_PATH), "masterfile.db")
    pdf = specsheet.for_subject(mp, qstr(qs, "q", ""))
    if not pdf:
        h._send(404, {"error": "no consolidated dimensions for that subject (build the Masterfile first)"}); return
    h._send(200, pdf, "application/pdf", {"Content-Disposition": "inline; filename=specsheet.pdf",
                                          "Cache-Control": "no-store"})


@get("/api/qr")
def r_qr(h, qs):
    # Offline QR for a part / NSN: encodes a deep-link to that part's dossier ON THIS SERVER so a
    # scan from a phone/second bay tablet on the same LAN jumps straight to it. Degrades gracefully
    # when no QR backend is installed.
    import qrgen
    q = qstr(qs, "q", "").strip()
    if len(q) < 2:
        h._send(400, {"error": "pass ?q=<part or NSN> (2+ chars)"}); return
    if not qrgen.available():
        h._send(503, {"ok": False, "unavailable": True,
                      "error": "QR support is not installed. Run: pip install segno"}); return
    # The base URL was previously built straight from the client-supplied Host header with no
    # validation -- any request could set Host: attacker.example and get back a QR code (which a
    # mechanic is told to scan with their phone) pointing at an attacker-controlled URL. Validated
    # against the actual bind address + an operator-configurable allowlist instead (finding #16) --
    # see core.safe_public_base().
    base = core.safe_public_base(h.headers.get("Host"))
    page = qstr(qs, "page", "/dossier") or "/dossier"
    try:
        scale = qint(qs, "scale", 6)
    except Exception:
        scale = 6
    mime, payload = qrgen.for_part(base, q, page=page, scale=scale)
    if mime is None:
        h._send(503, {"ok": False, "unavailable": True, "error": payload}); return
    # UX finding #9 (priority 5): safe_public_base() correctly falls back to 127.0.0.1 on the app's own
    # documented default deployment (loopback-only HOST, no VIEWER_ALLOWED_HOSTS configured) -- but a
    # QR code encoding 127.0.0.1 resolves to whatever device SCANS it, not this server, so it silently
    # fails on exactly the shipped default. That was already known (a console-only warning at startup),
    # but never reached the printed page making the "scan this" claim. Flag it here so the caller (e.g.
    # packet.html) can show an inline warning instead of an unqualified claim.
    local_only = base.lower().startswith(("http://127.0.0.1:", "http://localhost:", "http://[::1]:"))
    h._send(200, payload, mime, {"Cache-Control": "max-age=3600",
                                 "X-QR-Target": qrgen.deep_link(base, q, page),
                                 "X-QR-Local-Only": "1" if local_only else "0"})


@get("/api/publog")
def r_publog(h, qs):
    # Authoritative OFFLINE federal-catalog (PUBLOG/FLIS) lookup for an NSN/NIIN, or a reverse lookup
    # by manufacturer part number (?pn=). Degrades gracefully if the sidecar isn't built yet.
    import publog
    if not publog.available():
        h._send(200, {"ok": False, "unavailable": True,
                      "error": "PUBLOG data is not built yet. Run BUILD-PUBLOG.bat (host-side).",
                      "hint": "points at your 16GB DLA PUBLOG/FLIS CSV export"}); return
    pn = qstr(qs, "pn", "").strip()
    if pn:
        h._send(200, {"ok": True, "kind": "part_number", "query": pn, "matches": publog.by_part_number(pn)}); return
    q = qstr(qs, "nsn", "") or qstr(qs, "q", "")
    rec = publog.lookup(q)
    if not rec:
        h._send(200, {"ok": True, "found": False, "query": q}); return
    h._send(200, {"ok": True, "found": rec.get("found", False), "record": rec})


@get("/api/publog_stats")
def r_publog_stats(h, qs):
    import publog
    h._send(200, publog.stats())


@get("/api/publogdiff")
def r_publogdiff(h, qs):
    # authoritative look-alike diff between two NSNs/NIINs: characteristics diff + fit-fingerprint %
    # + interchangeability verdict (GREEN/AMBER/RED). Degrades if PUBLOG isn't built.
    import publogdiff
    if not publogdiff.available():
        h._send(200, {"ok": False, "unavailable": True, "error": "PUBLOG not built (BUILD-PUBLOG.bat)"}); return
    a = qstr(qs, "a", ""); b = qstr(qs, "b", "")
    if len(a) < 2 or len(b) < 2:
        h._send(400, {"error": "pass a= and b= (two NSNs/NIINs)"}); return
    h._send(200, {"ok": True, "diff": publogdiff.compare(a, b),
                  "verdict": publogdiff.interchangeability(a, b)})


@get("/api/publog_intel")
def r_publog_intel(h, qs):
    # single-part authoritative intelligence: supersession/AAC, reference-number confidence + vendor
    # status, nicknames (+clash), and the TM cross-links (TECH_DOC_NBR). All degrade independently.
    import publogdiff
    if not publogdiff.available():
        h._send(200, {"ok": False, "unavailable": True, "error": "PUBLOG not built (BUILD-PUBLOG.bat)"}); return
    q = qstr(qs, "nsn", "") or qstr(qs, "q", "")
    if len(q) < 2:
        h._send(400, {"error": "pass ?nsn="}); return
    h._send(200, {"ok": True, "supersession": publogdiff.supersession(q),
                  "references": publogdiff.reference_confidence(q), "vendors": publogdiff.vendor_status(q),
                  "nicknames": publogdiff.nicknames(q), "tech_docs": publogdiff.tech_docs(q),
                  "substitutes": publogdiff.substitutes(q)})


@get("/api/dimscad")
def r_dimscad(h, qs):
    # APPROXIMATE 3-D/CAD from a part's dimensional data: PUBLOG named characteristics -> a parametric
    # primitive + dimensioned isometric SVG + an OBJ mesh (add ?obj=1 to download the OBJ). Degrades to
    # an "not enough dimensional data" note. Never a substitute for the cited figure.
    import dimscad
    q = qstr(qs, "q", "") or qstr(qs, "nsn", "")
    if len(q) < 2:
        h._send(400, {"error": "q required (NSN / part / name)"}); return
    dims, item = {}, ""
    try:
        import publog
        if publog.available():
            rec = publog.lookup(q)
            if rec and rec.get("found"):
                item = rec.get("item_name", "") or ""
                dims = dimscad.dims_from_characteristics(rec.get("characteristics"))
    except Exception:
        pass
    res = dimscad.build(item or q, dims)
    if qflag(qs, "obj"):
        h._send(200, res["obj"], "text/plain; charset=utf-8",
                {"Content-Disposition": "inline; filename=approx_model.obj"}); return
    h._send(200, {"ok": True, "item_name": item or q, "primitive": res["primitive"],
                  "dims_in": res["dims_in"], "enough": res["enough"], "svg": res["svg"]})


@get("/api/master")
def r_master(h, qs):
    # the consolidated Masterfile view for a subject: corpus (authoritative, page-cited) + external (supplemental),
    # merged, raw + filtered. NO external links surfaced.
    import masterfile, os
    mp = os.path.join(os.path.dirname(core.DB_PATH), "masterfile.db")
    h._send(200, masterfile.for_subject(mp, qstr(qs, "q", "")))


@get("/api/external")
def r_external(h, qs):
    # external gap-fill (Internet Archive / Wayback) for a subject -- READ-ONLY on enrich.db, NO network.
    # Corpus is authoritative: pass the dimension types the corpus already answers so they're filtered out.
    import enrich, os
    q = qstr(qs, "q", "")
    have = [t.strip() for t in qstr(qs, "have", "").split(",") if t.strip()]
    enr = os.path.join(os.path.dirname(os.path.dirname(core.DB_PATH)), "index", "enrich.db")
    enr2 = os.path.join(os.path.dirname(core.DB_PATH), "enrich.db")
    path = enr if os.path.exists(enr) else (enr2 if os.path.exists(enr2) else enr)
    h._send(200, enrich.external_for_query(path, q, corpus_types=have))


@get("/api/tables")
def r_tables(h, qs):
    # structured tables (RPSTL / spec / leading-particulars) extracted from a doc's page
    import tables, sqlite3
    doc = qint(qs, "doc", 0); page = qint(qs, "page", 0)
    path = None
    try:
        con = core.db()          # v1.13: pooled (close() is a harmless no-op) -> no leak on error paths
        r = con.execute("SELECT path FROM documents WHERE id=?", (doc,)).fetchone()
        con.close()
        path = r[0] if r else None
    except Exception:
        path = None
    h._send(200, {"doc": doc, "page": page, "available": tables.available(),
                  "tables": tables.extract_page(path, page) if path else []})


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


@get("/api/partspdf")
def r_partspdf(h, qs):
    import partspdf, sqlite3
    q = qstr(qs, "q", "").strip()
    items = []
    if len(q) >= 2:
        try:
            from patterns import norm_nsn
            ref = norm_nsn(q)
            con = core.db()          # v1.13: pooled (close() is a harmless no-op) -> no leak on error paths
            for r in con.execute("SELECT DISTINCT nsn, name, part_number, cagec FROM parts "
                                  "WHERE nsn=? OR name=? COLLATE NOCASE OR part_number=? COLLATE NOCASE LIMIT 60",
                                  (ref, q, q)):
                items.append({"nsn": r[0], "name": r[1], "part_number": r[2], "cagec": r[3], "qty": 1})
            con.close()
        except Exception:
            items = []
    pdf = partspdf.build_pdf(items, {"tm": q})
    fn = "parts_request_" + ("".join(ch for ch in q if ch.isalnum() or ch in "-_")[:30] or "sheet") + ".pdf"
    h._send(200, pdf, "application/pdf", {"Content-Disposition": "inline; filename=\"%s\"" % fn})


@get("/api/procedure")
def r_procedure(h, qs):
    h._send(200, core.procedure_for(qstr(qs, "q"), qint(qs, "limit", 6, 1, 40)))


@get("/api/procedure_full")
def r_procedure_full(h, qs):
    import procedure_feature as _pf; _pf.core = core   # inject the running core module (no cycle; works as script OR import)
    h._send(200, _pf.procedure_full(qstr(qs, "q")))


# ---- parts / references ----------------------------------------------------------------------------

@get("/api/part")
def r_part(h, qs):
    h._send(200, core.part_lookup(qstr(qs, "nsn")))


@get("/api/partdiff")
def r_partdiff(h, qs):
    h._send(200, core.part_differences(qstr(qs, "q"), qint(qs, "limit", 80, 1, 200)))


@get("/api/correlations")
def r_correlations(h, qs):
    h._send(200, core.correlations_for(qstr(qs, "nsn")))


@get("/api/niin_review")
def r_niin_review(h, qs):
    h._send(200, core.niin_review(qint(qs, "limit", 200, 1, 1000), qint(qs, "offset", 0, 0),
                                  qflag(qs, "pending")))


@get("/api/faultparts")
def r_faultparts(h, qs):
    h._send(200, core.fault_parts(qstr(qs, "fault"), qint(qs, "limit", 10, 1, 100)))


@get("/api/reference")
def r_reference(h, qs):
    h._send(200, core.reference_for(qstr(qs, "nsn"), qstr(qs, "size")))


# ---- keywords / tags --------------------------------------------------------------------------------

@get("/api/keywords")
def r_keywords(h, qs):
    h._send(200, core.user_keywords_list())


@get("/api/tags")
def r_tags(h, qs):
    h._send(200, core.user_tags_for(qstr(qs, "nsn"), qstr(qs, "name")))


# ---- collections / schematics -----------------------------------------------------------------------

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


@get("/api/coverage")
def r_coverage(h, qs):
    # ONE handler (was a duplicate-route collision): ?vehicle= -> per-vehicle coverage (home-page widget);
    # otherwise the mission-control overview (the /coverage page and /ops page).
    v = qstr(qs, "vehicle")
    if v:
        cov = core.coverage(v)
        h._send(200, {"vehicle": v, "coverage": cov.get(v) if isinstance(cov, dict) else cov})
        return
    h._send(200, _coverage_overview_cached())


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
        fn = "figuresheet_" + ("".join(ch for ch in q if ch.isalnum() or ch in "-_")[:30] or "part") + ".pdf"
        h._send(200, pdf, "application/pdf", {"Content-Disposition": "inline; filename=\"%s\"" % fn})
    else:
        h._send(404, {"error": "no figures found for that part"})


def _jobcard_gather(qs):
    """Shared: pull procedures + torque + look-alike for a task from the LIVE features (core.db injected)."""
    from features import procedures_feature as PF
    from features import parts_feature as PARTS
    q = qstr(qs, "q", "").strip()
    try:    procs = PF.procedure_for(q, qint(qs, "np", 6, 1, 12)).get("procedures", [])
    except Exception: procs = []
    try:    tq = PF.torque_specs(q, qint(qs, "nt", 14, 1, 40)).get("specs", [])
    except Exception: tq = []
    try:    la = PARTS.part_differences(q, 40)
    except Exception: la = None
    return q, procs, tq, la


@get("/api/jobcard")
def r_jobcard(h, qs):
    # one printable Work Order for a task: procedures + tools + materials + cautions + torque + parts + figures
    import jobcard
    q, procs, tq, la = _jobcard_gather(qs)
    if len(q) < 2:
        h._send(400, {"error": "q required (task / part name, NSN, or part number)"}); return
    pdf = jobcard.jobcard(core.DB_PATH, q, procs, tq, lookalike=la,
                          dpi=qint(qs, "dpi", 150, 72, 300), max_figs=qint(qs, "nf", 8, 0, 20))
    if pdf:
        fn = "workorder_" + ("".join(ch for ch in q if ch.isalnum() or ch in "-_")[:30] or "task") + ".pdf"
        h._send(200, pdf, "application/pdf", {"Content-Disposition": "inline; filename=\"%s\"" % fn})
    else:
        h._send(404, {"error": "nothing resolved for that task (no procedures, torque, parts, or figures)"})


@get("/api/jobcard_preview")
def r_jobcard_preview(h, qs):
    # structured summary of what the Work Order would contain (no PDF build) -- powers the /jobcard builder page
    import jobcard
    q, procs, tq, la = _jobcard_gather(qs)
    if len(q) < 2:
        h._send(400, {"error": "q required"}); return
    h._send(200, jobcard.preview(core.DB_PATH, q, procs, tq, lookalike=la, max_figs=qint(qs, "nf", 8, 0, 20)))


def _jobpack_data(qs):
    """Gather the COMPLETE job-package payload for a part: procedures/torque/look-alike (shared) +
    Masterfile dims + PUBLOG identity/supersession + safety cautions. Every piece best-effort."""
    import os, time
    q, procs, tq, la = _jobcard_gather(qs)
    pkg = {"title": q, "generated": time.strftime("%Y-%m-%d"), "procedures": procs, "torque": tq}
    # parts to order (from the look-alike variants)
    try:
        if la and la.get("found") and la.get("variants"):
            pkg["parts"] = [{"nsn": v.get("nsn"), "uoc": ", ".join(v.get("uoc") or []),
                             "cagec": ", ".join(v.get("cagec") or []), "note": v.get("relation") or ""}
                            for v in la["variants"][:8]]
            pkg["title"] = la.get("nomenclature") or q
    except Exception:
        pass
    # consolidated dimensions (Masterfile) -- v1.13 R13: attach a real page CITE to each dim by cross-
    # referencing the cited+validated measures path, so /part honours its "every value cites the manual"
    # promise. Where no cited match is found, the dim is flagged consolidated-only (never a fake cite).
    try:
        import masterfile
        mp = os.path.join(os.path.dirname(core.DB_PATH), "masterfile.db")
        m = masterfile.for_subject(mp, q)
        dims = [dict(d) for d in (m.get("filtered") or [])[:14]]
        try:
            import measures, re as _re
            cited = measures.find_for_query(core.DB_PATH, q, 120).get("results") or []
            def _canon(v):
                return _re.sub(r"[^0-9a-z.]", "", str(v or "").lower())
            cite_by = {}
            for r in cited:
                cite_by.setdefault((r.get("type"), _canon(r.get("value"))), r.get("page_url"))
            for d in dims:
                pu = cite_by.get((d.get("type"), _canon(d.get("value"))))
                if pu:
                    d["page_url"] = pu; d["cited"] = True
                else:
                    d["cited"] = False          # consolidated value; verify on /measures (honest, not a fake cite)
        except Exception:
            pass
        pkg["dims"] = dims
    except Exception:
        pass
    # safety cautions
    try:
        import cautions
        cj = cautions.find_for_query(core.DB_PATH, q, limit=8) if hasattr(cautions, "find_for_query") else None
        # v1.13 FIX: the corpus refactor renamed the caution list key cautions->results; reading the old key
        # silently dropped SAFETY callouts from /part + the job package. Accept either (results preferred).
        if cj:
            pkg["cautions"] = cj.get("results") or cj.get("cautions") or []
    except Exception:
        pass
    # authoritative PUBLOG identity + supersession
    try:
        import publog, publogdiff
        if publog.available():
            rec = publog.lookup(q)
            if rec and rec.get("found"):
                pkg["nsn"] = rec.get("nsn"); pkg["item_name"] = rec.get("item_name") or pkg["title"]
                pkg["fsc_title"] = rec.get("fsc_title")
                sup = publogdiff.supersession(rec.get("niin") or q)
                if sup.get("available"):
                    pkg["supersession"] = sup
    except Exception:
        pass
    return q, pkg


@get("/api/jobpack")
def r_jobpack(h, qs):
    # THE COMPLETE job package for a part -> one printable PDF (identity + PUBLOG + alerts + parts + dims +
    # torque + cautions + procedure). Reuses every index; degrades section-by-section.
    import jobpack
    if not jobpack.available():
        h._send(503, {"error": "reportlab not installed"}); return
    q, pkg = _jobpack_data(qs)
    if len(q) < 2:
        h._send(400, {"error": "q required (part name / NSN / part number)"}); return
    pdf = jobpack.build(pkg)
    fn = "jobpackage_" + ("".join(ch for ch in q if ch.isalnum() or ch in "-_")[:30] or "part") + ".pdf"
    h._send(200, pdf, "application/pdf", {"Content-Disposition": "inline; filename=\"%s\"" % fn})


@get("/api/ask")
def r_ask(h, qs):
    # offline CITED question answering (extractive: retrieve pages, return the best-matching sentences +
    # their manual/page). No network, no LLM. Empty when nothing in the corpus matches.
    import ask
    q = qstr(qs, "q", "").strip()
    if len(q) < 3:
        h._send(400, {"error": "ask a question (3+ chars)"}); return
    h._send(200, ask.answer(core.DB_PATH, core.INDEX_DIR, q,
                            k=qint(qs, "k", 12, 4, 30), max_sentences=qint(qs, "n", 5, 1, 12)))


@get("/api/standards")
def r_standards(h, qs):
    # decode MS/AN/NAS/MIL-PRF/SAE/ASTM standard-hardware & spec designations found for a query (or given text)
    import standards
    q = qstr(qs, "q", "").strip()
    txt = qstr(qs, "text", "")
    if txt:
        h._send(200, {"ok": True, "standards": standards.scan(txt)}); return
    if len(q) < 2:
        h._send(400, {"error": "q or text required"}); return
    one = standards.classify(q)                     # is the query itself a designation?
    found = []
    for pg in _pages_for(q, 10):
        found += standards.scan(pg.get("body") or "")
    seen, ded = set(), []
    for c in found:
        if c["token"].upper() not in seen:
            seen.add(c["token"].upper()); ded.append(c)
    h._send(200, {"ok": True, "query": q, "designation": (one or None), "standards": ded[:40]})


@get("/api/nsndecode")
def r_nsndecode(h, qs):
    # decode the STRUCTURE of a NATO Stock Number: FSG/FSC group + NCB country + NIIN (deterministic)
    import nsndecode
    q = qstr(qs, "q", "").strip()
    txt = qstr(qs, "text", "")
    if txt:
        h._send(200, {"ok": True, "nsns": nsndecode.scan(txt)}); return
    if not q:
        h._send(400, {"error": "q or text required"}); return
    one = nsndecode.decode(q)
    if not one.get("valid"):
        h._send(200, {"ok": True, "query": q, "decoded": None, "note": "not a 13-digit NSN"}); return
    h._send(200, {"ok": True, "query": q, "decoded": one})


@get("/api/smr")
def r_smr(h, qs):
    # decode a 5-char SMR (Source, Maintenance, Recoverability) code, or scan given text for them
    import smrdecode
    q = qstr(qs, "q", "").strip()
    txt = qstr(qs, "text", "")
    if txt:
        h._send(200, {"ok": True, "codes": smrdecode.scan(txt)}); return
    if not q:
        h._send(400, {"error": "q or text required"}); return
    d = smrdecode.decode(q)
    if not d.get("valid"):
        h._send(200, {"ok": True, "query": q, "decoded": None, "note": "not a 5-character SMR code"}); return
    h._send(200, {"ok": True, "query": q, "decoded": d, "summary": smrdecode.summary(q)})


@get("/api/cage")
def r_cage(h, qs):
    # validate/classify a CAGE or NCAGE code (structure only). The company name comes from PUBLOG (/api/publog).
    import cage
    q = qstr(qs, "q", "").strip()
    txt = qstr(qs, "text", "")
    if txt:
        h._send(200, {"ok": True, "codes": cage.scan(txt)}); return
    if not q:
        h._send(400, {"error": "q or text required"}); return
    v = cage.validate(q)
    v["identity_note"] = "structure only; look up the assignee via PUBLOG (/api/publog)"
    h._send(200, {"ok": True, "query": q, "cage": v})


@get("/api/harnesstrace")
def r_harnesstrace(h, qs):
    # infer wiring continuity from pinouts: nets across connectors, or a trace from one connector/pin.
    import pinouts, harnesstrace
    txt = qstr(qs, "text", "")
    q = qstr(qs, "q", "").strip()
    if not txt and q:
        txt = "\n".join((pg.get("body") or "") for pg in _pages_for(q, 6))
    if not txt:
        h._send(400, {"error": "q or text required"}); return
    pins = pinouts.extract_pinouts(txt)
    conn, pin = qstr(qs, "connector", "").strip(), qstr(qs, "pin", "").strip()
    if conn and pin:
        h._send(200, {"ok": True, "trace": harnesstrace.trace(pins, conn, pin)}); return
    h._send(200, {"ok": True, "connectors": pins, "nets": harnesstrace.build_nets(pins)})


@get("/api/mac")
def r_mac(h, qs):
    # parse Maintenance Allocation Chart rows (function/level/man-hours) from the matched pages or given text
    import macchart
    txt = qstr(qs, "text", "")
    q = qstr(qs, "q", "").strip()
    if not txt and q:
        txt = "\n".join((pg.get("body") or "") for pg in _pages_for(q, 8))
    if not txt:
        h._send(400, {"error": "q or text required"}); return
    comp = qstr(qs, "component", "").strip()
    if comp:
        h._send(200, {"ok": True, "component": comp, "rows": macchart.for_component(txt, comp)}); return
    h._send(200, {"ok": True, "rows": macchart.extract_mac(txt)})


def _canon_folder_or_400(h, folder):
    """Shared VIEWER_INGEST_ROOTS fence for every route that takes a caller-supplied folder path
    (/api/ingest, /api/ingest_preview, /api/airgap_manifest, /api/airgap_verify, /api/ingest_scan).
    Returns the canonicalized folder on success, or None after already sending a 400 on failure --
    callers just do `folder = _canon_folder_or_400(h, folder); if folder is None: return`.
    Factored out so the fence can't be silently skipped by a future route the way
    /api/airgap_manifest and /api/ingest_scan originally were (they called ingestpipe.scan_folder()
    directly on the raw path), and /api/airgap_verify still was until this fix."""
    import features.ingest_feature as ingest_feature
    ok, real = ingest_feature.canon_ingest_path(folder)
    if not ok:
        h._send(400, {"error": real})
        return None
    return real


@post("/api/airgap_manifest")
def r_airgap_manifest(h, qs, payload):
    # build a SIGNED update-package manifest for a folder of manuals (air-gap transfer). Read-only.
    import airgap, ingestpipe, os
    folder = (payload.get("folder") or "").strip()
    secret = payload.get("secret") or ""
    if not folder or not secret:
        h._send(400, {"error": "folder and secret required"}); return
    # Same VIEWER_INGEST_ROOTS fence /api/ingest and /api/ingest_preview enforce -- this route
    # used to call scan_folder() on the raw path directly, bypassing the fence entirely (finding
    # from the audit: an operator who configures VIEWER_INGEST_ROOTS to restrict which folders may
    # be touched was still fully exposed via this endpoint).
    folder = _canon_folder_or_400(h, folder)
    if folder is None: return
    found = ingestpipe.scan_folder(folder)
    rels = [os.path.relpath(f["path"], folder) for f in found]
    h._send(200, {"ok": True, "manifest": airgap.make_manifest(folder, rels, secret,
                  label=payload.get("label", "viewer-update"))})


@post("/api/airgap_verify")
def r_airgap_verify(h, qs, payload):
    # verify a signed update package against a folder on the receiving side. Fail-closed.
    import airgap
    manifest = payload.get("manifest"); folder = (payload.get("folder") or "").strip(); secret = payload.get("secret") or ""
    if not (isinstance(manifest, dict) and folder and secret):
        h._send(400, {"error": "manifest (object), folder, and secret required"}); return
    # Same fence as the sibling airgap/ingest routes -- previously missing here specifically
    # (finding from the audit): manifest+secret are both caller-supplied in this same POST body,
    # so a caller can self-sign an arbitrary manifest and use `folder` to probe file
    # presence/hashes anywhere on the host, unrestricted by an operator's VIEWER_INGEST_ROOTS.
    folder = _canon_folder_or_400(h, folder)
    if folder is None: return
    h._send(200, {"ok": True, "result": airgap.verify(manifest, folder, secret)})


@post("/api/ingest_scan")
def r_ingest_scan(h, qs, payload):
    # scan a folder of manuals -> an ingestion plan (new vs already-in-corpus). Read-only over the folder.
    import ingestpipe
    folder = (payload.get("folder") or "").strip()
    if not folder:
        h._send(400, {"error": "folder path required"}); return
    # Same VIEWER_INGEST_ROOTS fence as /api/ingest and /api/airgap_manifest -- see the comment on
    # r_airgap_manifest above.
    folder = _canon_folder_or_400(h, folder)
    if folder is None: return
    found = ingestpipe.scan_folder(folder, recursive=bool(payload.get("recursive", True)))
    if not found:
        h._send(200, {"ok": True, "folder": folder, "found": 0,
                      "note": "no supported files found (or folder not accessible from the server)"}); return
    known_names = []
    try:
        import sqlite3
        con = core.db()          # v1.13: pooled (close() is a harmless no-op) -> no leak on error paths
        known_names = [r[0] for r in con.execute("SELECT DISTINCT filename FROM documents").fetchall() if r[0]]
        con.close()
    except Exception:
        known_names = []
    h._send(200, {"ok": True, "folder": folder, "found": len(found), **ingestpipe.plan(found, known_names=known_names)})


@get("/api/form_2404")
def r_form_2404(h, qs):
    # a blank DA-2404/5988-E style PMCS worksheet PDF (POST with fault data to fill it)
    import forms
    if not forms.available():
        h._send(503, {"error": "reportlab not installed"}); return
    pdf = forms.build_2404({"equipment": {"admin_no": qstr(qs, "admin", ""), "nomenclature": qstr(qs, "q", "")}})
    h._send(200, pdf, "application/pdf", {"Content-Disposition": "inline; filename=pmcs_2404_blank.pdf"})


@post("/api/form_2404")
def r_form_2404_post(h, qs, payload):
    # build a filled PMCS worksheet from logged faults
    import forms
    if not forms.available():
        h._send(503, {"error": "reportlab not installed"}); return
    pdf = forms.build_2404(payload or {})
    h._send(200, pdf, "application/pdf", {"Content-Disposition": "inline; filename=pmcs_2404.pdf"})


@get("/api/form_2407")
def r_form_2407(h, qs):
    # a blank DA-2407/5990-E style maintenance request PDF (POST with data to fill it)
    import forms
    if not forms.available():
        h._send(503, {"error": "reportlab not installed"}); return
    pdf = forms.build_2407({"organization": qstr(qs, "org", ""),
                            "equipment": {"admin_no": qstr(qs, "admin", ""), "nomenclature": qstr(qs, "q", ""),
                                          "nsn": qstr(qs, "nsn", "")}})
    h._send(200, pdf, "application/pdf", {"Content-Disposition": "inline; filename=maint_request_2407_blank.pdf"})


@post("/api/form_2407")
def r_form_2407_post(h, qs, payload):
    # build a filled maintenance request from equipment + fault + work-requested data
    import forms
    if not forms.available():
        h._send(503, {"error": "reportlab not installed"}); return
    pdf = forms.build_2407(payload or {})
    h._send(200, pdf, "application/pdf", {"Content-Disposition": "inline; filename=maint_request_2407.pdf"})


@get("/api/handover")
def r_handover(h, qs):
    # shift-handover digest: what's awaiting sign-off + recent field notes, shop-wide.
    import handover
    reviews, notes = [], []
    try:
        import signoff
        reviews = signoff.queue(_signoff_db(), "pending")
    except Exception:
        pass
    try:
        import fieldnotes
        notes = fieldnotes.recent(_notes_db())
    except Exception:
        pass
    h._send(200, handover.build_digest(pending_reviews=reviews, recent_notes=notes,
                                       since_hours=qint(qs, "hours", 24, 1, 720)))


@get("/api/intervals")
def r_intervals(h, qs):
    # service intervals (usage/calendar/event) for a vehicle/system
    import intervals
    q = qstr(qs, "q", "").strip()
    if len(q) < 2:
        h._send(400, {"error": "q required"}); return
    iv, seen = [], set()
    for pg in _pages_for(q, 12):
        for x in intervals.extract_intervals(pg.get("body") or ""):
            k = (x["value"], x["unit"])
            if k in seen:
                continue
            seen.add(k); x["doc"] = pg["doc"]; x["page"] = pg["page"]; iv.append(x)
    h._send(200, {"ok": True, "query": q, "intervals": iv[:40]})


@get("/api/fluids")
def r_fluids(h, qs):
    # per-system fluids & capacities matrix for a vehicle
    import fluidsmatrix
    q = qstr(qs, "q", "").strip()
    if len(q) < 2:
        h._send(400, {"error": "q required"}); return
    merged = {}
    for pg in _pages_for(q, 12):
        for sys, v in fluidsmatrix.matrix(pg.get("body") or "").items():
            if sys not in merged and (v.get("fluid") or v.get("capacity")):
                v["doc"] = pg["doc"]; v["page"] = pg["page"]; merged[sys] = v
    h._send(200, {"ok": True, "query": q, "fluids": merged})


@get("/api/commonality")
def r_commonality(h, qs):
    # which vehicles/platforms use a given part (fleet commonality)
    import commonality
    q = qstr(qs, "q", "") or qstr(qs, "nsn", "")
    if len(q) < 3:
        h._send(400, {"error": "q required (NSN / part number)"}); return
    h._send(200, {"ok": True, **commonality.for_part(core.DB_PATH, q)})


@get("/api/rpstl")
def r_rpstl(h, qs):
    # structured RPSTL rows (figure/item/SMR/CAGEC/part#/NSN/qty/nomenclature) parsed from a doc/page or query
    import rpstl, sqlite3
    doc = qint(qs, "doc", 0); page = qint(qs, "page", 0); q = qstr(qs, "q", "")
    text = ""
    try:
        con = core.db()          # v1.13: pooled (close() is a harmless no-op) -> no leak on error paths
        if doc and page:
            r = con.execute("SELECT body_text FROM pages WHERE document_id=? AND page_number=? LIMIT 1", (doc, page)).fetchone()
            text = (r[0] if r else "") or ""
        elif q:
            for pg in _pages_for(q, 8):
                text += "\n" + (pg.get("body") or "")
        con.close()
    except Exception:
        text = ""
    h._send(200, {"ok": True, **rpstl.parse(text)})


@get("/api/crossmethod")
def r_crossmethod(h, qs):
    # cross-METHOD agreement for a subject: gather the same dimension from measures (+ tables/publog when
    # available) and report concurrence (confirmed / single / conflict).
    import crossmethod, measures
    q = qstr(qs, "q", "").strip()
    if len(q) < 2:
        h._send(400, {"error": "q required"}); return
    obs = []
    try:
        for m in measures.find_for_query(core.DB_PATH, q, limit=60).get("results", []):
            obs.append({"method": "measures", "type": m.get("type"), "value": m.get("value"),
                        "unit": m.get("unit"), "source": "doc %s p.%s" % (m.get("doc"), m.get("page"))})
    except Exception:
        pass
    try:
        import publog, publogdiff
        if publog.available():
            rec = publog.lookup(q)
            for c in (rec.get("characteristics") or []) if rec else []:
                import validate
                if validate.to_float(c.get("reply")) is not None:
                    obs.append({"method": "publog", "type": (c.get("requirement") or "").lower()[:20],
                                "value": c.get("reply"), "unit": "", "source": "PUBLOG"})
    except Exception:
        pass
    rec = crossmethod.reconcile(obs)
    h._send(200, {"ok": True, "query": q, "reconciled": rec, "summary": crossmethod.summary(rec)})


@get("/api/faulttree")
def r_faulttree(h, qs):
    # guided troubleshooting: symptom -> the manual's MALFUNCTION / STEP / CORRECTIVE-ACTION tree, cited.
    import faulttree
    q = qstr(qs, "q", "").strip()
    if len(q) < 2:
        h._send(400, {"error": "q required (a symptom or system)"}); return
    h._send(200, faulttree.find_for_query(core.DB_PATH, q, qint(qs, "limit", 25, 1, 60)))


@get("/api/conflicts")
def r_conflicts(h, qs):
    # cross-manual conflict check: measured values (torque/pressure/dimension) that DISAGREE between
    # manuals for the same part, each cited. Safety-focused; empty when the manuals agree.
    import conflicts
    q = qstr(qs, "q", "").strip()
    if len(q) < 2:
        h._send(400, {"error": "q required"}); return
    try:
        tol = float(qstr(qs, "tol", "0.05")) or 0.05
    except Exception:
        tol = 0.05
    h._send(200, conflicts.check_query(core.DB_PATH, q, limit=qint(qs, "limit", 120, 10, 400), rel_tol=tol))


@get("/api/partsummary")
def r_partsummary(h, qs):
    # fast single-call summary for the unified /part page (same gather, JSON not PDF)
    q, pkg = _jobpack_data(qs)
    if len(q) < 2:
        h._send(400, {"error": "q required"}); return
    # trim procedures to a light shape for the page
    pkg["procedures"] = [{"kind": p.get("kind"), "vehicle": p.get("vehicle") or p.get("tm_number"),
                          "page": p.get("page"), "doc_id": p.get("doc_id"),
                          "n_steps": len(p.get("steps") or []), "n_tools": len(p.get("tools") or [])}
                         for p in (pkg.get("procedures") or [])[:6]]
    h._send(200, {"ok": True, "query": q, "summary": pkg})


# ---- status / ops / health ---------------------------------------------------------------------------

def _exposed_read_guard(h):
    """Gate for GET endpoints that leak host internals (filesystem paths, run/ingest state) rather
    than manual content. do_POST already requires the shared X-Viewer-Token when the server is
    network-exposed (_EXPOSED); do_GET never did, on the (correct, and kept as-is) assumption that
    the normal exposed-mode use case is a mechanic's phone browsing/searching manuals over LAN with
    no way to set a custom header on plain navigation. But that same blanket assumption left every
    GET route that reveals real filesystem paths or internal run state -- not manual content --
    wide open to anyone on the network. Applied to: /api/audit, /api/ops, /api/status,
    /api/command_status (embeds status_summary(), the same payload /api/status protects),
    /api/ingest_status (leaks the raw host path of the current/last ingest job), /api/provenance
    (self-documented "INTERNAL AUDIT (operator, not mechanic)"), and /api/integrity (streams file
    paths/checksums). Returns True if the request may proceed; sends 401 and returns False otherwise.
    """
    if not core._EXPOSED:
        return True
    if core._auth_ok(h.headers.get("X-Viewer-Token")):
        return True
    h._send(401, core.AUTH_REQUIRED_BODY)
    return False


@get("/api/status")
def r_status(h, qs):
    if not _exposed_read_guard(h): return
    h._send(200, core.status_summary())


@get("/api/ops")
def r_ops(h, qs):
    if not _exposed_read_guard(h): return
    h._send(200, core.ops_summary())


_COMMAND_STATUS_CACHE = {"t": 0.0, "body": None}
_COMMAND_STATUS_TTL = 60.0           # v1.13.4: see note at the handler -- same TTL as _SEARCH_LRU
_COMMAND_STATUS_LOCK = _threading.Lock()

_COVERAGE_OVERVIEW_CACHE = {"t": 0.0, "body": None}
_COVERAGE_OVERVIEW_TTL = 60.0
_COVERAGE_OVERVIEW_LOCK = _threading.Lock()


def _coverage_overview_cached():
    """TTL-cached coverage.overview() -- the same 12-53s aggregate (a COUNT(*) scan reading every page's
    body_text) is called from BOTH /api/command_status and /api/coverage (no ?vehicle=, backing /coverage
    and /ops). v1.13.4: /api/coverage had no caching at all -- the same 'page silently hangs on Loading...'
    regression diagnosed and fixed for /command, still live on its other call site. Centralized here (one
    cache, one TTL) instead of each route keeping a separate copy, so the two routes share one computation
    per window instead of each paying the full cost independently."""
    now = time.time()
    with _COVERAGE_OVERVIEW_LOCK:
        if _COVERAGE_OVERVIEW_CACHE["body"] is not None and (now - _COVERAGE_OVERVIEW_CACHE["t"]) < _COVERAGE_OVERVIEW_TTL:
            return _COVERAGE_OVERVIEW_CACHE["body"]
    import coverage
    body = coverage.overview(core.DB_PATH, core.INDEX_DIR)
    with _COVERAGE_OVERVIEW_LOCK:
        _COVERAGE_OVERVIEW_CACHE["t"] = time.time(); _COVERAGE_OVERVIEW_CACHE["body"] = body
    return body


@get("/api/command_status")
def r_command_status(h, qs):
    # ONE 'are we complete?' aggregate for the command center: OCR progress, corpus coverage, PUBLOG build
    # state, and Masterfile dimensional gaps. Every piece best-effort so one missing sidecar can't 500.
    # v1.13.4: coverage.overview() alone measured 12-53s cold (a COUNT(*) scan of every page's body_text
    # across an 892k-row/3.65GB+ table -- slow until the OS file cache warms, worse on a bigger corpus or
    # a memory-constrained box) -- live on /command, that read as the page silently hanging on "Loading...".
    # TTL-cache the whole aggregate like _SEARCH_LRU already does for search: the underlying data only
    # changes as OCR/ingest progress, so a 60s-stale "glance" dashboard is fine, and it makes every load
    # after the first one instant instead of re-paying the full aggregate cost every single time.
    if not _exposed_read_guard(h): return
    now = time.time()
    with _COMMAND_STATUS_LOCK:
        if _COMMAND_STATUS_CACHE["body"] is not None and (now - _COMMAND_STATUS_CACHE["t"]) < _COMMAND_STATUS_TTL:
            h._send(200, _COMMAND_STATUS_CACHE["body"]); return
    import os
    out = {}
    try:
        out["ocr"] = core.status_summary()
    except Exception as e:
        out["ocr"] = {"error": str(e)}
    try:
        out["coverage"] = _coverage_overview_cached()
    except Exception as e:
        out["coverage"] = {"error": str(e)}
    try:
        import publog
        out["publog"] = publog.stats()
    except Exception as e:
        out["publog"] = {"available": False, "error": str(e)}
    try:
        import masterfile
        mp = os.path.join(os.path.dirname(core.DB_PATH), "masterfile.db")
        out["masterfile"] = masterfile.coverage(mp) if hasattr(masterfile, "coverage") else {}
    except Exception as e:
        out["masterfile"] = {"error": str(e)}
    with _COMMAND_STATUS_LOCK:
        _COMMAND_STATUS_CACHE["t"] = time.time(); _COMMAND_STATUS_CACHE["body"] = out
    h._send(200, out)


# ---- R13: data-integrity validation, resilience, human sign-off, TM currency, verification cockpit ----
@get("/api/validate")
def r_validate(h, qs):
    # range/plausibility-check the measured values for a query; quarantine garbled/impossible ones.
    import validate, measures
    q = qstr(qs, "q", "").strip()
    if len(q) < 2:
        h._send(400, {"error": "q required"}); return
    try:
        rows = measures.find_for_query(core.DB_PATH, q, limit=qint(qs, "limit", 80, 10, 300)).get("results", [])
    except Exception as e:
        h._send(200, {"ok": False, "error": str(e), "rows": [], "counts": {}}); return
    res = validate.validate_rows(rows)
    h._send(200, {"ok": True, "query": q, **res})


_INTEGRITY_CACHE = {"t": 0.0, "body": None}
_INTEGRITY_TTL = 300.0               # v1.13.4: see note below -- longer than _COMMAND_STATUS_TTL on purpose
_INTEGRITY_LOCK = _threading.Lock()


@get("/api/integrity")
def r_integrity(h, qs):
    # DB corruption / checksum status across the index + sidecars.
    # v1.13.4: manifest() streams a FULL SHA-256 over every byte of every listed file -- ~13GB total here
    # (viewer.db ~3.65GB + publog.db ~9GB + the smaller sidecars) -- measured 49s live, on EVERY /verify page
    # load, since this had no caching at all. TTL-cache it like _COMMAND_STATUS_CACHE; 300s (not 60s) because
    # this is heavier and the underlying files change far less often than OCR/search state. ?force=1 bypasses
    # the cache for a genuinely fresh tamper/corruption check on demand -- never silently hide that option.
    if not _exposed_read_guard(h): return
    now = time.time()
    if not qflag(qs, "force"):
        with _INTEGRITY_LOCK:
            if _INTEGRITY_CACHE["body"] is not None and (now - _INTEGRITY_CACHE["t"]) < _INTEGRITY_TTL:
                h._send(200, _INTEGRITY_CACHE["body"]); return
    import integrity, os
    d = os.path.dirname(core.DB_PATH)
    names = ["viewer.db", "publog.db", "masterfile.db", "measures.db", "tables.db", "enrich.db", "kg.db", "signoff.db"]
    paths = [os.path.join(d, n) for n in names]
    out = integrity.status(paths)
    with _INTEGRITY_LOCK:
        _INTEGRITY_CACHE["t"] = time.time(); _INTEGRITY_CACHE["body"] = out
    h._send(200, out)


@get("/api/tmrev")
def r_tmrev(h, qs):
    # TM revision / currency: is this the current manual, or is a newer change in the corpus?
    import tmrev
    tm = qstr(qs, "tm", "") or qstr(qs, "q", "")
    if len(tm) < 3:
        h._send(400, {"error": "tm required"}); return
    h._send(200, tmrev.currency(core.DB_PATH, tm))


@get("/api/verifystate")
def r_verifystate(h, qs):
    import verifystate, os
    # v1.13.4: this file is engine/features/routes.py -- reaching <root>/docs needs THREE dirname() hops
    # (features -> engine -> root), not two. Left at two since the v0.96.0 restructure moved this code out
    # of the old engine/viewer_app.py monolith (where two hops WAS correct); it's pointed at the
    # nonexistent engine/docs ever since, so /verify has never been able to find a verify log at all --
    # confirmed live: last_verify.present was False even right after a real, fully-GREEN VERIFY.bat run.
    root_docs = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docs")
    h._send(200, verifystate.snapshot(core.DB_PATH, root_docs))


def _signoff_db():
    import os
    return os.path.join(os.path.dirname(core.DB_PATH), "signoff.db")


@get("/api/signoff")
def r_signoff(h, qs):
    # review queue (default: pending) or the audit trail for one subject (?kind=&key=).
    import signoff
    kind = qstr(qs, "kind", ""); key = qstr(qs, "key", "")
    if kind and key:
        h._send(200, {"ok": True, "status": signoff.status_of(_signoff_db(), kind, key),
                      "audit": signoff.audit(_signoff_db(), kind, key)}); return
    h._send(200, {"ok": True, "queue": signoff.queue(_signoff_db(), qstr(qs, "status", "pending"))})


@post("/api/signoff")
def r_signoff_post(h, qs, payload):
    # submit a value for review, or record an SME decision (approve/reject/override). Append-only audit.
    import signoff
    kind = (payload.get("kind") or "").strip(); key = (payload.get("key") or "").strip()
    action = (payload.get("action") or "").strip()
    by = (payload.get("by") or "").strip() or "anonymous"
    if not kind or not key:
        h._send(400, {"error": "kind and key required"}); return
    try:
        if action == "submit":
            eid = signoff.submit(_signoff_db(), kind, key, payload.get("value"), source=payload.get("source"), by=by, note=payload.get("note"))
        elif action in ("approve", "reject", "override"):
            eid = signoff.decide(_signoff_db(), kind, key, action, by=by, value=payload.get("value"), note=payload.get("note"))
        else:
            h._send(400, {"error": "action must be submit/approve/reject/override"}); return
    except Exception as e:
        h._send(400, {"error": str(e)}); return
    h._send(200, {"ok": True, "event_id": eid, "status": signoff.status_of(_signoff_db(), kind, key)})


# ---- v1.9: serviceability / torque-sequence / kit-BOM / pinouts / training / field-notes ----
def _pages_for(q, limit=12):
    """Bounded FTS page bodies for a query (shared by the text extractors below)."""
    import sqlite3, re as _re
    terms = [t for t in _re.findall(r"[A-Za-z0-9]+", q or "") if len(t) > 1]
    if not terms:
        return []
    try:
        con = core.db()          # v1.13: pooled + Row factory already set; close() no-op -> leak-free
        rows = con.execute("SELECT d.id AS doc, d.tm_number AS tm, p.page_number AS page, p.body_text AS body "
                           "FROM pages_fts JOIN pages p ON p.id=pages_fts.rowid JOIN documents d ON d.id=p.document_id "
                           "WHERE pages_fts MATCH ? ORDER BY rank LIMIT ?", (" OR ".join(terms), limit)).fetchall()
        con.close(); return [dict(r) for r in rows]
    except Exception:
        return []


@get("/api/serviceability")
def r_serviceability(h, qs):
    # serviceable/wear limits for a part + optional 'is my measured value in tolerance?' (?measured=&unit=)
    import serviceability
    q = qstr(qs, "q", "").strip()
    if len(q) < 2:
        h._send(400, {"error": "q required"}); return
    lims, seen = [], set()
    for pg in _pages_for(q, 12):
        for l in serviceability.extract_limits(pg.get("body") or ""):
            k = (l["bound"], l["value"], l["unit"])
            if k in seen:
                continue
            seen.add(k); l["doc"] = pg["doc"]; l["tm"] = pg["tm"]; l["page"] = pg["page"]; lims.append(l)
    out = {"ok": True, "query": q, "limits": lims[:40]}
    measured = qstr(qs, "measured", "")
    if measured:
        out["assessment"] = serviceability.assess(measured, lims, unit=qstr(qs, "unit", "") or None)
    h._send(200, out)


@get("/api/torqueseq")
def r_torqueseq(h, qs):
    # torque sequence + numbered bolt-pattern diagram for a part/procedure
    import torqueseq
    q = qstr(qs, "q", "").strip()
    if len(q) < 2:
        h._send(400, {"error": "q required"}); return
    best = None
    for pg in _pages_for(q, 10):
        d = torqueseq.detect_sequence(pg.get("body") or "")
        if d.get("pattern") or d.get("stages"):
            best = torqueseq.build(pg.get("body") or "", qint(qs, "n", 0, 0, 40) or None)
            best["doc"] = pg["doc"]; best["page"] = pg["page"]; break
    if not best:
        best = torqueseq.build("", qint(qs, "n", 6, 2, 40))
        best["enough"] = False
    best["ok"] = True
    h._send(200, best)


@get("/api/oneuse")
def r_oneuse(h, qs):
    # v1.13 (#41/#42 -- SAFETY): one-time-use / torque-to-yield / discard-after-removal fastener
    # flags for a part or NSN. Extractive only (R13): every flag carries the manual's own sentence
    # plus its doc/tm/page citation; nothing inferred.
    import oneuse
    q = qstr(qs, "q", "").strip()
    if len(q) < 2:
        h._send(400, {"error": "q required (part name or NSN)"}); return
    h._send(200, oneuse.find_for_query(core.DB_PATH, q, limit=qint(qs, "limit", 10, 1, 40)))


@get("/api/bom")
def r_bom(h, qs):
    # complete kit / bill-of-materials for a job: parts + tools + consumables
    import bom
    q = qstr(qs, "q", "").strip()
    if len(q) < 2:
        h._send(400, {"error": "q required"}); return
    parts, tools, cons = [], [], []
    try:
        from features import procedures_feature as PF
        procs = PF.procedure_for(q, 4).get("procedures", [])
        for p in procs:
            tools += (p.get("tools") or [])
            for s in (p.get("steps") or []):
                cons += bom.find_consumables(s)
    except Exception:
        procs = []
    try:
        from features import parts_feature as PARTS
        la = PARTS.part_differences(q, 30)
        if la and la.get("variants"):
            parts = [{"nsn": v.get("nsn"), "name": la.get("nomenclature") or q} for v in la["variants"][:12]]
    except Exception:
        pass
    # v1.13 (#41/#42): merge one-time-use / TTY fastener flags into the kit as cited warnings, so
    # the kit itself says which fasteners MUST be replaced. Best-effort; kit never fails on this.
    warns = []
    try:
        import oneuse
        of = oneuse.find_for_query(core.DB_PATH, q, limit=6)
        if of.get("ok"):
            warns = (of.get("flags") or [])[:8]
    except Exception:
        warns = []
    h._send(200, {"ok": True, "query": q, "kit": bom.build_kit(parts, tools, cons, warnings=warns)})


@get("/api/pinouts")
def r_pinouts(h, qs):
    # connector pinouts + wire colors for a doc/page or a query
    import pinouts, sqlite3
    doc = qint(qs, "doc", 0); page = qint(qs, "page", 0); q = qstr(qs, "q", "")
    conns = []
    if doc and page:
        try:
            con = core.db()          # v1.13: pooled (close() is a harmless no-op) -> no leak on error paths
            r = con.execute("SELECT body_text FROM pages WHERE document_id=? AND page_number=? LIMIT 1", (doc, page)).fetchone()
            con.close()
            if r:
                conns = pinouts.extract_pinouts(r[0] or "")
        except Exception:
            conns = []
    elif q:
        for pg in _pages_for(q, 10):
            conns += pinouts.extract_pinouts(pg.get("body") or "")
    h._send(200, {"ok": True, "connectors": conns[:30]})


@get("/api/quiz")
def r_quiz(h, qs):
    # a cited multiple-choice quiz generated from the corpus (learn mode)
    import training, measures
    q = qstr(qs, "q", "").strip() or "torque"
    facts = []
    try:
        res = measures.find_for_query(core.DB_PATH, q, limit=60)
        for m in res.get("results", []):
            if m.get("value"):
                facts.append({"subject": (m.get("context") or q)[:60], "type": m.get("type"),
                              "value": m.get("value"), "unit": m.get("unit"), "doc": m.get("doc"), "page": m.get("page")})
    except Exception:
        pass
    h._send(200, {"ok": True, "query": q, "quiz": training.build_quiz(facts, n=qint(qs, "n", 10, 1, 25),
                                                                      seed=qint(qs, "seed", 0, 0, 999999) or None)})


def _notes_db():
    import os
    return os.path.join(os.path.dirname(core.DB_PATH), "notes.db")


@get("/api/notes")
def r_notes(h, qs):
    import fieldnotes
    subj = qstr(qs, "q", "") or qstr(qs, "subject", "")
    if subj:
        h._send(200, {"ok": True, "subject": subj, "notes": fieldnotes.for_subject(_notes_db(), subj)}); return
    h._send(200, {"ok": True, "recent": fieldnotes.recent(_notes_db())})


@post("/api/notes")
def r_notes_post(h, qs, payload):
    import fieldnotes
    action = (payload.get("action") or "add").strip()
    by = (payload.get("by") or "anonymous").strip() or "anonymous"
    try:
        if action == "add":
            subj = (payload.get("subject") or "").strip()
            nid = fieldnotes.add(_notes_db(), subj, payload.get("text") or "", by=by,
                                 cite_doc=payload.get("cite_doc"), cite_page=payload.get("cite_page"))
            h._send(200, {"ok": True, "id": nid})
        elif action in ("endorse", "retract"):
            fieldnotes.endorse(_notes_db(), int(payload.get("id")), by=by, retract=(action == "retract"))
            h._send(200, {"ok": True})
        else:
            h._send(400, {"error": "action must be add/endorse/retract"})
    except Exception as e:
        h._send(400, {"error": str(e)})


@get("/api/audit")
def r_audit(h, qs):
    if not _exposed_read_guard(h): return
    h._send(200, core.file_audit(qint(qs, "limit", 600, 1, 2000)))


@get("/healthz")
def r_healthz(h, qs):
    import preflight as _pf
    res = _pf.checks(core.DB_PATH)
    ok = not any(s == "FAIL" for _, s, _ in res)
    h._send(200 if ok else 503, {"ok": ok, "version": core.VERSION,
            "checks": [{"name": n, "status": s, "detail": d} for n, s, d in res]})


@get("/api/rps")
def r_rps(h, qs):
    ov = (qs.get("mode") or [None])[0]           # optional NON-persistent preview of a concrete mode
    if core._rps:
        prof = {}
        try:
            import sysprobe; prof = sysprobe.load_or_build()
        except Exception: prof = {}
        if ov:                                    # explicit preview (?mode=) -> concrete mode, no persistence
            m, why = core._rps.mode_for(prof, ov)
        elif core.RPS_OVERRIDE in core._rps.VALID_MODES:
            m, why = core._rps.mode_for(prof, core.RPS_OVERRIDE)
        else:                                     # reflect the persisted Settings choice (auto/perf/retro)
            m, why = core._rps.mode_for_setting(prof, core.RPS_SETTING)
        out = core._rps.profile_summary(prof, m, why)
        out["page_cache_stats"] = core._rps.cache_stats(core.INDEX_DIR)
        out["setting"] = core.RPS_SETTING                                    # the saved Settings-panel choice
        out["setting_labels"] = core._rps.RUN_MODE_LABELS                    # {auto|performance|retro: label}
        out["env_forced"] = bool(core.RPS_OVERRIDE in core._rps.VALID_MODES) # env/CLI VIEWER_MODE overriding UI
        out["recommended_mode"] = prof.get("recommended_run_mode")          # sysprobe's hardware pick
        h._send(200, out)
    else:
        h._send(200, {"mode": "modern", "reason": "rps module unavailable", "flags": {},
                      "setting": "auto", "setting_labels": {}, "env_forced": False})


@post("/api/rps_mode")
def p_rps_mode(h, qs, payload):
    """Persist the Settings-panel run-mode choice and re-apply it live. Body: {"setting": auto|performance|retro}
    (also accepts "mode" as an alias). Fail-loud: reports saved=False if the choice could not be written."""
    if not core._rps or not hasattr(core, "set_run_mode"):
        h._send(503, {"ok": False, "error": "run-mode switching unavailable in this build"}); return
    setting = (payload.get("setting") or payload.get("mode") or "").strip()
    if not setting:
        h._send(400, {"ok": False, "error": "missing 'setting' (auto|performance|retro)"}); return
    r = core.set_run_mode(setting)
    r["ok"] = True
    h._send(200, r)


# ---- ingest --------------------------------------------------------------------------------------------

@get("/api/ingest_preview")
def r_ingest_preview(h, qs):
    h._send(200, core.ingest_preview(qstr(qs, "path")))


@get("/api/ingest_status")
def r_ingest_status(h, qs):
    if not _exposed_read_guard(h): return
    h._send(200, core.ingest_status())


# ---- page render / words / callouts ----------------------------------------------------------------------

@get("/api/pagewords")
def r_pagewords(h, qs):
    h._send(200, core.page_words(qint(qs, "doc", 0), qstr(qs, "page", "1")))


@get("/api/callouts")
def r_callouts(h, qs):
    h._send(200, core.page_callouts(qint(qs, "doc", 0), qstr(qs, "page", "1")))


@get("/page")
def r_page(h, qs):
    # NOTE: kept the monolith's contract -- ANY failure here answers 404 (the viewer treats a
    # missing/broken page image as "no image"), via PageRenderError in the boundary.
    try:
        clip = None
        cv = (qs.get("clip") or [None])[0]
        if cv:
            parts = [p for p in cv.split(",") if p != ""]
            if len(parts) == 4: clip = parts
        # Cap dpi: full page modest (fast); HD raises the full-page ceiling; clip crops high.
        req_dpi = int(qstr(qs, "dpi", "130") or 130)
        req_dpi = min(req_dpi, 700 if clip else 400)
        doc_i = qint(qs, "doc", 0); pg_s = qstr(qs, "page", "1")
        hl = (qs.get("hl") or [None])[0]; cln = qflag(qs, "clean")
        ctr = int(qstr(qs, "contrast", "0") or 0); binz = qflag(qs, "binarize")
        # cheap param-based ETag, checked BEFORE rendering -> repeat views 304 without touching the renderer
        import hashlib as _hl
        petag = '"' + _hl.md5(("%s|%s|%s|%d|%d|%d|%s|%s" % (doc_i, pg_s, req_dpi, int(cln), ctr, int(binz), hl or "", cv or "")).encode()).hexdigest() + '"'
        if (h.headers.get("If-None-Match") or "") == petag:
            h.send_response(304); h.send_header("ETag", petag)
            h.send_header("Cache-Control", "max-age=3600"); h.send_header("Content-Length", "0"); h.end_headers(); return
        if clip is None and not hl:                # cacheable full-page render (RPS page cache)
            try: pg_i = int(pg_s)
            except Exception: pg_i = 1
            data = core.cached_page_render(doc_i, pg_i, req_dpi, clean=cln, contrast=ctr, binarize=binz)
            core._warm_adjacent(doc_i, pg_i, req_dpi, clean=cln, contrast=ctr, binarize=binz)
        else:
            data = core.render_page_png(doc_i, pg_s, req_dpi, hl, clean=cln, contrast=ctr, binarize=binz, clip=clip)
        h._send(200, data, "image/png", {"Cache-Control": "max-age=3600", "ETag": petag})
    except Exception as e:
        h._send(404, {"error": str(e) if isinstance(e, FileNotFoundError) else "page image not available"})


# ======================================== POST routes =====================================================

@post("/api/niin_review_decision")
def p_niin_decision(h, qs, payload):
    r = core.record_niin_decision(payload.get("niin", ""), payload.get("decision", ""),
            payload.get("canonical_nsn", ""), payload.get("note", ""), payload.get("by", ""))
    h._send(200 if r.get("ok") else 400, r)


@post("/api/ingest")
def p_ingest(h, qs, payload):
    h._send(200, core.ingest_start(payload.get("path") or ""))


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


@post("/api/keywords")
def p_keywords(h, qs, payload):
    act = (payload.get("action") or "save").strip()
    if act == "delete": r = core.user_keywords_delete(payload.get("index"))
    else: r = core.user_keywords_save(payload.get("terms") or [])
    h._send(200 if r.get("ok") else 400, r)


@post("/api/tags")
def p_tags(h, qs, payload):
    act = (payload.get("action") or "save").strip()
    if act == "delete": r = core.user_tags_remove(payload.get("nsn", ""), payload.get("name", ""), payload.get("tag", ""))
    else: r = core.user_tags_add(payload.get("nsn", ""), payload.get("name", ""), payload.get("tag", ""))
    h._send(200 if r.get("ok") else 400, r)


@post("/api/side_override")
def p_side_override(h, qs, payload):
    r = core._side_save(payload.get("doc_id"), (payload.get("side") or "").strip(), payload.get("by", ""))
    h._send(200 if r.get("ok") else 400, r)


@post("/api/image3d")
def p_image3d(h, qs, payload):
    nsn = (payload.get("nsn") or "").strip()
    info = core._part_image(nsn)
    path = core._fig_get_crop(info.get("doc_id"), info.get("page")) if info.get("found") else None
    r = core._i3d.generate(nsn, path)
    h._send(200 if r.get("ok") else 400, r)


@post("/api/rpstl_override")
def p_rpstl_override(h, qs, payload):
    r = core._rpstl_save(payload.get("pn", ""), payload.get("fields", {}) or payload, payload.get("by", ""))
    h._send(200 if r.get("ok") else 400, r)


@post("/api/chapter_override")
def p_chapter_override(h, qs, payload):
    r = core._chapter_save(payload.get("doc_id"), (payload.get("side") or "").strip(), payload.get("page"))
    h._send(200 if r.get("ok") else 400, r)


@post("/api/request")
def p_request(h, qs, payload):
    if not ((payload.get("session", {}).get("tech_status") or "").strip()):
        h._send(400, {"error": "Tech status is required before generating the sheet."}); return
    core.save_request(payload)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf: out = tf.name
    try:                                       # v1.13: never orphan the temp PDF if build/read raises
        core.build_request_pdf(out, payload.get("session", {}), payload.get("items", []))
        data = open(out, "rb").read()
    finally:
        try: os.unlink(out)
        except Exception: pass
    bumper = (payload.get("session", {}).get("bumper") or "request").replace(" ", "_")
    h._send(200, data, "application/pdf", {"Content-Disposition": 'attachment; filename="104th_parts_request_%s.pdf"' % bumper})
