#!/usr/bin/env python3
"""THE VIEWER -- EXPERIMENTAL local image->3D scaffold (opt-in, NOT authoritative).

This is a *framework*, not a shipped model. It lets you optionally wire a LOCAL image->3D model (e.g. TripoSR
/ InstantMesh / Shap-E) that runs on YOUR GPU to turn a part's cited figure crop into a rough mesh, shown in
the 3D modal's "Approximation" tab -- always watermarked "ARTISTIC APPROXIMATION - NOT TO SCALE". It is
deliberately decoupled and disabled until you configure a backend, because AI-generated geometry is an
approximation and must never be treated as engineering-accurate in a maintenance tool.

Configure a backend either way:
  * env  VIEWER_IMG3D_CMD = 'python C:\\models\\triposr_run.py "{in}" "{out}"'   (uses {in}=PNG, {out}=OBJ)
  * or a file engine/image3d_backend.txt containing that same command template.
If neither is set, the feature reports 'not configured' and the UI shows setup guidance.

Meshes are written to a SIDECAR dir (index/mesh3d/); the index is never written (R1/R6). `core` is injected.
"""
import os, subprocess, shlex, time

core = None
HERE = os.path.dirname(os.path.abspath(__file__))


def _mesh_dir():
    d = os.path.join(os.path.dirname(core.DB_PATH), "mesh3d")
    try: os.makedirs(d, exist_ok=True)
    except Exception: pass
    return d


def backend_cmd():
    """The configured local image->3D command template, or '' if not configured."""
    c = os.environ.get("VIEWER_IMG3D_CMD", "").strip()
    if c:
        return c
    f = os.path.join(HERE, "image3d_backend.txt")
    if os.path.exists(f):
        try:
            t = open(f, "r", encoding="utf-8").read().strip()
            if t and not t.startswith("#"):
                return t
        except Exception:
            pass
    return ""


def _mesh_path(nsn):
    safe = "".join(ch for ch in (nsn or "") if ch.isalnum() or ch in "-_")
    return os.path.join(_mesh_dir(), "%s.obj" % safe) if safe else None


def status(nsn):
    """Is a backend configured? Is there already a generated mesh for this NSN?"""
    mp = _mesh_path(nsn)
    exists = bool(mp and os.path.exists(mp) and os.path.getsize(mp) > 0)
    return {"nsn": (nsn or "").strip(), "configured": bool(backend_cmd()),
            "exists": exists, "mesh_url": ("/api/image3d_mesh?nsn=%s" % (nsn or "")) if exists else None,
            "note": "Experimental, artistic approximation — never engineering-accurate.",
            "setup": "docs/IMAGE3D-SETUP.md" if not backend_cmd() else None}


def generate(nsn, image_path, timeout=600):
    """Run the configured backend to turn image_path (a figure crop PNG) into a mesh for this NSN.
    Returns a status dict. No-op with a clear message if no backend is configured."""
    cmd = backend_cmd()
    if not cmd:
        return {"ok": False, "configured": False, "error": "no local image->3D backend configured",
                "setup": "docs/IMAGE3D-SETUP.md"}
    if not image_path or not os.path.exists(image_path):
        return {"ok": False, "configured": True, "error": "source figure crop not found"}
    mp = _mesh_path(nsn)
    if not mp:
        return {"ok": False, "configured": True, "error": "bad nsn"}
    filled = cmd.replace("{in}", image_path).replace("{out}", mp)
    try:
        t0 = time.time()
        p = subprocess.run(shlex.split(filled, posix=(os.name != "nt")), timeout=timeout,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        ok = (p.returncode == 0 and os.path.exists(mp) and os.path.getsize(mp) > 0)
        return {"ok": ok, "configured": True, "nsn": (nsn or "").strip(),
                "seconds": round(time.time() - t0, 1),
                "mesh_url": ("/api/image3d_mesh?nsn=%s" % nsn) if ok else None,
                "error": None if ok else "backend ran but produced no mesh (rc=%s)" % p.returncode}
    except subprocess.TimeoutExpired:
        return {"ok": False, "configured": True, "error": "backend timed out (%ss)" % timeout}
    except Exception as e:
        return {"ok": False, "configured": True, "error": "backend error: %s" % e}


def mesh_vf(nsn, max_faces=200000):
    """Parse the generated OBJ into {V,F} for gl3d.js. Returns None if absent/unparseable."""
    mp = _mesh_path(nsn)
    if not (mp and os.path.exists(mp)):
        return None
    V = []; F = []
    try:
        with open(mp, "r", encoding="utf-8", errors="ignore") as f:
            for ln in f:
                if ln.startswith("v "):
                    p = ln.split()
                    if len(p) >= 4: V.append([float(p[1]), float(p[2]), float(p[3])])
                elif ln.startswith("f "):
                    idx = [int(t.split("/")[0]) for t in ln.split()[1:] if t.split("/")[0].lstrip("-").isdigit()]
                    if len(idx) >= 3:
                        idx = [(i - 1) if i > 0 else (len(V) + i) for i in idx]   # OBJ is 1-indexed; support negatives
                        for k in range(1, len(idx) - 1):
                            F.append([idx[0], idx[k], idx[k + 1]])
                            if len(F) >= max_faces: break
                if len(F) >= max_faces: break
    except Exception:
        return None
    if not V or not F:
        return None
    return {"V": V, "F": F, "approx": True}
