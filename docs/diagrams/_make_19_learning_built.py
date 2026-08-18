#!/usr/bin/env python3
"""Built data-flow: self-learning search (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,700
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def arrow(x1,y1,x2,y2,col="#9aa5b1"): return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="1.7" fill="none" marker-end="url(#a)"/>'
P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
P.append('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9aa5b1"/></marker></defs>')
P.append(box(0,0,W,H,BG,BG,0))
P.append(t(40,46,"Self-learning search — built",22,TXT,700))
P.append(t(40,70,"v0.16.0 · learns from successful 104th sheets (request_items) · rotating example · quick-picks · popularity-ranked results. Additive, no migration (R1).",11.5,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# capture
P.append(box(40,112,330,120,PANEL,LINE,12))
P.append(t(58,136,"CAPTURE (already happens)",12,GRN,700))
P.append(box(58,150,294,30,P2,LINE)); P.append(t(70,170,"POST /api/request → build the 104th PDF",10.5,TXT,400))
P.append(arrow(205,180,205,192))
P.append(box(58,194,294,30,P2,LINE)); P.append(t(70,214,"save_request → request_items (nsn · name · date)",10.2,TXT,400))

# aggregate
P.append(arrow(370,170,420,170,ACC))
P.append(box(420,112,330,120,PANEL,LINE,12))
P.append(t(438,136,"LEARN",12,ACC,700))
P.append(box(438,150,294,30,P2,LINE)); P.append(t(450,170,"GET /api/popular",10.5,"#cfe0ff",700))
P.append(box(438,186,294,38,P2,LINE)); P.append(t(450,204,"GROUP BY nsn / nomenclature,",9.8,SUB,400)); P.append(t(450,217,"rank by frequency + recency",9.8,SUB,400))

# popular store
P.append(arrow(585,232,585,256,ACC))
P.append(box(420,256,330,40,"#16223a","#2c3f5e",9)); P.append(t(585,281,"POPULAR  ·  top parts (cold-start SEED until logged)",10.5,"#9bc0ff",700,"middle"))

# three surfacings
P.append(t(40,300,"SURFACE (three ways)",12,AMB,700))
cards=[
 ("Rotating example","One real example in the search & modal field — a random common part, rotates each open. Replaces the 4 static examples.","placeholder = 'BATTERY, STORAGE · 6140-01-485-1472'"),
 ("'Commonly requested' quick-picks","A thin row of ★ chips on Home — tap to search instantly.","top 6 from POPULAR (or SEED)"),
 ("Popularity-ranked results","Keyword results you've requested before float to the top, marked ★ requested.","popular_nsns() boost · stable sort"),
]
cw=355; gap=17; x0=40; y=316
for i,(h,d,code) in enumerate(cards):
    x=x0+i*(cw+gap)
    P.append(box(x,y,cw,150,PANEL,LINE,11))
    P.append(f'<rect x="{x}" y="{y}" width="5" height="150" rx="2" fill="{AMB}"/>')
    P.append(t(x+18,y+28,str(i+1)+" · "+h,12.5,TXT,700))
    words=d.split(); line=""; ln=0
    for wd in words:
        if len(line)+len(wd)+1>46: P.append(t(x+18,y+50+ln*16,line,9.8,SUB,400)); line=wd; ln+=1
        else: line=(line+" "+wd).strip()
    if line: P.append(t(x+18,y+50+ln*16,line,9.8,SUB,400))
    P.append(box(x+16,y+112,cw-32,26,"#10151c",LINE,6))
    P.append(t(x+24,y+129,code,8.6,"#8fae8f",400))
    P.append(arrow(x+cw/2,296,x+cw/2,y,AMB))

# loop back
P.append(box(40,500,1100,46,PANEL,LINE,12))
P.append(t(60,528,"More sheets generated  →  better signal  →  the parts your shop reaches for surface first.  Offline & private (stays in your index).",12,GRN,700))
P.append(arrow(900,316+150,900,500,"#5d6675"))

P.append(t(40,H-14,"Also: search/modal copy trimmed; single rotating example does the teaching. Dark (R3) · CHANGELOG 0.16.0 (R4) · visual panel (R5).",10,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/19-learning-search-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
