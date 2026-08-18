#!/usr/bin/env python3
"""Proposal markup: structured grounding layer (RPSTL parts + variants + verbatim procedures) — dark R3."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,900
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def arrow(x1,y1,x2,y2,col="#9aa5b1"): return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="1.7" fill="none" marker-end="url(#a)"/>'
def wrap(x,y,s,width,size,fill,dy=14,wt=400):
    out=[];words=s.split();line="";ln=0
    for wd in words:
        if len(line)+len(wd)+1>width: out.append(t(x,y+ln*dy,line,size,fill,wt));line=wd;ln+=1
        else: line=(line+" "+wd).strip()
    if line: out.append(t(x,y+ln*dy,line,size,fill,wt))
    return "".join(out),ln+1
P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
P.append('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9aa5b1"/></marker></defs>')
P.append(box(0,0,W,H,BG,BG,0))
P.append(t(40,46,"Structured grounding layer — design markup (top pick, before build)",21,TXT,700))
P.append(t(40,70,"Parse the manuals' own RPSTL parts tables & maintenance work packages into structured records → exact part auto-fill, look-alike warnings, and a verbatim procedure panel. Every field stays cited to its page.",11,SUB,400))
# data proof strip
P.append(box(40,86,1100,30,P2,LINE,7))
P.append(t(52,106,"In your corpus (sample index):",10,SUB,700))
proof=[("ITEM NO","4,223"),("SMR","4,590"),("PART NUMBER","3,764"),("USABLE ON CODE","3,748"),("torque","1,561"),("lb-ft","1,030")]
x=250
for a,b in proof:
    P.append(t(x,106,a+" ",9.5,SUB,400)); P.append(t(x+len(a)*6.2+4,106,b,9.5,"#bfe6c5",700)); x+=len(a)*6.2+len(b)*7+30

# EXTRACTION (left)
P.append(box(40,128,520,330,PANEL,LINE,12))
P.append(t(58,152,"1 · EXTRACTION  (offline, idempotent, resumable)",12,ACC,700))
P.append(box(58,166,484,72,P2,LINE)); P.append(t(70,186,"RPSTL / -24P parts pages",11,TXT,700))
s,_=wrap(70,204,"Parse repeating rows: FIG · ITEM · SMR · CAGEC · NSN · PART NUMBER · NOMENCLATURE · USABLE-ON-CODE.",80,9.4,SUB,13); P.append(s)
P.append(box(58,246,484,72,P2,LINE)); P.append(t(70,266,"Maintenance work packages (WP)",11,TXT,700))
s,_=wrap(70,284,"Parse tasks: REMOVAL / INSTALLATION / DISASSEMBLY → numbered steps, tools, torque values — captured verbatim with page refs.",80,9.4,SUB,13); P.append(s)
P.append(arrow(300,318,300,336,ACC))
P.append(box(58,338,484,104,"#101a14",GRN,9))
P.append(t(70,358,"→ schema migration 0004 (additive, R1) fills the reserved tables:",10.5,"#bfe6c5",700))
s,_=wrap(70,376,"parts (+ cagec, smr, fig_no, item_no, uoc, nomenclature, doc, page, vehicle) · part_variants (differs_how, how_to_tell) · procedures (kind, steps, tools, torque, doc, page) · figures.",80,9,SUB,13); P.append(s)
s,_=wrap(70,422,"Confidence score per record; the source page is always kept for citation.",80,9,AMB,13); P.append(s)

# OUTPUTS (right)
P.append(t(580,148,"2 · GROUNDED OUTPUTS",12,AMB,700))
outs=[
 ("A · Exact part auto-fill",GRN,
  "Add a part → NSN, part#, FIG, nomenclature fill from the structured RPSTL row (not a guessed snippet), cited to the catalog page.",128),
 ("B · Look-alike warning",AMB,
  "Same nomenclature, different NSN/part#? Show '⚠ 2 variants — check Usable-On-Code' with the cited distinguishing column. Only when the data shows a real difference.",212),
 ("C · Verbatim procedure panel",ACC,
  "For a part/fault: remove/install steps, tools, and torque shown VERBATIM with TM+page — never paraphrased. Your original goal C.",312),
]
for h,acc,d,y in outs:
    P.append(box(580,y,560,82,PANEL,LINE,11))
    P.append(f'<rect x="580" y="{y}" width="5" height="82" rx="2" fill="{acc}"/>')
    P.append(t(598,y+24,h,12.5,TXT,700))
    s,_=wrap(598,y+44,d,78,9.6,SUB,14); P.append(s)
P.append(box(580,406,560,42,"#16223a","#2c3f5e",9))
P.append(t(598,432,"+ OCR coverage meter (parallel): /api/coverage → per-vehicle '% searchable' shown in the hub & search.",10,"#9bc0ff",400))

# SEQUENCING
P.append(t(40,488,"3 · SEQUENCING",12,ACC,700))
ph=[("PHASE 1  (foundation)",GRN,"Structured RPSTL parts + look-alike variants + exact auto-fill. Migration 0004. Coverage meter. Quick wins: multi-sheet pagination (>6 items) + capture confirm/override.","build first"),
    ("PHASE 2  (verbatim procedures)",ACC,"Procedure panel: remove/install/tools/torque, cited & verbatim, linked from a part or fault. Builds on Phase-1 parts & figures.","next"),
    ("PARALLEL  (OCR)",AMB,"Keep completing GPU OCR; each pass raises extraction coverage for both phases. Coverage meter makes the progress visible.","ongoing")]
y=504
for h,acc,d,tag in ph:
    P.append(box(40,y,1100,80,PANEL,LINE,11))
    P.append(f'<rect x="40" y="{y}" width="6" height="80" rx="3" fill="{acc}"/>')
    P.append(t(60,y+26,h,12.5,TXT,700))
    P.append(box(1000,y+16,124,26,acc,LINE,6)); P.append(t(1062,y+33,tag,9.5,"#0f1419",700,"middle"))
    s,_=wrap(60,y+46,d,128,9.6,SUB,14); P.append(s)
    y+=88

# honesty note
P.append(box(40,y+4,1100,60,PANEL,RED,12,1))
P.append(t(58,y+26,"GROUNDING GUARANTEE",11,RED,700))
s,_=wrap(58,y+44,"Extraction is OCR/table-noisy, so: nothing is shown without its cited source page; low-confidence records are flagged for the mechanic to verify; a look-alike difference is only stated when the manual's data actually shows it. We surface the manual — we never paraphrase specs or invent a variant.",150,9.6,SUB,13); P.append(s)
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/24-structured-grounding-proposal"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
