#!/usr/bin/env python3
"""THE VIEWER -- page word/callout metadata + page-image render routes (v1.14 routes/ split).
Moved verbatim out of the former monolithic engine/features/routes.py. DI via `core`."""
from features.registry import get, post, qstr, qint, qflag, safe_header_token

core = None          # injected by viewer_app at startup


@get("/api/pagewords")
def r_pagewords(h, qs):
    h._send(200, core.page_words(qint(qs, "doc", 0), qint(qs, "page", 1, 1)))


@get("/api/callouts")
def r_callouts(h, qs):
    h._send(200, core.page_callouts(qint(qs, "doc", 0), qint(qs, "page", 1, 1)))


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
        # Cap dpi: full page modest (fast); HD raises the full-page ceiling; a genuinely small
        # clip (magnifier/loupe crop) may go higher. `clip` is only ever clamped into [0,1] with
        # a floor on minimum size (render_feature._clip_rect_for) -- never a ceiling -- so a
        # request can pass clip=0,0,1,1 (the whole page) and must NOT get the raised ceiling; it
        # is capped the same as a plain full-page request.
        req_dpi = int(qstr(qs, "dpi", "130") or 130)
        small_clip = False
        if clip:
            try:
                xs = [max(0.0, min(1.0, float(v))) for v in clip]
                small_clip = len(xs) == 4 and (xs[2] - xs[0]) <= 0.35 and (xs[3] - xs[1]) <= 0.35
            except Exception:
                small_clip = False
        # RPS tier-keyed ceiling (rps.feature_flags()['render_dpi_cap']: modern=400, lite=220,
        # legacy=150) -- NOT a flat 400 for every tier. A genuinely small clip (magnifier/loupe)
        # may go higher than the full-page cap, scaled proportionally to the tier so legacy stays
        # legacy-sized instead of jumping to the modern tier's headroom.
        dpi_cap = (core.RPS_FLAGS or {}).get("render_dpi_cap", 400)
        req_dpi = min(req_dpi, int(dpi_cap * 1.75) if small_clip else dpi_cap)
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
