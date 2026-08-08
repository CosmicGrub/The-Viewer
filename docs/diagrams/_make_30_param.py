#!/usr/bin/env python3
"""Proposal: dimension-driven parametric reconstruction (Tier 2.5) — what the docs can/can't ground (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,860
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def arrow(x1,y1,x2,y2,col="#9aa5b1"): return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="1.7" fill="none" marker-end="url(#a)"/>'
def wrap(x,y,s,width,size,fill,dy=14,wt=400):
    out=[];words=s.split();line="";ln=0
    for wd in words:
        if len(line)+len(wd)+1>width: out.append(t(x,y+ln*dy,line,size,fill,wt));line=wd;ln+=1
        else: line=(line+" "+wd).strip()
    if line: out.append(t(x,y+ln*dy,line,size,fill,wt))
    return "".join(out),ln+1
P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
P.append('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9aa5b1"/></marker></defs>')
P.append(box(0,0,W,H,BG,BG,0))
P.append(t(40,46,"Dimension-driven parametric reconstruction — does the combo count? Yes, for a real subset",20,TXT,700))
P.append(t(40,70,"Reconstructing 3D from stated dimensions + views is real engineering, NOT generation. The catch: TMs/RPSTLs are illustrations + scattered specs — not full dimensioned drawings (TDP).",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
# evidence strip
P.append(box(40,100,1100,52,P2,LINE,8))
P.append(t(54,120,"In your corpus (sample):",10,SUB,700))
ev=[("diameter","846"),("threads","~600"),("torque","1,706"),("dim/spec tables","1,301"),("clearances","1,807")]
x=240
for a,b in ev:
    P.append(t(x,120,a,9.5,SUB,400)); P.append(t(x+len(a)*6.2+4,120,b,9.5,"#bfe6c5",700)); x+=len(a)*6.2+len(b)*7+34
P.append(t(54,142,"BUT — tolerances: 85 · explicit bolt-circles: 2  → full GD&T / complete dimensioning is rare (these aren't engineering drawings).",9.3,AMB,400))
# two columns
P.append(box(40,168,545,250,PANEL,GRN,12))
P.append(t(58,192,"WHAT IT RELIABLY GROUNDS",12,GRN,700))
good=[("Standard / parametric parts (big population)","NSN/part# → a standard (bolt, nut, washer, fitting, bearing, connector) → exact geometry from the standard's tables."),
      ("The distinguishing features themselves","Thread size, hole/port COUNT, connector/pin type — stated or countable in the figure. This is the look-alike case, nailed."),
      ("Key stated dimensions","Diameters, lengths, clearances, port/thread sizes that the manual does give — enough to size a parametric family member exactly.")]
yy=210
for h,d in good:
    P.append(t(58,yy,"• "+h,10.3,TXT,700)); s,n=wrap(70,yy+15,d,72,9.2,SUB,12); P.append(s); yy+=15+n*12+10
P.append(box(595,168,545,250,PANEL,AMB,12))
P.append(t(613,192,"WHERE IT BECOMES INFERENCE",12,AMB,700))
bad=[("Complex castings / housings","A TM rarely dimensions every surface of an irregular casting → the model would interpolate the un-stated geometry. Guessing."),
     ("Under-dimensioned / single illustration","One exploded view + no dimensions = depth unrecoverable for that shape."),
     ("Internal / occluded features","What isn't drawn or specified can't be reconstructed.")]
yy=210
for h,d in bad:
    P.append(t(613,yy,"• "+h,10.3,TXT,700)); s,n=wrap(625,yy+15,d,72,9.2,SUB,12); P.append(s); yy+=15+n*12+12
# pipeline
P.append(t(40,448,"GROUNDED PIPELINE (Tier 2.5 — slots between the 2D viewer and real-CAD/photogrammetry)",12,ACC,700))
steps=[("Extract parameters","spec tables (parsable) · NSN→standard identity · countable features (holes/ports) · SME confirms a few key dims",P2),
       ("Parametric CAD generator","code-CAD (CadQuery / build123d / OpenSCAD) — exact, offline, per part-FAMILY template instantiated by the params",("#16301f")),
       ("Confidence-labeled 3D (Three.js)","rotate · angle · zoom-to-feature · linked from the part — SPECIFIED features exact; unstated surfaces shown schematic & flagged",("#3a2f1a"))]
x=40; cw=355; gap=17; y=466
for i,(h,d,col) in enumerate(steps):
    xx=x+i*(cw+gap)
    P.append(box(xx,y,cw,108,col,LINE,11))
    P.append(t(xx+14,y+24,str(i+1)+" · "+h,11.5,TXT,700))
    s,_=wrap(xx+14,y+44,d,52,9.3,SUB,13); P.append(s)
    if i<2: P.append(arrow(xx+cw,y+54,xx+cw+gap,y+54,ACC))
# grounding rule
P.append(box(40,596,1100,96,PANEL,RED,12,1))
P.append(t(58,620,"THE GROUNDING RULE (what keeps it honest)",12,RED,700))
s,_=wrap(58,642,"Model only what the documentation specifies. A specified feature (thread, hole count, port, stated dimension) is rendered exactly and cited to its source. Anything not specified is shown as a plain schematic placeholder, clearly marked 'representative — not to scale', and never presented as authoritative geometry. So a reconstructed part is trustworthy precisely where it's labeled trustworthy — and the look-alike difference is always in the trustworthy part.",172,9.6,SUB,13); P.append(s)
# verdict
P.append(box(40,704,1100,120,PANEL,LINE,12))
P.append(t(58,728,"VERDICT — yes, it accounts for something real:",12,GRN,700))
s,_=wrap(58,750,"For the large standard-hardware population and for the exact distinguishing features between look-alikes, dimension-driven parametric reconstruction gives accurate, rotatable, cited 3D from the docs alone — no photos, no CAD sourcing. It does NOT give accurate full 3D of arbitrary complex castings from a TM (that still needs a TDP or photogrammetry). Best use: auto-build standard parts + a 'spec-accurate' model that visibly encodes the look-alike difference; fall back to the 2D viewer where the geometry isn't specified.",176,9.7,SUB,14); P.append(s)
P.append(t(40,H-12,"Proposal only — nothing built. Companion to diagrams 28–29. Dark (R3). Your call on whether to add Tier 2.5.",9.6,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/30-parametric-reconstruction"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1180)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
