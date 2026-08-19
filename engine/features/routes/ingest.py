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


@post("/api/ingest")
def p_ingest(h, qs, payload):
    h._send(200, core.ingest_start(payload.get("path") or ""))


@get("/api/ingest_preview")
def r_ingest_preview(h, qs):
    h._send(200, core.ingest_preview(qstr(qs, "path")))


@get("/api/ingest_status")
def r_ingest_status(h, qs):
    if not _exposed_read_guard(h): return
    h._send(200, core.ingest_status())
