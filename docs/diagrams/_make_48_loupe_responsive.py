#!/usr/bin/env python3
"""BUILT 0.34.0: tight/seamless loupe — instant local zoom + sharpen-on-pause (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,680
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
P.append(t(40,46,"BUILT — Tight, seamless loupe  (v0.34.0)",20,TXT,700))
P.append(t(40,70,"The magnifier now tracks the cursor with ZERO latency and sharpens the instant you pause — no lag, no blank frames. All accessibility toggles share one responsive feel.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# Panel 1: the two-layer model
P.append(t(56,116,"1 · INSTANT LOCAL ZOOM  +  SHARPEN-ON-PAUSE",12,ACC,700))
P.append(box(40,126,1100,250,PANEL,LINE,12))
# moving
P.append(t(80,156,"while moving",11,AMB,700))
P.append(f'<circle cx="160" cy="232" r="56" fill="#0a0e12" stroke="{ACC}" stroke-width="2"/>')
for i in range(5): P.append(f'<line x1="112" y1="{200+i*16}" x2="208" y2="{200+i*16}" stroke="#5a6675" stroke-width="2" opacity="0.6"/>')
P.append(t(160,300,"local CSS zoom of the page image",8.8,SUB,400,"middle"))
P.append(t(160,314,"follows cursor every frame (rAF) — instant, soft",8.4,GRN,400,"middle"))
P.append(arrow(240,232,300,232,TEAL)); P.append(t(270,222,"pause",8.6,SUB,400,"middle"))
# paused
P.append(t(330,156,"when you pause (60 ms)",11,GRN,700))
P.append(f'<circle cx="410" cy="232" r="56" fill="#0a0e12" stroke="{GRN}" stroke-width="2"/>')
for i in range(5): P.append(f'<line x1="362" y1="{200+i*16}" x2="458" y2="{200+i*16}" stroke="#cdd6e0" stroke-width="2.4"/>')
P.append(t(410,300,"high-DPI crop swaps in (/page?clip=…)",8.8,SUB,400,"middle"))
P.append(t(410,314,"crisp, real resolution — cached for revisits",8.4,GRN,400,"middle"))
# right: properties
P.append(box(520,150,600,200,P2,LINE,10))
props=[("rAF positioning","one transform update per frame — no layout thrash, buttery follow"),
       ("zero-latency base","local magnification shows immediately; never a blank/white loupe"),
       ("debounced fetch","the server crop is requested only when the cursor settles (60 ms)"),
       ("cell cache","crops are keyed by region+zoom; revisiting a spot is instant"),
       ("wheel to zoom","scroll over the loupe to change magnification (1.8×–6×), live"),
       ("cursor handoff","the pointer hides and the loupe becomes the cursor — seamless")]
y=176
for h,d in props:
    P.append(f'<circle cx="536" cy="{y-4}" r="3" fill="{ACC}"/>'); P.append(t(548,y,h,9.8,TXT,700)); s,_=wrap(548,y+14,d,92,8.8,SUB,11); P.append(s); y+=29

# Panel 2: unified controls
P.append(t(56,408,"2 · ALL ACCESSIBILITY CONTROLS — ONE DYNAMIC FEEL",12,ACC,700))
P.append(box(40,418,1100,180,PANEL,LINE,12))
chips=[("🧹 Clean",GRN),("contrast",SUB),("tilt Y",SUB),("tilt X",SUB),("↔ Mirror",ACC),("✦ HD",GRN),("🔎 Loupe",ACC)]
x=60
for lab,c in chips:
    w=86 if len(lab)>7 else 74
    P.append(box(x,440,w,30,"#16223a" if c in (GRN,ACC) else P2, ACC if c in (GRN,ACC) else LINE,7,1))
    P.append(t(x+w/2,460,lab,9.2,TXT if c in (GRN,ACC) else SUB,700,"middle")); x+=w+10
P.append(t(60,498,"Active toggles share a state: accent border + subtle glow; smooth .12s transitions; press feedback (scale).",9.4,SUB,400))
P.append(t(60,516,"They compose cleanly — the loupe reflects Clean/contrast in its crop; HD raises full-page DPI; tilt/mirror are CSS overlays.",9.4,SUB,400))
s,_=wrap(60,544,"All presentation-only and reversible (R1/R6): none of these touch the page data, the index, search, or the 104th sheet. The loupe is the same real drawing, re-rasterised sharper — nothing invented.",184,9.2,GRN,13); P.append(s)
P.append(t(40,H-12,"BUILT diagram. Dark (R3). v0.34.0 · 2026-06-02.",9.2,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/48-loupe-responsive-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"), "bytes ->", base+".pdf")
