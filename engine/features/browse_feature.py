#!/usr/bin/env python3
"""THE VIEWER -- browse & overview (extracted verbatim from viewer_app, v0.96.0 modularization).

Vehicle hub, document grouping, side-of-the-house listing, 3D library + its OCR hookup,
schematics list, OCR coverage meter, and the status/ops summaries. DI via `core`."""
import json
import os
import re
import sqlite3
import time

from patterns import norm_nsn, NSN_RE

core = None          # injected by viewer_app at startup


def doc_type(tm, fname):
    t = ((tm or "") + " " + (fname or "")).upper()
    if "MWO" in t: return "MWO / modifications"
    if "TROUBLESHOOT" in t: return "Troubleshooting"
    if re.search(r"24P|20P|13&P|RPSTL|\bPARTS\b|\b-P\b", t): return "Parts (RPSTL)"
    if re.search(r"\bLO\b|LUBRICAT", t): return "Lubrication"
    if "SCHEMATIC" in t or "WIRING" in t: return "Schematics / wiring"
    if re.search(r"-10\b|OPERATOR", t): return "Operator (-10)"
    if re.search(r"-20|-23|-24|-34|-40|MAINT", t): return "Maintenance (-20/-24)"
    return "Other"


def doc_meta(doc_id):
    con = core.db(); r = con.execute("SELECT id, path, vehicle, tm_number, nsn, title, page_count, type FROM documents WHERE id=?", (doc_id,)).fetchone(); con.close()
    if not r: return None
    d = dict(r); d["filename"] = os.path.basename(d["path"] or ""); return d


def vehicle_hub(key):
    con = core.db(); nsn = norm_nsn(key)
    if nsn:
        vehicles = [r["vehicle"] for r in con.execute("SELECT DISTINCT vehicle FROM documents WHERE nsn=? AND vehicle IS NOT NULL", (nsn,)).fetchall()]
    else:
        vehicles = [key]
    vehicles = [v for v in vehicles if v]
    if not vehicles: con.close(); return None
    groups = {}
    qmarks = ",".join("?" * len(vehicles))
    for r in con.execute(
        "SELECT id, path, tm_number, nsn, title, page_count, type FROM documents "
        "WHERE vehicle IN (" + qmarks + ") AND type LIKE 'pdf%' ORDER BY tm_number", vehicles).fetchall():
        d = dict(r); d["filename"] = os.path.basename(d["path"] or "")
        g = doc_type(d["tm_number"], d["filename"])
        groups.setdefault(g, []).append({"doc_id": d["id"], "filename": d["filename"], "tm_number": d["tm_number"],
                                         "nsn": d["nsn"], "page_count": d["page_count"]})
    con.close()
    order = ["Operator (-10)","Maintenance (-20/-24)","Troubleshooting","Parts (RPSTL)","Schematics / wiring","Lubrication","MWO / modifications","Other"]
    ordered = [(g, groups[g]) for g in order if g in groups]
    return {"vehicles": vehicles, "nsn": nsn, "groups": ordered,
            "total": sum(len(v) for v in groups.values())}


def list_vehicles(limit=400):
    """Browse-by-vehicle: every vehicle in the index with its PDF doc count + a representative end-item NSN."""
    con = core.db()
    rows = con.execute(
        "SELECT vehicle, COUNT(*) AS docs, "
        "       MAX(CASE WHEN nsn IS NOT NULL THEN nsn END) AS nsn "
        "FROM documents WHERE vehicle IS NOT NULL AND vehicle<>'' AND type LIKE 'pdf%' "
        "GROUP BY vehicle ORDER BY docs DESC, vehicle LIMIT ?", (limit,)).fetchall()
    con.close()
    return [{"vehicle": r["vehicle"], "docs": r["docs"], "nsn": r["nsn"]} for r in rows]


def by_side(side=None, q="", limit=400, offset=0):
    """Divide the repository by 'side of the house': operator (10-level) vs mechanic (20-level), classified
    LIVE per document via tm_side() (Army TM coverage indicator). Read-only -- nothing is written to the
    index, so it respects R1/R6 and reflects new docs the moment they're added. Combined manuals (-12/-13/
    -14) appear on BOTH sides by design. Returns counts + the (optionally filtered) document list for `side`."""
    con = core.db(); q = (q or "").strip()
    where = "type LIKE 'pdf%'"; args = []
    if q:
        where += (" AND (upper(COALESCE(vehicle,'')) LIKE ? OR upper(COALESCE(title,'')) LIKE ? OR "
                  "upper(COALESCE(tm_number,'')) LIKE ?)")
        lu = "%" + q.upper() + "%"; args += [lu, lu, lu]
    rows = con.execute(
        "SELECT id, vehicle, tm_number, title, nsn, page_count, path FROM documents WHERE " + where +
        " ORDER BY COALESCE(vehicle,''), COALESCE(tm_number,''), id", args).fetchall()
    con.close()
    n_op = n_mech = n_both = 0; items = []
    for r in rows:
        cls = core.tm_side(r["tm_number"] or "", r["title"] or "", r["path"] or "")
        if cls["operator"] and cls["mechanic"]: n_both += 1
        if cls["operator"]: n_op += 1
        if cls["mechanic"]: n_mech += 1
        if side in ("operator", "mechanic") and not cls[side]:
            continue
        items.append({"doc_id": r["id"], "vehicle": r["vehicle"], "tm": r["tm_number"], "title": r["title"],
                      "nsn": r["nsn"], "pages": r["page_count"], "filename": os.path.basename(r["path"] or ""),
                      "coverage": cls["coverage"], "operator": cls["operator"], "mechanic": cls["mechanic"],
                      "basis": cls["basis"]})
    total = len(items)
    items = items[max(0, int(offset)):max(0, int(offset)) + max(1, min(int(limit), 1000))]
    return {"side": side, "counts": {"operator": n_op, "mechanic": n_mech, "both": n_both, "documents": len(rows)},
            "total": total, "offset": offset, "items": items}


_THREED_WHERE = ("characteristics IS NOT NULL AND characteristics<>'' AND ("
                 "upper(characteristics) LIKE '%DIAMETER%' OR upper(characteristics) LIKE '%LENGTH%' OR "
                 "upper(characteristics) LIKE '%HEIGHT%' OR upper(characteristics) LIKE '%WIDTH%' OR "
                 "upper(characteristics) LIKE '%THICKNESS%')")


def threed_list(q="", limit=60, offset=0, figures_only=True):
    """The 3D library. By DEFAULT it front-loads parts that have a REAL cited figure (a confirmed image),
    sourced from the parts index -- so the page leads with working, wired examples (every card has a picture).
    `figures_only=False` (route ?all=1) falls back to the full FLIS-dimension set (representative shapes only)."""
    con = core.db()
    qq = (q or "").strip()
    lim = max(1, min(int(limit), 200)); off = max(0, int(offset))
    if figures_only:
        args = []
        wf = "p.fig_no IS NOT NULL AND COALESCE(TRIM(p.nsn),'')<>''"
        if qq:
            wf += (" AND (p.nsn LIKE ? OR upper(COALESCE(p.fig_title,'')) LIKE ? OR "
                   "upper(COALESCE(r.item_name,'')) LIKE ?)")
            args += ["%" + qq + "%", "%" + qq.upper() + "%", "%" + qq.upper() + "%"]
        try:
            total = con.execute("SELECT COUNT(DISTINCT p.nsn) FROM parts p LEFT JOIN ref_nsn r ON r.nsn=p.nsn "
                               "WHERE " + wf, args).fetchone()[0]
            rows = con.execute(
                "SELECT p.nsn AS nsn, MAX(COALESCE(NULLIF(r.item_name,''), p.fig_title)) AS item_name, "
                "MAX(r.part_no) AS part_no, MAX(r.cagec) AS cagec, MAX(r.characteristics) AS characteristics, "
                "MAX(p.fig_no) AS fig_no, MAX(p.document_id) AS _doc, MAX(p.page) AS _page "
                "FROM parts p LEFT JOIN ref_nsn r ON r.nsn=p.nsn WHERE " + wf +
                " GROUP BY p.nsn ORDER BY item_name LIMIT ? OFFSET ?", args + [lim, off]).fetchall()
        except sqlite3.OperationalError as e:
            con.close(); return {"total": 0, "items": [], "error": str(e), "mode": "figures"}
        con.close()
        items = []
        for r in rows:
            d = dict(r); doc = d.pop("_doc", None); pg = d.pop("_page", None)
            if doc and pg: d["image_url"] = "/figcrop?doc=%s&page=%s&dpi=150" % (doc, pg)
            items.append(d)
        return {"total": total, "offset": off, "items": items, "mode": "figures"}
    # --- full FLIS-dimension set (representative shapes; many won't have a figure) ---
    args = []; where = _THREED_WHERE
    if qq:
        where += " AND (nsn LIKE ? OR upper(COALESCE(item_name,'')) LIKE ? OR upper(COALESCE(part_no,'')) LIKE ?)"
        args += ["%" + qq + "%", "%" + qq.upper() + "%", "%" + qq.upper() + "%"]
    try:
        total = con.execute("SELECT COUNT(*) FROM ref_nsn WHERE " + where, args).fetchone()[0]
        rows = con.execute("SELECT nsn,item_name,part_no,cagec,characteristics,data_date FROM ref_nsn WHERE "
                           + where + " ORDER BY COALESCE(NULLIF(item_name,''),nsn) LIMIT ? OFFSET ?",
                           args + [lim, off]).fetchall()
        items = [dict(r) for r in rows]
    except sqlite3.OperationalError as e:
        return {"total": 0, "items": [], "error": str(e)}
    con.close()
    for it in items:
        try:
            pi = core._part_image(it.get("nsn") or "")
            if pi.get("found"):
                it["image_url"] = pi.get("url"); it["fig_no"] = pi.get("fig_no")
                if not (it.get("item_name") or "").strip() and (pi.get("fig_title") or "").strip():
                    it["item_name"] = pi["fig_title"]
        except Exception:
            pass
    return {"total": total, "offset": off, "items": items, "mode": "all"}


def _nsn_fts_phrase(nsn):
    """Turn an NSN into an FTS5 phrase of its number groups ("2540 01 123 4567") so it matches the dashed
    form in the text regardless of how the tokenizer split the hyphens."""
    m = NSN_RE.search(nsn or "")
    return ('"%s %s %s %s"' % (m.group(1), m.group(2), m.group(3), m.group(4))) if m else None


def threed_refs(nsn, part_no="", limit=40):
    """OCR hookup for the 3D library: where a representative part shows up IN THE MANUALS (read-only over
    the text layer), plus which Smart Collections it falls into. Connects a 3D shape to the real TM pages."""
    con = core.db()
    phrase = _nsn_fts_phrase(nsn)
    terms = []
    if phrase: terms.append(phrase)
    pn = re.sub(r'"', " ", (part_no or "").strip())
    if pn and len(pn) >= 4: terms.append('"%s"' % pn)
    if not terms:
        try: con.close()                   # audit fix v0.72.3: early-return was leaking the connection
        except Exception: pass
        return {"nsn": nsn, "pages": [], "collections": [], "count": 0}
    match = " OR ".join(terms)
    pages = []
    try:
        rows = con.execute(
            "SELECT d.id AS doc_id, d.vehicle, d.tm_number, p.page_number, "
            "snippet(pages_fts,0,'<<','>>','...',10) AS snip, p.source "
            "FROM pages_fts JOIN pages p ON p.id=pages_fts.rowid JOIN documents d ON d.id=p.document_id "
            "WHERE pages_fts MATCH ? ORDER BY rank LIMIT ?",
            (match, max(1, min(int(limit), 100)))).fetchall()
        pages = [dict(r) for r in rows]
    except sqlite3.OperationalError:
        pages = []
    cols = []                                      # collection membership: a page matching BOTH this part AND the collection's query
    if phrase:
        for d in core._collections_defs().values():
            try:
                if con.execute("SELECT 1 FROM pages_fts WHERE pages_fts MATCH ? LIMIT 1",
                               ("(%s) AND %s" % (d["query"], phrase),)).fetchone():
                    cols.append({"slug": d["slug"], "name": d["name"]})
            except sqlite3.OperationalError:
                continue
    try: con.close()                       # audit fix v0.72.3: close before returning (was leaking)
    except Exception: pass
    return {"nsn": nsn, "match": match, "count": len(pages), "pages": pages, "collections": cols}


_SCHEM_WHERE = ("type LIKE 'pdf%' AND (upper(COALESCE(path,'')) LIKE '%SCHEMATIC%' OR "
                "upper(COALESCE(path,'')) LIKE '%WIRING%' OR upper(COALESCE(tm_number,'')) LIKE '%SCHEM%' OR "
                "upper(COALESCE(title,'')) LIKE '%SCHEMATIC%' OR upper(COALESCE(title,'')) LIKE '%WIRING%')")


def schematics_list(q="", limit=60, offset=0):
    """The schematics collection: documents classified as schematic / wiring diagrams. Searchable +
    paginated; each opens in a page viewer. (Exploded-view RPSTL figures live in the vehicle hub.)"""
    con = core.db(); args = []
    where = _SCHEM_WHERE
    q = (q or "").strip()
    if q:
        where += (" AND (upper(COALESCE(vehicle,'')) LIKE ? OR upper(COALESCE(title,'')) LIKE ? OR "
                  "upper(COALESCE(tm_number,'')) LIKE ? OR COALESCE(nsn,'') LIKE ? OR upper(COALESCE(path,'')) LIKE ?)")
        lu = "%" + q.upper() + "%"; args += [lu, lu, lu, "%" + q + "%", lu]
    try:
        total = con.execute("SELECT COUNT(*) FROM documents WHERE " + where, args).fetchone()[0]
        rows = con.execute("SELECT id,vehicle,tm_number,title,nsn,page_count,path FROM documents WHERE "
                           + where + " ORDER BY COALESCE(vehicle,''), COALESCE(tm_number,''), id LIMIT ? OFFSET ?",
                           args + [max(1, min(int(limit), 200)), max(0, int(offset))]).fetchall()
        items = [{"doc_id": r["id"], "vehicle": r["vehicle"], "tm": r["tm_number"], "title": r["title"],
                  "nsn": r["nsn"], "pages": r["page_count"], "filename": os.path.basename(r["path"] or "")} for r in rows]
    except sqlite3.OperationalError as e:
        return {"total": 0, "items": [], "error": str(e)}
    con.close()
    return {"total": total, "offset": offset, "items": items}


_COVERAGE_CACHE = {"ts": 0.0, "data": None}   # the all-vehicles aggregate is a full-corpus scan; memoize it
_COVERAGE_TTL = 600                            # seconds; coverage only drifts as OCR adds searchable pages


def coverage(vehicle=None):
    """Per-vehicle share of pages that are searchable (text or OCR'd) -- the OCR coverage meter.
    The all-vehicles form scans every page (heavy on a big corpus), so it is memoized for _COVERAGE_TTL.
    A single-vehicle query filters hard and stays uncached."""
    if not vehicle and _COVERAGE_CACHE["data"] is not None and (time.time() - _COVERAGE_CACHE["ts"]) < _COVERAGE_TTL:
        return _COVERAGE_CACHE["data"]
    con = core.db()
    try:
        rows = con.execute(
            "SELECT d.vehicle, COUNT(*) total, SUM(CASE WHEN p.source IN('text','ocr') THEN 1 ELSE 0 END) searchable "
            "FROM pages p JOIN documents d ON d.id=p.document_id WHERE d.vehicle IS NOT NULL AND d.vehicle<>'' "
            + ("AND d.vehicle=? " if vehicle else "") + "GROUP BY d.vehicle",
            (vehicle,) if vehicle else ()).fetchall()
    except sqlite3.OperationalError:
        rows = []
    con.close()
    out = {}
    for r in rows:
        tot = r["total"] or 0; s = r["searchable"] or 0
        out[r["vehicle"]] = {"total": tot, "searchable": s, "pct": round(100 * s / tot) if tot else 0}
    if not vehicle:
        _COVERAGE_CACHE["data"] = out; _COVERAGE_CACHE["ts"] = time.time()
    return out


def latest_snapshot_info():
    """Most recent safeguard snapshot (read-only, no hashing) for the System Status page."""
    vault = os.path.join(os.path.dirname(core.DB_PATH), "..", "backups", "vault")
    vault = os.path.abspath(vault)
    if not os.path.isdir(vault): return None
    snaps = sorted(d for d in os.listdir(vault) if d.startswith("SNAP_"))
    if not snaps: return None
    last = snaps[-1]
    info = {"snapid": last, "count_total": len(snaps)}
    try:
        man = json.load(open(os.path.join(vault, last, "manifest.json"), encoding="utf-8"))
        info["created"] = man.get("created"); info["files"] = man.get("count")
        info["db"] = (man.get("db") or {}).get("integrity")
    except Exception: pass
    return info


def status_summary():
    """Fast one-glance health for the System Status page. Uses indexed columns only
    (ocr_status, autoindexes) so it stays quick even on the multi-GB index."""
    con = core.db()
    def one(q, *a):
        try: return con.execute(q, a).fetchone()[0]
        except Exception: return None
    docs = one("SELECT COUNT(*) FROM documents")
    pages = one("SELECT COUNT(*) FROM pages")
    pend = one("SELECT COUNT(*) FROM pages WHERE ocr_status='pending'") or 0
    run = one("SELECT COUNT(*) FROM pages WHERE ocr_status='running'") or 0
    done = one("SELECT COUNT(*) FROM pages WHERE ocr_status='done'") or 0
    skip = one("SELECT COUNT(*) FROM pages WHERE ocr_status='skipped'") or 0
    parts = one("SELECT COUNT(*) FROM parts")
    ref = one("SELECT COUNT(*) FROM ref_nsn")
    con.close()
    searchable = (pages - pend - run) if pages else 0
    cov = round(100 * searchable / pages, 1) if pages else 0
    ocr_total = pend + run + done + skip
    ocr_progress = round(100 * (done + skip) / ocr_total, 1) if ocr_total else 100.0
    corr = os.path.exists(_corr_path_b())
    corr_info = None
    if corr:
        try:
            cc = sqlite3.connect("file:%s?mode=ro" % _corr_path_b(), uri=True)
            corr_info = {"interchangeable": cc.execute("SELECT COUNT(*) FROM nsn_platforms WHERE n_vehicles>1").fetchone()[0],
                         "niin_review": cc.execute("SELECT COUNT(*) FROM niin_aliases").fetchone()[0],
                         "supersession": cc.execute("SELECT COUNT(*) FROM supersession_held").fetchone()[0]}
            cc.close()
        except Exception: corr_info = None
    dbsize = os.path.getsize(core.DB_PATH) if os.path.exists(core.DB_PATH) else 0
    return {
        "version": core.VERSION,
        "documents": docs, "pages": pages, "parts": parts, "ref_nsn": ref,
        "searchable_pages": searchable, "coverage_pct": cov,
        "ocr": {"pending": pend, "running": run, "done": done, "skipped": skip, "progress_pct": ocr_progress},
        "correlations": corr_info, "correlations_present": corr,
        "db_size_bytes": dbsize, "snapshot": latest_snapshot_info(),
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def _corr_path_b():
    return os.path.join(os.path.dirname(core.DB_PATH), "correlations.db")


def ops_summary():
    """One-glance operations view: runtime mode, page cache, recent ingest/OCR runs, latest snapshot,
    and corpus counts. Cheap queries only (no full-table OCR scan — that lives on the Status page)."""
    out = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"), "version": core.VERSION}
    out["rps"] = {"mode": core.RPS_MODE, "reason": core.RPS_REASON, "flags": core.RPS_FLAGS}
    if core._rps:
        try: out["page_cache"] = core._rps.cache_stats(core.INDEX_DIR)
        except Exception: out["page_cache"] = None
    con = core.db()
    def one(sql):
        try: return con.execute(sql).fetchone()[0]
        except Exception: return None
    out["counts"] = {"documents": one("SELECT COUNT(*) FROM documents"),
                     "vehicles": one("SELECT COUNT(DISTINCT vehicle) FROM documents WHERE vehicle IS NOT NULL AND vehicle<>''")}
    try:
        out["recent_runs"] = [dict(r) for r in con.execute(
            "SELECT id, kind, started_at, finished_at, files_seen, new_docs, pages_indexed, ocr_queued, ocr_done, failed "
            "FROM runs ORDER BY id DESC LIMIT 8")]
    except Exception:
        out["recent_runs"] = []
    con.close()
    try: out["snapshot"] = latest_snapshot_info()
    except Exception: out["snapshot"] = None
    try: out["recent_errors"] = core.recent_errors()        # v0.96.0 (B10): tail of the rotating error log
    except Exception: out["recent_errors"] = []
    return out


def file_audit(limit=600):
    """Integrity check: of the first N indexed documents, how many source files are now MISSING on disk
    (moved/deleted external drive, etc.). Read-only; a maintenance signal, not a fix."""
    con = core.db()
    try: rows = con.execute("SELECT id, path, vehicle FROM documents LIMIT ?", (limit,)).fetchall()
    except Exception: rows = []
    con.close()
    missing = []
    for r in rows:
        p = r["path"]
        try:
            if p and not os.path.exists(p): missing.append({"id": r["id"], "path": p, "vehicle": r["vehicle"]})
        except Exception: pass
    return {"checked": len(rows), "missing": len(missing), "sample": [m["path"] for m in missing[:12]]}
