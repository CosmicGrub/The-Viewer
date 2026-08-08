#!/usr/bin/env python3
import os, re, sqlite3, json
DB_PATH = "index/viewer.db"
NSN_RE = re.compile(r"(\d{4})-?(\d{2})-?(\d{3})-?(\d{4})")
def norm_nsn(s):
    m = NSN_RE.search(s or "")
    return "%s-%s-%s-%s" % m.groups() if m else (s or "").strip()
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
if __name__ == "__main__":
    for nsn in ["5305-01-674-1467", "5305016741467", "1005-01-177-2665", "0000-00-000-0000", ""]:
        print(repr(nsn), "->", json.dumps(correlations_for(nsn))[:240])
