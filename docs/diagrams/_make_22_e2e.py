#!/usr/bin/env python3
"""End-to-end process — current state (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,860
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def arrow(x1,y1,x2,y2,col="#9aa5b1",wd=1.7): return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="{wd}" fill="none" marker-end="url(#a)"/>'
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
P.append(t(40,46,"THE VIEWER — end-to-end process, current state",22,TXT,700))
P.append(t(40,70,"Onboarding → search → manual page → parts cart → tech-status gate → 104th sheet → learns. Everything anchors to the real manual; nothing invented.",11.5,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
# grounding legend
P.append(t(40,108,"GROUNDING:",10,SUB,700))
leg=[("your input","#2c3f5e"),("real manual page","#16301f"),("verbatim / cited","#3a2f1a"),("learned from logs","#1a2740")]
x=130
for lbl,col in leg:
    P.append(box(x,98,14,12,col,LINE,3)); P.append(t(x+20,108,lbl,9.5,SUB,400)); x+=len(lbl)*6.4+44
stages=[
 ("1 · Onboarding modal","Mirrors the 104th header (live preview). Bumper# + Fault required. Express 'what do you need?' field set apart.","#2c3f5e","your input"),
 ("2 · Entry","Exact NSN/part in express → jumps straight to the page/hub. Otherwise Home: commonly-requested (learned), browse-by-vehicle, recents, rotating example.","#1a2740","learned + your input"),
 ("3 · Search engine","Predictive FTS5 + synonyms + typo-tolerance + part#/FIG + All/Any · Last-4 NSN (cover) · full NSN (part/vehicle) · results you've requested float up.","#16301f","real index"),
 ("4 · Smart results","Filter by vehicle / manual-type / text-vs-OCR with counts; ★ requested badge. Cards link to the page or the vehicle hub.","#16301f","real index"),
 ("5 · Viewer  &  Vehicle hub","Real manual page (zoom · thumbnails · highlight-the-hit). 'Schematics & install' panel: cited figure → page → vehicle schematic set. Hub groups the whole manual set.","#3a2f1a","verbatim / cited"),
 ("6 · Parts cart (104th blocks)","Add a part → nomenclature auto-derived from the matched line; NSN/part#/FIG/QTY editable; FEDLOG row (manual). Simple/Advanced view.","#2c3f5e","page-derived + your input"),
 ("7 · Tech-status gate (mandatory)","Suggests status from the fault via PMCS 'Not Fully Mission Capable If' (cited) or prior history; you confirm. Sheet can't generate while blank.","#3a2f1a","verbatim / cited"),
 ("8 · Save + generate","sessions / faults / request_items written; the 104th ECC PDF is produced with the header + item blocks filled.","#16301f","your record"),
]
y=124; rh=78; gap=6
for i,(h,d,col,tag) in enumerate(stages):
    P.append(box(40,y,1100,rh,PANEL,LINE,11))
    P.append(f'<rect x="40" y="{y}" width="6" height="{rh}" rx="3" fill="{col}"/>')
    P.append(t(62,y+26,h,13,TXT,700))
    s,_=wrap(62,y+46,d,110,9.8,SUB,14); P.append(s)
    P.append(box(960,y+18,166,30,col,LINE,7)); P.append(t(1043,y+38,tag,9.5,TXT,600,"middle"))
    if i<len(stages)-1: P.append(arrow(90,y+rh,90,y+rh+gap+0.1,"#5d6675"))
    y+=rh+gap
# learning loop back 8 -> 2/3
P.append(arrow(1135,y-rh+34,1160,y-rh+34,"#3a4d6e"))
P.append(f'<path d="M1160,{y-rh+34} C1175,{y-rh+34} 1175,150 1150,150" stroke="#3a4d6e" stroke-width="1.6" fill="none" marker-end="url(#a)"/>')
P.append(t(1150,140,"learns",9,"#7c8696",400,"end"))
P.append(t(40,H-14,"The one quality lever: OCR coverage. Text-layer manuals are fully searchable/citable now; scanned pages sharpen as OCR completes (search, schematics, and PMCS tech-status all benefit).",10,AMB,400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/22-end-to-end-current"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
