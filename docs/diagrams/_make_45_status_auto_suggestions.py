#!/usr/bin/env python3
"""BUILT 0.31.0: System Status page + auto-snapshots + OCR finishing + suggestions (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,840
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"; TEAL="#1d9e75"
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
def bar(x,y,w,pct,col):
    return box(x,y,w,12,P2,LINE,6)+f'<rect x="{x}" y="{y}" width="{int(w*pct/100)}" height="12" rx="6" fill="{col}"/>'
P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
P.append('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9aa5b1"/></marker></defs>')
P.append(box(0,0,W,H,BG,BG,0))
P.append(t(40,46,"BUILT — System Status · auto-snapshots · OCR finishing · suggestions  (v0.31.0)",19,TXT,700))
P.append(t(40,70,"A one-glance health page, automatic daily backups, a resumable OCR finisher, and three recall/curation features — all additive.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# Panel 1: status page mock
P.append(t(56,116,"1 · SYSTEM STATUS PAGE  (/status · /api/status)",12,ACC,700))
P.append(box(40,126,560,290,PANEL,LINE,12))
# metric tiles
for i,(k,v) in enumerate([("Documents","39,683"),("Pages","1,848,465"),("Parts","227,908"),("NSNs","41,701")]):
    x=58+i*132; P.append(box(x,144,122,46,P2,LINE,8)); P.append(t(x+12,162,k,8.6,SUB,400)); P.append(t(x+12,182,v,13,TXT,700))
P.append(t(58,214,"Searchable coverage",10,TXT,700)); P.append(t(560,214,"93.5%",10,GRN,700,"end"))
P.append(bar(58,222,524,93.5,GRN))
P.append(t(58,254,"OCR progress",10,TXT,700)); P.append(t(560,254,"1.6% (118,964 pending)",10,AMB,700,"end"))
P.append(bar(58,262,524,2,AMB))
P.append(box(58,286,256,52,P2,LINE,8)); P.append(t(70,304,"Data protection",9.4,SUB,700)); P.append(t(70,322,"last snapshot · vault count",8.8,SUB,400))
P.append(box(326,286,256,52,P2,LINE,8)); P.append(t(338,304,"Correlations",9.4,SUB,700)); P.append(t(338,322,"19,511 interchange · 884 drift",8.8,SUB,400))
P.append(t(58,360,"NIIN-drift review queue (FSC-conflict flagged) + Fault→parts lookup",9.2,SUB,400))
P.append(t(58,378,"Fast: indexed counts only — no slow full-table scans on the 3.6 GB index.",9,GRN,400))
P.append(t(58,398,"Read-only dashboard; opens at http://127.0.0.1:8765/status",8.8,SUB,400))

# Panel 2: auto snapshots
P.append(t(620,116,"2 · AUTOMATIC SNAPSHOTS",12,ACC,700))
P.append(box(604,126,536,290,PANEL,LINE,12))
P.append(box(624,146,230,52,"#13241c",GRN,8)); P.append(t(739,168,"Daily Windows task",10,"#bfe6cf",700,"middle")); P.append(t(739,184,"register_snapshot_task.bat",8.6,"#8fbf9f",400,"middle"))
P.append(arrow(854,172,884,172,TEAL))
P.append(box(890,146,230,52,P2,LINE,8)); P.append(t(1005,168,"safeguard snapshot+verify",9,TXT,700,"middle")); P.append(t(1005,184,"06:00 daily",8.6,SUB,400,"middle"))
P.append(t(624,228,"Plus: snapshot BEFORE every data-mutating run",10,TXT,700))
for i,(a,b) in enumerate([("run_ocr_gpu.bat","--label pre-ocr"),("run_enrich.bat","--label pre-enrich")]):
    y=248+i*30; P.append(t(640,y,"• "+a,9.6,TXT,700)); P.append(t(900,y,b,9.2,AMB,400))
s,_=wrap(624,316,"Runs natively on Windows so it reads the real, intact files. Snapshots are additive (R6); the main index is never modified (R1). Pre-op snapshots give a restore point; enrichment also has its own rollback.",80,9,SUB,12); P.append(s)
s,_=wrap(624,372,"Manual any time: run_safeguard.bat snapshot | verify | recover /all.",80,8.8,GRN,12); P.append(s)

# Panel 3: OCR finishing
P.append(t(56,442,"3 · OCR FINISHING (resumable, on your GPU)",12,ACC,700))
P.append(box(40,452,560,150,PANEL,LINE,12))
steps=[("prioritize","parts catalogs first"),("ocr batch","RapidOCR + CUDA"),("loop until pending=0","resumable"),("refresh parts index","auto")]
x=58
for i,(h,d) in enumerate(steps):
    P.append(box(x,472,124,52,P2,LINE,8)); P.append(t(x+10,492,h,9.2,TXT,700)); s,_=wrap(x+10,508,d,20,8.2,SUB,10); P.append(s)
    if i<3: P.append(arrow(x+124,498,x+132,498,ACC))
    x+=132
s,_=wrap(58,548,"118,964 scanned pages remain (6.5%). 'ocrall' already finishes them across resumable batches; a snapshot is taken first and progress shows on the status page. The multi-day run executes on YOUR GPU — I made it bulletproof + trackable, I can't run it in this environment.",90,9,SUB,12); P.append(s)

# Panel 4: suggestions
P.append(t(620,442,"4 · SUGGESTIONS DEVELOPED",12,ACC,700))
P.append(box(604,452,536,150,PANEL,LINE,12))
sg=[("Nomenclature normalization","'BOLT, MACHINE'<->'machine bolt', gskt->gasket; widens recall (tested)",GRN),
    ("Fault -> parts","/api/faultparts: parts most requested for similar faults (your history)",ACC),
    ("NIIN-drift review queue","/api/niin_review: 884 groups, FSC-conflict flagged for review",AMB),
    ("Scanner-friendly NSN","USB barcode wedge types into search; camera-scan optional later",SUB)]
y=472
for h,d,c in sg:
    P.append(f'<circle cx="624" cy="{y}" r="4" fill="{c}"/>'); P.append(t(636,y+4,h,9.8,TXT,700)); s,_=wrap(636,y+18,d,82,8.6,SUB,11); P.append(s); y+=34

# invariants + honesty
P.append(box(40,620,1100,90,PANEL,GRN,12,1))
P.append(t(58,644,"GROUNDING & INVARIANTS (R1 · R6)",12,GRN,700))
s,_=wrap(58,664,"All additive and reversible: new read-only endpoints + a status page + Windows automation; no change to the dataset, FTS search, or 104th sheet. Nomenclature widening only ADDS results when a query is sparse. Honest gaps: tool-list roll-up needs structured 'tools' data (the procedures table is empty) so it's deferred; fault->parts grows as requests are logged; OCR completion is GPU-time on your machine.",182,9.6,SUB,13); P.append(s)
P.append(box(40,718,1100,96,PANEL,LINE,12))
P.append(t(58,742,"NEW ENDPOINTS / FILES",12,AMB,700))
for i,(a,b) in enumerate([("/api/status + /status","fast health dashboard"),("/api/niin_review","drift queue (sidecar)"),
     ("/api/faultparts","predictive parts from history"),("register_snapshot_task.bat","daily Windows backup"),
     ("normalize_nomenclature()","recall widening (in search)"),("snapshot hooks","pre-ocr / pre-enrich")]):
    cx=58+(i%3)*370; cy=766+(i//3)*22; P.append(t(cx,cy,"• "+a,9.6,TXT,700)); P.append(t(cx+200,cy,b,9,SUB,400))
P.append(t(40,H-8,"BUILT diagram. Dark (R3). v0.31.0 · 2026-06-02.",9.2,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/45-status-auto-suggestions-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"), "bytes ->", base+".pdf")
