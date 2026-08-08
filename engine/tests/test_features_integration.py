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

for n in passed: print("PASS", n)
for n in failed: print("FAIL", n)
print("\n%d passed, %d failed (of %d integration checks)" % (len(passed), len(failed), len(passed) + len(failed)))
sys.exit(1 if failed else 0)
