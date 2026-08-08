#!/usr/bin/env python3
"""BUILT 0.32.0: NIIN-review confirm/reject workflow (append-only) + OCR run guide (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,720
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
P.append(t(40,46,"BUILT — NIIN-review workflow + OCR run guide  (v0.32.0)",20,TXT,700))
P.append(t(40,70,"The 884 NIIN-drift findings are now an actionable confirm/reject queue with decisions saved append-only — and a clear, resumable OCR finish on your GPU.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# Panel 1: review workflow
P.append(t(56,116,"1 · NIIN-DRIFT REVIEW — confirm / reject (append-only)",12,ACC,700))
P.append(box(40,126,1100,250,PANEL,LINE,12))
# flow: correlations -> status page queue -> decide -> reviews.db
P.append(box(60,150,180,56,P2,LINE,8)); P.append(t(150,172,"correlations.db",10,TXT,700,"middle")); P.append(t(150,188,"884 drift groups",8.6,SUB,400,"middle"))
P.append(arrow(240,178,266,178,TEAL))
P.append(box(270,150,210,56,P2,LINE,8)); P.append(t(375,170,"/status review queue",9.6,ACC,700,"middle")); P.append(t(375,186,"FSC-conflict flagged",8.6,SUB,400,"middle")); P.append(t(375,199,"pending / all filter",8.2,SUB,400,"middle"))
P.append(arrow(480,178,506,178,TEAL))
P.append(box(510,150,250,56,P2,LINE,8)); P.append(t(635,168,"choose a decision",9.6,TXT,700,"middle"))
for i,(d,c) in enumerate([("distinct",GRN),("interchange",ACC),("error",RED),("dismiss",SUB)]):
    P.append(box(520+i*58,182,54,18,P2,c,5,1)); P.append(t(547+i*58,194,d,7.6,c,700,"middle"))
P.append(arrow(760,178,786,178,TEAL))
P.append(box(790,150,210,56,"#13241c",GRN,8)); P.append(t(895,170,"POST decision",9.6,"#bfe6cf",700,"middle")); P.append(t(895,186,"/api/niin_review_decision",8.2,"#8fbf9f",400,"middle"))
P.append(arrow(895,206,895,224,TEAL))
P.append(box(790,226,210,52,P2,GRN,8,1)); P.append(t(895,246,"reviews.db (sidecar)",9.4,"#bfe6cf",700,"middle")); P.append(t(895,262,"INSERT only — never update",8.2,"#8fbf9f",400,"middle"))
# semantics
P.append(t(60,238,"Decision semantics:",9.6,AMB,700))
for i,(d,desc) in enumerate([("distinct","genuinely different items — keep both"),
        ("interchangeable","same item; optional canonical NSN"),
        ("error","extraction/OCR error — flag for fix"),
        ("dismiss","reviewed, no action")]):
    y=256+i*20; P.append(t(72,y,"• "+d,9.2,TXT,700)); P.append(t(230,y,desc,9,SUB,400))
s,_=wrap(440,256,"Append-only (R6): changing your mind inserts a new row; the latest wins and the full history is kept for audit. Decisions are recorded for review — the main index is never auto-changed (R1). The queue shows decided/pending counts and hides decided items by default.",118,9,SUB,12); P.append(s)
P.append(t(60,360,"Validated: 9-digit NIIN + a known decision required; roundtrip tested (append-only, latest-wins).",9,GRN,400))

# Panel 2: OCR run
P.append(t(56,408,"2 · FINISH OCR ON YOUR GPU  (resumable)",12,ACC,700))
P.append(box(40,418,1100,210,PANEL,LINE,12))
steps=[("run_ocr_gpu.bat","installs RapidOCR + onnxruntime-gpu"),
       ("snapshot (pre-ocr)","restore point first"),
       ("cleanup","requeue half-finished pages"),
       ("ocrall","prioritize -> loop to 0 pending"),
       ("watch /status","live OCR progress bar")]
x=58
for i,(h,d) in enumerate(steps):
    P.append(box(x,440,200,54,P2,LINE,8)); P.append(t(x+12,460,str(i+1)+" · "+h,9.4,TXT,700)); s,_=wrap(x+12,476,d,32,8.2,SUB,10); P.append(s)
    if i<4: P.append(arrow(x+200,467,x+212,467,ACC))
    x+=214
P.append(t(58,520,"~119,000 pages remain (6.5%).  Resumable: stop/re-run anytime.  Falls back to CPU automatically.",9.6,TXT,400))
P.append(t(58,540,"Estimate: GPU ~ a few hours–half a day · CPU ~ 1–3 days (varies by GPU, page complexity, DPI).",9.2,SUB,400))
s,_=wrap(58,564,"Honest: this is compute time on YOUR machine — the assistant can't run it remotely. OCR only ADDS text to blank pages (R6), so it's safe and outside any rollback. When it finishes, mirror-mode readable labels light up on those pages. Full steps: docs/OCR-RUN-GUIDE.md.",184,9,SUB,12); P.append(s)
P.append(t(40,H-12,"BUILT diagram. Dark (R3). v0.32.0 · 2026-06-02 · companion: docs/OCR-RUN-GUIDE.md.",9.2,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/46-niin-review-ocr-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1180)
print("wrote", os.path.getsize(base+".pdf"), "bytes ->", base+".pdf")
