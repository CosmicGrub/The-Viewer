#!/usr/bin/env python3
"""Proposal: schematic -> interactive 3D, the honest feasibility spectrum (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,880
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def wrap(x,y,s,width,size,fill,dy=14,wt=400):
    out=[];words=s.split();line="";ln=0
    for wd in words:
        if len(line)+len(wd)+1>width: out.append(t(x,y+ln*dy,line,size,fill,wt));line=wd;ln+=1
        else: line=(line+" "+wd).strip()
    if line: out.append(t(x,y+ln*dy,line,size,fill,wt))
    return "".join(out),ln+1
P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
P.append(box(0,0,W,H,BG,BG,0))
P.append(t(40,46,"Schematic → interactive 3D: what's actually possible (and what isn't)",21,TXT,700))
P.append(t(40,70,"The honest core: a 2D line drawing has no depth data. Accurate 3D must come from real 3D sources — never invented from a scan. Five approaches, grounded → speculative.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
tiers=[
 ("1 · Interactive 2D — deep zoom + clickable callouts","RECOMMENDED · GROUNDED",GRN,
  "Tile-zoom the REAL scanned schematic (like a map); auto-place clickable hotspots on the FIG callout numbers (from OCR coordinates) that jump to the part row (NSN/part#). Pan, deep-zoom to fine detail on the authoritative drawing.",
  "Accuracy = the manual itself · Effort ~2–4 wks · Needs schematic OCR done","Delivers the real job: inspect fine features + identify the exact part. Not rotation, but honest."),
 ("2 · Multi-view switcher (where the TM has them)","GROUNDED, LIMITED",ACC,
  "Many TMs show front/side/section views. Stitch the views the manual already provides into a view switcher — several real angles, no invented geometry.",
  "Accuracy = real drawing views · Effort ~1–2 wks","Pseudo-3D from real art · only the angles the manual provides."),
 ("3 · True 3D from REAL CAD / 3D-TM assets","ACCURATE 3D — if files exist",AMB,
  "Render actual 3D models (glTF/STEP→glTF, IETM/S1000D or OEM CAD) in a rotatable viewer, linked to the parts index. Real rotation, zoom, pick-a-part.",
  "Accuracy = the CAD · Viewer ~2–3 wks · BLOCKER: sourcing the files (controlled/availability)","True rotation & feature zoom · depends on obtaining 3D data — an org/supply problem, not code."),
 ("4 · True 3D via photogrammetry of the real part","ACCURATE 3D — capture workflow",AMB,
  "Photograph the actual part (many angles) → reconstruct an accurate textured mesh (COLMAP/RealityCapture). Build a library over time, prioritising look-alike parts. Rotate any captured part, zoom to holes/ports/connectors.",
  "Accuracy = the real part · Pipeline ~3–5 wks + per-part capture labor","The genuine 'rotate & zoom to the tiny difference' experience · grows part-by-part."),
 ("5 · AI single-image → 3D from the scan","NOT RECOMMENDED",RED,
  "Neural image-to-3D would generate a plausible mesh from one drawing — but it INVENTS geometry (wrong hole count, wrong port). For parts ID where the tiny difference is the whole point, a confident-but-wrong model is dangerous.",
  "Accuracy = hallucinated · Fast to demo, wrong in practice","Breaks the project's never-invent rule. The exact failure mode you care about (holes/ports) is what it gets wrong."),
]
y=100
for h,tag,acc,d,meta,note in tiers:
    bh=140
    P.append(box(40,y,1100,bh,PANEL,LINE,12))
    P.append(f'<rect x="40" y="{y}" width="6" height="{bh}" rx="3" fill="{acc}"/>')
    P.append(t(60,y+26,h,13.5,TXT,700))
    P.append(box(1140-230,y+12,214,24,acc,LINE,6)); P.append(t(1140-123,y+29,tag,9.3,"#0f1419" if acc in(GRN,ACC,AMB) else TXT,700,"middle"))
    s,n=wrap(60,y+48,d,128,9.8,SUB,14); P.append(s)
    P.append(t(60,y+bh-32,meta,9.4,(("#8fae8f") if acc==GRN else ("#cbb87a" if acc==AMB else ("#d98a8a" if acc==RED else "#9bb3d6"))),700))
    s,_=wrap(60,y+bh-16,note,150,9,SUB,12); P.append(s)
    y+=bh+8
P.append(t(40,H-14,"Bottom line: build the grounded interactive viewer now; treat true 3D as an optional module fed by REAL 3D data (CAD or photogrammetry). Avoid AI-from-scan. Proposal only — your call.",10,AMB,400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/28-3d-feasibility-spectrum"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
