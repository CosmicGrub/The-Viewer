#!/usr/bin/env python3
"""MOCKUP: dual-track changelog — Modern + Legacy (Retroactive Post-Support), branched timeline (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,860
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"; TEAL="#1d9e75"; PUR="#7f77dd"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def arrow(x1,y1,x2,y2,col="#9aa5b1",dash=""): return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="1.6" fill="none" marker-end="url(#a)"{dash}/>'
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
P.append(t(40,46,"MOCKUP — Dual-track changelog: Modern + Legacy (Retroactive Post-Support)",20,TXT,700))
P.append(t(40,70,"The Legacy line BRANCHES at the exact version it was created, runs in parallel, and each entry notes what's shared vs. backported from the modern track.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# === Branched timeline ===
P.append(t(56,118,"1 · BRANCHED VERSION TIMELINE (the canonical view, dark + PDF)",12,ACC,700))
P.append(box(40,128,1100,270,PANEL,LINE,12))
# modern lane
mY=185; xs=[140,300,460,620,780,940]
mver=["0.35.0","0.36.0","0.37.0","0.38.0","0.39.0","0.40.0"]
P.append(t(60,mY-28,"MODERN  (Performance · Win10/11)",10,GRN,700))
P.append(f'<line x1="120" y1="{mY}" x2="1000" y2="{mY}" stroke="#3a5a44" stroke-width="2.5"/>')
for i,x in enumerate(xs):
    P.append(f'<circle cx="{x}" cy="{mY}" r="7" fill="#16301f" stroke="#2f7d4f" stroke-width="2"/>')
    P.append(t(x,mY-16,mver[i],8.6,TXT,700,"middle"))
P.append(arrow(1000,mY,1020,mY,"#3a5a44"))
# legacy lane
lY=330; lxs=[460,620,780,940]
lver=["0.37.0-legacy","0.38.0-legacy","0.39.0-legacy","0.40.0-legacy"]
P.append(t(60,lY+34,"LEGACY  (Retroactive Post-Support · Win7/Vista)",10,ACC,700))
P.append(f'<line x1="460" y1="{lY}" x2="1000" y2="{lY}" stroke="#2b486e" stroke-width="2.5"/>')
# branch from modern 0.37.0 (x=460) down to legacy start
P.append(f'<path d="M460,{mY+7} C460,{mY+50} 460,{lY-50} 460,{lY-7}" stroke="{PUR}" stroke-width="2" fill="none" stroke-dasharray="2 0"/>')
P.append(t(360,265,"branches here",8.6,PUR,700)); P.append(t(360,279,"(legacy created)",8,SUB,400))
for i,x in enumerate(lxs):
    P.append(f'<circle cx="{x}" cy="{lY}" r="7" fill="#16223a" stroke="#4f9dff" stroke-width="2"/>')
    P.append(t(x,lY+22,lver[i],8.4,TXT,700,"middle"))
P.append(arrow(1000,lY,1020,lY,"#2b486e"))
# backport cross-links (modern -> legacy) dashed
for x in [620,780,940]:
    P.append(f'<path d="M{x},{mY+7} L{x},{lY-7}" stroke="{AMB}" stroke-width="1.3" stroke-dasharray="4 3" fill="none" marker-end="url(#a)"/>')
P.append(t(625,260,"backport",7.8,AMB,700)); P.append(t(625,272,"(adapted)",7.4,SUB,400))
# parity legend
P.append(t(60,378,"Parity badge per legacy entry:",8.8,SUB,700))
P.append(t(250,378,"✓ same feature   ~ adapted (Poppler/Tesseract/lite)   – N/A (GPU-only, not applicable)",8.8,SUB,400))

# === Markup sample ===
P.append(t(56,424,"2 · CHANGELOG-LEGACY.md — entry format (markup)",12,ACC,700))
P.append(box(40,434,560,340,PANEL,LINE,12))
code=[("## [0.37.0-legacy] — 2026-06-02 — Legacy track created", TXT,700),
      ("Forked from modern 0.37.0 at the complete-compat point.",SUB,400),
      ("Target: Windows 7 / Vista, comparable responsiveness.",SUB,400),
      ("",SUB,400),
      ("### In this build",TXT,700),
      ("- Core search / vehicle hub / 104th sheet  ✓ same",GRN,400),
      ("- Page render via Poppler (pdftoppm)        ~ adapted",AMB,400),
      ("- OCR via Tesseract (CPU)                   ~ adapted",AMB,400),
      ("- ES5 UI bundle + Firefox ESR note          ~ adapted",AMB,400),
      ("- Pre-baked page cache + warm-on-view       + new",ACC,400),
      ("- GPU acceleration                          – N/A",SUB,400),
      ("",SUB,400),
      ("### Parity with modern",TXT,700),
      ("Matches modern 0.37.0 features; GPU is the only",SUB,400),
      ("omission (speed, not a feature).",SUB,400),
      ("",SUB,400),
      ("## [0.40.0-legacy] — later — backport",TXT,700),
      ("Backported the alias map + status page from",SUB,400),
      ("modern 0.40.0 (adapted for the lite UI).",SUB,400)]
yy=458
for line,c,wt in code:
    P.append(t(58,yy,line,8.4,c,wt)); yy+=16.2

# === Recommendation ===
P.append(t(620,424,"3 · HOW IT FITS + MY RECOMMENDATION",12,ACC,700))
P.append(box(604,434,536,340,PANEL,GRN,12,1))
recs=[("Two files, one timeline",
       "CHANGELOG.md (modern) + CHANGELOG-LEGACY.md (legacy), plus ONE branched visual timeline (this) that shows where legacy forked and every backport. Each stays readable; the diagram shows the relationship."),
      ("Version as <base>-legacy",
       "Name legacy builds after the modern baseline they branch from (0.37.0-legacy) so the relationship is always explicit at a glance."),
      ("Parity line on every entry",
       "Each legacy entry tags features same / adapted / N-A and ends with a 'Parity with modern' summary — answers 'is it caught up?' instantly."),
      ("Backports are first-class",
       "When a modern feature lands in legacy, it gets its own dated legacy entry + a dashed cross-link on the timeline (your 'added in conjunction with overall progress')."),
      ("R5 visual, automated",
       "Extend the visual-changelog generator to emit this branched timeline so it stays current with every release (fits rules R4/R5).")]
y=458
for h,d in recs:
    P.append(f'<circle cx="620" cy="{y-4}" r="3" fill="{GRN}"/>'); P.append(t(632,y,h,9.8,TXT,700)); s,n=wrap(632,y+15,d,86,8.6,SUB,11.5); P.append(s); y+=20+n*11.5

P.append(t(40,H-12,"MOCKUP — your call. Dark (R3). Concept only; nothing built. Pairs with the Retroactive Post-Support plan (diagram 52).",9.2,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/53-dualtrack-changelog-mockup"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"), "bytes ->", base+".pdf")
