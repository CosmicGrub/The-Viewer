#!/usr/bin/env python3
"""Proposal: interactive + legible schematics — markup, pipeline, options (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,1090
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def arrow(x1,y1,x2,y2,col="#9aa5b1"): return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="1.6" fill="none" marker-end="url(#a)"/>'
def ln(x1,y1,x2,y2,col="#6b7280"): return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="1" stroke-dasharray="3 3" fill="none"/>'
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
P.append(t(40,46,"Readable, interactive schematics — options & how it works",21,TXT,700))
P.append(t(40,70,"It's the SAME drawing — enhanced for legibility (contrast/sharpen/de-speckle), deep-zoomable, with hover/highlight. No content invented; everything cited to its page.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
# markup (left)
P.append(t(56,116,"THE VIEWER (marked up)",12,ACC,700))
P.append(box(40,126,520,300,PANEL,LINE,12))
# toolbar
P.append(box(56,140,488,26,P2,LINE,6))
for i,lab in enumerate(["▣ zoom","⟲ fit","◧ clean: on","contrast","◎ loupe","▭ highlight"]):
    P.append(t(66+i*82,157,lab,8.6,SUB,400))
# stage
sx,sy,sw,sh=56,176,488,234
P.append(box(sx,sy,sw,sh,"#0a0e12",LINE,8))
# fake schematic lines
for i in range(5):
    yy=sy+30+i*36
    P.append(f'<line x1="{sx+24}" y1="{yy}" x2="{sx+sw-24}" y2="{yy}" stroke="#3a4452" stroke-width="1.2"/>')
for i in range(7):
    xx=sx+40+i*64
    P.append(f'<line x1="{xx}" y1="{sy+24}" x2="{xx}" y2="{sy+sh-24}" stroke="#3a4452" stroke-width="1"/>')
# callout dots
for cx0,cy0,nbr in [(sx+120,sy+66,"3"),(sx+250,sy+138,"7"),(sx+360,sy+210,"12")]:
    P.append(f'<circle cx="{cx0}" cy="{cy0}" r="9" fill="#16223a" stroke="#4f9dff"/>'); P.append(t(cx0,cy0+3,nbr,8.5,"#bcd4ff",700,"middle"))
# spotlight box
P.append(f'<rect x="{sx+200}" y="{sy+100}" width="120" height="74" fill="none" stroke="#caa24a" stroke-width="1.6" stroke-dasharray="4 3"/>')
# loupe
P.append(f'<circle cx="{sx+400}" cy="{sy+70}" r="26" fill="#0a0e12" stroke="#4f9dff" stroke-width="1.6"/>'); P.append(t(sx+400,sy+74,"+",13,ACC,700,"middle"))
# callouts
P.append(ln(sx+sw,sy+30,600,150)); P.append(t(606,150,"① deep zoom / pan to any portion",9.5,GRN,700))
P.append(ln(sx+360,sy+210,600,186)); P.append(t(606,186,"② callout numbers hover → highlight + open the part",9.5,ACC,700))
P.append(ln(sx+260,sy+137,600,222)); P.append(t(606,222,"③ spotlight / box-highlight a section",9.5,AMB,700))
P.append(ln(sx+400,sy+70,600,258)); P.append(t(606,258,"④ magnifier loupe on hover",9.5,ACC,700))
P.append(ln(sx+250,sy+150,600,294)); P.append(t(606,294,"⑤ 'clean' toggle + contrast = legibility",9.5,GRN,700))
P.append(t(606,330,"Example (real page): see the before/after image shared with this.",9.5,SUB,400))

# pipeline (right)
P.append(t(606,360,"LEGIBILITY PIPELINE (offline, grounded)",12,ACC,700))
steps=[("Render page hi-DPI (PyMuPDF)","crisp raster of the real page"),
       ("Grayscale + auto-contrast","stretch faded scans"),
       ("Sharpen (unsharp) + de-speckle","crisper lines, less scan noise"),
       ("Optional: deskew · binarize · upscale","straighten · black-on-white · enlarge low-res"),
       ("Tile pyramid → deep-zoom viewer","OpenSeadragon: smooth zoom/pan + overlays")]
y=374
for i,(h,d) in enumerate(steps):
    P.append(box(606,y,534,46,P2,LINE,8)); P.append(t(620,y+19,str(i+1)+" · "+h,10.4,TXT,700)); s,_=wrap(620,y+34,d,84,8.6,SUB,11); P.append(s)
    if i<len(steps)-1: P.append(arrow(873,y+46,873,y+52,ACC))
    y+=52
# options ladder (bottom)
P.append(t(40,640,"OPTIONS  (grounded → richer)",12,AMB,700))
opts=[("A · Legibility cleanup","MINIMUM · NOW",GRN,"Contrast / sharpen / de-speckle / deskew + a 'clean' toggle and contrast slider. Proven on your scan (shared).","low effort · it's the real drawing, enhanced"),
      ("B · Deep zoom + pan","RESIZE/ZOOM",GRN,"Tile the page; OpenSeadragon for smooth zoom to any portion, fully offline.","low-med effort"),
      ("C · Hover loupe + box-highlight / spotlight","HOVER/HIGHLIGHT",ACC,"Magnifier that follows the cursor; drag to highlight a region or dim everything outside it.","med effort"),
      ("D · Callout hotspots → parts","SMART",AMB,"Hover/click a FIG callout number to highlight it and open the part (NSN/part#). Ties to the parts index; needs OCR boxes.","med effort · OCR-gated"),
      ("E · Vectorize the line art","CRISPEST",AMB,"Trace clean line drawings to SVG → infinite-zoom crispness + per-line hover/recolor. Best for clean schematics.","high effort")]
y=654
for h,tag,acc,d,meta in opts:
    bh=58
    P.append(box(40,y,1100,bh,PANEL,LINE,11))
    P.append(f'<rect x="40" y="{y}" width="6" height="{bh}" rx="3" fill="{acc}"/>')
    P.append(t(60,y+22,h,11.5,TXT,700))
    P.append(box(992,y+10,136,22,acc,LINE,6)); P.append(t(1060,y+25,tag,9,"#0f1419" if acc in(GRN,ACC,AMB) else TXT,700,"middle"))
    s,_=wrap(60,y+40,d,108,9.3,SUB,12); P.append(s)
    P.append(t(900,y+45,meta,8.6,("#8fae8f" if acc==GRN else ("#9bb3d6" if acc==ACC else "#cbb87a")),700))
    y+=bh+6
# grounding + rec
P.append(box(40,y+4,1100,84,PANEL,RED,12,1))
P.append(t(58,y+28,"GROUNDING + RECOMMENDATION",12,RED,700))
s,_=wrap(58,y+48,"Enhancement (contrast, sharpen, de-speckle, deskew, interpolated upscale) is legitimate — it's the same drawing, more legible, cited to its page. Avoid AI super-resolution / inpainting that fabricates strokes (it can invent detail). Recommended bundle: A (cleanup) + B (deep zoom) + C (loupe/highlight) now; D (callout→part) as OCR completes; E (vectorize) optional for the cleanest line schematics.",172,9.6,SUB,13); P.append(s)
P.append(t(40,H-12,"Proposal — your call. Companion to the interactive-schematic plan (diagrams 28/29). Dark (R3).",9.4,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/40-schematics-interactive"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
