#!/usr/bin/env python3
"""Direct coverage for POST /api/request (engine/features/routes/parts_refs.py:p_request) -- the
104th ECC parts-request PDF route. Prior to this test the route was only exercised indirectly by
test_routes.py's blanket empty-body sweep (which sends `{}`, never a malformed `session`), so three
load-bearing behaviors had zero direct coverage:

  1. the tech_status validation gate -- including the case where the CLIENT sends `session` as a
     non-dict JSON value (string/number/list/null). Before the v1.15 fix this raised an uncaught
     AttributeError (`"not-a-dict".get(...)`) -> 500 instead of the intended 400.
  2. core.save_request(payload) actually PERSISTING the session + items (a 200 PDF response alone
     doesn't prove the record was saved).
  3. the temp-file cleanup-on-exception path (v1.13 comment in the route) -- if build_request_pdf
     raises, the NamedTemporaryFile must still be unlinked, not orphaned.

Pure stdlib runner; mirrors test_routes.py / test_hardening.py's server-spinning pattern."""
import json
import os
import sqlite3
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)
import fixture  # noqa: E402


def _post(base, path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(base + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers or {})
    except Exception as e:
        return -1, str(e).encode(), {}


def main():
    tmp = tempfile.mkdtemp(prefix="parts_request_route_")
    db, _corr = fixture.build(tmp)
    import viewer_app as V
    V.DB_PATH = db

    from http.server import ThreadingHTTPServer
    srv = ThreadingHTTPServer(("127.0.0.1", 0), V.Handler)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True); th.start()
    time.sleep(0.3)
    base = "http://127.0.0.1:%d" % port

    tests = []
    try:
        def check(name, ok):
            tests.append((name, ok))

        # ---- 1a. validation gate: MISSING session key -> 400, not 500 (pre-existing behavior) ----
        status, body, _ = _post(base, "/api/request", {"items": []})
        check("missing session key -> 400", status == 400 and b"Tech status" in body)

        # ---- 1b. validation gate: session present but EMPTY dict -> 400 ----
        status, body, _ = _post(base, "/api/request", {"session": {}, "items": []})
        check("empty session dict -> 400", status == 400 and b"Tech status" in body)

        # ---- 1c. THE bug: session sent as a non-dict JSON value -> must be a clean 400, never 500 ----
        for bad_session, label in [("not-a-dict", "string"), (42, "number"), ([1, 2], "list"), (None, "null")]:
            status, body, _ = _post(base, "/api/request", {"session": bad_session, "items": []})
            check("session as %s -> 400 (not 500)" % label,
                  status == 400 and b"Tech status" in body)

        # ---- 2. valid request: 200 PDF, AND core.save_request actually persisted the row ----
        con = sqlite3.connect(db)
        before = con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        con.close()

        session = {"mechanic": "SGT Route Test", "bumper": "RT-99", "tm": "TM 9-2320",
                   "tech_status": "NMCS", "fault": "test fault for route coverage"}
        items = [{"item_name": "BOLT, MACHINE", "nsn": "5305-01-674-1467", "qty": 3, "fig": "14"}]
        status, body, headers = _post(base, "/api/request", {"session": session, "items": items})
        check("valid request -> 200", status == 200)
        check("valid request -> application/pdf", headers.get("Content-Type") == "application/pdf")
        check("valid request -> PDF magic bytes", body[:5] == b"%PDF-")
        check("valid request -> Content-Disposition carries bumper token",
              "RT-99" in (headers.get("Content-Disposition") or ""))

        con = sqlite3.connect(db); con.row_factory = sqlite3.Row
        after = con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        row = con.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 1").fetchone()
        item_row = con.execute("SELECT * FROM request_items WHERE session_id=?", (row["id"],)).fetchone()
        con.close()
        check("save_request persisted a new sessions row", after == before + 1)
        check("save_request persisted the mechanic/bumper/tech_status fields",
              row is not None and row["mechanic"] == "SGT Route Test"
              and row["bumper_number"] == "RT-99" and row["tech_status"] == "NMCS")
        check("save_request persisted the submitted item",
              item_row is not None and item_row["nsn"] == "5305-01-674-1467")

        # ---- 3. temp-file cleanup-on-exception: build_request_pdf raising must not orphan the temp PDF ----
        iso_dir = tempfile.mkdtemp(prefix="parts_request_isolated_tmp_")
        orig_tempdir = tempfile.tempdir
        orig_build = V.build_request_pdf

        def _boom(*a, **kw):
            raise RuntimeError("forced failure for cleanup-on-exception coverage")

        tempfile.tempdir = iso_dir
        V.build_request_pdf = _boom
        try:
            status, body, _ = _post(base, "/api/request",
                                     {"session": {"tech_status": "NMCS", "bumper": "CLEANUP"}, "items": []})
            check("build_request_pdf raising -> 500 (not swallowed, not 200)", status == 500)
            leftover = os.listdir(iso_dir)
            check("no orphaned temp PDF after an exception in build_request_pdf", leftover == [])
        finally:
            tempfile.tempdir = orig_tempdir
            V.build_request_pdf = orig_build

    finally:
        srv.shutdown()

    fails = [n for n, ok in tests if not ok]
    for n, ok in tests:
        print(("PASS " if ok else "FAIL ") + n)
    print("\n%d passed, %d failed" % (len(tests) - len(fails), len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
