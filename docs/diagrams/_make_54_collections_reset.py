#!/usr/bin/env python3
"""BUILT 0.39.0: 3D Library + Schematics Library collection pages + reset buttons (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,700
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; TEAL="#1d9e75"
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
P.append(t(40,46,"BUILT — 3D Library + Schematics Library + reset everywhere  (v0.39.0)",20,TXT,700))
P.append(t(40,70,"Two dedicated, browsable collection pages reachable from the header, plus a Reset on every moveable view.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# Panel 1: two libraries
P.append(t(56,116,"1 · TWO COLLECTION PAGES (linked from the home header)",12,ACC,700))
P.append(box(40,126,1100,250,PANEL,LINE,12))
# 3D
P.append(box(60,148,510,210,PANEL,ACC,10,1)); P.append(t(80,172,"🧊 3D Library   /3d",12,ACC,700))
s,_=wrap(80,192,"Every part with enough FLIS dimensions to render a representative 3D shape — 20,869 of them. Searchable, paginated grid; each card is a live mini 3D thumbnail.",66,9.2,SUB,12); P.append(s)
P.append(t(80,248,"Click → drag-rotate · scroll-zoom · ⟲ reset · double-click reset",9,GRN,400))
P.append(t(80,266,"/api/threed?q=&limit=&offset=  (ref_nsn with DIAMETER/LENGTH/…)",8.4,SUB,400))
P.append(t(80,292,"Self-contained renderer: family shape (cyl/hex/disc/box),",8.6,SUB,400))
P.append(t(80,306,"material/colour tint, depth-shaded — NOT a CAD model (grounded).",8.6,SUB,400))
# schematics
P.append(box(600,148,510,210,PANEL,AMB,10,1)); P.append(t(620,172,"📐 Schematics Library   /schematics",12,AMB,700))
s,_=wrap(620,192,"Every schematic / wiring-diagram document in the corpus — 1,093 of them. Searchable by vehicle / TM / title / NSN; each card shows a rendered page-1 thumbnail.",66,9.2,SUB,12); P.append(s)
P.append(t(620,248,"Click → built-in page viewer: prev/next, 🧹 clean, zoom ±, ⟲ reset",9,GRN,400))
P.append(t(620,266,"/api/schematics?q=&limit=&offset=  (documents typed schematic/wiring)",8.4,SUB,400))
P.append(t(620,292,"Pages render on demand via /page; arrow keys page through.",8.6,SUB,400))
P.append(t(620,306,"Exploded-view RPSTL figures remain in the vehicle hub.",8.6,SUB,400))

# Panel 2: reset
P.append(t(56,408,"2 · RESET ON EVERY MOVEABLE / INTERACTIVE VIEW",12,ACC,700))
P.append(box(40,418,1100,200,PANEL,LINE,12))
rsets=[("Schematic page viewer","⟲ Reset clears tilt X/Y, zoom, and mirror back to the default view (sliders + buttons reset too)."),
       ("Representative 3D viewer","⟲ Reset + double-click restores the default rotation + zoom."),
       ("3D Library cards","double-click or ⟲ in the modal resets rotation/zoom."),
       ("Schematics viewer","⟲ Reset returns zoom to 100%.")]
y=444
for h,d in rsets:
    P.append(f'<circle cx="60" cy="{y-4}" r="3.5" fill="{GRN}"/>'); P.append(t(74,y,h,10,TXT,700)); s,_=wrap(310,y,d,108,9,SUB,12); P.append(s); y+=34
s,_=wrap(60,584,"Triggered by the user demonstrating tilt with no way to reset. Every transform now has a clearly-labelled Reset; presentation-only and reversible (R1).",184,9.2,GRN,13); P.append(s)
P.append(t(40,H-12,"BUILT diagram. Dark (R3). v0.39.0 · 2026-06-02 · new pages: ui/threed.html, ui/schematics.html.",9.2,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/54-collections-reset-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1180)
print("wrote", os.path.getsize(base+".pdf"), "bytes ->", base+".pdf")
