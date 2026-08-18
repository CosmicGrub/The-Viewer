#!/usr/bin/env python3
"""BUILT 0.42.0: Circuit Lab — overlay editor + real-time MNA simulator (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,940
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
P.append(t(40,46,"BUILT — Circuit Lab: overlay editor + real-time circuit simulator  (v0.42.0)",19,TXT,700))
P.append(t(40,70,"Build or trace a circuit directly on top of a real TM schematic, then watch it run — a learning, advanced-viewing and display tool. 100% offline, custom MNA engine, no GPL.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# 1 — the data-flow pipeline (R2)
P.append(t(56,116,"1 · DATA FLOW — from a sheet to a live simulation",12,ACC,700))
P.append(box(40,126,1100,196,PANEL,LINE,12))
flow=[("Real TM schematic","optional backdrop: /page?doc&page rendered behind the grid, dialable opacity",PUR),
      ("Overlay editor","drop V/R/C/L/D/LED/SW/GND on a snap grid · draw wires pin->pin · tune values",ACC),
      ("Graph -> nodes","union-find merges wired & coincident pins; a Ground pin fixes node 0",TEAL),
      ("Netlist","each part becomes {type,name,n:[a,b],value} — the simulator's input",AMB),
      ("MNA engine","circuitsim.js stamps G·v=i, companion models for C/L, Newton for diodes",GRN),
      ("Live render","node colours by voltage, current as moving dots, per-node scope, logic HIGH/LOW",RED)]
x=58
for i,(h,d,c) in enumerate(flow):
    bx=x; P.append(box(bx,150,168,140,P2,c,10,1)); P.append(t(bx+12,172,str(i+1),11,c,700)); P.append(t(bx+28,172,h,9.6,TXT,700))
    s,_=wrap(bx+12,192,d,29,8.2,SUB,11); P.append(s)
    if i<5: P.append(arrow(bx+168,220,bx+180,220,c))
    x+=180
P.append(t(58,308,"The tuning loop closes here: drag a value slider -> netlist re-stamps -> engine re-solves -> the render updates live (real-time on the 4050).",8.8,GRN,400))

# 2 — the editor surface
P.append(t(56,352,"2 · THE EDITOR SURFACE",12,ACC,700))
P.append(box(40,362,545,250,PANEL,LINE,12))
P.append(t(58,386,"Tools",10.5,TXT,700))
for i,d in enumerate(["Select — move parts, click to tune value (log sliders for R/C/L)","Wire — click pin to pin, or to bare grid points","Rotate (R) / Delete (Del) / Esc to cancel","Place palette: Source, R, C, L, Diode, LED, Switch, Ground","6 demo circuits: divider, RC, RLC, rectifier, switch->lamp, logic"]):
    P.append(t(58,406+i*18,"• "+d,8.8,SUB,400))
P.append(t(58,506,"Run controls",10.5,TXT,700))
for i,d in enumerate(["▶ Run (animate transient) · DC (operating point) · Step","Speed slider sets the timestep; Show = Analog or Logic view","Scope: click any node to plot its voltage over time"]):
    P.append(t(58,526+i*18,"• "+d,8.8,SUB,400))

# 3 — what the engine solves (numerical heart)
P.append(t(620,352,"3 · WHAT THE ENGINE SOLVES (validated)",12,ACC,700))
P.append(box(604,362,536,250,PANEL,LINE,12))
tests=[("Voltage divider","2.500 V","exact"),("Ohm's law","5.00 mA","exact"),
       ("RC transient @ tau","3.159 V","<1% vs 3.161"),("Diode drop @ 4.4 mA","0.574 V","exact for Is=1e-12"),
       ("Series D + LED","3.34 mA","converges (pnjlim)"),("Underdamped RLC","overshoot->5 V","rings then settles")]
P.append(t(622,386,"Unit tests — all pass",10.5,GRN,700))
yy=406
for nm,val,note in tests:
    P.append(f'<circle cx="628" cy="{yy-3}" r="3" fill="{GRN}"/>'); P.append(t(640,yy,nm,9,TXT,600)); P.append(t(880,yy,val,9,ACC,700)); P.append(t(980,yy,note,8.4,SUB,400)); yy+=20
P.append(t(622,540,"Backward-Euler companion models for C/L; SPICE-style voltage limiting lets series",8.6,SUB,400))
P.append(t(622,554,"junctions and LEDs converge. Gaussian elimination w/ partial pivoting.",8.6,SUB,400))
P.append(t(622,584,"Dependency-free: runs as a browser global and as a Node module (how it's tested).",8.6,GRN,400))

# 4 — grounding
P.append(box(40,632,1100,128,PANEL,RED,12,1))
P.append(t(58,656,"GROUNDED — a teaching overlay, not a claim about the manual (R1/R6)",12,RED,700))
s,_=wrap(58,676,"The circuit is GROUNDED in what YOU build or trace: your placement is the source of truth — ideal for 'what happens if this relay coil opens, or this resistor doubles?'. The simulator never rewrites the TM, and the real cited sheet sits right behind the overlay. Auto-extracting a netlist straight from a raster TM (vision model) is deliberately NOT done here — that's the deferred power feature for the desktop/RTX 5070, and any such netlist would be labelled 'auto-extracted — verify against the TM' before use. Presentation-only and additive: the route is new, nothing existing changed.",184,9.4,SUB,13); P.append(s)

# 5 — RPS row (R7)
P.append(box(40,772,1100,118,PANEL,AMB,12,1))
P.append(t(58,796,"RPS — Retroactive Post-Support degradation path",12,AMB,700))
s,_=wrap(58,816,"The live simulator is a modern-browser feature; on the 4050 it runs effortlessly. On the Win7/Vista LEGACY build it degrades gracefully: the editor still draws your circuit and the real schematic still opens in the static viewer — the animation simply turns off. So Circuit Lab is logged on the modern track from 0.42.0; the legacy track records it as 'static-overlay only (no live sim)'. Backwards-compatible and rollbackable (R1): delete the /circuitlab + /circuitsim.js routes and the two link buttons to fully revert.",184,9.4,SUB,13); P.append(s)
P.append(t(40,H-14,"BUILT diagram. Dark (R3). v0.42.0 · 2026-06-02 · engine/ui/circuitlab.html + circuitsim.js + viewer_app.py routes. Sources: MNA/SPICE method; EveryCircuit/CircuitJS/Scheme-it (concept refs).",9,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/59-circuitlab-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"), "bytes pdf")
