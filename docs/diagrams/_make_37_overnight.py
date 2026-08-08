#!/usr/bin/env python3
"""Overnight batch summary (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,760
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def wrap(x,y,s,width,size,fill,dy=13,wt=400):
    out=[];words=s.split();line="";ln=0
    for wd in words:
        if len(line)+len(wd)+1>width: out.append(t(x,y+ln*dy,line,size,fill,wt));line=wd;ln+=1
        else: line=(line+" "+wd).strip()
    if line: out.append(t(x,y+ln*dy,line,size,fill,wt))
    return "".join(out),ln+1
P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
P.append(box(0,0,W,H,BG,BG,0))
P.append(t(40,46,"Overnight batch — what got done (v0.25.0)",22,TXT,700))
P.append(t(40,70,"All on your live full index, additive (R1) & append-only (R6). One-click rollback ready. Index verified intact: 39,683 docs · 1,848,465 pages.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
cards=[
 ("✓ Parts on the FULL index",GRN,"227,908 records · 45,068 distinct part NSNs extracted from 40,793 RPSTL pages.","done"),
 ("✓ FLIS enrichment — whole catalog",GRN,"41,701 NSNs: 44k names · 41k part#/CAGE · 31k dimensions · 40k AAC+price+date.","done"),
 ("✓ Supersession · vintage · multiple-choice",GRN,"FLIS year tag (e.g. 'FLIS 2013'), current/interchangeable NSN cross-ref, multiple part# choices — on the cart.","done"),
 ("✓ 2D→3D representative viewer",GRN,"Offline rotatable solid scaled to FLIS dimensions; features listed verbatim & cited; 'not a CAD model'.","done"),
 ("✓ Search speed",GRN,"Indexes + ANALYZE refreshed; full-text ~45 ms over 1.85M pages.","done"),
 ("✓ Rollback (R1)",GRN,"run_rollback.bat (dry-run default; /yes to apply). Removes enrichment+parts; keeps docs/pages/OCR.","ready"),
 ("◐ OCR to 100%",AMB,"Multi-day GPU job — cannot finish unattended here. Pipeline ready: run_ocr_gpu.bat. Re-run parts+enrich after.","your GPU"),
]
cw=540; gap=20; x0=40; y0=104; rh=92
for i,(h,acc,d,tag) in enumerate(cards):
    col=i%2; row=i//2
    x=x0+col*(cw+gap); y=y0+row*(rh+12)
    P.append(box(x,y,cw,rh,PANEL,LINE,11))
    P.append(f'<rect x="{x}" y="{y}" width="5" height="{rh}" rx="2" fill="{acc}"/>')
    P.append(t(x+18,y+26,h,12.5,TXT,700))
    P.append(box(x+cw-96,y+12,80,22,acc,LINE,6)); P.append(t(x+cw-56,y+27,tag,9,"#0f1419" if acc in(GRN,AMB) else TXT,700,"middle"))
    s,_=wrap(x+18,y+46,d,74,9.4,SUB,13); P.append(s)
P.append(box(40,y0+4*(rh+12)+6,1100,70,PANEL,ACC,12,1))
P.append(t(58,y0+4*(rh+12)+30,"WHEN YOU WAKE UP",12,ACC,700))
s,_=wrap(58,y0+4*(rh+12)+50,"Everything is live and searchable. If you want to undo any of it: dry-run run_rollback.bat to see exactly what it removes, then run with /yes. To finish OCR: run_ocr_gpu.bat on the GPU box, then re-run parts + enrich to extend the catalog enrichment to the newly-readable NSNs.",176,9.6,SUB,13); P.append(s)
P.append(t(40,H-12,"Dark (R3) · CHANGELOG 0.25.0 (R4) · visual panel (R5) · rollback in docs/ROLLBACK.md.",9.2,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/37-overnight-batch"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1180)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
