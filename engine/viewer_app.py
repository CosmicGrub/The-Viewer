#!/usr/bin/env python3
"""
THE VIEWER -- offline local web app (search + NSN + vehicle hub + document viewer + parts request).

v0.96.0 RESTRUCTURE (backlog A1/A5/A7 + B/J hardening): this file is now a thin shell --
configuration, the per-thread SQLite plumbing, RPS init, the HTTP Handler (one dict-lookup
dispatch inside ONE error boundary), and main(). The domain logic moved verbatim into
engine/features/ (search/parts/browse/procedures/render/ingest/sessions + routes), each using
the same `core` dependency-injection pattern as the earlier extractions (collections_feature,
sides_feature, ...). Every public name is re-exported here, so `import viewer_app as V` keeps
working for the regression suites and any script. The pre-split monolith is preserved at
backups/pre-v0.96-restructure/viewer_app.py (R1: rollback = copy back + delete features/).

Hardening shipped with the split (v0.96.0):
  B9   one error boundary -- handlers can't drop the socket; unexpected errors -> clean JSON 500
  B10  rotating server-error log (engine/logs/server-errors.log) surfaced in /api/ops
  B11  central param validation -- a bad ?limit=abc answers 400, never 500
  B13  POST body cap (413) + per-connection timeout
  B16  graceful Ctrl+C: WAL checkpoint + socket close
  J67  hard server-side row caps regardless of client
  J68  same-origin check on POST
  J69  unexpected exception text goes to the log, not the client
  J70  /api/ingest paths canonicalized (+ optional VIEWER_INGEST_ROOTS fence)

The server binds 127.0.0.1 by default (B15). To expose it on a LAN deliberately:
    python viewer_app.py --host 0.0.0.0 --port 8765
"""
import argparse, json, os, re, sqlite3, sys, tempfile, time, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    import fitz
except Exception:
    fitz = None

VERSION = "1.13.4"

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from parts_request_pdf import build_request_pdf                  # noqa: E402
from patterns import NSN_RE, norm_nsn                            # noqa: E402  (A6: canonical patterns)
try:
    from patterns import tm_side                      # operator(10) vs mechanic(20) "side of the house"
except Exception:                                     # defensive fallback (keeps the server up if patterns is unreadable)
    def tm_side(tm_number, title="", path=""):
        blob = " ".join(x for x in (tm_number or "", title or "", path or "") if x)
        codes = [m.group(1) for m in re.finditer(r"(?:^|[-\s])(\d{2,3})(&?P)?(?=$|[-\s&])", blob)]
        two = [c for c in codes if len(c) == 2 and c[0] in "1234"]
        op = mech = False
        if two:
            c = two[-1]
            if c[0] == "1": op = True; mech = (c != "10")
            else: mech = True
        if re.search(r"\d(?:&?P)\b", tm_number or "", re.I): mech = True
        if not op and not mech: mech = True
        return {"operator": op, "mechanic": mech, "coverage": (two[-1] if two else ""), "basis": "fallback"}

DB_PATH = os.path.join(HERE, "..", "index", "viewer.db")
# Federal Supply Classes that denote whole vehicles / end items (ground + a few)
FSC_VEHICLE = {"2310","2320","2330","2350","2355","1510","1520","1525","1550","2210","3805","3810","3820","3825","3895","2420","2430"}


def nsn_kind(nsn):
    return "vehicle" if nsn[:4] in FSC_VEHICLE else "part"


INDEX_DIR = os.path.abspath(os.path.dirname(DB_PATH))
try:
    import rps as _rps
except Exception:
    _rps = None
try:
    import settings as _settings
except Exception:
    _settings = None
# RPS_OVERRIDE = a CONCRETE mode forced by env/CLI (modern|lite|legacy) -- highest precedence, back-compat.
RPS_OVERRIDE = os.environ.get("VIEWER_MODE") or None
# RPS_SETTING = the USER-FACING Settings-panel choice (auto|performance|retro), persisted across restarts.
# Precedence: VIEWER_RUN_MODE env  >  saved settings file  >  "auto".  (A concrete VIEWER_MODE still wins
# over both, in rps_init, so existing launch scripts behave exactly as before.)
def _load_run_setting():
    env = os.environ.get("VIEWER_RUN_MODE")
    if env:
        return _settings.normalize_run_mode(env) if _settings else env.strip().lower()
    if _settings:
        try: return _settings.normalize_run_mode(_settings.get("run_mode", "auto"))
        except Exception: pass
    return "auto"
RPS_SETTING = _load_run_setting()
RPS_MODE = "modern"; RPS_REASON = "default"; RPS_FLAGS = {"sqlite": {}, "page_cache": False, "prefetch": 0}


def rps_init():
    """Pick the runtime mode (modern/lite/legacy) from the hardware probe + the user's choice. Read-only
    on the index; safe to fail (a probe glitch must never stop the server from starting)."""
    global RPS_MODE, RPS_REASON, RPS_FLAGS
    if not _rps: return
    prof = {}
    try:
        import sysprobe; prof = sysprobe.load_or_build()
    except Exception: prof = {}
    try:
        if RPS_OVERRIDE in _rps.VALID_MODES:                 # concrete env/CLI force (back-compat) wins
            RPS_MODE, RPS_REASON = _rps.mode_for(prof, RPS_OVERRIDE)
        else:                                                # otherwise honour the persisted Settings choice
            RPS_MODE, RPS_REASON = _rps.mode_for_setting(prof, RPS_SETTING)
        RPS_FLAGS = _rps.feature_flags(RPS_MODE)
    except Exception: pass


def set_run_mode(setting):
    """Persist a Settings-panel run-mode choice (auto|performance|retro) and RE-APPLY it live. Returns a
    status dict. Fail-loud: if the choice can't be saved, `saved` is False so the UI can warn the user.
    Note: UI effects, page-cache and render-DPI switch immediately; SQLite tuning applies to NEW
    connections, so it takes full effect on the next restart (existing pooled connections keep their
    pragmas)."""
    global RPS_SETTING
    norm = _settings.normalize_run_mode(setting) if _settings else str(setting or "auto").strip().lower()
    saved = False
    if _settings:
        try: saved = _settings.set("run_mode", norm)
        except Exception: saved = False
    RPS_SETTING = norm
    rps_init()                                               # recompute mode + flags from the new choice
    return {"saved": bool(saved), "setting": RPS_SETTING, "mode": RPS_MODE, "reason": RPS_REASON,
            "applies": "UI/render now; SQLite tuning on new connections (full effect after restart)"}


import threading as _threading                                    # noqa: E402
_tls = _threading.local()


class _ReuseConn(object):
    """Thin proxy so callers' con.close() is a harmless no-op — the real connection is kept per-thread and
    reused across requests (saves the connect + PRAGMA setup each time). Read-mostly, autocommit."""
    __slots__ = ("_c",)
    def __init__(self, real): self._c = real
    def execute(self, *a, **k): return self._c.execute(*a, **k)
    def executemany(self, *a, **k): return self._c.executemany(*a, **k)
    def cursor(self): return self._c.cursor()
    def commit(self): return self._c.commit()
    def rollback(self): return self._c.rollback()
    def close(self): pass
    def __enter__(self): return self._c.__enter__()
    def __exit__(self, *a): return self._c.__exit__(*a)
    @property
    def row_factory(self): return self._c.row_factory
    @row_factory.setter
    def row_factory(self, v): self._c.row_factory = v


def _new_conn():
    con = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False); con.row_factory = sqlite3.Row
    try:                                                  # RPS: tune the connection for the machine (HDD / low-RAM)
        sq = (RPS_FLAGS or {}).get("sqlite") or {}
        if "cache_kb" in sq:   con.execute("PRAGMA cache_size=%d" % int(sq["cache_kb"]))
        if "mmap" in sq:       con.execute("PRAGMA mmap_size=%d" % int(sq["mmap"]))
        if sq.get("temp_store"): con.execute("PRAGMA temp_store=%s" % sq["temp_store"])
    except Exception: pass
    return con


def db():
    """A per-thread reused SQLite connection (Tier-1 perf). Callers may .close() it harmlessly. In the
    special relaxed/OCR mode we never reuse (that path takes exclusive locks), returning a fresh conn."""
    if os.environ.get("VIEWER_RELAXED") == "1":
        con = sqlite3.connect(DB_PATH, timeout=30); con.row_factory = sqlite3.Row
        con.execute("PRAGMA locking_mode=EXCLUSIVE"); con.execute("PRAGMA journal_mode=TRUNCATE")
        return con
    c = getattr(_tls, "con", None)
    if c is not None:
        try: c.execute("SELECT 1")                        # liveness check; rebuild if the cached conn went bad
        except Exception:
            try: c.close()
            except Exception: pass
            c = None
    if c is None:
        try: c = _new_conn(); _tls.con = c
        except Exception:
            con = sqlite3.connect(DB_PATH, timeout=30); con.row_factory = sqlite3.Row; return con
    return _ReuseConn(c)


# fts5vocab ready-flag: owned HERE (not in search_feature) so the regression tests can keep
# doing `V._VOCAB_READY = False` to force a re-check, exactly as against the monolith.
_VOCAB_READY = False


def doc_path(doc_id):
    """v1.13 unified data access: resolve a document id -> filesystem path via the PER-THREAD POOLED
    connection (no fresh connect, no leaked handle). Returns the path str or None. This replaces the
    ~15 scattered `sqlite3.connect(mode=ro) ... close()-inside-try` idioms that both leaked on error
    and bypassed the pool. Read-only; never raises."""
    try:
        did = int(doc_id)
    except (TypeError, ValueError):
        return None
    try:
        r = db().execute("SELECT path FROM documents WHERE id=?", (did,)).fetchone()
        return (r["path"] if r else None)
    except Exception:
        return None


# ---- exposure posture (v1.13): loopback is the mechanics' normal path and is unaffected. When the
# server is deliberately bound to a non-loopback address, mutating requests must carry a shared token.
_EXPOSED = False
_AUTH_TOKEN = os.environ.get("VIEWER_AUTH_TOKEN") or ""


def _auth_ok(token):
    """Constant-time token check for network-exposed mode. Empty configured token = deny all mutation."""
    import hmac as _hmac
    if not _AUTH_TOKEN:
        return False
    return _hmac.compare_digest(str(token or ""), _AUTH_TOKEN)


# ---- rotating server-error log (B10/J69): tracebacks go here, never to the client --------------
LOG_DIR = os.path.join(HERE, "logs")
MAX_POST_BYTES = 8 * 1024 * 1024          # B13: parts-request payloads are a few KB; 8 MB is generous
_errlog = None


def _setup_error_log():
    global _errlog
    try:
        import logging
        from logging.handlers import RotatingFileHandler
        os.makedirs(LOG_DIR, exist_ok=True)
        lg = logging.getLogger("viewer.errors")
        lg.setLevel(logging.ERROR)
        if not lg.handlers:
            hd = RotatingFileHandler(os.path.join(LOG_DIR, "server-errors.log"),
                                     maxBytes=1024 * 1024, backupCount=3, encoding="utf-8")
            hd.setFormatter(logging.Formatter("%(asctime)s  %(message)s"))
            lg.addHandler(hd)
        _errlog = lg
    except Exception:
        _errlog = None


def log_exception(context):
    """Log the current exception (traceback included) and return a short reference id the
    client response can carry, so a log line is findable without leaking internals (J69)."""
    import traceback, hashlib
    ref = hashlib.md5(("%s|%s" % (context, time.time())).encode()).hexdigest()[:8]
    try:
        if _errlog is None: _setup_error_log()
        if _errlog is not None:
            _errlog.error("ref=%s  %s\n%s", ref, context, traceback.format_exc())
        else:
            sys.stderr.write("[error ref=%s] %s\n%s\n" % (ref, context, traceback.format_exc()))
    except Exception:
        pass
    return ref


def recent_errors(n=10):
    """Tail of the rotating error log (header lines only) for the /ops view (B10). Read-only."""
    p = os.path.join(LOG_DIR, "server-errors.log")
    if not os.path.exists(p): return []
    try:
        lines = open(p, "r", encoding="utf-8", errors="replace").read().splitlines()
        heads = [l for l in lines if "ref=" in l]
        return heads[-n:]
    except Exception:
        return []


# ---- the modularized feature packages (v0.96.0) + the established DI injections ----------------
import features.search_feature as _fsearch                        # noqa: E402
import features.parts_feature as _fparts                          # noqa: E402
import features.browse_feature as _fbrowse                        # noqa: E402
import features.procedures_feature as _fproc                      # noqa: E402
import features.render_feature as _frender                        # noqa: E402
import features.ingest_feature as _fingest                        # noqa: E402
import features.sessions_feature as _fsess                        # noqa: E402
import features.corpus as _fcorpus                                # noqa: E402  (v1.13 shared FTS retrieval)
import features.routes as _froutes                                # noqa: E402
from features import registry as _registry                        # noqa: E402

for _m in (_fsearch, _fparts, _fbrowse, _fproc, _frender, _fingest, _fsess, _fcorpus, _froutes):
    _m.core = sys.modules[__name__]

# Re-export every name the monolith exposed (tests, scripts, and the DI feature modules call
# these through `viewer_app` / `core`). Verbatim functions; behavior unchanged.
from features.search_feature import (                             # noqa: E402,F401
    normalize_nomenclature, _meta_rows, _load_synonyms, user_keywords_list, user_keywords_save,
    user_keywords_delete, _kw_user_path, _part_key, user_tags_for, user_tags_add, user_tags_remove,
    _ensure_vocab, _within1, fuzzy_terms, _alts, _vehicles, _has_suggest_terms, suggest,
    build_match, search, find_in_doc, did_you_mean)
from features.parts_feature import (                              # noqa: E402,F401
    _corr_path, correlations_for, VALID_NIIN_DECISIONS, _reviews_path, _reviews_con,
    record_niin_decision, _latest_decisions, nsn_aliases, niin_review, fault_parts,
    popular_items, popular_nsns, TECH_CODES, _ts_terms, tech_status_suggest,
    part_lookup, part_differences, reference_for)
from features.browse_feature import (                             # noqa: E402,F401
    doc_type, doc_meta, vehicle_hub, list_vehicles, by_side, threed_list, _nsn_fts_phrase,
    threed_refs, schematics_list, coverage, latest_snapshot_info, status_summary,
    ops_summary, file_audit)
from features.procedures_feature import (                         # noqa: E402,F401
    _proc_kind, _parse_procedure, procedure_for, _norm_unit, torque_specs)
from features.render_feature import (                             # noqa: E402,F401
    _clean_png, _poppler_png, _which, _get_doc, _clip_rect_for, render_page_png,
    cached_page_render, _warm_adjacent, page_words, _locate_box, _digits, page_callouts)
from features.ingest_feature import ingest_preview, ingest_start, ingest_status   # noqa: E402,F401
from features.sessions_feature import recent_sessions, save_request               # noqa: E402,F401

# ---- the earlier extractions (unchanged): DI exactly as before ----------------------------------
from collections_feature import (smart_collections_list, smart_collection_eval, smart_collection_save,
                                 smart_collection_pin, smart_collection_delete, _collections_defs)
import collections_feature as _cf; _cf.core = sys.modules[__name__]   # inject the running module (no import cycle)
from sides_feature import (by_side as _side_browse, save_override as _side_save,
                           uncertain as _side_uncertain, classify as _side_classify)
import sides_feature as _sf; _sf.core = sys.modules[__name__]
from chapters_feature import (chapters as _chapters, jump as _chapter_jump, save_override as _chapter_save,
                              review as _chapters_review)
import chapters_feature as _ch; _ch.core = sys.modules[__name__]
from figures_feature import (part_image as _part_image, get_crop as _fig_get_crop)
import figures_feature as _fig; _fig.core = sys.modules[__name__]
import image3d_experiment as _i3d; _i3d.core = sys.modules[__name__]
import localmodel as _lm; _lm.core = sys.modules[__name__]
from rpstl_feature import (lookup as _pn_lookup, review as _rpstl_review, save_override as _rpstl_save)
import rpstl_feature as _rp; _rp.core = sys.modules[__name__]
from figures_feature import callout_crop as _callout_crop
from xref_feature import (part_record as _part_record, coverage as _xref_coverage)
import xref_feature as _xr; _xr.core = sys.modules[__name__]
import xref_online as _xo; _xo.core = sys.modules[__name__]   # X4: opt-in cached online enrichment (off by default)
from material_feature import part_material as _part_material
import material_feature as _mf; _mf.core = sys.modules[__name__]


def _same_origin(origin, host):
    """J68: a browser-sent Origin on a POST must match our Host (scheme-independent, exact netloc)."""
    try:
        o = urllib.parse.urlparse(origin)
        return bool(host) and (o.netloc or "").lower() == host.lower()
    except Exception:
        return False


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"            # keep-alive: reuse the TCP connection across requests (RPS latency win)
    timeout = 60                              # B13: a stalled/dead client can't pin a thread forever
    def log_message(self, *a): pass

    def _send(self, code, body, ctype="application/json", extra=None):
        # B9 invariant (v1.13): mark the response as begun BEFORE any bytes go out. The error boundary
        # only emits its 500 when nothing has been sent, so a handler that sends-then-raises can never
        # double-send and desync the keep-alive stream. Structural, not by-convention.
        self._sent = True
        if isinstance(body, (dict, list)): body = json.dumps(body, separators=(",", ":")).encode("utf-8")  # compact JSON: fewer bytes
        elif isinstance(body, str): body = body.encode("utf-8")
        etag = None
        try:                                  # ETag / 304: don't re-send an unchanged body (perf)
            etag = (extra or {}).get("ETag")  # caller may supply a cheap param-based ETag (skips hashing a big PNG)
            if etag is None and code == 200 and len(body) >= 64:
                import hashlib as _hl
                etag = '"' + _hl.md5(body).hexdigest() + '"'
            if etag and (self.headers.get("If-None-Match") or "") == etag:
                self.send_response(304); self.send_header("ETag", etag)
                if extra and extra.get("Cache-Control"): self.send_header("Cache-Control", extra["Cache-Control"])
                self.send_header("Content-Length", "0"); self.end_headers(); return
        except Exception: etag = None
        enc = None
        try:                                  # gzip text-ish payloads when the client supports it (RPS bandwidth win)
            ae = self.headers.get("Accept-Encoding", "") or ""
            compressible = any(ctype.startswith(p) for p in ("application/json", "text/", "application/javascript", "image/svg"))
            if "gzip" in ae and compressible and len(body) >= 512:
                import gzip as _gz; body = _gz.compress(body, 6); enc = "gzip"
        except Exception: pass
        self.send_response(code); self.send_header("Content-Type", ctype)
        if etag: self.send_header("ETag", etag)
        if enc: self.send_header("Content-Encoding", enc); self.send_header("Vary", "Accept-Encoding")
        self.send_header("Content-Length", str(len(body)))
        if extra:
            for k, v in extra.items():
                if k == "ETag": continue            # already emitted above
                self.send_header(k, v)
        self.end_headers()
        try: self.wfile.write(body)
        except Exception: pass

    # ---- ONE error boundary (B9): registry dispatch; nothing below it can drop the socket ------
    def _dispatch(self, table, u, qs, payload=None):
        self._sent = False                                # reset per request (Handler is reused on keep-alive)
        fn = table.get(u.path)
        if fn is None:
            self._send(404, {"error": "not found"}); return
        self._route_path = u.path
        try:
            if payload is None: fn(self, qs)
            else: fn(self, qs, payload)
        except _registry.ParamError as e:                 # malformed client input -> 400 (B11)
            self._send(400, {"error": str(e)})
        except FileNotFoundError as e:                    # missing doc/page/crop -> 404
            self._send(404, {"error": str(e)})
        except sqlite3.OperationalError as e:             # B14: an OPTIONAL sidecar TABLE isn't built yet ->
            m = str(e)                                    # degrade gracefully (not a server bug) instead of 500.
            if "no such table" in m and not self._sent:   # (column drift / locked / corrupt stay 500 -- real issues)
                self._send(200, {"ok": False, "unavailable": True,
                                 "error": "this feature's data is not built yet",
                                 "detail": m})
            else:
                ref = log_exception("%s %s" % ("POST" if payload is not None else "GET", u.path))
                if not self._sent:                        # never double-send onto a keep-alive stream
                    try: self._send(500, {"error": "internal server error", "ref": ref})
                    except Exception: pass
        except Exception:                                 # anything else: log it, generic 500 (B10/J69)
            ref = log_exception("%s %s" % ("POST" if payload is not None else "GET", u.path))
            if not self._sent:
                try: self._send(500, {"error": "internal server error", "ref": ref})
                except Exception: pass

    def do_GET(self):
        u = urllib.parse.urlparse(self.path); qs = urllib.parse.parse_qs(u.query)
        self._dispatch(_registry.GET, u, qs)

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        self._sent = False
        # v1.13: we only speak Content-Length. A chunked body would leave unread bytes in rfile and
        # desync the next keep-alive request, so reject it loudly and close the connection.
        if (self.headers.get("Transfer-Encoding") or "").lower().find("chunked") >= 0:
            self.close_connection = True
            self._send(411, {"error": "chunked Transfer-Encoding not supported; send Content-Length"}); return
        origin = self.headers.get("Origin")
        if origin and origin != "null" and not _same_origin(origin, self.headers.get("Host") or ""):
            self.close_connection = True                                         # body unread -> keep-alive would desync
            self._send(403, {"error": "cross-origin POST rejected"}); return     # J68
        # v1.13: exposure posture -- when bound to a non-loopback address, mutating requests require the
        # shared token (constant-time compared). Loopback (the mechanics' normal path) is unaffected.
        if _EXPOSED and not _auth_ok(self.headers.get("X-Viewer-Token")):
            self.close_connection = True
            self._send(401, {"error": "authentication required on a network-exposed VIEWER (set X-Viewer-Token)"}); return
        try: length = int(self.headers.get("Content-Length", 0) or 0)
        except Exception: length = 0
        if length > MAX_POST_BYTES:
            self.close_connection = True                                         # refuse WITHOUT reading the body
            self._send(413, {"error": "request body too large"}); return        # B13
        raw = self.rfile.read(length) if length else b"{}"
        try: payload = json.loads(raw.decode("utf-8") or "{}")
        except Exception: payload = {}
        qs = urllib.parse.parse_qs(u.query)
        self._dispatch(_registry.POST, u, qs, payload)


class _BoundedThreadingHTTPServer(ThreadingHTTPServer):
    """v1.13 resource governor: ThreadingHTTPServer spawns one thread per connection with no ceiling, so
    an asset burst (a viewer page firing page/callouts/pagewords/cadimg at once, x a second bay tablet)
    could fan out into unbounded threads each rendering PDFs + allocating mmap on a 6 GB laptop. A bounded
    semaphore caps concurrent workers: excess connections queue (backpressure) instead of thrashing the
    machine. Size scales with cores; override with VIEWER_MAX_WORKERS."""
    daemon_threads = True
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        try:
            n = int(os.environ.get("VIEWER_MAX_WORKERS") or 0)
        except Exception:
            n = 0
        if n <= 0:
            try: n = max(8, min(64, (os.cpu_count() or 4) * 4))
            except Exception: n = 16
        self._worker_sem = _threading.BoundedSemaphore(n)
        self.max_workers = n

    def process_request(self, request, client_address):
        self._worker_sem.acquire()                     # blocks the accept loop when saturated (backpressure)
        super().process_request(request, client_address)

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            try: self._worker_sem.release()
            except Exception: pass


def _auto_optimize():
    """v1.13: make the FAST, WAL-concurrent index state the shipped DEFAULT instead of depending on
    someone remembering to run optimize_index.py. Two parts, both OCR-safe and idempotent:
      * WAL journal mode is set SYNCHRONOUSLY at boot (a cheap, reversible PRAGMA) so server reads never
        block the live OCR writer.
      * missing indexes are built in a BACKGROUND daemon thread with a long busy_timeout, so boot is never
        stalled and the build politely waits (then gives up) if OCR is actively writing.
    Opt out with VIEWER_NO_AUTO_OPTIMIZE=1. Best-effort throughout; never raises into the caller."""
    if os.environ.get("VIEWER_NO_AUTO_OPTIMIZE") == "1":
        return
    try:                                              # WAL now (fast, reversible, biggest concurrency win)
        c = sqlite3.connect(DB_PATH, timeout=5)
        try:
            mode = c.execute("PRAGMA journal_mode=WAL").fetchone()
            if mode: print("[optimize] journal_mode=%s (concurrent reads during OCR writes)" % mode[0])
        finally:
            c.close()
    except Exception:
        pass

    def _bg():
        try:
            idx = [("ix_pages_document", "CREATE INDEX IF NOT EXISTS ix_pages_document ON pages(document_id)"),
                   ("ix_parts_name", "CREATE INDEX IF NOT EXISTS ix_parts_name ON parts(name COLLATE NOCASE)"),
                   ("ix_parts_nomenclature",
                    "CREATE INDEX IF NOT EXISTS ix_parts_nomenclature ON parts(nomenclature COLLATE NOCASE)")]
            c = sqlite3.connect(DB_PATH, timeout=130)
            try:
                c.execute("PRAGMA busy_timeout=120000")
                have = set(r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='index'"))
                built = 0
                for name, sql in idx:
                    if name in have:
                        continue
                    try:
                        c.execute(sql); c.commit(); built += 1
                    except Exception:
                        pass                          # OCR busy / table absent -> the manual optimizer can finish it
                if built:
                    try: c.execute("ANALYZE"); c.commit()
                    except Exception: pass
                    print("[optimize] built %d missing index(es) in the background" % built)
            finally:
                c.close()
        except Exception:
            pass
    t = _threading.Thread(target=_bg, name="viewer-optimize", daemon=True)
    t.start()


def main():
    global DB_PATH, INDEX_DIR
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.environ.get("VIEWER_DB", DB_PATH))
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1",
                    help="default 127.0.0.1 (local only, B15); set 0.0.0.0 to expose on the LAN deliberately")
    ap.add_argument("--mode", default=None, help="force RPS mode: modern | lite | legacy")
    ap.add_argument("--prebake", type=int, default=0, metavar="N", help="pre-render the first N pages of every doc into the cache, then exit")
    args = ap.parse_args(); DB_PATH = os.path.abspath(args.db); INDEX_DIR = os.path.abspath(os.path.dirname(DB_PATH))
    if not os.path.exists(DB_PATH): print(f"[WARN] index not found at {DB_PATH}")
    global RPS_OVERRIDE
    if args.mode: RPS_OVERRIDE = args.mode
    rps_init()
    _setup_error_log()
    print(f"[RPS] mode={RPS_MODE} ({RPS_REASON})")
    try:                                       # cold-start warmup: prime the connection, mmap & planner so the first query is fast
        wc = db()
        wc.execute("SELECT 1").fetchone()
        try: wc.execute("SELECT COUNT(*) FROM documents").fetchone()
        except Exception: pass
        try: wc.execute("SELECT id FROM pages LIMIT 1").fetchone()
        except Exception: pass
        wc.close(); print("[warmup] index primed")
    except Exception: pass
    _auto_optimize()                          # v1.13: WAL now + background index build (OCR-safe, idempotent)
    if args.prebake > 0:
        if not _rps: print("[prebake] rps module unavailable"); return
        con = db(); docs = [(r["id"], r["page_count"]) for r in con.execute("SELECT id, page_count FROM documents")]; con.close()
        dpi = (RPS_FLAGS or {}).get("default_dpi", 120)
        print(f"[prebake] rendering up to {args.prebake} page(s) of {len(docs)} docs at {dpi} dpi...")
        made = _rps.prebake(INDEX_DIR, lambda d, p, dp, cl: render_page_png(d, p, dp, None, clean=cl), docs, dpi=dpi, pages_per_doc=args.prebake, log=print)
        print(f"[prebake] done — {made} new pages cached. {_rps.cache_stats(INDEX_DIR)}")
        return
    global _EXPOSED
    _EXPOSED = args.host not in ("127.0.0.1", "localhost", "::1")
    if _EXPOSED:
        print("=" * 72)
        print("[EXPOSURE] Binding to a NON-LOOPBACK address (%s) -- the VIEWER is reachable on the network." % args.host)
        if _AUTH_TOKEN:
            print("[EXPOSURE] Mutating requests require the X-Viewer-Token header (VIEWER_AUTH_TOKEN is set).")
        else:
            print("[EXPOSURE] VIEWER_AUTH_TOKEN is NOT set -- ALL mutating POSTs will be REJECTED (401).")
            print("[EXPOSURE] Set VIEWER_AUTH_TOKEN to allow authenticated writes over the network.")
        print("=" * 72)
    srv = _BoundedThreadingHTTPServer((args.host, args.port), Handler)
    print(f"THE VIEWER v{VERSION} running at http://{args.host}:{args.port}  (index: {DB_PATH})"); print("Press Ctrl+C to stop.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down…")
    finally:                                   # B16: graceful shutdown — close sockets, checkpoint the WAL
        try: srv.server_close()
        except Exception: pass
        try:
            c = sqlite3.connect(DB_PATH, timeout=5)
            c.execute("PRAGMA wal_checkpoint(TRUNCATE)"); c.close()
            print("[shutdown] WAL checkpointed; sockets closed. stopped.")
        except Exception:
            print("stopped.")


if __name__ == "__main__": main()
# v0.97.0 — search quality (exact boost · did-you-mean · phrase/NEAR · LRU) + UI dedup + header-wrap layout fix (see docs/CHANGELOG.md)
