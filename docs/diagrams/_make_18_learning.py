#!/usr/bin/env python3
"""Proposal markup: self-learning predictive search + cleaner modal (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,840
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def arrow(x1,y1,x2,y2,col="#9aa5b1"): return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="1.7" fill="none" marker-end="url(#a)"/>'
P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
P.append('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9aa5b1"/></marker></defs>')
P.append(box(0,0,W,H,BG,BG,0))
P.append(t(40,46,"Self-learning search + a calmer modal — proposal",22,TXT,700))
P.append(t(40,70,"Surface what you already log. Decide before we build. (Fault is already mandatory — no change needed there.)",11.5,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# ---- the learning loop ----
P.append(t(40,116,"THE LEARNING LOOP  ·  no new plumbing — request_items already captures every end-to-end success",12,ACC,700))
loop=[("Generate 104th sheet","every part the mechanic actually requested"),
      ("request_items (the log)","nsn · nomenclature · part# · created_at — already stored"),
      ("/api/popular","rank by frequency + recency (NSN & nomenclature)"),
      ("Rotating example + quick-picks","one clean, real example that rotates; 'commonly requested' chips"),
      ("Faster next search","the parts your shop reaches for surface first")]
n=len(loop); bw=196; gap=18; x0=40; y=132
for i,(h,d) in enumerate(loop):
    x=x0+i*(bw+gap)
    P.append(box(x,y,bw,70,P2,LINE))
    P.append(t(x+12,y+24,h,11,TXT,700) if len(h)<26 else t(x+12,y+22,h,10.2,TXT,700))
    # wrap desc 2 lines
    words=d.split(); line=""; ln=0
    for wd in words:
        if len(line)+len(wd)+1>30: P.append(t(x+12,y+40+ln*13,line,8.6,SUB,400)); line=wd; ln+=1
        else: line=(line+" "+wd).strip()
    if line: P.append(t(x+12,y+40+ln*13,line,8.6,SUB,400))
    if i<n-1: P.append(arrow(x+bw,y+35,x+bw+gap,y+35))
# loop-back arrow
P.append(arrow(x0+ (n-1)*(bw+gap)+bw/2, y+72, x0+bw/2, y+72, "#5d6675"))
P.append(t((x0+ (n-1)*(bw+gap)+bw/2 + x0+bw/2)/2, y+88, "learns & retains (offline, in your index)", 9, "#7c8696", 400, "middle"))

# ---- before / after search field ----
ax,aw=40,560; ay=260
P.append(box(ax,ay,aw,150,PANEL,LINE,12))
P.append(f'<rect x="{ax}" y="{ay}" width="{aw}" height="28" rx="12" fill="{P2}" stroke="{LINE}"/>')
P.append(t(ax+14,ay+19,"SEARCH FIELD  ·  fewer examples, one that rotates",12,GRN,700))
P.append(t(ax+18,ay+48,"BEFORE — 4 static examples (busy):",9.5,SUB,700))
P.append(box(ax+18,ay+56,aw-36,30,"#232c39",LINE,7))
P.append(t(ax+28,ay+75,"What do you need? e.g. gasket · 5330-01-186-9023 · 2202 …",10,"#7c8696",400))
P.append(t(ax+18,ay+108,"AFTER — one real example, rotates each open:",9.5,SUB,700))
P.append(box(ax+18,ay+116,aw-36,30,"#16223a","#2c3f5e",7))
P.append(t(ax+28,ay+135,"ALTERNATOR, DUAL VOLTAGE · 2920-01-449-2202",10.5,"#9bc0ff",400))
P.append(t(ax+aw-26,ay+135,"↻",13,AMB,700,"end"))

# cold start note
P.append(box(ax,ay+162,aw,70,PANEL,LINE,12))
P.append(t(ax+16,ay+186,"Cold start (new install):",10.5,AMB,700))
P.append(t(ax+16,ay+206,"a small curated seed list (battery, gasket, alternator, fuel filter w/ real",9.6,SUB,400))
P.append(t(ax+16,ay+220,"NSNs) shows first, then quietly shifts to YOUR common parts as they log.",9.6,SUB,400))

# ---- recommendations ----
rx,rw=620,520; ry=260
P.append(t(rx,ry-6,"RECOMMENDATIONS",12,ACC,700))
recs=[
 ("1 · Learn from successful sheets","Aggregate request_items (your end-to-end log) by NSN + nomenclature, weighted by frequency and recency. No migration.",GRN),
 ("2 · Rotating example, not a list","Show ONE clean example in the field; pick a random common item each open. Calmer, and it teaches by showing real format.",GRN),
 ("3 · 'Commonly requested' quick-picks","A thin row of 4-5 learned chips on Home / under search — tap to search. Subtle, not hand-holding.",GRN),
 ("4 · Predictive stays as-is, ranked","Keep live FTS typeahead; just boost learned-popular hits to the top. No intrusive dropdown.",ACC),
 ("5 · Trim the copy","Shorter modal subtitle + one-line hint. Let the rotating example do the explaining.",AMB),
 ("6 · Optional: also learn searches","Add an opt-in search log later for broader signal (noisier). Start with high-signal successful sheets only.",SUB),
]
cw=520; y=ry+8
for i,(h,d,acc) in enumerate(recs):
    yy=y+i*92
    P.append(box(rx,yy,cw,82,PANEL,LINE,10))
    P.append(f'<rect x="{rx}" y="{yy}" width="5" height="82" rx="2" fill="{acc}"/>')
    P.append(t(rx+18,yy+24,h,12,TXT,700))
    words=d.split(); line=""; ln=0
    for wd in words:
        if len(line)+len(wd)+1>72: P.append(t(rx+18,yy+44+ln*16,line,9.6,SUB,400)); line=wd; ln+=1
        else: line=(line+" "+wd).strip()
    if line: P.append(t(rx+18,yy+44+ln*16,line,9.6,SUB,400))

P.append(t(40,H-14,"Proposal only — nothing built yet. Offline & private (stays in your index). Dark (R3). On approval: data-flow diagram (R2), CHANGELOG (R4) + visual panel (R5).",10,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/18-learning-search-proposal"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
