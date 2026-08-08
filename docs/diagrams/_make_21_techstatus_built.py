#!/usr/bin/env python3
"""Built: tech-status derivation + mandatory gate (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,720
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
P.append(t(40,46,"Tech Status — derived from fault + part, confirmed before the sheet — built",21,TXT,700))
P.append(t(40,70,"v0.17.0 · PMCS 'Not Fully Mission Capable If' (cited) + prior history · mandatory confirm gate · full codes. Additive (R1).",11.5,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# LEFT: gate mockup
gx,gw=40,560; gy=104
P.append(box(gx,gy,gw,560,PANEL,LINE,12))
P.append(t(gx+20,gy+30,"Confirm equipment status",15,TXT,700))
P.append(box(gx+250,gy+16,70,24,"#5a2330",LINE,6)); P.append(t(gx+285,gy+33,"NMCS",12,"#f2b8b8",700,"middle"))
s,_=wrap(gx+20,gy+52,"The fault matches a PMCS 'Not Fully Mission Capable If' criterion — a deadlining fault. Parts are on order, so supply (NMCS) is suggested. Review the cited criteria and confirm.",84,9.6,SUB); P.append(s)
# evidence
ey=gy+96
P.append(box(gx+18,ey,gw-36,150,"#141a23",LINE,9))
P.append(t(gx+30,ey+20,"CITED PMCS CRITERIA — 'NOT FULLY MISSION CAPABLE IF'",8.5,AMB,700))
P.append(box(gx+30,ey+30,gw-60,52,P2,LINE,7))
P.append(t(gx+40,ey+48,"📄 TM 9-2320-327-10 · p.298 — open",10,ACC,700))
s,_=wrap(gx+40,ey+64,"…NOT FULLY MISSION CAPABLE IF: Steering hard to turn, steering wheel turns but vehicle doesn't react, reaction is slow, steering wheel will not turn…",80,8.8,SUB,12); P.append(s)
P.append(box(gx+30,ey+90,gw-60,46,P2,LINE,7))
P.append(t(gx+40,ey+108,"📄 TM 9-2320-327-10 · p.292 — open",10,ACC,700))
s,_=wrap(gx+40,ey+124,"…NOT FULLY MISSION CAPABLE IF PROCEDURE … steering …",80,8.8,SUB,12); P.append(s)
# dropdown
dy=ey+166
P.append(t(gx+20,dy,"TECH STATUS — required to generate the sheet *",10,TXT,700))
P.append(box(gx+20,dy+10,gw-40,40,P2,ACC,8))
P.append(t(gx+34,dy+35,"NMCS",13,TXT,700)); P.append(t(gx+gw-54,dy+35,"▾",13,SUB,400))
s,_=wrap(gx+20,dy+70,"FMC fully mission capable · PMCM/PMCS partially (maint/supply) · NMCM/NMCS non-mission-capable (maint/supply). You confirm — the app never decides readiness on its own.",84,8.8,SUB,12); P.append(s)
# buttons
by=dy+108
P.append(box(gx+gw-360,by,150,36,"none",LINE,8)); P.append(t(gx+gw-285,by+23,"Cancel",12,SUB,600,"middle"))
P.append(box(gx+gw-196,by,176,36,GRN,GRN,8)); P.append(t(gx+gw-108,by+23,"Confirm & generate sheet",11.5,"#eafff0",700,"middle"))

# RIGHT: data flow
rx,rw=636,504; ry=104
P.append(box(rx,ry,rw,560,PANEL,LINE,12))
P.append(f'<rect x="{rx}" y="{ry}" width="{rw}" height="30" rx="12" fill="{P2}" stroke="{LINE}"/>')
P.append(t(rx+14,ry+20,"DATA FLOW",12,ACC,700))
steps=[
 ("Export clicked","derive vehicle from cart items + the fault text",P2),
 ("GET /api/techstatus","vehicle · fault · parts",P2),
 ("A · PMCS criteria (authoritative)","FTS over the vehicle's pages: ('not fully mission capable' OR 'mission capable') AND fault-terms → cite the matched line",("#16301f")),
 ("B · prior history","sessions+faults: status confirmed for similar faults before",("#1a2740")),
 ("Suggest + evidence","NMCS (deadline) · or history · or none → manual",P2),
 ("MANDATORY confirm gate","mechanic accepts/overrides; cannot proceed while blank",("#3a2f1a")),
 ("POST /api/request","server also rejects a blank tech status (belt + suspenders)",P2),
 ("104th PDF · TECH STATUS filled","always present, human-confirmed, cited basis",("#16301f")),
]
yy=ry+44
for i,(h,d,col) in enumerate(steps):
    bh=52
    P.append(box(rx+18,yy,rw-36,bh,col,LINE,8))
    P.append(t(rx+30,yy+21,h,11,TXT,700))
    s,_=wrap(rx+30,yy+37,d,74,9,SUB,12); P.append(s)
    if i<len(steps)-1: P.append(arrow(rx+rw/2,yy+bh,rx+rw/2,yy+bh+10,AMB if i in(4,) else "#9aa5b1"))
    yy+=bh+10
P.append(t(40,H-12,"Verified on the live index: Buffalo steering/headlight faults → cited NMCS criteria; cosmetic faults → no auto-suggestion (manual). Dark (R3) · CHANGELOG 0.17.0 (R4) · visual panel (R5).",9.6,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/21-tech-status-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1180)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
