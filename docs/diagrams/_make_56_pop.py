#!/usr/bin/env python3
"""BUILT 0.40.0: WebGL 3D (glossy/turntable/smooth) + schematics pan/zoom/blueprint (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,640
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; TEAL="#1d9e75"
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
P.append(t(40,46,"BUILT — Making it POP: real-time WebGL 3D + dynamic schematics  (v0.40.0)",20,TXT,700))
P.append(t(40,70,"On the current RTX 4050, fully offline (no Three.js / no CDN). Grounded: same geometry & pages, just rendered & navigated dynamically.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

P.append(t(56,116,"3D VIEWER — engine/ui/gl3d.js (dependency-free WebGL)",12,ACC,700))
P.append(box(40,126,545,300,PANEL,LINE,12))
for i,(h,d) in enumerate([
 ("Real-time WebGL render","A tiny self-written GL renderer (no library) draws the FLIS-scaled shapes lit in 3D — replaces the flat SVG. Offline + RPS-safe (SVG fallback if WebGL is missing)."),
 ("Glossy multi-light shading","Key + fill + rim/fresnel lights, sharp specular, soft tonemap — a metallic 'product render' look that pops."),
 ("Antialiasing + smooth surfaces","MSAA on; round families (cyl/hex/disc) use averaged normals so cylinders look round, boxes stay crisp."),
 ("Idle turntable","Auto-spins gently; grab to orbit (pauses), release and it resumes after a beat — dynamic by default."),
 ("Orbit · zoom · reset","Drag to orbit, scroll to zoom, double-click / ⟲ to reset. Wired into the 3D Library; the cart viewer adopts it next."),
]):
    P.append(t(58,150+i*55,"• "+h,10.2,TXT,700)); s,_=wrap(70,166+i*55,d,80,8.8,SUB,12); P.append(s)
P.append(t(58,418,"Grounded: representative shapes from real dimensions — better rendering, nothing invented.",8.8,GRN,400))

P.append(t(620,116,"SCHEMATICS VIEWER — dynamic navigation",12,ACC,700))
P.append(box(604,126,536,300,PANEL,LINE,12))
for i,(h,d) in enumerate([
 ("Buttery pan + cursor zoom","Drag to pan; scroll zooms toward the point under the cursor (transform-origin follows the pointer). Smooth, no reload — pure transform."),
 ("Blueprint mode","One tap flips a page to white-lines-on-blue (invert + hue) — classic schematic look, instant 'pop'."),
 ("Clean (legibility)","Server-side grayscale + contrast + de-speckle on the real page; toggles live."),
 ("Fade page transitions","Pages cross-fade in (pre-loaded) instead of blanking — feels fluid."),
 ("Reset · arrow-key paging","⟲ resets zoom+pan; ←/→ page through; double-click resets. All on the real rendered pages."),
]):
    P.append(t(622,150+i*55,"• "+h,10.2,TXT,700)); s,_=wrap(634,166+i*55,d,80,8.8,SUB,12); P.append(s)
P.append(t(622,418,"Grounded: it's the real PDF page — rendered, themed, and navigated, never altered.",8.8,GRN,400))

P.append(box(40,442,1100,158,PANEL,GRN,12,1))
P.append(t(58,466,"WHY IT STAYS HONEST + OFFLINE",12,GRN,700))
s,_=wrap(58,486,"All of this is presentation only (R1/R6): the dataset, search, and 104th sheet are untouched. The 3D is the same parametric geometry from real FLIS dimensions, just lit properly; the schematic is the same real page, just navigated and themed. No Three.js and no CDN — the WebGL renderer is ~120 lines we own, so the app stays fully offline and the SVG fallback keeps Win7/Vista (RPS) working.",182,9.4,SUB,13); P.append(s)
P.append(t(58,556,"Next envelope steps (per proposal 55): parametric template library (thread helix/gear teeth), schematic vectorisation + per-wire hover — both on the 4050. Photogrammetry + net-extraction await the desktop/RTX 5070 (reminder set).",9,SUB,400))
P.append(t(40,H-12,"BUILT diagram. Dark (R3). v0.40.0 · 2026-06-02 · new: engine/ui/gl3d.js + /gl3d.js route.",9.2,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/56-pop-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"), "bytes ->", base+".pdf")
