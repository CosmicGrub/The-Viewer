#!/usr/bin/env python3
"""Built: online->offline reference enrichment, cited & official-only (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,680
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
P.append(t(40,46,"Online → offline reference enrichment — built",22,TXT,700))
P.append(t(40,70,"v0.20.0 · fetched ONCE from official public-domain sources · baked into separate, cited reference tables · engine stays offline. Additive (migration 0005).",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
# online sources
P.append(box(40,104,300,150,PANEL,LINE,12))
P.append(t(58,128,"ONLINE · once, official only",12,AMB,700))
P.append(box(58,142,264,46,P2,LINE)); P.append(t(70,162,"FED-STD-H28 (public domain)",10.3,TXT,700)); P.append(t(70,178,"standard-hardware thread/dims",9,SUB,400))
P.append(box(58,196,264,46,P2,LINE)); P.append(t(70,216,"GSA NSN Extract (data.gov)",10.3,TXT,700)); P.append(t(70,232,"official NSN → name / desc / price",9,SUB,400))
P.append(arrow(340,179,388,179,AMB))
# enrich
P.append(box(388,104,330,150,PANEL,ACC,12))
P.append(t(406,128,"viewer_ingest.py  enrich",12,ACC,700))
P.append(box(406,142,294,46,"#101a14",GRN)); P.append(t(418,162,"ref_hardware (cited seed)",10.3,"#bfe6c5",700)); P.append(t(418,178,"22 thread/dim rows · source + URL + date",8.6,SUB,400))
P.append(box(406,196,294,46,"#101a14",GRN)); P.append(t(418,216,"ref_nsn — filtered to YOUR NSNs",10.3,"#bfe6c5",700)); P.append(t(418,232,"--gsa CSV; only in-index NSNs ingested",8.6,SUB,400))
P.append(arrow(718,179,766,179,GRN))
# offline use
P.append(box(766,104,374,150,PANEL,LINE,12))
P.append(t(784,128,"OFFLINE · in the app",12,GRN,700))
P.append(box(784,142,338,100,P2,LINE))
P.append(t(796,162,"/api/reference → cart line:",10.3,TXT,700))
s,_=wrap(796,180,"📚 External reference (cited, offline): SCREW CAP HEX · GSA list $3.45 · thread 1/2-13 · tap 27/64 · ~75 lb-ft (general ref — TM governs)",52,8.8,"#9aa6b6",12); P.append(s)
# grounding guarantees
P.append(box(40,274,1100,150,PANEL,RED,12,1))
P.append(t(58,298,"PROVENANCE & SEPARATION (what keeps it grounded)",12,RED,700))
gg=["Stored in SEPARATE tables (ref_hardware / ref_nsn) — never merged into manual citations, so external data can't pose as TM-sourced.",
    "Every row carries source + URL + fetch date, and is labeled '📚 External reference (cited)' in the UI.",
    "Official / public-domain only (FED-STD-H28, GSA/data.gov). Third-party scrapers excluded by your choice.",
    "Torque shown is a GENERAL reference — the TM's stated torque governs. FEDLOG price/AAC/ARC still come from your AMDF (GSA shown as 'list', clearly labeled).",
    "NSN ingest is filtered to NSNs already in your index (targeted, relevant). Engine is offline after the one-time fetch."]
yy=320
for g in gg:
    P.append(t(58,yy,"•",10,RED,700)); s,n=wrap(72,yy,g,150,9.4,SUB,13); P.append(s); yy+=n*13+4
# honest note + verdict
P.append(box(40,440,1100,96,PANEL,LINE,12))
P.append(t(58,464,"WHAT IT UNLOCKS — and the remaining gap",12,GRN,700))
s,_=wrap(58,486,"Fills missing nomenclature on the request sheet, and gives cited dimensions for standard hardware (the Tier 2.5 key). For full parametric 3D you still need each part's specific SIZE — parsed from RPSTL text, the fuller NSN characteristics (FLIS) where available, or SME-confirmed; model only when size is certain (your decisions, recorded for Tier 2.5).",176,9.6,SUB,14); P.append(s)
P.append(t(40,H-16,"Verified on the live index: migration 0005 applies, hardware seed loads, GSA ingest keeps only in-index NSNs (bogus excluded), /api/reference returns cited data. Dark (R3) · CHANGELOG 0.20.0 (R4) · visual panel (R5).",9.2,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/31-reference-enrichment-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
