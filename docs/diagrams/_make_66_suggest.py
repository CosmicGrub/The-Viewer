#!/usr/bin/env python3
"""BUILT 0.49.0: type-ahead predictive search (offline) (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,560
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
P.append(t(40,46,"BUILT — Type-ahead predictive search  (v0.49.0)",19,TXT,700))
P.append(t(40,70,"Google-style suggestions as you type — but fully offline, so it's instant. Strengthens the core 'predictive search' goal.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
# sources
P.append(t(56,116,"1 · WHERE THE SUGGESTIONS COME FROM  (/api/suggest — prefix, ranked)",12,ACC,700))
P.append(box(40,126,1100,150,PANEL,LINE,12))
src=[("Vehicles",PUR,"distinct vehicle names (cached 5 min) — jump straight to a platform"),
     ("Parts",AMB,"item names previously requested (your own catalog of real parts)"),
     ("Manual words",TEAL,"real terms from the pages via the FTS vocab table, ranked by frequency — typo-free, on-topic")]
x=58
for nm,c,d in src:
    P.append(box(x,150,348,108,P2,c,10,1));P.append(t(x+12,172,nm,10.5,c,700));s,_=wrap(x+12,192,d,54,8.6,SUB,11);P.append(s);x+=360
P.append(t(58,300,"Ranked vehicles → parts → words; deduped; 8 shown. All from indexed columns / the FTS vocab — no scan, no network. Debounced 120 ms; ↑/↓ to choose, Enter to search.",8.8,GRN,400))
# mock dropdown
P.append(t(56,332,"2 · IN THE SEARCH BOX",12,ACC,700))
P.append(box(40,342,1100,120,PANEL,LINE,12))
P.append(box(58,360,420,30,"#1f2733",LINE,6));P.append(t(70,380,"alt",12,TXT,400))
P.append(box(58,392,420,62,PANEL,ACC,8,1))
P.append(t(72,410,"🔩  ALTERNATOR ASSEMBLY",11,TXT,400));P.append(t(458,410,"PART",8.5,SUB,700,"end"))
P.append(t(72,430,"🔎  alternator",11,TXT,400));P.append(t(458,430,"TERM",8.5,SUB,700,"end"))
P.append(t(72,448,"🚛  M1083 ALT…",11,TXT,400));P.append(t(458,448,"VEHICLE",8.5,SUB,700,"end"))
s,_=wrap(510,376,"Selecting a suggestion fills the box and runs the search. The dropdown closes on Escape, blur, or an outside click; keyboard-navigable and screen-reader labelled (role=combobox/listbox).",92,9.2,SUB,13);P.append(s)
# grounded
P.append(box(40,476,1100,62,PANEL,GRN,12,1))
P.append(t(58,498,"GROUNDED & ADDITIVE (R1/R6)",11.5,GRN,700))
s,_=wrap(58,516,"Read-only over existing indexes (vocab + vehicles + request history) — nothing written, no scan. Verified on a synthetic FTS5 vocab DB: 'alt'→ALTERNATOR/alternator, 'hmmwv'→vehicle, ranking vehicles>parts>words. New /api/suggest route only; rollback = remove it + the dropdown. JS lints clean.",186,9.2,SUB,12.5);P.append(s)
P.append(t(40,H-12,"BUILT diagram. Dark (R3). v0.49.0 · 2026-06-02 · suggest() in viewer_app.py + /api/suggest + index.html type-ahead dropdown.",9,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/66-suggest-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1180)
print("wrote", os.path.getsize(base+".pdf"), "bytes")
