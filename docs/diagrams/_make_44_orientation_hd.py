#!/usr/bin/env python3
"""BUILT 0.30.0: dual-axis tilt + mirror with readable labels + on-demand HD (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,720
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"
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
P.append(t(40,46,"BUILT — Schematic orientation + HD  (v0.30.0)",20,TXT,700))
P.append(t(40,70,"Tilt on BOTH axes, a mirror for working from the opposite side with labels re-drawn readable (text pages), and on-demand HD that renders from the lossless source. All presentation-only; the page data is never altered.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# left: tilt axes demo
P.append(t(56,116,"1 · DUAL-AXIS TILT (honest flat-sheet)",12,ACC,700))
P.append(box(40,126,360,250,PANEL,LINE,12))
P.append('<g transform="translate(150,200)">')
P.append('<g transform="matrix(0.92,0.14,-0.18,0.86,0,0)">')
P.append(box(-90,-70,180,140,"#11161d","#3a4452",4))
for i in range(5): P.append(f'<line x1="-74" y1="{-50+i*26}" x2="74" y2="{-50+i*26}" stroke="#46505f" stroke-width="1"/>')
P.append('</g></g>')
P.append(t(150,300,"rotateY (tilt Y) + rotateX (tilt X)",9.5,AMB,400,"middle"))
P.append(t(150,318,"-60 deg .. +60 deg each",9,SUB,400,"middle"))
P.append(t(150,348,"CSS perspective — not reconstructed depth",8.6,GRN,400,"middle"))

# middle: mirror + labels
P.append(t(420,116,"2 · MIRROR + READABLE LABELS",12,ACC,700))
P.append(box(404,126,360,250,PANEL,LINE,12))
# normal vs mirrored chip
P.append(box(424,150,150,90,"#0a0e12",LINE,6)); P.append(t(499,170,"BOLT",11,"#dfe6ee",700,"middle")); P.append(t(499,200,"FIG 14",9,SUB,400,"middle")); P.append(t(434,236,"normal",8.4,SUB,400))
P.append(box(594,150,150,90,"#0a0e12",AMB,6))
# mirrored drawing (reversed) with a readable label chip over it
P.append('<g transform="translate(669,195) scale(-1,1)">')
P.append(t(0,-22,"TLOB",11,"#5a6675",700,"middle"))
P.append('</g>')
P.append(f'<rect x="636" y="164" width="66" height="18" rx="3" fill="rgba(255,255,255,.92)"/>'); P.append(t(669,178,"BOLT",10.5,"#0a0e12",700,"middle"))
P.append(t(604,236,"mirrored — label re-drawn readable",8.4,AMB,400))
s,_=wrap(424,262,"The drawing flips (scaleX -1) so you can orient from the opposite side. On pages with a text layer, each word box (from PyMuPDF, /api/pagewords) is re-drawn un-mirrored at its mirrored position so labels stay readable.",58,9,SUB,12); P.append(s)
s,_=wrap(424,340,"Honest: a mirror is an orientation aid, NOT a true rear view (that needs a different figure). Image-only pages show no overlay until OCR provides boxes.",58,8.8,GRN,12); P.append(s)

# right: HD
P.append(t(784,116,"3 · ON-DEMAND HD",12,ACC,700))
P.append(box(768,126,372,250,PANEL,LINE,12))
P.append(box(788,150,150,80,"#0a0e12",LINE,6)); P.append(t(863,186,"default",9,SUB,400,"middle")); P.append(t(863,202,"~150 dpi",8.4,SUB,400,"middle"))
P.append(t(948,196,"→",16,ACC,700,"middle"))
P.append(box(972,150,150,80,"#0a0e12",GRN,6)); P.append(t(1047,182,"✦ HD",10,"#bfe6cf",700,"middle")); P.append(t(1047,200,"up to 400 dpi",8.6,"#8fbf9f",400,"middle")); P.append(t(1047,216,"full page",8.2,"#8fbf9f",400,"middle"))
s,_=wrap(788,256,"HD re-renders the page from the lossless source PDF at high resolution on demand — full fidelity, no pre-baked duplicates (which would explode storage on the 85GB corpus with no quality gain). The loupe already goes to 700 dpi on the region under the cursor.",60,9,SUB,12); P.append(s)
s,_=wrap(788,344,"Every file keeps its highest fidelity: we render from source, never from a downscaled copy.",60,8.8,GRN,12); P.append(s)

# bottom invariants
P.append(box(40,400,1100,108,PANEL,GRN,12,1))
P.append(t(58,424,"INVARIANTS (R1 · R6)",12,GRN,700))
s,_=wrap(58,446,"All four controls (tilt X, tilt Y, mirror, HD) are presentation-only and reversible: the page bytes, the index, FTS search, and 104th sheet generation are untouched. Mirror labels are read-only overlays from the PDF text layer; HD changes only render resolution. Nothing is invented — tilt is a flat-sheet rotation, the mirror is a flip, HD is a higher-DPI render of the same source.",178,9.6,SUB,13); P.append(s)
P.append(box(40,520,1100,150,PANEL,LINE,12))
P.append(t(58,544,"NEW / CHANGED",12,AMB,700))
for i,(a,b) in enumerate([("Toolbar: tilt Y + tilt X sliders","each -60..+60 deg, CSS perspective"),
     ("Toolbar: ↔ Mirror","flip + readable label overlay (text pages)"),
     ("Toolbar: ✦ HD","full-page render up to 400 dpi from source"),
     ("Server: /api/pagewords","normalized word boxes from PyMuPDF (OCR-gated)"),
     ("Server: /page full-page cap 300 -> 400","HD headroom; clip loupe still 700")]):
    y=566+i*20; P.append(t(58,y,"• "+a,9.6,TXT,700)); s,_=wrap(420,y,b,86,9.2,SUB,12); P.append(s)
P.append(t(40,H-10,"BUILT diagram. Dark (R3). v0.30.0 · 2026-06-02.",9.2,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/44-orientation-hd-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1180)
print("wrote", os.path.getsize(base+".pdf"), "bytes ->", base+".pdf")
