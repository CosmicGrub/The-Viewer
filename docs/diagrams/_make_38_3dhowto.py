#!/usr/bin/env python3
"""Markup + how-it-works for the 2D->3D representative viewer (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,900
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def arrow(x1,y1,x2,y2,col="#9aa5b1"): return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="1.7" fill="none" marker-end="url(#a)"/>'
def line(x1,y1,x2,y2,col="#6b7280"): return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="1" stroke-dasharray="3 3" fill="none"/>'
def wrap(x,y,s,width,size,fill,dy=13,wt=400):
    out=[];words=s.split();ln=0;cur=""
    for wd in words:
        if len(cur)+len(wd)+1>width: out.append(t(x,y+ln*dy,cur,size,fill,wt));cur=wd;ln+=1
        else: cur=(cur+" "+wd).strip()
    if cur: out.append(t(x,y+ln*dy,cur,size,fill,wt))
    return "".join(out),ln+1
P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
P.append('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9aa5b1"/></marker></defs>')
P.append(box(0,0,W,H,BG,BG,0))
P.append(t(40,46,"How the 2D→3D representative viewer works",22,TXT,700))
P.append(t(40,70,"It does not guess geometry. It scales a bounding solid to the dimensions FLIS states, lists the real features verbatim, and lets you rotate it.",11.5,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# LEFT: markup of the viewer
P.append(t(56,116,"THE VIEWER (marked up)",12,ACC,700))
P.append(box(40,126,520,360,PANEL,LINE,12))
# select
P.append(box(60,142,360,26,P2,LINE,6)); P.append(t(72,159,"Example part  ▾",10,TXT,400))
# stage with a small iso box
sx,sy,sw,sh=60,182,300,250
P.append(box(sx,sy,sw,sh,"#0a0e12",LINE,8))
# draw a small iso cube
import math
def iso(x,y,z): 
    rx,ry=-0.42,0.62
    cy,syy=math.cos(ry),math.sin(ry); cx,sxx=math.cos(rx),math.sin(rx)
    x1=x*cy+z*syy; z1=-x*syy+z*cy; y1=y*cx-z1*sxx
    return x1,y1
V=[(-1.4,-0.7,-0.6),(1.4,-0.7,-0.6),(1.4,0.7,-0.6),(-1.4,0.7,-0.6),(-1.4,-0.7,0.6),(1.4,-0.7,0.6),(1.4,0.7,0.6),(-1.4,0.7,0.6)]
E=[(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
PR=[iso(*v) for v in V]
xs=[p[0] for p in PR]; ys=[p[1] for p in PR]
mnx,mxx,mny,mxy=min(xs),max(xs),min(ys),max(ys)
sc=70; cX,cY=sx+sw/2,sy+sh/2; mx,my=(mnx+mxx)/2,(mny+mxy)/2
def sp(p): return (cX+(p[0]-mx)*sc, cY+(p[1]-my)*sc)
for a,b in E:
    A=sp(PR[a]); B=sp(PR[b])
    P.append(f'<line x1="{A[0]:.0f}" y1="{A[1]:.0f}" x2="{B[0]:.0f}" y2="{B[1]:.0f}" stroke="#4f9dff" stroke-width="1.6"/>')
c=sp(iso(0,0,0)); P.append(f'<ellipse cx="{c[0]:.0f}" cy="{c[1]:.0f}" rx="10" ry="16" fill="none" stroke="#caa24a" stroke-width="1.4" opacity="0.75"/>')
# controls
P.append(box(60,442,80,24,P2,LINE,6)); P.append(t(100,458,"▷ spin",9.5,SUB,400,"middle"))
P.append(box(146,442,80,24,P2,LINE,6)); P.append(t(186,458,"↻ reset",9.5,SUB,400,"middle"))
P.append(t(236,458,"zoom",9,SUB,400)); P.append(box(276,450,134,8,P2,LINE,4)); P.append(f'<circle cx="320" cy="454" r="7" fill="#4f9dff"/>')
# right info panel inside viewer
P.append(box(372,182,168,250,P2,LINE,8))
P.append(t(384,202,"Dimensions used",9,TXT,700)); P.append(t(384,216,"L · W · H · ⌀ · bore",8.5,SUB,400))
P.append(t(384,238,"FLIS characteristics",9,AMB,700))
for i,ln in enumerate(["OUTSIDE DIA: 0.865\"","HOLE DIA: 0.511\"","THICKNESS: 0.200\"","MATERIAL: STEEL","STYLE: SPLIT HELICAL"]):
    P.append(t(384,254+i*14,ln,7.6,SUB,400))
P.append(box(384,332,80,18,"#3a2f1a",LINE,5)); P.append(t(424,344,"FLIS 2016",8.5,AMB,700,"middle"))
s,_=wrap(384,366,"Representative — not a CAD model; only listed features asserted.",26,7.6,"#7c8696",10); P.append(s)
# callouts
P.append(line(360,300,600,150)); P.append(t(606,150,"① bounding solid scaled to stated L×W×H",9.5,GRN,700))
P.append(line(c[0],c[1],600,190)); P.append(t(606,190,"② amber ellipse = a stated bore (hole ⌀)",9.5,AMB,700))
P.append(line(320,454,600,230)); P.append(t(606,230,"③ drag = rotate · scroll/slider = zoom · spin",9.5,ACC,700))
P.append(line(460,238,600,270)); P.append(t(606,270,"④ the distinguishing features, verbatim & cited",9.5,GRN,700))
P.append(line(424,341,600,310)); P.append(t(606,310,"⑤ FLIS vintage tag (year the data is effective)",9.5,AMB,700))

# RIGHT: data flow
P.append(t(606,360,"HOW IT'S BUILT (per part)",12,ACC,700))
steps=[("FLIS characteristics (cited)","'OUTSIDE DIAMETER: 0.865 IN; HOLE DIAMETER: 0.511 IN; THICKNESS: 0.200 IN…'"),
       ("Parse stated dimensions","regex → L, W, H, ⌀, bore (only what FLIS actually states)"),
       ("Bounding solid + bore","8 vertices of an L×W×H box + a centered ellipse for the hole"),
       ("Rotate + orthographic project","rotation matrix (drag sets angles) → 2D points"),
       ("Draw SVG wireframe","12 edges + bore → offline, no library, no WebGL")]
y=376
for i,(h,d) in enumerate(steps):
    P.append(box(606,y,534,52,P2,LINE,8))
    P.append(t(620,y+21,str(i+1)+" · "+h,11,TXT,700))
    s,_=wrap(620,y+37,d,86,8.8,SUB,11); P.append(s)
    if i<len(steps)-1: P.append(arrow(873,y+52,873,y+60,ACC))
    y+=60
# grounding
P.append(box(40,690,1100,180,PANEL,RED,12,1))
P.append(t(58,714,"THE GROUNDING RULE (why this is honest)",12,RED,700))
gg=["Model only what the documentation specifies. The solid is scaled to the dimensions FLIS states; nothing is invented.",
    "Surfaces are schematic — a bounding solid, not exact geometry. It conveys size + the stated bore, not unstated curves/features.",
    "The distinguishing features (hole count, thread, material, style) are shown VERBATIM next to it and cited to FLIS, with the data's year.",
    "So it's trustworthy exactly where it's labeled trustworthy — and a true CAD/photogrammetry model can drop in later for parts that need exact surfaces."]
yy=736
for g in gg:
    P.append(t(58,yy,"•",10,RED,700)); s,n=wrap(72,yy,g,150,9.6,SUB,13); P.append(s); yy+=n*13+4
P.append(t(40,H-12,"The interactive version is live in the chat. Dark (R3). Matches the in-app '🧊 View representative 3D' on cart parts with FLIS dimensions.",9.4,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/38-2d3d-howitworks"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1180)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
