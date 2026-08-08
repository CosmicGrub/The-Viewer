#!/usr/bin/env python3
"""v0.96.0 hardening acceptance (backlog B9/B11/B13, J67-J70): start the real server on the
deterministic fixture index and assert the NEW defensive behaviors:

  - malformed params answer 400 (central validation), never 500
  - unknown paths answer 404 JSON
  - an oversized POST body is refused 413 WITHOUT reading it (connection closed)
  - a cross-origin POST is refused 403; same-origin (and no-Origin tools) pass
  - /shared.js + /base.css (the deduplicated UI foundation) are served
  - /healthz and /api/ops carry the VERSION constant
  - a traversal-style /api/ingest_preview path answers ok:false (canonicalized)

Pure stdlib. RUN ON WINDOWS / a coherent env (imports viewer_app)."""
import http.client
import json
import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)
import fixture                                            # noqa: E402

PORT = 8893


def _req(path, data=None, hdrs=None):
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), data=data, headers=hdrs or {})
    try:
        with urllib.request.urlopen(r, timeout=10) as x:
            return x.status, x.read()[:200]
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:200]
    except Exception as e:
        return -1, str(e).encode()


def _raw_oversize():
    """Claim a huge Content-Length and read the refusal without ever sending the body."""
    c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=10)
    c.putrequest("POST", "/api/tags")
    c.putheader("Content-Length", str(9 * 1024 * 1024))
    c.putheader("Content-Type", "application/json")
    c.endheaders()
    r = c.getresponse()
    return r.status, r.read()[:80]


def main():
    tmp = tempfile.mkdtemp()
    db, _corr = fixture.build(tmp)
    import viewer_app as V
    V.DB_PATH = db; V.INDEX_DIR = os.path.dirname(db)
    from http.server import ThreadingHTTPServer
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), V.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); time.sleep(0.4)

    tests = []
    c, b = _req("/api/search?q=brake&limit=abc"); tests.append(("bad limit -> 400 (B11)", c == 400))
    c, b = _req("/api/doc?id=zzz"); tests.append(("bad id -> 400 (B11)", c == 400))
    c, b = _req("/nope/nothing"); tests.append(("unknown path -> 404 JSON", c == 404 and b.startswith(b"{")))
    c, b = _req("/shared.js"); tests.append(("/shared.js served (A2)", c == 200))
    c, b = _req("/base.css"); tests.append(("/base.css served (A3)", c == 200))
    c, b = _req("/api/ops"); tests.append(("/api/ops carries version (N89)", c == 200 and b"version" in b))
    c, b = _req("/healthz"); tests.append(("/healthz carries version (N89)", b"version" in b))
    c, b = _raw_oversize(); tests.append(("oversize POST -> 413 unread (B13)", c == 413))
    c, b = _req("/api/tags", data=b"{}",
                hdrs={"Content-Type": "application/json", "Origin": "http://evil.example"})
    tests.append(("cross-origin POST -> 403 (J68)", c == 403))
    c, b = _req("/api/tags", data=json.dumps({"nsn": "5305-01-674-1467", "tag": "hardening"}).encode(),
                hdrs={"Content-Type": "application/json", "Origin": "http://127.0.0.1:%d" % PORT})
    tests.append(("same-origin POST passes (J68)", c == 200))
    c, b = _req("/api/ingest_preview?path=..%2F..%2F..%2Fnowhere")
    tests.append(("traversal ingest path -> ok:false (J70)", c == 200 and b"false" in b))
    c, b = _req("/api/search?q=brake&limit=5"); tests.append(("normal search still 200", c == 200))

    fails = [n for n, ok in tests if not ok]
    for n, ok in tests:
        print(("PASS " if ok else "FAIL ") + n)
    print("\n%d passed, %d failed" % (len(tests) - len(fails), len(fails)))
    srv.shutdown()
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
