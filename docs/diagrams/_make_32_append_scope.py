#!/usr/bin/env python3
"""Built: append-only NSN enrichment (R6) + space/scope of growing the dataset (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,760
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"
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
P.append(t(40,46,"More NSNs (append-only, R6) + the space/scope of growing the dataset",21,TXT,700))
P.append(t(40,70,"v0.21.0 · NSN enrichment now keeps every version forever (R6: add, never remove). And: what it costs to add NSNs vs whole TMs.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
# R6 banner
P.append(box(40,98,1100,30,"#101a14",GRN,7))
P.append(t(54,118,"NEW RULE R6 — append-only: you may always ADD to the search engine, but never take away, even if the information is outdated.",11,"#bfe6c5",700))
# append-only flow (left)
P.append(box(40,144,560,250,PANEL,LINE,12))
P.append(t(58,168,"APPEND-ONLY NSN ENRICHMENT (built)",12,ACC,700))
fl=[("GSA NSN Extract (re-fetch anytime)","official, data.gov"),
    ("ref_nsn_log — APPEND every version","old + new both kept; nothing overwritten-without-trace"),
    ("ref_nsn — 'current' pointer (latest)","convenience only; history lives in the log"),
    ("/api/reference → cart: current + 'N versions on file'","outdated NSN data stays searchable")]
yy=184
for h,d in fl:
    P.append(box(58,yy,524,42,P2,LINE,8)); P.append(t(70,yy+19,h,10.4,TXT,700)); P.append(t(70,yy+34,d,8.8,SUB,400))
    if yy<184+3*50: P.append(arrow(320,yy+42,320,yy+50,GRN))
    yy+=50
P.append(t(58,388,"Verified: two passes on one NSN → both versions retained; current = latest.",9,SUB,400))
# space/scope (right)
P.append(box(620,144,520,250,PANEL,LINE,12))
P.append(t(638,168,"SPACE & SCOPE — adding NSNs vs TMs",12,AMB,700))
rows=[("NSNs for everything in your set","TEXT","tiny — ~0.5 KB/row; even 100k NSNs ≈ tens of MB. (GSA bulk CSV download is a few hundred MB, but you keep only your matches.)",GRN),
      ("Hardware / thread standards","TEXT","trivial — kilobytes (FED-STD-H28 dims).",GRN),
      ("More TM documents (full manuals)","BINARY","heavy — PDFs MB–tens of MB each + OCR/index; hundreds of TMs = GB–tens of GB + OCR time. Different sourcing (public TM repositories, not data.gov).",AMB)]
yy=184
for h,kind,d,col in rows:
    bh=64
    P.append(box(638,yy,484,bh,P2,LINE,8))
    P.append(t(650,yy+20,h,10.6,TXT,700))
    P.append(box(1060,yy+8,52,18,col,LINE,5)); P.append(t(1086,yy+21,kind,8,"#0f1419",700,"middle"))
    s,_=wrap(650,yy+37,d,72,8.6,SUB,11); P.append(s)
    yy+=bh+6
# recommendation
P.append(box(40,410,1100,150,PANEL,LINE,12))
P.append(t(58,434,"WHAT I'D DO",12,GRN,700))
recs=["Your definite want — 'new NSNs for everything' — is the cheap one. Run `enrich --gsa <official GSA extract.csv>`: it appends current GSA name/desc/price for every NSN already in your index, keeping all prior versions (R6). Tens of MB at most.",
      "Standards/hardware: already seeded; trivial to extend.",
      "Adding whole TMs is the space-heavy, sourcing-sensitive part — best done deliberately by platform/manual, with version/authority checks. It's a different pipeline (crawl + OCR + index) than the NSN text enrichment.",
      "One practical note: the GSA Extract is a bulk download (hundreds of MB) — that's a file download, so I'll state size/source and get your OK, or you drop the CSV in and point `--gsa` at it."]
yy=456
for r in recs:
    P.append(t(58,yy,"•",10,GRN,700)); s,n=wrap(72,yy,r,150,9.3,SUB,13); P.append(s); yy+=n*13+5
P.append(t(40,H-16,"Built & verified on the live index (append-only retention confirmed). Dark (R3) · CHANGELOG 0.21.0 (R4) · visual panel (R5).",9.2,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/32-append-only-and-scope"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
