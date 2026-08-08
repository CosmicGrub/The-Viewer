#!/usr/bin/env python3
"""BUILT 0.51-0.54: workflow+ops wave — job packet, part dossier, find-in-manual, ops dashboard (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,760
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"
ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"; TEAL="#1d9e75"; PUR="#7f77dd"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def wrap(x,y,s,width,size,fill,dy=13,wt=400):
    out=[];words=s.split();c="";l=0
    for wd in words:
        if len(c)+len(wd)+1>width: out.append(t(x,y+l*dy,c,size,fill,wt));c=wd;l+=1
        else: c=(c+" "+wd).strip()
    if c: out.append(t(x,y+l*dy,c,size,fill,wt))
    return "".join(out),l+1
P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
P.append(box(0,0,W,H,BG,BG,0))
P.append(t(40,46,"BUILT — Workflow + Ops wave  (v0.51 – v0.54)",19,TXT,700))
P.append(t(40,70,"Bringing it together for the shop floor and keeping an eye on the engine. Four additive features; each reads existing indexes and deep-links the cited page.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

def panel(x,y,w,h,num,ver,title,color,rows,foot):
    out=[box(x,y,w,h,PANEL,LINE,12)]
    out.append(f'<rect x="{x}" y="{y}" width="6" height="{h}" rx="3" fill="{color}"/>')
    out.append(t(x+20,y+26,num,12,color,700)); out.append(t(x+44,y+26,title,13,TXT,700)); out.append(t(x+w-16,y+26,ver,10,SUB,700,"end"))
    yy=y+48
    for r in rows:
        out.append(f'<circle cx="{x+24}" cy="{yy-3}" r="3" fill="{color}"/>')
        s,n=wrap(x+36,yy,r,int((w-60)/5.2),8.8,SUB,11); out.append(s); yy+=4+n*11
    fs,_=wrap(x+20,y+h-22,foot,int((w-40)/5.0),8.4,GRN,11); out.append(fs)
    return "".join(out)

P.append(panel(40,108,552,210,"1","v0.51","🖨 Job packet  (/packet)",AMB,
  ["A take-to-the-bay sheet: the procedure (steps + tools + cautions) plus the parts-to-order table (NSN · UOC · CAGEC), with check-boxes and fillable bumper/WO fields.",
   "Light, print-optimised layout (@media print hides the chrome); one Print / Save-as-PDF button. Built from /api/procedure + /api/partdiff.",
   "Linked from the procedure page and the Solve-it hub."],
  "Dependency-free (browser print); read-only; verify on the cited sheet (R1/R6)."))
P.append(panel(604,108,552,210,"2","v0.52","📋 Part dossier  (/dossier)",PUR,
  ["One page per NSN that aggregates EVERYTHING: reference data, catalog figures, look-alike variants, the how-to procedure, the schematic and the 3-D model.",
   "Pulls /api/part + /api/reference + /api/partdiff + /api/procedure + /api/schematics + /api/threed and deep-links each.",
   "A single source of truth per part; jump-off buttons to packet / how-to / look-alike / solve."],
  "Read-only aggregation of existing endpoints; the manual stays truth (R1/R6)."))
P.append(panel(40,332,552,210,"3","v0.53","🔎 Find in manual  (Ctrl+F)",TEAL,
  ["The in-document Ctrl+F the mission asked for: type a term and jump between every match across the WHOLE open document — match count, per-page snippets, next/prev.",
   "/api/findindoc scopes the search to one document (fast); the match page opens with the term highlighted (reuses the page render hl=).",
   "Ctrl+F focuses the box; ▲/▼ and Enter/Shift+Enter cycle matches."],
  "Scoped, read-only; validated (3 hits/2 pages, doc-scoped) (R1/R6)."))
P.append(panel(604,332,552,210,"4","v0.54","📊 Ops dashboard  (/ops)",ACC,
  ["One glance at engine health: runtime RPS mode, document & vehicle counts, page-cache size, snapshot count, searchable coverage per vehicle, and recent ingest/OCR runs.",
   "/api/ops (cheap signals, no full OCR scan) + /api/coverage + /api/audit. A file-integrity audit flags indexed PDFs now MISSING on disk (unplugged drive, etc.).",
   "Links to the live OCR Status page for the running percentage."],
  "Read-only; cheap queries; audit validated (2/3 missing caught) (R1/R6)."))

P.append(box(40,560,1116,86,PANEL,GRN,12,1))
P.append(t(58,584,"THE ARC THIS COMPLETES",12,GRN,700))
s,_=wrap(58,604,"Find it (search + type-ahead) → understand it (look-alike, dossier) → do the job (procedure, Solve-it hub, job packet) → keep the corpus healthy (add documents, ops dashboard, file audit). Every feature this session is read-only and additive over the existing index, each deep-linking the real cited manual page; the mechanic's workflow is now one connected path, and the engine has an instrument panel.",186,9.4,SUB,13);P.append(s)
P.append(box(40,656,1116,72,PANEL,LINE,12))
P.append(t(58,678,"VERIFIED",11,ACC,700))
s,_=wrap(58,696,"All page JS lints clean (node --check). New server functions (find_in_doc, ops_summary, file_audit) compile and pass synthetic tests; the 21-test feature regression suite + 23 pillars stay green. Mount-truncation in the sandbox handled via fragment-extraction + synthetic DBs; file tools authoritative for the host machine.",186,9,SUB,12);P.append(s)
P.append(t(40,H-12,"BUILT diagram. Dark (R3). v0.51-0.54 · 2026-06-02 · packet/dossier/find_in_doc/ops in viewer_app.py + ui/{packet,dossier,ops}.html + index viewer. Additive (R1/R6).",9,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/68-workflow-ops-wave-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1180)
print("wrote", os.path.getsize(base+".pdf"), "bytes")
