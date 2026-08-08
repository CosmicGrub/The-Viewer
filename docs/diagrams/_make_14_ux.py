#!/usr/bin/env python3
"""Generate 14-ux-dynamic-frontend.svg + .pdf (dark, R3). Data-flow for the 0.13.0 UX pass."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,760
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}"/>'
def txt(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def arrow(x1,y1,x2,y2): return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="#9aa5b1" stroke-width="1.7" fill="none" marker-end="url(#a)"/>'
P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
P.append('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9aa5b1"/></marker></defs>')
P.append(box(0,0,W,H,BG,BG,0))
P.append(txt(40,50,"THE VIEWER — Dynamic front-end UX pass",24,TXT,700))
P.append(txt(40,76,"v0.13.0 · Home/browse-by-vehicle · smart results (filters+counts) · viewer zoom/thumbnails/highlight · responsive+touch+large-text. All additive (R1).",12,SUB,400))
P.append(f'<line x1="40" y1="92" x2="{W-40}" y2="92" stroke="{LINE}"/>')

# Column headers
def panel(x,y,w,h,title,acc=ACC):
    P.append(box(x,y,w,h,PANEL,LINE,12))
    P.append(f'<rect x="{x}" y="{y}" width="{w}" height="30" rx="12" fill="{P2}" stroke="{LINE}"/>')
    P.append(txt(x+14,y+20,title,12,acc,700))

# 1. Browser app (client) toggles
panel(40,110,330,150,"CLIENT  ·  preferences (localStorage)")
P.append(box(58,150,140,34)); P.append(txt(128,172,"A+  large text",11,TXT,600,"middle"))
P.append(box(212,150,140,34)); P.append(txt(282,172,"Simple / Advanced",11,TXT,600,"middle"))
P.append(box(58,196,294,30)); P.append(txt(205,216,"recent searches (viewer_recent_q)",11,SUB,400,"middle"))
P.append(txt(58,246,"Persist across launches · CSS classes body.big / body.simple",10,SUB,400))

# 2. HOME
panel(40,280,330,250,"HOME  ·  browse-by-vehicle + recents")
P.append(box(58,322,294,46)); P.append(txt(70,342,"Vehicle grid + filter box",11.5,TXT,600)); P.append(txt(70,358,"GET /api/vehicles  → name · #manuals · NSN",10,SUB,400))
P.append(box(58,376,294,40)); P.append(txt(70,393,"Recent searches (chips)",11.5,TXT,600)); P.append(txt(70,408,"from localStorage → click re-runs search",10,SUB,400))
P.append(box(58,424,294,44)); P.append(txt(70,442,"Recent parts requests",11.5,TXT,600)); P.append(txt(70,457,"GET /api/sessions → bumper · fault · #items",10,SUB,400))
P.append(txt(58,496,"Shown whenever the search box is empty.",10,SUB,400))
P.append(txt(58,512,"Click a vehicle → vehicle hub.",10,SUB,400))

# 3. SEARCH + SMART RESULTS
panel(410,110,360,420,"SEARCH  →  SMART RESULTS")
P.append(box(428,150,324,38)); P.append(txt(440,174,"Type query  →  GET /api/search (FTS5 / NSN)",11,TXT,600))
P.append(arrow(590,188,590,206))
P.append(box(428,208,324,70,P2,LINE)); P.append(txt(440,228,"Build facets (client-side, from results):",11,ACC,700))
P.append(txt(440,246,"• vehicle counts   • manual type (classifyType)",10.5,SUB,400))
P.append(txt(440,262,"• Text vs OCR source   • result count N of M",10.5,SUB,400))
P.append(arrow(590,278,590,296))
P.append(box(428,298,324,40,P2,LINE)); P.append(txt(440,323,"Filter bar: clickable chips toggle filters",11,TXT,600))
P.append(arrow(590,338,590,356))
P.append(box(428,358,324,150,P2,LINE)); P.append(txt(440,378,"Result cards (filtered view)",11,ACC,700))
P.append(txt(440,398,"vehicle · type · TM · NSN · page · OCR badge",10.5,SUB,400))
P.append(txt(440,416,"snippet w/ <mark> hit   →  View page / Add",10.5,SUB,400))
P.append(box(440,430,300,30,"#1f2733",LINE,7)); P.append(txt(450,449,"NSN banner → vehicle? open full breakdown hub",10,"#bcd4ff",400))
P.append(txt(440,486,"Predictive (offline FTS5) · exact NSN bypass preserved.",10,SUB,400))

# 4. VIEWER
panel(810,110,330,420,"DOCUMENT VIEWER  ·  zoom · thumbnails · highlight",GRN_:=ACC)
P.append(box(828,150,294,58)); P.append(txt(840,170,"Zoom  −/100%/+",11.5,TXT,600)); P.append(txt(840,188,"DPIS[90..340] → /page?dpi= re-render (sharp)",10,SUB,400))
P.append(box(828,216,294,66)); P.append(txt(840,236,"Highlight the hit  🖍",11.5,TXT,600)); P.append(txt(840,254,"/page?hl=term → PyMuPDF page.search_for()",10,SUB,400)); P.append(txt(840,270,"draws yellow boxes on the text layer",10,SUB,400))
P.append(box(828,290,294,72)); P.append(txt(840,310,"Thumbnail strip  ▦",11.5,TXT,600)); P.append(txt(840,328,"window ±8 pages · /page?dpi=24 lazy",10,SUB,400)); P.append(txt(840,344,"click jumps · current highlighted",10,SUB,400))
P.append(box(828,370,294,68,"#1f2733",LINE)); P.append(txt(840,390,"Schematics & install panel (kept)",11.5,"#bfe6c5",700)); P.append(txt(840,408,"cited FIG → page → vehicle schematic set",10,SUB,400)); P.append(txt(840,424,"verbatim & cited — never invented",10,SUB,400))
P.append(txt(828,462,"Prev/Next · arrow keys · Esc · Add this part.",10,SUB,400))
P.append(txt(828,478,"On phones the panel stacks below; thumbs hidden.",10,SUB,400))

# server lane
P.append(box(40,560,1100,120,PANEL,LINE,12))
P.append(txt(60,584,"SERVER  ·  viewer_app.py  (additive endpoints, no schema change)",12,ACC,700))
for i,(ep,desc) in enumerate([
    ("GET /api/vehicles","distinct vehicles + #manuals + NSN (browse)"),
    ("GET /api/sessions","recent request sessions (bumper · fault · items)"),
    ("GET /page?…&hl=","PyMuPDF search_for → highlight boxes, then render"),
    ("GET /api/search","unchanged · GET /api/vehicle hub unchanged"),
]):
    x=60+i*272
    P.append(box(x,600,250,62,P2,LINE))
    P.append(txt(x+12,622,ep,11,TXT,700))
    P.append(txt(x+12,642,desc,9.5,SUB,400))
# arrows client->server
P.append(arrow(205,530,205,560))
P.append(arrow(590,530,590,560))
P.append(arrow(975,530,975,560))
P.append(txt(40,H-14,"Dark (R3) · ships with PDF · backwards-compatible & rollbackable (R1) · accompanies CHANGELOG 0.13.0 (R4) + visual panel (R5).",10,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/14-ux-dynamic-frontend"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
print("wrote 14-ux-dynamic-frontend.svg +.pdf", os.path.getsize(base+".pdf"),"bytes")
