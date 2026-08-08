#!/usr/bin/env python3
"""THE VIEWER -- RPSTL parts-list row parser + part-number correlation.

An RPSTL (Repair Parts & Special Tools List) page pairs an exploded-view FIGURE with a parts LIST whose rows
map:  ITEM# -> SMR -> NSN -> CAGEC -> PART NUMBER -> NOMENCLATURE -> QTY.  This parses those rows from the OCR
text (multi-signal column detection, confidence-scored) so a PART NUMBER resolves directly to its item, its
NSN, its real nomenclature, and -- crucially -- its figure (the correlative breakdown image).

Rows live in a SIDECAR (index/rpstl.db); the main index is never written (R1/R6). A manual override sidecar
(index/rpstl_override.json) fixes low-confidence rows. FLIS validation (NSN -> official INC name) is applied by
the host builder via `core`. Stdlib only, RPS-safe. `core` injected by viewer_app.
"""
import os, re, sqlite3, json

core = None

NSN_RE = re.compile(r"\b(\d{4})-?(\d{2})-?(\d{3})-?(\d{4})\b")
# SMR source-maintenance-recoverability code: 5 (sometimes 6) letters, e.g. PAOZZ, PAFZZ, XBOZZ, MOFFF.
SMR_RE = re.compile(r"\b([A-KM-Z][A-Z]{1}[A-Z0-9]{3,4})\b")
# CAGEC: 5-char alphanumeric Commercial And Government Entity Code (mostly digits, e.g. 19207, 81337, 0VGW1).
CAGEC_RE = re.compile(r"\b([0-9A-Z]{5})\b")
# Part number: has a digit, length >=4, may include dashes/letters/slashes; not purely a 5-digit CAGEC.
PN_RE = re.compile(r"\b([A-Z0-9][A-Z0-9\-/]{3,24})\b", re.I)
ITEM_RE = re.compile(r"^\s*(\d{1,3})\b")
_SMR_STOP = {"WASHER", "SCREW", "VALVE", "PLATE", "COVER", "BRACK"}   # avoid matching words as SMR


def norm_pn(pn):
    """Canonical part-number key: upper, strip spaces; keep dashes. Also a 'base' with trailing variant dropped."""
    p = re.sub(r"\s+", "", (pn or "")).upper()
    return p


def pn_base(pn):
    """Drop a trailing variant suffix (e.g. -010, -010X, REV A) so 12420572-010X groups with 12420572."""
    p = norm_pn(pn)
    return re.sub(r"[-/][0-9A-Z]{1,4}$", "", p) or p


def _is_nomen(tok):
    # nomenclature tokens are mostly letters/commas (HOSE,NONMETALLIC), allow & and .
    letters = sum(c.isalpha() for c in tok)
    return letters >= 3 and letters >= 0.6 * len(tok)


def parse_line(line):
    """Parse one parts-list line into a row dict with a confidence 0..1. Returns None if clearly not a row."""
    s = re.sub(r"\s+", " ", (line or "").strip())
    if len(s) < 8:
        return None
    row = {"item": None, "smr": None, "nsn": None, "cagec": None, "part_no": None,
           "nomenclature": None, "qty": None}
    # NSN
    m = NSN_RE.search(s)
    if m:
        row["nsn"] = "%s-%s-%s-%s" % (m.group(1), m.group(2), m.group(3), m.group(4))
    # item number (leading)
    im = ITEM_RE.match(s)
    if im:
        row["item"] = int(im.group(1))
    # SMR
    for sm in SMR_RE.finditer(s):
        tok = sm.group(1)
        if tok[:5] not in _SMR_STOP and not tok.isdigit():
            row["smr"] = tok; break
    # CAGEC: a 5-char code that is NOT part of the NSN digits; prefer one near the part number
    cands = [c.group(1) for c in CAGEC_RE.finditer(s)]
    nsn_digits = "".join(ch for ch in (row["nsn"] or "") if ch.isdigit())
    for c in cands:
        if c == row.get("smr"):
            continue
        if c.isdigit() and c in nsn_digits:    # skip 5-digit runs that belong to the NSN
            continue
        row["cagec"] = c; break
    # part number: the token after the CAGEC with a digit, not nsn/cagec/smr
    used = {row.get("cagec"), row.get("smr")}
    pn = None
    for pm in PN_RE.finditer(s):
        tok = pm.group(1).upper()
        if tok in used: continue
        if not any(ch.isdigit() for ch in tok): continue
        if row["nsn"] and tok.replace("-", "") in nsn_digits: continue
        if len(tok) == 5 and tok.isdigit(): continue       # looks like a CAGEC
        if row["item"] is not None and tok == str(row["item"]): continue
        pn = pm.group(1); break
    row["part_no"] = pn
    # nomenclature: letter-rich tokens, EXCLUDING the codes we already identified (SMR/CAGEC/PN/NSN/item/qty)
    used_toks = set(t for t in (row.get("smr"), row.get("cagec"), (row.get("part_no") or "").upper()) if t)
    if row.get("item") is not None: used_toks.add(str(row["item"]))
    if row.get("qty") is not None: used_toks.add(str(row["qty"]))
    def _is_used(tt):
        u = tt.upper().strip(",.;")
        if u in used_toks: return True
        d = tt.replace("-", "")
        if row["nsn"] and d and d.isdigit() and d in nsn_digits: return True
        return False
    toks = s.split(" ")
    nom_toks = [tt for tt in toks if _is_nomen(tt) and not _is_used(tt)]
    if nom_toks:
        row["nomenclature"] = re.sub(r"\s+", " ", " ".join(nom_toks))[:80].strip(" ,.-")
    # qty: a trailing small integer
    qm = re.search(r"(\d{1,3})\s*$", s)
    if qm and (row["item"] is None or int(qm.group(1)) != row["item"]):
        row["qty"] = int(qm.group(1))
    # confidence: how many of the load-bearing fields we got
    got = sum(1 for k in ("item", "nsn", "cagec", "part_no", "nomenclature") if row.get(k))
    row["confidence"] = round(got / 5.0, 2)
    # a row needs at least a part number OR an NSN to be useful
    if not row["part_no"] and not row["nsn"]:
        return None
    return row


_FIG_RE = re.compile(r"\bFIG(?:URE)?\.?\s*([0-9]+(?:-[0-9]+)?)", re.I)


def parse_page(text, doc_id=None, page=None):
    """Parse all parts-list rows on a page; attach the page's figure number when present."""
    fig = None
    fm = _FIG_RE.search(text or "")
    if fm: fig = fm.group(1)
    rows = []
    for ln in re.split(r"\r?\n", text or ""):
        r = parse_line(ln)
        if r:
            r["fig_no"] = fig; r["doc_id"] = doc_id; r["page"] = page
            rows.append(r)
    return rows


# ---- sidecar read side (used by the running app) -------------------------------------------------
def _db_path():
    return os.path.join(os.path.dirname(core.DB_PATH), "rpstl.db")

def _override_path():
    return os.path.join(os.path.dirname(core.DB_PATH), "rpstl_override.json")

def _connect_ro():
    p = _db_path()
    if not os.path.exists(p):
        return None
    try:
        c = sqlite3.connect("file:%s?mode=ro" % p, uri=True); c.row_factory = sqlite3.Row; return c
    except Exception:
        return None

def load_overrides():
    p = _override_path()
    if not os.path.exists(p): return {}
    try:
        with open(p, "r", encoding="utf-8") as f: return json.load(f) or {}
    except Exception:
        return {}

def save_override(pn, fields, by=""):
    import time
    p = _override_path(); blob = {}
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f: blob = json.load(f) or {}
        except Exception: blob = {}
    key = norm_pn(pn)
    rec = {k: fields[k] for k in ("nsn", "nomenclature", "cagec", "item", "fig_no", "doc_id", "page") if k in fields}
    rec["by"] = by or ""; rec["at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    blob[key] = rec
    import safeguard; safeguard.atomic_write(p, json.dumps(blob, indent=2))          # v1.13: fsync + retry
    return {"ok": True, "part_no": key}

def lookup(pn, cagec=None, limit=20):
    """Resolve a PART NUMBER to its RPSTL row(s) (+ figure), honoring overrides + variant grouping."""
    key = norm_pn(pn)
    if not key:
        return {"found": False, "query": pn}
    ov = load_overrides().get(key)
    con = _connect_ro()
    rows = []
    if con is not None:
        try:
            q = "SELECT * FROM parts_rows WHERE pn_norm=?"; args = [key]
            r = con.execute(q, args).fetchall()
            if not r:                                   # variant grouping: match the base then suffixed
                r = con.execute("SELECT * FROM parts_rows WHERE pn_base=? ORDER BY confidence DESC LIMIT ?",
                                [pn_base(pn), limit]).fetchall()
            if cagec:
                r = [x for x in r if (x["cagec"] or "").upper() == cagec.upper()] or r
            rows = [dict(x) for x in r]
        except Exception:
            rows = []
        con.close()
    if ov:
        rows.insert(0, {**ov, "part_no": key, "pn_norm": key, "confidence": 1.0, "overridden": True})
    if not rows:
        return {"found": False, "query": key}
    best = rows[0]
    img = None
    if best.get("doc_id") and best.get("page"):
        img = "/figcrop?doc=%s&page=%s&dpi=150" % (best["doc_id"], best["page"])
    callout = None
    if best.get("doc_id") and best.get("page") and best.get("item"):
        callout = "/api/callout_crop?doc=%s&page=%s&item=%s" % (best["doc_id"], best["page"], best["item"])
    return {"found": True, "query": key, "part_no": best.get("part_no"), "cagec": best.get("cagec"),
            "nsn": best.get("nsn"), "item": best.get("item"), "nomenclature": best.get("nomenclature"),
            "fig_no": best.get("fig_no"), "doc_id": best.get("doc_id"), "page": best.get("page"),
            "confidence": best.get("confidence"), "image_url": img, "callout_url": callout,
            "variants": rows[:limit]}


def review(limit=200, max_conf=0.6):
    """Low-confidence rows for the review/override UI."""
    con = _connect_ro()
    if con is None:
        return {"total": 0, "items": [], "note": "rpstl.db not built yet — run BUILD-RPSTL.bat"}
    try:
        rows = con.execute("SELECT * FROM parts_rows WHERE confidence <= ? ORDER BY confidence, pn_norm LIMIT ?",
                           [max_conf, limit]).fetchall()
        items = [dict(r) for r in rows]
    except Exception:
        items = []
    con.close()
    return {"total": len(items), "items": items}
