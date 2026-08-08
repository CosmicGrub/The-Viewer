#!/usr/bin/env python3
"""BUILT 0.60.0: OCR-driven page callouts — clickable part#/NSN/figure markers pulled from a page's text;
positioned hotspots where a text layer exists, chip list otherwise. Batch 2 of 3. (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,612
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"
ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; TEAL="#1d9e75"; PUR="#7f77dd"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def wrap(x,y,s,width,size,fill,dy=13,wt=400):
    out=[];words=s.split();c="";l=0
    for wd in words:
        if len(c)+len(wd)+1>width: out.append(t(x,y+l*dy,c,size,fill,wt));c=wd;l+=1
        else: c=(c+" "+wd).strip()
    if c: out.append(t(x,y+l*dy,c,size,fill,wt))
    return "".join(out),l+1
def arrow(x1,y1,x2,y2,color=SUB):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.6" marker-end="url(#ah)"/>'
P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
P.append(f'<defs><marker id="ah" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="{SUB}"/></marker></defs>')
P.append(box(0,0,W,H,BG,BG,0))
P.append(t(40,46,"BUILT — OCR-driven page callouts  (v0.60.0)   ·  Batch 2 of 3",19,TXT,700))
P.append(t(40,70,"Turn the part numbers, NSNs and figure references buried in a page's text into clickable jumps — straight to the part dossier, Look-Alike Parts, or the cited figure.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# flow
fy=108
P.append(box(40,fy,224,92,PANEL,AMB,12)); P.append(t(58,fy+25,"📄  One page's body_text",12,TXT,700))
s,_=wrap(58,fy+45,"read a single indexed row — native-text OR OCR'd page (OCR fills body_text).",36,9,SUB,11); P.append(s)
P.append(box(300,fy,224,92,PANEL,TEAL,12)); P.append(t(318,fy+25,"🔎  Extract callouts",12,TXT,700))
s,_=wrap(318,fy+45,"NSN regex · labeled P/N · FIG refs — deduped (dashed + bare NSN collapse to one).",36,9,SUB,11); P.append(s)
P.append(box(560,fy,224,92,PANEL,PUR,12)); P.append(t(578,fy+25,"📐  Anchor to word boxes",12,TXT,700))
s,_=wrap(578,fy+45,"match each token to a get_text('words') box → normalized coords (native pages only).",36,9,SUB,11); P.append(s)
P.append(box(820,fy,320,92,PANEL,ACC,12)); P.append(t(838,fy+25,"🏷  Hotspots + chip bar",12,TXT,700))
s,_=wrap(838,fy+45,"numbered dots on the image where boxes exist; a clickable chip bar always (works on OCR pages with no coords).",52,9,SUB,11); P.append(s)
P.append(arrow(264,fy+46,300,fy+46)); P.append(arrow(524,fy+46,560,fy+46)); P.append(arrow(784,fy+46,820,fy+46))

def panel(x,y,w,h,ic,title,color,rows,metric):
    out=[box(x,y,w,h,PANEL,LINE,12), f'<rect x="{x}" y="{y}" width="6" height="{h}" rx="3" fill="{color}"/>']
    out.append(t(x+20,y+24,ic+"  "+title,12.5,TXT,700)); yy=y+44
    for r in rows:
        out.append(f'<circle cx="{x+24}" cy="{yy-3}" r="3" fill="{color}"/>'); s,n=wrap(x+36,yy,r,int((w-58)/5.2),8.7,SUB,11); out.append(s); yy+=3+n*11
    out.append(box(x+16,y+h-30,w-32,22,P2,color,6,1)); out.append(t(x+26,y+h-15,metric,8.8,color,700))
    return "".join(out)
py=220
P.append(panel(40,py,360,206,"🏷","Three callout kinds → one click",AMB,
  ["NSN (most precise, incl. bare 13-digit) → opens the part dossier.",
   "Labeled part number (P/N: …, PART NO. …) → opens Look-Alike Parts.",
   "FIG / FIGURE n(-n) → find-in-manual jump to that figure in THIS document.",
   "Deduped; capped at 60 per page; verbatim from the manual — never invented."],
  "Buried tokens become one-tap jumps."))
P.append(panel(412,py,360,206,"📐","Positioned where we can locate it",TEAL,
  ["Native-text pages: each token is matched to its PyMuPDF word box → a numbered dot sits ON the spot; dots follow tilt/zoom and flip with the page.",
   "OCR-only pages have body_text but no word boxes → no dots, but the SAME callouts appear in the chip bar.",
   "Honest: we only place a dot we can actually locate."],
  "Dots on native pages · chips everywhere."))
P.append(panel(784,py,356,206,"🛡","Read-only & safe with the scan",GRN,
  ["One /api/callouts fetch per page — a single indexed row + the page's word list. No writes (R1/R6).",
   "WAL → these reads never block the OCR writer; runs fine mid-scan.",
   "Wired into the main viewer (🏷 Callouts toggle) AND the Schematics gate (chip bar).",
   "Shared extractor page_callouts() — Batch 3 (3D) reuses it."],
  "Read-only · no OCR contention · reused by Batch 3."))

P.append(box(40,448,1100,84,PANEL,GRN,12,1))
P.append(t(58,470,"VERIFIED",11.5,GRN,700))
s,_=wrap(58,488,"Isolation test of the extractor: on a native page, a dashed NSN and its bare-digit twin collapsed to one dossier link, two labeled part numbers and two FIG refs were found, and the NSN anchored to its word box. On an OCR-only page (no boxes) the same NSN + FIG came through as chips with no coords — exactly the fallback. Main-viewer callout JS and the Schematics chip loader both syntax-checked and run. Server function + /api/callouts route confirmed on the host.",188,9.2,SUB,12.5);P.append(s)
P.append(t(40,H-12,"BUILT diagram. Dark (R3). v0.60.0 · 2026-06-02 · viewer_app.py (page_callouts + /api/callouts) · index.html (🏷 toggle, hotspots+chips) · schematics.html (chip bar). Additive (R1/R6).",9,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/74-page-callouts-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1180)
print("wrote", os.path.getsize(base+".pdf"), "bytes")
