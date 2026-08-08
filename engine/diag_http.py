#!/usr/bin/env python3
"""Hit the LIVE running server over HTTP exactly like the browser does, and report what it returns.
Read-only. RUN ON WINDOWS (host) WHILE THE APP IS RUNNING. Writes index/diag_http.txt.
"""
import os, sys, json, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "http://127.0.0.1:8765"
out = []
def p(s=""):
    print(s); out.append(str(s))

def get(path, binary=False):
    url = BASE + path
    req = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            return r.status, r.headers.get("Content-Type", ""), len(body), body
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", "") if e.headers else "", len((e.read() or b"")), b""
    except Exception as e:
        return "ERR", str(e), 0, b""

def main():
    p("=== LIVE SERVER PROBE (%s) ===" % BASE)
    # 1) the 3-D page HTML the browser actually receives
    st, ct, n, body = get("/3d")
    p("")
    p("GET /3d                -> status=%s  type=%s  bytes=%s" % (st, ct, n))
    if body:
        txt = body.decode("utf-8", "replace")
        for marker in ["working examples", 'id="showall"', "all=1", "image_url", "0814"]:
            p("    HTML contains %-18r : %s" % (marker, marker in txt))

    # 2) the API the page calls on load
    st, ct, n, body = get("/api/threed?limit=8")
    p("")
    p("GET /api/threed?limit=8 -> status=%s  type=%s  bytes=%s" % (st, ct, n))
    first = None
    if body:
        try:
            j = json.loads(body.decode("utf-8", "replace"))
            p("    mode=%s  total=%s  items=%s" % (j.get("mode"), j.get("total"), len(j.get("items", []))))
            if j.get("error"): p("    ERROR field: %s" % j["error"])
            for it in j.get("items", [])[:5]:
                p("      %s  %-24s image_url=%s" % (it.get("nsn"), (it.get("item_name") or "")[:24], it.get("image_url")))
            its = j.get("items", [])
            if its: first = its[0].get("image_url")
        except Exception as e:
            p("    JSON parse failed: %s  (first 200 bytes: %r)" % (e, body[:200]))

    # 3) the figure image itself -- the exact URL the first card requests
    if first:
        st, ct, n, body = get(first, binary=True)
        p("")
        p("GET %s -> status=%s  type=%s  bytes=%s" % (first, st, ct, n))
        if isinstance(body, (bytes, bytearray)) and body[:8] == b"\x89PNG\r\n\x1a\n":
            p("    -> valid PNG signature. The image LOADS over HTTP. (If the browser still shows blocky, it's a stale tab/cache.)")
        elif st == 200:
            p("    -> 200 but NOT a PNG (first bytes: %r) -- THIS would make the browser's <img> fail." % (bytes(body[:32]),))
        else:
            p("    -> non-200 -- THIS is why the figure doesn't show; /figcrop is erroring on the live server.")
    else:
        p("\n(no image_url in the API result -- nothing for the card to load)")

    try:
        open(os.path.join(HERE, "..", "index", "diag_http.txt"), "w", encoding="utf-8").write("\n".join(out))
        p("\n[saved to index/diag_http.txt]")
    except Exception as e:
        p("save failed: %s" % e)
    return 0

if __name__ == "__main__":
    sys.exit(main())
