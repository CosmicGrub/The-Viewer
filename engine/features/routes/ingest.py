#!/usr/bin/env python3
"""THE VIEWER -- ingest / air-gap manifest / PMCS-form routes (v1.14 routes/ split). Moved
verbatim out of the former monolithic engine/features/routes.py. DI via `core`."""
import os

from features.registry import get, post, qstr, qint, qflag, safe_header_token
from features.routes._shared import _exposed_read_guard

core = None          # injected by viewer_app at startup


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


@post("/api/airgap_export_decisions")
def r_airgap_export_decisions(h, qs, payload):
    # sign the full local NIIN-review-decision history for transfer to another unit
    # (recommendations annex #17: airgap-multiunit). No folder/VIEWER_INGEST_ROOTS fence needed --
    # unlike airgap_manifest/airgap_verify, this never touches an arbitrary caller-supplied path.
    import airgap
    import features.parts_feature as parts_feature
    secret = payload.get("secret") or ""
    if not secret:
        h._send(400, {"error": "secret required"}); return
    decisions = parts_feature.all_decisions()
    h._send(200, {"ok": True, "manifest": airgap.export_decisions(
        decisions, secret, label=payload.get("label", "unit-decisions"))})


@post("/api/airgap_import_decisions")
def r_airgap_import_decisions(h, qs, payload):
    # verify + merge a signed decisions export from another unit. Fail-closed on a bad signature
    # (nothing is written); a NIIN whose local latest decision disagrees with the incoming one is
    # surfaced as a conflict and NOT written -- see parts_feature.apply_imported_decisions()'s
    # docstring for why this never auto-resolves a disagreement.
    import airgap
    import features.parts_feature as parts_feature
    manifest = payload.get("manifest"); secret = payload.get("secret") or ""
    if not (isinstance(manifest, dict) and secret):
        h._send(400, {"error": "manifest (object) and secret required"}); return
    verified = airgap.import_decisions(manifest, secret)
    if not verified["ok"]:
        h._send(200, {"ok": False, "error": verified.get("error", "verification failed"),
                      "imported": 0, "conflicts": []}); return
    result = parts_feature.apply_imported_decisions(verified["decisions"])
    h._send(200, {"ok": True, **result})


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
        con = core.db()          # v1.13: pooled (close() is a harmless no-op) -> no leak on error paths
        # documents has no `filename` column -- only `path`/`rel_path`. `filename` is a value
        # derived at read time elsewhere (e.g. browse_feature.py: os.path.basename(path)), never a
        # stored column. Querying it raised sqlite3.OperationalError on every call, which the bare
        # `except Exception` below silently swallowed, so known_names was always [] and the
        # by-name half of plan()'s "hash OR name" duplicate detection never actually ran.
        known_names = [os.path.basename(r[0]) for r in con.execute("SELECT DISTINCT path FROM documents").fetchall() if r[0]]
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


@post("/api/ingest")
def p_ingest(h, qs, payload):
    h._send(200, core.ingest_start(payload.get("path") or ""))


@post("/api/ingest_upload")
def p_ingest_upload(h, qs, payload):
    # A single file's bytes, base64-encoded in the JSON body (same convention r_visualmatch() in
    # features/routes/search.py already uses for an uploaded image) -- viewer_app.py's do_POST
    # grants this ONE route a larger raw-body cap (MAX_UPLOAD_POST_BYTES) than every other POST
    # route gets, since a real PDF is far bigger than the small JSON payloads MAX_POST_BYTES was
    # sized for.
    h._send(200, core.ingest_upload(payload.get("filename") or "", payload.get("data") or ""))


@post("/api/ocr_backlog_start")
def p_ocr_backlog_start(h, qs, payload):
    # Same in-app job model as /api/ingest, no folder path needed -- just finishes OCR on whatever
    # pages are already queued (an earlier crawl-only run, or anything pre-dating this feature).
    # Unlike /api/ingest, this route has no required parameter to validate before it does anything
    # -- /api/ingest naturally no-ops on a bare/empty POST (an empty `path` fails canon_ingest_path()
    # before any subprocess or snapshot happens), but a bare POST here has nothing to fail on, so it
    # would otherwise launch a real subprocess + take a real safeguard snapshot on ANY POST,
    # confirmed or not (caught live: test_routes.py's generic "hit every POST route with an empty
    # body, just check it doesn't 500" sweep was silently kicking off a real ocrall run every time
    # this test suite ran). Requiring an explicit confirm:true is the same shape of safety valve
    # /api/ingest gets for free from its path requirement.
    if not payload.get("confirm"):
        h._send(400, {"ok": False, "error": "confirm:true required"}); return
    h._send(200, core.ocr_backlog_start())


@get("/api/ingest_preview")
def r_ingest_preview(h, qs):
    # Leaks the same class of info (real host paths + filenames) as /api/ingest_status and the
    # rest of the _exposed_read_guard()-gated routes -- must be gated identically in exposed mode.
    if not _exposed_read_guard(h): return
    h._send(200, core.ingest_preview(qstr(qs, "path")))


@get("/api/ingest_status")
def r_ingest_status(h, qs):
    if not _exposed_read_guard(h): return
    h._send(200, core.ingest_status())
