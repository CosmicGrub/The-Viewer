#!/usr/bin/env python3
"""Route-level regression coverage for features/routes/ingest.py (viewer-audits-upgrades audit:
7 verified findings). Starts the real server against the deterministic fixture DB and hits the
actual HTTP routes -- same pattern as test_hardening.py / test_routes.py -- so a regression in the
route wiring itself (not just the underlying feature module, which some of these already have unit
coverage for) fails red.

Covers:
  - POST /api/ingest_scan: duplicate-by-filename detection actually works now (documents.path ->
    os.path.basename(), not the nonexistent documents.filename column) + the VIEWER_INGEST_ROOTS
    fence on this route.
  - GET  /api/ingest_preview: gated by _exposed_read_guard() like its /api/ingest_status sibling
    (previously the one route in this family that leaked real host paths/filenames unauthenticated
    in exposed mode).
  - POST /api/ingest: the route that actually kicks off a background crawl subprocess, exercised
    through the real HTTP path for the first time -- the VIEWER_INGEST_ROOTS fence and the
    already-running guard, both via the route (subprocess.Popen + safeguard mocked, same technique
    test_features.py's ingest_start race test already established).
  - POST /api/airgap_manifest: builds a real signed manifest for a real folder + enforces the fence
    (this route used to bypass the fence entirely).
  - POST /api/airgap_verify: accept / tamper-reject / wrong-secret-reject + enforces the fence (this
    route was the one specifically missing it after r_airgap_manifest was fixed).
  - POST /api/form_2404 + /api/form_2407: a filled payload's data actually lands in the rendered
    PDF text (the existing GET/empty-body sweep only proves the blank form doesn't 5xx).

Pure stdlib except PyMuPDF (fitz/pymupdf), imported lazily and skipped if unavailable for the PDF
text-extraction checks -- same convention as test_medium_fixes.py / test_extraction.py.
RUN ON WINDOWS / a coherent env (imports viewer_app)."""
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)
import fixture                                            # noqa: E402

PORT = 8894
BASE = "http://127.0.0.1:%d" % PORT


def _req(path, data=None, hdrs=None):
    body = json.dumps(data).encode() if data is not None else None
    h = dict(hdrs or {})
    if body is not None:
        h.setdefault("Content-Type", "application/json")
    r = urllib.request.Request(BASE + path, data=body, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=15) as x:
            return x.status, x.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return -1, str(e).encode()


def _json(b):
    try:
        return json.loads(b)
    except Exception:
        return {}


def main():
    tmp = tempfile.mkdtemp(prefix="ingest_routes_")
    db, _corr = fixture.build(tmp)
    import viewer_app as V
    V.DB_PATH = db; V.INDEX_DIR = os.path.dirname(db)
    from http.server import ThreadingHTTPServer
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), V.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); time.sleep(0.4)

    tests = []

    def check(name, cond):
        tests.append((name, bool(cond)))

    # Deterministic baseline: no ingest-root fence configured unless a section below sets one.
    _orig_roots = os.environ.pop("VIEWER_INGEST_ROOTS", None)

    try:
        # =====================================================================================
        # POST /api/ingest_scan -- duplicate-by-filename detection (the `filename` column fix)
        # =====================================================================================
        scan_dir = tempfile.mkdtemp(prefix="ingest_scan_")
        dup_name = "TM-9-9999-OLD-10.pdf"
        open(os.path.join(scan_dir, dup_name), "wb").write(b"%PDF-1.4 re-downloaded copy" + b"\x00" * 200)
        open(os.path.join(scan_dir, "TM-9-0000-NEW-10.pdf"), "wb").write(b"%PDF-1.4 brand new manual" + b"\x00" * 200)
        con = sqlite3.connect(db)
        # Simulate a manual already indexed under a DIFFERENT path (a prior ingest run, a different
        # drive/mount) but the SAME filename -- the exact "re-download / re-mounted USB / re-copy"
        # scenario the finding describes.
        con.execute("INSERT INTO documents(id, path) VALUES (999, ?)",
                    (os.path.join("Z:\\some\\prior\\ingest\\path", dup_name),))
        con.commit(); con.close()

        c, b = _req("/api/ingest_scan", {"folder": scan_dir})
        r = _json(b)
        check("ingest_scan -> 200", c == 200)
        check("ingest_scan finds both files", r.get("found") == 2)
        check("ingest_scan detects the already-indexed filename as a duplicate (bug fix)",
              r.get("counts", {}).get("duplicate") == 1)
        check("ingest_scan counts only the truly-new file as new",
              r.get("counts", {}).get("new") == 1)
        dup_reported = {d.get("name") for d in r.get("duplicate", [])}
        check("ingest_scan flags the correct file as the duplicate", dup_name in dup_reported)
        new_reported = {d.get("name") for d in r.get("new", [])}
        check("ingest_scan does NOT flag the new file as duplicate", "TM-9-0000-NEW-10.pdf" in new_reported)

        # VIEWER_INGEST_ROOTS fence must still be enforced on this route (finding: zero coverage).
        fence_root = tempfile.mkdtemp(prefix="ingest_scan_fenceroot_")
        outside_dir = tempfile.mkdtemp(prefix="ingest_scan_outside_")
        os.environ["VIEWER_INGEST_ROOTS"] = fence_root
        try:
            c, b = _req("/api/ingest_scan", {"folder": outside_dir})
            check("ingest_scan fence rejects a folder outside VIEWER_INGEST_ROOTS -> 400", c == 400)
            inside_dir = os.path.join(fence_root, "inside")
            os.makedirs(inside_dir, exist_ok=True)
            open(os.path.join(inside_dir, "ok.pdf"), "wb").write(b"%PDF-1.4 x")
            c, b = _req("/api/ingest_scan", {"folder": inside_dir})
            check("ingest_scan fence allows a folder inside VIEWER_INGEST_ROOTS -> 200", c == 200)
        finally:
            os.environ.pop("VIEWER_INGEST_ROOTS", None)

        # =====================================================================================
        # GET /api/ingest_preview -- must be gated by _exposed_read_guard() (security fix)
        # =====================================================================================
        preview_dir = tempfile.mkdtemp(prefix="ingest_preview_exposed_")
        open(os.path.join(preview_dir, "SECRET_MANUAL_ROUTE_TEST.pdf"), "wb").write(b"%PDF-1.4 x")
        old_exposed, old_token = V._EXPOSED, V._AUTH_TOKEN
        try:
            V._EXPOSED = True
            V._AUTH_TOKEN = "route-test-token-2026"
            c, b = _req("/api/ingest_preview?path=" + urllib.parse.quote(preview_dir))
            check("ingest_preview exposed + no token -> 401 (fix)", c == 401)
            check("ingest_preview exposed + no token: real folder path not leaked",
                  preview_dir.encode() not in b)
            check("ingest_preview exposed + no token: real filename not leaked",
                  b"SECRET_MANUAL_ROUTE_TEST" not in b)

            c, b = _req("/api/ingest_preview?path=" + urllib.parse.quote(preview_dir),
                        hdrs={"X-Viewer-Token": "route-test-token-2026"})
            check("ingest_preview exposed + valid token -> 200", c == 200)
            check("ingest_preview exposed + valid token still functions (not over-blocked)",
                  b"SECRET_MANUAL_ROUTE_TEST" in b)

            # sanity: its already-guarded sibling behaves identically (same gate, not a re-implementation)
            c, b = _req("/api/ingest_status")
            check("ingest_status exposed + no token -> 401 (sanity/parity)", c == 401)
        finally:
            V._EXPOSED, V._AUTH_TOKEN = old_exposed, old_token

        # =====================================================================================
        # POST /api/ingest -- the route was never invoked anywhere; exercise the real HTTP path
        # =====================================================================================
        from features import ingest_feature as _ingest_mod
        import subprocess as _subprocess_mod
        _real_popen = _subprocess_mod.Popen
        _real_sg_mod = sys.modules.get("safeguard")
        _popen_calls = []

        class _FakeProc:
            def __init__(self, running):
                self._running = running
            def poll(self):
                return None if self._running else 0

        class _FakeSafeguard:
            def snapshot(self, *a, **kw):
                return ("SNAP_test", {})

        def _fake_popen(cmd, **kw):
            _popen_calls.append(cmd)
            return _FakeProc(running=False)

        ingest_dir = tempfile.mkdtemp(prefix="ingest_post_")
        open(os.path.join(ingest_dir, "some.pdf"), "wb").write(b"%PDF-1.4 x")
        fence_root2 = tempfile.mkdtemp(prefix="ingest_post_fenceroot_")
        try:
            _subprocess_mod.Popen = _fake_popen
            sys.modules["safeguard"] = _FakeSafeguard()
            _ingest_mod._INGEST = {"proc": None, "path": "", "started": 0.0}

            # fence: folder outside the configured roots -> ok:false, no subprocess ever launched.
            # (p_ingest always answers HTTP 200 -- the fence result travels in the JSON body, same
            # as ingest_start()'s own contract -- so we assert on the body, not the status code.)
            os.environ["VIEWER_INGEST_ROOTS"] = fence_root2
            c, b = _req("/api/ingest", {"path": ingest_dir})
            r = _json(b)
            check("POST /api/ingest fence rejects outside folder (ok:false)", c == 200 and r.get("ok") is False)
            check("POST /api/ingest fence: error mentions ingest roots",
                  "ingest root" in (r.get("error") or "").lower())
            check("POST /api/ingest fence: no subprocess launched", len(_popen_calls) == 0)
            os.environ.pop("VIEWER_INGEST_ROOTS", None)

            # success path: folder allowed (no fence configured) -> ok:true, started:true, crawl launched.
            c, b = _req("/api/ingest", {"path": ingest_dir})
            r = _json(b)
            check("POST /api/ingest starts a crawl -> ok + started", c == 200 and r.get("ok") is True and r.get("started") is True)
            check("POST /api/ingest actually launched the crawl subprocess", len(_popen_calls) == 1)

            # already-running guard, exercised through the actual route (not just ingest_start()
            # called directly, which test_features.py already covers at the module level).
            _ingest_mod._INGEST = {"proc": _FakeProc(running=True), "path": ingest_dir, "started": time.time()}
            c, b = _req("/api/ingest", {"path": ingest_dir})
            r = _json(b)
            check("POST /api/ingest already-running -> ok:false", c == 200 and r.get("ok") is False)
            check("POST /api/ingest already-running error message", "already in progress" in (r.get("error") or ""))
            check("POST /api/ingest already-running: no second subprocess launched", len(_popen_calls) == 1)
        finally:
            _subprocess_mod.Popen = _real_popen
            if _real_sg_mod is not None: sys.modules["safeguard"] = _real_sg_mod
            else: sys.modules.pop("safeguard", None)
            _ingest_mod._INGEST = {"proc": None, "path": "", "started": 0.0}
            os.environ.pop("VIEWER_INGEST_ROOTS", None)

        # =====================================================================================
        # POST /api/airgap_manifest -- real signed manifest for a real folder + fence enforcement
        # =====================================================================================
        import airgap
        am_dir = tempfile.mkdtemp(prefix="airgap_manifest_src_")
        open(os.path.join(am_dir, "TM-A.pdf"), "wb").write(b"%PDF-1.4 alpha" + b"\x00" * 300)
        open(os.path.join(am_dir, "TM-B.pdf"), "wb").write(b"%PDF-1.4 bravo" + b"\x01" * 300)
        secret = "route-test-secret-2026"

        c, b = _req("/api/airgap_manifest", {"folder": am_dir, "secret": secret})
        r = _json(b)
        check("airgap_manifest -> 200 ok", c == 200 and r.get("ok") is True)
        manifest = r.get("manifest") or {}
        check("airgap_manifest counts both files", manifest.get("count") == 2)
        check("airgap_manifest signature validates with the real secret", airgap.signature_valid(manifest, secret))
        check("airgap_manifest signature rejects the wrong secret", not airgap.signature_valid(manifest, "wrong-secret"))

        fence_root3 = tempfile.mkdtemp(prefix="airgap_manifest_fenceroot_")
        os.environ["VIEWER_INGEST_ROOTS"] = fence_root3
        try:
            c, b = _req("/api/airgap_manifest", {"folder": am_dir, "secret": secret})
            check("airgap_manifest fence rejects a folder outside VIEWER_INGEST_ROOTS -> 400", c == 400)
        finally:
            os.environ.pop("VIEWER_INGEST_ROOTS", None)

        # =====================================================================================
        # POST /api/airgap_verify -- accept / tamper-reject / wrong-secret-reject + fence
        # =====================================================================================
        av_src = tempfile.mkdtemp(prefix="airgap_verify_src_")
        open(os.path.join(av_src, "TM-C.pdf"), "wb").write(b"%PDF-1.4 charlie" + b"\x02" * 300)
        av_secret = "route-verify-secret-2026"
        av_manifest = airgap.make_manifest(av_src, ["TM-C.pdf"], av_secret)

        av_dst = tempfile.mkdtemp(prefix="airgap_verify_dst_")
        shutil.copy(os.path.join(av_src, "TM-C.pdf"), os.path.join(av_dst, "TM-C.pdf"))

        c, b = _req("/api/airgap_verify", {"manifest": av_manifest, "folder": av_dst, "secret": av_secret})
        r = _json(b)
        result = r.get("result") or {}
        check("airgap_verify -> 200 ok", c == 200 and r.get("ok") is True)
        check("airgap_verify accepts a clean transfer", result.get("ok") is True and result.get("verdict") == "ACCEPT")

        with open(os.path.join(av_dst, "TM-C.pdf"), "r+b") as f:
            f.seek(20); f.write(b"\xff\xff")
        c, b = _req("/api/airgap_verify", {"manifest": av_manifest, "folder": av_dst, "secret": av_secret})
        r = _json(b); result = r.get("result") or {}
        check("airgap_verify rejects a tampered file", result.get("ok") is False and result.get("verdict") == "REJECT")
        check("airgap_verify reports the tampered filename", "TM-C.pdf" in (result.get("tampered") or []))

        shutil.copy(os.path.join(av_src, "TM-C.pdf"), os.path.join(av_dst, "TM-C.pdf"))   # restore clean copy
        c, b = _req("/api/airgap_verify", {"manifest": av_manifest, "folder": av_dst, "secret": "attacker-guess"})
        r = _json(b); result = r.get("result") or {}
        check("airgap_verify rejects the wrong secret", result.get("ok") is False and result.get("signature_valid") is False)

        fence_root4 = tempfile.mkdtemp(prefix="airgap_verify_fenceroot_")
        os.environ["VIEWER_INGEST_ROOTS"] = fence_root4
        try:
            c, b = _req("/api/airgap_verify", {"manifest": av_manifest, "folder": av_dst, "secret": av_secret})
            check("airgap_verify fence rejects a folder outside VIEWER_INGEST_ROOTS -> 400", c == 400)
        finally:
            os.environ.pop("VIEWER_INGEST_ROOTS", None)

        # =====================================================================================
        # POST /api/form_2404 + /api/form_2407 -- filled payload data actually renders into the PDF
        # =====================================================================================
        try:
            import forms as _forms
        except Exception:
            _forms = None
        if _forms is not None and _forms.available():
            _fitz = None
            for _modname in ("pymupdf", "fitz"):
                try:
                    _fitz = __import__(_modname); break
                except Exception:
                    continue
            if _fitz is not None:
                payload_2404 = {
                    "equipment": {"admin_no": "RT-2404-ADMIN-99", "nomenclature": "ROUTE TEST TRUCK"},
                    "faults": [{"item": "5", "deficiency": "ROUTE_TEST_DEFICIENCY_TEXT",
                                "corrective": "ROUTE_TEST_CORRECTIVE_TEXT", "status": "X"}],
                }
                c, b = _req("/api/form_2404", payload_2404)
                check("POST /api/form_2404 -> 200 PDF", c == 200 and b[:5] == b"%PDF-")
                doc = _fitz.open(stream=b, filetype="pdf")
                text_2404 = "\n".join(p.get_text() for p in doc)
                doc.close()
                check("POST /api/form_2404 fills admin_no into the PDF", "RT-2404-ADMIN-99" in text_2404)
                check("POST /api/form_2404 fills deficiency text into the PDF", "ROUTE_TEST_DEFICIENCY_TEXT" in text_2404)
                check("POST /api/form_2404 fills corrective text into the PDF", "ROUTE_TEST_CORRECTIVE_TEXT" in text_2404)

                payload_2407 = {
                    "organization": "RT-2407-ORG", "wo_no": "RT-WO-0099",
                    "equipment": {"admin_no": "RT-2407-ADMIN-77", "nomenclature": "ROUTE TEST TRAILER"},
                    "fault": "ROUTE_TEST_FAULT_NARRATIVE", "work_requested": "ROUTE_TEST_WORK_REQUESTED_TEXT",
                }
                c, b = _req("/api/form_2407", payload_2407)
                check("POST /api/form_2407 -> 200 PDF", c == 200 and b[:5] == b"%PDF-")
                doc = _fitz.open(stream=b, filetype="pdf")
                text_2407 = "\n".join(p.get_text() for p in doc)
                doc.close()
                check("POST /api/form_2407 fills admin_no into the PDF", "RT-2407-ADMIN-77" in text_2407)
                check("POST /api/form_2407 fills fault text into the PDF", "ROUTE_TEST_FAULT_NARRATIVE" in text_2407)
                check("POST /api/form_2407 fills work_requested text into the PDF", "ROUTE_TEST_WORK_REQUESTED_TEXT" in text_2407)
            else:
                print("SKIP form_2404/2407 filled-payload text checks (PyMuPDF not installed)")
        else:
            print("SKIP form_2404/2407 filled-payload text checks (reportlab not installed)")
    finally:
        if _orig_roots is None: os.environ.pop("VIEWER_INGEST_ROOTS", None)
        else: os.environ["VIEWER_INGEST_ROOTS"] = _orig_roots
        srv.shutdown()

    fails = [n for n, ok in tests if not ok]
    for n, ok in tests:
        print(("PASS " if ok else "FAIL ") + n)
    print("\n%d passed, %d failed" % (len(tests) - len(fails), len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

# END OF FILE
