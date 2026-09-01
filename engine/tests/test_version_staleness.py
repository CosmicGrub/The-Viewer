#!/usr/bin/env python3
"""Regression tests for v1.42.0 version-staleness detection (engine/viewer_app.py's
STARTUP_VERSION/STARTUP_TIME/current_disk_version(), and the new fields it feeds on /healthz and
/api/ops).

Exercises the real scenario this feature exists for: a server process keeps running while the code
on disk is changed underneath it (e.g. `git pull` without a restart). Starts a REAL HTTP server
(ThreadingHTTPServer + viewer_app.Handler, same pattern as test_ops_status.py), then:

  1. confirms a freshly-started process reports no mismatch (code_changed_since_start == False)
     against its own on-disk file,
  2. safely rewrites the VERSION= line in the actual engine/viewer_app.py on disk (saving/restoring
     the original bytes in a try/finally so a crash mid-test can't leave the repo file mutated),
     forces the disk-version cache to expire, and confirms the mismatch IS now reported via both
     /healthz and /api/ops,
  3. confirms a second, freshly-started process reading that same (now-changed) on-disk file reports
     NO mismatch -- STARTUP_VERSION tracks whatever VERSION the process actually launched with, not
     a fixed historical constant,
  4. confirms the disk re-read is TTL-cached: back-to-back /healthz calls within the TTL don't add
     meaningful per-request latency (a file open+regex per request would be the wrong design here).

RUN ON WINDOWS / a coherent env -- it imports viewer_app, and it edits the real
engine/viewer_app.py file on disk for step 2/3 (reverted immediately afterward). Pure stdlib runner.
"""
import json
import os
import re
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)
import fixture                                                    # noqa: E402


def _req(base, path):
    try:
        with urllib.request.urlopen(base + path, timeout=10) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read()
        try: return e.code, json.loads(raw.decode("utf-8"))
        except Exception: return e.code, raw
    except Exception as e:
        return -1, str(e)


def _start_server(V, tmp):
    from http.server import ThreadingHTTPServer
    srv = ThreadingHTTPServer(("127.0.0.1", 0), V.Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start(); time.sleep(0.3)
    return srv, "http://127.0.0.1:%d" % port


def main():
    tests = []
    tmp = tempfile.mkdtemp(prefix="viewer_version_staleness_")
    db, _corr = fixture.build(tmp)

    viewer_app_path = os.path.join(ENGINE, "viewer_app.py")
    with open(viewer_app_path, "r", encoding="utf-8") as f:
        original_source = f.read()

    import viewer_app as V
    V.DB_PATH = db; V.INDEX_DIR = os.path.dirname(db)

    srv, base = _start_server(V, tmp)
    try:
        # ---- 1. fresh process, unmodified disk -> no mismatch reported -----------------------------
        c, b = _req(base, "/healthz")
        tests.append(("GET /healthz -> 200", c == 200))
        tests.append(("healthz reports started_with_version == version (fresh process)",
                      b.get("started_with_version") == V.STARTUP_VERSION == b.get("version")))
        tests.append(("healthz code_changed_since_start is False initially", b.get("code_changed_since_start") is False))
        tests.append(("healthz carries a started_at timestamp", isinstance(b.get("started_at"), str) and len(b.get("started_at") or "") > 0))

        c, b = _req(base, "/api/ops")
        tests.append(("GET /api/ops -> 200", c == 200))
        tests.append(("ops reports started_with_version == version (fresh process)",
                      b.get("started_with_version") == V.STARTUP_VERSION == b.get("version")))
        tests.append(("ops code_changed_since_start is False initially", b.get("code_changed_since_start") is False))
        tests.append(("ops carries a started_at timestamp", isinstance(b.get("started_at"), str) and len(b.get("started_at") or "") > 0))

        # ---- 4. TTL cache: back-to-back calls don't each pay a disk read ---------------------------
        t0 = time.time()
        for _ in range(20):
            _req(base, "/healthz")
        elapsed = time.time() - t0
        tests.append(("20 back-to-back /healthz calls complete quickly (cached disk read, <3s total, got %.2fs)" % elapsed,
                      elapsed < 3.0))

        # ---- 2. mutate the real on-disk VERSION line, force the cache to expire, confirm mismatch --
        new_version = "9.9.9-test-staleness"
        mutated_source = re.sub(r'VERSION = "[^"]+"', 'VERSION = "%s"' % new_version, original_source, count=1)
        assert mutated_source != original_source, "VERSION= line pattern did not match -- test fixture assumption broken"
        try:
            with open(viewer_app_path, "w", encoding="utf-8") as f:
                f.write(mutated_source)
            V._disk_version_cache["t"] = 0.0   # force the TTL cache to re-read on next call

            c, b = _req(base, "/healthz")
            tests.append(("healthz detects on-disk VERSION change -> code_changed_since_start True",
                          c == 200 and b.get("code_changed_since_start") is True))
            tests.append(("healthz version stays the running process's version (unchanged)",
                          b.get("version") == V.STARTUP_VERSION))
            tests.append(("healthz started_with_version unchanged by the disk edit",
                          b.get("started_with_version") == V.STARTUP_VERSION))

            c, b = _req(base, "/api/ops")
            tests.append(("ops detects on-disk VERSION change -> code_changed_since_start True",
                          c == 200 and b.get("code_changed_since_start") is True))
            tests.append(("ops version stays the running process's version (unchanged)",
                          b.get("version") == V.STARTUP_VERSION))

            # ---- 3. a FRESH process started against this now-mutated file sees no mismatch ---------
            import subprocess
            check = subprocess.run(
                [sys.executable, "-c",
                 "import sys; sys.path.insert(0, %r); import viewer_app as V2; "
                 "print(V2.STARTUP_VERSION); print(V2.current_disk_version()); "
                 "print(V2.current_disk_version() == V2.STARTUP_VERSION)" % ENGINE],
                capture_output=True, text=True, timeout=30)
            out_lines = [l.strip() for l in (check.stdout or "").splitlines() if l.strip()]
            tests.append(("fresh subprocess against mutated disk starts clean (no output error)",
                          check.returncode == 0 and len(out_lines) >= 3))
            if len(out_lines) >= 3:
                tests.append(("fresh subprocess STARTUP_VERSION reflects the mutated on-disk value",
                              out_lines[0] == new_version))
                tests.append(("fresh subprocess sees no staleness against the file it just loaded",
                              out_lines[2] == "True"))
        finally:
            with open(viewer_app_path, "w", encoding="utf-8") as f:
                f.write(original_source)

        # confirm the running (never-restarted) process, now pointed at the RESTORED original file,
        # goes back to reporting no mismatch once its cache expires again
        V._disk_version_cache["t"] = 0.0
        c, b = _req(base, "/healthz")
        tests.append(("healthz returns to code_changed_since_start False after the disk file is restored",
                      c == 200 and b.get("code_changed_since_start") is False))

    finally:
        srv.shutdown()
        # belt-and-suspenders: guarantee the repo file is never left mutated even on an early exception
        with open(viewer_app_path, "r", encoding="utf-8") as f:
            current = f.read()
        if current != original_source:
            with open(viewer_app_path, "w", encoding="utf-8") as f:
                f.write(original_source)

    fails = [n for n, ok in tests if not ok]
    for n, ok in tests:
        print(("PASS " if ok else "FAIL ") + n)
    print("\n%d passed, %d failed" % (len(tests) - len(fails), len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
