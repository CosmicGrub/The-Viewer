#!/usr/bin/env python3
"""Proposal markup: layouts/presets behind a Settings button, decoupled from the core (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,860
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def arrow(x1,y1,x2,y2,col="#9aa5b1",wd=1.8): return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="{wd}" fill="none" marker-end="url(#a)"/>'
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
P.append(t(40,46,"Switchable layouts behind a Settings button — proposal",22,TXT,700))
P.append(t(40,70,"Consolidate today's scattered toggles into one Settings panel + named presets. Presentation only — the dataset, search, and the 104th flow never change.",11.5,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# DECOUPLING BOUNDARY
P.append(box(40,104,540,150,PANEL,"#3a4d6e",12))
P.append(t(58,128,"PRESENTATION LAYER  ·  what a layout changes",12,ACC,700))
for i,(a) in enumerate(["Text size · density/compact · spacing","Simple ↔ Advanced fields · which chrome shows","Default match (All/Any) · viewer defaults","= CSS classes on <body> + a saved preference"]):
    P.append(t(60,154+i*22,"• "+a,10,SUB if i<3 else AMB,400 if i<3 else 700))
P.append(box(600,104,540,150,PANEL,GRN,12))
P.append(t(618,128,"INVARIANT CORE  ·  never changes with layout",12,GRN,700))
for i,(a) in enumerate(["The dataset / index (server-side)","Search (FTS5, NSN, Last-4, synonyms, ranking)","End-to-end: modal → cart → tech gate → 104th PDF","= server endpoints; identical for every layout"]):
    P.append(t(620,154+i*22,"• "+a,10,SUB if i<3 else GRN,400 if i<3 else 700))
P.append(arrow(580,179,600,179,"#9aa5b1"))
P.append(t(590,150,"settings only style the UI →",9,"#7c8696",400,"middle"))
P.append(t(590,205,"✗ never cross into data / search / request",9,RED,700,"middle"))

# SETTINGS PANEL MOCKUP (left)
sx,sw=40,540; sy=276
P.append(box(sx,sy,sw,300,PANEL,LINE,12))
P.append(t(sx+18,sy+28,"⚙  Settings",14,TXT,700))
P.append(t(sx+18,sy+50,"One place for everything that's a header button today.",9.5,SUB,400))
# preset selector
P.append(t(sx+18,sy+78,"LAYOUT PRESET",9,AMB,700))
P.append(box(sx+18,sy+86,sw-36,34,P2,ACC,8)); P.append(t(sx+32,sy+108,"Shop floor / Touch",12,TXT,700)); P.append(t(sx+sw-32,sy+108,"▾",12,SUB,400,"end"))
# grouped toggles
rows=[("Text size","Normal · Large · X-Large"),("Density","Comfortable · Compact"),
      ("Fields","Simple · Advanced"),("Search match","All words · Any word"),
      ("Viewer","Thumbnails / highlight defaults")]
yy=sy+132
for lbl,opt in rows:
    P.append(t(sx+18,yy,lbl,10.5,TXT,700)); P.append(t(sx+sw-18,yy,opt,9.5,SUB,400,"end"))
    P.append(f'<line x1="{sx+18}" y1="{yy+8}" x2="{sx+sw-18}" y2="{yy+8}" stroke="{LINE}"/>')
    yy+=27
P.append(box(sx+18,sy+270,150,24,"none",LINE,7)); P.append(t(sx+93,sy+287,"Reset to default",9.5,SUB,600,"middle"))
P.append(t(sx+sw-18,sy+287,"saved on this device",9,"#7c8696",400,"end"))

# PRESETS (right)
px=600
P.append(t(px,sy+2,"NAMED PRESETS  ·  each bundles the settings at left",12,AMB,700))
presets=[("Simple / Junior","Large text · simple fields · minimal chrome — fast for new mechanics.","#1e3a26"),
         ("Advanced / SME","All fields · compact density · every facet — max info for experts.","#1a2740"),
         ("Shop floor / Touch","X-large text · big tap targets · high contrast — phone/tablet at the vehicle.","#3a2f1a"),
         ("Compact / Desktop","Dense · small text · keyboard-first — most on screen at once.","#243042")]
yy=sy+16
for h,d,col in presets:
    P.append(box(px,yy,540,62,col,LINE,10))
    P.append(t(px+16,yy+24,h,12,TXT,700))
    s,_=wrap(px+16,yy+42,d,72,9.4,SUB,13); P.append(s)
    yy+=70

# GUARANTEE + REC
gy=596
P.append(box(40,gy,1100,110,PANEL,LINE,12))
P.append(t(58,gy+26,"WHY IT CAN'T BREAK THE PROGRAM",12,GRN,700))
s,_=wrap(58,gy+48,"Layout state is CSS classes + a saved preference; it never alters the request payload, the search calls, or the dataset. Unknown/missing settings fall back to the default layout, and Reset-to-default is always one click — so a bad custom layout can't strand you (backwards-compatible & rollbackable, R1). The end-to-end process runs identically under every preset.",165,9.8,SUB,14); P.append(s)
P.append(t(40,gy+128,"RECOMMENDATION:",11,ACC,700))
s,_=wrap(195,gy+128,"Add a ⚙ Settings panel that absorbs the existing header toggles, plus the four presets above and a Reset. Persist per device. Verify each preset still passes the core flow (search → view → add → generate sheet).",150,10,SUB,15); P.append(s)
P.append(t(40,H-14,"Proposal only — nothing built yet. Dark (R3). On approval: data-flow diagram (R2), CHANGELOG (R4) + visual panel (R5).",10,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/25-layouts-settings-proposal"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
