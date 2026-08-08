#!/usr/bin/env python3
"""Built: PUB LOG via FLIS Reading Room direct CSVs, folder-merge (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,660
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
P.append(t(40,46,"PUB LOG via the FLIS Reading Room — direct CSVs (built)",21,TXT,700))
P.append(t(40,70,"v0.23.0 · No Windows app needed: the Reading Room publishes monthly CSVs. enrich --publog-dir merges them per NSN (append-only, R6). Correction to 0.22.x.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
# the files (left)
P.append(box(40,104,420,310,PANEL,LINE,12))
P.append(t(58,128,"DOWNLOAD (free, no CAC) — direct monthly CSVs",11.5,AMB,700))
files=[("Identification","NSN → item name"),("H-Series (H6)","approved item names"),
       ("Reference","part # + CAGE"),("Characteristics","size / thread / material (Tier 2.5)"),
       ("Management","AAC + I&S substitutes"),("CAGE","manufacturer per CAGE"),
       ("History","INACTIVE / cancelled NSNs (kept, R6)")]
yy=146
for nm,fl in files:
    P.append(box(58,yy,384,30,P2,LINE,6)); P.append(t(70,yy+19,nm,10.3,TXT,700)); P.append(t(430,yy+19,fl,9,SUB,400,"end"))
    yy+=36
# flow to enrich (mid)
P.append(arrow(460,260,508,260,AMB))
P.append(box(508,180,300,160,PANEL,ACC,12))
P.append(t(526,204,"enrich --publog-dir <folder>",11.5,ACC,700))
s,_=wrap(526,226,"Reads every CSV; keeps only in-index NSNs; composes NSN from FSC+NIIN if needed; MERGES fields per NSN across files — non-clobbering. Appends every version to ref_nsn_log (R6).",42,9.2,SUB,13); P.append(s)
P.append(arrow(808,260,856,260,GRN))
# result (right)
P.append(box(856,180,284,160,PANEL,GRN,12))
P.append(t(874,204,"ONE MERGED RECORD",11.5,GRN,700))
s,_=wrap(874,226,"Identification→name · Reference→part#/CAGE · Characteristics→size — combined into the cited offline reference; cart auto-fills part# + AAC.",40,9.2,SUB,13); P.append(s)
# verified
P.append(box(40,430,1100,80,PANEL,LINE,12))
P.append(t(58,454,"VERIFIED",12,GRN,700))
s,_=wrap(58,476,"Folder ingest of 3 Reading-Room-style files (Identification + Reference + Characteristics) for one NSN → a single merged record (name + part# + CAGE + characteristics), with 3 versions retained in ref_nsn_log (non-clobbering UPSERT + append-only). Only the download is heavy; the ingest is fast (your NSNs only).",174,9.6,SUB,13); P.append(s)
P.append(box(40,524,1100,86,PANEL,AMB,12,1))
P.append(t(58,548,"CORRECTION & R6 NOTE",11.5,AMB,700))
s,_=wrap(58,570,"Earlier I said the PUB LOG fill needed DLA's Windows app + Batch/SQL export — the Reading Room makes that unnecessary; these are plain CSVs. And History.zip means even decommissioned NSNs in your corpus get nomenclature/part# — kept, never removed (R6).",176,9.6,SUB,13); P.append(s)
P.append(t(40,H-10,"Built & verified. Dark (R3) · CHANGELOG 0.23.0 (R4) · visual panel (R5) · quickstart in docs/PUBLOG-EXPORT-QUICKSTART.md.",9.0,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/35-flis-reading-room"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1180)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
