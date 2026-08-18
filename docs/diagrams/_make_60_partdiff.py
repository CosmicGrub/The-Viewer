#!/usr/bin/env python3
"""BUILT 0.43.0: Look-Alike Parts recognizer — tell apart parts that look identical (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,760
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"
ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"; TEAL="#1d9e75"; PUR="#7f77dd"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def arrow(x1,y1,x2,y2,col="#9aa5b1"): return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="1.7" fill="none" marker-end="url(#a)"/>'
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
P.append(t(40,46,"BUILT — Look-Alike Parts recognizer  (v0.43.0)",19,TXT,700))
P.append(t(40,70,"Tells apart parts that look identical in the manual but are functionally different — by NSN, UOC, CAGEC, SMR or supply class — with grounded 'how to tell them apart' cues. Read-only.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# pipeline
P.append(t(56,116,"1 · HOW IT WORKS  (/partdiff · /api/partdiff)",12,ACC,700))
P.append(box(40,126,1100,180,PANEL,LINE,12))
flow=[("Query","an NSN or a part name",PUR),
      ("Same-name group","every catalogued part sharing that name/nomenclature",ACC),
      ("Group by NSN","collapse to distinct stock numbers + their attributes",TEAL),
      ("Find discriminators","which fields vary: NSN · FSC · UOC · CAGEC · SMR · part#",AMB),
      ("Classify + cross-ref","vs the correlations sidecar (true substitutes vs real differences)",GRN),
      ("Compare + cite","side-by-side cards, how-to-tell-apart, links to the real figure",RED)]
x=58
for i,(h,d,c) in enumerate(flow):
    bx=x; P.append(box(bx,150,168,140,P2,c,10,1)); P.append(t(bx+12,172,str(i+1),11,c,700)); P.append(t(bx+28,172,h,9.4,TXT,700))
    s,_=wrap(bx+12,192,d,29,8.2,SUB,11); P.append(s)
    if i<5: P.append(arrow(bx+168,220,bx+180,220,c))
    x+=180

# the four verdicts
P.append(t(56,338,"2 · THE FOUR VERDICTS (colour-coded in the UI)",12,ACC,700))
P.append(box(40,348,1100,150,PANEL,LINE,12))
verd=[("reference",ACC,"the part you searched — the anchor for the comparison"),
      ("different variant",AMB,"same name, different NSN — usually a different VEHICLE CONFIG. The tell is the UOC (Usable-On-Code); also CAGEC / part#. THIS is the dangerous look-alike."),
      ("same item (format drift)",GRN,"same NIIN, just a different NSN format — genuinely the same part. Interchangeable."),
      ("different item class",TEAL,"different FSC — merely shares a figure title (e.g. a bracket inside an 'engine assembly' figure). NOT a substitute.")]
y=372
for nm,c,d in verd:
    P.append(f'<rect x="58" y="{y-11}" width="150" height="16" rx="4" fill="{c}" fill-opacity="0.18" stroke="{c}"/>')
    P.append(t(64,y,nm,9.4,c,700)); s,n=wrap(222,y,d,118,8.8,SUB,11); P.append(s); y+=14+ (n-1)*11 + 10

# UOC callout
P.append(box(40,512,1100,86,PANEL,AMB,12,1))
P.append(t(58,536,"WHY UOC IS THE KEY",12,AMB,700))
s,_=wrap(58,556,"In an RPSTL, two parts can be drawn the same and share a name, yet one fits configuration A and the other configuration B. The Usable-On-Code (UOC) is the field that disambiguates them — pick the wrong NSN and the part may not fit. The recognizer surfaces the UOC contrast first, then CAGEC (maker) and part number.",182,9.4,SUB,13); P.append(s)

# grounding
P.append(box(40,610,1100,118,PANEL,GRN,12,1))
P.append(t(58,634,"GROUNDED & ADDITIVE (R1/R6)",12,GRN,700))
s,_=wrap(58,654,"Read-only over the existing parts index + the optional correlations sidecar — no new data invented, nothing written to the index. Every variant cites the real figure & page so the mechanic confirms on the sheet. Confirmed-same items (NIIN drift) and cross-platform interchangeable NSNs are labelled as substitutes, not differences. As OCR coverage climbs, item names sharpen and the look-alike groups get finer. New routes only (rollback = remove /partdiff + /api/partdiff). The empty part_variants table is now meaningfully populated on demand at query time.",182,9.4,SUB,13); P.append(s)
P.append(t(40,H-12,"BUILT diagram. Dark (R3). v0.43.0 · 2026-06-02 · engine/ui/partdiff.html + part_differences() in viewer_app.py. Read-only; correlations sidecar optional.",9,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/60-partdiff-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"), "bytes")
