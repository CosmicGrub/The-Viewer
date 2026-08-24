#!/usr/bin/env python3
"""PROPOSAL: circuit editor + real-time simulator + logic + net-extraction bridge (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,1180
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"; TEAL="#1d9e75"; PUR="#7f77dd"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def arrow(x1,y1,x2,y2,col="#9aa5b1",dash=""): return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="1.6" fill="none" marker-end="url(#a)"/>'
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
P.append(t(40,46,"PROPOSAL — Interactive schematics: editor + real-time circuit simulator + logic + net-extraction",19,TXT,700))
P.append(t(40,70,"How EveryCircuit / Scheme-it / LucidChart / Falstad CircuitJS actually work, and how to bring it into THE VIEWER — grounded, offline, on the current specs.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# References
P.append(t(56,114,"1 · HOW THE REFERENCE TOOLS WORK",12,ACC,700))
P.append(box(40,124,1100,150,PANEL,LINE,12))
refs=[("EveryCircuit","Real-time custom MNA engine + nonlinear device models. Transient/AC/DC. Tune a knob and it re-solves live; current animates as moving charges; per-node waveform scopes; digital wires colour-coded.",GRN),
      ("Falstad CircuitJS1","Open-source (GPLv2) browser simulator (GWT->JS) with OFFLINE standalone builds. Same live animation + scopes + analog & digital. Embeddable via iframe — the fastest path to a working sim.",ACC),
      ("Digi-Key Scheme-it","Browser schematic CAPTURE: 700+ symbols (+millions via catalog), BOM manager, export SVG/PDF/KiCAD. Drawing + parts, NOT a simulator.",AMB),
      ("LucidChart / Scheme-it style editor","Drag-place symbols, wire them, snap-to-grid, properties — the 'digitally manipulatable schematic' authoring surface.",PUR),
      ("SINA / Netlistify (research)","Deep-learning image->netlist: component detection + connectivity (CCL) + OCR + VLM. SINA ~96% accuracy, open-source. This is the BRIDGE from a raster TM schematic to a simulatable netlist.",TEAL)]
y=144
for nm,d,c in refs:
    P.append(f'<circle cx="58" cy="{y-3}" r="3.5" fill="{c}"/>'); P.append(t(70,y,nm,9.8,c,700)); s,n=wrap(280,y,d,128,8.8,SUB,11); P.append(s); y+=12+n*11

# Architecture
P.append(t(56,300,"2 · ARCHITECTURE FOR THE VIEWER (three layers + a bridge)",12,ACC,700))
P.append(box(40,310,1100,250,PANEL,LINE,12))
# layer boxes
P.append(box(60,332,330,200,P2,PUR,10,1)); P.append(t(75,354,"A · SCHEMATIC EDITOR / CAPTURE",10,PUR,700))
for i,d in enumerate(["Canvas (SVG/Canvas) + symbol library","drag-place parts · draw/route wires · grid snap","properties panel + values + BOM","data model = a NETLIST (nodes, components)","export SVG / PDF / netlist","FULLY OFFLINE, doable now"]):
    P.append(t(75,374+i*18,"• "+d,8.6,SUB,400))
P.append(box(404,332,330,200,P2,ACC,10,1)); P.append(t(419,354,"B · REAL-TIME SIMULATOR",10,ACC,700))
for i,d in enumerate(["engine solves the netlist each step","tune a parameter -> instant re-solve","animate current (moving dots) + node colours","scopes: per-node V/I waveforms","DC · AC sweep · transient","Option 1: embed CircuitJS (GPLv2, fast)","Option 2: custom MNA engine (no-GPL, tight)"]):
    P.append(t(419,374+i*18,"• "+d,8.6,SUB,400))
P.append(box(748,332,372,200,P2,GRN,10,1)); P.append(t(763,354,"C · DYNAMIC LOGIC RENDERING",10,GRN,700))
for i,d in enumerate(["digital gates / flip-flops / buses","event-driven 0/1 propagation (light)","colour-coded logic states + bus values","clock stepping + timing-diagram scopes","truth tables on hover","pairs with the analog engine"]):
    P.append(t(763,374+i*18,"• "+d,8.6,SUB,400))
P.append(t(60,548,"All three are client-side JS — no server load; the RTX 4050 is far more than enough (the sim is light).",8.8,GRN,400))

# the sim loop
P.append(t(56,584,"3 · HOW THE REAL-TIME SIM WORKS (the numerical heart — EveryCircuit / SPICE / CircuitJS)",12,ACC,700))
P.append(box(40,594,1100,180,PANEL,LINE,12))
steps=[("Build the matrix","Modified Nodal Analysis: assemble G·v = i from the netlist (one equation per node)."),
       ("Stamp components","Each R/L/C/diode/transistor/source 'stamps' its contribution; L/C use companion models per timestep."),
       ("Solve (nonlinear)","Newton-Raphson iterates until the nonlinear devices (diodes, transistors) converge."),
       ("Integrate time","Trapezoidal / backward-Euler advance one dt; repeat ~real-time for a smooth animation."),
       ("Animate + tune","Map node voltages->colours, branch currents->moving-dot speed; a slider edits a value and re-solves live.")]
x=58
for i,(h,d) in enumerate(steps):
    P.append(box(x,616,205,116,P2,LINE,8)); P.append(t(x+10,636,str(i+1)+" "+h,9.4,TXT,700)); s,_=wrap(x+10,652,d,33,8.2,SUB,10); P.append(s)
    if i<4: P.append(arrow(x+205,672,x+213,672,ACC))
    x+=214

# the bridge
P.append(t(56,800,"4 · THE BRIDGE — from a real TM schematic to a simulatable netlist",12,ACC,700))
P.append(box(40,810,1100,150,PANEL,LINE,12))
br=[("raster TM schematic","the real scanned/vector page in the library"),
    ("detect components","vision model (YOLO-style) finds relays, resistors, connectors…"),
    ("trace connectivity","line-following / connected-components builds the wires + nodes"),
    ("OCR + VLM labels","ref-designators, values, pin IDs assigned (SINA-style)"),
    ("netlist","-> load straight into the editor + simulator")]
x=58
for i,(h,d) in enumerate(br):
    col=GRN if i==0 else (TEAL if i<4 else ACC)
    P.append(box(x,832,205,72,P2,col,8,1)); P.append(t(x+10,852,h,9.2,TXT,700)); s,_=wrap(x+10,868,d,34,8.0,SUB,10); P.append(s)
    if i<4: P.append(arrow(x+205,868,x+213,868,col))
    x+=214
P.append(t(58,930,"On the 4050: inference works for component/line detection. Bigger models + batching all 1,093 schematics + any fine-tuning -> the desktop/RTX 5070 (12 GB). This is the one 'needs-power' piece.",8.8,AMB,400))

# grounding + recommendation
P.append(box(40,978,1100,96,PANEL,RED,12,1))
P.append(t(58,1002,"THE GROUNDING LINE",12,RED,700))
s,_=wrap(58,1022,"The editor + simulator are GROUNDED when YOU build/edit a circuit — your input is the source of truth (great for training: 'what happens if this relay coil opens?'). An AUTO-extracted netlist from a TM raster MUST be shown for review/edit and labelled 'auto-extracted — verify against the TM' before it's trusted; the cited TM page always sits alongside. We never present a simulated result as the manual's ground truth without that human check.",184,9.4,SUB,13); P.append(s)
P.append(box(40,1082,1100,80,PANEL,GRN,12,1))
P.append(t(58,1106,"RECOMMENDED PATH",12,GRN,700))
s,_=wrap(58,1126,"1) Build the schematic EDITOR (capture + netlist + BOM, offline) — immediate value. 2) Add the SIMULATOR by embedding Falstad CircuitJS (GPLv2, offline) to validate UX fast, then optionally a custom MNA engine for tight integration + no-GPL distribution. 3) Logic rendering. 4) The net-extraction BRIDGE last (the power feature). All on the 4050 except heavy extraction.",184,9.4,SUB,13); P.append(s)
P.append(t(40,H-12,"PROPOSAL — your call. Dark (R3). Nothing built yet. Sources: everycircuit.com · falstad CircuitJS (GPLv2) · digikey Scheme-it · SINA/Netlistify.",9,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/58-circuitsim-proposal"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"), "bytes")
