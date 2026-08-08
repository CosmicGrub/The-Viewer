#!/usr/bin/env python3
"""BUILT 0.50.0: one-click Add documents (folder ingest, no CLI) (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,620
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
P.append(t(40,46,"BUILT — Add documents: index new TMs without the command line  (v0.50.0)",19,TXT,700))
P.append(t(40,70,"Fulfils the mission's 'any additional files added without a sweat' goal: point the program at a folder of PDFs and it indexes the new ones — safely.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
# flow
P.append(t(56,116,"THE FLOW  (/ingest)",12,ACC,700))
P.append(box(40,126,1100,168,PANEL,LINE,12))
fl=[("Paste a folder","a path on this PC (sub-folders included)",PUR),
    ("Preview","/api/ingest_preview — read-only: how many PDFs, how many NEW vs already indexed, sample names",ACC),
    ("Snapshot + index","/api/ingest — safeguard snapshot, then the tested 'crawl' adds docs + extracts text + queues OCR",GRN),
    ("Live progress","/api/ingest_status reads the runs table: files seen · docs added · text pages · OCR queued",TEAL)]
x=58
for i,(h,d,c) in enumerate(fl):
    bx=x;P.append(box(bx,150,254,128,P2,c,10,1));P.append(t(bx+12,172,str(i+1)+" "+h,9.6,c,700));s,_=wrap(bx+12,192,d,42,8.4,SUB,11);P.append(s)
    if i<3:P.append(arrow(bx+254,214,bx+264,214,c));x+=266
P.append(t(58,318,"Already-indexed files are skipped (dedup by path + fingerprint); the crawl is resumable, so a big folder can be done in passes. Keep-alive makes the 2-second status polling cheap.",8.8,GRN,400))
# safety
P.append(t(56,352,"WHAT MAKES IT SAFE",12,ACC,700))
P.append(box(40,362,1100,150,PANEL,LINE,12))
sf=[("Additive only",GRN,"the crawl pipeline only ADDS documents and text — it never deletes or overwrites your existing corpus or index (R6)."),
    ("Snapshot first",ACC,"a safeguard snapshot is taken before any write, so the whole add is rollbackable (R1)."),
    ("Reuses the tested path",AMB,"runs the same viewer_ingest.py 'crawl' that built the corpus — no new, unproven write code; progress comes from the runs table."),
    ("Read-only preview",TEAL,"you see exactly what WOULD be added before committing — nothing is written during preview.")]
y=386
for nm,c,d in sf:
    P.append(f'<circle cx="58" cy="{y-3}" r="3.5" fill="{c}"/>');P.append(t(70,y,nm,9.8,c,700));s,n=wrap(230,y,d,126,8.6,SUB,11);P.append(s);y+=8+n*11
# grounded
P.append(box(40,526,1100,70,PANEL,GRN,12,1))
P.append(t(58,550,"VERIFIED",11.5,GRN,700))
s,_=wrap(58,568,"ingest_preview validated on a synthetic folder: 4 PDFs across sub-folders, 1 already indexed → 3 new, bad path rejected, status idle when nothing runs. The write path shells out to the proven crawl CLI in the background. After adding, run the GPU OCR to make scanned pages searchable. New /ingest + 3 endpoints; rollback = remove them. JS lints clean.",184,9.2,SUB,12.5);P.append(s)
P.append(t(40,H-12,"BUILT diagram. Dark (R3). v0.50.0 · 2026-06-02 · ingest_preview/start/status() in viewer_app.py + engine/ui/ingest.html. Additive (R1/R6).",9,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/67-ingest-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1180)
print("wrote", os.path.getsize(base+".pdf"), "bytes")
