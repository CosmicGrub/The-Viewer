#!/usr/bin/env python3
"""Built (POC): PUB LOG reference ingest — part#/CAGE/characteristics/AAC/substitutes (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,680
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
P.append(t(40,46,"PUB LOG reference ingest — proof of concept (built)",21,TXT,700))
P.append(t(40,70,"v0.22.0 · enrich --publog reads a PUB LOG export and fills NSN→name/part#/CAGE/characteristics/AAC/substitutes. Append-only (R6), cited, offline. Migration 0007.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
# flow
P.append(box(40,104,300,120,PANEL,LINE,12))
P.append(t(58,128,"ONE-TIME (connected machine)",12,AMB,700))
s,_=wrap(58,150,"Download PublogDVD.zip (free, no CAC) → PUB LOG Batch/SQL export → CSV (NSN, item name, part#, CAGE, characteristics, AAC, substitutes).",40,9.4,SUB,13); P.append(s)
P.append(arrow(340,164,388,164,AMB))
P.append(box(388,104,330,120,PANEL,ACC,12))
P.append(t(406,128,"enrich --publog <csv>",12,ACC,700))
s,_=wrap(406,150,"Matches ONLY NSNs already in your index; appends a version to ref_nsn_log (R6) and UPSERTs ref_nsn. CSV or XLSX.",46,9.4,SUB,13); P.append(s)
P.append(arrow(718,164,766,164,GRN))
P.append(box(766,104,374,120,PANEL,GRN,12))
P.append(t(784,128,"OFFLINE in the app",12,GRN,700))
s,_=wrap(784,150,"Cart auto-fills authoritative PART # (MCRD) + AAC; shows item name, CAGE, characteristics, substitutes — labeled '📚 External reference (cited).'",46,9.4,SUB,13); P.append(s)
# verified sample
P.append(box(40,244,1100,120,PANEL,LINE,12))
P.append(t(58,268,"VERIFIED ON THE LIVE INDEX (POC)",12,GRN,700))
P.append(box(58,282,1064,30,P2,LINE,6))
P.append(t(70,302,"NSN 6115-00-118-1241  →  SCREW, CAP, HEXAGON HEAD · P/N MS90726-60 · CAGE 96906 · AAC D · char: 1/2-13 UNC; GR5; STEEL · subs: 5305-01-310-1234",10,"#bfe6c5",400))
s,_=wrap(58,330,"PUB LOG ingest filtered to in-index NSNs (a bogus NSN was excluded). Every field landed and is queryable via /api/reference; part# + AAC auto-fill the 104th.",170,9.6,SUB,13); P.append(s)
# what each field unblocks
P.append(t(40,388,"WHAT EACH FIELD CLOSES",12,AMB,700))
cells=[("PART # + CAGE (MCRD)","auto-fills the 104th part# — the authoritative number OCR couldn't pin down",GRN),
       ("Characteristics (CHAR)","'1/2-13 UNC' = the SIZE parameter for Tier 2.5 parametric 3D (matches ref_hardware)",ACC),
       ("AAC (MDI&S)","fills the 104th's AAC FEDLOG block",AMB),
       ("Substitutes (MDI&S)","real interchangeable NSNs → grounds look-alike / substitute warnings","#3a4d6e")]
x=40; cw=268; gap=10; y=404
for h,d,acc in cells:
    P.append(box(x,y,cw,96,PANEL,LINE,11))
    P.append(f'<rect x="{x}" y="{y}" width="5" height="96" rx="2" fill="{acc}"/>')
    P.append(t(x+16,y+24,h,11,TXT,700)); s,_=wrap(x+16,y+44,d,38,9.2,SUB,13); P.append(s)
    x+=cw+gap
# honesty
P.append(box(40,516,1100,118,PANEL,AMB,12,1))
P.append(t(58,540,"SCOPE OF THIS POC (honest)",12,AMB,700))
s,_=wrap(58,562,"The ingest + schema + UI are proven on synthetic PUB-LOG-shaped rows against real in-index NSNs. The actual fill needs you to do the one-time PUB LOG download + Batch/SQL export on a connected machine (the ~GB .ZIP and the IMD product format aren't fetched here). Column-name variants are handled; if your export uses different headers we map them in minutes. Everything append-only & cited (R6); the engine never goes online.",174,9.6,SUB,13); P.append(s)
P.append(t(40,H-12,"Built & verified. Dark (R3) · CHANGELOG 0.22.0 (R4) · visual panel (R5) · sourcing in docs/REFERENCE-SOURCING.md.",9.2,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/34-publog-poc-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
