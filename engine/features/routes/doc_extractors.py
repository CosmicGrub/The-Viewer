#!/usr/bin/env python3
"""THE VIEWER -- per-document/page field-extraction routes ("catalog §" endpoints: callouts, VLM,
layout, dimscan, KG, IETM, acronyms, tables, cautions, specs, pdfmeta, provenance, Masterfile,
specsheet, QR, PUBLOG, dimscad, external gap-fill, hybrid tables, parts-request PDF, procedure).
v1.14 routes/ split -- moved verbatim out of the former monolithic engine/features/routes.py.
DI via `core`."""
import os

from features.registry import get, post, qstr, qint, qflag, safe_header_token
from features.routes._shared import _exposed_read_guard

core = None          # injected by viewer_app at startup


def _page_gray(path, page, dpi=150):
    import pymupdf as fitz, numpy as np, os
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
        import pymupdf as fitz, numpy as np, os
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
    # Review finding: safe_public_base() (viewer_app.py) emits an UNBRACKETED "::1:PORT" when
    # HOST=="::1" (`"%s:%d" % (HOST, PORT)`, not the bracketed "[::1]:PORT" form) -- the app explicitly
    # anticipates --host ::1 as a loopback binding (see viewer_app.py's own _EXPOSED check), so missing
    # this form meant the exact silent-failure case this fix exists to prevent could itself go
    # undetected on that one deployment choice. Cover both forms.
    local_only = base.lower().startswith(("http://127.0.0.1:", "http://localhost:", "http://[::1]:", "http://::1:"))
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
    fn = "parts_request_" + (safe_header_token(q) or "sheet") + ".pdf"
    h._send(200, pdf, "application/pdf", {"Content-Disposition": "inline; filename=\"%s\"" % fn})


@get("/api/procedure")
def r_procedure(h, qs):
    h._send(200, core.procedure_for(qstr(qs, "q"), qint(qs, "limit", 6, 1, 40)))


@get("/api/procedure_full")
def r_procedure_full(h, qs):
    import procedure_feature as _pf; _pf.core = core   # inject the running core module (no cycle; works as script OR import)
    h._send(200, _pf.procedure_full(qstr(qs, "q")))
