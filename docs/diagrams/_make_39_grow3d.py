#!/usr/bin/env python3
"""Roadmap: growing 3D coverage over time, grounded (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,890
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def arrow(x1,y1,x2,y2,col="#9aa5b1"): return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="1.7" fill="none" marker-end="url(#a)"/>'
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
P.append(t(40,46,"Growing the 3D coverage — methods that compound over time",21,TXT,700))
P.append(t(40,70,"Every method is grounded: dimensions come from FLIS or the manual's own drawings, never invented. Coverage climbs as OCR, FLIS refreshes, and curation accrue.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
# current state metrics
for i,(a,b,c) in enumerate([("45,068","part NSNs in index",ACC),("41,701","enriched from FLIS",GRN),("20,869","renderable in 3D now",AMB),("6,092","with a stated bore",GRN)]):
    x=40+i*278
    P.append(box(x,100,262,58,PANEL,LINE,10)); P.append(t(x+16,132,a,20,c,700)); P.append(t(x+108,132,b,10,SUB,400))
# the ladder
P.append(t(40,190,"THE GROWTH LADDER  (grounded → progressively richer)",12,ACC,700))
rungs=[
 ("1 · Expand the FLIS dimension parser","FREE · NOW",GRN,
  "Use the fields already in your data: 'overall length', 'body diameter', 'nominal thread size', radius, depth. Prefer OVERALL dims for accuracy; gate the button to renderable parts.",
  "Grounded: data already indexed · pushes ~20.9k → ~30k+ · low effort"),
 ("2 · Parametric family templates","RICHER SHAPES",ACC,
  "For standard families (bolt, nut, washer, flange, connector, bearing) render a real shape from the characteristics + thread — not just a box. Recognizable, still grounded.",
  "Grounded: standards + FLIS dims · med effort"),
 ("3 · Extract dimensions from the TM drawings","YOUR ASK",AMB,
  "Read dimension callouts off the figure/exploded-view pages (OCR boxes + dimension-line detection), tie them to the figure's part via the parts index, attach as cited dims. Literally 2D sketch → 3D dims.",
  "Grounded: the manual's own drawing, cited · needs OCR done · med-high effort"),
 ("4 · Multi-view orthographic reconstruction","HIGHER FIDELITY",AMB,
  "Where a TM gives front/side/section dimensioned views, reconstruct a more accurate solid (real engineering reconstruction).",
  "Grounded: the drawing's own views · high effort"),
 ("5 · Real CAD / photogrammetry (look-alikes)","EXACT, SELECTIVE",RED,
  "For the highest-value look-alike parts, import real CAD or photograph the part — exact surfaces where it matters. A library that grows.",
  "Grounded: real geometry · per-part labor / data-rights"),
 ("6 · SME confirm / curate loop","LEARNS",GRN,
  "Let an SME confirm/correct a part's dims or attach a model; stored & reused (like the parts learning). Coverage grows with use.",
  "Grounded: human-verified · low effort, ongoing"),
]
y=204
for h,tag,acc,d,meta in rungs:
    bh=86
    P.append(box(40,y,1100,bh,PANEL,LINE,11))
    P.append(f'<rect x="40" y="{y}" width="6" height="{bh}" rx="3" fill="{acc}"/>')
    P.append(t(60,y+24,h,12.5,TXT,700))
    P.append(box(1000,y+11,128,22,acc,LINE,6)); P.append(t(1064,y+26,tag,9,"#0f1419" if acc in(GRN,ACC,AMB) else TXT,700,"middle"))
    s,_=wrap(60,y+44,d,140,9.4,SUB,13); P.append(s)
    P.append(t(60,y+bh-10,meta,9,(("#8fae8f") if acc==GRN else ("#9bb3d6" if acc==ACC else ("#cbb87a" if acc==AMB else "#d98a8a"))),700))
    y+=bh+6
# compounding note
P.append(box(40,y+4,1100,70,PANEL,GRN,12,1))
P.append(t(58,y+28,"WHY IT COMPOUNDS",12,GRN,700))
s,_=wrap(58,y+48,"Each OCR pass makes more drawings readable (feeds #3/#4); each monthly FLIS refresh adds characteristics; each parser/template/SME addition lifts the renderable count — all additive (R1) and append-only (R6). A per-vehicle '3D coverage %' meter makes the climb visible. The representative model is the floor; CAD/photogrammetry is the ceiling for the parts that earn it.",172,9.6,SUB,13); P.append(s)
P.append(t(40,H-12,"Proposal — your call on which rungs to build. The interactive viewer already in chat is rung 0. Dark (R3).",9.4,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/39-grow-3d-coverage"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
