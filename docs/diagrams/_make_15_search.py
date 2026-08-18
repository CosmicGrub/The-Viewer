#!/usr/bin/env python3
"""Generate 15-search-upgrades.svg + .pdf (dark, R3). Data-flow for the 0.14.0 search upgrades."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,720
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def arrow(x1,y1,x2,y2,col="#9aa5b1"): return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="1.7" fill="none" marker-end="url(#a)"/>'
P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
P.append('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9aa5b1"/></marker></defs>')
P.append(box(0,0,W,H,BG,BG,0))
P.append(t(40,50,"THE VIEWER — Search upgrades: Last-4 + smarter key terms",24,TXT,700))
P.append(t(40,76,"v0.14.0 · Last-4 NSN/NIIN lookup (cover/end-item) · synonyms · part#/FIG/callout · All/Any · offline fuzzy. Additive (R1).",12,SUB,400))
P.append(f'<line x1="40" y1="92" x2="{W-40}" y2="92" stroke="{LINE}"/>')

# Query box
P.append(box(40,112,1100,52,PANEL,LINE,12))
P.append(t(60,143,"Query  (one box)  →  GET /api/search?q=…&any=0|1&mode=text?",13,ACC,700))
P.append(t(720,143,'examples:  "gasket"   "FIG 7"   "5330-01-186"   "2202"   "altenator"',11,SUB,400))
P.append(arrow(590,164,590,186))

# Router
P.append(box(40,186,1100,46,P2,LINE))
P.append(t(60,214,"Router decides the mode from the query shape:",12,TXT,700))
P.append(t(430,214,"exactly 4 digits → Last-4   ·   ≥11 NSN digits → exact NSN   ·   else → key-term search",11,SUB,400))

# three lanes
lanes=[
 (40,"LAST-4  (4 digits)", ACC, [
   ("Match COVER / end-item NSN", "documents WHERE nsn LIKE '%2202'"),
   ("Classify part vs vehicle (FSC)", "banner: 'LAST-4 •2202 · N manuals'"),
   ("Escape hatch button", "'Search all manuals for 2202' → mode=text (FTS body)"),
 ]),
 (415,"FULL NSN  (≥11 digits)", GRN, [
   ("Exact phrase match in pages", 'pages_fts MATCH "2920 01 449 2202"'),
   ("+ cover-NSN match", "documents WHERE nsn = …"),
   ("Vehicle NSN → breakdown hub", "(unchanged from 0.10)"),
 ]),
 (790,"KEY TERMS  (everything else)", AMB, [
   ("Synonyms (extensible JSON)", "gasket → seal · packing · o-ring"),
   ("Fuzzy / typo (fts5vocab, edit-dist 1)", "altenator → alternator"),
   ("part# / FIG / callout precision", "5330-01-186 → adjacent phrase · fig→figure"),
   ("All (AND)  vs  Any (OR) toggle", "per-word groups combined either way"),
 ]),
]
for x,title,acc,rows in lanes:
    w=345; y=252; h=300
    P.append(box(x,y,w,h,PANEL,LINE,12))
    P.append(f'<rect x="{x}" y="{y}" width="{w}" height="30" rx="12" fill="{P2}" stroke="{LINE}"/>')
    P.append(t(x+14,y+20,title,12,acc,700))
    yy=y+44
    for head,desc in rows:
        bh=52
        P.append(box(x+16,yy,w-32,bh,P2,LINE))
        P.append(t(x+28,yy+21,head,11.5,TXT,700))
        P.append(t(x+28,yy+39,desc,9.8,SUB,400))
        yy+=bh+8
    P.append(arrow(x+w/2,232,x+w/2,252,acc))

# build_match → FTS5
P.append(box(40,572,1100,58,PANEL,LINE,12))
P.append(t(60,596,"build_match()  →  one FTS5 MATCH expression  →  ranked results  →  smart-results cards (filters/counts)",12,ACC,700))
P.append(t(60,617,'e.g.  ("gasket"* OR "seal" OR "packing")  AND  ("7"*)        ·  ANY mode flattens every alternative into one OR',10.5,SUB,400))
P.append(arrow(212,552,212,572,ACC)); P.append(arrow(587,552,587,572,GRN)); P.append(arrow(962,552,962,572,AMB))

P.append(t(40,H-14,"Cover-NSN-only Last-4 (your call) keeps false positives low; the escape hatch reaches part NSNs in body text. Dark+PDF (R3) · CHANGELOG 0.14.0 (R4) · visual panel (R5).",10,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/15-search-upgrades"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote 15-search-upgrades .svg/.pdf", os.path.getsize(base+".pdf"),"bytes")
