#!/usr/bin/env python3
"""THE VIEWER -- LOCAL 3-D MODELS: wire a real, user-provided model file into the 3-D view, replacing the
parametric "placeholder" when one exists. Authoritative (NOT the AI 'approximation' path in image3d_experiment).

Drop a file named by the part's NSN into the sidecar folder  index/models3d/  :
    <NSN>.obj   or   <NSN>.stl    (ASCII or binary STL)
e.g.  index/models3d/5305-01-674-1467.obj
The 3-D modal then loads THAT mesh (auto-centred/auto-fit by gl3d.js) instead of the representative geometry.

Pure stdlib (struct for binary STL); never writes the index (R1/R6). `core` is injected by viewer_app.
  localmodel.status(nsn)   -> {exists, fmt, mesh_url, ...}
  localmodel.mesh_vf(nsn)  -> {V, F, local:True, fmt} | None
"""
import os, struct

core = None
HERE = os.path.dirname(os.path.abspath(__file__))
EXTS = (".obj", ".stl")

# v1.13: AI-generated ILLUSTRATIVE tier. A model dropped in  index/models3d/ai/<NSN>.obj|.stl  (e.g. a
# Meshy image-to-3D export) is treated as an APPROXIMATION -- never authoritative. An authoritative file
# in the root folder ALWAYS wins, so a real model can't be shadowed by a generated one. R13: a generated
# mesh is plausible, not measured, so it is loudly badged and must never be used for part ID / measurement.
AI_SUBDIR = "ai"
_CAVEAT = ("AI-GENERATED APPROXIMATION -- illustrative only. NOT to scale, NOT verified, and NOT for part "
           "identification or measurement. Confirm against the manual figure or an authoritative model.")


def models_dir():
    d = os.path.join(os.path.dirname(core.DB_PATH), "models3d")
    try: os.makedirs(d, exist_ok=True)
    except Exception: pass
    return d


def ai_dir():
    """index/models3d/ai/ -- the AI-generated illustrative tier (auto-created)."""
    d = os.path.join(models_dir(), AI_SUBDIR)
    try: os.makedirs(d, exist_ok=True)
    except Exception: pass
    return d


def _safe(nsn):
    return "".join(ch for ch in (nsn or "") if ch.isalnum() or ch in "-_")


def _find_in(d, safe):
    """(path, fmt) for a model named `safe` in directory d, or (None, None). Case-insensitive ext."""
    for ext in EXTS:
        p = os.path.join(d, safe + ext)
        if os.path.exists(p) and os.path.getsize(p) > 0:
            return p, ext.lstrip(".")
    try:                                                  # case-insensitive sweep (handles .OBJ / .STL)
        for fn in os.listdir(d):
            root, ext = os.path.splitext(fn)
            if root == safe and ext.lower() in EXTS:
                p = os.path.join(d, fn)
                if os.path.getsize(p) > 0:
                    return p, ext.lower().lstrip(".")
    except Exception:
        pass
    return None, None


def find(nsn):
    """AUTHORITATIVE local model only (index/models3d/<NSN>.obj|.stl). (path, fmt) or (None, None).
    Back-compatible: the AI illustrative tier (ai/ subfolder) is resolved via find_any()."""
    safe = _safe(nsn)
    if not safe:
        return None, None
    return _find_in(models_dir(), safe)


def find_any(nsn):
    """Resolve a model WITH its tier. Authoritative (root) beats illustrative (ai/) so a generated mesh
    can never shadow a real one. Returns (path, fmt, tier) with tier in {authoritative, illustrative},
    or (None, None, None)."""
    safe = _safe(nsn)
    if not safe:
        return None, None, None
    p, fmt = _find_in(models_dir(), safe)
    if p:
        return p, fmt, "authoritative"
    p, fmt = _find_in(ai_dir(), safe)
    if p:
        return p, fmt, "illustrative"
    return None, None, None


def status(nsn):
    p, fmt, tier = find_any(nsn)
    exists = bool(p)
    illustrative = tier == "illustrative"
    return {"nsn": (nsn or "").strip(), "exists": exists, "fmt": fmt,
            "tier": tier, "authoritative": tier == "authoritative", "illustrative": illustrative,
            "mesh_url": ("/api/localmodel_mesh?nsn=%s" % (nsn or "")) if exists else None,
            "filename": os.path.basename(p) if p else None,
            "note": (_CAVEAT if illustrative else
                     "Authoritative local model (your file) — replaces the representative placeholder."),
            "caveat": _CAVEAT if illustrative else None,
            "dir": models_dir(), "ai_dir": ai_dir()}


# ---------------- parsers ----------------
def _parse_obj(path, max_faces):
    V = []; F = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            if ln.startswith("v "):
                p = ln.split()
                if len(p) >= 4:
                    try: V.append([float(p[1]), float(p[2]), float(p[3])])
                    except ValueError: pass
            elif ln.startswith("f "):
                idx = [t.split("/")[0] for t in ln.split()[1:]]
                idx = [int(t) for t in idx if t.lstrip("-").isdigit()]
                if len(idx) >= 3:
                    idx = [(i - 1) if i > 0 else (len(V) + i) for i in idx]   # 1-indexed; support negatives
                    for k in range(1, len(idx) - 1):
                        F.append([idx[0], idx[k], idx[k + 1]])
                        if len(F) >= max_faces: break
            if len(F) >= max_faces: break
    return V, F


def _stl_is_binary(path):
    size = os.path.getsize(path)
    if size < 84:
        return False
    with open(path, "rb") as f:
        head = f.read(80)
        cnt = struct.unpack("<I", f.read(4))[0]
    # binary STL is exactly 84 + 50*count bytes; ASCII starts with "solid" and won't match that size
    if 84 + 50 * cnt == size:
        return True
    return not head[:5].lower().startswith(b"solid")


def _parse_stl(path, max_faces):
    V = []; F = []
    if _stl_is_binary(path):
        with open(path, "rb") as f:
            f.read(80); n = struct.unpack("<I", f.read(4))[0]
            n = min(n, max_faces)
            for _ in range(n):
                data = f.read(50)
                if len(data) < 50: break
                vals = struct.unpack("<12fH", data)   # normal(3) + 3 verts(9) + attr
                b = len(V)
                V.append([vals[3], vals[4], vals[5]]); V.append([vals[6], vals[7], vals[8]]); V.append([vals[9], vals[10], vals[11]])
                F.append([b, b + 1, b + 2])
    else:
        tri = []
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for ln in f:
                ln = ln.strip()
                if ln.startswith("vertex"):
                    p = ln.split()
                    if len(p) >= 4:
                        try: tri.append([float(p[1]), float(p[2]), float(p[3])])
                        except ValueError: pass
                        if len(tri) == 3:
                            b = len(V); V += tri; F.append([b, b + 1, b + 2]); tri = []
                            if len(F) >= max_faces: break
    return V, F


def mesh_vf(nsn, max_faces=300000):
    """Parse the local model into {V,F} for gl3d.js, carrying its TIER so the viewer can badge an AI
    illustrative mesh loudly. Returns None if absent/unparseable."""
    p, fmt, tier = find_any(nsn)
    if not p:
        return None
    try:
        if fmt == "obj":
            V, F = _parse_obj(p, max_faces)
        elif fmt == "stl":
            V, F = _parse_stl(p, max_faces)
        else:
            return None
    except Exception:
        return None
    if not V or not F:
        return None
    return {"V": V, "F": F, "local": True, "fmt": fmt, "faces": len(F), "verts": len(V),
            "tier": tier, "illustrative": tier == "illustrative",
            "caveat": _CAVEAT if tier == "illustrative" else None}
