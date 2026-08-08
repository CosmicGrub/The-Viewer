"""publogdiff.py -- authoritative look-alike intelligence on top of the PUBLOG/FLIS sidecar. Turns "these two
parts share a name" into a grounded, decisive answer:

  * compare(a, b)         -- align the two NIINs' item CHARACTERISTICS by MRC, flag the rows that DIFFER,
                             and score a fit-fingerprint % (bundle 1).
  * interchangeability(a,b)- GREEN fully interchangeable (shared I&S family / related NSN) / AMBER one-way
                             substitute / RED not interchangeable, with the reason (bundle 2).
  * substitutes(niin)     -- NSNs you can use instead (I&S family + related + supersession) (bundle 2).
  * supersession(niin)    -- replaced-by chain + AAC (Acquisition Advice Code) obsolescence flag (bundle 2).
  * reference_confidence(niin) -- decode each part number's RNCC/RNVC: exact vs 'similar, may differ' (bundle 3).
  * vendor_status(niin)   -- CAGE active/inactive per part number (bundle 3).
  * nicknames(niin|inc)   -- colloquial + related-INC names, and a CLASH warning when a nickname maps to
                             more than one official item (bundle 4).
  * tech_docs(niin)       -- TECH_DOC_NBR phrases -> the manual(s) that reference this part (bundle 4 crosslink).

Read-only over index/publog.db. Every function accepts an explicit db_path (defaults to the live sidecar) so
it degrades gracefully and is unit-testable. No links; fully offline (R11)."""

from __future__ import annotations
import os, re, sqlite3


def _default_db():
    try:
        import publog
        return publog.db_path()
    except Exception:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "index", "publog.db")


def _niin(s):
    """v1.13: delegates to patterns.niin_of, the canonical NIIN extractor (R13: partial digit
    fragments are refused instead of zero-padded into a guessed key)."""
    import patterns
    return patterns.niin_of(s)


def _con(db_path=None):
    p = db_path or _default_db()
    if not (p and os.path.exists(p)):
        return None
    con = sqlite3.connect("file:%s?mode=ro" % p, uri=True)
    con.row_factory = sqlite3.Row
    return con


def available(db_path=None):
    p = db_path or _default_db()
    return bool(p and os.path.exists(p) and os.path.getsize(p) > 0)


# ---- code decodes (conservative; unknown codes fall back to the raw value) ------------------------
_RNVC = {"1": "exact — single interchangeable item", "2": "similar — item may differ (verify!)",
         "9": "reference covers multiple items"}
_RNCC = {"3": "primary/identifying number", "5": "secondary / informational", "6": "vendor design-control",
         "1": "manufacturer part number", "4": "specification/standard", "C": "vendor item drawing",
         "D": "source-control drawing"}
# AAC (Acquisition Advice Code): terminal/obsolescent families flagged. Common procurable = B,C,D,G,J...
_AAC_TERMINAL = set("HJKLOVYZ")   # phased-out / terminal / no-longer-procured families (per FLIS)
_AAC = {"C": "stocked, procurable", "D": "stocked (spec/std item)", "B": "procurable",
        "G": "stocked, procurable", "H": "terminal — no replacement", "J": "terminal item",
        "K": "terminal item", "L": "local purchase", "O": "terminal — obsolete", "Y": "terminal",
        "Z": "terminal (insurance item)", "V": "terminal"}
_ISC = {"1": "approved item (preferred/standard)", "2": "approved substitute",
        "3": "non-standard, permit use", "4": "non-standard", "C": "collaborative decision"}


def _decode(d, k):
    k = (k or "").strip().upper()
    return d.get(k, ("code %s" % k) if k else "")


def _charx(con, niin, cap=200):
    rows = con.execute("SELECT mrc,requirement,reply FROM charx WHERE niin=? LIMIT ?", (niin, cap)).fetchall()
    out = {}
    for r in rows:
        key = (r["requirement"] or r["mrc"] or "").strip()
        if key:
            out[key] = (r["reply"] or "").strip()
    return out


def compare(a, b, db_path=None):
    """Bundle 1: characteristics diff + fit-fingerprint % between two NIIN/NSNs."""
    con = _con(db_path)
    if con is None:
        return {"available": False}
    na, nb = _niin(a), _niin(b)
    try:
        ca, cb = _charx(con, na), _charx(con, nb)
        names = {}
        for x in (na, nb):
            r = con.execute("SELECT fsc,item_name FROM nsn WHERE niin=? LIMIT 1", (x,)).fetchone()
            names[x] = (r["item_name"] if r else "") or ""
        keys = sorted(set(ca) | set(cb))
        rows, same, differ = [], 0, 0
        for k in keys:
            va, vb = ca.get(k, ""), cb.get(k, "")
            d = (va or "") != (vb or "")
            both = bool(va) and bool(vb)
            if both:
                if d:
                    differ += 1
                else:
                    same += 1
            rows.append({"characteristic": k, "a": va, "b": vb, "differ": d, "both": both})
        comparable = same + differ
        sim = round(100.0 * same / comparable) if comparable else None
        return {"available": True, "a": {"niin": na, "item_name": names.get(na, "")},
                "b": {"niin": nb, "item_name": names.get(nb, "")},
                "rows": rows, "same": same, "differ": differ, "comparable": comparable,
                "similarity_pct": sim,
                "differing": [r["characteristic"] for r in rows if r["differ"] and r["both"]]}
    finally:
        con.close()


def _isc_family(con, niin):
    """NIINs in the same standardization decision (shared related_nsn / ISC linkage)."""
    fam = set()
    for r in con.execute("SELECT related_nsn,isc FROM stdz WHERE niin=?", (niin,)).fetchall():
        rn = _niin(r["related_nsn"])
        if rn:
            fam.add(rn)
    # reverse: others that name this niin as their related_nsn
    for r in con.execute("SELECT niin FROM stdz WHERE related_nsn LIKE ?", ("%" + niin,)).fetchall():
        if r["niin"]:
            fam.add(r["niin"])
    fam.discard(niin)
    return fam


def _verdict_trust(verdict):
    """v1.13 (R13): one trust badge per verdict. green = FLIS-linked (authoritative, corroborated);
    amber = needs human verification; red = authoritative single statement of no link."""
    try:
        import trust as _trust
        if verdict == "green":
            return _trust.badge(source="publog", n_samples=2)
        if verdict == "amber":
            return _trust.badge(source="publog", confidence="review")
        return _trust.badge(source="publog", n_samples=1)
    except Exception:
        return None


def interchangeability(a, b, db_path=None):
    """Bundle 2: GREEN/AMBER/RED verdict + reason (+ v1.13 trust badge)."""
    con = _con(db_path)
    if con is None:
        return {"available": False}
    na, nb = _niin(a), _niin(b)
    try:
        fam_a = _isc_family(con, na)
        # supersession links either way?
        rep = con.execute("SELECT 1 FROM cancelled WHERE (niin=? AND cancelled_niin=?) OR (niin=? AND cancelled_niin=?) LIMIT 1",
                          (na, nb, nb, na)).fetchone()
        isc = con.execute("SELECT isc FROM stdz WHERE niin=? AND isc!='' LIMIT 1", (na,)).fetchone()
        if nb in fam_a:
            return {"available": True, "verdict": "green", "label": "Interchangeable (same standardization family)",
                    "reason": "Both NSNs are linked in FLIS standardization (I&S).",
                    "isc": isc["isc"] if isc else "", "isc_meaning": _decode(_ISC, isc["isc"]) if isc else "",
                    "trust": _verdict_trust("green")}
        if rep:
            return {"available": True, "verdict": "amber", "label": "One-way substitute (supersession)",
                    "reason": "One of these NIINs replaces the other — substitute in the supersession direction only.",
                    "trust": _verdict_trust("amber")}
        # fall back to characteristics closeness
        cmp = compare(na, nb, db_path)
        sim = cmp.get("similarity_pct")
        if sim is not None and sim >= 90 and cmp.get("comparable", 0) >= 3:
            return {"available": True, "verdict": "amber", "label": "Likely similar — verify",
                    "reason": "Not linked in FLIS I&S, but characteristics are %d%% identical (%d specs)."
                              % (sim, cmp["comparable"]), "similarity_pct": sim, "differing": cmp.get("differing"),
                    "trust": _verdict_trust("amber")}
        return {"available": True, "verdict": "red", "label": "Not interchangeable (no FLIS link)",
                "reason": "No standardization/supersession link" + (
                    "; characteristics differ." if sim is not None else " and no comparable characteristics."),
                "similarity_pct": sim, "differing": cmp.get("differing"),
                "trust": _verdict_trust("red")}
    finally:
        con.close()


def substitutes(niin, db_path=None, limit=20):
    """Bundle 2: NSNs usable instead of this one (I&S family + related + what replaced it)."""
    con = _con(db_path)
    if con is None:
        return {"available": False}
    n = _niin(niin)
    try:
        cand = set(_isc_family(con, n))
        for r in con.execute("SELECT niin FROM cancelled WHERE cancelled_niin=? LIMIT 20", (n,)).fetchall():
            if r["niin"]:
                cand.add(r["niin"])
        out = []
        for c in list(cand)[:limit]:
            nm = con.execute("SELECT fsc,item_name FROM nsn WHERE niin=? LIMIT 1", (c,)).fetchone()
            fsc = nm["fsc"] if nm else ""
            out.append({"niin": c, "nsn": ("%s-%s-%s-%s" % (fsc, c[:2], c[2:5], c[5:])) if fsc else c,
                        "item_name": nm["item_name"] if nm else ""})
        return {"available": True, "niin": n, "count": len(out), "substitutes": out}
    finally:
        con.close()


def supersession(niin, db_path=None):
    """Bundle 2: obsolescence status from AAC + replaced-by chain."""
    con = _con(db_path)
    if con is None:
        return {"available": False}
    n = _niin(niin)
    try:
        aacs = [r["aac"] for r in con.execute("SELECT aac FROM moe WHERE niin=? AND aac!=''", (n,)).fetchall()]
        aac = aacs[0] if aacs else ""
        terminal = bool(aac) and aac.upper()[0] in _AAC_TERMINAL
        replaced_by = [r["niin"] for r in con.execute("SELECT niin FROM cancelled WHERE cancelled_niin=? LIMIT 6", (n,)).fetchall() if r["niin"]]
        replaces = [r["cancelled_niin"] for r in con.execute("SELECT cancelled_niin FROM cancelled WHERE niin=? LIMIT 6", (n,)).fetchall() if r["cancelled_niin"]]
        status = "obsolete/terminal" if (terminal or replaced_by) else ("active" if aac else "unknown")
        return {"available": True, "niin": n, "aac": aac, "aac_meaning": _decode(_AAC, aac),
                "terminal": terminal, "status": status, "replaced_by": replaced_by, "replaces": replaces}
    finally:
        con.close()


def reference_confidence(niin, db_path=None, limit=40):
    """Bundle 3: decode each part number's RNCC/RNVC (exact vs 'similar, may differ')."""
    con = _con(db_path)
    if con is None:
        return {"available": False}
    n = _niin(niin)
    try:
        out = []
        for r in con.execute("SELECT part_number,cage_code,rncc,rnvc FROM part WHERE niin=? LIMIT ?", (n, limit)).fetchall():
            cage = con.execute("SELECT company,status FROM cage WHERE cage_code=? LIMIT 1", (r["cage_code"],)).fetchone()
            exact = (r["rnvc"] or "").strip() == "1"
            out.append({"part_number": r["part_number"], "cage": r["cage_code"],
                        "company": cage["company"] if cage else "",
                        "vendor_active": _cage_active(cage["status"] if cage else ""),
                        "rncc": r["rncc"], "rnvc": r["rnvc"],
                        "rnvc_meaning": _decode(_RNVC, r["rnvc"]), "rncc_meaning": _decode(_RNCC, r["rncc"]),
                        "exact": exact})
        return {"available": True, "niin": n, "parts": out}
    finally:
        con.close()


def _cage_active(status):
    s = (status or "").strip().upper()
    if not s:
        return None
    return s in ("A", "H")   # A=active; H=historically-active retained record. Others (e.g. 'N') = inactive.


def vendor_status(niin, db_path=None):
    """Bundle 3: which vendors (CAGE) behind this part are active vs inactive."""
    rc = reference_confidence(niin, db_path)
    if not rc.get("available"):
        return rc
    vendors, seen = [], set()
    for p in rc["parts"]:
        if p["cage"] and p["cage"] not in seen:
            seen.add(p["cage"])
            vendors.append({"cage": p["cage"], "company": p["company"], "active": p["vendor_active"]})
    return {"available": True, "niin": rc["niin"], "vendors": vendors,
            "any_active": any(v["active"] for v in vendors) if vendors else None}


def _inc_for(con, niin):
    r = con.execute("SELECT inc FROM nsn WHERE niin=? LIMIT 1", (niin,)).fetchone()
    return r["inc"] if r else ""


def nicknames(key, db_path=None):
    """Bundle 4: colloquial + related-INC names for a NIIN (or INC), plus a CLASH warning when a nickname
    maps to more than one distinct official item name."""
    con = _con(db_path)
    if con is None:
        return {"available": False}
    try:
        inc = ""
        if re.fullmatch(r"\d{5}", (key or "").strip()):
            inc = key.strip()
        else:
            inc = _inc_for(con, _niin(key))
        if not inc:
            return {"available": True, "inc": "", "nicknames": [], "related": [], "clashes": []}
        colls = [r["colloquial_name"] for r in con.execute("SELECT colloquial_name FROM colloquial WHERE inc=?", (inc,)).fetchall() if r["colloquial_name"]]
        related = [{"inc": r["related_inc"], "item_name": r["item_name"]} for r in
                   con.execute("SELECT related_inc,item_name FROM h6related WHERE inc=? LIMIT 20", (inc,)).fetchall()]
        clashes = []
        for nick in set(colls):
            owners = con.execute("SELECT DISTINCT inc FROM colloquial WHERE colloquial_name=? LIMIT 5", (nick,)).fetchall()
            if len(owners) > 1:
                clashes.append({"nickname": nick, "incs": [o["inc"] for o in owners]})
        return {"available": True, "inc": inc, "nicknames": sorted(set(colls)), "related": related, "clashes": clashes}
    finally:
        con.close()


def tech_docs(niin, db_path=None):
    """Bundle 4 crosslink: TECH_DOC_NBR phrases -> manual references for this part."""
    con = _con(db_path)
    if con is None:
        return {"available": False}
    n = _niin(niin)
    try:
        docs, seen = [], set()
        for r in con.execute("SELECT phrase,tech_doc FROM phrase WHERE niin=? LIMIT 30", (n,)).fetchall():
            td = (r["tech_doc"] or "").strip()
            if td and td not in seen:
                seen.add(td)
                docs.append({"tech_doc": td, "phrase": (r["phrase"] or "").strip()})
        return {"available": True, "niin": n, "tech_docs": docs}
    finally:
        con.close()


# --------------------------------------------------------------------------- #
# self-test: `python publogdiff.py` -- builds a tiny publog-shaped db in memory #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "publogdiff_test.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    con.executescript("""
      CREATE TABLE nsn(niin TEXT, fsc TEXT, inc TEXT, item_name TEXT, end_item_name TEXT, sos TEXT, cancelled_niin TEXT);
      CREATE TABLE charx(niin TEXT, mrc TEXT, requirement TEXT, reply TEXT);
      CREATE TABLE part(niin TEXT, part_number TEXT, part_norm TEXT, cage_code TEXT, rncc TEXT, rnvc TEXT);
      CREATE TABLE cage(cage_code TEXT, company TEXT, city TEXT, state TEXT, country TEXT, status TEXT);
      CREATE TABLE stdz(niin TEXT, related_nsn TEXT, isc TEXT, dt TEXT);
      CREATE TABLE moe(niin TEXT, aac TEXT, pica TEXT, sica TEXT);
      CREATE TABLE phrase(niin TEXT, phrase TEXT, tech_doc TEXT);
      CREATE TABLE colloquial(inc TEXT, colloquial_name TEXT);
      CREATE TABLE h6related(inc TEXT, related_inc TEXT, item_name TEXT);
      CREATE TABLE cancelled(niin TEXT, cancelled_niin TEXT, fsc TEXT, eff_date TEXT, stat TEXT);
    """)
    A, B = "000000001", "000000002"
    con.execute("INSERT INTO nsn VALUES(?,?,?,?,?,?,?)", (A, "2920", "12345", "ALTERNATOR", "", "", ""))
    con.execute("INSERT INTO nsn VALUES(?,?,?,?,?,?,?)", (B, "2920", "12345", "ALTERNATOR", "", "", ""))
    for mrc, req, va, vb in [("A", "OUTPUT VOLTAGE", "28V", "28V"), ("B", "OUTPUT CURRENT", "100A", "200A"),
                             ("C", "MOUNTING", "PAD", "PAD")]:
        con.execute("INSERT INTO charx VALUES(?,?,?,?)", (A, mrc, req, va))
        con.execute("INSERT INTO charx VALUES(?,?,?,?)", (B, mrc, req, vb))
    con.execute("INSERT INTO part VALUES(?,?,?,?,?,?)", (A, "PN-EXACT", "PNEXACT", "11111", "3", "1"))
    con.execute("INSERT INTO part VALUES(?,?,?,?,?,?)", (A, "PN-SIMILAR", "PNSIMILAR", "22222", "5", "2"))
    con.execute("INSERT INTO cage VALUES(?,?,?,?,?,?)", ("11111", "ACME", "X", "Y", "US", "A"))
    con.execute("INSERT INTO cage VALUES(?,?,?,?,?,?)", ("22222", "DEFUNCT CO", "X", "Y", "US", "N"))
    con.execute("INSERT INTO stdz VALUES(?,?,?,?)", (A, B, "1", "01-JAN-2000"))     # A<->B I&S family
    con.execute("INSERT INTO moe VALUES(?,?,?,?)", (A, "C", "10", ""))              # active
    con.execute("INSERT INTO moe VALUES(?,?,?,?)", (B, "H", "10", ""))              # terminal
    con.execute("INSERT INTO phrase VALUES(?,?,?)", (A, "REFER TO TM 9-2320", "TM 9-2320-280-20"))
    con.execute("INSERT INTO colloquial VALUES(?,?)", ("12345", "GENERATOR"))
    con.execute("INSERT INTO h6related VALUES(?,?,?)", ("12345", "67890", "GENERATOR ENGINE ACCESSORY"))
    con.commit(); con.close()

    c = compare(A, B, tmp)
    assert c["similarity_pct"] == 67, c                         # 2 of 3 specs match
    assert "OUTPUT CURRENT" in c["differing"], c
    print("compare OK -> %d%% identical, differs in %s" % (c["similarity_pct"], c["differing"]))

    v = interchangeability(A, B, tmp)
    assert v["verdict"] == "green", v                            # linked I&S family
    print("interchangeability OK -> %s (%s)" % (v["verdict"], v["label"]))

    s = substitutes(A, tmp)
    assert any(x["niin"] == B for x in s["substitutes"]), s
    print("substitutes OK -> %d found" % s["count"])

    sup = supersession(B, tmp)
    assert sup["terminal"] and sup["status"] == "obsolete/terminal", sup
    print("supersession OK -> B is %s (AAC %s = %s)" % (sup["status"], sup["aac"], sup["aac_meaning"]))

    rc = reference_confidence(A, tmp)
    exact = [p for p in rc["parts"] if p["exact"]]
    assert exact and exact[0]["part_number"] == "PN-EXACT", rc
    inactive = [p for p in rc["parts"] if p["vendor_active"] is False]
    assert inactive and inactive[0]["cage"] == "22222", rc
    print("reference_confidence OK -> exact=%s, inactive-vendor=%s" % (exact[0]["part_number"], inactive[0]["cage"]))

    nk = nicknames(A, tmp)
    assert "GENERATOR" in nk["nicknames"], nk
    print("nicknames OK -> %s (related %d)" % (nk["nicknames"], len(nk["related"])))

    td = tech_docs(A, tmp)
    assert td["tech_docs"] and td["tech_docs"][0]["tech_doc"] == "TM 9-2320-280-20", td
    print("tech_docs OK -> %s" % td["tech_docs"][0]["tech_doc"])
    print("publogdiff self-test PASS")

# END OF FILE
