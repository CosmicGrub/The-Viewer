#!/usr/bin/env python3
"""Assessment: authoritative military NSN data sources — PUB LOG is the answer (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,840
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def wrap(x,y,s,width,size,fill,dy=13,wt=400):
    out=[];words=s.split();line="";ln=0
    for wd in words:
        if len(line)+len(wd)+1>width: out.append(t(x,y+ln*dy,line,size,fill,wt));line=wd;ln+=1
        else: line=(line+" "+wd).strip()
    if line: out.append(t(x,y+ln*dy,line,size,fill,wt))
    return "".join(out),ln+1
P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
P.append(box(0,0,W,H,BG,BG,0))
P.append(t(40,46,"Where authoritative military NSN data comes from — assessment",21,TXT,700))
P.append(t(40,70,"You asked to assess fuller sources before pulling. Verdict: PUB LOG (DLA) — free, monthly, no CAC, public-domain — and it carries the exact fields we were missing.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
# sources ranked
srcs=[
 ("PUB LOG® (DLA)","USE THIS",GRN,
  "Publicly-releasable FLIS catalog: NSN→item name, Characteristics (CHAR), Master Cross-Reference (NSN↔part#↔CAGE), Interchangeability/Substitutability + AAC, item-name directory. Single .ZIP, updated monthly, free, no CAC.",
  "Authoritative · current · comprehensive · public-domain"),
 ("WebFLIS® (DLA)","spot checks",ACC,
  "Per-NSN web lookup (name, part numbers, suppliers). Interactive, not bulk — good for verifying one NSN.",
  "official · not a bulk fill"),
 ("GSA NSN Extract (data.gov)","superseded",AMB,
  "Public/CC0, but the GSA-Advantage commercial subset, last updated 2017. PUB LOG covers it and far more.",
  "public-domain but partial & dated"),
 ("FED LOG® (DLA)","restricted",RED,
  "Fuller product incl. management/pricing — but access-controlled; not the public path.",
  "not publicly downloadable"),
 ("Commercial mirrors (nsnlookup, ISO, etc.)","avoid",RED,
  "Scrape FLIS; unofficial, variable quality. Excluded by your 'official-only' choice.",
  "unofficial"),
]
y=98
for h,tag,acc,d,meta in srcs:
    bh=104 if h.startswith("PUB") else 80
    P.append(box(40,y,720,bh,PANEL,LINE,11))
    P.append(f'<rect x="40" y="{y}" width="6" height="{bh}" rx="3" fill="{acc}"/>')
    P.append(t(60,y+24,h,13,TXT,700))
    P.append(box(620,y+10,128,22,acc,LINE,6)); P.append(t(684,y+25,tag,9,"#0f1419" if acc in(GRN,ACC,AMB) else TXT,700,"middle"))
    s,n=wrap(60,y+44,d,98,9.4,SUB,13); P.append(s)
    P.append(t(60,y+bh-12,meta,9,(("#8fae8f") if acc==GRN else ("#9bb3d6" if acc==ACC else ("#cbb87a" if acc==AMB else "#d98a8a"))),700))
    y+=bh+8
# what PUB LOG fills (right)
P.append(box(780,98,360,418,PANEL,GRN,12))
P.append(t(798,122,"WHAT PUB LOG FILLS HERE",12,GRN,700))
fills=[("NSN → nomenclature","the parts-request sheet item names"),
       ("NSN ↔ PART # + CAGE (MCRD)","the exact part# OCR couldn't pin down — Phase-2 gap, solved by data"),
       ("Characteristics (CHAR)","size / thread / material → the SIZE parameter for Tier 2.5 parametric 3D"),
       ("AAC (acquisition advice)","fills the 104th's AAC FEDLOG block"),
       ("Interchangeability / Substitutability","real substitute parts → grounds look-alike / variant warnings")]
yy=146
for h,d in fills:
    P.append(box(798,yy,326,62,P2,LINE,8))
    P.append(t(810,yy+20,h,10.6,"#bfe6c5",700)); s,_=wrap(810,yy+36,d,46,8.8,SUB,12); P.append(s)
    yy+=70
# procedure / caveats
P.append(box(40,548,1100,140,PANEL,LINE,12))
P.append(t(58,572,"ONE-TIME, OFFLINE-PRESERVING PROCEDURE",12,ACC,700))
proc=["On a CONNECTED machine: download PublogDVD.zip (free, no CAC) from DLA → extract.",
      "Use PUB LOG's built-in Search Batch / SQL export to dump records for your NSN list to CSV (NSN, item name, part#, CAGE, characteristics, AAC).",
      "Run `enrich` against that CSV → fills the offline reference tables (append-only, cited, R6). Copy the DB back. Engine never goes online.",
      "Caveats: the .ZIP is large (~GB); data is in the IMD product format, so the Batch/SQL export step is how you get clean CSV. Restricted/proprietary/NATO data is excluded (fine for us)."]
yy=592
for pr in proc:
    P.append(t(58,yy,"•",10,ACC,700)); s,n=wrap(72,yy,pr,150,9.4,SUB,13); P.append(s); yy+=n*13+4
P.append(box(40,700,1100,80,PANEL,AMB,12,1))
P.append(t(58,724,"BONUS — this also unblocks earlier gaps",11,AMB,700))
s,_=wrap(58,744,"PUB LOG's MCRD gives the authoritative NSN↔part# we deferred in the structured-parts work (it was OCR-noisy), CHAR gives the Tier 2.5 size parameter we said we'd need, and MDI&S gives real substitutes for look-alike warnings + the AAC field. One public, free, monthly dataset closes several gaps at once — additively (R6).",176,9.6,SUB,13); P.append(s)
P.append(t(40,H-14,"Assessment only — no download taken. To wire ingestion I'd extend `enrich` to the PUB LOG fields. Dark (R3). Your call.",9.4,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/33-nsn-sourcing-assessment"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
