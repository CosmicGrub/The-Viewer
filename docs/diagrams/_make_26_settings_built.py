#!/usr/bin/env python3
"""Built: Settings panel + layout presets, decoupled from the core (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,640
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
P.append(t(40,46,"Settings & layout presets — built",22,TXT,700))
P.append(t(40,70,"v0.18.0 · ⚙ panel consolidates the toggles + 4 presets · per-device persist + Reset · presentation only. Client-only, no server/engine change (R1).",11.5,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
# panel mockup
sx,sw=40,500; sy=104
P.append(box(sx,sy,sw,470,PANEL,LINE,12))
P.append(t(sx+18,sy+28,"⚙  Settings & layout",14,TXT,700))
P.append(t(sx+18,sy+78-30,"LAYOUT PRESET",9,AMB,700))
P.append(box(sx+18,sy+56,sw-36,32,P2,ACC,8)); P.append(t(sx+32,sy+77,"Shop floor / Touch",12,TXT,700)); P.append(t(sx+sw-32,sy+77,"▾",12,SUB,400,"end"))
rows=[("Text size","X-Large"),("Density","Comfortable"),("Fields","Simple"),("Search match","All words"),("Viewer thumbnails","Off by default"),("Highlight search hit","On by default")]
yy=sy+112
for lbl,val in rows:
    P.append(t(sx+18,yy,lbl,11,TXT,700)); 
    P.append(box(sx+sw-210,yy-15,192,26,P2,LINE,6)); P.append(t(sx+sw-200,yy+3,val,10.5,SUB,400)); P.append(t(sx+sw-28,yy+3,"▾",10,SUB,400,"end"))
    yy+=42
P.append(box(sx+18,sy+430,150,26,"none",LINE,7)); P.append(t(sx+93,sy+447,"Reset to default",9.5,SUB,600,"middle"))
P.append(box(sx+sw-100,sy+430,82,26,GRN,GRN,7)); P.append(t(sx+sw-59,sy+447,"Done",10.5,"#eafff0",700,"middle"))
# flow right
rx=580
P.append(t(rx,sy+18,"WHAT HAPPENS WHEN YOU SWITCH",12,ACC,700))
fl=[("⚙ Settings (preset or fine-tune)","",P2),
    ("applySettings()","maps choices → body classes",P2),
    ("body.sz-xl · body.den-compact · body.simple · MATCH_ANY · viewer defaults","CSS + 2 JS vars — that's all a layout is","#101a14"),
    ("localStorage 'viewer_settings'","per device · legacy keys migrated · Reset restores default","#1a2740")]
yy=sy+34
for h,d,col in fl:
    bh=58
    P.append(box(rx,yy,560,bh,col,LINE,9))
    s,_=wrap(rx+14,yy+24,h,64,11,TXT,13,700); P.append(s)
    if d: P.append(t(rx+14,yy+44,d,9.4,SUB,400))
    yy+=bh+10
    if yy<sy+34+4*68: P.append(arrow(rx+280,yy-10,rx+280,yy,ACC))
# invariant core
P.append(box(rx,yy+6,560,96,PANEL,GRN,12,1))
P.append(t(rx+16,yy+30,"INVARIANT CORE — untouched",12,GRN,700))
s,_=wrap(rx+16,yy+50,"No change to /api/search, /api/request, the index, or the request payload. The end-to-end flow (modal → search → cart → tech gate → 104th PDF) runs identically. A startup self-check confirms the core controls exist after every layout apply.",76,9.6,SUB,14); P.append(s)
P.append(t(40,H-14,"Verified: presets flip CSS classes only; search + sheet generation unaffected; JS lint clean. Dark (R3) · CHANGELOG 0.18.0 (R4) · visual panel (R5).",9.6,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/26-settings-presets-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
