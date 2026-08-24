#!/usr/bin/env python3
"""BUILT 0.61.0: Smart Collections enhancements — scope to vehicle/manual-type, 'new since last visit'
badge, one-click save-as + pin, group results + printable bay sheet. (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,600
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"
ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; TEAL="#1d9e75"; PUR="#7f77dd"
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
P.append(t(40,46,"BUILT — Smart Collections, four add-ons  (v0.61.0)",19,TXT,700))
P.append(t(40,70,"You asked for these in plain terms. All still read-only on the index, sidecar-only writes — safe to use while the OCR scan runs.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
def panel(x,y,w,h,ic,title,color,rows,metric):
    out=[box(x,y,w,h,PANEL,LINE,12), f'<rect x="{x}" y="{y}" width="6" height="{h}" rx="3" fill="{color}"/>']
    out.append(t(x+20,y+24,ic+"  "+title,12.5,TXT,700)); yy=y+44
    for r in rows:
        out.append(f'<circle cx="{x+24}" cy="{yy-3}" r="3" fill="{color}"/>'); s,n=wrap(x+36,yy,r,int((w-58)/5.2),8.7,SUB,11); out.append(s); yy+=3+n*11
    out.append(box(x+16,y+h-30,w-32,22,P2,color,6,1)); out.append(t(x+26,y+h-15,metric,8.8,color,700))
    return "".join(out)
P.append(panel(40,108,553,184,"🚚","Filter to one vehicle / manual",AMB,
  ["A saved collection can be scoped to a vehicle (e.g. M1097) and/or a kind of manual (Operator -10, Maintenance -20/-24, Parts/RPSTL, Lubrication, Schematics, Troubleshooting).",
   "Manual-type matched with GLOB on a trailing boundary so '-20' lands on the TM's level code, NOT on the stock-class digits inside 9-2320 (that bug was caught + fixed in test).",
   "Scope pickers populate from a live vehicle list."],
  "Less scrolling past the trucks/books you don't need."))
P.append(panel(604,108,553,184,"🆕","Show what's new",TEAL,
  ["Because a collection auto-fills as OCR runs, it can tell you what newly turned up: a green +N new badge.",
   "Opening a collection records its current size; next time, the badge shows how many pages appeared since.",
   "Baseline stored in a tiny collection_seen sidecar table (one row per collection) — never the main index."],
  "A passive 'what just became searchable in my area' feed."))
P.append(panel(40,300,553,184,"📌","Save a search in one click + pin",PUR,
  ["A 📌 Save as collection button on the main results bar turns the search you just ran into a collection — name it and go.",
   "Pin (★) your most-used collections; pinned float to the top of the grid.",
   "All sidecar-only; pinning works for built-ins too (stores a row carrying their values)."],
  "Capture a good search; keep favourites on top."))
P.append(panel(604,300,553,184,"🖨","Group + take-to-bay sheet",ACC,
  ["Group a collection's hits by vehicle or by manual so a long list is easy to scan.",
   "Print take-to-bay sheet builds a clean grouped table (vehicle · manual · page · excerpt) in a new window and prints it.",
   "Pulls up to 500 hits; uses the same live results."],
  "Carry the list out to the work bay on paper."))
P.append(box(40,504,1116,72,PANEL,GRN,12,1))
P.append(t(58,526,"VERIFIED",11.5,GRN,700))
s,_=wrap(58,544,"Scope isolation test on a temp index: operator (-10) manuals are correctly EXCLUDED from the Maintenance filter (the old LIKE '%-23%' wrongly matched 9-2320 — now fixed with a boundary GLOB); Parts resolves to -24P; vehicle scope narrows as expected. 'New' badge: opening set the baseline, an OCR-filled page then showed +1. collections.html JS syntax-clean and ES5-clean (0 arrow fns, 0 template literals); the main-page save button block syntax-checks. Server fns + pin route confirmed on host.",188,9.2,SUB,12.5);P.append(s)
P.append(t(40,H-12,"BUILT diagram. Dark (R3). v0.61.0 · 2026-06-02 · viewer_app.py (scope/seen/pin/facets) · collections.html · index.html (📌). Sidecar-only (R1/R6).",9,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/75-collections-plus-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"), "bytes")
