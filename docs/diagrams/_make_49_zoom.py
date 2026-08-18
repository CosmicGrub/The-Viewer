#!/usr/bin/env python3
"""BUILT 0.35.0: page zoom — slider + scroll-to-cursor (loupe off) (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,620
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def arrow(x1,y1,x2,y2,col="#9aa5b1"): return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="1.6" fill="none" marker-end="url(#a)"/>'
def wrap(x,y,s,width,size,fill,dy=13,wt=400):
    out=[];words=s.split();c="";l=0
    for wd in words:
        if len(c)+len(wd)+1>width: out.append(t(x,y+l*dy,c,size,fill,wt));c=wd;l+=1
        else: c=(c+" "+wd).strip()
    if c: out.append(t(x,y+l*dy,c,size,fill,wt))
    return "".join(out),l+1
P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
P.append('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9aa5b1"/></marker></defs>')
P.append(box(0,0,W,H,BG,BG,0))
P.append(t(40,46,"BUILT — Page zoom: slider + scroll-to-cursor  (v0.35.0)",20,TXT,700))
P.append(t(40,70,"Slide the schematic closer, or hover a spot and scroll to zoom in/out toward it — smooth and instant, composed into the same transform as tilt/mirror.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# Panel 1: two ways to zoom
P.append(t(56,116,"1 · TWO WAYS TO ZOOM",12,ACC,700))
P.append(box(40,126,1100,210,PANEL,LINE,12))
# slider
P.append(t(70,156,"A · Zoom slider (like tilt X/Y)",10.5,TXT,700))
P.append(box(70,168,360,34,P2,LINE,8))
P.append(t(86,190,"zoom",9,SUB,400)); P.append(box(126,182,280,8,"#0a0e12",LINE,6)); P.append(f'<circle cx="250" cy="186" r="8" fill="{ACC}"/>')
P.append(t(86,222,"100% ───────────── 400%, continuous",9,SUB,400))
s,_=wrap(70,244,"Drag to scale the page about its centre. The % readout combines the render DPI and the slider so it always reads true.",58,9,SUB,12); P.append(s)
# scroll
P.append(t(560,156,"B · Hover + scroll (loupe OFF)",10.5,TXT,700))
P.append(f'<circle cx="640" cy="240" r="50" fill="none" stroke="{LINE}"/>')
P.append(box(610,210,60,60,"#0a0e12",ACC,6))
P.append('<text x="640" y="245" font-size="20" fill="#e6e9ee" text-anchor="middle">✛</text>')
P.append(arrow(700,224,740,210,ACC)); P.append(t(744,210,"scroll up → zoom in toward the spot",9,GRN,400))
P.append(arrow(700,256,740,270,ACC)); P.append(t(744,272,"scroll down → zoom out",9,SUB,400))
s,_=wrap(560,300,"Zooms toward the point under the cursor (transform-origin follows the pointer). Double-click resets to fit. When the loupe is ON, the wheel drives the loupe instead — no conflict.",80,9,SUB,12); P.append(s)

# Panel 2: how it composes
P.append(t(56,368,"2 · ONE TRANSFORM PIPELINE",12,ACC,700))
P.append(box(40,378,1100,150,PANEL,LINE,12))
chain=["scale(zoom)","perspective","rotateY (tilt Y)","rotateX (tilt X)","scaleX(-1) mirror"]
x=70
for i,c in enumerate(chain):
    P.append(box(x,400,190,40,P2,LINE,8)); P.append(t(x+95,425,c,9.4,TXT,700,"middle"))
    if i<len(chain)-1: P.append(arrow(x+190,420,x+202,420,ACC))
    x+=202
s,_=wrap(70,470,"Zoom is one more term in the viewer's CSS transform, so it stacks cleanly with tilt and mirror and stays GPU-smooth. Resets per page. The stage scrolls (overflow:auto) so you can pan a zoomed page; HD + the loupe keep fine detail crisp.",184,9.2,SUB,13); P.append(s)
P.append(t(70,512,"Presentation-only & reversible (R1/R6): the page data, index, search and 104th sheet are untouched.",9.2,GRN,400))
P.append(t(40,H-10,"BUILT diagram. Dark (R3). v0.35.0 · 2026-06-02.",9.2,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/49-zoom-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"), "bytes ->", base+".pdf")
