#!/usr/bin/env python3
"""THE VIEWER -- "side of the house" engine: cache + manual overrides + cover/MAC corroboration.

Builds on patterns.tm_side() (the deterministic Army-TM-coverage classifier). Adds three tightenings that
keep speed constant and stay RPS-safe (stdlib only; never writes the index -- R1/R6):

  1. CACHE       -- classify every document ONCE, keyed on a cheap signature (doc count + max rowid). The
                    map is reused until documents change, so /api/by_side + counts are O(1) after the first
                    build instead of re-scanning on every call.
  2. OVERRIDES   -- sides_override.json sidecar: pin any document to operator|mechanic|both by hand. Append-
                    only (keeps a log). Overrides always win, so the 'uncertain' tail is fixed without guessing.
  3. CORROBORATE -- for LOW-confidence docs only (no TM coverage code), peek at the already-OCR'd first page:
                    "OPERATOR'S MANUAL" on the cover -> operator; "MAINTENANCE ALLOCATION CHART" / "UNIT
                    MAINTENANCE" -> mechanic. Runs only on the few unknowns, so there is no global speed cost.

`core` (the running viewer_app module) is injected by viewer_app -- no import cycle.
"""
import os, re, json, time, sqlite3, threading

core = None   # injected: import sides_feature as _sf; _sf.core = sys.modules[__name__]

_CACHE = {"sig": None, "map": {}, "counts": {}}
_OVR_CACHE = {"mtime": None, "data": {}}
_CACHE_LOCK = threading.Lock()   # ThreadingHTTPServer can call side_map() concurrently -- see side_map()

_COVER_OP = re.compile(r"OPERATOR'?S?\s+MANUAL|OPERATOR'?S?\s+INSTRUCTIONS", re.I)
_COVER_MECH = re.compile(r"MAINTENANCE\s+ALLOCATION\s+CHART|\bUNIT\s+MAINTENANCE\b|\bFIELD\s+MAINTENANCE\b|"
                         r"\bDIRECT\s+SUPPORT\b|\bGENERAL\s+SUPPORT\b|REPAIR\s+PARTS\s+AND\s+SPECIAL", re.I)


def _override_path():
    return os.path.join(os.path.dirname(core.DB_PATH), "sides_override.json")


def load_overrides():
    """{doc_id(int): 'operator'|'mechanic'|'both'} from the sidecar (cached on mtime)."""
    p = _override_path()
    try:
        mt = os.path.getmtime(p)
    except OSError:
        _OVR_CACHE["mtime"] = None; _OVR_CACHE["data"] = {}; return {}
    if _OVR_CACHE["mtime"] == mt:
        return _OVR_CACHE["data"]
    data = {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for k, v in (raw.get("overrides") or {}).items():
            side = (v.get("side") if isinstance(v, dict) else v) or ""
            if side in ("operator", "mechanic", "both"):
                data[int(k)] = side
    except Exception:
        data = {}
    _OVR_CACHE["mtime"] = mt; _OVR_CACHE["data"] = data
    return data


def save_override(doc_id, side, by=""):
    """Pin a document to a side. Append-only: merges into overrides + appends a log entry (audit trail)."""
    if side not in ("operator", "mechanic", "both"):
        return {"ok": False, "error": "side must be operator|mechanic|both"}
    # doc_id arrives straight from the POST JSON payload (p_side_override), unlike GET routes' integer
    # params which are funneled through registry.qint() -- guard the conversion here the same way, so a
    # missing/malformed doc_id (e.g. omitted entirely) returns a clean ok:False/400 instead of an
    # unhandled ValueError/TypeError that the dispatch boundary turns into a generic 500.
    try:
        doc_id = int(doc_id)
    except (TypeError, ValueError):
        return {"ok": False, "error": "doc_id must be an integer"}
    p = _override_path()
    blob = {"overrides": {}, "log": []}
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f: blob = json.load(f)
        except Exception:
            blob = {"overrides": {}, "log": []}
    blob.setdefault("overrides", {}); blob.setdefault("log", [])
    key = str(doc_id)
    prev = blob["overrides"].get(key)
    blob["overrides"][key] = {"side": side, "by": by or "", "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    # v1.13.4: only log a REAL change (new doc_id, or the side actually flipped) -- previously every call
    # appended unconditionally, so a repeat click/retry of the SAME pin (nothing changed) still grew the
    # log forever with no new information, the same unbounded-write-only-bloat class as the keywords bug
    # fixed earlier today. "log" is read back nowhere in the codebase (grepped) -- it exists purely as an
    # audit trail, so only recording actual changes keeps that promise meaningful instead of just noisy.
    if prev is None or prev.get("side") != side:
        blob["log"].append({"doc_id": doc_id, "side": side, "by": by or "", "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
    import safeguard          # v1.13: fsync + _replace_retry (absorbs the transient Windows WinError5 lock)
    safeguard.atomic_write(p, json.dumps(blob, indent=2))
    _OVR_CACHE["mtime"] = None                      # force reload
    _CACHE["sig"] = None                            # force side-map rebuild (override changes the map)
    return {"ok": True, "doc_id": doc_id, "side": side}


def _docs_sig(con):
    row = con.execute("SELECT COUNT(*), COALESCE(MAX(id),0) FROM documents WHERE type LIKE 'pdf%'").fetchone()
    ovp = _override_path()
    try: omt = os.path.getmtime(ovp)
    except OSError: omt = 0
    return (row[0], row[1], omt)


def _corroborate(con, doc_id):
    """LOW-confidence only: read the first OCR'd page(s) and look for cover/MAC tells. Returns
    (operator, mechanic) booleans discovered, or (False, False) if nothing found."""
    try:
        rows = con.execute("SELECT body_text FROM pages WHERE document_id=? AND page_number<=2 "
                           "ORDER BY page_number LIMIT 2", (doc_id,)).fetchall()
    except Exception:
        return False, False
    txt = " ".join((r[0] or "") for r in rows)[:4000]
    if not txt:
        return False, False
    return bool(_COVER_OP.search(txt)), bool(_COVER_MECH.search(txt))


def _build_map(con):
    overrides = load_overrides()
    rows = con.execute("SELECT id, vehicle, tm_number, title, nsn, page_count, path FROM documents "
                       "WHERE type LIKE 'pdf%' ORDER BY COALESCE(vehicle,''), COALESCE(tm_number,''), id").fetchall()
    m = {}; n_op = n_mech = n_both = n_unc = 0
    for r in rows:
        cls = core.tm_side(r["tm_number"] or "", r["title"] or "", r["path"] or "")
        operator, mechanic = cls["operator"], cls["mechanic"]
        conf, basis = cls["confidence"], cls["basis"]
        if conf == "low":                            # corroborate the unknowns from OCR'd page 1 (cheap, rare)
            co, cm = _corroborate(con, r["id"])
            if co or cm:
                operator = operator or co; mechanic = mechanic or cm
                if not (co and cm): mechanic = cm or (mechanic and not co)
                operator = co or operator
                conf = "medium"; basis = basis + "; corroborated (cover/MAC)"
        ov = overrides.get(r["id"])
        if ov:                                       # manual pin wins
            operator = ov in ("operator", "both")
            mechanic = ov in ("mechanic", "both")
            conf = "override"; basis = "manual override -> %s" % ov
        m[r["id"]] = {"doc_id": r["id"], "vehicle": r["vehicle"], "tm": r["tm_number"], "title": r["title"],
                      "nsn": r["nsn"], "pages": r["page_count"], "filename": os.path.basename(r["path"] or ""),
                      "coverage": cls["coverage"], "operator": operator, "mechanic": mechanic,
                      "confidence": conf, "basis": basis}
        if operator: n_op += 1
        if mechanic: n_mech += 1
        if operator and mechanic: n_both += 1
        if conf == "low": n_unc += 1
    counts = {"operator": n_op, "mechanic": n_mech, "both": n_both, "uncertain": n_unc, "documents": len(rows)}
    return m, counts


def side_map(con):
    """Cached {doc_id: classification}. Rebuilds only when documents OR overrides change.

    Locked (v1.13): ThreadingHTTPServer can call this concurrently, and the rebuild is 3 separate dict
    writes (map, counts, sig) -- without a lock, one thread's exception-path reset can land between
    another thread's successful map/counts write and its sig write, pairing a *valid* sig with an
    *empty* map. Once sig matches, every later call skips rebuilding, so that corrupted pairing would
    stick forever. Compute the rebuild into locals first and only touch _CACHE once we're done, so a
    failed rebuild never has a chance to observe (or clobber) another thread's in-progress one."""
    with _CACHE_LOCK:
        try:
            sig = _docs_sig(con)
            if _CACHE["sig"] != sig:
                m, counts = _build_map(con)
                _CACHE["map"], _CACHE["counts"], _CACHE["sig"] = m, counts, sig
        except sqlite3.OperationalError:
            # documents is missing a column this classifier depends on (older/partial schema, or a
            # migration mid-flight) -- degrade to "nothing classified" instead of 500ing every
            # /api/by_side & /api/side_uncertain call. Logged (unlike a silent swallow) so a PERSISTENT
            # failure after a prior successful build -- where we keep serving the last known-good map,
            # deliberately, rather than blanking it -- is still visible to whoever watches the error log.
            try: core.log_exception("side_map")
            except Exception: pass
            if _CACHE["sig"] is None:
                _CACHE["map"], _CACHE["counts"] = {}, {"operator": 0, "mechanic": 0, "both": 0,
                                                        "uncertain": 0, "documents": 0}
        return _CACHE["map"], _CACHE["counts"]


def classify(doc_id, tm_number="", title="", path=""):
    """Single-doc classification honoring overrides (no full map needed) -- used by side-filtered search."""
    ov = load_overrides().get(int(doc_id) if str(doc_id).isdigit() else -1)
    if ov:
        return {"operator": ov in ("operator", "both"), "mechanic": ov in ("mechanic", "both"),
                "confidence": "override"}
    return core.tm_side(tm_number or "", title or "", path or "")


def by_side(side=None, q="", limit=400, offset=0):
    """Documents on a side (operator|mechanic) + counts, from the cached map. Read-only (R1/R6)."""
    con = core.db()
    try:
        m, counts = side_map(con)
    finally:
        try: con.close()
        except Exception: pass
    q = (q or "").strip().upper()
    items = []
    for rec in m.values():
        if side in ("operator", "mechanic") and not rec[side]:
            continue
        if q and q not in ((rec["vehicle"] or "") + " " + (rec["tm"] or "") + " " + (rec["title"] or "")).upper():
            continue
        items.append(rec)
    items.sort(key=lambda r: ((r["vehicle"] or ""), (r["tm"] or ""), r["doc_id"]))
    total = len(items)
    off = max(0, int(offset)); lim = max(1, min(int(limit), 1000))
    return {"side": side, "counts": counts, "total": total, "offset": off, "items": items[off:off + lim]}


def uncertain(limit=200):
    """The low-confidence docs for review (the override UI lists these)."""
    con = core.db()
    try:
        m, _ = side_map(con)
    finally:
        try: con.close()
        except Exception: pass
    out = [r for r in m.values() if r["confidence"] in ("low", "medium")]
    out.sort(key=lambda r: (r["confidence"] != "low", (r["tm"] or "")))
    return {"total": len(out), "items": out[:max(1, min(int(limit), 1000))]}
