#!/usr/bin/env python3
"""BUILT 0.27.0: schematic legibility viewer — clean+contrast, tilt, loupe (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,760
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"
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
P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
P.append('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9aa5b1"/></marker></defs>')
P.append(box(0,0,W,H,BG,BG,0))
P.append(t(40,46,"BUILT — Schematic legibility viewer  (v0.27.0)",21,TXT,700))
P.append(t(40,70,"Same drawing, made readable: a 'Clean' toggle + contrast (server-side, PyMuPDF→Pillow), a 3D tilt of the flat page, and a hover loupe. Nothing invented; cited to its page.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# Left: toolbar markup
P.append(t(56,116,"VIEWER TOOLBAR (new controls)",12,ACC,700))
P.append(box(40,126,540,330,PANEL,LINE,12))
P.append(box(56,140,508,28,P2,LINE,6))
for i,(lab,col) in enumerate([("🧹 Clean",GRN),("contrast ▮▮▮",SUB),("tilt ◣",AMB),("🔎 Loupe",ACC)]):
    P.append(t(70+i*128,158,lab,9.4,col,700))
# stage with schematic + loupe + tilt hint
sx,sy,sw,sh=56,180,508,262
P.append(box(sx,sy,sw,sh,"#0a0e12",LINE,8))
# tilted page group
P.append(f'<g transform="translate({sx+70},{sy+30}) skewY(-6)">')
P.append(box(0,0,300,200,"#11161d","#3a4452",4))
for i in range(6):
    P.append(f'<line x1="20" y1="{24+i*30}" x2="280" y2="{24+i*30}" stroke="#46505f" stroke-width="1.1"/>')
for i in range(7):
    P.append(f'<line x1="{28+i*40}" y1="18" x2="{28+i*40}" y2="186" stroke="#46505f" stroke-width="0.9"/>')
P.append('</g>')
P.append(t(sx+70,sy+250,"flat page, tilted in 3D (perspective rotateY)",8.6,AMB,400))
# loupe
P.append(f'<circle cx="{sx+400}" cy="{sy+78}" r="34" fill="#0a0e12" stroke="{ACC}" stroke-width="1.8"/>')
for i in range(4): P.append(f'<line x1="{sx+372}" y1="{sy+62+i*10}" x2="{sx+428}" y2="{sy+62+i*10}" stroke="#5a6675" stroke-width="1.3"/>')
P.append(t(sx+400,sy+82,"2.6×",10,ACC,700,"middle"))
P.append(t(sx+400,sy+128,"loupe follows cursor",8.6,ACC,400,"middle"))

# Right: data flow
P.append(t(606,116,"REQUEST FLOW  (offline, same dataset)",12,ACC,700))
steps=[("Click 🧹 Clean / move contrast","UI sets VP.clean + VP.contrast, reloads page image"),
       ("GET /page?...&clean=1&contrast=N","server renders the real page hi-DPI (PyMuPDF)"),
       ("_clean_png(): grayscale → autocontrast","→ de-speckle (median) → unsharp → optional contrast/binarize (Pillow)"),
       ("Crisp PNG returned & shown","tilt = CSS perspective rotateY on the <img> (no re-fetch)"),
       ("🔎 Loupe = client-side magnifier","background-zoom of the same PNG under the cursor")]
y=132
for i,(h,d) in enumerate(steps):
    P.append(box(606,y,534,52,P2,LINE,8)); P.append(t(620,y+21,str(i+1)+" · "+h,10.4,TXT,700)); s,_=wrap(620,y+37,d,92,8.8,SUB,11); P.append(s)
    if i<len(steps)-1: P.append(arrow(873,y+52,873,y+58,ACC))
    y+=58

# bottom: invariants / grounding
P.append(box(40,478,1100,96,PANEL,GRN,12,1))
P.append(t(58,502,"INVARIANTS & GROUNDING (R1 · R6)",12,GRN,700))
s,_=wrap(58,522,"Pure enhancement of the real page — contrast, sharpen, de-speckle, optional high-contrast/binarize — plus a flat-sheet 3D tilt and a magnifier. No strokes, depth, or detail are fabricated. Off by default: the dataset, FTS search, and the 104th sheet are untouched; toggles are presentation-only and reversible. Cleanup runs server-side via Pillow (auto-installed by run_app.bat); loupe + tilt are client-side CSS.",170,9.6,SUB,13); P.append(s)
P.append(box(40,584,1100,150,PANEL,LINE,12))
P.append(t(58,608,"WHAT'S NEXT (proposed, not yet built)",12,AMB,700))
nxt=[("Deep-zoom tiles (B)","OpenSeadragon tile pyramid for buttery zoom/pan to any portion — larger build."),
     ("Spotlight / box-highlight (C)","drag a region to dim everything outside it — pairs with the loupe."),
     ("Callout hotspots → parts (D)","hover a FIG number to highlight + open the NSN — OCR-box gated, grows as OCR completes."),
     ("Vectorize line art (E)","trace clean schematics to SVG for infinite-zoom crispness — optional, high effort.")]
y=624
for h,d in nxt:
    P.append(t(58,y,"• "+h,10,TXT,700)); s,_=wrap(330,y,d,108,9.2,SUB,12); P.append(s); y+=26
P.append(t(40,H-10,"BUILT diagram — companion to proposal 40. Dark (R3). v0.27.0 · 2026-06-02.",9.4,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/41-schematic-viewer-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"),"bytes ->", base+".pdf")
