#!/usr/bin/env python3
"""BUILT 0.47.0: How-to-do-it (procedure) view — steps + tools + cautions from the manuals (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,640
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"
ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"; TEAL="#1d9e75"; PUR="#7f77dd"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def arrow(x1,y1,x2,y2,col="#9aa5b1"): return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="1.7" fill="none" marker-end="url(#a)"/>'
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
P.append(t(40,46,"BUILT — How to do it: the procedure view  (v0.47.0)",19,TXT,700))
P.append(t(40,70,"Closes the mission's 'complete instructional rundown' gap: find a part, then see HOW to remove/install it — steps, tools, and the WARNINGs — each cited to the real page.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
# flow
P.append(t(56,116,"1 · FROM A PART NAME TO THE STEPS  (/procedure · /api/procedure)",12,ACC,700))
P.append(box(40,126,1100,150,PANEL,LINE,12))
fl=[("Part / NSN","what you searched",PUR),("FTS match","pages with this part AND a procedure word (removal/install/…)",ACC),
    ("Parse the page","numbered steps · TOOLS REQUIRED block · WARNING/CAUTION/NOTE · section kind",TEAL),
    ("Present + cite","kind-tagged cards, tools chips, caution callouts, link to the real page",GRN)]
x=58
for i,(h,d,c) in enumerate(fl):
    bx=x;P.append(box(bx,150,250,108,P2,c,10,1));P.append(t(bx+12,172,str(i+1)+" "+h,10,c,700));s,_=wrap(bx+12,192,d,40,8.4,SUB,11);P.append(s)
    if i<3:P.append(arrow(bx+250,204,bx+262,204,c));x+=262
# what it extracts
P.append(t(56,308,"2 · WHAT IT EXTRACTS FROM EACH PAGE",12,ACC,700))
P.append(box(40,318,1100,170,PANEL,LINE,12))
ex=[("Section kind",AMB,"Removal / Installation / Disassembly / Assembly / Replacement / Adjustment / Repair / Service / Inspection / Cleaning — from a standalone heading (not 'ENGINE ASSEMBLY')."),
    ("Numbered steps",GRN,"lines like '1. Disconnect…' '2. Drain…' captured in order, in full."),
    ("Tools required",ACC,"the 'TOOLS REQUIRED / Special Tools / TMDE' block — listed as chips so you can stage them before starting."),
    ("Cautions",RED,"WARNING / CAUTION / NOTE / DANGER callouts pulled out and colour-coded so safety text can't be missed.")]
y=342
for nm,c,d in ex:
    P.append(f'<circle cx="58" cy="{y-3}" r="3.5" fill="{c}"/>');P.append(t(70,y,nm,9.8,c,700));s,n=wrap(220,y,d,128,8.8,SUB,11);P.append(s);y+=10+n*11
# grounded + verified
P.append(box(40,500,1100,124,PANEL,GRN,12,1))
P.append(t(58,524,"GROUNDED, AND HONEST ABOUT IT (R1/R6)",12,GRN,700))
s,_=wrap(58,544,"The procedures table shipped empty, so this parses the procedure straight from the manual page TEXT at query time — read-only, nothing invented or written back. Every card links to the real cited page and the UI says 'verify torque, sequences and cautions on the actual sheet'. It's a fast on-ramp to the page, not a replacement for it. Coverage grows as OCR makes more scanned procedure pages searchable. Parser verified on a representative work-package page: kind=Removal, 3 steps, tools + WARNING/CAUTION/NOTE all captured; the FTS query mirrors the proven search() path.",184,9.4,SUB,13);P.append(s)
P.append(t(40,H-12,"BUILT diagram. Dark (R3). v0.47.0 · 2026-06-02 · procedure_for()+_parse_procedure() in viewer_app.py + engine/ui/procedure.html. Read-only.",9,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/64-procedure-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1180)
print("wrote", os.path.getsize(base+".pdf"), "bytes")
