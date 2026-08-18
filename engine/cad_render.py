#!/usr/bin/env python3
"""THE VIEWER -- CAD-image renderer for the representative 3-D parts.

For any part it classifies the shape (name + NSN supply class), builds the SAME parametric geometry as
partgeo.js, scales it to the FLIS dimensions, and renders a shaded isometric "CAD image" (facet shading +
edge lines) with overall-dimension callouts and a title block. Pure Python + Pillow (no GPU, no heavy deps),
so it runs anywhere the app runs. Output cached to a SIDECAR dir (index/cadcache/) -- never touches the index.

  cad_render.render(name, chars, nsn) -> PIL.Image
  cad_render.ensure(nsn, name, chars, cache_dir) -> path (renders + caches if missing)
  python cad_render.py --demo   # render a few sample families to ./cad_demo/
"""
import os, re, math, sys

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except Exception:
    Image = None

import cad_mesh

CAD_VERSION = "7"          # 7 = colour + material TEXTURE on EVERY tier (v1/v2/v3); max-quality SS4 + key/fill
TAU = math.pi * 2

# ---------------- geometry primitives (Y up; mirror partgeo.js) ----------------
def _cyl(rB, rT=None, h=1.0, seg=64, capB=True, capT=True):
    rT = rB if rT is None else rT
    V, F = [], []; y0, y1 = -h/2, h/2
    for i in range(seg):
        a = i/seg*TAU; c, s = math.cos(a), math.sin(a)
        V.append([c*rB, y0, s*rB]); V.append([c*rT, y1, s*rT])
    for i in range(seg):
        j = (i+1) % seg; F.append([i*2, j*2, j*2+1, i*2+1])
    if capB and rB > 1e-6:
        bc = len(V); V.append([0, y0, 0])
        for i in range(seg): j = (i+1) % seg; F.append([bc, j*2, i*2])
    if capT and rT > 1e-6:
        tc = len(V); V.append([0, y1, 0])
        for i in range(seg): j = (i+1) % seg; F.append([tc, i*2+1, j*2+1])
    return V, F

def _prism(r, h, sides=6, chamfer=None):
    chamfer = r*0.16 if chamfer is None else chamfer
    V, F = [], []; y0, y1 = -h/2, h/2; rc = r-chamfer
    for i in range(sides):
        a = (i+0.5)/sides*TAU; c, s = math.cos(a), math.sin(a)
        V += [[c*rc, y0, s*rc], [c*r, y0+chamfer, s*r], [c*r, y1-chamfer, s*r], [c*rc, y1, s*rc]]
    for i in range(sides):
        j = (i+1) % sides; b, n = i*4, j*4
        F += [[b, n, n+1, b+1], [b+1, n+1, n+2, b+2], [b+2, n+2, n+3, b+3]]
    bc = len(V); V.append([0, y0, 0])
    for i in range(sides): j = (i+1) % sides; F.append([bc, j*4, i*4])
    tc = len(V); V.append([0, y1, 0])
    for i in range(sides): j = (i+1) % sides; F.append([tc, i*4+3, j*4+3])
    return V, F

def _tube(R, r, h, seg=72):
    V, F = [], []; y0, y1 = -h/2, h/2
    for i in range(seg):
        a = i/seg*TAU; c, s = math.cos(a), math.sin(a)
        V += [[c*R, y0, s*R], [c*R, y1, s*R], [c*r, y0, s*r], [c*r, y1, s*r]]
    for i in range(seg):
        j = (i+1) % seg; b, n = i*4, j*4
        F += [[b, n, n+1, b+1], [b+2, b+3, n+3, n+2], [b+1, n+1, n+3, b+3], [b, b+2, n+2, n]]
    return V, F

def _torus(R, rt, su=64, sv=34):
    V, F = [], []
    for i in range(su):
        a = i/su*TAU; ca, sa = math.cos(a), math.sin(a)
        for j in range(sv):
            b = j/sv*TAU; cb, sb = math.cos(b), math.sin(b)
            V.append([(R+rt*cb)*ca, rt*sb, (R+rt*cb)*sa])
    for i in range(su):
        ni = (i+1) % su
        for j in range(sv):
            nj = (j+1) % sv
            F.append([i*sv+j, ni*sv+j, ni*sv+nj, i*sv+nj])
    return V, F

def _sphere(rr, su=40, sv=28):
    V, F = [], []
    for i in range(sv+1):
        th = i/sv*math.pi; st, ct = math.sin(th), math.cos(th)
        for j in range(su):
            ph = j/su*TAU; V.append([rr*st*math.cos(ph), rr*ct, rr*st*math.sin(ph)])
    for i in range(sv):
        for j in range(su):
            nj = (j+1) % su
            F.append([i*su+j, (i+1)*su+j, (i+1)*su+nj, i*su+nj])
    return V, F

def _helix(R, rw, turns, h, su=None, sv=16):
    su = su or max(128, int(turns*48)); V, F = [], []
    for i in range(su+1):
        u = i/su; a = u*turns*TAU; y = -h/2+u*h
        cx, cz = math.cos(a)*R, math.sin(a)*R; rx, rz = math.cos(a), math.sin(a)
        for j in range(sv):
            b = j/sv*TAU; cb, sb = math.cos(b), math.sin(b)
            V.append([cx+cb*rw*rx, y+sb*rw, cz+cb*rw*rz])
    for i in range(su):
        for j in range(sv):
            nj = (j+1) % sv
            F.append([i*sv+j, (i+1)*sv+j, (i+1)*sv+nj, i*sv+nj])
    return V, F

def _gear(R, td, n, h, bore, seg=0):
    n = max(6, min(40, int(n or 14))); V, F = [], []; y0, y1 = -h/2, h/2
    for i in range(n):
        a0 = i/n*TAU; a1 = (i+0.5)/n*TAU; rr = R-td; ro = R
        pts = [(a0, rr), (a0+0.12/n*TAU, ro), (a1-0.12/n*TAU, ro), (a1, rr)]
        for a, r in pts:
            c, s = math.cos(a), math.sin(a); V += [[c*r, y0, s*r], [c*r, y1, s*r]]
    ppt = n*4
    for i in range(ppt):
        j = (i+1) % ppt; b, m = i*2, j*2; F.append([b, m, m+1, b+1])
    if bore > 1e-4:
        bi = len(V)
        for i in range(ppt):
            a = i/ppt*TAU; c, s = math.cos(a), math.sin(a); V += [[c*bore, y0, s*bore], [c*bore, y1, s*bore]]
        for i in range(ppt):
            j = (i+1) % ppt; o0, o1, i0, i1 = i*2, j*2, bi+i*2, bi+j*2
            F += [[o0+1, o1+1, i1+1, i0+1], [o0, i0, i1, o1], [i0, i0+1, i1+1, i1]]
    else:
        tc = len(V); V.append([0, y1, 0])
        for i in range(ppt): j = (i+1) % ppt; F.append([tc, i*2+1, j*2+1])
        bc = len(V); V.append([0, y0, 0])
        for i in range(ppt): j = (i+1) % ppt; F.append([bc, j*2, i*2])
    return V, F

def _box(w, h, d):
    return cad_mesh.box_mesh(w, h, d, origin="center")

class _Mesh:
    def __init__(self): self.V = []; self.F = []
    def add(self, g, ox=0, oy=0, oz=0):
        o = len(self.V); Vg, Fg = g
        for v in Vg: self.V.append([v[0]+ox, v[1]+oy, v[2]+oz])
        for f in Fg: self.F.append([k+o for k in f])
        return self
    def out(self): return self.V, self.F

# ---------------- family builders (mirror partgeo.js) ----------------
def f_bolt(p):
    m=_Mesh(); dia=p.get('dia') or p.get('W') or 0.4; L=p.get('L') or 1.4; headD=dia*1.7; headH=dia*0.7
    m.add(_cyl(dia*0.5,dia*0.5,L,24,True,False),0,-headH*0.5,0)
    rings=max(5,round(L/(dia*0.32)))
    for i in range(rings): m.add(_cyl(dia*0.5,dia*0.42,dia*0.18,18,False,False),0,-L*0.5-headH*0.5+dia*0.10+i*(L/rings),0)
    m.add(_prism(headD*0.5,headH,6,headH*0.22),0,L*0.5-headH*0.5,0); return m.out()
def f_nut(p):
    m=_Mesh(); af=p.get('dia') or p.get('W') or 0.5; h=af*0.8; bore=af*0.32
    m.add(_prism(af*0.62,h,6,h*0.22)); m.add(_tube(af*0.62,bore,h*1.001,30)); return m.out()
def f_washer(p):
    R=(p.get('dia') or p.get('W') or 0.6)*0.5; r=R*0.5; h=max(p.get('H') or 0.06, R*0.10); return _tube(R,r,h,36)
def f_gasket(p):
    R=(p.get('dia') or p.get('W') or 1.2)*0.5; r=R*0.62; h=max(p.get('H') or 0.05,R*0.05); m=_Mesh(); m.add(_tube(R,r,h,40))
    holes=max(4,min(12,round(R*8))); hr=R*0.10; ringR=(R+r)/2
    for i in range(holes): a=i/holes*TAU; m.add(_tube(hr,hr*0.55,h*1.02,12),math.cos(a)*ringR,0,math.sin(a)*ringR)
    return m.out()
def f_bearing(p):
    R=(p.get('dia') or p.get('W') or 1.0)*0.5; h=p.get('H') or R*0.5; bore=R*0.5; m=_Mesh()
    m.add(_tube(R,R*0.78,h,36)); m.add(_tube(bore*1.18,bore,h,30))
    balls=max(7,round(R*12)); br=(R*0.78-bore*1.18)*0.5*0.92; ringR=(R*0.78+bore*1.18)/2
    for i in range(balls): a=i/balls*TAU; m.add(_sphere(br,14,10),math.cos(a)*ringR,0,math.sin(a)*ringR)
    return m.out()
def f_gear(p):
    R=(p.get('dia') or p.get('W') or 1.0)*0.5; h=p.get('H') or R*0.4; bore=(p.get('bore')*0.5 if p.get('bore') else R*0.28)
    n=p.get('teeth') or round(R*16); return _gear(R,R*0.16,max(6,min(80,n)),h,bore,0)
def f_spring(p):
    R=(p.get('dia') or p.get('W') or 0.5)*0.5; h=p.get('L') or p.get('H') or 1.6; wire=R*0.20
    turns=p.get('turns') or max(4,round(h/(wire*2.6))); return _helix(R,wire,max(2,min(40,turns)),h,None,8)
def f_tube(p):
    R=(p.get('dia') or p.get('W') or 0.5)*0.5; h=p.get('L') or 1.4; return _tube(R,R*0.72,h,32)
def f_oring(p):
    R=(p.get('dia') or p.get('W') or 0.6)*0.5; rt=R*0.22; return _torus(R-rt,rt,36,18)
def f_shaft(p):
    R=(p.get('dia') or p.get('W') or 0.3)*0.5; h=p.get('L') or 1.6; m=_Mesh()
    m.add(_cyl(R*0.82,R,h*0.06,24,False,True),0,h*0.5-h*0.03,0); m.add(_cyl(R,R,h*0.9,24,False,False),0,0,0)
    m.add(_cyl(R,R*0.82,h*0.06,24,True,False),0,-h*0.5+h*0.03,0); return m.out()
def f_bracket(p):
    w=p.get('W') or 1.0; h=p.get('H') or 1.0; t=max(p.get('L') or 0.12,w*0.10); m=_Mesh()
    m.add(_box(w,t,w*0.7),0,-h*0.5+t*0.5,0); m.add(_box(t,h,w*0.7),-w*0.5+t*0.5,0,0)
    m.add(_tube(w*0.12,w*0.06,t*1.3,14),w*0.22,-h*0.5+t*0.5,w*0.18); m.add(_tube(w*0.12,w*0.06,t*1.3,14),w*0.22,-h*0.5+t*0.5,-w*0.18)
    return m.out()
def f_battery(p):
    w=p.get('W') or 1.0; h=p.get('H') or 0.9; d=p.get('L') or 0.7; m=_Mesh(); m.add(_box(w,h,d))
    m.add(_cyl(w*0.09,w*0.09,h*0.18,16,True,True),-w*0.22,h*0.5+h*0.09,d*0.16); m.add(_cyl(w*0.09,w*0.09,h*0.18,16,True,True),w*0.22,h*0.5+h*0.09,d*0.16)
    return m.out()
def f_box(p): return _box(p.get('W') or 1, p.get('H') or 1, p.get('L') or 1)
def f_plate(p):
    w=p.get('W') or p.get('dia') or 1.2; d=p.get('L') or w*0.7; t=max(p.get('H') or 0.08,w*0.04); m=_Mesh(); m.add(_box(w,t,d))
    hr=min(w,d)*0.08; ox=w*0.5-hr*1.9; oz=d*0.5-hr*1.9
    for sx,sz in [(ox,oz),(-ox,oz),(ox,-oz),(-ox,-oz)]: m.add(_tube(hr,hr*0.5,t*1.3,12),sx,0,sz)
    return m.out()
def f_cover(p):
    w=p.get('W') or p.get('dia') or 1.4; d=p.get('L') or w*0.8; h=max(p.get('H') or w*0.22,w*0.10); t=max(w*0.05,0.04); m=_Mesh()
    m.add(_box(w,t,d),0,h*0.5-t*0.5,0); m.add(_box(t,h,d),-w*0.5+t*0.5,0,0); m.add(_box(t,h,d),w*0.5-t*0.5,0,0)
    m.add(_box(w,h,t),0,0,-d*0.5+t*0.5); m.add(_box(w,h,t),0,0,d*0.5-t*0.5); return m.out()
def f_pad(p):
    w=p.get('W') or p.get('dia') or 1.0; d=p.get('L') or w*0.7; h=max(p.get('H') or 0.25,w*0.12); m=_Mesh()
    m.add(_box(w,h*0.7,d),0,-h*0.15,0); m.add(_box(w*0.86,h*0.5,d*0.86),0,h*0.30,0); return m.out()
def f_link(p):
    L=p.get('L') or 1.6; w=p.get('W') or L*0.30; t=max(p.get('H') or w*0.5,0.06); m=_Mesh(); m.add(_box(L*0.66,t,w*0.6))
    er=w*0.5; m.add(_tube(er,er*0.45,t,18),L*0.5-er,0,0); m.add(_tube(er,er*0.45,t,18),-L*0.5+er,0,0); return m.out()
def f_lever(p):
    L=p.get('L') or 1.8; w=p.get('W') or L*0.18; t=max(w*0.5,0.06); m=_Mesh(); m.add(_box(L*0.86,t,w))
    er=w*0.7; m.add(_tube(er,er*0.4,t*1.2,18),-L*0.5+er,0,0); m.add(_sphere(w*0.6,14,10),L*0.5,0,0); return m.out()
def f_rivet(p):
    dia=p.get('dia') or p.get('W') or 0.25; L=p.get('L') or 0.7; m=_Mesh()
    m.add(_cyl(dia*0.5,dia*0.5,L,20,True,False),0,-L*0.5,0); m.add(_cyl(dia*0.95,dia*0.55,dia*0.5,20,True,True),0,dia*0.18,0); return m.out()
def f_switch(p):
    w=p.get('W') or 0.7; h=p.get('H') or 0.6; d=p.get('L') or 0.6; m=_Mesh(); m.add(_box(w,h,d))
    m.add(_cyl(w*0.10,w*0.07,h*0.5,12,True,True),0,h*0.5+h*0.22,0); m.add(_sphere(w*0.12,12,8),0,h*0.5+h*0.5,0)
    m.add(_box(w*0.10,h*0.3,w*0.06),-w*0.25,-h*0.5-h*0.12,0); m.add(_box(w*0.10,h*0.3,w*0.06),w*0.25,-h*0.5-h*0.12,0); return m.out()
def f_cylinder(p):
    R=(p.get('dia') or p.get('W') or 0.8)*0.5; h=p.get('L') or p.get('H') or 1.6; m=_Mesh(); m.add(_cyl(R,R,h,28,True,True))
    m.add(_cyl(R*1.12,R*1.12,h*0.08,28,True,True),0,h*0.5-h*0.04,0); m.add(_cyl(R*1.12,R*1.12,h*0.08,28,True,True),0,-h*0.5+h*0.04,0)
    m.add(_cyl(R*0.18,R*0.18,R*0.7,14,True,True),R*0.9,h*0.18,0); return m.out()
def f_canister(p):
    R=(p.get('dia') or p.get('W') or 1.0)*0.5; h=p.get('L') or p.get('H') or 1.6; m=_Mesh(); m.add(_cyl(R,R,h*0.8,28,True,False),0,-h*0.1,0)
    dome=_sphere(R,20,10); Vd=[[v[0],max(0,v[1])*0.6+h*0.30,v[2]] for v in dome[0]]; m.add((Vd,dome[1]),0,0,0)
    m.add(_cyl(R*1.08,R*1.08,h*0.07,28,True,True),0,-h*0.5+h*0.035,0); m.add(_cyl(R*0.16,R*0.16,h*0.2,12,True,True),0,h*0.45,0); return m.out()

BUILDERS = {'bolt':f_bolt,'nut':f_nut,'washer':f_washer,'gasket':f_gasket,'oring':f_oring,'bearing':f_bearing,
    'gear':f_gear,'spring':f_spring,'tube':f_tube,'shaft':f_shaft,'bracket':f_bracket,'battery':f_battery,'box':f_box,
    'plate':f_plate,'cover':f_cover,'pad':f_pad,'link':f_link,'lever':f_lever,'rivet':f_rivet,'switch':f_switch,
    'cylinder':f_cylinder,'canister':f_canister}

# ---------------- classify (name -> family, NSN FSC fallback) ----------------
FSC_MAP = {'5305':'bolt','5306':'bolt','5307':'bolt','5315':'shaft','5320':'rivet','5310':'nut','5311':'nut','5325':'bracket',
 '5330':'gasket','5331':'oring','5340':'bracket','5342':'bracket','5345':'washer','5355':'shaft','5360':'spring','5365':'shaft',
 '5970':'pad','5975':'box','5999':'plate','3110':'bearing','3120':'bearing','3130':'bearing','3020':'gear','3010':'cylinder',
 '3040':'lever','4710':'tube','4720':'tube','4730':'tube','4820':'cylinder','2910':'cylinder','2915':'cylinder','2920':'cylinder',
 '2930':'canister','2940':'canister','2990':'cover','2510':'cover','2520':'cylinder','2530':'cylinder','2540':'bracket',
 '2541':'bracket','2590':'box','2805':'cylinder','5905':'shaft','5910':'shaft','5915':'shaft','5920':'shaft','5925':'switch',
 '5930':'switch','5935':'tube','5940':'bracket','5945':'switch','5950':'cylinder','5955':'shaft','5960':'shaft','5961':'shaft',
 '5962':'plate','5963':'plate','5985':'cylinder','5995':'tube','6150':'tube','6210':'cover','6220':'cover','6240':'shaft',
 '6250':'shaft','6260':'shaft','4010':'tube','4030':'bracket','9905':'plate','7690':'plate','9390':'pad','2610':'oring',
 '2620':'oring','2640':'oring','4130':'canister','4140':'cylinder','4320':'cylinder','4330':'canister','5120':'shaft',
 '5130':'cylinder','5133':'shaft','5136':'shaft','5210':'shaft','1005':'tube','1010':'tube'}
FSG_MAP = {'53':'bracket','31':'bearing','30':'gear','47':'tube','48':'cylinder','29':'cylinder','26':'oring','25':'box','28':'box','61':'tube','59':'tube'}

def family(name, chars=""):
    t = ((name or "")+" "+(chars or "")).upper(); R = lambda p: re.search(p, t)
    if R(r"\bNUT\b"): return "nut"
    if R(r"\bRIVET\b"): return "rivet"
    if R(r"BOLT|SCREW|CAPSCREW|\bSTUD\b|\bSCRW\b"): return "bolt"
    if R(r"WASHER\b"): return "washer"
    if R(r"GASKET|\bSHIM\b"): return "gasket"
    if R(r"O-?RING|\bSEAL\b|PACKING|QUAD RING"): return "oring"
    if R(r"BEARING"): return "bearing"
    if R(r"GEAR|SPROCKET|PINION"): return "gear"
    if R(r"SPRING|\bCOIL\b"): return "spring"
    if R(r"\bLINK\b"): return "link"
    if R(r"\bLEVER\b|\bHANDLE\b|\bCRANK\b|\bPEDAL\b|CONTROL ARM|\bARM\b"): return "lever"
    if R(r"SWITCH|\bRELAY\b"): return "switch"
    if R(r"CIRCUIT CARD|\bCCA\b|PRINTED.*BOARD|\bBOARD\b"): return "plate"
    if R(r"AIR CLEANER|\bFILTER\b|\bCARTRIDGE\b|\bELEMENT\b|CANISTER|RESERVOIR|\bTANK\b|ACCUMULATOR|DRIER"): return "canister"
    if R(r"CYLINDER|ACTUATOR|\bMOTOR\b|\bPUMP\b|SOLENOID|COMPRESSOR|\bVALVE\b"): return "cylinder"
    if R(r"COVER|\bDOOR\b|\bPANEL\b|HATCH|\bLID\b|\bGUARD\b|SHIELD|DEFLECTOR|BEZEL"): return "cover"
    if R(r"INSULAT|\bPAD\b|CUSHION|\bMAT\b|\bSTRAP\b|WEBBING"): return "pad"
    if R(r"PIPE|TUBE|TUBING|HOSE|CONDUIT|NIPPLE|COUPLING|ADAPTER|UNION|ELBOW|FITTING|CONNECTOR|CABLE|\bWIRE\b|WIRING|HARNESS|CORD|\bLEAD\b"): return "tube"
    if R(r"GROMMET|\bBAND\b|\bBELT\b|\bRING\b"): return "oring"
    if R(r"\bPIN\b|DOWEL|\bSHAFT\b|\bROD\b|SPACER|SLEEVE|BUSHING|ROLLER|\bKEY\b|WEDGE|COTTER|\bPLUG\b|\bCAP\b|\bCOCK\b|\bLAMP\b|\bBULB\b|\bFUSE\b|STANDOFF"): return "shaft"
    if R(r"BRACKET|MOUNT|\bCLAMP\b|SUPPORT|\bANGLE\b|TERMINAL|\bLUG\b|CONTACT|RETAINER|\bCLIP\b|HINGE|LATCH|STRIKE|\bCATCH\b|\bHASP\b|\bHOOK\b"): return "bracket"
    if R(r"PLATE|MARKER|DECAL|LABEL|PLACARD|NAMEPLATE|\bTAG\b|IDENTIFICATION|ARMOR|ARMOUR|\bBUS\b|\bBAR\b"): return "plate"
    if R(r"BATTERY"): return "battery"
    return "box"

def classify(name, chars, nsn):
    f = family(name, chars)
    if f == "box" and nsn:
        m = re.match(r"\s*(\d{4})", nsn)
        if m:
            fsc = m.group(1)
            return FSC_MAP.get(fsc) or FSG_MAP.get(fsc[:2]) or "box"
    return f

# ---------------- dims + material from FLIS characteristics ----------------
def _num(ch, labels):
    ch = (ch or "").upper()
    for lab in labels:
        i = ch.find(lab)
        if i >= 0:
            m = re.search(r"[-+]?\d*\.?\d+", ch[i+len(lab):])
            if m:
                v = float(m.group(0))
                if v > 0: return v
    return 0

def dims(ch):
    dia = _num(ch, ['OVERALL DIAMETER:','BODY DIAMETER:','OUTSIDE DIAMETER:','HEAD DIAMETER:','BASE DIAMETER:','THREAD DIAMETER:','DIAMETER:'])
    bore = _num(ch, ['HOLE DIAMETER:','INSIDE DIAMETER:','BORE DIAMETER:'])
    L = _num(ch, ['OVERALL LENGTH:','BODY LENGTH:','FASTENER LENGTH:','LENGTH:'])
    W = _num(ch, ['OVERALL WIDTH:','BODY WIDTH:','WIDTH:']) or dia
    H = _num(ch, ['OVERALL HEIGHT:','BODY HEIGHT:','HEAD HEIGHT:','HEIGHT:','THICKNESS:']) or dia
    if dia: W = dia; H = dia; L = L or dia
    return {'L': L or 1, 'W': W or 1, 'H': H or 1, 'dia': dia, 'bore': bore}

#   (pattern, base-rgb, metalness, texture-class)
_MATS = [(r"STAINLESS|\bCRES\b",(182,186,191),0.85,"metal"), (r"CAST IRON",(120,122,126),0.45,"cast"),
         (r"STEEL|\bIRON\b|ALLOY STEEL|\bCRS\b|\bCS\b",(150,157,166),0.7,"metal"), (r"ALUMIN",(186,190,196),0.6,"metal"),
         (r"TITAN",(158,162,167),0.6,"metal"), (r"BRASS",(183,149,64),0.72,"brass"), (r"BRONZE|COPPER",(178,114,64),0.66,"brass"),
         (r"RUBBER|ELASTOMER|NEOPRENE|SILICONE|\bSBR\b|VITON",(58,58,62),0.05,"rubber"),
         (r"NYLON|PLASTIC|POLY|\bPVC\b|PHENOLIC|ACETAL|DELRIN|\bABS\b",(72,76,84),0.1,"plastic"),
         (r"\bWOOD|PLYWOOD|\bOAK\b|BIRCH|MAPLE",(150,116,74),0.05,"wood"),
         (r"GLASS|ACRYLIC|LEXAN|POLYCARB",(150,170,180),0.25,"plastic")]
_COLORS = {"BLACK":(42,42,46),"GRAY":(135,140,148),"GREY":(135,140,148),"WHITE":(220,222,226),"SILVER":(190,194,198),
  "RED":(150,52,52),"BLUE":(56,86,120),"GREEN":(64,96,64),"YELLOW":(200,176,70),"ORANGE":(200,116,46),
  "BROWN":(96,74,52),"TAN":(186,160,112),"SAND":(196,178,128),"GOLD":(196,162,74),"OLIVE":(96,96,52)}
_MULTI = [("OLIVE DRAB",(70,72,44)),("FOREST GREEN",(48,76,48)),("CARC GREEN",(86,96,52)),("GLOSS BLACK",(34,34,36)),
  ("FLAT BLACK",(40,40,42)),("DESERT SAND",(200,182,142)),("DESERT TAN",(196,170,122)),("FIELD DRAB",(110,96,66)),
  ("OD GREEN",(70,72,44)),("CARC TAN",(196,170,122))]
def material_props(ch, nm, use_color=True):
    """Return (base_rgb, metalness, texture_class). When use_color, a FLIS-stated colour overrides the base tint
    (keeping metalness + texture) — an OLIVE DRAB steel bracket is green AND painted-textured."""
    blob = ((ch or "")+" "+(nm or "")).upper()
    rgb, metal, klass = (150, 157, 166), 0.55, "metal"
    for pat, r, me, k in _MATS:
        if re.search(pat, blob): rgb, metal, klass = r, me, k; break
    if use_color:
        col = None
        for name, c in _MULTI:
            if name in blob: col = c; break
        if col is None:
            mm = re.search(r"COLOR[^:]*:\s*([A-Z][A-Z ]{2,})", blob)
            cw = mm.group(1).strip().split(" ")[0] if mm else ""
            if cw in _COLORS: col = _COLORS[cw]
            else:
                for name in ("BLACK","OLIVE","GREEN","RED","GRAY","GREY","TAN","SAND","BROWN","WHITE","YELLOW","BLUE"):
                    if re.search(r"\b"+name+r"\b", blob): col = _COLORS[name]; break
        if col:
            rgb = col
            if klass == "metal" and (col[0]+col[1]+col[2]) < 360: klass = "painted"
    return rgb, metal, klass

# ---- procedural surface texture (screen-space, masked to the part) ----
try:
    import numpy as _np
except Exception:
    _np = None
def _smooth1d(a, r):
    k = 2*r+1; ker = _np.ones(k, _np.float32)/k
    return _np.convolve(a, ker, mode="same")
def _lowfreq(rng, H, W, k):
    small = rng.standard_normal((max(2, k), max(2, k))).astype(_np.float32)
    rng01 = (small - small.min())/((small.max()-small.min()) or 1)
    im = Image.fromarray((rng01*255).astype("uint8")).resize((W, H), Image.BILINEAR)
    a = _np.asarray(im).astype(_np.float32)/255.0
    return a - a.mean()
def _surface_texture(W, H, klass, seed=1):
    """A multiplicative detail map (~0.8..1.2) for the material's surface look. None if numpy is absent."""
    if _np is None: return None
    rng = _np.random.default_rng((seed or 1) & 0x7fffffff)
    yy, xx = _np.mgrid[0:H, 0:W].astype(_np.float32)
    t = _np.ones((H, W), _np.float32)
    if klass in ("metal", "brass"):
        col = _smooth1d(rng.standard_normal(W).astype(_np.float32), 2)
        t += 0.05*col[None, :] + 0.028*_np.sin(xx*0.9 + 3.0*col[None, :]) + 0.02*_lowfreq(rng, H, W, 8)
    elif klass == "cast":
        t += 0.10*_lowfreq(rng, H, W, 3) + 0.05*rng.standard_normal((H, W)).astype(_np.float32)
    elif klass == "rubber":
        t += 0.05*rng.standard_normal((H, W)).astype(_np.float32); t *= 0.985
    elif klass == "plastic":
        t += 0.05*_lowfreq(rng, H, W, 5)
    elif klass == "wood":
        g = _smooth1d(rng.standard_normal(H).astype(_np.float32), 3)
        t += 0.11*_np.sin(yy*0.22 + 4.0*g[:, None]) + 0.04*g[:, None]
    else:  # painted / CARC: subtle orange-peel
        t += 0.05*_lowfreq(rng, H, W, 6) + 0.015*rng.standard_normal((H, W)).astype(_np.float32)
    return _np.clip(t, 0.78, 1.22)

# ---------------- render ----------------
def _font(sz):
    try:
        for f in ("DejaVuSans.ttf", "arial.ttf", "Arial.ttf"):
            try: return ImageFont.truetype(f, sz)
            except Exception: continue
    except Exception: pass
    return ImageFont.load_default()

def render(name, chars, nsn, w=620, h=480, style="v3", yaw=0.0, pitch=None, title=True, colorize=None, texturize=None):
    """Return a PIL.Image: shaded isometric CAD view + dimension callouts + title block.
    style: 'v1' = original (head-down, flat diffuse, no colour/texture); 'v2' = + right-side-up + specular/metallic;
    'v3' = + FLIS colour + material surface texture (current).
    yaw   = extra rotation about the vertical axis (radians) — for turntable frames (default 0 = the canonical view).
    pitch = override the camera tilt (radians); None keeps the canonical three-quarter tilt."""
    if Image is None: raise RuntimeError("Pillow not available")
    fam = classify(name or "", chars or "", nsn or "")
    d = dims(chars or "")
    try: V, F = (BUILDERS.get(fam) or f_box)(d)
    except Exception: V, F = f_box(d)
    if not V: V, F = f_box(d)
    SS = 4  # supersample (max-quality: 4× — render large, downsample with LANCZOS for crisp anti-aliasing)
    W, H = w*SS, h*SS
    img = Image.new("RGB", (W, H), (244, 246, 248))
    dr = ImageDraw.Draw(img, "RGBA")
    # faint CAD grid
    for gx in range(0, W, 28*SS): dr.line([(gx,0),(gx,H)], fill=(228,232,236), width=1)
    for gy in range(0, H, 28*SS): dr.line([(0,gy),(W,gy)], fill=(228,232,236), width=1)
    # rotate (three-quarter iso) + orthographic project; yaw spins about the vertical axis (turntable)
    rx, ry = (-0.62 if pitch is None else pitch), 0.72 + (yaw or 0.0)
    cy, sy, cx, sx = math.cos(ry), math.sin(ry), math.cos(rx), math.sin(rx)
    P = []
    for v in V:
        x, y, z = v[0], (-v[1] if style != "v1" else v[1]), v[2]   # v1=original head-down; v2/v3=right-side-up
        x1 = x*cy + z*sy; z1 = -x*sy + z*cy; y1 = y*cx - z1*sx; z2 = y*sx + z1*cx
        P.append((x1, y1, z2))
    xs = [p[0] for p in P]; ys = [p[1] for p in P]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    span = max(maxx-minx, maxy-miny, 1e-3)
    draw_h = H*0.66
    sc = min(W*0.62, draw_h)/span
    cX, cY = W/2, H*0.46
    mx, my = (minx+maxx)/2, (miny+maxy)/2
    def sp(p): return (cX+(p[0]-mx)*sc, cY+(p[1]-my)*sc)
    # soft contact shadow under the part (depth cue) — nested translucent ellipses (cheap fake blur), all tiers
    try:
        sh_y = cY + (maxy-my)*sc + 10*SS
        sh_w = (maxx-minx)*sc*0.62; sh_h = max(6*SS, sh_w*0.16)
        for k in range(5, 0, -1):
            ew = sh_w*(0.62 + 0.10*k); eh = sh_h*(0.55 + 0.12*k); al = int(16 - k*2)
            dr.ellipse([cX-ew, sh_y-eh/2, cX+ew, sh_y+eh/2], fill=(20, 26, 33, max(3, al)))
    except Exception:
        pass
    # FLIS colour on EVERY tier now (v6). colorize=None -> coloured; pass False to reproduce the old grey v1/v2.
    use_color = True if colorize is None else bool(colorize)
    base, metal, klass = material_props(chars, name, use_color=use_color)
    def _norm(v): n = math.sqrt(sum(c*c for c in v)) or 1; return [c/n for c in v]
    light = _norm((0.4, 0.82, 0.42))                                       # key light
    fill  = _norm((-0.55, 0.18, 0.62))                                     # soft fill from the other side (lifts shadows)
    hx, hy, hz = light[0], light[1], light[2]+1.0; hl = math.sqrt(hx*hx+hy*hy+hz*hz) or 1   # half-vector (view=+Z)
    white = (236, 239, 243)
    sr = white[0]*(1-metal)+base[0]*metal; sg = white[1]*(1-metal)+base[1]*metal; sb = white[2]*(1-metal)+base[2]*metal
    faces = []
    for f in F:
        zc = sum(P[i][2] for i in f)/len(f)
        a, b, c = P[f[0]], P[f[1]], P[f[2]]
        ux, uy, uz = b[0]-a[0], b[1]-a[1], b[2]-a[2]
        vx, vy, vz = c[0]-a[0], c[1]-a[1], c[2]-a[2]
        nx, ny, nz = uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx
        nl = math.sqrt(nx*nx+ny*ny+nz*nz) or 1; nnx, nny, nnz = nx/nl, ny/nl, nz/nl
        ndl = max(0.0, nnx*light[0]+nny*light[1]+nnz*light[2])              # key diffuse
        ndf = max(0.0, nnx*fill[0]+nny*fill[1]+nnz*fill[2])                 # fill diffuse (softens the dark side)
        ndh = max(0.0, (nnx*hx+nny*hy+nnz*hz)/hl)                           # specular (Blinn-Phong)
        spec = ((ndh ** 16) * (0.30 + 0.55*metal)) if style != "v1" else 0.0
        faces.append((zc, f, 0.30 + 0.55*ndl + 0.16*ndf, spec))            # ambient + key + fill
    faces.sort(key=lambda t: t[0])
    mask = Image.new("L", (W, H), 0); mdr = ImageDraw.Draw(mask)
    for zc, f, br, spec in faces:
        pts = [sp(P[i]) for i in f]
        r = min(255, int(base[0]*br + spec*sr)); g = min(255, int(base[1]*br + spec*sg)); bl = min(255, int(base[2]*br + spec*sb))
        # q-pass: facet edge = a subtle darkened tint of the face fill (not a hard black wire) -> clean on fine meshes
        oc = (int(r*0.72), int(g*0.72), int(bl*0.72))
        dr.polygon(pts, fill=(r, g, bl), outline=oc); mdr.polygon(pts, fill=255)
    # wrap the part in its material's surface texture (screen-space, masked to the silhouette)
    try:
        use_tex = True if texturize is None else bool(texturize)   # v7: material texture on EVERY tier (was v3-only)
        tex = _surface_texture(W, H, klass, seed=(abs(hash(nsn or name or klass)) % 100000) or 1) if use_tex else None
        if tex is not None:
            arr = _np.asarray(img).astype(_np.float32); mm = _np.asarray(mask) > 0
            for c in range(3):
                cc = arr[:, :, c]; cc[mm] = _np.clip(cc[mm]*tex[mm], 0, 255)
            img = Image.fromarray(arr.astype("uint8"), "RGB"); dr = ImageDraw.Draw(img, "RGBA")
    except Exception:
        pass   # texture is cosmetic — never let it fail the render
    # q-pass: crisp silhouette + hole outlines from the part mask (the CAD "ink" line), all tiers
    try:
        sil = mask.filter(ImageFilter.FIND_EDGES)
        if SS >= 3: sil = sil.filter(ImageFilter.MaxFilter(3))
        img.paste((24, 30, 38), (0, 0), sil); dr = ImageDraw.Draw(img, "RGBA")
    except Exception:
        pass
    # ---- overall-dimension callouts (the bounding box in inches) ----
    blue = (40, 100, 170)
    fnt = _font(15*SS); fsm = _font(12*SS)
    def dim_label(txt):
        return txt
    pad = 16*SS
    # vertical extent (H) on the right
    x_r = cX + (maxx-mx)*sc + 26*SS
    y_top, y_bot = cY+(miny-my)*sc, cY+(maxy-my)*sc
    dr.line([(x_r, y_top),(x_r, y_bot)], fill=blue, width=2)
    for yy in (y_top, y_bot): dr.line([(x_r-6*SS, yy),(x_r+6*SS, yy)], fill=blue, width=2)
    hv = d['dia'] or d['H']
    dr.text((x_r+10*SS, (y_top+y_bot)/2-9*SS), ("H %.2f\"" % d['H']) if not d['dia'] else ("⌀ %.2f\"" % d['dia']), fill=blue, font=fsm)
    # horizontal extent (L/W) along the bottom
    x_l, x_rr = cX+(minx-mx)*sc, cX+(maxx-mx)*sc
    y_b = cY+(maxy-my)*sc + 22*SS
    dr.line([(x_l, y_b),(x_rr, y_b)], fill=blue, width=2)
    for xx in (x_l, x_rr): dr.line([(xx, y_b-6*SS),(xx, y_b+6*SS)], fill=blue, width=2)
    dr.text(((x_l+x_rr)/2-20*SS, y_b+6*SS), "L %.2f\"" % (d['L'] or d['W']), fill=blue, font=fsm)
    # ---- title block (suppressed for turntable frames; the viewer shows the info as chrome) ----
    if title:
        tb_h = 72*SS
        dr.rectangle([(0, H-tb_h),(W, H)], fill=(28, 36, 46))
        dr.line([(0, H-tb_h),(W, H-tb_h)], fill=blue, width=2*SS)
        nm = (name or "").strip() or "(unnamed part)"
        dr.text((pad, H-tb_h+9*SS), nm[:46], fill=(235, 238, 242), font=fnt)
        sub = "NSN %s   ·   shape: %s   ·   %s" % (nsn or "—", fam, "scaled to FLIS dims")
        dr.text((pad, H-tb_h+33*SS), sub, fill=(150, 165, 180), font=fsm)
        dr.text((pad, H-tb_h+51*SS), "REPRESENTATIVE CAD APPROXIMATION — not a manufacturing drawing", fill=(110, 125, 140), font=fsm)
        # corner mark
        dr.text((W-150*SS, H-tb_h+9*SS), "THE VIEWER", fill=(79, 157, 255), font=fsm)
        dr.text((W-150*SS, H-tb_h+27*SS), "auto-CAD v"+CAD_VERSION, fill=(110, 125, 140), font=fsm)
    return img.resize((w, h), Image.LANCZOS)

# ---------------- real CAD mesh export (STL / OBJ) ----------------
def mesh_for(name, chars, nsn):
    """The raw parametric mesh (V, F) + family, scaled to FLIS dims — for STL/OBJ export."""
    fam = classify(name or "", chars or "", nsn or "")
    d = dims(chars or "")
    try: V, F = (BUILDERS.get(fam) or f_box)(d)
    except Exception: V, F = f_box(d)
    if not V: V, F = f_box(d)
    return V, F, fam

_KLASS_ID = {"steel":1,"metal":1,"alum":1,"iron":1,"chrome":1,"zinc":1,"nickel":1,"cast":1,
             "brass":6,"bronze":6,"copper":6,
             "rubber":2,"neoprene":2,"elasto":2,"synthetic rubber":2,
             "wood":3,
             "plastic":4,"nylon":4,"poly":4,"pvc":4,"acetal":4,
             "paint":5,"carc":5,"coat":5,"enamel":5,"painted":5}

def material_for(name, chars, nsn):
    """The CAD material for a part -> {color hex, metal, klass, klass_id, gl:[spec,shininess,metallic]} so the
    WebGL 3-D model can be grafted with the CAD image's colour + surface-texture class."""
    rgb, metal, klass = material_props(chars or "", name or "", use_color=True)
    kl = (klass or "").lower(); kid = 0
    for key, v in _KLASS_ID.items():
        if key in kl: kid = v; break
    if kid == 0 and (metal or 0) > 0.4: kid = 1
    if kid in (1, 6): gl = [0.62, 60.0, (1.0 if kid == 1 else 0.85)]
    elif kid == 2: gl = [0.14, 8.0, 0.0]
    elif kid == 3: gl = [0.22, 16.0, 0.0]
    elif kid == 4: gl = [0.50, 40.0, 0.0]
    elif kid == 5: gl = [0.30, 22.0, 0.0]
    else: gl = [0.50, 40.0, 0.0]
    try: hexc = "#%02x%02x%02x" % (int(rgb[0]), int(rgb[1]), int(rgb[2]))
    except Exception: hexc = "#8a9099"
    return {"color": hexc, "metal": round(float(metal or 0), 3), "klass": klass, "klass_id": kid, "gl": gl}

def _tris(F):
    for f in F:
        for k in range(1, len(f)-1):
            yield (f[0], f[k], f[k+1])

def to_stl(V, F, name="part"):
    """ASCII STL (triangulated) — openable in any CAD / 3-D-print slicer."""
    nm = re.sub(r"[^A-Za-z0-9_]", "_", (name or "part"))[:60] or "part"
    out = ["solid %s" % nm]
    for i, j, k in _tris(F):
        a, b, c = V[i], V[j], V[k]
        ux, uy, uz = b[0]-a[0], b[1]-a[1], b[2]-a[2]
        vx, vy, vz = c[0]-a[0], c[1]-a[1], c[2]-a[2]
        nx, ny, nz = uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx
        nl = math.sqrt(nx*nx+ny*ny+nz*nz) or 1
        out.append("facet normal %.5f %.5f %.5f" % (nx/nl, ny/nl, nz/nl))
        out.append(" outer loop")
        for p in (a, b, c): out.append("  vertex %.5f %.5f %.5f" % (p[0], p[1], p[2]))
        out.append(" endloop"); out.append("endfacet")
    out.append("endsolid %s" % nm)
    return "\n".join(out)

def to_obj(V, F):
    """Wavefront OBJ (keeps n-gon faces) — openable in any 3-D tool."""
    out = ["# THE VIEWER representative CAD approximation (scaled to FLIS dims)"]
    for v in V: out.append("v %.5f %.5f %.5f" % (v[0], v[1], v[2]))
    for f in F: out.append("f " + " ".join(str(i+1) for i in f))
    return "\n".join(out)

# CAD detail level per program build / RPS tier: heavier machines get the textured v3, legacy gets the light v1.
TIER_STYLE = {"modern": "v3", "lite": "v2", "legacy": "v1"}

def cache_path(cache_dir, nsn, style="v3"):
    safe = re.sub(r"[^0-9A-Za-z]", "", (nsn or "part"))
    st = style if style in ("v1", "v2", "v3") else "v3"
    return os.path.join(cache_dir, "%s_%s.png" % (safe or "part", st))   # <nsn>_v3.png == the modern set

def _fallback_card(name, nsn, w=620, h=480):
    """A clean placeholder for the rare part whose shape can't be modelled — so every part still gets an image."""
    img = Image.new("RGB", (w, h), (244, 246, 248)); dr = ImageDraw.Draw(img)
    L = (120, 128, 138)
    dr.rectangle([w*0.36, h*0.32, w*0.64, h*0.60], outline=L, width=3)        # front
    dr.line([(w*0.36, h*0.32), (w*0.44, h*0.24)], fill=L, width=3)
    dr.line([(w*0.64, h*0.32), (w*0.72, h*0.24)], fill=L, width=3)
    dr.line([(w*0.44, h*0.24), (w*0.72, h*0.24)], fill=L, width=3)
    dr.line([(w*0.72, h*0.24), (w*0.72, h*0.52)], fill=L, width=3)
    dr.line([(w*0.64, h*0.60), (w*0.72, h*0.52)], fill=L, width=3)
    tb = 64; dr.rectangle([(0, h-tb), (w, h)], fill=(28, 36, 46))
    dr.text((14, h-tb+9), ((name or "(unnamed part)").strip()[:46]), fill=(235, 238, 242), font=_font(15))
    dr.text((14, h-tb+31), "NSN %s   ·   representative shape unavailable" % (nsn or "—"), fill=(150, 165, 180), font=_font(12))
    dr.text((14, h-tb+47), "THE VIEWER auto-CAD — dimensional data could not be modelled", fill=(110, 125, 140), font=_font(12))
    return img

def ensure(nsn, name, chars, cache_dir, style="v3"):
    """Render + cache (idempotent) at the given detail style ('v1'|'v2'|'v3'). Always yields an image for a known
    part (falls back to a placeholder card if the shape can't be modelled). Returns the PNG path, or None."""
    if Image is None: return None
    st = style if style in ("v1", "v2", "v3") else "v3"
    try: os.makedirs(cache_dir, exist_ok=True)
    except Exception: pass
    out = cache_path(cache_dir, nsn, st)
    if os.path.exists(out) and os.path.getsize(out) > 0: return out
    im = None
    try:
        im = render(name, chars, nsn, style=st)
    except Exception:
        try: im = _fallback_card(name, nsn)
        except Exception: im = None
    if im is None: return None
    try: im.save(out, "PNG"); return out
    except Exception: return None

# ---------------- interactive turntable (rotating/scalable CAD) ----------------
SPIN_FRAMES = {"v1": 12, "v2": 16, "v3": 24}   # tier-aware default frame counts (legacy/lite/modern)

def spin_path(cache_dir, nsn, n, style="v3"):
    safe = re.sub(r"[^0-9A-Za-z]", "", (nsn or "part"))
    st = style if style in ("v1", "v2", "v3") else "v3"
    return os.path.join(cache_dir, "%s_spin%d_%s.png" % (safe or "part", int(n), st))

def render_spin(name, chars, nsn, n=24, style="v3", fw=440, fh=340):
    """A horizontal sprite sheet of N CAD frames around a full 360° turntable (no title block — clean rotation).
    Each frame is fw x fh; the sheet is (n*fw) x fh. The viewer scrubs frames on drag to spin the part."""
    if Image is None: raise RuntimeError("Pillow not available")
    n = max(4, min(48, int(n)))
    sheet = Image.new("RGB", (fw*n, fh), (244, 246, 248))
    for i in range(n):
        ya = (i / n) * (2*math.pi)
        try:
            fr = render(name, chars, nsn, w=fw, h=fh, style=style, yaw=ya, title=False)
        except Exception:
            fr = _fallback_card(name, nsn, fw, fh)
        sheet.paste(fr, (i*fw, 0))
    return sheet, n

def ensure_spin(nsn, name, chars, cache_dir, n=24, style="v3"):
    """Render + cache the turntable sprite sheet (idempotent). Returns (path, frames) or (None, 0)."""
    if Image is None: return None, 0
    st = style if style in ("v1", "v2", "v3") else "v3"
    n = max(4, min(48, int(n)))
    try: os.makedirs(cache_dir, exist_ok=True)
    except Exception: pass
    out = spin_path(cache_dir, nsn, n, st)
    if os.path.exists(out) and os.path.getsize(out) > 0: return out, n
    try:
        sheet, frames = render_spin(name, chars, nsn, n=n, style=st)
        sheet.save(out, "PNG"); return out, frames
    except Exception:
        return None, 0

def _demo():
    samples = [("BOLT,MACHINE", "OVERALL LENGTH: 2.0 IN THREAD DIAMETER: 0.375 IN", "5305-01-111-1111"),
               ("GEAR,SPUR", "OVERALL DIAMETER: 3.0 IN OVERALL HEIGHT: 0.8 IN", "3020-01-222-2222"),
               ("BEARING,BALL", "OUTSIDE DIAMETER: 2.0 IN WIDTH: 0.6 IN", "3110-01-333-3333"),
               ("AIR CLEANER ASSEMBLY", "DIAMETER: 6 IN LENGTH: 9 IN", "2940-01-444-4444"),
               ("BRACKET,MOUNTING", "WIDTH: 3 IN HEIGHT: 2.5 IN", "5340-01-555-5555"),
               ("", "", "5945-00-666-6666")]
    out = os.path.join(os.getcwd(), "cad_demo"); os.makedirs(out, exist_ok=True)
    for nm, ch, ns in samples:
        im = render(nm, ch, ns); fn = os.path.join(out, classify(nm, ch, ns)+".png"); im.save(fn, "PNG"); print("wrote", fn)

if __name__ == "__main__":
    if "--demo" in sys.argv: _demo()
    else: print("cad_render: use --demo, or import render()/ensure().")
