#!/usr/bin/env python3
"""THE VIEWER -- Smart Collections feature (extracted from viewer_app for modularity).

A collection is a saved named query evaluated LIVE against pages_fts, so it auto-fills as OCR adds text.
Definitions live in collections.db (its OWN sidecar), so creating/deleting one NEVER writes the main index
and NEVER contends with the OCR writer (R1/R6). Shared primitives (the live DB connection, the index path)
come from viewer_app at call time via `core` -- this keeps the module import-cycle-safe.
"""
import os, re, sqlite3, time
# `core` is the running viewer_app module, INJECTED by viewer_app after it imports us (see viewer_app.py).
# We do NOT `import viewer_app` here: that would create a circular import that dead-locks when the app runs
# as `python viewer_app.py` (__main__) — the exact "refused to connect" failure. Injection also means
# core.DB_PATH reflects the --db override set in main(), because `core` IS the live running module.
core = None

SEED_COLLECTIONS = [
    ("warnings",    "Warnings & Cautions",     'WARNING OR CAUTION OR DANGER OR WARNINGS OR CAUTIONS'),
    ("torque",      "Torque specs",            'torque OR "ft-lb" OR "lb-ft" OR "foot-pounds" OR "inch-pounds" OR "newton-meters"'),
    ("wiring",      "Wiring & schematics",     'schematic OR wiring OR harness OR connector OR pinout OR receptacle'),
    ("hydraulics",  "Hydraulics",              'hydraulic OR cylinder OR "relief valve" OR accumulator OR "hydraulic pump"'),
    ("lubrication", "Lubrication & PMCS",      'lubricate OR lubrication OR grease OR PMCS OR "oil change"'),
    ("remove",      "Removal & installation",  'removal OR installation OR disassembly OR assembly OR "remove and"'),
]
_SEED_SLUGS = {s for s, _, _ in SEED_COLLECTIONS}

_MTYPES = [
    ("operator", "Operator (-10)",          ["*-10[ P.&-]*", "*OPERATOR*"]),
    ("maint",    "Maintenance (-20/-24)",   ["*-20[ P.&-]*", "*-23[ P.&-]*", "*-24[ P.&-]*", "*-34[ P.&-]*", "*-40[ P.&-]*", "*MAINT*"]),
    ("parts",    "Parts (RPSTL)",           ["*-20P*", "*-24P*", "*&P*", "*RPSTL*", "*PARTS*"]),
    ("lube",     "Lubrication (LO)",        ["*LO 9-*", "*LUBRICAT*"]),
    ("schem",    "Schematics / wiring",     ["*SCHEMATIC*", "*WIRING*"]),
    ("trouble",  "Troubleshooting",         ["*TROUBLESHOOT*"]),
]
_MTYPE_MAP = {k: (label, pats) for k, label, pats in _MTYPES}
_DOC_BLOB = "upper(coalesce(d.tm_number,'')||' '||coalesce(d.title,'')||' '||coalesce(d.path,''))"

def _collections_path():
    return os.path.join(os.path.dirname(core.DB_PATH), "collections.db")

def _collections_ensure(con):
    con.execute("CREATE TABLE IF NOT EXISTS collections(slug TEXT PRIMARY KEY, name TEXT, query TEXT, "
                "created TEXT, hidden INTEGER DEFAULT 0)")
    cols = {r[1] for r in con.execute("PRAGMA table_info(collections)")}
    for c, decl in (("vehicle", "TEXT"), ("mtype", "TEXT"), ("pinned", "INTEGER DEFAULT 0")):
        if c not in cols:
            con.execute("ALTER TABLE collections ADD COLUMN %s %s" % (c, decl))
    con.execute("CREATE TABLE IF NOT EXISTS collection_seen(slug TEXT PRIMARY KEY, last_count INTEGER, last_seen TEXT)")

def _slugify(s):
    out = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:48]
    return out or ("c" + ("%08x" % (abs(hash(s or "")) & 0xffffffff)))

def _scope_label(vehicle, mtype):
    parts = []
    if vehicle: parts.append(vehicle)
    if mtype and mtype in _MTYPE_MAP: parts.append(_MTYPE_MAP[mtype][0])
    return " · ".join(parts)

def _scope_where(vehicle, mtype):
    where = []; args = []
    if vehicle:
        where.append("d.vehicle = ? COLLATE NOCASE"); args.append(vehicle)
    if mtype and mtype in _MTYPE_MAP:
        pats = _MTYPE_MAP[mtype][1]
        where.append("(" + " OR ".join(_DOC_BLOB + " GLOB ?" for _ in pats) + ")"); args += pats
    return ((" AND " + " AND ".join(where)) if where else ""), args

def _collections_defs():
    defs = {slug: {"slug": slug, "name": name, "query": q, "seed": True, "vehicle": None, "mtype": None, "pinned": 0}
            for slug, name, q in SEED_COLLECTIONS}
    p = _collections_path()
    if os.path.exists(p):
        try:
            con = sqlite3.connect("file:%s?mode=ro" % p, uri=True); con.row_factory = sqlite3.Row
            if con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='collections'").fetchone():
                cols = {r[1] for r in con.execute("PRAGMA table_info(collections)")}
                has = lambda c: c in cols
                sel = "slug,name,query,hidden" + (",vehicle" if has("vehicle") else "") + \
                      (",mtype" if has("mtype") else "") + (",pinned" if has("pinned") else "")
                for r in con.execute("SELECT " + sel + " FROM collections"):
                    if r["hidden"]:
                        defs.pop(r["slug"], None)
                    else:
                        defs[r["slug"]] = {"slug": r["slug"], "name": r["name"], "query": r["query"],
                                           "seed": r["slug"] in _SEED_SLUGS,
                                           "vehicle": (r["vehicle"] if has("vehicle") else None) or None,
                                           "mtype": (r["mtype"] if has("mtype") else None) or None,
                                           "pinned": (r["pinned"] if has("pinned") else 0) or 0}
            con.close()
        except Exception:
            pass
    return defs

def _seen_map():
    p = _collections_path(); out = {}
    if not os.path.exists(p): return out
    try:
        con = sqlite3.connect("file:%s?mode=ro" % p, uri=True)
        if con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='collection_seen'").fetchone():
            for slug, lc, ls in con.execute("SELECT slug,last_count,last_seen FROM collection_seen"):
                out[slug] = {"last_count": lc or 0, "last_seen": ls}
        con.close()
    except Exception:
        pass
    return out

def _mark_seen(slug, count):
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    con = sqlite3.connect(_collections_path(), timeout=30)
    try:
        _collections_ensure(con)
        con.execute("INSERT INTO collection_seen(slug,last_count,last_seen) VALUES(?,?,?) "
                    "ON CONFLICT(slug) DO UPDATE SET last_count=excluded.last_count, last_seen=excluded.last_seen",
                    (slug, int(count), now))
        con.commit()
    finally:
        con.close()

def _fts_count(con, query, vehicle=None, mtype=None, cap=2000):
    try:
        sw, sa = _scope_where(vehicle, mtype)
        if sw:
            sql = ("SELECT COUNT(*) FROM (SELECT 1 FROM pages_fts JOIN pages p ON p.id=pages_fts.rowid "
                   "JOIN documents d ON d.id=p.document_id WHERE pages_fts MATCH ?" + sw + " LIMIT ?)")
            n = con.execute(sql, [query] + sa + [cap]).fetchone()[0]
        else:
            n = con.execute("SELECT COUNT(*) FROM (SELECT 1 FROM pages_fts WHERE pages_fts MATCH ? LIMIT ?)",
                            (query, cap)).fetchone()[0]
        return int(n), (n >= cap)
    except Exception:
        return 0, False

def smart_collections_list():
    con = core.db(); seen = _seen_map(); out = []
    for d in _collections_defs().values():
        n, capped = _fts_count(con, d["query"], d.get("vehicle"), d.get("mtype"))
        s = seen.get(d["slug"]); new = 0
        if s and not capped:
            new = max(0, n - int(s.get("last_count") or 0))
        out.append({"slug": d["slug"], "name": d["name"], "query": d["query"], "seed": d["seed"],
                    "count": n, "capped": capped, "new": new, "pinned": int(d.get("pinned") or 0),
                    "vehicle": d.get("vehicle"), "mtype": d.get("mtype"),
                    "scope": _scope_label(d.get("vehicle"), d.get("mtype"))})
    out.sort(key=lambda x: (not x["pinned"], not x["seed"], x["name"].lower()))
    return {"collections": out, "facets": _collection_facets()}

def smart_collection_eval(slug, limit=80, offset=0):
    d = _collections_defs().get(slug)
    if not d:
        return {"error": "no such collection", "items": []}
    con = core.db()
    sw, sa = _scope_where(d.get("vehicle"), d.get("mtype"))
    try:
        rows = con.execute(
            "SELECT d.id AS doc_id, d.vehicle, d.tm_number, d.nsn, d.title, p.page_number, "
            "snippet(pages_fts,0,'<<','>>','...',12) AS snip, p.source "
            "FROM pages_fts JOIN pages p ON p.id=pages_fts.rowid JOIN documents d ON d.id=p.document_id "
            "WHERE pages_fts MATCH ?" + sw + " ORDER BY rank LIMIT ? OFFSET ?",
            [d["query"]] + sa + [max(1, min(int(limit), 500)), max(0, int(offset))]).fetchall()
    except sqlite3.OperationalError as e:
        return {"slug": slug, "name": d["name"], "query": d["query"], "items": [], "error": str(e)}
    if int(offset) == 0:
        try:
            n, _cap = _fts_count(con, d["query"], d.get("vehicle"), d.get("mtype"))
            _mark_seen(slug, n)
        except Exception:
            pass
    return {"slug": slug, "name": d["name"], "query": d["query"], "seed": d["seed"],
            "vehicle": d.get("vehicle"), "mtype": d.get("mtype"),
            "scope": _scope_label(d.get("vehicle"), d.get("mtype")),
            "offset": int(offset), "items": [dict(r) for r in rows]}

def smart_collection_save(name, query, vehicle="", mtype="", pinned=None):
    name = (name or "").strip(); query = (query or "").strip()
    vehicle = (vehicle or "").strip(); mtype = (mtype or "").strip()
    if mtype and mtype not in _MTYPE_MAP: mtype = ""
    if not name or not query:
        return {"ok": False, "error": "name and query are required"}
    slug = _slugify(name); now = time.strftime("%Y-%m-%dT%H:%M:%S"); pin = 1 if pinned else 0
    con = sqlite3.connect(_collections_path(), timeout=30)
    try:
        _collections_ensure(con)
        con.execute("INSERT INTO collections(slug,name,query,created,hidden,vehicle,mtype,pinned) "
                    "VALUES(?,?,?,?,0,?,?,?) ON CONFLICT(slug) DO UPDATE SET name=excluded.name, "
                    "query=excluded.query, hidden=0, vehicle=excluded.vehicle, mtype=excluded.mtype, pinned=excluded.pinned",
                    (slug, name, query, now, vehicle or None, mtype or None, pin))
        con.commit()
    finally:
        con.close()
    return {"ok": True, "slug": slug}

def smart_collection_pin(slug, pinned):
    d = _collections_defs().get((slug or "").strip())
    if not d: return {"ok": False, "error": "no such collection"}
    now = time.strftime("%Y-%m-%dT%H:%M:%S"); pin = 1 if pinned else 0
    con = sqlite3.connect(_collections_path(), timeout=30)
    try:
        _collections_ensure(con)
        con.execute("INSERT INTO collections(slug,name,query,created,hidden,vehicle,mtype,pinned) "
                    "VALUES(?,?,?,?,0,?,?,?) ON CONFLICT(slug) DO UPDATE SET pinned=excluded.pinned",
                    (d["slug"], d["name"], d["query"], now, d.get("vehicle"), d.get("mtype"), pin))
        con.commit()
    finally:
        con.close()
    return {"ok": True, "slug": d["slug"], "pinned": pin}

def smart_collection_delete(slug):
    slug = (slug or "").strip()
    if not slug:
        return {"ok": False, "error": "slug required"}
    is_seed = slug in _SEED_SLUGS; now = time.strftime("%Y-%m-%dT%H:%M:%S")
    con = sqlite3.connect(_collections_path(), timeout=30)
    try:
        _collections_ensure(con)
        if is_seed:
            con.execute("INSERT INTO collections(slug,name,query,created,hidden) VALUES(?,?,?,?,1) "
                        "ON CONFLICT(slug) DO UPDATE SET hidden=1", (slug, slug, "", now))
        else:
            con.execute("DELETE FROM collections WHERE slug=?", (slug,))
        con.commit()
    finally:
        con.close()
    return {"ok": True, "slug": slug, "hidden": is_seed}

def _collection_facets():
    con = core.db(); vehicles = []
    try:
        for r in con.execute("SELECT vehicle, COUNT(*) c FROM documents WHERE vehicle IS NOT NULL AND vehicle<>'' "
                             "GROUP BY vehicle ORDER BY c DESC, vehicle LIMIT 250"):
            vehicles.append(r[0])
    except Exception:
        pass
    return {"vehicles": vehicles, "types": [{"key": k, "label": lbl} for k, lbl, _ in _MTYPES]}
