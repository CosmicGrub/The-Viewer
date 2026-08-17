#!/usr/bin/env python3
"""THE VIEWER -- Living Schematic (PoC): infer a connectivity GRAPH (netlist) from a schematic page's vectors.

Reuses schem_overlay.schem_paths() (lines / polylines / rectangles / text words, normalized 0..1), then:
  - decomposes paths into wire SEGMENTS
  - snaps near-coincident endpoints into NODES
  - builds EDGES, computes node degree, and groups edges into NETS (connected components, union-find)
  - attaches component-reference labels (R1, C12, K3, …) and rectangles (symbol boxes)
  - scores a CONFIDENCE for how graph-like the page is
Read-only; never touches the corpus (R1). Output cached to a JSON sidecar by the route.

  schemgraph.graph_from_paths(raw) -> graph dict
  schemgraph.graph_for(pdf_path, page) -> graph dict
  python schemgraph.py --selftest        # synthetic graph, no PDF needed
"""
import os, re, json, math, sys

REF = re.compile(r"^[A-Z]{1,3}\d{1,4}[A-Z]?$")          # R1, C12, U3, Q2, K1, TB4, CR2 ...
NET = re.compile(r"^[+-]?\d{1,3}V$|^GND$|^GROUND$|^B\+$|^PWR$|^VCC$|^VBATT$")

def _segments(raw):
    segs = []
    for p in raw.get("paths", []):
        if p.get("t") == "l":
            segs.append((p["x1"], p["y1"], p["x2"], p["y2"]))
        elif p.get("t") == "p":
            pts = p.get("pts", [])
            for i in range(len(pts) - 1):
                segs.append((pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1]))
    # drop zero-length and near-zero specks
    return [s for s in segs if (abs(s[0]-s[2]) + abs(s[1]-s[3])) > 8e-4]

def graph_from_paths(raw, snap=0.007):
    W, H = raw.get("w", 0), raw.get("h", 0)
    segs = _segments(raw)
    # spatial-hash snap of endpoints -> node ids
    cell = max(snap, 1e-4)
    grid = {}
    nodes = []   # (x, y)
    def key(x, y): return (int(x / cell), int(y / cell))
    def node_id(x, y):
        kx, ky = key(x, y)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for i in grid.get((kx+dx, ky+dy), ()):
                    nx, ny = nodes[i]
                    if (nx-x)**2 + (ny-y)**2 <= snap*snap:
                        return i
        i = len(nodes); nodes.append((x, y)); grid.setdefault((kx, ky), []).append(i); return i
    edges = []
    for (x1, y1, x2, y2) in segs:
        a = node_id(x1, y1); b = node_id(x2, y2)
        if a != b: edges.append((a, b, x1, y1, x2, y2))
    # T-junction split: a wire that touches the INTERIOR of another wire splits it (so taps connect to the net)
    split = []
    for (a, b, x1, y1, x2, y2) in edges:
        dx, dy = x2-x1, y2-y1; L2 = dx*dx + dy*dy
        on = []
        if L2 > 1e-12:
            for ni in range(len(nodes)):
                if ni == a or ni == b: continue
                px, py = nodes[ni]
                ti = ((px-x1)*dx + (py-y1)*dy) / L2
                if 0.02 < ti < 0.98:
                    cx, cy = x1+ti*dx, y1+ti*dy
                    if (cx-px)**2 + (cy-py)**2 <= snap*snap: on.append((ti, ni, px, py))
        if not on:
            split.append((a, b, x1, y1, x2, y2))
        else:
            on.sort(); seq = [(a, x1, y1)] + [(ni, px, py) for (_, ni, px, py) in on] + [(b, x2, y2)]
            for k in range(len(seq)-1):
                n0, X0, Y0 = seq[k]; n1, X1, Y1 = seq[k+1]
                if n0 != n1: split.append((n0, n1, X0, Y0, X1, Y1))
    edges = split
    deg = [0]*len(nodes)
    for e in edges: deg[e[0]] += 1; deg[e[1]] += 1
    # union-find -> nets
    parent = list(range(len(nodes)))
    def find(i):
        while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for e in edges:
        ra, rb = find(e[0]), find(e[1])
        if ra != rb: parent[ra] = rb
    net_edges = {}
    for idx, e in enumerate(edges):
        net_edges.setdefault(find(e[0]), []).append(idx)
    nets = list(net_edges.values())
    # components: ref labels + rectangles (symbol boxes)
    comps = []
    for w in raw.get("words", []):
        tt = (w.get("t") or "").strip().upper()
        if REF.match(tt):
            comps.append({"ref": tt, "x": round((w["x0"]+w["x1"])/2, 5), "y": round((w["y0"]+w["y1"])/2, 5),
                          "kind": "net" if NET.match(tt) else "part"})
    rects = [{"x": r["x"], "y": r["y"], "w": r["w"], "h": r["h"]} for r in raw.get("paths", []) if r.get("t") == "r"]
    # confidence: well-connected edges + presence of labels + a sane net count
    conf = 0.0
    if edges:
        conn = sum(1 for e in edges if deg[e[0]] >= 2 and deg[e[1]] >= 2)
        junc = sum(1 for d in deg if d >= 3)
        conf = (0.50*(conn/len(edges)) + 0.20*min(1.0, junc/8.0)
                + 0.18*min(1.0, len(comps)/8.0) + 0.12*(1.0 if 1 <= len(nets) <= 200 else 0.0))
    conf = round(min(0.97, conf), 2)
    return {
        "w": W, "h": H, "has_vector": raw.get("has_vector", False),
        "nodes": [{"x": round(x, 5), "y": round(y, 5), "d": deg[i]} for i, (x, y) in enumerate(nodes)],
        "edges": [{"a": e[0], "b": e[1], "x1": round(e[2], 5), "y1": round(e[3], 5), "x2": round(e[4], 5), "y2": round(e[5], 5)} for e in edges],
        "nets": nets, "comps": comps, "rects": rects,
        "counts": {"segments": len(segs), "nodes": len(nodes), "edges": len(edges),
                   "nets": len(nets), "components": len(comps), "rects": len(rects)},
        "confidence": conf,
    }

def graph_for(pdf_path, page=1):
    try:
        import schem_overlay
        raw = schem_overlay.schem_paths(pdf_path or "", page)
    except Exception as e:
        return {"error": str(e), "has_vector": False, "edges": [], "nets": [], "confidence": 0.0}
    g = graph_from_paths(raw)
    g["page"] = page
    return g

# ---- cache (sidecar JSON; never touches the index) ----
def cache_path(cache_dir, doc_id, page):
    return os.path.join(cache_dir, "%s_%s.json" % (doc_id, page))

def ensure(cache_dir, doc_id, page, pdf_path):
    try: os.makedirs(cache_dir, exist_ok=True)
    except Exception: pass
    out = cache_path(cache_dir, doc_id, page)
    if os.path.exists(out) and os.path.getsize(out) > 0:
        try: return json.load(open(out, encoding="utf-8"))
        except Exception: pass
    g = graph_for(pdf_path, page)
    try:
        # safeguard.atomic_write, not a bare open(...,"w"): a crash mid-write used to leave a
        # truncated/corrupt JSON cache file that the size>0 check above would then treat as
        # "already cached" forever -- the broken schematic graph was served permanently, never
        # regenerated. This is also what routes.py's own r_schemgraph-style handler does for its
        # inline cache write (see the matching fix there).
        import safeguard
        safeguard.atomic_write(out, json.dumps(g))
    except Exception: pass
    return g

def _selftest():
    # a tiny synthetic "circuit": a rectangular loop + a tap, with labels — verifies snapping/nets/confidence
    raw = {"w": 1000, "h": 700, "has_vector": True, "paths": [
        {"t": "l", "x1": 0.2, "y1": 0.2, "x2": 0.8, "y2": 0.2},   # top
        {"t": "l", "x1": 0.8, "y1": 0.2, "x2": 0.8, "y2": 0.7},   # right
        {"t": "l", "x1": 0.8, "y1": 0.7, "x2": 0.2, "y2": 0.7},   # bottom
        {"t": "l", "x1": 0.2, "y1": 0.7, "x2": 0.2, "y2": 0.2},   # left
        {"t": "l", "x1": 0.5, "y1": 0.2, "x2": 0.5, "y2": 0.45},  # tap from top
        {"t": "r", "x": 0.46, "y": 0.45, "w": 0.08, "h": 0.05},   # a component box
    ], "words": [{"x0": 0.46, "y0": 0.40, "x1": 0.54, "y1": 0.44, "t": "R1"},
                 {"x0": 0.46, "y0": 0.62, "x1": 0.54, "y1": 0.66, "t": "24V"}]}
    g = graph_from_paths(raw)
    print("counts:", g["counts"], "confidence:", g["confidence"])
    print("comps:", g["comps"])
    assert g["counts"]["nodes"] >= 5 and g["counts"]["edges"] >= 5, "snap failed"
    assert g["counts"]["nets"] == 1, "expected one connected net, got %d" % g["counts"]["nets"]
    assert any(c["ref"] == "R1" for c in g["comps"]), "label attach failed"
    print("SELFTEST OK")

if __name__ == "__main__":
    if "--selftest" in sys.argv: _selftest()
    elif "--pdf" in sys.argv:
        i = sys.argv.index("--pdf"); pdf = sys.argv[i+1]; pg = int(sys.argv[i+2]) if len(sys.argv) > i+2 else 1
        g = graph_for(pdf, pg); print(json.dumps(g["counts"]), "conf", g["confidence"])
    else:
        print("schemgraph: use --selftest, or import graph_for()/ensure().")
