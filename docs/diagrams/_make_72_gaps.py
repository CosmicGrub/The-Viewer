#!/usr/bin/env python3
"""BUILT 0.58.0: gap-closing optimization pass — OCR dedup/adaptive DPI, legacy memory + cold-start
warmup, Circuit Lab MNA → Web Worker, loupe neighbour-prefetch + result hover-prefetch (dark R3)."""
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
P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
P.append(box(0,0,W,H,BG,BG,0))
P.append(t(40,46,"BUILT — Gap-closing optimization pass  (v0.58.0)",19,TXT,700))
P.append(t(40,70,"Four gaps the speed passes hadn't touched: the OCR build, weak-PC startup, the live simulator, and the page/loupe round-trips. Each closed additively.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
def panel(x,y,w,h,ic,title,color,rows,metric):
    out=[box(x,y,w,h,PANEL,LINE,12), f'<rect x="{x}" y="{y}" width="6" height="{h}" rx="3" fill="{color}"/>']
    out.append(t(x+20,y+24,ic+"  "+title,12.5,TXT,700)); yy=y+44
    for r in rows:
        out.append(f'<circle cx="{x+24}" cy="{yy-3}" r="3" fill="{color}"/>'); s,n=wrap(x+36,yy,r,int((w-58)/5.2),8.7,SUB,11); out.append(s); yy+=3+n*11
    out.append(box(x+16,y+h-30,w-32,22,P2,color,6,1)); out.append(t(x+26,y+h-15,"RESULT: "+metric,8.8,color,700))
    return "".join(out)
P.append(panel(40,108,553,190,"🔎","OCR build — dedup + adaptive DPI",AMB,
  ["A density probe skips blank pages; identical rendered pages are md5-hashed and the OCR result is REUSED instead of re-inferred.",
   "Sparse pages render at a lower adaptive DPI (160 floor) — opt-in via --adaptive so accuracy is never silently traded.",
   "Batch log now reports dedup_reused. Corpus stays read-only (R1); applies on the next pass."],
  "Fewer GPU inferences per batch (dup pages reuse one result)."))
P.append(panel(604,108,553,190,"🧊","Legacy memory + cold-start warmup",TEAL,
  ["RPS now sizes the open-PDF LRU per mode (modern 8 / lite 3 / legacy 2) so a low-RAM PC keeps a small footprint.",
   "After rps_init the server warms the path (SELECT 1 + COUNT + one page) so the FIRST real request isn't the one paying for parse + cache fill.",
   "Per-mode SQLite cache/mmap unchanged; reversible."],
  "Smaller legacy footprint; first request no longer cold."))
P.append(panel(40,310,553,190,"🧵","Circuit Lab MNA → Web Worker",PUR,
  ["The continuous RUN loop's matrix solve now runs in circuitsim-worker.js, OFF the main thread; the page renders from posted snapshots so a heavy circuit can't stutter the UI.",
   "Edit / DC / single-Step stay inline + synchronous (unchanged). A WorkerSim shim exposes v()/i()/state() so draw() is untouched.",
   "Guaranteed inline fallback if Workers are absent or error (no breakage, R1)."],
  "Run-loop math off the UI thread (validated; inline fallback)."))
P.append(panel(604,310,553,190,"⚡","Loupe + result hover-prefetch",ACC,
  ["Hovering a search result warms its page render (debounced, de-duped) so the click opens from cache instantly.",
   "The loupe already upscales locally with zero latency; it now also prefetches the 4 neighbouring crisp crops so a slow drag stays sharp instead of flashing soft-then-sharp.",
   "Pure client-side; no new API surface."],
  "Click-to-open feels instant; loupe drag stays crisp."))
P.append(box(40,518,1116,64,PANEL,GRN,12,1))
P.append(t(58,540,"NO OVERBUILD — EACH GAP CLOSED IN PLACE, FALLBACKS INTACT",11.5,GRN,700))
s,_=wrap(58,558,"None of these add a page or an API to learn. The OCR and startup wins are server-side and reversible; the Worker and prefetch wins are client-side with the original synchronous/inline paths kept as guaranteed fallbacks. Worker + shim validated in isolation (node --check + a mock-Worker run: init/dc/step posted, snapshots drawn, inline rebuilt on stop); hover-prefetch dedup + URL verified. 23 pillars green; viewer_app imports clean.",188,9.2,SUB,12.5);P.append(s)
P.append(t(40,H-10,"BUILT diagram. Dark (R3). v0.58.0 · 2026-06-02 · viewer_ingest.py · rps.py/viewer_app.py warmup · circuitsim-worker.js + circuitlab.html · index.html. Additive (R1/R6).",9,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/72-gap-closing-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"), "bytes")
