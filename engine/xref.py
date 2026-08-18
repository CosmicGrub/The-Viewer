#!/usr/bin/env python3
"""THE VIEWER -- CROSS-REFERENCE / RELATED PARTS & ASSEMBLIES (v0.99.25). For a part, surface: the assemblies/figures
it belongs to (fig_no + fig_title), its SIBLINGS (other parts called out on the same figure = same assembly), and
SEE-ALSO parts (parts in other figures with the same assembly title). Read-only on the parts index; db_path explicit.
Powers a 'related' panel on the dossier so a mechanic sees what a part sits inside and what ships with it."""
import os, sqlite3


def _db(db_path):
    con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True); con.row_factory = sqlite3.Row; return con


def _norm_nsn(s):
    """Canonical NSN if `s` contains one, else `s` unchanged (for the name/part-number OR-lookup
    below). Delegates to patterns.norm_nsn -- the project's single \\b-anchored source of truth --
    instead of a local regex copy (medium finding #21: the old `len(d) >= 13` form here stripped
    ALL non-digits from the whole input and accepted anything 13+ digits long, silently slicing
    out only the first 13 -- a 15/16-digit invoice or tracking number pasted into search fabricated
    a plausible-looking but bogus NSN instead of being rejected. Review finding on the first fix:
    that bug was fixed by adding yet another verbatim regex copy -- the 8th+ across this codebase
    -- instead of importing the canonical implementation, which is a one-line adaptation since
    patterns.norm_nsn returns None on no match, not the raw string)."""
    import patterns
    return patterns.norm_nsn(s) or (s or "").strip()


def related(db_path, q, limit=60):
    q = (q or "").strip()
    empty = {"query": q, "found": False, "nomenclature": None, "assemblies": [], "siblings": [], "see_also": []}
    if len(q) < 2:
        return empty
    ref = _norm_nsn(q)
    try:
        con = _db(db_path)
        # resolve the part's rows (by nsn/name/part_number) -> its (doc,fig) locations + nomenclature
        rows = con.execute(
            "SELECT document_id AS doc, page, nsn, part_number AS pn, name, nomenclature AS nomen, fig_no, fig_title "
            "FROM parts WHERE nsn=? OR name=? COLLATE NOCASE OR part_number=? COLLATE NOCASE "
            "OR nomenclature=? COLLATE NOCASE LIMIT ?", (ref, q, q, q, limit * 4)).fetchall()
        if not rows:
            con.close(); empty["query"] = q; return empty
        nom = None
        figset = []      # (doc, fig_no, fig_title, page, )
        selfkeys = set()
        for r in rows:
            if nom is None:
                nom = r["name"] or r["nomen"]
            selfkeys.add((r["nsn"] or "", (r["pn"] or "").upper(), (r["name"] or "").upper()))
            if r["fig_no"] or r["fig_title"]:
                figset.append((r["doc"], r["fig_no"], r["fig_title"], r["page"]))
        # dedup assemblies
        asm = {}; titles = set()
        for doc, fno, ftitle, page in figset:
            key = (doc, fno)
            if key not in asm:
                # vehicle for the doc
                v = con.execute("SELECT vehicle, tm_number FROM documents WHERE id=?", (doc,)).fetchone()
                asm[key] = {"doc": doc, "fig_no": fno, "fig_title": ftitle, "page": page,
                            "vehicle": (v["vehicle"] if v else None), "tm": (v["tm_number"] if v else None),
                            "locate_url": "/deepzoom?doc=%s&page=%s" % (doc, page) if page else None}
            if ftitle:
                titles.add(ftitle.strip())
        assemblies = list(asm.values())[:limit]

        # siblings: other distinct parts on the same (doc, fig_no)
        siblings = []; seen = set(selfkeys)
        for a in assemblies:
            # AND binds tighter than OR -- the original "...fig_no IS ? OR (document_id=? AND
            # fig_no=?)" parsed as (document_id=? AND fig_no IS ?) OR (document_id=? AND fig_no=?),
            # which (since both document_id checks bind the same value) collapsed to "same doc AND
            # (no figure at all OR this figure)" -- every part in the document with NO figure
            # assigned at all was pulled in as a "sibling" of any real figure's parts. Simply
            # parenthesizing the OR group does NOT fix this on its own -- "fig_no IS NULL OR
            # fig_no=?" still matches NULL rows regardless of grouping, confirmed by the regression
            # test below. Siblings are, by definition, other parts on the exact same (doc, fig_no);
            # there was never a legitimate reason to also match fig_no IS NULL here, so that branch
            # is dropped entirely rather than reparenthesized.
            srows = con.execute(
                "SELECT nsn, part_number AS pn, name, fig_no FROM parts "
                "WHERE document_id=? AND fig_no=? LIMIT 200",
                (a["doc"], a["fig_no"])).fetchall() \
                if a["fig_no"] else []
            for s in srows:
                k = (s["nsn"] or "", (s["pn"] or "").upper(), (s["name"] or "").upper())
                if k in seen:
                    continue
                seen.add(k)
                siblings.append({"nsn": s["nsn"], "part_number": s["pn"], "name": s["name"],
                                 "dossier_url": ("/dossier?q=" + s["nsn"]) if s["nsn"] else None})
                if len(siblings) >= limit:
                    break
            if len(siblings) >= limit:
                break

        # see-also: parts in figures sharing an assembly title (different figure)
        see_also = []
        seen2 = set(k[0] for k in selfkeys if k[0]) | set(s["nsn"] for s in siblings if s["nsn"])
        for ttl in list(titles)[:6]:
            trows = con.execute(
                "SELECT DISTINCT nsn, name, fig_title FROM parts WHERE fig_title=? COLLATE NOCASE "
                "AND nsn IS NOT NULL AND nsn<>'' LIMIT 40", (ttl,)).fetchall()
            for tr in trows:
                if (tr["nsn"] or "") in seen2:
                    continue
                seen2.add(tr["nsn"] or "")
                see_also.append({"nsn": tr["nsn"], "name": tr["name"], "assembly": tr["fig_title"],
                                 "dossier_url": "/dossier?q=" + tr["nsn"]})
                if len(see_also) >= 40:
                    break
        con.close()
    except Exception as e:
        empty["query"] = q; empty["error"] = str(e); return empty
    return {"query": q, "found": True, "nomenclature": nom, "assemblies": assemblies,
            "siblings": siblings[:limit], "see_also": see_also[:40]}


if __name__ == "__main__":
    import tempfile
    d = tempfile.mkdtemp(); db = os.path.join(d, "v.db"); c = sqlite3.connect(db)
    c.execute("CREATE TABLE documents(id INTEGER PRIMARY KEY, vehicle TEXT, tm_number TEXT, title TEXT)")
    c.execute("CREATE TABLE parts(id INTEGER PRIMARY KEY, document_id INT, page INT, nsn TEXT, part_number TEXT, name TEXT, nomenclature TEXT, cagec TEXT, smr TEXT, uoc TEXT, fig_no TEXT, fig_title TEXT)")
    c.execute("INSERT INTO documents VALUES(1,'HMMWV M998','TM 9-2320-280-24P','P')")
    c.executemany("INSERT INTO parts(document_id,page,nsn,part_number,name,fig_no,fig_title) VALUES(?,?,?,?,?,?,?)", [
        (1, 44, '2920-01-333-3333', 'A1', 'ALTERNATOR', 'FIG 12', 'CHARGING SYSTEM'),
        (1, 44, '5305-01-111-1111', 'B1', 'BOLT', 'FIG 12', 'CHARGING SYSTEM'),
        (1, 44, '5310-01-222-2222', 'N1', 'NUT', 'FIG 12', 'CHARGING SYSTEM'),
        (1, 60, '2920-01-999-9999', 'V1', 'VOLTAGE REGULATOR', 'FIG 15', 'CHARGING SYSTEM'),
        # same document, NO figure assigned at all -- regression case for the operator-precedence
        # bug (finding #10): must NEVER show up as a "sibling" of the FIG 12 parts above.
        (1, 90, '5975-01-444-4444', 'X1', 'LOOSE PART NO FIGURE', None, None)])
    c.commit(); c.close()
    r = related(db, "ALTERNATOR")
    print("assemblies:", [(a["fig_no"], a["fig_title"]) for a in r["assemblies"]])
    print("siblings:", [s["name"] for s in r["siblings"]])
    print("see_also:", [(x["name"], x["assembly"]) for x in r["see_also"]])
    assert any(s["name"] == "BOLT" for s in r["siblings"]), "sibling BOLT missing"
    assert any(x["name"] == "VOLTAGE REGULATOR" for x in r["see_also"]), "see_also missing"
    assert not any(s["name"] == "LOOSE PART NO FIGURE" for s in r["siblings"]), \
        "NULL-fig_no part leaked in as a sibling (operator-precedence bug regressed)"
    print("xref self-test OK")
# END OF FILE
