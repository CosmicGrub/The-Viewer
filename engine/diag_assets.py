#!/usr/bin/env python3
"""Dump the real JSON shapes the asset drawer consumes, so the client parsing matches the server.
RUN ON WINDOWS while a server is up. Default base http://127.0.0.1:8766. Writes index/diag_assets.txt."""
import sys, json, os, urllib.request, urllib.error
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8766"
HERE = os.path.dirname(os.path.abspath(__file__))
out = []
def p(s=""):
    print(s); out.append(str(s))
def get(path):
    try:
        with urllib.request.urlopen(urllib.request.Request(BASE+path, headers={"Cache-Control":"no-cache"}), timeout=40) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, (e.read() or b"")
    except Exception as e:
        return "ERR", str(e).encode()
def js(b):
    try: return json.loads(b.decode("utf-8","replace"))
    except Exception: return None
def keys(o):
    if isinstance(o, dict): return list(o.keys())
    if isinstance(o, list) and o and isinstance(o[0], dict): return ["[list of]"]+list(o[0].keys())
    return type(o).__name__

def main():
    p("=== asset endpoint shapes === base=%s" % BASE)
    st, b = get("/api/threed?limit=3")
    j = js(b); items = (j or {}).get("items", [])
    nsn = items[0].get("nsn") if items else "5305-01-574-1476"
    p("sample nsn = %s" % nsn); p("")
    for label, path in [
        ("part_record",  "/api/part_record?nsn="+nsn),
        ("part_image",   "/api/part_image?nsn="+nsn),
        ("threed_refs",  "/api/threed_refs?nsn="+nsn),
        ("part_material","/api/part_material?nsn="+nsn),
    ]:
        st, b = get(path); j = js(b)
        p("%-13s [%s]  keys=%s" % (label, st, keys(j)))
        p("   raw: %s" % (b.decode("utf-8","replace")[:300]))
        p("")
    # part_by_number: need a PN
    st, b = get("/api/part_record?nsn="+nsn); rec = js(b) or {}
    pn = (rec.get("record") or rec).get("part_no") or (rec.get("record") or rec).get("part_number") or ""
    p("sample part_no = %r" % pn)
    if pn:
        st, b = get("/api/part_by_number?pn="+urllib.parse.quote(pn)); j = js(b)
        p("part_by_number [%s]  keys=%s" % (st, keys(j)))
        p("   raw: %s" % (b.decode("utf-8","replace")[:300]))
    try:
        open(os.path.join(HERE,"..","index","diag_assets.txt"),"w",encoding="utf-8").write("\n".join(out))
    except Exception: pass
    return 0
import urllib.parse
if __name__ == "__main__":
    sys.exit(main())
