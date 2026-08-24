#!/usr/bin/env python3
"""THE VIEWER -- FIGURE → PARTS (v0.99.8): the inverse of the part locator. Given a document + page (a figure
sheet), list every part called out ON that sheet, from the structured parts index (more complete than the OCR
callouts). Completes the two-way navigation: locate a part -> its figures -> all parts on each of those figures.
Read-only on the index (R1). db_path passed explicitly."""
import os, sqlite3
from urllib.parse import quote as _q


def _db(db_path):
    con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True); con.row_factory = sqlite3.Row; return con


def parts_on(db_path, doc, page, limit=400):
    try:
        doc = int(doc); page = int(page)
    except Exception:
        return {"doc": doc, "page": page, "count": 0, "parts": [], "error": "bad doc/page"}
    out = []; seen = set(); fig = None; figtitle = None
    try:
        con = _db(db_path)
        rows = con.execute(
            "SELECT nsn, part_number AS pn, name, nomenclature AS nomen, cagec, smr, uoc, fig_no, fig_title "
            "FROM parts WHERE document_id=? AND page=? ORDER BY "
            "CASE WHEN COALESCE(nsn,'')<>'' THEN 0 ELSE 1 END, name LIMIT ?", (doc, page, limit * 2)).fetchall()
        con.close()
    except Exception as e:
        return {"doc": doc, "page": page, "count": 0, "parts": [], "error": str(e)}
    for r in rows:
        key = (r["nsn"] or "", (r["pn"] or "").upper(), (r["name"] or "").upper())
        if key in seen:
            continue
        seen.add(key)
        if fig is None and r["fig_no"]:
            fig = r["fig_no"]; figtitle = r["fig_title"]
        nsn = r["nsn"]; pn = r["pn"]
        out.append({
            "nsn": nsn, "part_number": pn, "name": r["name"], "nomenclature": r["nomen"],
            "cagec": r["cagec"], "smr": r["smr"], "uoc": r["uoc"], "fig_no": r["fig_no"],
            "dossier_url": ("/dossier?q=" + _q(nsn, safe="")) if nsn else (("/partdiff?q=" + _q(pn, safe="")) if pn else None),
            "locate_url": ("/locate?q=" + _q(nsn or pn or (r["name"] or "").strip(), safe="")) if (nsn or pn or r["name"]) else None,
            "cad_url": ("/cadimg?nsn=" + _q(nsn, safe="")) if nsn else None,
        })
        if len(out) >= limit:
            break
    return {"doc": doc, "page": page, "fig_no": fig, "fig_title": figtitle, "count": len(out), "parts": out}


if __name__ == "__main__":
    import json, sqlite3, tempfile
    d = tempfile.mkdtemp(); db = os.path.join(d, "v.db")
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE parts(id INTEGER PRIMARY KEY, document_id INT, page INT, nsn TEXT, part_number TEXT, name TEXT, nomenclature TEXT, cagec TEXT, smr TEXT, uoc TEXT, fig_no TEXT, fig_title TEXT)")
    c.executemany("INSERT INTO parts(document_id,page,nsn,part_number,name,cagec,fig_no,fig_title) VALUES(?,?,?,?,?,?,?,?)", [
        (1, 12, '5305-01-111-1111', 'B1', 'BOLT', '19207', 'FIG 5', 'ELECTRICAL'),
        (1, 12, '5310-01-222-2222', 'N1', 'NUT', '19207', 'FIG 5', 'ELECTRICAL'),
        (1, 12, '5305-01-111-1111', 'B1', 'BOLT', '19207', 'FIG 5', 'ELECTRICAL'),   # dup
        (1, 44, '2920-01-333-3333', 'A1', 'ALTERNATOR', '19207', 'FIG 12', 'WIRING'),
    ])
    c.commit(); c.close()
    r = parts_on(db, 1, 12)
    print("fig:", r["fig_no"], "count:", r["count"], "->", [p["name"] for p in r["parts"]])
