#!/usr/bin/env python3
"""THE VIEWER -- side/chapter browsing + documents/vehicles/sessions routes (v1.14 routes/ split).
Moved verbatim out of the former monolithic engine/features/routes.py. DI via `core`."""
from features.registry import get, post, qstr, qint, qflag, safe_header_token

core = None          # injected by viewer_app at startup


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


# ---- POST overrides (side / chapter) ---------------------------------------------------------------

@post("/api/side_override")
def p_side_override(h, qs, payload):
    r = core._side_save(payload.get("doc_id"), (payload.get("side") or "").strip(), payload.get("by", ""))
    h._send(200 if r.get("ok") else 400, r)


@post("/api/chapter_override")
def p_chapter_override(h, qs, payload):
    r = core._chapter_save(payload.get("doc_id"), (payload.get("side") or "").strip(), payload.get("page"))
    h._send(200 if r.get("ok") else 400, r)
