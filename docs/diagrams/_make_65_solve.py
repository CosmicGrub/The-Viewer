#!/usr/bin/env python3
"""BUILT 0.48.0: Solve-it workflow hub — symptom to fix in one place (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,600
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
P.append(t(40,46,"BUILT — Solve it: the workflow hub  (v0.48.0)",19,TXT,700))
P.append(t(40,70,"One screen that walks a mechanic from a symptom to a fix — stitching together features that already exist, each step cited. The program now matches the real shop workflow.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
# the chain
P.append(t(56,116,"THE CHAIN  (/solve — orchestrates the existing endpoints, no new index work)",12,ACC,700))
P.append(box(40,126,1100,210,PANEL,LINE,12))
chain=[("Symptom","'no-start, not charging' or a part / NSN",PUR),
       ("Likely parts","/api/faultparts — parts most used for this fault (your history) + manual hits (/api/search)",AMB),
       ("How to do it","/api/procedure — remove/install steps, tools, WARNINGs (cited)",GRN),
       ("Look-alike check","/api/partdiff — don't order the wrong NSN; the UOC is the tell",TEAL),
       ("Related schematic","/api/schematics — open the wiring in the viewer / Circuit Lab",ACC)]
x=58
for i,(h,d,c) in enumerate(chain):
    bx=x;P.append(box(bx,150,206,150,P2,c,10,1));P.append(t(bx+12,172,h,10,c,700));s,_=wrap(bx+12,192,d,33,8.2,SUB,11);P.append(s)
    if i<4:P.append(arrow(bx+206,225,bx+216,225,c));x+=216
P.append(t(58,326,"Two stages: (1) symptom → likely parts + the pages that mention it; (2) pick the part → the full fix bundle. Keep-alive (0.46) makes the multi-call orchestration snappy.",8.8,GRN,400))
# value
P.append(box(40,358,1100,100,PANEL,LINE,12))
P.append(t(58,382,"WHY IT MATTERS",11,AMB,700))
s,_=wrap(58,402,"Until now the mechanic had to bounce between search, the parts catalog, the procedure pages and the schematics by hand. The hub assembles them into one 'case file' for the job: what part, how to replace it, what tools, what to watch, which NSN is right for THIS vehicle, and the wiring — turning a pile of capabilities into a single guided path from broken to fixed.",184,9.4,SUB,13);P.append(s)
# grounded
P.append(box(40,470,1100,96,PANEL,GRN,12,1))
P.append(t(58,494,"GROUNDED & ADDITIVE (R1/R6)",12,GRN,700))
s,_=wrap(58,514,"Pure client-side orchestration of endpoints that are already tested — no new database work, nothing written back. Every panel deep-links to the real cited page so the manual stays the source of truth, and the UI reminds you to confirm torque, sequence and the exact NSN (UOC) on the sheet. New /solve route only; rollback = remove it. solve.html JS lints clean.",184,9.4,SUB,13);P.append(s)
P.append(t(40,H-12,"BUILT diagram. Dark (R3). v0.48.0 · 2026-06-02 · engine/ui/solve.html (+ /solve route). Reuses faultparts/search/procedure/partdiff/schematics.",9,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/65-solve-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"), "bytes")
