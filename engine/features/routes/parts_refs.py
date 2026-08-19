#!/usr/bin/env python3
"""THE VIEWER -- parts/references + keywords/tags + the parts-request PDF route (v1.14 routes/
split). Moved verbatim out of the former monolithic engine/features/routes.py. DI via `core`."""
import os
import tempfile

from features.registry import get, post, qstr, qint, qflag, safe_header_token

core = None          # injected by viewer_app at startup


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


# ---- POST: niin decisions / keywords / tags / parts-request PDF -------------------------------------

@post("/api/niin_review_decision")
def p_niin_decision(h, qs, payload):
    r = core.record_niin_decision(payload.get("niin", ""), payload.get("decision", ""),
            payload.get("canonical_nsn", ""), payload.get("note", ""), payload.get("by", ""))
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
    bumper = safe_header_token(payload.get("session", {}).get("bumper")) or "request"
    h._send(200, data, "application/pdf", {"Content-Disposition": 'attachment; filename="104th_parts_request_%s.pdf"' % bumper})
