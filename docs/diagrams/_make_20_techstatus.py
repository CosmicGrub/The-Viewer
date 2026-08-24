#!/usr/bin/env python3
"""Proposal markup: auto-derive Tech Status from fault + part, grounded in PMCS criteria (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,900
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def arrow(x1,y1,x2,y2,col="#9aa5b1"): return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="1.7" fill="none" marker-end="url(#a)"/>'
def wrap(x,y,s,width,size,fill,dy=15,wt=400):
    out=[]; words=s.split(); line=""; ln=0
    for wd in words:
        if len(line)+len(wd)+1>width: out.append(t(x,y+ln*dy,line,size,fill,wt)); line=wd; ln+=1
        else: line=(line+" "+wd).strip()
    if line: out.append(t(x,y+ln*dy,line,size,fill,wt))
    return "".join(out), ln+1
P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
P.append('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9aa5b1"/></marker></defs>')
P.append(box(0,0,W,H,BG,BG,0))
P.append(t(40,46,"Auto-deriving Tech Status from the fault + part — proposal",22,TXT,700))
P.append(t(40,70,"Grounded in the TM's PMCS 'Not Fully Mission Capable If' criteria. Required & filled before the sheet generates. Decide before we build.",11.5,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# HOW IT'S DECIDED (left)
P.append(box(40,104,690,168,PANEL,LINE,12))
P.append(t(58,128,"HOW TECH STATUS IS ACTUALLY DECIDED",12,ACC,700))
s,_=wrap(58,150,"A fault either deadlines the vehicle or it doesn't. The TM's PMCS 'NOT FULLY MISSION CAPABLE IF' column is the authority — it states exactly which faults make the vehicle non-mission-capable.",98,10,SUB); P.append(s)
# mapping chips
my=200
maps=[("Deadline fault + waiting on the part","NMCS","#5a2330"),
      ("Deadline fault, in maintenance","NMCM","#5a2330"),
      ("Degrades but mission-capable","PMC","#5a4a1e"),
      ("No mission impact","FMC","#1e3a26")]
x=58
for lbl,code,col in maps:
    bw=160
    P.append(box(x,my,bw,52,col,LINE,8))
    P.append(t(x+bw/2,my+22,code,13,TXT,700,"middle"))
    s,_=wrap(x+8,my+38,lbl,26,8,SUB,11); P.append(s)
    x+=bw+8
P.append(t(58,266,"Since this is a PARTS request (waiting on supply), a deadline fault most often → NMCS.",9.5,AMB,400))

# DATA PROOF (right)
P.append(box(748,104,392,168,PANEL,LINE,12))
P.append(t(766,128,"THE DATA IS IN YOUR CORPUS",12,GRN,700))
proof=[("‘Not Fully Mission Capable If’","381 pages"),("PMCS tables","1,158 pages"),("‘mission capable’","439 pages")]
yy=150
for a,b in proof:
    P.append(box(766,yy,356,30,P2,LINE,7))
    P.append(t(778,yy+20,a,10.5,TXT,400)); P.append(t(1110,yy+20,b,10.5,"#bfe6c5",700,"end"))
    yy+=37
P.append(t(766,yy+12,"(sample index of 45k pages — the full index is ~40× larger)",9,SUB,400))

# THREE SIGNAL SOURCES
P.append(t(40,300,"SIGNAL SOURCES  (combine for confidence)",12,AMB,700))
sigs=[
 ("A · PMCS-grounded (authoritative)",GRN,
  "Search the vehicle's PMCS pages for the fault/part terms; read the matched 'Not Fully Mission Capable If' line and cite it verbatim.",
  "Doctrinally correct + cited. Coverage depends on OCR (partial now, grows)."),
 ("B · Keyword rules (works today)",ACC,
  "Offline deadline-term classifier: e.g. no-start / steering / brakes / Class III leak → likely NMC; gauge / lamp / cosmetic → PMC-FMC. Extensible JSON.",
  "Instant, offline, no OCR needed. Approximate — a starting guess only."),
 ("C · Learned from history",AMB,
  "Same fault + part on past sessions → the tech status the mechanic confirmed before. Improves with use (like the parts learning).",
  "Gets smarter over time. Empty on a fresh install."),
]
cw=355; gap=17; x0=40; y=316
for i,(h,acc,d,note) in enumerate(sigs):
    x=x0+i*(cw+gap)
    P.append(box(x,y,cw,160,PANEL,LINE,11))
    P.append(f'<rect x="{x}" y="{y}" width="5" height="160" rx="2" fill="{acc}"/>')
    P.append(t(x+18,y+26,h,11.5,TXT,700))
    s,n=wrap(x+18,y+48,d,50,9.6,SUB,15); P.append(s)
    s,_=wrap(x+18,y+48+n*15+8,note,52,9,"#7c8696",13); P.append(s)

# PIPELINE
py=512
P.append(t(40,py-6,"RECOMMENDED PIPELINE  ·  propose with evidence → mechanic confirms (mandatory) → onto the sheet",12,ACC,700))
steps=[("Fault + parts on the request","the inputs"),
       ("A → B → C","PMCS evidence, else rules, else history"),
       ("SUGGEST status + cite","e.g. NMCS — 'NOT FMC IF: service brakes inoperative' (TM 9-2320-327-10)"),
       ("MANDATORY confirm at export","mechanic accepts or overrides — sheet won't generate while blank"),
       ("TECH STATUS on the 104th","filled, every time")]
bw=205; gap2=18; x=40; yb=py+8
for i,(h,d) in enumerate(steps):
    P.append(box(x,yb,bw,92,P2,LINE))
    s,n=wrap(x+12,yb+22,h,28,10.5,TXT,13,700); P.append(s)
    s,_=wrap(x+12,yb+22+n*13+6,d,32,8.6,SUB,11); P.append(s)
    if i<len(steps)-1: P.append(arrow(x+bw,yb+46,x+bw+gap2,yb+46, AMB if i==2 else "#9aa5b1"))
    x+=bw+gap2
P.append(box(40+3*(bw+gap2),yb-6,bw,104,"none","#6b5526",10,2))  # highlight the confirm gate
P.append(t(40+3*(bw+gap2)+bw/2,yb+104,"the gate that guarantees it's always set",8.5,AMB,400,"middle"))

# RESPONSIBILITY + RECS
ry=672
P.append(box(40,ry,560,180,PANEL,LINE,12))
P.append(t(58,ry+24,"WHY A CONFIRM GATE (not silent auto-fill)",12,RED,700))
s,_=wrap(58,ry+48,"Tech status is a formal readiness call with real consequences. The app should PROPOSE it with cited evidence and require a human to confirm — never silently decide, and never invent a deadline. It stays a faithful, cited determination (the project's safety stance).",70,10,SUB); P.append(s)
s,_=wrap(58,ry+128,"It is still MANDATORY: the sheet will not generate with Tech Status blank, so it's always present by the end — just human-confirmed.",70,10,AMB); P.append(s)

P.append(box(620,ry,520,180,PANEL,LINE,12))
P.append(t(638,ry+24,"RECOMMENDATION",12,ACC,700))
recs=["Hybrid: A (PMCS, cited) → B (rules) → C (history), best evidence wins.",
      "Suggest + mandatory confirm at 'Generate sheet' — pre-filled, editable, blocks if blank.",
      "Use full codes (FMC / PMCM / PMCS / NMCM / NMCS); parts-request defaults toward the supply (S) code.",
      "Ship the keyword-rule pack first (works now); PMCS-cited evidence strengthens as OCR completes."]
yy=ry+46
for r in recs:
    P.append(t(638,yy,"•",10,ACC,700)); s,n=wrap(652,yy,r,76,9.6,SUB,13); P.append(s); yy+=n*13+8
P.append(t(40,H-12,"Proposal only — nothing built yet. Dark (R3). On approval: data-flow diagram (R2), CHANGELOG (R4) + visual panel (R5).",10,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/20-tech-status-proposal"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
