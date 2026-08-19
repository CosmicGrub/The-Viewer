#!/usr/bin/env python3
"""Direct-coverage regression tests for engine/features/routes/ops_status.py.

Targets three gaps a deep audit found with zero test coverage on this file:

  1. POST /api/signoff and POST /api/rps_mode called .strip() on raw JSON-body fields with no type
     guard -> any client sending a non-string value (int/list/dict) crashed with an uncaught
     AttributeError, caught only by the generic top-level handler as a 500 -- violating this
     codebase's own documented invariant (registry.py's ParamError docstring: "malformed client
     input -> ParamError -> 400 (never a 500)"). The existing POST blanket-sweep in test_routes.py
     only ever sends an EMPTY body ({}), which never exercises a wrong-typed field.
  2. GET /api/coverage?vehicle= did an EXACT SQL match against documents.vehicle with no
     normalization, so a value differing only in case/whitespace from the stored value silently
     returned {"coverage": null} instead of the real data.
  3. The signoff module (append-only SME review/audit workflow: submit/approve/reject/override) and
     core.set_run_mode() (persists the Settings-panel run-mode choice) were never imported by ANY
     test file -- nothing verified the audit trail records real decisions correctly, or that an
     override is distinguishable from a plain approve.

RUN ON WINDOWS / a coherent env -- it imports viewer_app. Pure stdlib runner."""
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
import fixture                                                    # noqa: E402


def _req(base, path, data=None, method=None):
    hdrs = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(base + path,
                                 data=(json.dumps(data).encode() if data is not None else None),
                                 headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read()
        try: return e.code, json.loads(raw.decode("utf-8"))
        except Exception: return e.code, raw
    except Exception as e:
        return -1, str(e)


def main():
    tests = []
    tmp = tempfile.mkdtemp(prefix="viewer_ops_status_")
    db, _corr = fixture.build(tmp)
    import viewer_app as V
    V.DB_PATH = db; V.INDEX_DIR = os.path.dirname(db)
    # Isolate the persisted run-mode setting into this test's own tempdir -- set_run_mode() writes
    # through settings.py's module-level SETTINGS_PATH; without this override a run of this test
    # would durably rewrite the real repo's index/viewer_settings.json.
    import settings as _settings_mod
    _settings_mod.SETTINGS_PATH = os.path.join(tmp, "viewer_settings.json")

    from http.server import ThreadingHTTPServer
    srv = ThreadingHTTPServer(("127.0.0.1", 0), V.Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start(); time.sleep(0.3)
    base = "http://127.0.0.1:%d" % port

    try:
        # ---- /api/signoff: real submit/approve/reject/override round trip + audit trail ----------
        c, b = _req(base, "/api/signoff")
        tests.append(("GET /api/signoff (empty queue) -> 200", c == 200 and b.get("ok") is True))

        c, b = _req(base, "/api/signoff", {"kind": "torque", "key": "HMMWV mounting bolt",
                                            "action": "submit", "value": "85 ft-lb", "by": "tester"})
        tests.append(("POST signoff submit -> 200 ok", c == 200 and b.get("ok") is True and "event_id" in b))
        tests.append(("submit -> status pending", (b.get("status") or {}).get("status") == "pending"))

        c, b = _req(base, "/api/signoff?kind=torque&key=HMMWV%20mounting%20bolt")
        tests.append(("GET signoff status after submit -> pending",
                      c == 200 and b.get("status", {}).get("status") == "pending"))
        tests.append(("audit trail has 1 event (submit)", len(b.get("audit") or []) == 1
                      and b["audit"][0]["action"] == "submit"))

        c, b = _req(base, "/api/signoff", {"kind": "torque", "key": "HMMWV mounting bolt",
                                            "action": "approve", "by": "sme1"})
        tests.append(("POST signoff approve -> 200 ok, status verified",
                      c == 200 and b.get("ok") is True and b["status"]["status"] == "verified"))

        c, b = _req(base, "/api/signoff?kind=torque&key=HMMWV%20mounting%20bolt")
        tests.append(("audit trail now has 2 events, latest is approve",
                      len(b.get("audit") or []) == 2 and b["audit"][-1]["action"] == "approve"))

        # override must be distinguishable from approve in the audit log (both map to the same
        # "verified" status, but the recorded action string must differ)
        _req(base, "/api/signoff", {"kind": "nsn", "key": "2530-01-367-8888", "action": "submit",
                                     "value": "v1", "by": "tester"})
        c, b = _req(base, "/api/signoff", {"kind": "nsn", "key": "2530-01-367-8888",
                                            "action": "override", "by": "sme2",
                                            "value": "v2-corrected", "note": "corrected"})
        tests.append(("POST signoff override -> 200 ok, status verified",
                      c == 200 and b.get("ok") is True and b["status"]["status"] == "verified"))
        c, b = _req(base, "/api/signoff?kind=nsn&key=2530-01-367-8888")
        tests.append(("override recorded as 'override', not 'approve', in the audit trail",
                      b["audit"][-1]["action"] == "override"))

        c, b = _req(base, "/api/signoff", {"kind": "dimension", "key": "reject-me",
                                            "action": "reject", "by": "sme3"})
        tests.append(("POST signoff reject -> status rejected",
                      c == 200 and b["status"]["status"] == "rejected"))

        c, b = _req(base, "/api/signoff", {"kind": "torque", "key": ""})
        tests.append(("POST signoff missing key -> 400", c == 400))

        c, b = _req(base, "/api/signoff", {"kind": "torque", "key": "x", "action": "not-a-verb"})
        tests.append(("POST signoff bad action -> 400", c == 400))

        # ---- regression: non-string payload fields must 400, never crash 500 (the confirmed bug) --
        for bad_body in ({"kind": 123, "key": "x", "action": "submit", "value": "v"},
                         {"kind": "torque", "key": ["a", "b"], "action": "submit"},
                         {"kind": "torque", "key": "x", "action": 42},
                         {"kind": "torque", "key": "x", "action": "submit", "by": {"n": 1}}):
            c, b = _req(base, "/api/signoff", bad_body)
            tests.append(("POST signoff non-string field %r -> 400 (not 500)" % (bad_body,),
                          c == 400 and isinstance(b, dict) and "error" in b))

        # ---- /api/rps_mode: persist + re-apply the Settings-panel run-mode choice ------------------
        c, b = _req(base, "/api/rps")
        tests.append(("GET /api/rps -> 200", c == 200))
        rps_available = c == 200 and "setting" in b and b.get("reason") != "rps module unavailable"

        if rps_available:
            c, b = _req(base, "/api/rps_mode", {"setting": "performance"})
            tests.append(("POST rps_mode performance -> 200 ok", c == 200 and b.get("ok") is True))
            tests.append(("rps_mode response reflects the new setting", b.get("setting") == "performance"))

            c, b = _req(base, "/api/rps")
            tests.append(("GET /api/rps reflects persisted setting", c == 200 and b.get("setting") == "performance"))

            c, b = _req(base, "/api/rps_mode", {"mode": "retro"})   # "mode" alias
            tests.append(("POST rps_mode via 'mode' alias -> 200 ok",
                          c == 200 and b.get("ok") is True and b.get("setting") == "retro"))

            c, b = _req(base, "/api/rps_mode", {})
            tests.append(("POST rps_mode missing setting -> 400", c == 400))

            for bad_body in ({"setting": 123}, {"setting": ["performance"]}, {"mode": {"x": 1}}):
                c, b = _req(base, "/api/rps_mode", bad_body)
                tests.append(("POST rps_mode non-string field %r -> 400 (not 500)" % (bad_body,),
                              c == 400 and isinstance(b, dict) and "error" in b))
        else:
            tests.append(("rps module unavailable in this build -- skipping rps_mode assertions", True))

        # ---- /api/coverage?vehicle=: case/whitespace-insensitive resolution ------------------------
        c, b = _req(base, "/api/coverage?vehicle=M915%20Truck")
        tests.append(("coverage exact-case vehicle -> real data", c == 200 and b.get("coverage") is not None))
        exact_total = (b.get("coverage") or {}).get("total")

        c, b = _req(base, "/api/coverage?vehicle=m915%20truck")     # lowercase
        tests.append(("coverage lowercase vehicle -> resolved (not null)",
                      c == 200 and b.get("coverage") is not None and b["coverage"].get("total") == exact_total))

        c, b = _req(base, "/api/coverage?vehicle=%20%20M915%20Truck%20%20")   # surrounding whitespace
        tests.append(("coverage whitespace-padded vehicle -> resolved (not null)",
                      c == 200 and b.get("coverage") is not None and b["coverage"].get("total") == exact_total))

        c, b = _req(base, "/api/coverage?vehicle=NoSuchVehicleXYZ")
        tests.append(("coverage for a genuinely unknown vehicle -> still null", c == 200 and b.get("coverage") is None))

    finally:
        srv.shutdown()

    fails = [n for n, ok in tests if not ok]
    for n, ok in tests:
        print(("PASS " if ok else "FAIL ") + n)
    print("\n%d passed, %d failed" % (len(tests) - len(fails), len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
