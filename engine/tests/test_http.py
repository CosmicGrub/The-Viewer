#!/usr/bin/env python3
"""THE VIEWER -- HTTP-LEVEL INTEGRATION + FUZZ (v0.99.30). Spins the real app on a test port against a tiny synthetic
index, then hits every registered GET route (with benign + adversarial params) and asserts the server NEVER returns a
5xx and /api routes return parseable JSON. Complements the unit/property fuzz with real request-path coverage.
Run host-side (needs the app importable): python tests/test_http.py   [N_fuzz]"""
import os, sys, time, json, socket, sqlite3, tempfile, subprocess, urllib.request, urllib.error, random, string

HERE = os.path.dirname(os.path.abspath(__file__))
ENG = os.path.join(HERE, "..")
sys.path.insert(0, ENG)


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


# Routes that legitimately return a binary body (PDF/PNG/SVG), not JSON, on a successful /api/ GET --
# mirrors the expect_json=False list test_routes.py already curates for the same routes.
BINARY_API_ROUTES = {
    "/api/form_2404", "/api/form_2407", "/api/partspdf", "/api/callout_crop",
    "/api/qr", "/api/specsheet", "/api/figuresheet", "/api/jobcard", "/api/jobpack",
}


def _is_binary_route(url):
    path = url.split("?", 1)[0]
    return path in BINARY_API_ROUTES


def _synth_db():
    # documents' columns mirror migrations/0001_init.sql (rel_path/fingerprint/type/nsn/page_count/etc.) --
    # a stripped-down subset here previously caused false-positive 500s (missing-column errors) on every
    # route that touches documents (by_side, chapters*, doc, vehicles, search): the routes were fine, this
    # fixture just drifted from the real schema. Keep it in sync; see engine/migrations/0001_init.sql.
    d = tempfile.mkdtemp(prefix="httptest_"); db = os.path.join(d, "viewer.db"); c = sqlite3.connect(db)
    c.execute("CREATE TABLE documents(id INTEGER PRIMARY KEY, path TEXT, rel_path TEXT, fingerprint TEXT, "
              "type TEXT, tm_number TEXT, nsn TEXT, title TEXT, vehicle TEXT, page_count INTEGER DEFAULT 0, "
              "size_bytes INTEGER, mtime REAL, status TEXT DEFAULT 'discovered', "
              "created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now')))")
    c.execute("CREATE TABLE parts(id INTEGER PRIMARY KEY, document_id INT, page INT, nsn TEXT, part_number TEXT, name TEXT, nomenclature TEXT, cagec TEXT, smr TEXT, uoc TEXT, fig_no TEXT, fig_title TEXT)")
    c.execute("CREATE TABLE pages(id INTEGER PRIMARY KEY, document_id INT, page_number INT, body_text TEXT, char_count INT, source TEXT, ocr_status TEXT, ocr_priority INT)")
    c.execute("INSERT INTO documents(id,path,type,tm_number,nsn,title,vehicle,page_count,status) "
              "VALUES(1,'/x/a.pdf','pdf_text','TM 9-2320-280-24P','5305-01-111-1111','Maint','HMMWV M998',12,'indexed')")
    c.execute("INSERT INTO parts(document_id,page,nsn,name,fig_no,fig_title) VALUES(1,12,'5305-01-111-1111','BOLT','FIG 5','ELEC')")
    c.execute("INSERT INTO pages(document_id,page_number,body_text,ocr_status) VALUES(1,12,'PREVENTIVE MAINTENANCE CHECKS AND SERVICES. 1. Check the bolt torque to 30 ft-lb.','done')")
    c.commit(); c.close(); return db


def main():
    n_fuzz = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    db = _synth_db(); port = _free_port()
    proc = subprocess.Popen([sys.executable, os.path.join(ENG, "viewer_app.py"), "--db", db, "--port", str(port)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = "http://127.0.0.1:%d" % port
    fails = []; hit = 0
    try:
        # wait for the server
        for _ in range(50):
            try:
                urllib.request.urlopen(base + "/", timeout=1); break
            except Exception:
                time.sleep(0.2)
        # discover routes from the live registry (import viewer_app first so routes get registered)
        import viewer_app  # noqa: F401
        from features import registry as REG
        routes = sorted(REG.GET.keys())
        rng = random.Random(1234)
        vals = ["", "alternator", "5305-01-111-1111", "1", "-9", "abc", "9" * 40, "%00", "1;DROP TABLE parts", "٣", "<x>"]

        def probe(url):
            nonlocal hit
            try:
                r = urllib.request.urlopen(base + url, timeout=8); code = r.getcode(); body = r.read(200000)
            except urllib.error.HTTPError as e:
                code = e.code; body = b""
            except Exception as e:
                fails.append("%s -> transport error %r" % (url, e)); return
            hit += 1
            if code >= 500:
                fails.append("%s -> HTTP %d (5xx)" % (url, code))
            if url.startswith("/api/") and code < 400 and not _is_binary_route(url):
                try:
                    json.loads(body.decode("utf-8", "replace"))
                except Exception:
                    fails.append("%s -> non-JSON body from /api" % url)

        # 1) every GET route, bare
        for rt in routes:
            if "%" in rt or "{" in rt:
                continue
            probe(rt)
        # 2) fuzz the param-taking api routes
        api = [r for r in routes if r.startswith("/api/")]
        if not api:
            n_fuzz = 0
        for _ in range(n_fuzz):
            rt = rng.choice(api); pn = rng.choice(["q", "vehicle", "doc", "page", "limit", "nf", "n"])
            probe("%s?%s=%s" % (rt, pn, urllib.parse.quote(rng.choice(vals))))
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except Exception: proc.kill()
    print("=" * 56)
    print("HTTP integration/fuzz: %d requests, %d routes" % (hit, len(routes) if 'routes' in dir() else 0))
    if fails:
        print("FAILURES (%d):" % len(fails))
        for f in fails[:25]:
            print("  FAIL", f)
        return 1
    print("no 5xx, all /api responses parseable as JSON.")
    return 0


if __name__ == "__main__":
    import urllib.parse
    sys.exit(main())
# END OF FILE
