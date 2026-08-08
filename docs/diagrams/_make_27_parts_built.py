#!/usr/bin/env python3
"""Built: structured parts index (Phase 1) + coverage + quick wins (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,700
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
P.append(t(40,46,"Structured parts index — built (Phase 1)",22,TXT,700))
P.append(t(40,70,"v0.19.0 · RPSTL → cited NSN↔figure index · /api/part + /api/coverage · catalog refs in the cart · multi-sheet PDF · suggestion capture. Additive (migration 0004).",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
# pipeline
P.append(box(40,104,360,150,PANEL,LINE,12))
P.append(t(58,128,"EXTRACT (offline, idempotent)",12,ACC,700))
P.append(box(58,142,324,46,P2,LINE)); P.append(t(70,162,"viewer_ingest.py  parts",10.5,"#cfe0ff",700)); P.append(t(70,178,"scans RPSTL pages ('Usable On Code')",9.5,SUB,400))
P.append(arrow(220,188,220,202,ACC))
P.append(box(58,204,324,42,"#101a14",GRN)); 
s,_=wrap(70,224,"parts table (migration 0004): NSN · FIG# · figure title · doc · page · vehicle — cited.",54,9.3,SUB,12); P.append(s)
P.append(t(58,270,"Auto-refreshes after run / ocrall.",9.5,SUB,400))
# data proof
P.append(box(420,104,320,150,PANEL,GRN,12))
P.append(t(438,128,"PROVEN ON YOUR INDEX",12,GRN,700))
for i,(a,b) in enumerate([("RPSTL pages parsed","3,748"),("NSN records","28,330"),("distinct NSNs","10,521")]):
    P.append(box(438,142+i*34,284,28,P2,LINE,6)); P.append(t(450,161+i*34,a,10,TXT,400)); P.append(t(710,161+i*34,b,10.5,"#bfe6c5",700,"end"))
P.append(t(438,250,"(sample index; grows with the full corpus + OCR)",9,SUB,400))
# outputs
P.append(t(760,128,"OUTPUTS",12,AMB,700))
P.append(box(760,140,380,52,PANEL,LINE,10)); P.append(t(774,160,"Cart: cited catalog ref + FIG auto-fill",11,TXT,700)); 
s,_=wrap(774,176,"'📐 In parts catalog: FIG 3 Cooling System (p.372) — verify' · click opens the page",54,8.8,SUB,11); P.append(s)
P.append(box(760,200,380,46,PANEL,LINE,10)); P.append(t(774,220,"Vehicle hub: '% searchable' coverage badge",11,TXT,700)); P.append(t(774,236,"GET /api/coverage — Buffalo 99% · M998 97% · gens 91%",8.8,SUB,400))
P.append(box(760,254,380,46,PANEL,LINE,10)); P.append(t(774,274,"GET /api/part?nsn= → cross-references",11,TXT,700)); P.append(t(774,290,"same NSN across figures, each cited",8.8,SUB,400))

# quick wins
P.append(t(40,300,"QUICK WINS",12,ACC,700))
qw=[("Multi-sheet 104th",">6 items now paginate across sheets ('Sheet 2 of 2') instead of capping at 6.","#16301f"),
    ("Capture suggestion","sessions store the suggested tech status + basis next to the confirmed one — sharper learning.","#1a2740")]
for i,(h,d,col) in enumerate(qw):
    x=40+i*560
    P.append(box(x,316,540,58,col,LINE,10)); P.append(t(x+16,338,h,12,TXT,700)); s,_=wrap(x+16,356,d,76,9.4,SUB,13); P.append(s)

# grounding guarantee
P.append(box(40,392,1100,150,PANEL,RED,12,1))
P.append(t(58,416,"GROUNDED — AND HONEST ABOUT THE LIMIT",12,RED,700))
s,_=wrap(58,438,"What's reliable and shipped: the NSN→figure→page→vehicle citation index (every record points at a real page you can open and verify). The cart auto-fills only the FIG number from the catalog and shows the cited figure title; it never fabricates a part number or nomenclature.",150,10,SUB,15); P.append(s)
s,_=wrap(58,500,"Deliberately deferred: exact NSN↔part#↔nomenclature row alignment and automatic look-alike-variant warnings. OCR de-interleaves RPSTL columns, so asserting those now risks putting a wrong part on a request sheet. That precise table parser is the Phase-2 follow-up, strengthened by the ongoing OCR pass.",150,10,AMB,15); P.append(s)
P.append(t(40,H-14,"Verified on the live index: migration applies, extractor populates, /api/part & /api/coverage return cited data, multi-sheet PDF confirmed. Dark (R3) · CHANGELOG 0.19.0 (R4) · visual panel (R5).",9.4,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/27-structured-parts-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1180)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
