#!/usr/bin/env python3
"""THE VIEWER -- offline Q&A / designation decoders / cross-manual diagnostics routes (v1.14
routes/ split). Moved verbatim out of the former monolithic engine/features/routes.py. DI via
`core`."""
from features.registry import get, post, qstr, qint, qfloat, qflag, safe_header_token
from features.routes._shared import _pages_for

core = None          # injected by viewer_app at startup


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
                reply = c.get("reply")
                if validate.to_float(reply) is not None:
                    # v1.15: normalize through measures.py's own unit classifier instead of hardcoding
                    # unit="" with the raw PUBLOG requirement string as `type`. crossmethod.reconcile()
                    # groups strictly on the (type, unit) pair, and measures.py's canonical units (e.g.
                    # "ft-lb", "psi") are never "" -- so the PUBLOG observation could never land in the
                    # same group as a measures-sourced one, and PUBLOG could never actually corroborate
                    # (status="confirmed") anything. PUBLOG replies carry their unit inline (e.g. "35 FT
                    # LB", "3.00 IN" -- same free-text shape dimscad.py already parses), so run them
                    # through the same extractor measures.py uses on manual text. A reply with no
                    # recognizable unit (e.g. a bare "35") can't be normalized to a comparable dimension,
                    # so it's skipped rather than added as an observation that can never match anything.
                    mm = measures.extract(str(reply), cap=1)
                    if mm:
                        obs.append({"method": "publog", "type": mm[0]["type"], "value": reply,
                                    "unit": mm[0]["unit"], "source": "PUBLOG"})
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
    # v1.15: clamped like every other numeric param in this file (was bare float() with an `or 0.05`
    # fallback -- a negative tol inverted detect()'s `spread <= rel_tol` gate into a permanent conflict,
    # and an explicit tol=0 was silently discarded back to the default). 0..1: a relative spread can't
    # go negative, and >=1 (>=100%) already disables conflict detection in every practical case.
    tol = qfloat(qs, "tol", 0.05, 0.0, 1.0)
    h._send(200, conflicts.check_query(core.DB_PATH, q, limit=qint(qs, "limit", 120, 10, 400), rel_tol=tol))


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
