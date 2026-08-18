#!/usr/bin/env python3
"""THE VIEWER -- search stack (extracted verbatim from viewer_app in the v0.96.0 modularization).

Synonyms/keywords/tags (the teachable layer), offline fuzzy matching, google-style type-ahead,
the FTS5 search itself, and in-document find. Shared primitives come from the running viewer_app
via the injected `core` (set by viewer_app at startup: features.search_feature.core = <module>),
which keeps this import-cycle-safe -- the established DI pattern (collections_feature et al).
"""
import json
import os
import re
import sqlite3
import time

from patterns import norm_nsn  # canonical NSN regex (A6: single source of truth)

core = None          # injected by viewer_app at startup
ENGINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- Army-TM nomenclature normalization: improve recall on cataloged item names ----
_NOMEN_ABBR = {
    "assy": "assembly", "assembly": "assy", "brkt": "bracket", "bracket": "brkt",
    "rh": "right hand", "lh": "left hand", "elec": "electrical", "electrical": "elec",
    "hyd": "hydraulic", "hydraulic": "hyd", "cyl": "cylinder", "cylinder": "cyl",
    "vlv": "valve", "valve": "vlv", "scr": "screw", "screw": "scr", "wshr": "washer",
    "washer": "wshr", "gskt": "gasket", "gasket": "gskt", "conn": "connector", "mtg": "mounting",
}


def normalize_nomenclature(q):
    """Return query variants that bridge Army cataloging style and plain English:
    comma-inverted names ('BOLT, MACHINE' <-> 'machine bolt') and common abbreviation expansions.
    Additive — used to widen search recall, never to replace the user's terms."""
    q = (q or "").strip()
    if not q: return []
    variants = []
    if "," in q:
        parts = [p.strip() for p in q.split(",") if p.strip()]
        if len(parts) >= 2:
            variants.append(" ".join(reversed(parts)))          # "BOLT, MACHINE" -> "MACHINE BOLT"
    toks = re.findall(r"[A-Za-z]+", q.lower())
    expanded = [_NOMEN_ABBR.get(t, t) for t in toks]
    if expanded != toks:
        variants.append(" ".join(expanded))
    out = []
    for v in variants:
        v = v.strip()
        if v and v.lower() != q.lower() and v not in out: out.append(v)
    return out


# ---- v1.13 (#11/#15): fielded search operators ---------------------------------------------------
_OP_RE = re.compile(r'(?:(?<=\s)|^)(tm|nsn|vehicle|side)\s*:\s*("[^"]{1,60}"|\S{1,60})', re.I)


def parse_operators(q):
    """Pull tm:/nsn:/vehicle:/side: operators out of the query text (anywhere they appear).
    Returns (free_text, ops) where ops maps operator -> value (last occurrence wins). Values may
    be quoted to include spaces (vehicle:"M915 Truck"). Purely lexical -- never guesses; an
    unknown side: value is dropped rather than silently filtering the wrong way."""
    ops = {}

    def _take(m):
        k = m.group(1).lower()
        v = m.group(2).strip()
        if v.startswith('"') and v.endswith('"'):
            v = v[1:-1]
        v = v.strip()
        if v:
            ops[k] = v
        return " "

    rest = _OP_RE.sub(_take, q or "")
    rest = re.sub(r"\s+", " ", rest).strip()
    side = (ops.get("side") or "").lower()
    if "side" in ops:
        if side in ("operator", "mechanic"):
            ops["side"] = side
        else:
            ops.pop("side", None)
    return rest, ops


def _doc_filters(tm=None, vehicle=None, nsn=None):
    """Parameterized SQL fragments filtering the documents join (alias d). Returns (where, args).
    nsn: compares digits-only against d.nsn with dashes stripped so '2530013678888' still hits
    '2530-01-367-8888'; a non-numeric value falls back to a plain LIKE."""
    where, args = "", []
    if vehicle:
        where += " AND d.vehicle LIKE ?"
        args.append("%" + str(vehicle).strip() + "%")
    if tm:
        where += " AND d.tm_number LIKE ?"
        args.append("%" + str(tm).strip() + "%")
    if nsn:
        digits = re.sub(r"\D", "", str(nsn))
        if digits:
            where += " AND replace(COALESCE(d.nsn,''),'-','') LIKE ?"
            args.append("%" + digits + "%")
        else:
            where += " AND COALESCE(d.nsn,'') LIKE ?"
            args.append("%" + str(nsn).strip() + "%")
    return where, args


def _meta_rows(con, where, args, limit):
    return [dict(r) for r in con.execute(
        "SELECT d.id AS doc_id, d.vehicle, d.tm_number, d.nsn, d.title, p.page_number, "
        "snippet(pages_fts,0,'<<','>>','...',12) AS snip, p.source "
        "FROM pages_fts JOIN pages p ON p.id=pages_fts.rowid JOIN documents d ON d.id=p.document_id "
        "WHERE " + where + " ORDER BY rank LIMIT ?", args + [limit]).fetchall()]


# ---- enhanced keyword search: synonyms + part#/FIG + ANY + offline fuzzy ----
SYN = {}

# v1.13.6: test override for the live-editable user sidecar. Was previously always ENGINE_DIR/keywords_user.json
# with no test-injectable seam -- test_hardening.py/test_routes.py POST real tag/keyword data through
# user_tags_add()/user_keywords_save(), which landed in the actual git-tracked file instead of a fixture
# copy, occasionally making verify_all.py --snapshot's self-baseline see the file mid-mutation and false-fail
# (a recurrence of the same class of bug 5e8be64 fixed once already: duplicate entries silently accumulating
# in this file from repeated local runs). Tests set KEYWORDS_USER_PATH to a tempdir path before serving.
KEYWORDS_USER_PATH = None


def _kw_user_path():
    # `is not None` (not a truthy check) so a caller accidentally setting KEYWORDS_USER_PATH = "" doesn't
    # silently fall through to the real tracked sidecar -- the exact isolation this override exists for.
    return KEYWORDS_USER_PATH if KEYWORDS_USER_PATH is not None else os.path.join(ENGINE_DIR, "keywords_user.json")


def _load_synonyms():
    """Load extensible alias groups from synonyms.json + keywords.json (bidirectional). keywords.json holds
    the 'strange but sensible' shop terms / colloquial names mapped to catalog nomenclature, so a slang or
    functional search still finds the right part. Both are plain JSON, offline; extend with build_keywords.py."""
    global SYN
    m = {}
    # synonyms.json + keywords.json are curated (code, always ENGINE_DIR); keywords_user.json is YOUR
    # live-editable additions (test-overridable via KEYWORDS_USER_PATH, see _kw_user_path()).
    for fn, path in (("synonyms.json", os.path.join(ENGINE_DIR, "synonyms.json")),
                      ("keywords.json", os.path.join(ENGINE_DIR, "keywords.json")),
                      ("keywords_user.json", _kw_user_path())):
        try:
            data = json.load(open(path, encoding="utf-8"))
            for grp in data.get("groups", []):
                terms = [str(t).lower().strip() for t in grp if str(t).strip()]
                for t in terms:
                    m.setdefault(t, set()).update(x for x in terms if x != t)
            # per-part tags (added inline via the pencil icon): each part's name + NSN + its tags become
            # mutually-findable, so a tag you put on a part also finds that part.
            for ent in (data.get("tags", {}) or {}).values():
                terms = [str(x).lower().strip() for x in
                         ([ent.get("name"), ent.get("nsn")] + (ent.get("tags") or [])) if str(x or "").strip()]
                for t in terms:
                    m.setdefault(t, set()).update(x for x in terms if x != t)
        except Exception:
            pass
    SYN = {k: sorted(v) for k, v in m.items()}


_load_synonyms()


def user_keywords_list():
    """The user's own keyword/tag groups (live-editable). Curated seed counts are reported too."""
    groups = []
    try:
        groups = json.load(open(_kw_user_path(), encoding="utf-8")).get("groups", [])
    except Exception:
        groups = []
    seed = 0
    for fn in ("synonyms.json", "keywords.json"):
        try: seed += len(json.load(open(os.path.join(ENGINE_DIR, fn), encoding="utf-8")).get("groups", []))
        except Exception: pass
    return {"groups": groups, "seed_groups": seed, "terms_indexed": len(SYN)}


def user_keywords_save(terms):
    """Add a keyword/tag group: a list of words that should all find each other in search. Writes the
    user sidecar only (never the curated files), then live-reloads search. Append-only in spirit."""
    terms = [str(t).strip() for t in (terms or []) if str(t).strip()]
    # de-dup case-insensitively, keep order
    seen = set(); clean = []
    for t in terms:
        if t.lower() not in seen: seen.add(t.lower()); clean.append(t)
    if len(clean) < 2:
        return {"ok": False, "error": "enter at least two words that mean the same thing"}
    try:
        try: doc = json.load(open(_kw_user_path(), encoding="utf-8"))
        except Exception: doc = {"groups": []}
        groups = doc.setdefault("groups", [])
        # de-dup case-insensitively against existing groups (same words, any order = same group) --
        # without this, identical submissions (e.g. repeated route-sweep/smoke traffic) pile up as
        # unbounded duplicates on every call, unlike user_tags_add()'s tag list a few lines down.
        want = set(t.lower() for t in clean)
        if not any(set(t.lower() for t in g) == want for g in groups):
            groups.append(clean)
        doc["_comment"] = "User-added keyword/tag groups (live). Each list = words that find each other in search."
        import safeguard          # v1.13: durable atomic write (fsync + _replace_retry, no leaked .tmp)
        safeguard.atomic_write(_kw_user_path(), json.dumps(doc, indent=2, ensure_ascii=False))
        _load_synonyms()                      # live reload -> the new words work immediately
        return {"ok": True, "group": clean, "groups": len(groups)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def user_keywords_delete(index):
    """Remove one user group by its index. Sidecar-only; live reload."""
    try:
        doc = json.load(open(_kw_user_path(), encoding="utf-8"))
        g = doc.get("groups", [])
        i = int(index)
        if 0 <= i < len(g):
            removed = g.pop(i)
            import safeguard          # v1.13: durable atomic write
            safeguard.atomic_write(_kw_user_path(), json.dumps(doc, indent=2, ensure_ascii=False))
            _load_synonyms()
            return {"ok": True, "removed": removed}
        return {"ok": False, "error": "no such group"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---- per-part tags (added inline via the pencil icon while browsing) -------------------------------
def _part_key(nsn, name):
    n = norm_nsn(nsn) if nsn else None
    return ("nsn:" + n) if n else ("name:" + (name or "").strip().lower())


def user_tags_for(nsn, name):
    """Tags on one part (keyed by NSN, else name). Read-only."""
    key = _part_key(nsn, name)
    try:
        ent = (json.load(open(_kw_user_path(), encoding="utf-8")).get("tags", {}) or {}).get(key) or {}
    except Exception:
        ent = {}
    return {"key": key, "name": ent.get("name", name), "nsn": ent.get("nsn", nsn), "tags": ent.get("tags", [])}


def user_tags_add(nsn, name, tag):
    """Tag a part. Writes the keywords_user.json sidecar and live-reloads search so the tag finds the part."""
    tag = (tag or "").strip()
    if not tag: return {"ok": False, "error": "empty tag"}
    if not (nsn or name): return {"ok": False, "error": "no part given"}
    key = _part_key(nsn, name)
    try:
        try: doc = json.load(open(_kw_user_path(), encoding="utf-8"))
        except Exception: doc = {}
        ent = doc.setdefault("tags", {}).setdefault(key, {"name": name, "nsn": (norm_nsn(nsn) or nsn), "tags": []})
        if name and not ent.get("name"): ent["name"] = name
        if nsn and not ent.get("nsn"): ent["nsn"] = norm_nsn(nsn) or nsn
        if tag.lower() not in [t.lower() for t in ent["tags"]]: ent["tags"].append(tag)
        import safeguard          # v1.13: durable atomic write
        safeguard.atomic_write(_kw_user_path(), json.dumps(doc, indent=2, ensure_ascii=False)); _load_synonyms()
        return {"ok": True, "key": key, "tags": ent["tags"]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def user_tags_remove(nsn, name, tag):
    tag = (tag or "").strip(); key = _part_key(nsn, name)
    try:
        doc = json.load(open(_kw_user_path(), encoding="utf-8"))
        ent = (doc.get("tags", {}) or {}).get(key)
        if ent:
            ent["tags"] = [t for t in ent.get("tags", []) if t.lower() != tag.lower()]
            import safeguard          # v1.13: durable atomic write
            safeguard.atomic_write(_kw_user_path(), json.dumps(doc, indent=2, ensure_ascii=False)); _load_synonyms()
        return {"ok": True, "key": key, "tags": (ent or {}).get("tags", [])}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _ensure_vocab(con):
    """Create an fts5vocab view over pages_fts (additive; powers offline fuzzy matching).
    The ready-flag lives on the CORE module (core._VOCAB_READY) so the regression tests can
    reset it (V._VOCAB_READY = False) exactly as they did against the monolith."""
    if core._VOCAB_READY: return True
    try:
        con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS pages_vocab USING fts5vocab('pages_fts','row')")
        core._VOCAB_READY = True
    except Exception:
        core._VOCAB_READY = False
    return core._VOCAB_READY


def _within1(a, b):
    """True if a and b are within Levenshtein distance 1 (insert/delete/substitute)."""
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


def fuzzy_terms(con, word, cap=4, min_doc=1):
    """Indexed terms within edit-distance 1 of `word` (typo tolerance). Bounded by a prefix scan.
    v1.13.4: rank by document frequency (`doc`, free on pages_vocab's fts5vocab 'row' mode -- was
    selected but never read), most-attested first. min_doc defaults to 1 (no filtering) because
    _alts() below feeds this into actual SEARCH query expansion -- a rare OCR-garbled token (e.g.
    "GASKT" for "gasket") is exactly what lets a fuzzy search still FIND a garbled scanned page, so
    filtering it out there would cost real recall. did_you_mean() below passes min_doc=2 explicitly:
    that path prints the suggestion as text TO a mechanic ("did you mean: ..."), where a one-off
    scan artifact is actively misleading rather than helpful -- a different bar for a different job."""
    w = word.lower()
    if len(w) < 5 or not w.isalpha(): return []
    if not _ensure_vocab(con): return []
    pre = w[:2]
    hi = pre[:-1] + chr(ord(pre[-1]) + 1)
    cands = []
    try:
        for term, doc in con.execute("SELECT term, doc FROM pages_vocab WHERE term>=? AND term<? LIMIT 3000", (pre, hi)):
            if term != w and term.isalpha() and abs(len(term) - len(w)) <= 1 and _within1(w, term) and doc >= min_doc:
                cands.append((doc, term))
    except Exception:
        return []
    cands.sort(key=lambda x: -x[0])          # most-attested (likely real) alternatives first
    return [t for _, t in cands[:cap]]


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


_VEH_CACHE = {"t": 0.0, "v": []}


def _vehicles(con):
    if time.time() - _VEH_CACHE["t"] < 300 and _VEH_CACHE["v"]: return _VEH_CACHE["v"]
    try:
        vs = [r[0] for r in con.execute("SELECT DISTINCT vehicle FROM documents WHERE vehicle IS NOT NULL AND vehicle<>''").fetchall()]
    except sqlite3.OperationalError:
        vs = []
    _VEH_CACHE.update({"t": time.time(), "v": vs}); return vs


_SUGGEST_TBL = {"checked": False, "has": False}


def _has_suggest_terms(con):
    if not _SUGGEST_TBL["checked"]:
        try:
            _SUGGEST_TBL["has"] = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='suggest_terms'").fetchone() is not None
        except Exception: _SUGGEST_TBL["has"] = False
        _SUGGEST_TBL["checked"] = True
    return _SUGGEST_TBL["has"]


_SUGGEST_CACHE = {}; _SUGGEST_ORDER = []      # bounded LRU of recent prefixes (static between maintenance runs)


def suggest(q, limit=8):
    """Offline, fast type-ahead: vehicles + real manual words + previously requested part names, prefix-
    matched. Prefers the precomputed suggest_terms table (a prefix lookup) over a GROUP BY of the FTS vocab,
    and caches recent prefixes. No network; powers the google-style search dropdown."""
    q = (q or "").strip()
    if len(q) < 2: return {"q": q, "suggestions": []}
    ql = q.lower(); ckey = (ql, limit)
    cached = _SUGGEST_CACHE.get(ckey)
    if cached is not None: return cached
    out = []; seen = set()
    def add(text, kind):
        k = (text or "").strip()
        if not k: return
        kk = k.lower()
        if kk in seen: return
        seen.add(kk); out.append({"text": k, "kind": kind})
    con = core.db()
    try:
        for v in _vehicles(con):
            if v.lower().startswith(ql): add(v, "vehicle")
        try:
            for r in con.execute("SELECT DISTINCT item_name FROM request_items WHERE LOWER(item_name) LIKE ? LIMIT 6", (ql + "%",)):
                if r[0]: add(r[0], "part")
        except sqlite3.OperationalError: pass
        pre = re.sub(r"[^a-z0-9]", "", ql)
        if pre:
            if _has_suggest_terms(con):               # fast path: precomputed prefix lookup
                try:
                    for r in con.execute("SELECT term FROM suggest_terms WHERE term GLOB ? ORDER BY freq DESC LIMIT ?", (pre + "*", limit*3)):
                        add(r[0], "term")
                except sqlite3.OperationalError: pass
            elif _ensure_vocab(con):                  # fallback: GROUP BY the FTS vocab (before optimize_index runs)
                try:
                    for r in con.execute("SELECT term, SUM(cnt) c FROM pages_vocab WHERE term GLOB ? GROUP BY term ORDER BY c DESC LIMIT ?", (pre + "*", limit*3)):
                        add(r[0], "term")
                except sqlite3.OperationalError: pass
    finally:
        con.close()
    order = {"vehicle": 0, "part": 1, "term": 2, "nsn": 3}
    out.sort(key=lambda s: order.get(s["kind"], 9))
    res = {"q": q, "suggestions": out[:limit]}
    _SUGGEST_CACHE[ckey] = res; _SUGGEST_ORDER.append(ckey)
    if len(_SUGGEST_ORDER) > 300:
        old = _SUGGEST_ORDER.pop(0); _SUGGEST_CACHE.pop(old, None)
    return res


def build_match(con, q, match_any=False, use_fuzzy=True):
    """Build an FTS5 MATCH expression with synonym/fuzzy expansion, part-number phrase precision,
    and AND (default) or ANY/OR combination.

    v0.97.0 (C22) — explicit operators now pass through:
      "quoted phrase"   -> kept as an exact FTS phrase (adjacency), AND'd with the other terms
      a NEAR b          -> NEAR("a" "b", 10)   (terms within ten tokens of each other)
    Queries without quotes/NEAR behave exactly as before."""
    nearm = re.match(r"^\s*([A-Za-z0-9]+)\s+NEAR\s+([A-Za-z0-9]+)\s*$", q or "")
    if nearm:
        return 'NEAR("%s" "%s", 10)' % (nearm.group(1), nearm.group(2))
    user_phrases = []
    rest = q
    if '"' in (q or ""):
        for p in re.findall(r'"([^"]{2,80})"', q)[:2]:
            words = re.findall(r"[A-Za-z0-9]+", p)
            if len(words) >= 1:
                user_phrases.append('"' + " ".join(words) + '"')
        rest = re.sub(r'"[^"]*"?', " ", q)
    toks = re.findall(r"[A-Za-z0-9]+", rest)[:6]
    if not toks and not user_phrases: return None
    groups = [_alts(con, t, idx == len(toks) - 1, use_fuzzy) for idx, t in enumerate(toks)]
    if match_any:
        body = " OR ".join(g[1:-1] for g in groups) if groups else ""
        if user_phrases:
            body = (" OR ".join(user_phrases) + ((" OR " + body) if body else ""))
        return body
    expr = " AND ".join(groups) if groups else ""
    # Part #, FIG #, callout codes (e.g. 5330-01-186, 12-345): require the parts to be adjacent for precision.
    phrases = []
    for c in re.findall(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+){1,}", rest)[:2]:
        parts = re.findall(r"[A-Za-z0-9]+", c)
        if len(parts) >= 2: phrases.append('"' + " ".join(parts) + '"')
    if phrases:
        expr = "(" + expr + ") AND (" + " OR ".join(phrases) + ")" if expr else "(" + " OR ".join(phrases) + ")"
    if user_phrases:
        up = " AND ".join(user_phrases)
        expr = ("(" + expr + ") AND " + up) if expr else up
    return expr


def search(q, limit=25, mode=None, match_any=False, use_fuzzy=True, tm=None, vehicle=None, nsn=None):
    """v1.13 (#11/#15): optional kwargs tm/vehicle/nsn are the fielded operators (parsed upstream by
    parse_operators in the route). All default None so every existing caller behaves identically.
    tm/vehicle filter the documents join (parameterized LIKE); nsn: with NO free text routes into the
    existing exact-NSN pipeline, otherwise it becomes a digits-normalized filter on d.nsn."""
    q = (q or "").strip()
    flt_where, flt_args = _doc_filters(tm=tm, vehicle=vehicle, nsn=(nsn if q else None))
    if nsn and not q:
        q = str(nsn).strip()          # bare nsn:<value> -> the normal last-4 / full-NSN routing below
    if not q:
        if not flt_where:
            return []
        # operators only (e.g. vehicle:HMMWV tm:9-2320): answer with the matching documents.
        con = core.db()
        rows = [dict(r) for r in con.execute(
            "SELECT d.id AS doc_id, d.vehicle, d.tm_number, d.nsn, d.title, d.page_count, 1 AS page_number, "
            "'document matches your tm:/vehicle:/nsn: filters' AS snip, 'meta' AS source "
            "FROM documents d WHERE 1=1" + flt_where + " ORDER BY d.vehicle, d.tm_number LIMIT ?",
            flt_args + [limit]).fetchall()]
        con.close(); return rows
    con = core.db()
    # 1) "Last 4" lookup -- exactly four digits -> match the document/end-item COVER NSN ending in them.
    if mode != "text" and re.fullmatch(r"\d{4}", q):
        rows = [dict(r) for r in con.execute(
            "SELECT d.id AS doc_id, d.vehicle, d.tm_number, d.nsn, d.title, d.page_count, 1 AS page_number, "
            "'cover / end-item NSN ending in ' || ? AS snip, 'meta' AS source "
            "FROM documents d WHERE d.nsn IS NOT NULL AND d.nsn LIKE '%'||?" + flt_where +
            " ORDER BY d.vehicle, d.tm_number LIMIT ?",
            [q, q] + flt_args + [limit]).fetchall()]
        for r in rows:
            r["last4_query"] = q
            r["nsn_kind"] = core.nsn_kind(r["nsn"]) if r.get("nsn") else "part"
        con.close(); return rows
    # 2) Full NSN -> exact-first NSN search (part or whole-vehicle)
    nsn = norm_nsn(q)
    if nsn and len(re.sub(r"\D", "", q)) >= 11:
        aliases = core.nsn_aliases(nsn)                   # confirmed-interchangeable equivalents (grounded)
        phrase = " OR ".join('"' + a.replace("-", " ") + '"' for a in aliases)
        try: rows = _meta_rows(con, "pages_fts MATCH ?" + flt_where, [phrase] + flt_args, limit)
        except sqlite3.OperationalError: rows = []
        qmarks = ",".join("?" * len(aliases))
        cover = [dict(r) for r in con.execute(
            "SELECT d.id AS doc_id, d.vehicle, d.tm_number, d.nsn, d.title, 1 AS page_number, "
            "'cover/end-item NSN match' AS snip, 'meta' AS source FROM documents d WHERE d.nsn IN (" + qmarks + ")"
            + flt_where + " LIMIT 10", aliases + flt_args).fetchall()]
        seen = set(); out = []
        for r in cover + rows:
            r["nsn_query"] = nsn; r["nsn_kind"] = core.nsn_kind(nsn)
            if len(aliases) > 1: r["aliases"] = aliases
            k = (r["doc_id"], r["page_number"])
            if k in seen: continue
            seen.add(k); out.append(r)
        con.close(); return out[:limit]
    # 3) Enhanced predictive keyword search (synonyms + part#/FIG + ANY/OR + fuzzy)
    match = build_match(con, q, match_any, use_fuzzy)
    if not match: con.close(); return []
    try: rows = _meta_rows(con, "pages_fts MATCH ?" + flt_where, [match] + flt_args, limit)
    except sqlite3.OperationalError:
        # v1.13: the LIKE fallback (only reached when a MATCH expr is malformed) is a leading-wildcard
        # scan of the whole pages table, so cap the scan hard and skip it for trivially short queries --
        # a rare-term scan-to-limit on a 3.65 GB table is a soft-DoS otherwise.
        if len((q or "").strip()) < 2:
            con.close(); return []
        like = "%" + q + "%"
        try:
            rows = [dict(r) for r in con.execute(
                "SELECT d.id AS doc_id,d.vehicle,d.tm_number,d.nsn,d.title,p.page_number,substr(p.body_text,1,200) AS snip,p.source "
                "FROM pages p JOIN documents d ON d.id=p.document_id WHERE p.body_text LIKE ?" + flt_where + " LIMIT ?",
                [like] + flt_args + [min(limit, 100)]).fetchall()]
        except sqlite3.OperationalError:
            rows = []
    # Nomenclature widening: if the catalog-style query is sparse, also try comma-inverted /
    # abbreviation-expanded variants and append unseen hits (additive — never removes results).
    if len(rows) < 3:
        seen = {(r["doc_id"], r["page_number"]) for r in rows}
        for variant in normalize_nomenclature(q):
            vm = build_match(con, variant, match_any, use_fuzzy)
            if not vm: continue
            try: extra = _meta_rows(con, "pages_fts MATCH ?" + flt_where, [vm] + flt_args, limit)
            except sqlite3.OperationalError: extra = []
            for r in extra:
                k = (r["doc_id"], r["page_number"])
                if k not in seen: rows.append(r); seen.add(k)
    # v0.97.0 (C18): exact-match boost — a verbatim hit of the whole query, or a row whose NSN is
    # cataloged under the query as an exact part number, floats above plain keyword hits. Additive
    # flags only; the FTS rank order is preserved within each band (stable sort).
    ql = q.lower().strip()
    exact_nsns = set()
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9\-]{4,}", q.strip() or ""):
        try:
            for r2 in con.execute("SELECT DISTINCT nsn FROM parts WHERE part_number = ? COLLATE NOCASE "
                                  "AND COALESCE(nsn,'')<>'' LIMIT 20", (q.strip(),)):
                exact_nsns.add(r2[0])
        except sqlite3.OperationalError:
            pass
    for r in rows:
        snip = (r.get("snip") or "").lower().replace("<<", "").replace(">>", "")
        if ql and len(ql) >= 4 and ql in snip:
            r["exact"] = True
        if exact_nsns and (r.get("nsn") or "").strip() in exact_nsns:
            r["exact"] = True; r["part_number_match"] = q.strip()
    # Learned ranking: float parts you've successfully requested before to the top (stable).
    pop = core.popular_nsns(con)
    if pop:
        for r in rows:
            if (r.get("nsn") or "").strip() in pop: r["boosted"] = True
    rows.sort(key=lambda r: (0 if r.get("exact") else 1, 0 if r.get("boosted") else 1))
    con.close(); return rows


def did_you_mean(q, max_suggestions=3):
    """v0.97.0 (C20): zero-result suggestions, fully offline. Each long alpha token is replaced
    with its closest indexed term (edit distance 1, via the FTS vocab); multi-word queries also
    fall back to their most specific single token. Read-only; bounded.
    v1.13.4: min_doc=2 -- this string is shown directly to a mechanic ("did you mean: ..."), so a
    one-off OCR-garbled vocab entry (e.g. "braae") must not outrank/replace a real suggestion just
    because of prefix-scan order (see fuzzy_terms() docstring for why _alts()'s search-expansion
    path, unlike this one, intentionally keeps min_doc=1)."""
    toks = re.findall(r"[A-Za-z0-9]+", (q or ""))
    if not toks: return []
    out = []
    con = core.db()
    try:
        for i, t in enumerate(toks):
            if len(t) < 5 or not t.isalpha(): continue
            for alt in fuzzy_terms(con, t, cap=2, min_doc=2):
                cand = " ".join(toks[:i] + [alt] + toks[i + 1:])
                if cand.lower() != (q or "").lower() and cand not in out:
                    out.append(cand)
                if len(out) >= max_suggestions: break
            if len(out) >= max_suggestions: break
    finally:
        con.close()
    if len(toks) > 1 and len(out) < max_suggestions:
        # "fewer words" fallback: offer the longest token that actually HITS the index alone.
        con = core.db()
        try:
            for t in sorted(toks, key=len, reverse=True):
                if len(t) < 5: continue
                try:
                    hit = con.execute("SELECT 1 FROM pages_fts WHERE pages_fts MATCH ? LIMIT 1",
                                      ('"%s"' % t.replace('"', ''),)).fetchone()
                except sqlite3.OperationalError:
                    hit = None
                if hit and t.lower() != (q or "").lower() and t not in out:
                    out.append(t); break
        finally:
            con.close()
    return out


def find_in_doc(doc_id, q, limit=80):
    """In-document find (Ctrl+F across a whole manual): pages of ONE document whose text contains the
    term, with per-page match counts + a snippet. Scoped to the doc, so it's fast. Read-only."""
    q = (q or "").strip()
    try: doc_id = int(doc_id)
    except Exception: return {"doc": doc_id, "q": q, "matches": []}
    if not q: return {"doc": doc_id, "q": q, "matches": []}
    con = core.db(); ql = q.lower(); like = "%" + ql + "%"
    try:
        rows = con.execute("SELECT page_number, body_text FROM pages WHERE document_id=? AND body_text IS NOT NULL "
                           "AND LOWER(body_text) LIKE ? ORDER BY page_number LIMIT ?", (doc_id, like, limit)).fetchall()
    except sqlite3.OperationalError:
        rows = []
    con.close()
    out = []
    for r in rows:
        bt = r["body_text"] or ""; low = bt.lower(); cnt = low.count(ql)
        i = low.find(ql); s = max(0, i - 40)
        snip = ("…" if s > 0 else "") + re.sub(r"\s+", " ", bt[s:i + len(q) + 40]).strip() + "…"
        out.append({"page": r["page_number"], "count": cnt, "snippet": snip})
    return {"doc": doc_id, "q": q, "pages": len(out), "total": sum(m["count"] for m in out), "matches": out}
