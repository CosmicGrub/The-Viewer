#!/usr/bin/env python3
"""BUILT 0.62.0: 3D library OCR hookup — a representative part links to the REAL manual pages that mention
its NSN (live from the text layer), the collections it falls into, and its dossier / Look-Alike Parts.
Batch 3 of 3. (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,600
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
P.append(t(40,46,"BUILT — 3D library, wired to the manuals  (v0.62.0)   ·  Batch 3 of 3",19,TXT,700))
P.append(t(40,70,"Open a representative 3D part and the side panel now shows the real TM pages that mention its NSN — pulled live from the OCR'd text — plus its dossier, look-alikes, and the collections it appears in.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# flow
fy=108
P.append(box(40,fy,230,92,PANEL,PUR,12)); P.append(t(58,fy+25,"🧊  Open a 3D part",12,TXT,700))
s,_=wrap(58,fy+45,"a representative shape (FLIS dims) — it carries the part's NSN + part number.",36,9,SUB,11); P.append(s)
P.append(box(306,fy,230,92,PANEL,TEAL,12)); P.append(t(324,fy+25,"🔢  NSN → text phrase",12,TXT,700))
s,_=wrap(324,fy+45,"the NSN becomes an FTS phrase \"2540 01 123 4567\" that matches the dashed form in the text.",36,9,SUB,11); P.append(s)
P.append(box(572,fy,230,92,PANEL,AMB,12)); P.append(t(590,fy+25,"🔎  Read the text layer",12,TXT,700))
s,_=wrap(590,fy+45,"find every page mentioning it + test each collection's query — all read-only.",36,9,SUB,11); P.append(s)
P.append(box(838,fy,302,92,PANEL,ACC,12)); P.append(t(856,fy+25,"📋  Side panel of jumps",12,TXT,700))
s,_=wrap(856,fy+45,"clickable manual pages (highlighted), dossier, Look-Alike Parts, and the collections it's in.",50,9,SUB,11); P.append(s)
P.append(arrow(270,fy+46,306,fy+46)); P.append(arrow(536,fy+46,572,fy+46)); P.append(arrow(802,fy+46,838,fy+46))

def panel(x,y,w,h,ic,title,color,rows,metric):
    out=[box(x,y,w,h,PANEL,LINE,12), f'<rect x="{x}" y="{y}" width="6" height="{h}" rx="3" fill="{color}"/>']
    out.append(t(x+20,y+24,ic+"  "+title,12.5,TXT,700)); yy=y+44
    for r in rows:
        out.append(f'<circle cx="{x+24}" cy="{yy-3}" r="3" fill="{color}"/>'); s,n=wrap(x+36,yy,r,int((w-58)/5.2),8.7,SUB,11); out.append(s); yy+=3+n*11
    out.append(box(x+16,y+h-30,w-32,22,P2,color,6,1)); out.append(t(x+26,y+h-15,metric,8.8,color,700))
    return "".join(out)
P.append(panel(40,224,360,200,"🔗","From a shape to the real pages",AMB,
  ["The 3D library was a dead end — a shape with FLIS specs and nothing more.",
   "Now each part links to the TM pages that actually reference its NSN, opened with the NSN highlighted.",
   "Also one-click to the part dossier and Look-Alike Parts for the same NSN.",
   "Grows on its own as OCR makes more pages searchable."],
  "The 3D shape is now a doorway into the manuals."))
P.append(panel(412,224,360,200,"🗂","Collections it belongs to",TEAL,
  ["For each collection, a cheap EXISTS asks: is there a page matching BOTH this part's NSN AND the collection's query?",
   "So a gasket can show 'In collections: Torque specs' if it's referenced on a torque page.",
   "Reuses the same collection definitions from Batches 1/1+."],
  "Ties the 3D part to the living collections."))
P.append(panel(784,224,356,200,"🛡","Read-only & RPS-safe",GRN,
  ["One /api/threed_refs fetch per part: an FTS read + a handful of EXISTS. No writes (R1/R6).",
   "WAL → never blocks the OCR writer; safe to use mid-scan.",
   "The 3D itself already degrades to SVG on old machines; the refs panel is plain DOM + fetch, so it works there too."],
  "No OCR contention · works on the SVG-fallback path."))
P.append(box(40,440,1100,84,PANEL,GRN,12,1))
P.append(t(58,462,"VERIFIED  ·  COMPLETES THE 3-BATCH OCR WIRING",11.5,GRN,700))
s,_=wrap(58,480,"Isolation test: the NSN phrase matched the dashed form on the right page (and correctly ignored an unrelated page); collection membership returned 'Torque specs', and after an OCR page added a WARNING mentioning the same NSN, 'Warnings' appeared too — the live-growth property. loadRefs JS syntax-checks; server function + /api/threed_refs route confirmed on host. With Batch 1 (collections), Batch 2 (page callouts) and this, the OCR text layer is now wired into search, the page/schematic viewers, collections, and the 3D library.",190,9.2,SUB,12.5);P.append(s)
P.append(t(40,H-12,"BUILT diagram. Dark (R3). v0.62.0 · 2026-06-02 · viewer_app.py (threed_refs + /api/threed_refs) · threed.html (loadRefs side panel). Read-only / additive (R1/R6).",9,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/76-threed-ocr-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"), "bytes")
