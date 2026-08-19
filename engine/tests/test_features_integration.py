#!/usr/bin/env python3
"""Integration coverage for the 0.90-0.95 imagery/CAD/schematic features AFTER v0.96 THE RESTRUCTURE —
proves the monolith->features/ split kept every route registered and every capability working.
Self-contained; no corpus. Run:  python tests/test_features_integration.py   (exit 0 = all pass)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import viewer_app as V   # noqa: F401  (importing the thin shell must trigger features/routes registration)

passed, failed = [], []
def ok(name, cond):
    (passed if cond else failed).append(name)

# --- the declarative registry has my routes (would catch a route dropped during the split) ---
GET = set()
try:
    from features import registry as REG
    GET = set(REG.GET.keys())
except Exception as e:
    failed.append("registry_import(%s)" % e)
for path in ("/cadimg", "/cadspin", "/cadstl", "/cadobj", "/api/cadmaterial",
             "/api/schempaths", "/api/schemgraph", "/api/localmodel", "/api/localmodel_mesh"):
    ok("route " + path, path in GET)

# --- cad_render: colour+texture engine (CAD_VERSION 7) still whole ---
try:
    import cad_render as C
    ok("cad_version_7", C.CAD_VERSION == "7")
    m = C.material_for("BRACKET, MOUNTING", "COLOR OLIVE DRAB", "5340-00-100-0010")
    ok("material_for_shape", isinstance(m, dict) and m.get("color", "").startswith("#")
       and "klass_id" in m and isinstance(m.get("gl"), list) and len(m["gl"]) == 3)
    if C.Image is not None:
        sheet, frames = C.render_spin("BEARING, BALL",
                                      "OUTSIDE DIAMETER 52 MM; INSIDE DIAMETER 25 MM; WIDTH 15 MM",
                                      "3110-00-100-0001", n=6, style="v3", fw=140, fh=110)
        ok("render_spin_frames", frames == 6 and sheet.width == 140 * 6 and sheet.height == 110)
        # colour+texture apply on EVERY tier now (v1 no longer forced grey)
        im1 = C.render("GASKET", "OUTSIDE DIAMETER 3 IN; RUBBER", "5330-00-100-0004", w=120, h=100, style="v1")
        ok("v1_renders", im1 is not None and im1.size == (120, 100))
    else:
        failed.append("PIL_unavailable")
except Exception as e:
    failed.append("cad_render(%s)" % e)

# --- schemgraph: netlist inference (T-junction tap collapses to ONE net) ---
try:
    import schemgraph as S
    raw = {"w": 1000, "h": 700, "has_vector": True, "paths": [
        {"t": "l", "x1": 0.2, "y1": 0.2, "x2": 0.8, "y2": 0.2},
        {"t": "l", "x1": 0.8, "y1": 0.2, "x2": 0.8, "y2": 0.7},
        {"t": "l", "x1": 0.8, "y1": 0.7, "x2": 0.2, "y2": 0.7},
        {"t": "l", "x1": 0.2, "y1": 0.7, "x2": 0.2, "y2": 0.2},
        {"t": "l", "x1": 0.5, "y1": 0.2, "x2": 0.5, "y2": 0.45},
    ], "words": [{"x0": 0.46, "y0": 0.40, "x1": 0.54, "y1": 0.44, "t": "R1"}]}
    g = S.graph_from_paths(raw)
    ok("schemgraph_one_net", g["counts"]["nets"] == 1)
    ok("schemgraph_component", any(c.get("ref") == "R1" for c in g["comps"]))
except Exception as e:
    failed.append("schemgraph(%s)" % e)

# --- localmodel: OBJ parse round-trip (authoritative local models) ---
try:
    import localmodel as L, tempfile
    class _Core: DB_PATH = os.path.join(tempfile.mkdtemp(prefix="lm_"), "viewer.db")
    L.core = _Core
    d = L.models_dir(); nsn = "TEST-INT-OBJ"
    with open(os.path.join(d, nsn + ".obj"), "w") as f:
        for v in [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]:
            f.write("v %g %g %g\n" % v)
        f.write("f 1 2 3\nf 1 3 4\n")
    vf = L.mesh_vf(nsn)
    ok("localmodel_parse", bool(vf) and len(vf["V"]) == 4 and len(vf["F"]) == 2 and vf.get("local") is True)
except Exception as e:
    failed.append("localmodel(%s)" % e)

# --- embed.py: search() caches the loaded (embeddings.npy, embeddings_ids.tsv) pair keyed by
# index_dir + both files' mtimes, instead of _np.load()-ing fresh off disk on EVERY call (unlike the
# keyword-search path's TTL'd LRU -- features/routes.py's _SEARCH_LRU, ~line 134). Confirms (a) a
# second search() against an unchanged index_dir does NOT trigger another real np.load, and (b)
# rebuilding embeddings.npy (BUILD-EMBEDDINGS.bat reran) DOES invalidate the cache and trigger
# exactly one more load, so a rebuilt index is picked up rather than silently served stale.
try:
    import embed as EMB, numpy as ENP, unittest.mock as mock, json as _json, time as _time

    if not EMB._OK:
        failed.append("embed_cache(numpy unavailable)")
    else:
        ed = tempfile.mkdtemp(prefix="embed_cache_")
        npy_p = os.path.join(ed, "embeddings.npy")
        tsv_p = os.path.join(ed, "embeddings_ids.tsv")
        ENP.save(npy_p, ENP.zeros((2, EMB.DIM), dtype=ENP.float32))
        with open(tsv_p, "w", encoding="utf-8") as f:
            f.write("docA\t1\ndocB\t2\n")
        # Meta stamped as "sentence-transformers" so _index_is_stale() short-circuits to False
        # regardless of which backend is actually active in this environment (the hash-bucket
        # version check only applies to hash-fallback indexes) -- irrelevant to what's under test here.
        with open(EMB._meta_path(ed), "w", encoding="utf-8") as f:
            _json.dump({"backend": "sentence-transformers", "hash_algo_version": None}, f)

        EMB._ARR_CACHE.clear()
        with mock.patch.object(EMB._np, "load", wraps=ENP.load) as m_load:
            r1 = EMB.search("hello", ed, top=5)
            r2 = EMB.search("world", ed, top=5)
            ok("embed_cache_hit_no_reload",
               m_load.call_count == 1 and r1.get("ready") is True and r2.get("ready") is True)

            # Rebuild: 3 rows instead of 2, mtime bumped forward explicitly (os.utime, not a sleep+
            # rewrite) so this can't flake on a filesystem whose mtime resolution could otherwise
            # make a fast rewrite look "unchanged" to the cache.
            ENP.save(npy_p, ENP.ones((3, EMB.DIM), dtype=ENP.float32))
            with open(tsv_p, "w", encoding="utf-8") as f:
                f.write("docA\t1\ndocB\t2\ndocC\t3\n")
            future = _time.time() + 5
            os.utime(npy_p, (future, future)); os.utime(tsv_p, (future, future))

            r3 = EMB.search("hello", ed, top=5)
            ok("embed_cache_invalidates_on_rebuild",
               m_load.call_count == 2 and r3.get("ready") is True)
        EMB._ARR_CACHE.clear()
except Exception as e:
    failed.append("embed_cache(%s)" % e)

for n in passed: print("PASS", n)
for n in failed: print("FAIL", n)
print("\n%d passed, %d failed (of %d integration checks)" % (len(passed), len(failed), len(passed) + len(failed)))
sys.exit(1 if failed else 0)
