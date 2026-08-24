#!/usr/bin/env python3
"""BUILT 0.37.0: COMPLETE backward compatibility Win11 -> Vista via per-OS engine substitution (dark R3)."""
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
P.append(t(40,46,"BUILT — COMPLETE backward compatibility: Win 11 -> Vista  (v0.37.0)",20,TXT,700))
P.append(t(40,70,"Every feature works on every Windows from 11 down to Vista. The engine substitutes the right tool per OS; only GPU acceleration (a speed booster) is Win10+.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# Panel 1: feature x OS grid
P.append(t(56,116,"1 · SAME FEATURES, PER-OS ENGINES",12,ACC,700))
P.append(box(40,126,1100,250,PANEL,LINE,12))
cols=["Win 11/10","Win 8/8.1","Win 7","Vista"]
cx=[470,640,790,930]
for i,cname in enumerate(cols): P.append(t(cx[i],150,cname,9.6,SUB,700,"middle"))
rows=[("Search · vehicle hub · 104th sheet",["stdlib","stdlib","stdlib","stdlib"],GRN),
      ("Viewer · HD · loupe · tilt · zoom",["yes","yes","yes","yes"],GRN),
      ("Page render",["PyMuPDF","PyMuPDF/Poppler","PyMuPDF/Poppler","Poppler"],ACC),
      ("OCR (text recovery)",["PP-OCRv5","RapidOCR/Tess","RapidOCR/Tess","Tesseract"],ACC),
      ("Auto-snapshots",["yes","yes","yes","yes"],GRN),
      ("GPU acceleration (speed only)",["yes","-","-","-"],AMB)]
y=168
for name,vals,c in rows:
    P.append(t(58,y+12,name,9.4,TXT,700))
    for i,v in enumerate(vals):
        col=GRN if v not in ("-",) else "#5f5e5a"
        P.append(t(cx[i],y+12,v if v!="-" else "—",8.4,col,400,"middle"))
    P.append(f'<line x1="56" y1="{y+20}" x2="1124" y2="{y+20}" stroke="{LINE}"/>'); y+=33
P.append(t(58,366,"Only the ENGINE changes by OS — the result (a searchable index, the viewer, the 104th sheet) is identical everywhere.",9,GRN,400))

# Panel 2: how
P.append(t(56,400,"2 · HOW (substitution chain, auto-detected by sysprobe)",12,ACC,700))
P.append(box(40,410,1100,180,PANEL,LINE,12))
# render chain
P.append(t(60,436,"Render:",10,AMB,700))
P.append(box(130,420,150,30,P2,LINE,7)); P.append(t(205,440,"PyMuPDF (modern)",8.6,TXT,400,"middle"))
P.append(t(290,440,"else",8.4,SUB,400)); P.append(box(330,420,150,30,P2,LINE,7)); P.append(t(405,440,"Poppler pdftoppm",8.6,TXT,400,"middle"))
P.append(t(495,440,"(Win7/Vista)",8,SUB,400))
# ocr chain
P.append(t(60,476,"OCR:",10,AMB,700))
P.append(box(130,460,150,30,P2,LINE,7)); P.append(t(205,480,"RapidOCR GPU",8.6,TXT,400,"middle"))
P.append(t(290,480,"else",8.4,SUB,400)); P.append(box(330,460,150,30,P2,LINE,7)); P.append(t(405,480,"RapidOCR CPU",8.6,TXT,400,"middle"))
P.append(t(490,480,"else",8.4,SUB,400)); P.append(box(530,460,150,30,P2,LINE,7)); P.append(t(605,480,"Tesseract",8.6,TXT,400,"middle"))
P.append(t(690,480,"(Win7/Vista)",8,SUB,400))
# core
P.append(t(60,516,"Core:",10,AMB,700)); P.append(t(130,516,"pure Python standard library + SQLite + a browser UI -> runs on any Windows (and old Python).",9,SUB,400))
s,_=wrap(60,540,"Python: Win7 -> 3.8 (last supported); Vista -> 3.4, or just run a PRE-BUILT index from the portable build (search/viewer/104th need only stdlib). Install Poppler + Tesseract for Windows on legacy OS; the probe (render_backend / ocr_backend) reports what's present and what to add.",184,9,SUB,12); P.append(s)

# honesty
P.append(box(40,604,1100,72,PANEL,GRN,12,1))
P.append(t(58,628,"THE ONE HONEST LIMIT",12,GRN,700))
s,_=wrap(58,648,"NVIDIA GPU acceleration is Win10+ only (CUDA/onnxruntime don't exist for Vista/7) — but it's a SPEED booster, not a feature. OCR still completes on Vista/7 via Tesseract and the searchable result is the same. Nothing a user can do is missing on the older OSes.",184,9.4,SUB,13); P.append(s)
P.append(t(40,H-8,"BUILT diagram. Dark (R3). v0.37.0 · 2026-06-02 · companion: SYSTEM-REQUIREMENTS.md.",9.2,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/51-complete-compat-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"), "bytes ->", base+".pdf")
