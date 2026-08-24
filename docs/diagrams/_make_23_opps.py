#!/usr/bin/env python3
"""Grounded improvement opportunities — ranked (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,760
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
P.append(t(40,46,"Where it can get better — while staying grounded",22,TXT,700))
P.append(t(40,70,"Every option below pulls from real data (the manuals' own tables, your AMDF extract, your logs). None invent steps, specs, or stock numbers.",11.5,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
cards=[
 ("1 · Structured RPSTL parts","HIGH IMPACT",GRN,
  "Parse the parts catalogs (RPSTL) into a real parts table: NSN ↔ part# ↔ FIG ↔ nomenclature ↔ vehicle. Adding a part auto-fills those fields exactly (cited), and powers look-alike variant warnings (your 'identical but different' goal).",
  "Grounded: the manual's own parts tables · Effort: med-high · Helped by OCR"),
 ("2 · FEDLOG / AMDF import","HIGH IMPACT",GRN,
  "Import a FEDLOG/AMDF CSV the unit already has; auto-fill the FEDLOG row (unit price · AAC · ARC) by NSN. Today those three are typed by hand.",
  "Grounded: your authoritative AMDF extract · Effort: low-med · Offline"),
 ("3 · Verbatim procedure panel","VISION (goal C)",AMB,
  "For a fault/part, surface the maintenance task verbatim & cited: remove/install steps, tools, torque — never paraphrased. Uses the unused 'procedures' table.",
  "Grounded: verbatim WP text, cited · Effort: high · OCR-dependent"),
 ("4 · Finish OCR + coverage meter",ACC and "UNLOCKS ALL" or "UNLOCKS ALL",ACC,
  "Complete the GPU OCR pass and show a per-vehicle coverage meter ('72% searchable'). Sharpens search, schematics, and PMCS tech-status everywhere.",
  "Grounded: makes scanned pages citable · Effort: med (CUDA runtime)"),
 ("5 · Multi-sheet pagination",ACC and "QUICK WIN" or "QUICK WIN","#3a4d6e",
  "When a request exceeds 6 items, paginate cleanly across multiple 104th sheets instead of capping at 6.",
  "Grounded: mechanical · Effort: low"),
 ("6 · Capture confirm/override","QUICK WIN","#3a4d6e",
  "Log when a mechanic accepts or overrides a tech-status (or part) suggestion, so the history signal and ranking get measurably better over time.",
  "Grounded: your own confirmations · Effort: low"),
]
cw=540; gap=20; x0=40; y0=104; rh=192
for i,(h,tagspec,acc,d,foot) in enumerate(cards):
    tag = tagspec if isinstance(tagspec,str) else tagspec
    col=i%2; row=i//2
    x=x0+col*(cw+gap); y=y0+row*(rh+16)
    P.append(box(x,y,cw,rh,PANEL,LINE,12))
    P.append(f'<rect x="{x}" y="{y}" width="6" height="{rh}" rx="3" fill="{acc}"/>')
    P.append(t(x+22,y+30,h,14,TXT,700))
    P.append(box(x+cw-150,y+14,134,24,acc,LINE,6)); P.append(t(x+cw-83,y+31,tag,9.5,"#0f1419" if acc in(GRN,AMB,ACC) else TXT,700,"middle"))
    s,n=wrap(x+22,y+56,d,68,10,SUB,15); P.append(s)
    P.append(t(x+22,y+rh-18,foot,9.2,"#8fae8f" if acc==GRN else ("#9bb3d6" if acc in(ACC,"#3a4d6e") else "#cbb87a"),700))
P.append(t(40,H-40,"My recommendation: start with #2 (FEDLOG import) + #5/#6 (quick wins) for immediate end-to-end completeness,",10.5,TXT,700))
P.append(t(40,H-24,"then #1 (structured RPSTL parts) as the big grounded accuracy leap, with #4 (OCR) running in parallel to unlock #1 and #3.",10.5,TXT,700))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/23-grounded-opportunities"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
