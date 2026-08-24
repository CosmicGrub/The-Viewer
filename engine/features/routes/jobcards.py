#!/usr/bin/env python3
"""THE VIEWER -- printable Work Order / job-package routes (v1.14 routes/ split). Moved verbatim
out of the former monolithic engine/features/routes.py. DI via `core`."""
import os
import time

from features.registry import get, post, qstr, qint, qflag, safe_header_token

core = None          # injected by viewer_app at startup


def _jobcard_gather(qs):
    """Shared: pull procedures + torque + look-alike for a task from the LIVE features (core.db injected)."""
    from features import procedures_feature as PF
    from features import parts_feature as PARTS
    q = qstr(qs, "q").strip()
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
        fn = "workorder_" + (safe_header_token(q) or "task") + ".pdf"
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
        import masterfile, jobcard
        mp = os.path.join(os.path.dirname(core.DB_PATH), "masterfile.db")
        # v1.15 FIX: for_subject()/find_for_query() only match when q is (nearly) the whole subject label,
        # so a free-text task like "remove the alternator" matched nothing even though the Masterfile has
        # data for "alternator". Extract the noun-phrase focus the same way jobcard.py already does for the
        # Work Order builder, so a full-sentence q degrades to the part name instead of losing this section.
        focus = jobcard._task_intent(q).get("focus") or q
        m = masterfile.for_subject(mp, focus)
        dims = [dict(d) for d in (m.get("filtered") or [])[:14]]
        try:
            import measures, re as _re
            cited = measures.find_for_query(core.DB_PATH, focus, 120).get("results") or []
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
    fn = "jobpackage_" + (safe_header_token(q) or "part") + ".pdf"
    h._send(200, pdf, "application/pdf", {"Content-Disposition": "inline; filename=\"%s\"" % fn})


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
