#!/usr/bin/env python3
"""BUILT 0.59.0: OCR-driven Smart Collections — living saved-query groups that auto-fill from the text
layer; definitions in a read-only-safe sidecar (no OCR contention). Batch 1 of 3. (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,610
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
def arrow(x1,y1,x2,y2,color=SUB):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.6" marker-end="url(#ah)"/>')
P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
P.append(f'<defs><marker id="ah" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="{SUB}"/></marker></defs>')
P.append(box(0,0,W,H,BG,BG,0))
P.append(t(40,46,"BUILT — OCR-driven Smart Collections  (v0.59.0)   ·  Batch 1 of 3",19,TXT,700))
P.append(t(40,70,"A collection is a saved search that evaluates LIVE against the full-text index — so it fills itself as OCR turns image-only pages into text. Nothing is materialized; nothing re-scans.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# --- flow row: OCR -> trigger -> FTS -> live query -> collection view ---
fy=108
P.append(box(40,fy,210,96,PANEL,AMB,12)); P.append(t(58,fy+26,"🔤  OCR fills a page",12,TXT,700))
s,_=wrap(58,fy+46,"writes body_text on a previously blank, image-only page (source='ocr').",34,9,SUB,11); P.append(s)
P.append(box(286,fy,210,96,PANEL,TEAL,12)); P.append(t(304,fy+26,"⚙  FTS trigger fires",12,TXT,700))
s,_=wrap(304,fy+46,"pages_au AFTER UPDATE OF body_text re-syncs pages_fts instantly — no rebuild.",34,9,SUB,11); P.append(s)
P.append(box(532,fy,210,96,PANEL,PUR,12)); P.append(t(550,fy+26,"🔎  Collection re-queries",12,TXT,700))
s,_=wrap(550,fy+46,"each collection is just a pages_fts MATCH, run read-only at view time.",34,9,SUB,11); P.append(s)
P.append(box(778,fy,362,96,PANEL,ACC,12)); P.append(t(796,fy+26,"🗂  /collections — count & hits grow on their own",12,TXT,700))
s,_=wrap(796,fy+46,"The card's live count ticks up and new pages appear in the list the next time it's opened — automatically, as the scan proceeds.",58,9,SUB,11); P.append(s)
P.append(arrow(250,fy+48,286,fy+48)); P.append(arrow(496,fy+48,532,fy+48)); P.append(arrow(742,fy+48,778,fy+48))

# --- panels ---
def panel(x,y,w,h,ic,title,color,rows,metric):
    out=[box(x,y,w,h,PANEL,LINE,12), f'<rect x="{x}" y="{y}" width="6" height="{h}" rx="3" fill="{color}"/>']
    out.append(t(x+20,y+24,ic+"  "+title,12.5,TXT,700)); yy=y+44
    for r in rows:
        out.append(f'<circle cx="{x+24}" cy="{yy-3}" r="3" fill="{color}"/>'); s,n=wrap(x+36,yy,r,int((w-58)/5.2),8.7,SUB,11); out.append(s); yy+=3+n*11
    out.append(box(x+16,y+h-30,w-32,22,P2,color,6,1)); out.append(t(x+26,y+h-15,metric,8.8,color,700))
    return "".join(out)
py=224
P.append(panel(40,py,360,200,"🗂","Built-in + saved collections",AMB,
  ["Six built-in seeds ship in code: Warnings & Cautions, Torque specs, Wiring & schematics, Hydraulics, Lubrication & PMCS, Removal & installation.",
   "Save your own from any search terms (same OR / phrase syntax as the main box).",
   "Built-ins can be hidden (reversible); saved ones can be deleted."],
  "AUTO-FILLS as OCR adds text — no re-scan, no materialized rows."))
P.append(panel(412,py,360,200,"🛡","Sidecar = zero OCR contention",GRN,
  ["Definitions live in collections.db — its OWN file and lock, like correlations.db / reviews.db.",
   "Listing & evaluating are READ-ONLY on the index (WAL → reads never block the OCR writer).",
   "Saving/deleting writes only the sidecar, never the main index (R1/R6).",
   "If the sidecar is absent, the six seeds still work."],
  "Safe to use WHILE the scan runs — batches never overlap."))
P.append(panel(784,py,356,200,"⚡","Fast & legacy-safe",TEAL,
  ["List counts are BOUNDED (COUNT over a LIMIT 2000 subquery) so the page stays quick on the multi-GB index; shows '2000+' when capped.",
   "Click a hit → opens that exact page with the term highlighted (reuses the /page hl render).",
   "Page is ES5-safe (XHR, var, no arrow/template) + rps.js — full RPS/legacy parity."],
  "Bounded counts · highlighted jump · IE11-ready."))

P.append(box(40,448,1100,80,PANEL,GRN,12,1))
P.append(t(58,470,"VERIFIED — AND IT GROWS ON ITS OWN",11.5,GRN,700))
s,_=wrap(58,488,"Isolation test on a temp index with the real FTS triggers: a blank page was OCR-filled mid-test; the 'Warnings' count went 1→2 and 'Wiring' 0→1 with NO reindex, and the OCR'd page appeared in the live results — exactly the auto-fill behaviour. Save / delete / seed-hide against the sidecar all pass. collections.html JS is syntax-clean and ES5-clean (0 arrow fns, 0 template literals). Server functions + GET/POST routes confirmed on the host.",186,9.2,SUB,12.5);P.append(s)
P.append(t(40,H-12,"BUILT diagram. Dark (R3). v0.59.0 · 2026-06-02 · viewer_app.py (smart_collections_* + /collections + /api/collections) · ui/collections.html · sidecar collections.db. Additive (R1/R6).",9,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/73-smart-collections-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"), "bytes")
