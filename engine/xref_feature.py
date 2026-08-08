#!/usr/bin/env python3
"""THE VIEWER -- cross-reference resolver: one unified, provenance-tracked part record.

Resolves a part number (or NSN) against everything we hold OFFLINE and returns a single record:
  official name (FLIS) + the OCR'd name kept visible · CAGEC/manufacturer · the vehicle(s) it fits ·
  interchangeable / superseded NSNs · the cited figure (breakdown image) · links to schematic/procedure/tags.

Every field carries a SOURCE + the engine carries a CONFIDENCE, and FLIS-vs-OCR disagreements are FLAGGED
(FLIS preferred, OCR shown) -- nothing is silently changed. Pure offline (index + ref_nsn FLIS enrichment +
correlations.db platform map + the rpstl sidecar). Read-only (R1/R6). `core` injected by viewer_app.
"""
import os, re, sqlite3, json

core = None
NSN_RE = re.compile(r"\b(\d{4})-?(\d{2})-?(\d{3})-?(\d{4})\b")

def _sidecar_json(name):
    p = os.path.join(os.path.dirname(core.DB_PATH), name)
    if not os.path.exists(p): return {}
    try:
        with open(p, "r", encoding="utf-8") as f: return json.load(f) or {}
    except Exception:
        return {}


def _norm_nsn(s):
    m = NSN_RE.search((s or "").strip())
    return "%s-%s-%s-%s" % (m.group(1), m.group(2), m.group(3), m.group(4)) if m else None

def _niin(nsn):
    """v1.13: delegates to patterns.niin_of, the canonical NIIN extractor (R13: ambiguous 10-12 or
    <9 digit fragments are refused ('') instead of truncated/passed through as a wrong key)."""
    import patterns
    return patterns.niin_of(nsn)

def _corr():
    p = os.path.join(os.path.dirname(core.DB_PATH), "correlations.db")
    if not os.path.exists(p): return None
    try:
        c = sqlite3.connect("file:%s?mode=ro" % p, uri=True); c.row_factory = sqlite3.Row; return c
    except Exception:
        return None

def _rpstl():
    p = os.path.join(os.path.dirname(core.DB_PATH), "rpstl.db")
    if not os.path.exists(p): return None
    try:
        c = sqlite3.connect("file:%s?mode=ro" % p, uri=True); c.row_factory = sqlite3.Row; return c
    except Exception:
        return None

_VEH_JUNK = re.compile(r"\.pdf$|^TM\b|^WORK$|^\W*$|ALL$", re.I)

def _clean_vehicles(s):
    """nsn_platforms.vehicles is a pipe-joined, noisy string (real names + filenames + junk). Keep plausible
    vehicle/end-item names."""
    out = []
    for tok in (s or "").split("|"):
        t = tok.strip()
        if not t or len(t) < 2: continue
        if _VEH_JUNK.search(t): continue
        if t.lower().endswith(".pdf"): continue
        if t not in out: out.append(t)
    return out[:20]


def vehicles_for(nsn):
    c = _corr()
    if not c: return []
    try:
        r = c.execute("SELECT vehicles FROM nsn_platforms WHERE nsn=?", (nsn,)).fetchone()
        return _clean_vehicles(r["vehicles"]) if r else []
    except Exception:
        return []
    finally:
        c.close()


def interchangeable_for(nsn):
    c = _corr()
    if not c: return []
    try:
        r = c.execute("SELECT variants FROM niin_aliases WHERE niin=?", (_niin(nsn),)).fetchone()
        if not r: return []
        return [v.strip() for v in (r["variants"] or "").split("|") if v.strip() and v.strip() != nsn][:12]
    except Exception:
        return []
    finally:
        c.close()


def superseded_by(nsn):
    c = _corr()
    if not c: return None
    try:
        r = c.execute("SELECT current_token FROM supersession_held WHERE old_nsn=?", (nsn,)).fetchone()
        return r["current_token"] if r else None
    except Exception:
        return None
    finally:
        c.close()


def _flis(con, nsn):
    try:
        r = con.execute("SELECT item_name, part_no, cagec, substitutes FROM ref_nsn WHERE nsn=? LIMIT 1",
                        (nsn,)).fetchone()
        return dict(r) if r else None
    except Exception:
        return None


def _rpstl_row(pn=None, nsn=None):
    c = _rpstl()
    if not c: return None
    try:
        if pn:
            key = re.sub(r"\s+", "", pn).upper()
            r = c.execute("SELECT * FROM parts_rows WHERE pn_norm=? ORDER BY confidence DESC LIMIT 1", (key,)).fetchone()
            if not r:
                base = re.sub(r"[-/][0-9A-Z]{1,4}$", "", key) or key
                r = c.execute("SELECT * FROM parts_rows WHERE pn_base=? ORDER BY confidence DESC LIMIT 1", (base,)).fetchone()
        else:
            r = c.execute("SELECT * FROM parts_rows WHERE nsn=? ORDER BY confidence DESC LIMIT 1", (nsn,)).fetchone()
        return dict(r) if r else None
    except Exception:
        return None
    finally:
        c.close()


def part_record(key):
    """Resolve a PART NUMBER or NSN into the unified, provenance-tracked record."""
    key = (key or "").strip()
    if not key:
        return {"found": False}
    as_nsn = _norm_nsn(key)
    row = _rpstl_row(nsn=as_nsn) if as_nsn else _rpstl_row(pn=key)
    nsn = as_nsn or (row.get("nsn") if row else None)
    ocr_name = row.get("nomenclature") if row else None
    doc_id = row.get("doc_id") if row else None
    page = row.get("page") if row else None
    fig = row.get("fig_no") if row else None
    item = row.get("item") if row else None
    cagec = row.get("cagec") if row else None
    part_no = row.get("part_no") if row else (None if as_nsn else key)

    prov = {}; conf = 0.3 if (row or nsn) else 0.0
    # NSN recovery from PUB LOG (build_xref -> pn_nsn.json: part# -> NIIN), when OCR lost the NSN
    if not nsn and part_no:
        niin = _sidecar_json("pn_nsn.json").get(re.sub(r"\s+", "", part_no).upper())
        if niin:
            con0 = core.db()
            try:
                r = con0.execute("SELECT nsn FROM ref_nsn WHERE replace(nsn,'-','') LIKE ? LIMIT 1",
                                 ("%" + niin,)).fetchone()
                if r and r["nsn"]: nsn = r["nsn"]; prov["nsn"] = "publog(PN+CAGEC)"; conf += 0.2
            except Exception: pass
            finally:
                try: con0.close()
                except Exception: pass
    flis = None
    con = core.db()
    try:
        if nsn:
            flis = _flis(con, nsn)
    finally:
        try: con.close()
        except Exception: pass

    # name: prefer FLIS, keep OCR visible, flag conflict
    name = ocr_name; conflict = False; name_src = "ocr"
    if flis and flis.get("item_name"):
        name = flis["item_name"]; name_src = "flis"; conf += 0.3
        if ocr_name and ocr_name.strip().upper().replace(" ", "") != flis["item_name"].strip().upper().replace(" ", ""):
            conflict = True
    prov["nomenclature"] = name_src
    if flis and flis.get("cagec") and not cagec:
        cagec = flis["cagec"]; prov["cagec"] = "flis"
    elif cagec:
        prov["cagec"] = "rpstl"
    if not part_no and flis and flis.get("part_no"):
        part_no = flis["part_no"]; prov["part_no"] = "flis"

    vehicles = vehicles_for(nsn) if nsn else []
    if vehicles: conf += 0.3; prov["vehicles"] = "correlations(nsn_platforms)"
    inter = interchangeable_for(nsn) if nsn else []
    if inter: prov["interchangeable"] = "correlations(niin_aliases)"
    superseded = superseded_by(nsn) if nsn else None
    if superseded: prov["superseded_by"] = "correlations(supersession)"

    manufacturer = None
    if cagec:
        manufacturer = _sidecar_json("cage.json").get(cagec.upper())
        if manufacturer: prov["manufacturer"] = "publog(P_CAGE)"
    # X4: cached PUBLIC online enrichment (offline read of the sidecar; never fetched at serve time)
    colloquial = None
    if nsn:
        oc = _sidecar_json("xref_online.json").get(nsn) or {}
        colloquial = oc.get("colloquial")
        if colloquial: prov["colloquial"] = "online(cached)"
        if not manufacturer and oc.get("manufacturer"):
            manufacturer = oc["manufacturer"]; prov["manufacturer"] = "online(cached)"
    image_url = ("/figcrop?doc=%s&page=%s&dpi=150" % (doc_id, page)) if (doc_id and page) else None
    callout_url = ("/api/callout_crop?doc=%s&page=%s&item=%s" % (doc_id, page, item)) if (doc_id and page and item) else None
    conf = round(min(conf, 1.0), 2)

    return {"found": bool(nsn or row), "query": key, "part_no": part_no, "cagec": cagec,
            "manufacturer": manufacturer, "nsn": nsn,
            "item": item, "fig_no": fig, "doc_id": doc_id, "page": page,
            "nomenclature": name, "ocr_nomenclature": ocr_name, "name_conflict": conflict,
            "colloquial": colloquial,
            "vehicles": vehicles, "interchangeable": inter, "superseded_by": superseded,
            "image_url": image_url, "callout_url": callout_url,
            "links": {"dossier": ("/dossier?q=%s" % nsn) if nsn else None,
                       "schematics": ("/schematics?q=%s" % (vehicles[0])) if vehicles else None,
                       "procedure": ("/procedure?q=%s" % (name or "")) if name else None,
                       "lookalike": ("/partdiff?q=%s" % nsn) if nsn else None},
            "confidence": conf, "provenance": prov}


def coverage():
    """How resolved is the corpus: rows total, with NSN, with a vehicle, FLIS-named."""
    c = _rpstl()
    if not c:
        return {"built": False, "note": "rpstl.db not built yet — run BUILD-RPSTL.bat"}
    try:
        total = c.execute("SELECT COUNT(*) FROM parts_rows").fetchone()[0]
        with_nsn = c.execute("SELECT COUNT(*) FROM parts_rows WHERE nsn IS NOT NULL AND nsn<>''").fetchone()[0]
        with_pn = c.execute("SELECT COUNT(*) FROM parts_rows WHERE part_no IS NOT NULL AND part_no<>''").fetchone()[0]
        low = c.execute("SELECT COUNT(*) FROM parts_rows WHERE confidence <= 0.6").fetchone()[0]
        validated = c.execute("SELECT COUNT(*) FROM parts_rows WHERE validated=1").fetchone()[0] \
            if c.execute("SELECT COUNT(*) FROM pragma_table_info('parts_rows') WHERE name='validated'").fetchone()[0] else 0
    except Exception:
        total = with_nsn = with_pn = low = validated = 0
    finally:
        c.close()
    pct = (lambda n: round(100.0 * n / total) if total else 0)
    return {"built": True, "rows": total, "with_nsn": with_nsn, "with_part_no": with_pn,
            "flis_validated": validated, "in_review": low,
            "pct_with_nsn": pct(with_nsn), "pct_validated": pct(validated), "pct_in_review": pct(low)}
