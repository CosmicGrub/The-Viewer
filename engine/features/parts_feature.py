#!/usr/bin/env python3
"""THE VIEWER -- parts intelligence (extracted verbatim from viewer_app, v0.96.0 modularization).

NSN correlations + NIIN-drift review queue (sidecars), confirmed-interchangeable aliases,
catalog part lookups, the Look-Alike Parts recognizer, external reference data, and the
learning layer (popular items, fault->parts, tech-status suggestion). DI via `core`."""
import os
import re
import sqlite3
import time

from patterns import norm_nsn, NSN_RE  # noqa: F401  (canonical patterns, A6)

core = None          # injected by viewer_app at startup


def _corr_path():
    return os.path.join(os.path.dirname(core.DB_PATH), "correlations.db")


def correlations_for(nsn):
    """Read-only correlative links for an NSN from the OPTIONAL sidecar correlations.db.
    Returns {} if the sidecar isn't present — purely additive, never required, never writes
    to the main index (R1). Surfaces: cross-platform interchangeability, NIIN format-drift
    review candidates, and held supersession pairs."""
    p = _corr_path()
    if not os.path.exists(p): return {}
    n = norm_nsn(nsn) if nsn else ""
    if not n: return {}
    digits = re.sub(r"\D", "", n); niin = digits[4:13] if len(digits) >= 13 else digits
    out = {"available": True}
    # v1.13.4: con=None + finally -- correlations.db is built incrementally (build_conflicts.py), so
    # any one of these three queries can legitimately throw against a partially-built sidecar; the old
    # close()-as-last-try-statement skipped closing on that path, leaking a handle on every such request
    # (this is the live handler behind GET /api/correlations, hit on every part/dossier page view).
    con = None
    try:
        con = sqlite3.connect("file:%s?mode=ro" % p, uri=True); con.row_factory = sqlite3.Row
        r = con.execute("SELECT n_vehicles,n_docs,vehicles FROM nsn_platforms WHERE nsn=?", (n,)).fetchone()
        if r and (r["n_vehicles"] or 0) > 1:
            out["interchangeable"] = {"n_vehicles": r["n_vehicles"], "n_docs": r["n_docs"],
                                       "vehicles": [v for v in (r["vehicles"] or "").split(" | ") if v]}
        a = con.execute("SELECT n,variants FROM niin_aliases WHERE niin=?", (niin,)).fetchone()
        if a:
            out["niin_review"] = {"niin": niin, "variants": [v for v in (a["variants"] or "").split(" | ") if v]}
        sup = con.execute("SELECT current_token FROM supersession_held WHERE old_nsn=?", (n,)).fetchall()
        if sup:
            out["superseded_held"] = [s["current_token"] for s in sup]
    except Exception as e:
        return {"available": False, "error": str(e)}
    finally:
        if con is not None:
            con.close()
    return out


VALID_NIIN_DECISIONS = {"distinct", "interchangeable", "error", "dismiss"}


def _reviews_path():
    return os.path.join(os.path.dirname(core.DB_PATH), "reviews.db")


def _reviews_con():
    """Open (and lazily create) the APPEND-ONLY review-decisions sidecar. Never touches viewer.db
    or the correlations sidecar (R1). Decisions are only inserted, never updated/deleted (R6) —
    the latest row per NIIN is the current decision; the full history is retained for audit."""
    con = sqlite3.connect(_reviews_path(), timeout=15); con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=TRUNCATE")
    con.execute("""CREATE TABLE IF NOT EXISTS niin_decisions(
        id INTEGER PRIMARY KEY, niin TEXT, decision TEXT, canonical_nsn TEXT, note TEXT,
        decided_by TEXT, decided_at TEXT DEFAULT (datetime('now')))""")
    con.execute("CREATE INDEX IF NOT EXISTS ix_niin_dec ON niin_decisions(niin)")
    return con


def record_niin_decision(niin, decision, canonical_nsn="", note="", by=""):
    niin = re.sub(r"\D", "", str(niin) if niin is not None else "")
    decision = (decision or "").strip().lower()
    if len(niin) < 9 or decision not in VALID_NIIN_DECISIONS:
        return {"ok": False, "error": "need a 9-digit NIIN and a decision in %s" % sorted(VALID_NIIN_DECISIONS)}
    con = _reviews_con()
    cur = con.execute("INSERT INTO niin_decisions(niin,decision,canonical_nsn,note,decided_by) VALUES(?,?,?,?,?)",
                      (niin, decision, (canonical_nsn or "").strip(), (note or "").strip()[:500], (by or "").strip()[:80]))
    con.commit(); rid = cur.lastrowid; con.close()
    return {"ok": True, "id": rid, "niin": niin, "decision": decision}


def _latest_decisions():
    """Map niin -> latest decision row (by id). Empty if no decisions recorded yet."""
    if not os.path.exists(_reviews_path()): return {}
    try:
        con = _reviews_con()
        rows = con.execute("""SELECT d.niin, d.decision, d.canonical_nsn, d.note, d.decided_at
            FROM niin_decisions d JOIN (SELECT niin, MAX(id) mid FROM niin_decisions GROUP BY niin) m
            ON m.mid=d.id""").fetchall()
        con.close()
        return {r["niin"]: {"decision": r["decision"], "canonical_nsn": r["canonical_nsn"],
                            "note": r["note"], "decided_at": r["decided_at"]} for r in rows}
    except Exception:
        return {}


def nsn_aliases(nsn):
    """Equivalent NSNs for a lookup, based ONLY on user-confirmed 'interchangeable' NIIN-drift
    decisions (grounded — never auto-merged). Returns [nsn] when there's no confirmed equivalence.
    Reads the append-only reviews.db + the correlations sidecar; both optional."""
    n = norm_nsn(nsn)
    if not n: return [nsn] if nsn else []
    digits = re.sub(r"\D", "", n); niin = digits[4:13] if len(digits) >= 13 else digits
    rp = _reviews_path()
    if not os.path.exists(rp): return [n]
    # v1.13.4: rc/cc=None + finally -- called on every search-result render (search_feature.py); a
    # not-yet-created niin_decisions/niin_aliases table used to leak the respective handle on throw.
    rc = None
    try:
        rc = sqlite3.connect("file:%s?mode=ro" % rp, uri=True); rc.row_factory = sqlite3.Row
        dr = rc.execute("SELECT decision, canonical_nsn FROM niin_decisions WHERE niin=? ORDER BY id DESC LIMIT 1",
                        (niin,)).fetchone()
    except Exception:
        return [n]
    finally:
        if rc is not None:
            rc.close()
    if not dr or dr["decision"] != "interchangeable": return [n]
    out = {n}
    if (dr["canonical_nsn"] or "").strip():
        cn = norm_nsn(dr["canonical_nsn"])
        if cn: out.add(cn)
    cp = _corr_path()
    if os.path.exists(cp):
        cc = None
        try:
            cc = sqlite3.connect("file:%s?mode=ro" % cp, uri=True)
            r = cc.execute("SELECT variants FROM niin_aliases WHERE niin=?", (niin,)).fetchone()
            if r and r[0]:
                for v in r[0].split(" | "):
                    nv = norm_nsn(v)
                    if nv: out.add(nv)
        except Exception: pass
        finally:
            if cc is not None:
                cc.close()
    return sorted(out)


def niin_review(limit=200, offset=0, pending_only=False):
    """The NIIN format-drift review queue: same NIIN written as different NSN strings (a data-quality
    signal). Read from the optional correlations sidecar; merges in the user's recorded decisions."""
    p = _corr_path()
    if not os.path.exists(p): return {"available": False, "items": []}
    # v1.13.4: con=None + finally -- wired live to GET /api/niin_review; con.close() used to only run
    # after both queries succeeded, leaking the handle on any throw (missing table, locked file, etc.).
    con = None
    try:
        con = sqlite3.connect("file:%s?mode=ro" % p, uri=True); con.row_factory = sqlite3.Row
        total = con.execute("SELECT COUNT(*) FROM niin_aliases").fetchone()[0]
        rows = con.execute("SELECT niin, n, variants FROM niin_aliases ORDER BY n DESC, niin").fetchall()
        dec = _latest_decisions()
        decided = sum(1 for r in rows if r["niin"] in dec)
        out = []
        for r in rows:
            d = dec.get(r["niin"])
            if pending_only and d: continue
            variants = [v for v in (r["variants"] or "").split(" | ") if v]
            fscs = sorted({v[:4] for v in variants})
            out.append({"niin": r["niin"], "n": r["n"], "variants": variants,
                        "fsc_conflict": len(fscs) > 1, "fscs": fscs, "decision": d})
            if len(out) >= offset + limit: pass
        page = out[offset:offset+limit]
        return {"available": True, "total": total, "decided": decided, "pending": total - decided,
                "offset": offset, "items": page}
    except Exception as e:
        return {"available": False, "error": str(e), "items": []}
    finally:
        if con is not None:
            con.close()


def fault_parts(fault, limit=10):
    """Predictive 'parts usually needed for this fault': from the end-to-end log, the parts most often
    requested on sessions whose fault text overlaps the given fault. Grounded in your own history."""
    terms = [t for t in re.findall(r"[A-Za-z0-9]+", (fault or "").lower()) if len(t) >= 4][:6]
    if not terms: return {"fault": fault, "terms": [], "parts": []}
    con = core.db()
    like = " OR ".join(["LOWER(f.description) LIKE ?"] * len(terms))
    args = ["%" + t + "%" for t in terms]
    try:
        rows = con.execute(
            "SELECT ri.item_name, ri.nsn, COUNT(*) n, MAX(ri.created_at) last "
            "FROM request_items ri JOIN sessions s ON s.id=ri.session_id JOIN faults f ON f.session_id=s.id "
            "WHERE (COALESCE(TRIM(ri.nsn),'')<>'' OR COALESCE(TRIM(ri.item_name),'')<>'') AND (" + like + ") "
            "GROUP BY COALESCE(NULLIF(TRIM(LOWER(ri.nsn)),''), TRIM(LOWER(ri.item_name))) "
            "ORDER BY n DESC, last DESC LIMIT ?", args + [limit]).fetchall()
        parts = [dict(r) for r in rows]
    except sqlite3.OperationalError:
        parts = []
    con.close()
    return {"fault": fault, "terms": terms, "parts": parts}


# ---- learning layer: surface parts that made it end-to-end onto a generated 104th sheet ----
def popular_items(limit=12):
    """Most-requested parts from request_items (the end-to-end success log), by frequency + recency.
    Bare item_name/nsn are taken from the most-recent row in each group (via MAX(created_at))."""
    con = core.db()
    try:
        rows = con.execute(
            "SELECT item_name, nsn, COUNT(*) AS n, MAX(created_at) AS last "
            "FROM request_items "
            "WHERE COALESCE(TRIM(item_name),'')<>'' OR COALESCE(TRIM(nsn),'')<>'' "
            "GROUP BY COALESCE(NULLIF(TRIM(LOWER(nsn)),''), TRIM(LOWER(item_name))) "
            "ORDER BY n DESC, last DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []
    finally:
        con.close()


_POP_CACHE = {"t": 0.0, "s": set()}


def popular_nsns(con):
    """Set of NSNs that have been successfully requested before (cached 60s) -- used to rank results."""
    now = time.time()
    if _POP_CACHE["s"] and now - _POP_CACHE["t"] < 60: return _POP_CACHE["s"]
    s = set()
    try:
        for (nsn,) in con.execute("SELECT DISTINCT TRIM(nsn) FROM request_items WHERE COALESCE(TRIM(nsn),'')<>''"):
            if nsn: s.add(nsn)
    except sqlite3.OperationalError:
        pass
    _POP_CACHE["t"] = now; _POP_CACHE["s"] = s
    return s


# ---- tech status: derive from fault + part, grounded in PMCS "Not Fully Mission Capable If" ----
TECH_CODES = ["FMC", "PMCM", "PMCS", "NMCM", "NMCS"]
_TS_STOP = {"the","and","not","with","for","this","that","from","your","you","are","was","has","will",
            "when","what","item","check","service","vehicle","fault","faults","damage","work","needed","its"}


def _ts_terms(text):
    out = []
    for tk in re.findall(r"[A-Za-z0-9]+", text or ""):
        t = tk.lower()
        if len(t) >= 4 and t not in _TS_STOP and t not in out: out.append(t)
    return out[:6]


def tech_status_suggest(vehicle, fault, parts=""):
    """Suggest a tech status by (A) matching the fault to the vehicle's PMCS 'Not Fully Mission
    Capable If' criteria (cited, authoritative), then (B) prior confirmed history. Never decides
    silently -- the UI requires a human to confirm."""
    con = core.db()
    terms = _ts_terms((fault or "") + " " + (parts or ""))
    evidence = []; suggestion = None; basis = None
    if vehicle and terms:
        termexpr = " OR ".join('"%s"' % t for t in terms)
        m = '("not fully mission capable" OR "mission capable") AND (' + termexpr + ')'
        try:
            rows = con.execute(
                "SELECT d.id doc_id, d.tm_number, p.page_number, p.body_text FROM pages_fts "
                "JOIN pages p ON p.id=pages_fts.rowid JOIN documents d ON d.id=p.document_id "
                "WHERE d.vehicle=? AND pages_fts MATCH ? ORDER BY rank LIMIT 8", (vehicle, m)).fetchall()
        except sqlite3.OperationalError:
            rows = []
        seen = set()
        for r in rows:
            key = (r["doc_id"], r["page_number"])
            if key in seen: continue
            seen.add(key)
            bt = re.sub(r"\s+", " ", r["body_text"] or "")
            snip = None
            for mo in re.finditer(r"not fully mission capable if", bt, re.I):
                seg = bt[mo.start():mo.start() + 240]
                if any(t in seg.lower() for t in terms): snip = seg; break
            if not snip:
                for t in terms:
                    k = bt.lower().find(t)
                    if k >= 0: snip = bt[max(0, k - 70):k + 170]; break
            evidence.append({"doc_id": r["doc_id"], "tm": r["tm_number"], "page": r["page_number"],
                             "text": (snip or "").strip()[:240]})
            if len(evidence) >= 4: break
        if evidence:
            suggestion = "NMCS"; basis = "pmcs"
    history = None
    if terms:
        like = " OR ".join(["f.description LIKE ?"] * len(terms))
        args = ["%" + t + "%" for t in terms]
        try:
            hr = con.execute(
                "SELECT UPPER(TRIM(s.tech_status)) st, COUNT(*) n FROM sessions s JOIN faults f ON f.session_id=s.id "
                "WHERE COALESCE(TRIM(s.tech_status),'')<>'' AND (" + like + ") GROUP BY st ORDER BY n DESC LIMIT 1", args).fetchone()
            if hr and hr[0]: history = {"status": hr[0], "count": hr[1]}
        except sqlite3.OperationalError:
            history = None
    if not suggestion and history:
        suggestion = history["status"]; basis = "history"
    if basis == "pmcs":
        rationale = "The fault matches a PMCS 'Not Fully Mission Capable If' criterion — a deadlining fault. Parts are on order, so supply (NMCS) is suggested. Review the cited criteria and confirm."
    elif basis == "history":
        rationale = "No PMCS criterion matched in the index, but this fault was logged as %s before. Confirm or override." % history["status"]
    else:
        rationale = "No PMCS criterion or prior history matched — set the status from the manual or your judgment."
    con.close()
    return {"suggestion": suggestion, "basis": basis, "rationale": rationale,
            "evidence": evidence, "history": history, "codes": TECH_CODES, "terms": terms}


def part_lookup(nsn):
    """Cited catalog references for an NSN: which figure(s)/page(s)/vehicle(s) it appears in (RPSTL).
    Grounded and verifiable — every ref points at a real page. Does not assert an exact part#."""
    nsn = (nsn or "").strip()
    if not nsn: return {"nsn": "", "found": False, "refs": []}
    nsn = norm_nsn(nsn) or nsn   # canonical dashed form -- parts.nsn is always stored dashed (A6)
    con = core.db()
    try:
        refs = [dict(r) for r in con.execute(
            "SELECT vehicle, fig_no, fig_title, MIN(page) AS page, document_id, COUNT(*) n "
            "FROM parts WHERE confidence IS NOT NULL AND nsn=? "
            "GROUP BY vehicle, fig_no, fig_title ORDER BY n DESC, vehicle LIMIT 20", (nsn,)).fetchall()]
    except sqlite3.OperationalError:
        refs = []
    con.close()
    nomen = next((r["fig_title"] for r in refs if r.get("fig_title")), None)
    return {"nsn": nsn, "found": bool(refs), "nomenclature": nomen, "refs": refs}


def part_differences(query, limit=80):
    """Look-alike recognizer: parts that share a name/nomenclature but are functionally
    DIFFERENT (different NSN / UOC / CAGEC / SMR / FSC), with grounded 'how to tell apart'
    cues. Read-only; every variant cites the figure & page it came from. Cross-references the
    optional correlations sidecar so confirmed-same items (NIIN format-drift) and cross-platform
    interchangeable NSNs are labelled as substitutes, not as real differences (R1/R6)."""
    q = (query or "").strip()
    empty = {"query": q, "found": False, "nomenclature": None, "variants": [], "discriminators": []}
    if not q: return empty
    con = core.db(); nom = None; ref_nsn = norm_nsn(q)
    try:
        if ref_nsn:
            r = con.execute(
                "SELECT COALESCE(NULLIF(name,''),NULLIF(nomenclature,''),fig_title) AS nom "
                "FROM parts WHERE nsn=? AND COALESCE(name,nomenclature,fig_title) IS NOT NULL LIMIT 1",
                (ref_nsn,)).fetchone()
            if r: nom = r["nom"]
        if not nom: nom = q
        rows = con.execute(
            "SELECT nsn, part_number, cagec, smr, uoc, vehicle, fig_no, fig_title, "
            "       MIN(page) AS page, document_id "
            "FROM parts WHERE nsn IS NOT NULL AND nsn<>'' AND "
            "      (name = ? COLLATE NOCASE OR nomenclature = ? COLLATE NOCASE) "   # NOCASE: uses the ix_parts_name/_nomenclature index
            "GROUP BY nsn, uoc, cagec, smr, part_number, vehicle, fig_no, document_id "
            "ORDER BY nsn LIMIT ?", (nom, nom, limit*6)).fetchall()
    except sqlite3.OperationalError:
        rows = []
    con.close()
    def niin_of(nsn):
        d = re.sub(r"\D", "", nsn or ""); return d[4:13] if len(d) >= 13 else d
    variants = {}
    for r in rows:
        nsn = r["nsn"]
        v = variants.setdefault(nsn, {"nsn": nsn, "fsc": re.sub(r"\D","",nsn or "")[:4],
            "niin": niin_of(nsn), "part_numbers": set(), "cagec": set(), "smr": set(),
            "uoc": set(), "vehicles": set(), "figs": set(), "refs": []})
        for src, dst in (("part_number","part_numbers"),("cagec","cagec"),("smr","smr"),("uoc","uoc"),("vehicle","vehicles")):
            val = (r[src] or "").strip()
            if val: v[dst].add(val)
        if r["fig_no"] or r["fig_title"]:
            v["figs"].add(((str(r["fig_no"]) if r["fig_no"] else "")+" "+(r["fig_title"] or "")).strip())
        if len(v["refs"]) < 6:
            v["refs"].append({"vehicle": r["vehicle"], "fig_no": r["fig_no"], "fig_title": r["fig_title"],
                              "page": r["page"], "document_id": r["document_id"]})
    if not variants:
        empty["nomenclature"] = nom; return empty
    distinct = list(variants.values())
    def union(f):
        s = set()
        for v in distinct: s |= v[f]
        return s
    disc = []
    if len(variants) > 1: disc.append(("NSN", "different national stock numbers"))
    if len({v["fsc"] for v in distinct}) > 1: disc.append(("FSC", "different supply class (first 4 digits) -- likely different item types, not substitutes"))
    if len(union("uoc")) > 1: disc.append(("UOC", "Usable-On-Code differs -- the part is selected by your vehicle's configuration"))
    if len(union("cagec")) > 1: disc.append(("CAGEC", "different manufacturer source code"))
    if len(union("smr")) > 1: disc.append(("SMR", "different source / maintenance / recoverability handling"))
    if len(union("part_numbers")) > 1: disc.append(("part #", "different manufacturer part numbers"))
    ref = variants.get(ref_nsn) or distinct[0]; ref_niin = ref["niin"]
    for v in distinct:
        tells = []
        if v["nsn"] == ref["nsn"]:
            v["relation"] = "reference"
        elif v["niin"] and v["niin"] == ref_niin:
            v["relation"] = "same item (format drift)"; tells.append("Same NIIN as the reference -- the same part catalogued in a different NSN format. Interchangeable.")
        elif v["fsc"] and ref["fsc"] and v["fsc"] != ref["fsc"]:
            v["relation"] = "different item class"; tells.append("Different FSC (%s vs %s) -- a different class of item that shares this figure; not a substitute." % (v["fsc"], ref["fsc"]))
        else:
            v["relation"] = "different variant"
            if v["uoc"] or ref["uoc"]:
                tells.append("Check UOC: [%s] vs reference [%s] -- fits a different vehicle configuration." % (", ".join(sorted(v["uoc"])) or "none listed", ", ".join(sorted(ref["uoc"])) or "none listed"))
            if v["cagec"] and ref["cagec"] and v["cagec"] != ref["cagec"]:
                tells.append("Different manufacturer (CAGEC %s vs %s)." % (", ".join(sorted(v["cagec"])), ", ".join(sorted(ref["cagec"]))))
            if v["part_numbers"] and ref["part_numbers"] and v["part_numbers"] != ref["part_numbers"]:
                tells.append("Different manufacturer part number.")
        corr = correlations_for(v["nsn"]) or {}
        if corr.get("interchangeable"):
            v["interchangeable_across"] = corr["interchangeable"].get("vehicles", [])
        v["how_to_tell_apart"] = tells
        for k in ("part_numbers","cagec","smr","uoc","vehicles","figs"): v[k] = sorted(v[k])
    order = {"reference":0,"different variant":1,"same item (format drift)":2,"different item class":3}
    distinct.sort(key=lambda v: (order.get(v["relation"],9), v["nsn"]))
    return {"query": q, "found": True, "nomenclature": nom, "reference_nsn": ref["nsn"],
            "n_variants": len(distinct), "discriminators": [{"field":f,"note":nt} for f,nt in disc],
            "variants": distinct[:limit]}


def reference_for(nsn=None, size=None):
    """External, cited reference data (kept separate from manual content): NSN→name/desc/GSA-price,
    and public-domain standard-hardware dimensions by thread size."""
    con = core.db(); out = {}
    if nsn:
        nsn = nsn.strip()
        nsn = norm_nsn(nsn) or nsn   # canonical dashed form -- ref_nsn.nsn is always stored dashed (A6)
        try:
            try:
                r = con.execute("SELECT nsn,item_name,description,gsa_price,part_no,cagec,characteristics,aac,substitutes,data_date,superseded,alt_parts,source,source_url,fetched_at FROM ref_nsn WHERE nsn=?", (nsn,)).fetchone()
            except sqlite3.OperationalError:
                try:
                    r = con.execute("SELECT nsn,item_name,description,gsa_price,part_no,cagec,characteristics,aac,substitutes,source,source_url,fetched_at FROM ref_nsn WHERE nsn=?", (nsn,)).fetchone()
                except sqlite3.OperationalError:
                    r = con.execute("SELECT nsn,item_name,description,gsa_price,source,source_url,fetched_at FROM ref_nsn WHERE nsn=?", (nsn,)).fetchone()
            if r: out["nsn"] = dict(r)
        except sqlite3.OperationalError: pass
        try:
            v = con.execute("SELECT COUNT(*) FROM ref_nsn_log WHERE nsn=?", (nsn,)).fetchone()
            if v and v[0] > 1: out["versions"] = v[0]   # R6: prior versions retained
        except sqlite3.OperationalError: pass
    if size:
        try:
            r = con.execute("SELECT size,series,major_in,major_mm,tpi_or_pitch,tap_drill,torque_ref_lbft,source,source_url FROM ref_hardware WHERE size LIKE ?||'%' LIMIT 1", (size.strip(),)).fetchone()
            if r: out["hardware"] = dict(r)
        except sqlite3.OperationalError: pass
    con.close(); return out
