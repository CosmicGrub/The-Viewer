#!/usr/bin/env python3
"""core_pillars.py — verbatim mirror of THE VIEWER's load-bearing logic (viewer_app.py
lines 1–523), isolated so it can be imported, unit-tested, and mutation-tested without the
HTTP server. It is a COPY for testing; viewer_app.py remains the source of truth. Keep in sync.
(Created because the sandbox mount caches viewer_app.py's inode and cannot re-read it.)"""
import argparse, json, os, re, sqlite3, sys, tempfile, time, urllib.parse
try:
    import pymupdf as fitz
except Exception:
    fitz = None

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from parts_request_pdf import build_request_pdf
except Exception:
    build_request_pdf = None

DB_PATH = os.path.join(HERE, "..", "index", "viewer.db")
# \b-anchored -- see patterns.py's NSN_RE (this is a verbatim mirror, kept in sync); unanchored,
# this misreads the first 13 digits of any longer digit run (invoice/tracking/PO numbers) as an NSN.
NSN_RE = re.compile(r"\b(\d{4})-?(\d{2})-?(\d{3})-?(\d{4})\b")
FSC_VEHICLE = {"2310","2320","2330","2350","2355","1510","1520","1525","1550","2210","3805","3810","3820","3825","3895","2420","2430"}

def db():
    con = sqlite3.connect(DB_PATH, timeout=30); con.row_factory = sqlite3.Row
    if os.environ.get("VIEWER_RELAXED") == "1":
        con.execute("PRAGMA locking_mode=EXCLUSIVE"); con.execute("PRAGMA journal_mode=TRUNCATE")
    return con

def _corr_path():
    return os.path.join(os.path.dirname(DB_PATH), "correlations.db")

def correlations_for(nsn):
    p = _corr_path()
    if not os.path.exists(p): return {}
    n = norm_nsn(nsn) if nsn else ""
    if not n: return {}
    digits = re.sub(r"\D", "", n); niin = digits[4:13] if len(digits) >= 13 else digits
    out = {"available": True}
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
        con.close()
    except Exception as e:
        return {"available": False, "error": str(e)}
    return out

def _reviews_path():
    return os.path.join(os.path.dirname(DB_PATH), "reviews.db")

def _latest_niin_decision(niin):
    p = _reviews_path()
    if not os.path.exists(p): return None
    try:
        con = sqlite3.connect("file:%s?mode=ro" % p, uri=True); con.row_factory = sqlite3.Row
        r = con.execute("SELECT decision, canonical_nsn FROM niin_decisions WHERE niin=? ORDER BY id DESC LIMIT 1",
                        (niin,)).fetchone()
        con.close()
        return dict(r) if r else None
    except Exception:
        return None

def nsn_aliases(nsn):
    """Equivalent NSNs for a lookup, based ONLY on user-confirmed 'interchangeable' NIIN-drift
    decisions (grounded — never auto-merged). Returns [nsn] when there's no confirmed equivalence."""
    n = norm_nsn(nsn)
    if not n: return [nsn] if nsn else []
    digits = re.sub(r"\D", "", n); niin = digits[4:13] if len(digits) >= 13 else digits
    dec = _latest_niin_decision(niin)
    if not dec or dec.get("decision") != "interchangeable": return [n]
    out = {n}
    if (dec.get("canonical_nsn") or "").strip():
        cn = norm_nsn(dec["canonical_nsn"])
        if cn: out.add(cn)
    cp = _corr_path()
    if os.path.exists(cp):
        try:
            con = sqlite3.connect("file:%s?mode=ro" % cp, uri=True)
            r = con.execute("SELECT variants FROM niin_aliases WHERE niin=?", (niin,)).fetchone()
            con.close()
            if r and r[0]:
                for v in r[0].split(" | "):
                    nv = norm_nsn(v)
                    if nv: out.add(nv)
        except Exception: pass
    return sorted(out)

def norm_nsn(s):
    m = NSN_RE.search((s or "").strip())
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}-{m.group(4)}" if m else None

def nsn_kind(nsn):
    return "vehicle" if nsn[:4] in FSC_VEHICLE else "part"

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

def _meta_rows(con, where, args, limit):
    return [dict(r) for r in con.execute(
        "SELECT d.id AS doc_id, d.vehicle, d.tm_number, d.nsn, d.title, p.page_number, "
        "snippet(pages_fts,0,'<<','>>','...',12) AS snip, p.source "
        "FROM pages_fts JOIN pages p ON p.id=pages_fts.rowid JOIN documents d ON d.id=p.document_id "
        "WHERE " + where + " ORDER BY rank LIMIT ?", args + [limit]).fetchall()]

SYN = {}
def _load_synonyms():
    global SYN
    m = {}
    try:
        data = json.load(open(os.path.join(HERE, "synonyms.json"), encoding="utf-8"))
        for grp in data.get("groups", []):
            terms = [str(t).lower().strip() for t in grp if str(t).strip()]
            for t in terms:
                m.setdefault(t, set()).update(x for x in terms if x != t)
    except Exception:
        pass
    SYN = {k: sorted(v) for k, v in m.items()}
_load_synonyms()

_VOCAB_READY = False
def _ensure_vocab(con):
    global _VOCAB_READY
    if _VOCAB_READY: return True
    try:
        con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS pages_vocab USING fts5vocab('pages_fts','row')")
        _VOCAB_READY = True
    except Exception:
        _VOCAB_READY = False
    return _VOCAB_READY

def _within1(a, b):
    if a == b: return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1: return False
    if la > lb: a, b, la, lb = b, a, lb, la
    i = j = diff = 0
    while i < la and j < lb:
        if a[i] == b[j]: i += 1; j += 1
        else:
            diff += 1
            if diff > 1: return False
            if la == lb: i += 1; j += 1
            else: j += 1
    diff += (lb - j) + (la - i)
    return diff <= 1

def fuzzy_terms(con, word, cap=4):
    w = word.lower()
    if len(w) < 5 or not w.isalpha(): return []
    if not _ensure_vocab(con): return []
    pre = w[:2]
    hi = pre[:-1] + chr(ord(pre[-1]) + 1)
    out = []
    try:
        for (term,) in con.execute("SELECT term FROM pages_vocab WHERE term>=? AND term<? LIMIT 3000", (pre, hi)):
            if term != w and term.isalpha() and abs(len(term) - len(w)) <= 1 and _within1(w, term):
                out.append(term)
                if len(out) >= cap: break
    except Exception:
        return []
    return out

def _alts(con, word, last, use_fuzzy):
    w = word.lower()
    alts = [w] + SYN.get(w, [])
    if use_fuzzy:
        for f in fuzzy_terms(con, w):
            if f not in alts: alts.append(f)
    alts = alts[:6]
    quoted = []
    for i, a in enumerate(alts):
        a = a.replace('"', '')
        quoted.append(('"%s"*' % a) if (last and i == 0) else ('"%s"' % a))
    return "(" + " OR ".join(quoted) + ")"

def popular_items(limit=12):
    con = db()
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
    con = db()
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

def build_match(con, q, match_any=False, use_fuzzy=True):
    toks = re.findall(r"[A-Za-z0-9]+", q)[:6]
    if not toks: return None
    groups = [_alts(con, t, idx == len(toks) - 1, use_fuzzy) for idx, t in enumerate(toks)]
    if match_any:
        return " OR ".join(g[1:-1] for g in groups)
    expr = " AND ".join(groups)
    phrases = []
    for c in re.findall(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+){1,}", q)[:2]:
        parts = re.findall(r"[A-Za-z0-9]+", c)
        if len(parts) >= 2: phrases.append('"' + " ".join(parts) + '"')
    if phrases:
        expr = "(" + expr + ") AND (" + " OR ".join(phrases) + ")"
    return expr

_NOMEN_ABBR = {
    "assy": "assembly", "assembly": "assy", "brkt": "bracket", "bracket": "brkt",
    "rh": "right hand", "lh": "left hand", "elec": "electrical", "electrical": "elec",
    "hyd": "hydraulic", "hydraulic": "hyd", "cyl": "cylinder", "cylinder": "cyl",
    "vlv": "valve", "valve": "vlv", "scr": "screw", "screw": "scr", "wshr": "washer",
    "washer": "wshr", "gskt": "gasket", "gasket": "gskt", "conn": "connector", "mtg": "mounting",
}
def normalize_nomenclature(q):
    q = (q or "").strip()
    if not q: return []
    variants = []
    if "," in q:
        parts = [p.strip() for p in q.split(",") if p.strip()]
        if len(parts) >= 2: variants.append(" ".join(reversed(parts)))
    toks = re.findall(r"[A-Za-z]+", q.lower())
    expanded = [_NOMEN_ABBR.get(t, t) for t in toks]
    if expanded != toks: variants.append(" ".join(expanded))
    out = []
    for v in variants:
        v = v.strip()
        if v and v.lower() != q.lower() and v not in out: out.append(v)
    return out

def search(q, limit=25, mode=None, match_any=False, use_fuzzy=True):
    q = (q or "").strip()
    if not q: return []
    con = db()
    if mode != "text" and re.fullmatch(r"\d{4}", q):
        rows = [dict(r) for r in con.execute(
            "SELECT id AS doc_id, vehicle, tm_number, nsn, title, page_count, 1 AS page_number, "
            "'cover / end-item NSN ending in ' || ? AS snip, 'meta' AS source "
            "FROM documents WHERE nsn IS NOT NULL AND nsn LIKE '%'||? ORDER BY vehicle, tm_number LIMIT ?",
            (q, q, limit)).fetchall()]
        for r in rows:
            r["last4_query"] = q
            r["nsn_kind"] = nsn_kind(r["nsn"]) if r.get("nsn") else "part"
        con.close(); return rows
    nsn = norm_nsn(q)
    if nsn and len(re.sub(r"\D","",q)) >= 11:
        aliases = nsn_aliases(nsn)                        # confirmed-interchangeable equivalents (grounded)
        phrase = " OR ".join('"' + a.replace("-", " ") + '"' for a in aliases)
        try: rows = _meta_rows(con, "pages_fts MATCH ?", [phrase], limit)
        except sqlite3.OperationalError: rows = []
        qmarks = ",".join("?" * len(aliases))
        cover = [dict(r) for r in con.execute(
            "SELECT id AS doc_id, vehicle, tm_number, nsn, title, 1 AS page_number, "
            "'cover/end-item NSN match' AS snip, 'meta' AS source FROM documents WHERE nsn IN (" + qmarks + ") LIMIT 10", aliases).fetchall()]
        seen=set(); out=[]
        for r in cover + rows:
            r["nsn_query"] = nsn; r["nsn_kind"] = nsn_kind(nsn)
            if len(aliases) > 1: r["aliases"] = aliases
            k=(r["doc_id"], r["page_number"])
            if k in seen: continue
            seen.add(k); out.append(r)
        con.close(); return out[:limit]
    match = build_match(con, q, match_any, use_fuzzy)
    if not match: con.close(); return []
    try: rows = _meta_rows(con, "pages_fts MATCH ?", [match], limit)
    except sqlite3.OperationalError:
        like = "%" + q + "%"
        rows = [dict(r) for r in con.execute(
            "SELECT d.id AS doc_id,d.vehicle,d.tm_number,d.nsn,d.title,p.page_number,substr(p.body_text,1,200) AS snip,p.source "
            "FROM pages p JOIN documents d ON d.id=p.document_id WHERE p.body_text LIKE ? LIMIT ?", (like, limit)).fetchall()]
    # Nomenclature widening: if the catalog-style query is sparse, also try comma-inverted /
    # abbreviation-expanded variants and append unseen hits (additive — never removes results).
    if len(rows) < 3:
        seen = {(r["doc_id"], r["page_number"]) for r in rows}
        for variant in normalize_nomenclature(q):
            vm = build_match(con, variant, match_any, use_fuzzy)
            if not vm: continue
            try: extra = _meta_rows(con, "pages_fts MATCH ?", [vm], limit)
            except sqlite3.OperationalError: extra = []
            for r in extra:
                k = (r["doc_id"], r["page_number"])
                if k not in seen: rows.append(r); seen.add(k)
    pop = popular_nsns(con)
    if pop:
        for r in rows:
            if (r.get("nsn") or "").strip() in pop: r["boosted"] = True
        rows.sort(key=lambda r: 0 if r.get("boosted") else 1)
    con.close(); return rows

def part_lookup(nsn):
    nsn = (nsn or "").strip()
    if not nsn: return {"nsn": "", "found": False, "refs": []}
    con = db()
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

def reference_for(nsn=None, size=None):
    con = db(); out = {}
    if nsn:
        nsn = nsn.strip()
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
            if v and v[0] > 1: out["versions"] = v[0]
        except sqlite3.OperationalError: pass
    if size:
        try:
            r = con.execute("SELECT size,series,major_in,major_mm,tpi_or_pitch,tap_drill,torque_ref_lbft,source,source_url FROM ref_hardware WHERE size LIKE ?||'%' LIMIT 1", (size.strip(),)).fetchone()
            if r: out["hardware"] = dict(r)
        except sqlite3.OperationalError: pass
    con.close(); return out

def coverage(vehicle=None):
    con = db()
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
    return out
