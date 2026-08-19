#!/usr/bin/env python3
"""THE VIEWER -- status / ops / health / command-center / data-integrity / sign-off routes (v1.14
routes/ split). Moved verbatim out of the former monolithic engine/features/routes.py. DI via
`core`. NOTE: r_coverage lives here (not in schematics.py, its original section) because it shares
_coverage_overview_cached with r_command_status -- colocating avoids duplicating that cache."""
import os
import time
import threading as _threading

from features.registry import get, post, qstr, qint, qflag, safe_header_token
from features.routes._shared import _exposed_read_guard, _signoff_db

core = None          # injected by viewer_app at startup


@get("/api/status")
def r_status(h, qs):
    if not _exposed_read_guard(h): return
    h._send(200, core.status_summary())


@get("/api/ops")
def r_ops(h, qs):
    if not _exposed_read_guard(h): return
    h._send(200, core.ops_summary())


_COMMAND_STATUS_CACHE = {"t": 0.0, "body": None}
_COMMAND_STATUS_TTL = 60.0           # v1.13.4: see note at the handler -- same TTL as _SEARCH_LRU
_COMMAND_STATUS_LOCK = _threading.Lock()

_COVERAGE_OVERVIEW_CACHE = {"t": 0.0, "body": None}
_COVERAGE_OVERVIEW_TTL = 60.0
_COVERAGE_OVERVIEW_LOCK = _threading.Lock()


def _coverage_overview_cached():
    """TTL-cached coverage.overview() -- the same 12-53s aggregate (a COUNT(*) scan reading every page's
    body_text) is called from BOTH /api/command_status and /api/coverage (no ?vehicle=, backing /coverage
    and /ops). v1.13.4: /api/coverage had no caching at all -- the same 'page silently hangs on Loading...'
    regression diagnosed and fixed for /command, still live on its other call site. Centralized here (one
    cache, one TTL) instead of each route keeping a separate copy, so the two routes share one computation
    per window instead of each paying the full cost independently."""
    now = time.time()
    with _COVERAGE_OVERVIEW_LOCK:
        if _COVERAGE_OVERVIEW_CACHE["body"] is not None and (now - _COVERAGE_OVERVIEW_CACHE["t"]) < _COVERAGE_OVERVIEW_TTL:
            return _COVERAGE_OVERVIEW_CACHE["body"]
    import coverage
    body = coverage.overview(core.DB_PATH, core.INDEX_DIR)
    with _COVERAGE_OVERVIEW_LOCK:
        _COVERAGE_OVERVIEW_CACHE["t"] = time.time(); _COVERAGE_OVERVIEW_CACHE["body"] = body
    return body


@get("/api/coverage")
def r_coverage(h, qs):
    # ONE handler (was a duplicate-route collision): ?vehicle= -> per-vehicle coverage (home-page widget);
    # otherwise the mission-control overview (the /coverage page and /ops page).
    v = qstr(qs, "vehicle")
    if v:
        cov = core.coverage(v)
        h._send(200, {"vehicle": v, "coverage": cov.get(v) if isinstance(cov, dict) else cov})
        return
    h._send(200, _coverage_overview_cached())


@get("/api/command_status")
def r_command_status(h, qs):
    # ONE 'are we complete?' aggregate for the command center: OCR progress, corpus coverage, PUBLOG build
    # state, and Masterfile dimensional gaps. Every piece best-effort so one missing sidecar can't 500.
    # v1.13.4: coverage.overview() alone measured 12-53s cold (a COUNT(*) scan of every page's body_text
    # across an 892k-row/3.65GB+ table -- slow until the OS file cache warms, worse on a bigger corpus or
    # a memory-constrained box) -- live on /command, that read as the page silently hanging on "Loading...".
    # TTL-cache the whole aggregate like _SEARCH_LRU already does for search: the underlying data only
    # changes as OCR/ingest progress, so a 60s-stale "glance" dashboard is fine, and it makes every load
    # after the first one instant instead of re-paying the full aggregate cost every single time.
    if not _exposed_read_guard(h): return
    now = time.time()
    with _COMMAND_STATUS_LOCK:
        if _COMMAND_STATUS_CACHE["body"] is not None and (now - _COMMAND_STATUS_CACHE["t"]) < _COMMAND_STATUS_TTL:
            h._send(200, _COMMAND_STATUS_CACHE["body"]); return
    import os
    out = {}
    try:
        out["ocr"] = core.status_summary()
    except Exception as e:
        out["ocr"] = {"error": str(e)}
    try:
        out["coverage"] = _coverage_overview_cached()
    except Exception as e:
        out["coverage"] = {"error": str(e)}
    try:
        import publog
        out["publog"] = publog.stats()
    except Exception as e:
        out["publog"] = {"available": False, "error": str(e)}
    try:
        import masterfile
        mp = os.path.join(os.path.dirname(core.DB_PATH), "masterfile.db")
        out["masterfile"] = masterfile.coverage(mp) if hasattr(masterfile, "coverage") else {}
    except Exception as e:
        out["masterfile"] = {"error": str(e)}
    with _COMMAND_STATUS_LOCK:
        _COMMAND_STATUS_CACHE["t"] = time.time(); _COMMAND_STATUS_CACHE["body"] = out
    h._send(200, out)


_INTEGRITY_CACHE = {"t": 0.0, "body": None}
_INTEGRITY_TTL = 300.0               # v1.13.4: see note below -- longer than _COMMAND_STATUS_TTL on purpose
_INTEGRITY_LOCK = _threading.Lock()


@get("/api/integrity")
def r_integrity(h, qs):
    # DB corruption / checksum status across the index + sidecars.
    # v1.13.4: manifest() streams a FULL SHA-256 over every byte of every listed file -- ~13GB total here
    # (viewer.db ~3.65GB + publog.db ~9GB + the smaller sidecars) -- measured 49s live, on EVERY /verify page
    # load, since this had no caching at all. TTL-cache it like _COMMAND_STATUS_CACHE; 300s (not 60s) because
    # this is heavier and the underlying files change far less often than OCR/search state. ?force=1 bypasses
    # the cache for a genuinely fresh tamper/corruption check on demand -- never silently hide that option.
    if not _exposed_read_guard(h): return
    now = time.time()
    if not qflag(qs, "force"):
        with _INTEGRITY_LOCK:
            if _INTEGRITY_CACHE["body"] is not None and (now - _INTEGRITY_CACHE["t"]) < _INTEGRITY_TTL:
                h._send(200, _INTEGRITY_CACHE["body"]); return
    import integrity, os
    d = os.path.dirname(core.DB_PATH)
    names = ["viewer.db", "publog.db", "masterfile.db", "measures.db", "tables.db", "enrich.db", "kg.db", "signoff.db"]
    paths = [os.path.join(d, n) for n in names]
    out = integrity.status(paths)
    with _INTEGRITY_LOCK:
        _INTEGRITY_CACHE["t"] = time.time(); _INTEGRITY_CACHE["body"] = out
    h._send(200, out)


@get("/api/tmrev")
def r_tmrev(h, qs):
    # TM revision / currency: is this the current manual, or is a newer change in the corpus?
    import tmrev
    tm = qstr(qs, "tm", "") or qstr(qs, "q", "")
    if len(tm) < 3:
        h._send(400, {"error": "tm required"}); return
    h._send(200, tmrev.currency(core.DB_PATH, tm))


@get("/api/verifystate")
def r_verifystate(h, qs):
    import verifystate, os
    # v1.13.4: this file is engine/features/routes.py -- reaching <root>/docs needs THREE dirname() hops
    # (features -> engine -> root), not two. Left at two since the v0.96.0 restructure moved this code out
    # of the old engine/viewer_app.py monolith (where two hops WAS correct); it's pointed at the
    # nonexistent engine/docs ever since, so /verify has never been able to find a verify log at all --
    # confirmed live: last_verify.present was False even right after a real, fully-GREEN VERIFY.bat run.
    # v1.14: this handler now lives at engine/features/routes/ops_status.py (one directory deeper than the
    # old engine/features/routes.py) -- the routes/ split -- so it needs FOUR dirname() hops to <root>/docs
    # (routes -> features -> engine -> root), not three.
    root_docs = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "docs")
    h._send(200, verifystate.snapshot(core.DB_PATH, root_docs))


@get("/api/signoff")
def r_signoff(h, qs):
    # review queue (default: pending) or the audit trail for one subject (?kind=&key=).
    import signoff
    kind = qstr(qs, "kind", ""); key = qstr(qs, "key", "")
    if kind and key:
        h._send(200, {"ok": True, "status": signoff.status_of(_signoff_db(), kind, key),
                      "audit": signoff.audit(_signoff_db(), kind, key)}); return
    h._send(200, {"ok": True, "queue": signoff.queue(_signoff_db(), qstr(qs, "status", "pending"))})


@post("/api/signoff")
def r_signoff_post(h, qs, payload):
    # submit a value for review, or record an SME decision (approve/reject/override). Append-only audit.
    import signoff
    kind = (payload.get("kind") or "").strip(); key = (payload.get("key") or "").strip()
    action = (payload.get("action") or "").strip()
    by = (payload.get("by") or "").strip() or "anonymous"
    if not kind or not key:
        h._send(400, {"error": "kind and key required"}); return
    try:
        if action == "submit":
            eid = signoff.submit(_signoff_db(), kind, key, payload.get("value"), source=payload.get("source"), by=by, note=payload.get("note"))
        elif action in ("approve", "reject", "override"):
            eid = signoff.decide(_signoff_db(), kind, key, action, by=by, value=payload.get("value"), note=payload.get("note"))
        else:
            h._send(400, {"error": "action must be submit/approve/reject/override"}); return
    except Exception as e:
        h._send(400, {"error": str(e)}); return
    h._send(200, {"ok": True, "event_id": eid, "status": signoff.status_of(_signoff_db(), kind, key)})


@get("/api/audit")
def r_audit(h, qs):
    if not _exposed_read_guard(h): return
    h._send(200, core.file_audit(qint(qs, "limit", 600, 1, 2000)))


@get("/healthz")
def r_healthz(h, qs):
    import preflight as _pf
    res = _pf.checks(core.DB_PATH)
    ok = not any(s == "FAIL" for _, s, _ in res)
    h._send(200 if ok else 503, {"ok": ok, "version": core.VERSION,
            "checks": [{"name": n, "status": s, "detail": d} for n, s, d in res]})


@get("/api/rps")
def r_rps(h, qs):
    ov = (qs.get("mode") or [None])[0]           # optional NON-persistent preview of a concrete mode
    if core._rps:
        prof = {}
        try:
            import sysprobe; prof = sysprobe.load_or_build()
        except Exception: prof = {}
        if ov:                                    # explicit preview (?mode=) -> concrete mode, no persistence
            m, why = core._rps.mode_for(prof, ov)
        elif core.RPS_OVERRIDE in core._rps.VALID_MODES:
            m, why = core._rps.mode_for(prof, core.RPS_OVERRIDE)
        else:                                     # reflect the persisted Settings choice (auto/perf/retro)
            m, why = core._rps.mode_for_setting(prof, core.RPS_SETTING)
        out = core._rps.profile_summary(prof, m, why)
        out["page_cache_stats"] = core._rps.cache_stats(core.INDEX_DIR)
        out["setting"] = core.RPS_SETTING                                    # the saved Settings-panel choice
        out["setting_labels"] = core._rps.RUN_MODE_LABELS                    # {auto|performance|retro: label}
        out["env_forced"] = bool(core.RPS_OVERRIDE in core._rps.VALID_MODES) # env/CLI VIEWER_MODE overriding UI
        out["recommended_mode"] = prof.get("recommended_run_mode")          # sysprobe's hardware pick
        h._send(200, out)
    else:
        h._send(200, {"mode": "modern", "reason": "rps module unavailable", "flags": {},
                      "setting": "auto", "setting_labels": {}, "env_forced": False})


@post("/api/rps_mode")
def p_rps_mode(h, qs, payload):
    """Persist the Settings-panel run-mode choice and re-apply it live. Body: {"setting": auto|performance|retro}
    (also accepts "mode" as an alias). Fail-loud: reports saved=False if the choice could not be written."""
    if not core._rps or not hasattr(core, "set_run_mode"):
        h._send(503, {"ok": False, "error": "run-mode switching unavailable in this build"}); return
    setting = (payload.get("setting") or payload.get("mode") or "").strip()
    if not setting:
        h._send(400, {"ok": False, "error": "missing 'setting' (auto|performance|retro)"}); return
    r = core.set_run_mode(setting)
    r["ok"] = True
    h._send(200, r)
