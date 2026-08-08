#!/usr/bin/env python3
"""THE VIEWER -- cross-figure PART LOCATOR (v0.99.7). "Where does this part show up?" Given an NSN, part number,
or name, find every FIGURE / page in the corpus that calls it out (from the parts index), with ready links to
deep-zoom, vectorize, and open the page. Read-only on the index (R1). db_path passed explicitly."""
import os, sqlite3, re

_NSN = re.compile(r"\d{4}-?\d{2}-?\d{3}-?\d{4}")


def _db(db_path):
    con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True); con.row_factory = sqlite3.Row; return con


def _norm_nsn(s):
    m = _NSN.search(s or "")
    if not m:
        return None
    d = re.sub(r"\D", "", m.group(0))
    return "%s-%s-%s-%s" % (d[0:4], d[4:6], d[6:9], d[9:13]) if len(d) == 13 else None


def locate(db_path, q, limit=250):
    q = (q or "").strip()
    if len(q) < 2:
        return {"query": q, "count": 0, "appearances": [], "note": "type an NSN, part number, or name"}
    nsn = _norm_nsn(q)
    like = "%" + q.upper() + "%"
    out = []; seen = set(); matched_names = set()
    try:
        con = _db(db_path)
        rows = con.execute(
            "SELECT p.document_id AS doc, p.page AS page, p.fig_no AS fig, p.fig_title AS figtitle, "
            "       p.nsn AS nsn, p.part_number AS pn, p.name AS name, p.nomenclature AS nomen, p.cagec AS cagec, "
            "       d.vehicle AS vehicle, d.tm_number AS tm, d.title AS title "
            "FROM parts p JOIN documents d ON d.id=p.document_id "
            "WHERE (?1 IS NOT NULL AND p.nsn=?1) OR upper(COALESCE(p.part_number,''))=?2 "
            "   OR upper(COALESCE(p.nsn,'')) LIKE ?3 OR upper(COALESCE(p.name,'')) LIKE ?3 "
            "   OR upper(COALESCE(p.nomenclature,'')) LIKE ?3 "
            "ORDER BY p.document_id, p.page LIMIT ?4",
            (nsn, q.upper(), like, limit * 4)).fetchall()
        con.close()
    except Exception as e:
        return {"query": q, "count": 0, "appearances": [], "error": str(e)}

    for r in rows:
        doc = r["doc"]; page = int(r["page"] or 1)
        key = (doc, page, r["fig"] or "")
        if key in seen:
            continue
        seen.add(key)
        if r["name"]:
            matched_names.add(r["name"])
        out.append({
            "doc": doc, "page": page, "fig_no": r["fig"], "fig_title": r["figtitle"],
            "nsn": r["nsn"], "part_number": r["pn"], "name": r["name"], "nomenclature": r["nomen"], "cagec": r["cagec"],
            "vehicle": r["vehicle"], "tm": r["tm"], "title": r["title"],
            "deepzoom_url": "/deepzoom?doc=%d&page=%d" % (doc, page),
            "vectorize_url": "/vectorize?doc=%d&page=%d" % (doc, page),
            "page_url": "/page?doc=%d&page=%d&dpi=200" % (doc, page),
        })
        if len(out) >= limit:
            break
    docs = len({a["doc"] for a in out})
    return {"query": q, "nsn": nsn, "count": len(out), "documents": docs,
            "names": sorted(matched_names)[:8], "appearances": out}


if __name__ == "__main__":
    import json, sys
    db = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "index", "viewer.db")
    print(json.dumps(locate(db, sys.argv[1] if len(sys.argv) > 1 else "alternator"), indent=2)[:1200])
