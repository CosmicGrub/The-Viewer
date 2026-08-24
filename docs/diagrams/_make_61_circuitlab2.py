#!/usr/bin/env python3
"""BUILT 0.44.0: Circuit Lab deepened — active devices + save/load/export + part linking (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,720
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"
ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"; TEAL="#1d9e75"; PUR="#7f77dd"
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
P.append(t(40,46,"BUILT — Circuit Lab, deepened  (v0.44.0)",19,TXT,700))
P.append(t(40,70,"Active devices, save / load / export, and parts that link to the catalog — on the same validated MNA engine. Still an overlay on the real schematic.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# new devices
P.append(t(56,116,"1 · NEW ACTIVE DEVICES (all unit-tested in the engine)",12,ACC,700))
P.append(box(40,126,1100,168,PANEL,LINE,12))
dev=[("AC source","time-varying sine V(t)=A·sin(2πft); drives real transient/ringing demos",AMB),
     ("MOSFET (N-ch)","square-law level-1, Newton-solved; switches & amplifies (on: drain→0.02 V)",TEAL),
     ("Op-amp","ideal high-gain VCVS; non-inverting ×2 gives exactly 2.000 V",PUR),
     ("Relay","behavioral coil + contact; 12 V energizes the 120 Ω coil → contact CLOSES → lamp lights",GRN)]
x=58
for i,(h,d,c) in enumerate(dev):
    bx=x;P.append(box(bx,150,256,128,P2,c,10,1));P.append(t(bx+12,172,h,10.5,c,700));s,_=wrap(bx+12,192,d,42,8.6,SUB,11);P.append(s)
    x+=268
P.append(t(58,288,"Relays matter for vehicle electrical systems — coils and contacts are everywhere in the wiring TMs.",8.8,GRN,400))

# the enablers
P.append(t(56,326,"2 · WHAT MADE IT POSSIBLE + THE NEW WORKFLOW",12,ACC,700))
P.append(box(40,336,545,250,PANEL,LINE,12))
P.append(t(58,360,"Generalised N-pin model",10.5,TXT,700))
for i,d in enumerate(["Parts now carry a pin-offset table (not just 2 leads)","rotation rotates the offsets; union-find still assigns nodes","3-pin (MOSFET, op-amp) and 4-pin (relay) devices just work","netlist() emits each device in the engine's pin order"]):
    P.append(t(58,380+i*18,"• "+d,8.8,SUB,400))
P.append(t(58,462,"8 demo circuits",10.5,TXT,700))
for i,d in enumerate(["divider · RC · RLC · diode+LED","AC+RC · MOSFET switch · relay-driven lamp · op-amp ×2","each validated end-to-end (build→netlist→solve)"]):
    P.append(t(58,482+i*18,"• "+d,8.8,SUB,400))

P.append(box(604,336,536,250,PANEL,LINE,12))
P.append(t(622,360,"Save / load / export",10.5,TXT,700))
for i,d in enumerate(["💾 Save / 📂 Load — persists in the browser (localStorage)","⬇ .json — download the full circuit; ⬆ import it back","⬇ netlist — SPICE-style .cir (R/C/L/V/SIN/D/M/relay notes)","portable: share a circuit as a file, reopen it anywhere"]):
    P.append(t(622,380+i*18,"• "+d,8.8,SUB,400))
P.append(t(622,462,"Parts link to the catalog",10.5,AMB,700))
s,_=wrap(622,482,"Tag any component with a TM part # / NSN. It shows on the symbol and is a one-click jump to the Look-Alike Parts recognizer (/partdiff) — so a drawn relay or resistor connects straight to the real cataloged part and its variants.",80,8.8,SUB,12);P.append(s)

# grounding
P.append(box(40,604,1100,100,PANEL,GRN,12,1))
P.append(t(58,628,"GROUNDED & ADDITIVE (R1/R6) · RPS (R7)",12,GRN,700))
s,_=wrap(58,648,"Same validated MNA core (all 10 unit tests pass: divider/RC/diode/RLC + AC/MOSFET/op-amp/relay). The circuit is grounded in what you build; the simulator never rewrites the TM and the cited sheet stays behind the overlay. Save/export are local files — nothing leaves the machine. RPS: still a modern-browser feature; the Win7/Vista legacy build keeps the static-overlay fallback. Fully additive — same routes, richer editor.",184,9.4,SUB,13);P.append(s)
P.append(t(40,H-12,"BUILT diagram. Dark (R3). v0.44.0 · 2026-06-02 · engine/ui/circuitlab.html + circuitsim.js. Engine: 10/10 unit tests pass.",9,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/61-circuitlab2-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"), "bytes")
