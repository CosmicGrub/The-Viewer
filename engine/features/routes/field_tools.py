#!/usr/bin/env python3
"""THE VIEWER -- shift-handover / intervals / fluids / commonality / RPSTL / serviceability /
torque-sequence / one-time-use / kit-BOM / pinouts / quiz / field-notes routes (v1.9-era section;
v1.14 routes/ split). Moved verbatim out of the former monolithic engine/features/routes.py. DI
via `core`."""
import os

from features.registry import get, post, qstr, qint, qflag, safe_header_token
from features.routes._shared import _pages_for, _signoff_db

core = None          # injected by viewer_app at startup


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
