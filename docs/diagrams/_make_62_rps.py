#!/usr/bin/env python3
"""BUILT 0.45.0: Retroactive Post-Support (RPS) — comparable speed on old/slow PCs (dark R3)."""
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
P.append(t(40,46,"BUILT — Retroactive Post-Support (RPS)  (v0.45.0)",19,TXT,700))
P.append(t(40,70,"A Windows-11 program that stays responsive all the way back to Windows 7 / Vista — by auto-adapting to the machine, not by dropping features. Corpus & index untouched.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# decision
P.append(t(56,116,"1 · ONE PROBE → ONE MODE (auto, overridable)",12,ACC,700))
P.append(box(40,126,1100,150,PANEL,LINE,12))
P.append(box(60,150,200,100,P2,PUR,10,1));P.append(t(75,172,"sysprobe.py",10,PUR,700))
for i,d in enumerate(["OS rank · RAM · cores","render backend (PyMuPDF","/ Poppler) · GPU · Python"]):P.append(t(75,192+i*15,d,8.4,SUB,400))
P.append(arrow(262,200,300,200,PUR))
modes=[("modern",GRN,"capable + Win10/11","full effects · server hi-fi loupe · prefetch 2 · big SQLite cache"),
       ("lite",AMB,"modern OS, weak HW","effects off · DPI 120 · local loupe · small cache (low-RAM/HDD)"),
       ("legacy",ACC,"Win7/Vista / Poppler","lite + ES5 polyfills + Poppler render + minimal SQLite footprint")]
x=305
for nm,c,when,what in modes:
    P.append(box(x,150,265,100,P2,c,10,1));P.append(t(x+13,172,nm,11,c,700));P.append(t(x+70,172,"· "+when,8.2,SUB,400))
    s,_=wrap(x+13,190,what,42,8.2,SUB,11);P.append(s);x+=275
P.append(t(60,268,"mode_for(profile, override) → modern | lite | legacy. Force with --mode or ?mode= ; the choice drives every switch below.",8.6,GRN,400))

# the five levers
P.append(t(56,304,"2 · WHAT EACH MODE ACTUALLY CHANGES",12,ACC,700))
P.append(box(40,314,1100,210,PANEL,LINE,12))
lev=[("Page-render cache","index/pagecache/ — a full-page PNG is rendered ONCE then served from disk. Pre-bake hot pages ( --prebake N ) and warm-on-view renders the next page(s) in a background thread. The single biggest win on a slow HDD.",TEAL),
     ("SQLite tuning","per-mode PRAGMAs on every connection: big mmap + MEMORY temp on modern; tiny cache, mmap off, FILE temp on legacy/low-RAM. Read-only — the index is never rewritten.",ACC),
     ("Render path","PyMuPDF when present; Poppler (pdftoppm) auto-substituted on Win7/Vista. DPI capped per mode (400 / 220 / 150) so an old GPU-less box isn't asked to rasterise huge pages.",AMB),
     ("ES5 polyfills","rps.js feature-detects and shims fetch / Promise / Object.assign / Array & String helpers / URLSearchParams so the modern UI runs on old Firefox ESR / IE11. No-ops on modern browsers.",PUR),
     ("Lite effects","off the modern path, animations & transitions are disabled (body.rps-lite/legacy) and the loupe stays local — the UI feels instant instead of janky.",GRN)]
y=338
for nm,d,c in lev:
    P.append(f'<circle cx="58" cy="{y-3}" r="3.5" fill="{c}"/>');P.append(t(70,y,nm,9.8,c,700));s,n=wrap(230,y,d,128,8.6,SUB,11);P.append(s);y+=8+n*11

# grounding
P.append(box(40,548,1100,90,PANEL,GRN,12,1))
P.append(t(58,572,"COMPLETE compatibility, not a cut-down build (R1/R6)",12,GRN,700))
s,_=wrap(58,592,"RPS keeps the FULL feature set working back to Win7/Vista via engine substitution + adaptation — it changes HOW things run, never WHAT the manual says. Everything is additive and read-only: the page cache is a regenerable sidecar, the SQLite pragmas are connection-local, the polyfills are client-side. Rollback = delete index/pagecache and ignore rps.py. The dual-track changelog records exactly what each legacy version carries vs adapts.",184,9.4,SUB,13);P.append(s)
# tested
P.append(box(40,650,1100,76,PANEL,LINE,12))
P.append(t(58,672,"VERIFIED",11,ACC,700))
s,_=wrap(58,690,"rps.py logic: 13/13 unit tests pass — mode decision (Nitro 5→modern, Win7/Poppler→legacy, 6 GB→lite, override wins/ignored-if-bad), feature flags, cache keys distinct by dpi/flags, cache round-trip, prebake renders then skips already-cached. Server-side cache/tuning/warm blocks compile & run; rps.js lints clean.",184,9,SUB,12);P.append(s)
P.append(t(40,H-12,"BUILT diagram. Dark (R3). v0.45.0 · 2026-06-02 · engine/rps.py + sysprobe.py + viewer_app.py + engine/ui/rps.js. Reminder: boost with the desktop later (RTX 5070).",9,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/62-rps-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1180)
print("wrote", os.path.getsize(base+".pdf"), "bytes")
