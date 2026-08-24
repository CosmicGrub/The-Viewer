"""dimscad.py -- APPROXIMATE 3-D / CAD from a part's dimensional data. When a real scanned figure or a
supplied CAD model isn't available, we can still give the mechanic a *shape sense* of the part by turning
its measured dimensions into a simple parametric primitive: a bolt/shaft -> cylinder, a bracket/plate ->
box, a washer -> annulus, a nut -> hex prism. Output is (a) a dimensioned isometric SVG preview to show
inline, and (b) a parametric OBJ mesh that drops straight into the existing 3-D library (localmodel.py
reads index/models3d/<NSN>.obj).

Dimensions come from PUBLOG named characteristics ('OVERALL LENGTH' -> '12 IN', 'DIAMETER' -> '.50 IN')
and/or the Masterfile. Clearly labelled APPROXIMATE -- it is a dimensional sketch, never a substitute for
the cited figure. Pure-python (math only), offline, no deps. Read-only."""

from __future__ import annotations
import math, re

import cad_mesh

_NUM = re.compile(r"[-+]?(?:\d{1,6}(?:,\d{3})*(?:\.\d+)?|\.\d+)")
_UNIT_TO_IN = {"in": 1.0, "inch": 1.0, "inches": 1.0, '"': 1.0, "ft": 12.0, "foot": 12.0, "feet": 12.0,
               "mm": 1 / 25.4, "cm": 1 / 2.54, "m": 39.3701}


def parse_dim(text):
    """'12.5 IN' / '.50 in' / '30 mm' -> value in INCHES (float) or None."""
    if not text:
        return None
    m = _NUM.search(str(text))
    if not m:
        return None
    try:
        v = float(m.group(0).replace(",", ""))
    except Exception:
        return None
    tail = str(text)[m.end():].strip().lower()
    unit = "in"
    for u in ("inches", "inch", "mm", "cm", "ft", "feet", "foot", "in", "m", '"'):
        if tail.startswith(u):
            unit = u
            break
    return round(v * _UNIT_TO_IN.get(unit, 1.0), 4)


_ROLE_KEYS = [
    ("diameter", ("diameter", "dia", "outside diameter", "o.d", "od ", "bolt diameter", "thread diameter")),
    ("inside_diameter", ("inside diameter", "inner diameter", "i.d", "bore", "id ")),
    ("length", ("length", "overall length", "long", "height overall", "len ")),
    ("width", ("width", "wide", "across flats", "flat")),
    ("height", ("height", "thickness", "thick", "depth")),
    ("thread", ("thread size", "thread", "pitch")),
]


def dims_from_characteristics(charx):
    """charx: iterable of {requirement, reply} (PUBLOG). -> {role: inches}. Best-effort keyword match."""
    dims = {}
    for c in charx or []:
        req = (c.get("requirement") or c.get("mrc") or "").lower()
        val = parse_dim(c.get("reply"))
        if val is None or val <= 0:
            continue
        for role, keys in _ROLE_KEYS:
            if any(k in req for k in keys) and role not in dims:
                dims[role] = val
                break
    return dims


def pick_primitive(item_name, dims):
    """Choose a primitive from the item name + which dims are present."""
    n = (item_name or "").lower()
    if dims.get("inside_diameter") and dims.get("diameter"):
        return "washer"
    if any(w in n for w in ("nut", "hex")):
        return "hex"
    if any(w in n for w in ("washer", "ring", "gasket", "seal", "o-ring")):
        return "washer"
    if any(w in n for w in ("bolt", "screw", "shaft", "pin", "rod", "stud", "bearing", "bushing", "spacer", "fitting", "cylinder")):
        return "cylinder"
    if any(w in n for w in ("plate", "bracket", "panel", "cover", "bar", "block", "mount", "gasket")):
        return "box"
    # fall back on geometry: has a diameter -> cylinder; else box
    return "cylinder" if dims.get("diameter") else "box"


# ---- geometry: parametric OBJ meshes (units = inches) --------------------------------------------
def _cylinder(d, h, seg=24):
    r = max(d, 0.05) / 2.0
    h = max(h, 0.05)
    V, F = [], []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        x, z = r * math.cos(a), r * math.sin(a)
        V.append((x, 0.0, z)); V.append((x, h, z))
    for i in range(seg):
        b0 = 2 * i + 1; b1 = 2 * ((i + 1) % seg) + 1
        t0, t1 = b0 + 1, b1 + 1
        F.append((b0, b1, t1, t0))
    cb = len(V) + 1; V.append((0, 0, 0)); ct = len(V) + 1; V.append((0, h, 0))
    for i in range(seg):
        b0 = 2 * i + 1; b1 = 2 * ((i + 1) % seg) + 1
        F.append((cb, b1, b0)); F.append((ct, b0 + 1, b1 + 1))
    return V, F


def _box(l, w, h):
    # NOTE the axis-mapping gotcha inherited from the original hand-rolled version: the second positional
    # arg here is 'w' (width) but it maps to the mesh's sz (its 3rd axis) below, NOT sy -- 'h' (height) is
    # what maps to sy. Callers (build_obj) rely on this exact l/w/h -> sx/sy/sz assignment.
    l = max(l, 0.05); w = max(w, 0.05); h = max(h, 0.05)
    return cad_mesh.box_mesh(l, h, w, origin="corner")


def _washer(od, idd, th, seg=24):
    ro = max(od, 0.1) / 2.0; ri = min(max(idd, 0.02) / 2.0, ro * 0.9); th = max(th, 0.03)
    V, F = [], []
    for i in range(seg):
        a = 2 * math.pi * i / seg; ca, sa = math.cos(a), math.sin(a)
        V.append((ro * ca, 0, ro * sa)); V.append((ro * ca, th, ro * sa))
        V.append((ri * ca, 0, ri * sa)); V.append((ri * ca, th, ri * sa))
    for i in range(seg):
        o = 4 * i + 1; n = 4 * ((i + 1) % seg) + 1
        F.append((o, n, n + 1, o + 1))            # outer wall
        F.append((o + 2, o + 3, n + 3, n + 2))    # inner wall
        F.append((o, o + 2, n + 2, n))            # bottom ring
        F.append((o + 1, n + 1, n + 3, o + 3))    # top ring
    return V, F


def _hex(af, h):
    r = max(af, 0.1) / math.sqrt(3)              # across-flats -> circumradius
    return _cylinder(2 * r, h, seg=6)


def build_obj(primitive, dims):
    d = dims
    # _cylinder / _washer / _hex hand-roll their own literal 1-based F tuples (offsets baked into the
    # index arithmetic, e.g. `2 * i + 1`). _box() alone delegates to the shared cad_mesh.box_mesh(),
    # which -- like cad_render.py's meshes -- returns 0-based indices; the +1 conversion to match the
    # other three primitives' convention happens right here, at each _box() call site, rather than via
    # a zero_based flag threaded through this function's branches AND its emission loop (that used to
    # mean remembering to update three separate spots for one geometry call -- an easy thing to miss on
    # the next primitive migrated onto cad_mesh). Converting locally, where the 0-based data is produced,
    # keeps the emission loop below a single unconditional path again.
    if primitive == "cylinder":
        V, F = _cylinder(d.get("diameter", d.get("width", 1.0)), d.get("length", d.get("height", 2.0)))
    elif primitive == "box":
        V, F = _box(d.get("length", 2.0), d.get("width", 1.0), d.get("height", 0.5))
        F = [tuple(i + 1 for i in f) for f in F]
    elif primitive == "washer":
        V, F = _washer(d.get("diameter", 1.0), d.get("inside_diameter", 0.5), d.get("height", 0.1))
    elif primitive == "hex":
        V, F = _hex(d.get("width", d.get("diameter", 0.75)), d.get("height", d.get("length", 0.5)))
    else:
        V, F = _box(2.0, 1.0, 0.5)
        F = [tuple(i + 1 for i in f) for f in F]
    out = ["# THE VIEWER - approximate parametric model from dimensions (dimscad.py)",
           "# primitive=%s  dims_in=%s" % (primitive, {k: d[k] for k in d})]
    for (x, y, z) in V:
        out.append("v %.4f %.4f %.4f" % (x, y, z))
    for f in F:
        out.append("f " + " ".join(str(i) for i in f))
    return "\n".join(out) + "\n"


# ---- dimensioned isometric SVG preview -----------------------------------------------------------
def _iso(x, y, z, s, ox, oy):
    c = math.cos(math.radians(30)); si = math.sin(math.radians(30))
    return (ox + (x - z) * c * s, oy - (y - (x + z) * si) * s)


def render_svg(primitive, dims, item_name="", w=460, h=360):
    ln = dims.get("length") or dims.get("height") or 2.0
    di = dims.get("diameter") or dims.get("width") or 1.0
    wd = dims.get("width") or di
    hh = dims.get("height") or (di if primitive != "box" else 0.5)
    big = max(ln, di, wd, hh, 0.1)
    s = 110.0 / big
    ox, oy = w / 2.0, h / 2.0 + 40
    P = ['<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI,Arial,sans-serif">' % (w, h)]
    P.append('<rect width="%d" height="%d" fill="#0c1116"/>' % (w, h))
    def line(a, b, col="#7fb8d6", sw=1.6):
        P.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%.1f"/>' % (a[0], a[1], b[0], b[1], col, sw))
    def label(x, y, txt, col="#e8c07a"):
        P.append('<text x="%.1f" y="%.1f" font-size="12" font-weight="700" fill="%s">%s</text>' % (x, y, col, txt))

    if primitive == "box":
        l, wi, he = ln, wd, hh
        verts = [(0, 0, 0), (l, 0, 0), (l, 0, wi), (0, 0, wi), (0, he, 0), (l, he, 0), (l, he, wi), (0, he, wi)]
        p = [_iso(x, y, z, s, ox, oy) for (x, y, z) in verts]
        for a, b in [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]:
            line(p[a], p[b])
        label((p[0][0] + p[1][0]) / 2 - 8, p[0][1] + 20, "L %.2f in" % l)
        label((p[1][0] + p[2][0]) / 2 + 6, (p[1][1] + p[2][1]) / 2 + 14, "W %.2f in" % wi)
        label(p[4][0] - 46, (p[0][1] + p[4][1]) / 2, "H %.2f in" % he)
    else:
        # cylinder / hex / washer -> draw an extruded circle (ellipse caps) with a diameter + length call-out
        d = di if primitive != "washer" else di
        r = d / 2.0
        top = _iso(0, ln, 0, s, ox, oy); bot = _iso(0, 0, 0, s, ox, oy)
        rx = r * s * math.cos(math.radians(30)); ry = r * s * math.sin(math.radians(30)) + r * s * 0.28
        for (cx, cy) in (top, bot):
            P.append('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="none" stroke="#7fb8d6" stroke-width="1.6"/>' % (cx, cy, rx, ry))
        line((top[0] - rx, top[1]), (bot[0] - rx, bot[1])); line((top[0] + rx, top[1]), (bot[0] + rx, bot[1]))
        if primitive == "washer" and dims.get("inside_diameter"):
            ir = dims["inside_diameter"] / 2.0
            irx = ir * s * math.cos(math.radians(30)); iry = ir * s * math.sin(math.radians(30)) + ir * s * 0.28
            P.append('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="none" stroke="#9aa6b6" stroke-width="1.3"/>' % (top[0], top[1], irx, iry))
            label(top[0] - 20, top[1] - ry - 8, "ID %.2f in" % dims["inside_diameter"])
        label(top[0] - 22, top[1] - ry - 10 if primitive != "washer" else top[1] - ry - 26, "%s %.2f in" % ("AF" if primitive == "hex" else "Ø", d))
        label(bot[0] + rx + 8, (top[1] + bot[1]) / 2, "L %.2f in" % ln)

    P.append('<text x="12" y="20" font-size="12.5" font-weight="700" fill="#8a98a8">Approximate model (%s) - from dimensions</text>' % primitive)
    P.append('<text x="12" y="%d" font-size="10.5" fill="#6b7280">Dimensional sketch only - confirm against the cited figure.</text>' % (h - 12))
    P.append("</svg>")
    return "\n".join(P)


def build(item_name, dims):
    """Top-level: pick a primitive and return the SVG + OBJ + what was used."""
    dims = {k: v for k, v in (dims or {}).items() if isinstance(v, (int, float)) and v > 0}
    prim = pick_primitive(item_name, dims)
    return {"item_name": item_name, "primitive": prim, "dims_in": dims,
            "svg": render_svg(prim, dims, item_name), "obj": build_obj(prim, dims),
            "enough": bool(dims)}


# --------------------------------------------------------------------------- #
# self-test: `python dimscad.py`                                               #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    assert parse_dim("12.5 IN") == 12.5, parse_dim("12.5 IN")
    assert parse_dim(".50 in") == 0.5
    assert parse_dim("25.4 mm") == 1.0, parse_dim("25.4 mm")
    print("dimscad parse_dim OK")

    charx = [{"requirement": "OVERALL LENGTH", "reply": "3.00 IN"},
             {"requirement": "THREAD DIAMETER", "reply": ".50 IN"},
             {"requirement": "MOUNTING", "reply": "PAD"}]
    dims = dims_from_characteristics(charx)
    assert dims.get("length") == 3.0 and dims.get("diameter") == 0.5, dims
    print("dimscad dims_from_characteristics OK -> %s" % dims)

    r = build("BOLT, MACHINE", dims)
    assert r["primitive"] == "cylinder", r["primitive"]
    assert r["obj"].count("\nv ") >= 24, "OBJ too small"
    assert "L 3.00 in" in r["svg"] and "<svg" in r["svg"], "SVG missing dims"
    print("dimscad build(cylinder) OK -> OBJ %d verts, SVG %d bytes"
          % (r["obj"].count("\nv "), len(r["svg"])))

    b = build("BRACKET, MOUNTING", {"length": 4.0, "width": 2.0, "height": 0.25})
    assert b["primitive"] == "box" and "f " in b["obj"], b["primitive"]
    assert "L 4.00 in" in b["svg"] and "W 2.00 in" in b["svg"], "box SVG dims"
    print("dimscad build(box) OK")

    wsh = build("WASHER, FLAT", {"diameter": 1.0, "inside_diameter": 0.5, "height": 0.1})
    assert wsh["primitive"] == "washer", wsh["primitive"]
    print("dimscad build(washer) OK")
    print("dimscad self-test PASS")

# END OF FILE
