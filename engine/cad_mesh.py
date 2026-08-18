#!/usr/bin/env python3
"""cad_mesh.py -- tiny shared geometry primitives used by BOTH cad_render.py (the family-builder library
behind the rendered CAD "photos") and dimscad.py (the approximate parametric OBJ built straight from PUBLOG
dimensions). Split out as its own leaf module -- rather than having either file import the other -- because
cad_render.py is already the far more heavily-imported of the two (routes.py, make_cad.py, bench/verify
scripts, ...), so importing it FROM dimscad.py would be a one-way dependency with no offsetting symmetry,
and the reverse (cad_render importing dimscad) has no precedent either. A shared module with zero
dependencies on either caller is the safe home. Pure math, stdlib only.

Every mesh here is returned as 0-based (V, F): V a list of [x,y,z] float triples, F a list of int-index
face tuples (quads, wound so each face's outward-right-hand-rule normal points away from the solid's
centroid) indexing into V starting at 0 -- matching cad_render.py's existing internal convention. Wavefront
OBJ is 1-indexed, so callers that emit OBJ text must add 1 at emission time (see cad_render.to_obj() and
dimscad.build_obj()); this module never bakes a 1-based convention into geometry itself.
"""


def box_mesh(sx, sy, sz, origin="center"):
    """An axis-aligned rectangular box: sx along x, sy along y, sz along z.

    origin='center' -> box is centered on the origin, spanning [-sx/2,sx/2] x [-sy/2,sy/2] x [-sz/2,sz/2]
                        (cad_render.py's convention -- every part family is built around its own centroid).
    origin='corner'  -> one corner sits at the origin, spanning [0,sx] x [0,sy] x [0,sz]
                        (dimscad.py's convention -- a simple from-the-ground-up dimensional sketch).

    Returns 0-based (V, F): 8 vertices, 6 quad faces, every face wound outward-facing regardless of which
    origin mode is used (translation and positive per-axis scaling both preserve winding orientation).
    """
    if origin == "corner":
        lo_x = lo_y = lo_z = 0.0
        hi_x, hi_y, hi_z = sx, sy, sz
    else:
        lo_x, hi_x = -sx / 2.0, sx / 2.0
        lo_y, hi_y = -sy / 2.0, sy / 2.0
        lo_z, hi_z = -sz / 2.0, sz / 2.0
    V = [[lo_x, lo_y, lo_z], [hi_x, lo_y, lo_z], [hi_x, hi_y, lo_z], [lo_x, hi_y, lo_z],
         [lo_x, lo_y, hi_z], [hi_x, lo_y, hi_z], [hi_x, hi_y, hi_z], [lo_x, hi_y, hi_z]]
    F = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [2, 3, 7, 6], [1, 2, 6, 5], [0, 4, 7, 3]]
    return V, F

# END OF FILE
