#!/usr/bin/env python3
"""Data-flow diagram (R2) — Retroactive Post-Support run-mode as a saved Settings choice (v1.13.2).
Dark theme (R3); emits SVG + PDF + preview PNG. Also doubles as the visual changelog panel (R5)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W, H = 1200, 720
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"
ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"; VIO="#8a7dff"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def arrow(x1,y1,x2,y2,col="#9aa5b1",dash=""):
    da=' stroke-dasharray="%s"'%dash if dash else ''
    return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="1.8" fill="none" marker-end="url(#a)"{da}/>'
def wrap(x,y,s,width,size,fill,dy=14,wt=400):
    out=[]; words=s.split(); line=""; ln=0
    for wd in words:
        if len(line)+len(wd)+1>width: out.append(t(x,y+ln*dy,line,size,fill,wt)); line=wd; ln+=1
        else: line=(line+" "+wd).strip()
    if line: out.append(t(x,y+ln*dy,line,size,fill,wt))
    return "".join(out), ln+1
P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
P.append('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9aa5b1"/></marker></defs>')
P.append(box(0,0,W,H,BG,BG,0))
P.append(t(40,46,"Retroactive Post-Support — run-mode as a saved Settings choice",22,TXT,700))
P.append(t(40,70,"v1.13.2 · sources → resolver → live feature flags · auto-pick from the hardware probe + a manual override that survives restarts (R1 additive).",11.5,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# ---- Column 1: SOURCES (precedence top→bottom) ----
cx=40; cw=300; y0=112
P.append(t(cx,y0,"SOURCES  (precedence ↓)",12,ACC,700))
srcs=[("1 · VIEWER_MODE  (env / CLI)","concrete modern|lite|legacy — wins, back-compat",VIO),
      ("2 · VIEWER_RUN_MODE  (env)","auto | performance | retro",P2),
      ("3 · index/viewer_settings.json","the Settings-panel choice — persisted (settings.py)","#1a2740"),
      ("4 · default","auto",P2)]
yy=y0+16
for hd,d,col in srcs:
    bh=60; P.append(box(cx,yy,cw,bh,col,LINE,9))
    s,_=wrap(cx+12,yy+24,hd,42,11.5,TXT,13,700); P.append(s)
    P.append(t(cx+12,yy+44,d,9.4,SUB,400)); yy+=bh+8
# sysprobe recommendation feeds the resolver too
P.append(box(cx,yy+2,cw,64,PANEL,GRN,9))
P.append(t(cx+12,yy+24,"engine/sysprobe.py",11.5,GRN,700))
s,_=wrap(cx+12,yy+42,"recommended_run_mode (Win10/11+RTX → Performance; Win7/Vista/low-RAM → Retro). Advisory.",44,9.3,SUB,12.5); P.append(s)

# ---- Column 2: RESOLVER ----
mx=380; mw=360; my=150
P.append(t(mx,y0,"RESOLVER  (pure, unit-testable)",12,ACC,700))
P.append(box(mx,my,mw,150,PANEL,ACC,12,1.4))
P.append(t(mx+16,my+28,"viewer_app.rps_init()",13,TXT,700))
s,_=wrap(mx+16,my+48,"concrete env override → rps.mode_for()  ·  otherwise → rps.mode_for_setting(profile, setting)",52,9.6,SUB,13); P.append(s)
P.append(t(mx+16,my+92,"rps.mode_for_setting()",12,VIO,700))
s,_=wrap(mx+16,my+110,"auto → hardware pick · performance → modern · retro → compat, never full-effects (still lite vs legacy by OS)",52,9.3,SUB,12.5); P.append(s)
# arrows sources -> resolver
P.append(arrow(cx+cw,y0+70,mx,my+40,ACC))
P.append(arrow(cx+cw,yy+30,mx,my+120,GRN,dash="4 3"))
# resolved mode chip
P.append(box(mx,my+168,mw,54,"#101a14",GRN,10))
P.append(t(mx+16,my+192,"RPS_MODE  +  RPS_FLAGS",12,GRN,700))
P.append(t(mx+16,my+210,"modern · lite · legacy   →   the on/off switches + tuning for this machine",9.4,SUB,400))
P.append(arrow(mx+mw/2,my+150,mx+mw/2,my+168,ACC))

# ---- Column 3: LIVE EFFECT (feature flags) ----
ex=770; ew=390; ey=112
P.append(t(ex,ey,"APPLIED LIVE  (RPS_FLAGS)",12,ACC,700))
eff=[("UI  (rps.js, ES5/ polyfilled)","effects · animations · loupe (server|local) · default DPI",P2),
     ("Render  (render_feature)","page-cache read/write + prefetch · render-DPI cap","#101a14"),
     ("SQLite  (_new_conn PRAGMAs)","cache_size · mmap_size · temp_store  (new conns; full on restart)","#1a2740")]
yy=ey+16
for hd,d,col in eff:
    bh=66; P.append(box(ex,yy,ew,bh,col,LINE,9))
    s,_=wrap(ex+12,yy+24,hd,52,11.5,TXT,13,700); P.append(s)
    s2,_=wrap(ex+12,yy+42,d,58,9.4,SUB,12.5); P.append(s2); yy+=bh+8
P.append(arrow(mx+mw,my+40,ex,ey+40,ACC))

# ---- Bottom: the manual override loop ----
by=520
P.append(box(cx,by,W-80,150,PANEL,LINE,12))
P.append(t(cx+16,by+28,"MANUAL OVERRIDE  (Settings panel → status.html)",12,AMB,700))
loop=[("Run-mode card","Auto · Performance · Retroactive Post-Support",P2),
      ("POST /api/rps_mode","{setting}",P2),
      ("viewer_app.set_run_mode()","normalize → settings.set() (durable)","#1a2740"),
      ("rps_init() re-runs","new RPS_MODE + RPS_FLAGS, no restart","#101a14"),
      ("GET /api/rps","reflects saved setting + resolved mode",P2)]
lx=cx+16
for i,(hd,d,col) in enumerate(loop):
    lw=205; P.append(box(lx,by+48,lw,74,col,LINE,9))
    s,_=wrap(lx+12,by+72,hd,30,11,TXT,13,700); P.append(s)
    s2,_=wrap(lx+12,by+94,d,32,9.2,SUB,12); P.append(s2)
    if i<len(loop)-1: P.append(arrow(lx+lw,by+85,lx+lw+18,by+85,AMB))
    lx+=lw+18
P.append(t(cx+16,by+140,"Fail-loud: set() returns saved=True/False so the UI can warn on a lost write. Fail-open on read: a corrupt settings file → auto, app still starts.",9.4,SUB,400))

P.append(t(40,H-14,"Verified: rps.mode_for unchanged; precedence env>settings>auto; additive keys only (R1/R6). Dark (R3) · CHANGELOG 1.13.2 (R4) · visual panel (R5).",9.6,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base=os.path.join(os.path.dirname(os.path.abspath(__file__)),"53-rps-run-mode-setting")
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1200)
print("wrote", base+".pdf", os.path.getsize(base+".pdf"), "bytes;  png", os.path.getsize(base+"_preview.png"))
