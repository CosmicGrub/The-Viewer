#!/usr/bin/env python3
"""BUILT 0.33.0: confirmed-interchangeable NSN alias map in search + GPU readiness (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,700
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"; TEAL="#1d9e75"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def arrow(x1,y1,x2,y2,col="#9aa5b1"): return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="1.6" fill="none" marker-end="url(#a)"/>'
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
P.append(t(40,46,"BUILT — NSN alias map in search + GPU readiness  (v0.33.0)",20,TXT,700))
P.append(t(40,70,"Confirmed-interchangeable NSNs now find each other in search; a one-command GPU check + a prioritized OCR queue make the OCR run fast and useful.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# Panel 1: alias map flow
P.append(t(56,116,"1 · CONFIRMED-INTERCHANGEABLE ALIAS MAP (grounded)",12,ACC,700))
P.append(box(40,126,1100,228,PANEL,LINE,12))
P.append(box(60,150,210,56,P2,LINE,8)); P.append(t(165,170,"you mark a NIIN group",9.6,TXT,700,"middle")); P.append(t(165,186,"'interchangeable' on /status",8.4,SUB,400,"middle"))
P.append(arrow(270,178,296,178,TEAL))
P.append(box(300,150,190,56,"#13241c",GRN,8)); P.append(t(395,172,"reviews.db",9.6,"#bfe6cf",700,"middle")); P.append(t(395,188,"append-only decision",8.2,"#8fbf9f",400,"middle"))
P.append(arrow(490,178,516,178,TEAL))
P.append(box(520,150,230,56,P2,LINE,8)); P.append(t(635,170,"nsn_aliases(nsn)",9.6,ACC,700,"middle")); P.append(t(635,186,"decision + correlations variants",8.0,SUB,400,"middle"))
P.append(arrow(750,178,776,178,TEAL))
P.append(box(780,150,300,56,P2,ACC,8,1)); P.append(t(930,170,"search expands the NSN phrase",9.4,ACC,700,"middle")); P.append(t(930,186,'"5303 01 674 1467" OR "5305 01 674 1467"',7.8,SUB,400,"middle"))
# example
P.append(t(60,238,"Example:",10,AMB,700))
P.append(t(120,238,"search 5303-01-674-1467  →  also surfaces pages/cover that wrote it as 5305-01-674-1467 (the confirmed-same bolt).",9.4,TXT,400))
s,_=wrap(60,262,"Grounded & reversible: aliases come ONLY from decisions YOU confirmed as 'interchangeable' — never auto-merged. No decision = no expansion (search is unchanged). Change your mind and the latest decision wins; delete reviews.db to undo entirely. The main index is never modified (R1/R6).",184,9.2,SUB,13); P.append(s)
P.append(t(60,338,"Tested: nsn_aliases expands only confirmed NIINs; sparse-query unaffected; alias search surfaces the equivalent NSN's pages (23/23 pillar tests).",9,GRN,400))

# Panel 2: GPU readiness + queue
P.append(t(56,386,"2 · GPU READINESS + PRIORITIZED OCR QUEUE",12,ACC,700))
P.append(box(40,396,1100,250,PANEL,LINE,12))
# gpu check
P.append(t(60,420,"python engine\\gpu_check.py  →  one clear verdict",10.5,TXT,700))
P.append(box(60,432,300,40,"#13241c",GRN,8)); P.append(t(75,457,"GPU READY ✓  (CUDAExecutionProvider)",9.4,"#bfe6cf",700))
P.append(box(380,432,300,40,"#2a1a1a",RED,8)); P.append(t(395,452,"CPU ONLY + exact fix",9.4,"#f0b3b0",700)); P.append(t(395,466,"(driver / onnxruntime-gpu / CUDA match)",8,"#cf9a98",400))
# queue table
P.append(t(60,500,"OCR queue — prioritized (parts catalogs first):",10.5,TXT,700))
rows=[("0  parts catalogs (RPSTL/24P)","25,516",GRN),("1  troubleshooting","373",ACC),("2  maintenance (-20/-24)","26,504",ACC),("3  operator (-10)","7,606",AMB),("5  everything else","59,240",SUB)]
y=518
for lab,n,c in rows:
    P.append(f'<rect x="60" y="{y-10}" width="8" height="8" rx="2" fill="{c}"/>'); P.append(t(76,y,lab,9.4,SUB,400)); P.append(t(360,y,n+" pages",9.4,TXT,700)); y+=19
P.append(t(60,624,"Status: 1.6% done · 93.5% of all pages already searchable · 275 stuck pages recovered. The run itself is GPU time on your box (resumable).",9.2,GRN,400))
# right note
s,_=wrap(640,520,"A partial run already helps: the pages mechanics search most (parts catalogs) are OCR'd first. Watch live progress on /status; stop and re-run anytime. OCR only ADDS text (R6).",80,9.2,SUB,13); P.append(s)
P.append(t(40,H-10,"BUILT diagram. Dark (R3). v0.33.0 · 2026-06-02 · companions: SETUP-GPU.md, OCR-RUN-GUIDE.md.",9.2,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/47-alias-gpu-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1180)
print("wrote", os.path.getsize(base+".pdf"), "bytes ->", base+".pdf")
