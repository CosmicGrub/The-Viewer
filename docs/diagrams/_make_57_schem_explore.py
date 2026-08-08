#!/usr/bin/env python3
"""BUILT 0.41.0: thorough schematics exploration — tilt any angle, mirror, related-sheets rail (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,600
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def wrap(x,y,s,width,size,fill,dy=13,wt=400):
    out=[];words=s.split();c="";l=0
    for wd in words:
        if len(c)+len(wd)+1>width: out.append(t(x,y+l*dy,c,size,fill,wt));c=wd;l+=1
        else: c=(c+" "+wd).strip()
    if c: out.append(t(x,y+l*dy,c,size,fill,wt))
    return "".join(out),l+1
P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
P.append(box(0,0,W,H,BG,BG,0))
P.append(t(40,46,"BUILT — Explore schematics from every angle  (v0.41.0)",20,TXT,700))
P.append(t(40,70,"The dedicated /schematics viewer now examines a sheet from the left, right, above, below — any angle — flips to the back, and jumps to the vehicle's other sheets.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# tilt demo
P.append(t(56,116,"1 · TILT TO ANY ANGLE + MIRROR (honest flat-sheet)",12,ACC,700))
P.append(box(40,126,545,250,PANEL,LINE,12))
poses=[("front","matrix(1,0,0,1,0,0)"),("tilt Y (side)","matrix(0.8,0.18,0,1,0,0)"),("tilt X (above)","matrix(1,0,-0.2,0.82,0,0)"),("mirror (back)","matrix(-1,0,0,1,0,0)")]
for i,(lab,mtx) in enumerate(poses):
    cx=110+(i%2)*250; cy=180+(i//2)*90
    P.append(f'<g transform="translate({cx},{cy}) {mtx.replace("matrix","matrix")}">')
    P.append(box(-46,-34,92,68,"#11161d","#3a4452",4))
    for k in range(4): P.append(f'<line x1="-36" y1="{-22+k*16}" x2="36" y2="{-22+k*16}" stroke="#46505f" stroke-width="1"/>')
    P.append('</g>')
    P.append(t(cx,cy+52,lab,8.8,SUB,400,"middle"))
P.append(t(58,360,"tilt X / tilt Y sliders (-70..70°) + ↔ mirror · CSS perspective — a real flat-sheet tilt, not invented depth.",8.6,GRN,400))

# rail + controls
P.append(t(620,116,"2 · RELATED SHEETS + FULL CONTROL SET",12,ACC,700))
P.append(box(604,126,536,250,PANEL,LINE,12))
P.append(t(622,150,"Related-sheets rail",10.5,TXT,700))
for i in range(5):
    P.append(box(622+i*100,160,88,52,"#fff","#2b333f",5))
    for k in range(3): P.append(f'<line x1="{628+i*100}" y1="{170+k*12}" x2="{702+i*100}" y2="{170+k*12}" stroke="#888" stroke-width="1"/>')
P.append(f'<rect x="622" y="160" width="88" height="52" rx="5" fill="none" stroke="{ACC}" stroke-width="2"/>')
s,_=wrap(622,232,"A filmstrip of the SAME vehicle's other schematic/wiring sheets (left-side, right-side, power, lighting…) — one click to switch. So every sensible view of the system is reachable, plus everything in between.",80,8.8,SUB,12); P.append(s)
P.append(t(622,296,"Per page: pan (drag) · zoom-to-cursor (wheel) · Clean · Blueprint · tilt X/Y · mirror · ⟲ reset · ←/→ paging.",8.8,SUB,400))
P.append(t(622,340,"All on the REAL rendered page — themed, tilted and navigated, never altered.",8.8,GRN,400))

P.append(box(40,392,1100,150,PANEL,GRN,12,1))
P.append(t(58,416,"THOROUGH, AND STILL GROUNDED (R1/R6)",12,GRN,700))
s,_=wrap(58,436,"'As thoroughly as possible': you can now examine a schematic from the left, the right, above, below, any angle in between, and the back — and hop across all the related sheets for that vehicle without leaving the viewer. It's presentation-only: the tilt is an honest flat-sheet rotation (CSS perspective), the mirror is a flip, and the page itself is never modified. A 2D schematic has no true hidden 3D, so we don't fabricate one — we let you explore the real sheet and its real companions fully.",182,9.4,SUB,13); P.append(s)
P.append(t(58,524,"Reachable from the home header (📐 Schematics). Pairs with the 3D Library. OCR (in progress) will add full-text search inside these sheets.",9,SUB,400))
P.append(t(40,H-12,"BUILT diagram. Dark (R3). v0.41.0 · 2026-06-02 · engine/ui/schematics.html.",9.2,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/57-schem-explore-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1180)
print("wrote", os.path.getsize(base+".pdf"), "bytes")
