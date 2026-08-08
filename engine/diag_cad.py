#!/usr/bin/env python3
"""Hit the LIVE /cadimg route for a real representative part and save the PNG. RUN ON WINDOWS while a server is up."""
import urllib.request, json, os, sys
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8766"
HERE = os.path.dirname(os.path.abspath(__file__))
def get(p):
    with urllib.request.urlopen(BASE+p, timeout=90) as r:
        return r.status, r.headers.get("Content-Type",""), r.read()
try:
    st, ct, b = get("/api/threed?all=1&limit=3"); j = json.loads(b); items = j.get("items", [])
    nsn = items[0]["nsn"] if items else "5305-01-574-1476"
    st, ct, b = get("/cadimg?nsn="+nsn)
    ok = b[:8] == b"\x89PNG\r\n\x1a\n"
    if ok: open(os.path.join(HERE,"..","index","cad_live.png"),"wb").write(b)
    msg = "nsn=%s  status=%s  type=%s  bytes=%d  %s" % (nsn, st, ct, len(b), "VALID PNG (saved cad_live.png)" if ok else "NOT A PNG")
    print(msg); open(os.path.join(HERE,"..","index","diag_cad.txt"),"w").write(msg)
except Exception as e:
    print("ERR", e); open(os.path.join(HERE,"..","index","diag_cad.txt"),"w").write("ERR "+str(e))
