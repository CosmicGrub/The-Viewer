#!/usr/bin/env python3
"""PROPOSAL: retroactive pre-support — comparable responsiveness on legacy Windows (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,940
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
P.append(t(40,46,"PROPOSAL — Retroactive post-support: comparable responsiveness on legacy Windows",20,TXT,700))
P.append(t(40,70,"Responsiveness != horsepower. Do the heavy work ONCE on the fast PC; the legacy box serves a finished artifact and does only light work. Daily use feels just as snappy.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# Panel 1: the key idea (compute once, serve light)
P.append(t(56,116,"1 · THE KEY MOVE — split heavy (once) from light (every day)",12,ACC,700))
P.append(box(40,126,1100,150,PANEL,LINE,12))
P.append(box(60,150,300,100,"#13241c",GRN,8)); P.append(t(210,172,"ONE-TIME, on the RTX 4050 PC",10,"#bfe6cf",700,"middle"))
for i,d in enumerate(["index + OCR (PP-OCRv5, GPU)","correlations, enrichment","pre-render page-image cache"]):
    P.append(t(78,192+i*16,"• "+d,8.8,"#8fbf9f",400))
P.append(arrow(360,200,470,200,TEAL)); P.append(t(415,192,"copy the",8.4,SUB,400,"middle")); P.append(t(415,214,"portable folder",8.4,SUB,400,"middle"))
P.append(box(478,150,300,100,P2,ACC,8,1)); P.append(t(628,172,"LEGACY BOX (Win7/Vista)",10,ACC,700,"middle"))
for i,d in enumerate(["serves a FINISHED viewer.db","search = SQLite FTS (instant)","open page = read a cached PNG"]):
    P.append(t(496,192+i*16,"• "+d,8.8,SUB,400))
P.append(box(796,150,324,100,P2,LINE,8)); P.append(t(958,172,"no heavy compute on the old PC",9.4,AMB,700,"middle"))
s,_=wrap(812,190,"It never OCRs or re-indexes. It just reads a small set of rows and a pre-made image. That is why it can feel as fast as the modern machine for everyday use.",46,8.6,SUB,11); P.append(s)

# Panel 2: the techniques
P.append(t(56,300,"2 · COMPATIBILITY-BASED ENHANCEMENTS (help the old PC without slowing it)",12,ACC,700))
P.append(box(40,310,1100,300,PANEL,LINE,12))
techs=[("Pre-rendered page cache","Opening a page becomes a disk read of a ready PNG, not a live PDF rasterise. Bake the common pages on the fast PC; warm the rest on first view.",GRN),
       ("ES5 / polyfilled 'legacy UI'","Old default browsers (IE11 on Win7, old Firefox) can't run modern JS. A transpiled ES5 bundle + a fetch->XMLHttpRequest shim makes the UI run on them. (Or ship Firefox ESR, which still supports Win7/Vista.)",AMB),
       ("SQLite tuned for low RAM / HDD","Set cache_size, mmap, and read patterns for spinning disks + small memory so search stays quick on a 2008-era machine.",ACC),
       ("Lite render + lite effects","Lower default DPI; local-only loupe (no server hi-DPI fetch); drop costly CSS (heavy 3D tilt, shadows). Same features, lighter touch.",ACC),
       ("Lean transport","gzip responses + keep-alive + lazy thumbnails = less disk/IO churn; snappier first paint on slow storage.",TEAL),
       ("Optional: split DBs","A tiny metadata/parts/NSN DB for instant browse + the big FTS DB only when full-text searching — keeps the common path light.",SUB)]
x=60;y=332
for i,(h,d,c) in enumerate(techs):
    bx=60 if i%2==0 else 600; by=332+(i//2)*92
    P.append(box(bx,by,520,82,PANEL,c,10,1)); P.append(f'<rect x="{bx}" y="{by}" width="6" height="82" rx="3" fill="{c}"/>')
    P.append(t(bx+18,by+22,h,11,TXT,700)); s,_=wrap(bx+18,by+40,d,86,8.8,SUB,11.5); P.append(s)

# Panel 3: two modes + expected feel
P.append(t(56,634,"3 · TWO MODES (auto-picked by the probe, manually overridable)",12,ACC,700))
P.append(box(40,644,1100,160,PANEL,LINE,12))
P.append(box(60,664,510,120,"#13241c",GRN,8)); P.append(t(80,686,"Performance mode  (Win10/11, RTX 4050)",10.5,"#bfe6cf",700))
s,_=wrap(80,706,"GPU OCR (PP-OCRv5), full effects, server hi-DPI loupe, high DPI, zoom/tilt/mirror, HD. Everything on.",70,9,SUB,12); P.append(s)
P.append(t(80,754,"Goal: maximum fidelity + speed.",9,GRN,700))
P.append(box(610,664,510,120,P2,ACC,8,1)); P.append(t(630,686,"Retroactive Post-Support mode  (Win7/Vista)",10.5,ACC,700))
s,_=wrap(630,706,"Finished portable index, page cache, ES5 UI, tuned SQLite, lite effects, Poppler+Tesseract. Same features, tuned to feel instant.",70,9,SUB,12); P.append(s)
P.append(t(630,754,"Goal: comparable RESPONSIVENESS on old hardware.",9,ACC,700))

# expected feel table
P.append(box(40,814,1100,86,PANEL,LINE,12))
P.append(t(58,836,"EXPECTED FEEL (everyday tasks)",11,AMB,700))
cells=[("Task","Modern RTX","Legacy + this plan"),("Search (FTS)","~50 ms","~120-200 ms (still instant)"),
       ("Open a page","~100 ms","~120 ms from cache (vs ~600 ms live)"),("Type-ahead / browse","instant","instant (stdlib + SQLite)")]
for r,row in enumerate(cells):
    yy=856+r*0  # single row layout
for i,(a,b,cc) in enumerate(cells):
    xx=58+i*0
y0=854
for r,(a,b,c) in enumerate(cells):
    P.append(t(60, y0+r*14, a, 8.8, (SUB if r==0 else TXT), 700 if r==0 else 400))
    P.append(t(360, y0+r*14, b, 8.8, (SUB if r==0 else GRN), 400))
    P.append(t(620, y0+r*14, c, 8.8, (SUB if r==0 else GRN), 400))
P.append(t(40,H-10,"PROPOSAL — your call. Dark (R3). Companion to SYSTEM-REQUIREMENTS.md. Nothing built yet; pick the pieces to implement.",9.2,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/52-retro-support-proposal"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"), "bytes ->", base+".pdf")
