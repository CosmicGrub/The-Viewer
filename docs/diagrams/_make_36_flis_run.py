#!/usr/bin/env python3
"""Done: PUB LOG enrichment RUN on the live index (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,650
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"
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
P.append(t(40,46,"PUB LOG enrichment — RUN on your live index",21,TXT,700))
P.append(t(40,70,"v0.24.0 · The 16 GB FLIS Reading Room catalog ingested into viewer.db (NIIN-keyed), append-only & cited. Index verified intact (39,683 docs).",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
# pipeline
P.append(box(40,104,250,150,PANEL,LINE,12))
P.append(t(58,128,"YOUR DOWNLOAD",12,AMB,700))
s,_=wrap(58,150,"16 GB FLIS Reading Room CSVs: Identification, Part, Management, Characteristics, Cancelled, H6 names.",30,9.4,SUB,13); P.append(s)
P.append(arrow(290,179,338,179,AMB))
P.append(box(338,104,300,150,PANEL,ACC,12))
P.append(t(356,128,"enrich_flis (NIIN-keyed)",12,ACC,700))
s,_=wrap(356,150,"Match middle-9-digit NIIN of each index NSN; INC→item name via H6; aggregate characteristics; merge non-clobbering; append-only (R6).",40,9.2,SUB,13); P.append(s)
P.append(arrow(638,179,686,179,GRN))
P.append(box(686,104,454,150,PANEL,GRN,12))
P.append(t(704,128,"LIVE in viewer.db",12,GRN,700))
fills=[("468","NSNs enriched"),("406","item names"),("463","part numbers"),("451","AAC codes"),("421","with characteristics (real dims)")]
yy=150
for a,b in fills:
    P.append(t(704,yy,a,11,"#bfe6c5",700)); P.append(t(745,yy,b,10,SUB,400)); yy+=18
# real examples
P.append(box(40,274,1100,130,PANEL,LINE,12))
P.append(t(58,298,"REAL RECORDS NOW IN YOUR OFFLINE INDEX (cited)",12,GRN,700))
ex=["6115-01-036-6374 → GENERATOR SET, DIESEL ENGINE · P/N MEP007B · CAGE 30554 · AAC V · $35,140.51 · freq 50–60 Hz, three-phase",
    "5985-00-933-2197 → MAST · P/N AB903G · nested height 72.000 in · base diameter 4.250 in (telescoping)",
    "5820-01-043-6476 → MODEM, COMMUNICATIONS · P/N SM-D-777153 · CAGE 80063 · $89,969.00"]
yy=322
for e in ex:
    P.append(t(58,yy,"• "+e,9.6,"#bfe6c5" if False else SUB,400)); yy+=22
P.append(t(58,yy+2,"Cart now auto-fills the authoritative part # and AAC onto the 104th; characteristics feed Tier 2.5.",9.6,ACC,400))
# next + honesty
P.append(box(40,420,1100,80,PANEL,AMB,12,1))
P.append(t(58,444,"COVERAGE & NEXT STEP",12,AMB,700))
s,_=wrap(58,466,"468 of ~501 cover/end-item NSNs were matched. The thousands of individual RPSTL part NSNs aren't extracted on viewer.db yet — run `parts` on the full index, then re-run enrich --publog-dir to fill those too. Productized as enrich_flis() for monthly re-runs.",176,9.6,SUB,13); P.append(s)
P.append(box(40,512,1100,60,PANEL,GRN,12,1))
P.append(t(58,534,"SAFE",12,GRN,700))
s,_=wrap(58,554,"Written with TRUNCATE journaling; the interrupted first attempt (slowed only by a full-DB integrity check) committed nothing; the index re-reads cleanly with all 39,683 docs. Additive (R1), append-only (R6).",176,9.6,SUB,13); P.append(s)
P.append(t(40,H-10,"Done & live. Dark (R3) · CHANGELOG 0.24.0 (R4) · visual panel (R5).",9.0,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/36-flis-enrichment-run"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1180)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
