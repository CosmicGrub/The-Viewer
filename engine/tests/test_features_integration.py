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
    # a dark PLATED/OXIDE finish must NOT fall into the "dark colour => painted" heuristic: a BLACK part
    # FINISHed ZINC PLATED stays metal/shiny (klass_id 1, gl metallic 1.0), matching material_feature.py's
    # /api/part_material verdict for the same characteristics instead of contradicting it.
    m2 = C.material_for("BOLT, MACHINE",
                        "MATERIAL: STEEL, ALLOY; COLOR: BLACK; FINISH: ZINC PLATED; OVERALL LENGTH: 2.0 IN",
                        "5305-01-111-1111")
    ok("material_for_plated_finish_stays_metal",
       m2["klass"] == "metal" and m2["klass_id"] == 1 and m2["gl"][2] == 1.0)
    # a genuine paint/CARC finish still classifies as painted (non-metallic), regardless of colour brightness
    m3 = C.material_for("BRACKET, MOUNTING", "MATERIAL: STEEL; COLOR: OLIVE DRAB; FINISH: CARC PAINT",
                        "5340-01-222-2222")
    ok("material_for_paint_finish_is_painted", m3["klass"] == "painted" and m3["gl"][2] == 0.0)
    if C.Image is not None:
        sheet, frames = C.render_spin("BEARING, BALL",
                                      "OUTSIDE DIAMETER 52 MM; INSIDE DIAMETER 25 MM; WIDTH 15 MM",
                                      "3110-00-100-0001", n=6, style="v3", fw=140, fh=110)
        ok("render_spin_frames", frames == 6 and sheet.width == 140 * 6 and sheet.height == 110)
        # colour+texture apply on EVERY tier now (v1 no longer forced grey)
        im1 = C.render("GASKET", "OUTSIDE DIAMETER 3 IN; RUBBER", "5330-00-100-0004", w=120, h=100, style="v1")
        ok("v1_renders", im1 is not None and im1.size == (120, 100))
        # ensure()/ensure_spin() write their PNG cache through safeguard.atomic_write (temp file + fsync +
        # os.replace), not a bare im.save(out, "PNG")/sheet.save(out, "PNG") straight onto the final cache
        # path -- the same fix schemgraph.py's and vectorize.py's own cache writes already use, so a crash
        # mid-write (or two ThreadingHTTPServer threads racing the same not-yet-cached NSN) can never leave
        # a truncated file at the exact path the size>0 staleness check would then serve forever.
        import tempfile, shutil, unittest.mock as mock
        import safeguard as _SG
        tdir = tempfile.mkdtemp(prefix="cadcache_")
        try:
            nsn_t, nm_t, ch_t = "5305-01-999-9999", "BOLT,MACHINE", "OVERALL LENGTH: 1.0 IN"
            out1 = C.ensure(nsn_t, nm_t, ch_t, tdir, style="v3")
            ok("ensure_writes_valid_png", out1 is not None and os.path.getsize(out1) > 100)
            im = C.Image.open(out1); im.load()
            ok("ensure_output_is_real_png", im.format == "PNG")
            os.remove(out1)
            with mock.patch.object(_SG, "atomic_write", side_effect=RuntimeError("simulated crash mid-write")):
                out2 = C.ensure(nsn_t, nm_t, ch_t, tdir, style="v3")
            ok("ensure_no_partial_file_on_write_failure", out2 is None and not os.path.exists(out1))

            out3, frames3 = C.ensure_spin(nsn_t, nm_t, ch_t, tdir, n=4, style="v3")
            ok("ensure_spin_writes_valid_png", out3 is not None and frames3 == 4 and os.path.getsize(out3) > 100)
            os.remove(out3)
            with mock.patch.object(_SG, "atomic_write", side_effect=RuntimeError("simulated crash mid-write")):
                out4, frames4 = C.ensure_spin(nsn_t, nm_t, ch_t, tdir, n=4, style="v3")
            ok("ensure_spin_no_partial_file_on_write_failure", out4 is None and frames4 == 0 and not os.path.exists(out3))
        finally:
            shutil.rmtree(tdir, ignore_errors=True)
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

# --- embed.py: _load_arrays() is RPS-aware -- on lite/legacy tier (core.RPS_MODE, read the same
# way features/render_feature.py's _get_doc() reads core.RPS_FLAGS for its open-PDF LRU cap) it
# memory-maps embeddings.npy from disk (np.load(..., mmap_mode='r')) instead of fully copying it
# into RAM. At THE VIEWER's documented default index cap (200,000 rows x 384 dims x float32) a full
# load pins ~293MB of resident RAM for the server's whole process lifetime from a single
# /api/semantic hit -- on the <4GB machines sysprobe.py's own tier profile already calls
# "Legacy / low-power", that's 10-15%+ of total system RAM, two orders of magnitude past what
# feature_flags() already tunes for this same tier elsewhere (SQLite cache_kb 8MB->1MB, doc_cache
# 8->2 open PDFs). Confirms (a) search()'s cosine ranking is IDENTICAL whether the backing array is
# a real in-memory copy (modern tier / core=None, today's unchanged default) or a memmap (lite /
# legacy tier) -- the mmap path isn't just "loads without crashing", it ranks correctly -- and
# (b) the loaded array is actually a numpy.memmap under lite/legacy (not "correct by accident"),
# while modern tier truly stays a plain, fully-resident ndarray (zero behavior change there).
try:
    import embed as EMB3, numpy as ENP3, unittest.mock as mock3, tempfile as _tf3, json as _json3

    if not EMB3._OK:
        failed.append("embed_rps_tier(numpy unavailable)")
    else:
        ed3 = _tf3.mkdtemp(prefix="embed_rps_")
        npy_p3 = os.path.join(ed3, "embeddings.npy")
        tsv_p3 = os.path.join(ed3, "embeddings_ids.tsv")

        # 5 synthetic rows; the forced "query" vector is row 2 scaled + a little noise, so it's
        # unambiguously nearest (by cosine) to doc2 in this 384-dim space -- deterministic (fixed
        # seed), independent of whichever real embed_text() backend happens to be installed here
        # (embed_text() itself is mocked out below so the backend never matters).
        rng3 = ENP3.random.RandomState(42)
        rows3 = rng3.normal(size=(5, EMB3.DIM)).astype(ENP3.float32)
        query_vec3 = (rows3[2] * 3.0 + rng3.normal(scale=0.01, size=EMB3.DIM).astype(ENP3.float32))
        ENP3.save(npy_p3, rows3)
        with open(tsv_p3, "w", encoding="utf-8") as f:
            for i in range(5):
                f.write("doc%d\t%d\n" % (i, i + 1))
        # meta stamped "sentence-transformers" so _index_is_stale() short-circuits False regardless
        # of the real active backend here -- same rationale as the embed_cache block above.
        with open(EMB3._meta_path(ed3), "w", encoding="utf-8") as f:
            _json3.dump({"backend": "sentence-transformers", "hash_algo_version": None}, f)

        class _CoreModern:
            RPS_MODE = "modern"

        class _CoreLite:
            RPS_MODE = "lite"

        class _CoreLegacy:
            RPS_MODE = "legacy"

        with mock3.patch.object(EMB3, "embed_text", return_value=query_vec3):
            EMB3._ARR_CACHE.clear(); EMB3.core = None       # standalone / no DI -> defaults to modern
            r_modern = EMB3.search("query", ed3, top=5)
            arr_modern = EMB3._ARR_CACHE[ed3][2]
            ok("embed_modern_none_core_is_full_ndarray_not_memmap",
               isinstance(arr_modern, ENP3.ndarray) and not isinstance(arr_modern, ENP3.memmap))

            EMB3._ARR_CACHE.clear(); EMB3.core = _CoreModern
            r_modern2 = EMB3.search("query", ed3, top=5)
            arr_modern2 = EMB3._ARR_CACHE[ed3][2]
            ok("embed_modern_tier_is_full_ndarray_not_memmap",
               isinstance(arr_modern2, ENP3.ndarray) and not isinstance(arr_modern2, ENP3.memmap))

            EMB3._ARR_CACHE.clear(); EMB3.core = _CoreLite
            r_lite = EMB3.search("query", ed3, top=5)
            arr_lite = EMB3._ARR_CACHE[ed3][2]
            ok("embed_lite_tier_array_is_memmap",
               isinstance(arr_lite, ENP3.memmap) and not arr_lite.flags.writeable)

            EMB3._ARR_CACHE.clear(); EMB3.core = _CoreLegacy
            r_legacy = EMB3.search("query", ed3, top=5)
            arr_legacy = EMB3._ARR_CACHE[ed3][2]
            ok("embed_legacy_tier_array_is_memmap",
               isinstance(arr_legacy, ENP3.memmap) and not arr_legacy.flags.writeable)

            # Same cosine ranking (order AND score) on every tier -- mmap'd search() isn't silently
            # wrong -- and doc2 (the vector the forced query is nearest to) correctly ranks #1.
            docs_modern = [r["doc"] for r in r_modern["results"]]
            docs_lite = [r["doc"] for r in r_lite["results"]]
            docs_legacy = [r["doc"] for r in r_legacy["results"]]
            ok("embed_rps_tier_ranking_matches_modern",
               docs_modern == docs_lite == docs_legacy and docs_modern[0] == "doc2")
            scores_modern = [r["score"] for r in r_modern["results"]]
            scores_lite = [r["score"] for r in r_lite["results"]]
            scores_legacy = [r["score"] for r in r_legacy["results"]]
            ok("embed_rps_tier_scores_match_modern",
               scores_modern == scores_lite == scores_legacy)

        EMB3._ARR_CACHE.clear(); EMB3.core = None
except Exception as e:
    failed.append("embed_rps_tier(%s)" % e)

for n in passed: print("PASS", n)
for n in failed: print("FAIL", n)
print("\n%d passed, %d failed (of %d integration checks)" % (len(passed), len(failed), len(passed) + len(failed)))
sys.exit(1 if failed else 0)
