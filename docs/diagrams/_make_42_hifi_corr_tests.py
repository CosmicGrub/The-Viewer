#!/usr/bin/env python3
"""BUILT 0.28.0: hi-fi loupe (clip render) + correlations sidecar + pillar/mutation tests (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,860
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
P.append(t(40,46,"BUILT — Hi-fi loupe · correlations · pillar + mutation tests  (v0.28.0)",20,TXT,700))
P.append(t(40,70,"The loupe now re-rasterises the REAL page region at high DPI (sharp at any zoom). Correlations the flat tables implied are connected in a deletable sidecar. The pillars are tested + mutation-checked.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# --- Panel 1: hi-fi loupe flow ---
P.append(t(56,116,"1 · HIGH-FIDELITY LOUPE (server clip render)",12,ACC,700))
P.append(box(40,126,1100,148,PANEL,LINE,12))
steps=[("Cursor over page","UI computes a normalized box (x0,y0,x1,y1) around the cursor"),
       ("GET /page?clip=..&dpi=520","server renders ONLY that sub-rectangle of the real page"),
       ("PyMuPDF get_pixmap(clip,dpi)","~21x more pixels for the region vs a stretched 130-dpi crop"),
       ("1:1 crisp crop in the loupe","no CSS upscaling — fidelity increases as you zoom")]
x=60
for i,(h,d) in enumerate(steps):
    bw=250
    P.append(box(x,150,bw,104,P2,LINE,8)); P.append(t(x+12,172,str(i+1)+" · "+h,10.2,TXT,700)); s,_=wrap(x+12,190,d,40,8.8,SUB,12); P.append(s)
    if i<3: P.append(arrow(x+bw,202,x+bw+12,202,ACC))
    x+=bw+22
P.append(t(60,268,"Grounded: it's the same drawing re-rasterised at higher resolution (vector pages gain true detail; scans get best honest interpolation — nothing invented).",9,GRN,400))

# --- Panel 2: correlations sidecar ---
P.append(t(56,300,"2 · CORRELATIONS CONNECTED (additive sidecar — viewer.db untouched)",12,ACC,700))
P.append(box(40,310,1100,180,PANEL,LINE,12))
# source -> derive -> sidecar -> endpoint
P.append(box(60,330,150,52,P2,LINE,8)); P.append(t(135,352,"viewer.db",10.5,TXT,700,"middle")); P.append(t(135,368,"(read-only)",9,SUB,400,"middle"))
P.append(arrow(210,356,236,356,TEAL))
P.append(box(240,330,210,52,P2,LINE,8)); P.append(t(345,350,"build_correlations.py",9.6,TXT,700,"middle")); P.append(t(345,366,"set-math derive",8.8,SUB,400,"middle"))
P.append(arrow(450,356,476,356,TEAL))
P.append(box(480,326,200,60,"#13241c",GRN,8)); P.append(t(580,346,"correlations.db",10,"#bfe6cf",700,"middle")); P.append(t(580,362,"3.6 MB sidecar",8.8,"#8fbf9f",400,"middle")); P.append(t(580,376,"delete = rollback",8.4,"#8fbf9f",400,"middle"))
P.append(arrow(680,356,706,356,TEAL))
P.append(box(710,330,200,52,P2,LINE,8)); P.append(t(810,350,"/api/correlations",9.6,ACC,700,"middle")); P.append(t(810,366,"(only if present)",8.8,SUB,400,"middle"))
# three findings cards
cards=[("19,511 NSNs","span >1 vehicle — top part fits 33 platforms / 396 docs",GRN),
       ("884 NIIN drifts","same NIIN, 2 NSN strings — flagged for review, not merged",AMB),
       ("311 supersessions","old → current where we hold both sides",ACC)]
x=60
for h,d,acc in cards:
    P.append(box(x,402,346,76,PANEL,acc,11,1)); P.append(f'<rect x="{x}" y="402" width="6" height="76" rx="3" fill="{acc}"/>')
    P.append(t(x+18,424,h,12.5,TXT,700)); s,_=wrap(x+18,442,d,52,9.2,SUB,12); P.append(s)
    x+=360

# --- Panel 3: tests + mutation ---
P.append(t(56,516,"3 · PILLAR TESTS + MUTATION TESTING",12,ACC,700))
P.append(box(40,526,1100,250,PANEL,LINE,12))
# pillars list
P.append(t(60,550,"17 / 17 pillar tests pass",13,GRN,700))
pill=["NSN parse + routing","keyword FTS","fuzzy typo (dist-1)","AND precision","last-4 + full-NSN",
      "parts lookup (cited)","reference enrichment (+R6 versions)","tech-status (PMCS+history+codes)",
      "coverage meter","correlations sidecar","104th sheet PDF (%PDF)"]
y=570
for i,pp in enumerate(pill):
    cx=60+(i%2)*270
    if i%2==0 and i>0: y+=21
    P.append(t(cx,y,"✓ "+pp,9.6,SUB,400))
y+=30
# mutation flow
P.append(t(60,y,"Mutation testing — 100% kill rate (15 / 15)",13,GRN,700)); y+=20
P.append(box(60,y,250,44,P2,LINE,8)); P.append(t(72,y+18,"inject 1 fault",10,TXT,700)); P.append(t(72,y+33,"into core_pillars.py",8.6,SUB,400))
P.append(arrow(310,y+22,336,y+22,RED))
P.append(box(340,y,250,44,P2,LINE,8)); P.append(t(352,y+18,"re-run 17 pillar tests",10,TXT,700)); P.append(t(352,y+33,"against the mutant",8.6,SUB,400))
P.append(arrow(590,y+22,616,y+22,RED))
P.append(box(620,y,250,44,"#13241c",GRN,8)); P.append(t(632,y+18,"a test fails = KILLED",10,"#bfe6cf",700)); P.append(t(632,y+33,"all pass = survivor (gap)",8.6,"#8fbf9f",400))
P.append(box(890,y,230,44,P2,AMB,8,1)); P.append(t(902,y+18,"2 equivalent mutants",9.4,AMB,700)); P.append(t(902,y+33,"found + replaced",8.6,SUB,400))
y+=64
s,_=wrap(60,y,"Faults injected: flip the FSC vehicle test · AND→OR in search · last-4→last-3 · disable the NSN path · flip 'confidence IS NOT NULL' · wrong tech-status code · offset coverage % · hide interchangeability · reorder tech codes. Every one was caught.",184,9.2,SUB,13); P.append(s)

P.append(t(40,H-12,"BUILT diagram. Dark (R3). v0.28.0 · 2026-06-02 · companions: CONGRUENCY-AND-TESTS.md, loupe-fidelity-demo.png.",9.4,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/42-hifi-corr-tests-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"), "bytes ->", base+".pdf")
