#!/usr/bin/env python3
"""PROPOSAL: pushing the envelope — deeper 3D + interactive schematics, now vs more-power (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,1000
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"; TEAL="#1d9e75"; PUR="#7f77dd"
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
P.append(t(40,46,"PROPOSAL — Pushing the envelope: deeper 3D + interactive schematics",20,TXT,700))
P.append(t(40,70,"What we can do NOW on the RTX 4050, what a stronger GPU (RTX 5070, 12 GB) unlocks, and the grounding line we never cross.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

def tier(x,y,w,h,title,col,items):
    P.append(box(x,y,w,h,PANEL,col,11,1)); P.append(f'<rect x="{x}" y="{y}" width="6" height="{h}" rx="3" fill="{col}"/>')
    P.append(t(x+18,y+20,title,11,col,700)); yy=y+38
    for hh,dd in items:
        P.append(t(x+18,yy,"• "+hh,9.6,TXT,700)); s,n=wrap(x+30,yy+13,dd,(w-46)//5,8.6,SUB,11); P.append(s); yy+=15+n*11
    return

# 3D column
P.append(t(56,116,"3D PARTS",14,TEAL,700))
tier(40,128,545,238,"NOW — on your RTX 4050 (grounded)",GRN,[
 ("Real-time WebGL (Three.js) viewer","Replace flat SVG with true lit 3D: PBR materials (metal/rough), soft shadows, smooth orbit, ambient occlusion. Same geometry, far more recognisable."),
 ("Parametric TEMPLATE library","Beyond 4 primitives: real hex bolt (head+chamfer+thread helix), bearing races, gear teeth from FLIS tooth-count, flanges, multi-hole brackets — driven by real characteristics."),
 ("Section · measure · exploded assemblies","Clipping-plane cross-sections, click-measure, and exploded RPSTL assemblies (figure -> its NSNs arranged in 3D). STL export for reference."),
])
tier(40,374,545,150,"MORE POWER — RTX 5070 12 GB",AMB,[
 ("Photogrammetry / Gaussian-splatting from REAL photos","Mechanic photographs the actual part; build a TRUE rotatable 3D capture (COLMAP + gsplat/NeRF, offline). VRAM-bound — 6 GB is tight; 12 GB trains faster + higher-res. THIS is the upgrade's headline."),
 ("AI image->mesh (TripoSR / InstantMesh)","One photo -> a mesh in seconds. Fast on GPU, but see the grounding line."),
])

# Schematics column
P.append(t(620,116,"SCHEMATICS",14,TEAL,700))
tier(604,128,536,238,"NOW — on your RTX 4050 (grounded)",GRN,[
 ("Vectorise raster -> SVG line art","Trace each schematic to clean vectors: infinite-zoom crispness, per-wire hover/highlight, recolour. The same drawing, made interactive."),
 ("Full-text search INSIDE diagrams","Once OCR completes, find every sheet containing 'fuel pump relay' or a connector ID; jump straight to it."),
 ("Callout -> part hotspots","Hover a component/figure number -> highlight it and open the NSN (ties to the parts index; OCR-box gated)."),
 ("Cross-sheet / off-page links","Click an off-page connector to jump to its continuation sheet; link a connector to its pinout table + the 3D part."),
])
tier(604,374,536,150,"MORE POWER — RTX 5070 12 GB",AMB,[
 ("Net / circuit EXTRACTION (the big one)","Vision models detect components + wires + labels -> a netlist. Click a wire and the WHOLE circuit lights up across sheets; 'where does J12-7 go?'. Vision-heavy -> more cores/VRAM = faster build + inference over all 1,093 schematics."),
 ("Symbol recognition + local 'explain this circuit' VLM","Identify standard symbols; a small offline vision-language model explains a circuit — grounded to the EXTRACTED netlist, not free invention. 12 GB opens usable VLMs (6 GB can't)."),
])

# grounding line
P.append(box(40,540,1100,96,PANEL,RED,12,1))
P.append(t(58,564,"THE GROUNDING LINE (never crossed — it's the whole point of this tool)",12,RED,700))
s,_=wrap(58,584,"GROUNDED (build freely): WebGL rendering, parametric templates, photogrammetry/splats from REAL photos, multi-view reconstruction from REAL drawings, schematic vectorisation + net extraction, OCR search/hotspots — all from real data. FLAGGED (aids only, clearly labelled, never authoritative): single-image AI 3D and AI super-resolution INVENT the hidden sides / unseen strokes. We can offer them as a quick visual aid with a bold 'AI-inferred, not verified' badge — but the 104th sheet and any decision stays on cited, real geometry.",184,9.4,SUB,13); P.append(s)

# hardware strip
P.append(box(40,650,1100,150,PANEL,LINE,12))
P.append(t(58,674,"HARDWARE — would the RTX 5070 help?",12,ACC,700))
P.append(box(60,690,300,96,P2,LINE,8)); P.append(t(80,712,"RTX 4050 (you have)",10,TXT,700));
for i,d in enumerate(["2,560 CUDA · 6 GB GDDR6","great: OCR, WebGL 3D, vectorise,","templates, OCR-search, hotspots"]):
    P.append(t(80,730+i*16,d,8.8,SUB,400))
P.append(t(378,740,"→",18,ACC,700,"middle"))
P.append(box(400,690,360,96,"#13241c",GRN,8)); P.append(t(420,712,"RTX 5070 12 GB (Blackwell)",10,"#bfe6cf",700))
for i,d in enumerate(["4,608 CUDA · 12 GB GDDR7 · ~798 AI TOPS","unlocks: photogrammetry/Gaussian-splat,","net-extraction vision models, local VLM,","faster batch over all schematics"]):
    P.append(t(420,730+i*15,d,8.6,"#8fbf9f",400))
s,_=wrap(778,712,"Verdict: the 4050 covers the whole 'NOW' column (most of the value). The 5070's 12 GB is worth it specifically for photo->true-3D capture and schematic net-extraction at scale — VRAM is the real limiter, not raw speed.",60,9,SUB,12); P.append(s)

# recommendation
P.append(box(40,814,1100,150,PANEL,GRN,12,1))
P.append(t(58,838,"MY RECOMMENDED ORDER (high value, all grounded, all on the 4050 first)",12,GRN,700))
recs=["1.  WebGL/Three.js real-3D viewer — biggest visual leap, runs now, makes parts instantly recognisable.",
      "2.  Schematic vectorisation + per-wire hover — turns flat scans into interactive line art.",
      "3.  Parametric template library — richer, more accurate shapes from the FLIS fields we already hold.",
      "4.  (as OCR finishes) full-text schematic search + callout->part hotspots.",
      "5.  THEN, if you get the 5070: photo->true-3D capture and schematic net/circuit extraction."]
for i,r in enumerate(recs): P.append(t(58,860+i*19,r,9.6,SUB,400))
P.append(t(40,H-12,"PROPOSAL — your call on order + whether to plan for the 5070. Dark (R3). Nothing built yet.",9.2,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/55-envelope-proposal"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1180)
print("wrote", os.path.getsize(base+".pdf"), "bytes ->", base+".pdf")
