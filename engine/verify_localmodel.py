#!/usr/bin/env python3
"""Verify localmodel.py: write a sample OBJ + ASCII STL + binary STL into index/models3d/, parse each to {V,F},
then clean up. Host-side. Exercises find/status/mesh_vf + both STL paths."""
import os, sys, struct
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import localmodel

# inject a minimal core so models_dir() resolves to <repo>/index/models3d
class _Core: DB_PATH = os.path.join(os.path.dirname(HERE), "index", "viewer.db")
localmodel.core = _Core
D = localmodel.models_dir()
print("models dir:", D)

# unit cube: 8 verts, 12 triangles
VERTS = [(0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)]
TRIS = [(0,1,2),(0,2,3),(4,6,5),(4,7,6),(0,4,5),(0,5,1),(1,5,6),(1,6,2),(2,6,7),(2,7,3),(3,7,4),(3,4,0)]

def write_obj(p):
    with open(p,"w") as f:
        for v in VERTS: f.write("v %g %g %g\n"%v)
        for t in TRIS: f.write("f %d %d %d\n"%(t[0]+1,t[1]+1,t[2]+1))
def write_ascii_stl(p):
    with open(p,"w") as f:
        f.write("solid cube\n")
        for t in TRIS:
            f.write("facet normal 0 0 0\n outer loop\n")
            for i in t: f.write("  vertex %g %g %g\n"%VERTS[i])
            f.write(" endloop\nendfacet\n")
        f.write("endsolid cube\n")
def write_bin_stl(p):
    with open(p,"wb") as f:
        f.write(b"\0"*80); f.write(struct.pack("<I", len(TRIS)))
        for t in TRIS:
            f.write(struct.pack("<3f",0,0,0))
            for i in t: f.write(struct.pack("<3f",*VERTS[i]))
            f.write(struct.pack("<H",0))

cases = [("TEST-LM-OBJ","obj",write_obj,".obj"), ("TEST-LM-ASTL","stl",write_ascii_stl,".stl"), ("TEST-LM-BSTL","stl",write_bin_stl,".stl")]
made = []
ok = True
try:
    for nsn,fmt,writer,ext in cases:
        p = os.path.join(D, nsn+ext); writer(p); made.append(p)
        st = localmodel.status(nsn)
        vf = localmodel.mesh_vf(nsn)
        good = bool(st.get("exists") and st.get("fmt")==fmt and vf and len(vf["V"])>=3 and len(vf["F"])>=12)
        ok = ok and good
        print("%-13s fmt=%s exists=%s -> verts=%s faces=%s  %s" % (
            nsn, st.get("fmt"), st.get("exists"),
            (len(vf["V"]) if vf else 0), (len(vf["F"]) if vf else 0), "OK" if good else "FAIL"))
finally:
    for p in made:
        try: os.remove(p)
        except Exception: pass
    print("cleaned up", len(made), "test files")
print("RESULT:", "ALL OK" if ok else "FAILURES")
sys.exit(0 if ok else 1)
