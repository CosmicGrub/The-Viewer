#!/usr/bin/env python3
"""THE VIEWER -- part imagery / 3-D / CAD routes (v1.14 routes/ split). Moved verbatim out of the
former monolithic engine/features/routes.py. DI via `core`."""
import os
import re

from features.registry import get, post, qstr, qint, qflag, safe_header_token

core = None          # injected by viewer_app at startup


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
    """Returns (style, tier). tier is the resolved RPS tier ('modern'/'lite'/'legacy') when style came from tier
    resolution, or None when the caller passed an explicit ?style= override (no tier in play). Since TIER_STYLE
    now maps 'lite' onto the same 'v3' style as 'modern' (v2/v3 render byte-identical pixels — see cad_render.py),
    `style` alone no longer distinguishes those two tiers; callers that need the tier itself (e.g. r_cadspin's
    tier-aware default frame count, which legitimately still differs even though the style doesn't) must use the
    returned tier, not try to re-derive it from style."""
    style = qstr(qs, "style").strip().lower()
    tier = None
    if style not in ("v1", "v2", "v3"):
        tier = qstr(qs, "tier").strip().lower() or core.RPS_MODE
        style = cad_render.TIER_STYLE.get(tier, "v3")
    return style, tier


@get("/cadimg")
def r_cadimg(h, qs):
    nsn = qstr(qs, "nsn").strip()
    if not nsn: h._send(404, {"error": "nsn required"}); return
    import cad_render
    row = _cad_row(nsn); name, chars = _cad_name_chars(qs, row)
    style, _tier = _cad_style(qs, cad_render)
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
    style, tier = _cad_style(qs, cad_render)
    try: n = int(qstr(qs, "n"))
    except Exception:
        # tier known (the normal RPS-resolved path) -> tier-keyed default, so 'lite' still defaults to fewer
        # frames than 'modern' even though they now share the same 'v3' style/cache. Explicit ?style= override
        # with no tier -> fall back to the old style-keyed default (SPIN_FRAMES), unchanged from before.
        n = cad_render.TIER_FRAMES.get(tier) if tier else None
        if n is None: n = cad_render.SPIN_FRAMES.get(style, 24)
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


# ---- POST overrides (3-D generation / RPSTL) --------------------------------------------------------

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
