#!/usr/bin/env python3
"""Proposal: recommended interactive-schematic architecture + optional 3D module + roadmap (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,760
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def arrow(x1,y1,x2,y2,col="#9aa5b1"): return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="1.7" fill="none" marker-end="url(#a)"/>'
def wrap(x,y,s,width,size,fill,dy=13,wt=400):
    out=[];words=s.split();line="";ln=0
    for wd in words:
        if len(line)+len(wd)+1>width: out.append(t(x,y+ln*dy,line,size,fill,wt));line=wd;ln+=1
        else: line=(line+" "+wd).strip()
    if line: out.append(t(x,y+ln*dy,line,size,fill,wt))
    return "".join(out),ln+1
P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
P.append('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9aa5b1"/></marker></defs>')
P.append(box(0,0,W,H,BG,BG,0))
P.append(t(40,46,"Recommended path: interactive schematic viewer + an optional, BYO-3D module",21,TXT,700))
P.append(t(40,70,"Grounded foundation first (real drawing, deep zoom, callout→part). True 3D is an opt-in slot that loads REAL 3D data — CAD or photogrammetry — never a guess.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
# Tier-1 architecture (left)
P.append(box(40,104,560,300,PANEL,GRN,12))
P.append(t(58,128,"FOUNDATION · interactive 2D schematic (grounded)",12,GRN,700))
steps=[("Rendered schematic page (real scan)","the authoritative drawing"),
       ("Deep-zoom tile pyramid (OpenSeadragon)","pan + zoom to fine detail: holes, ports, connectors"),
       ("Callout coordinates (PyMuPDF words / OCR boxes)","find the FIG item-numbers on the page automatically"),
       ("Auto-placed clickable hotspots","each callout → the part row"),
       ("→ parts index (FIG+item → NSN / part#, cited)","click a callout → exact part, opens the page")]
yy=144
for h,d in steps:
    P.append(box(58,yy,524,40,P2,LINE,8))
    P.append(t(70,yy+18,h,10.3,TXT,700)); P.append(t(70,yy+33,d,8.8,SUB,400))
    if yy<144+4*48: P.append(arrow(320,yy+40,320,yy+48,GRN))
    yy+=48
# Optional 3D (right)
P.append(box(620,104,520,300,PANEL,AMB,12))
P.append(t(638,128,"OPTIONAL · true 3D module (BYO real 3D)",12,AMB,700))
P.append(box(638,144,484,66,P2,LINE)); P.append(t(650,164,"Source A — real CAD / 3D-TM",10.5,TXT,700)); 
s,_=wrap(650,180,"glTF, or STEP/IGES → glTF (IETM/S1000D/OEM). Accurate as-built geometry.",60,8.8,SUB,12); P.append(s)
P.append(box(638,218,484,66,P2,LINE)); P.append(t(650,238,"Source B — photogrammetry of the real part",10.5,TXT,700));
s,_=wrap(650,254,"Many photos → textured mesh. Build a library, prioritise look-alike parts.",60,8.8,SUB,12); P.append(s)
P.append(arrow(880,284,880,296,AMB))
P.append(box(638,298,484,46,"#3a2f1a",LINE)); P.append(t(650,318,"Three.js viewer · rotate · angle · zoom-to-feature",10.5,TXT,700)); P.append(t(650,333,"linked from the part record (parts.model_ref)",8.8,SUB,400))
P.append(box(638,352,484,40,P2,RED)); P.append(t(650,377,"✗ never AI-generated from a 2D scan (invents geometry)",9.6,"#e0a0a0",700))

# roadmap
P.append(t(40,438,"PHASED ROADMAP  (rough, focused-effort estimates; gated on schematic OCR)",12,ACC,700))
ph=[("PREREQ","Schematic OCR coverage","The coverage meter shows when a vehicle's schematics are searchable enough for auto-hotspots.","#243042","ongoing"),
    ("PHASE A","Interactive 2D viewer","Deep-zoom + auto callout hotspots → parts. The grounded core; most of the practical value.","#16301f","~2–4 wks"),
    ("PHASE B","Multi-view + hotspot polish","View switcher where TMs provide multiple views; manual hotspot touch-up tools.","#1a2740","~1–2 wks"),
    ("PHASE C (opt)","3D import module","Three.js viewer + glTF import; link models to parts. Needs real CAD files.","#3a2f1a","~2–3 wks"),
    ("PHASE D (opt)","Photogrammetry library","Capture pipeline + growing part library, look-alikes first.","#3a2f1a","~3–5 wks + capture")]
x=40; cw=214; gap=8
for i,(tag,h,d,col,est) in enumerate(ph):
    xx=x+i*(cw+gap)
    P.append(box(xx,458,cw,170,PANEL,LINE,11))
    P.append(f'<rect x="{xx}" y="458" width="{cw}" height="26" rx="0" fill="{col}"/>')
    P.append(t(xx+12,475,tag,9.5,TXT,700)); P.append(t(xx+cw-12,475,est,8.8,SUB,700,"end"))
    s,_=wrap(xx+12,502,h,26,11,TXT,13,700); P.append(s)
    s,_=wrap(xx+12,540,d,30,8.8,SUB,12); P.append(s)
    if i<len(ph)-1: P.append(arrow(xx+cw,520,xx+cw+gap,520,"#5d6675"))
P.append(box(40,644,1100,86,PANEL,LINE,12))
P.append(t(58,668,"THEORY / WHY THIS WAY",11,ACC,700))
s,_=wrap(58,688,"2D→3D from one image is mathematically underdetermined — depth is unrecoverable, so any single-image 3D is a guess. For maintenance, accuracy beats realism: a deep-zoom of the real drawing reliably shows the hole count and the connector; a generated mesh might not. True rotation is worth it only when fed by real geometry (CAD) or the real part (photogrammetry). So: grounded viewer now, real-3D module when the data exists.",172,9.6,SUB,13); P.append(s)
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/29-3d-architecture-roadmap"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
