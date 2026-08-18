#!/usr/bin/env python3
"""Branched dual-track changelog timeline (R7): Modern + Legacy (Retroactive Post-Support).
Data-driven — to extend, add to MODERN / LEGACY / BACKPORTS and re-run. Dark (R3) + PDF (R5).
Outputs docs/diagrams/CHANGELOG-DUALTRACK.{svg,pdf}."""
import cairosvg, html, os

# (version, short label) — key modern milestones around/after the branch point
MODERN = [("0.37.0","COMPLETE compat"), ("0.42.0","Circuit Lab"), ("0.45.0","RPS"),
          ("0.48.0","Solve-it + procedures"), ("0.50.0","Add docs + search"), ("0.54.0","workflow + ops")]
BRANCH_AT = "0.37.0"                       # legacy forks from this modern version
# (legacy version, modern-base it tracks, short label) — curated milestones (full detail in CHANGELOG-LEGACY.md)
LEGACY = [("0.37.0-legacy","0.37.0","legacy created (compat foundation)"),
          ("0.42.0-legacy","0.42.0","Circuit Lab (static overlay)"),
          ("0.45.0-legacy","0.45.0","RPS delivered (full parity)"),
          ("0.48.0-legacy","0.48.0","workflow + procedures (full parity)"),
          ("0.50.0-legacy","0.50.0","add docs + search (full parity)"),
          ("0.54.0-legacy","0.54.0","packet/dossier/find/ops (full parity)")]
# backports: (modern_version, legacy_version, note) — drawn as dashed modern->legacy links
BACKPORTS = [("0.42.0","0.42.0-legacy","Circuit Lab → static-overlay (~adapted)"),
             ("0.45.0","0.45.0-legacy","RPS → legacy now runs well (✓ same)"),
             ("0.48.0","0.48.0-legacy","procedures / hub / search → full parity (✓ same)"),
             ("0.50.0","0.50.0-legacy","Add documents → full parity (✓ same)"),
             ("0.54.0","0.54.0-legacy","packet / dossier / find / ops → full parity (✓ same)")]

def esc(s): return html.escape(s)
W=1180; H=620
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; PUR="#7f77dd"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'

P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
P.append('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9aa5b1"/></marker></defs>')
P.append(box(0,0,W,H,BG,BG,0))
P.append(t(40,46,"THE VIEWER — Dual-track changelog timeline (Modern + Legacy)",21,TXT,700))
P.append(t(40,70,"The Legacy / Retroactive Post-Support line branches from the modern track at the version it was created, and shows every backport. Versions: <base>-legacy.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

n=len(MODERN); x0=160; dx=min(220,(W-260)//max(1,n-1)) if n>1 else 0
xof={v:x0+i*dx for i,(v,_) in enumerate(MODERN)}
mY=210; lY=400
# modern lane
P.append(t(60,mY-40,"MODERN  (Performance · Win 10/11)",11,GRN,700))
P.append(f'<line x1="{x0-30}" y1="{mY}" x2="{x0+(n-1)*dx+40}" y2="{mY}" stroke="#3a5a44" stroke-width="2.5"/>')
P.append(f'<path d="M{x0+(n-1)*dx+40},{mY} l16,0" stroke="#3a5a44" stroke-width="2.5" marker-end="url(#a)"/>')
for v,lab in MODERN:
    x=xof[v]; P.append(f'<circle cx="{x}" cy="{mY}" r="8" fill="#16301f" stroke="#2f7d4f" stroke-width="2"/>')
    P.append(t(x,mY-22,v,9.4,TXT,700,"middle")); P.append(t(x,mY-8,lab,7.8,SUB,400,"middle"))
# legacy lane
lxs=[xof[base] for (_,base,_) in LEGACY if base in xof]
lstart=min(lxs) if lxs else xof.get(BRANCH_AT,x0)
P.append(t(60,lY+44,"LEGACY  (Retroactive Post-Support · Win 7 / Vista)",11,ACC,700))
P.append(f'<line x1="{lstart}" y1="{lY}" x2="{x0+(n-1)*dx+40}" y2="{lY}" stroke="#2b486e" stroke-width="2.5"/>')
P.append(f'<path d="M{x0+(n-1)*dx+40},{lY} l16,0" stroke="#2b486e" stroke-width="2.5" marker-end="url(#a)"/>')
# branch curve
bx=xof.get(BRANCH_AT,x0)
P.append(f'<path d="M{bx},{mY+8} C{bx},{mY+70} {lstart},{lY-70} {lstart},{lY-8}" stroke="{PUR}" stroke-width="2" fill="none"/>')
P.append(t(bx-8,(mY+lY)//2,"branches here (legacy created)",8.6,PUR,700,"end"))
for lv,base,lab in LEGACY:
    x=xof.get(base,lstart); P.append(f'<circle cx="{x}" cy="{lY}" r="8" fill="#16223a" stroke="#4f9dff" stroke-width="2"/>')
    P.append(t(x,lY+24,lv,9.0,TXT,700,"middle")); P.append(t(x,lY+38,lab,7.8,SUB,400,"middle"))
# backport links
for _bi,(mv,lv,note) in enumerate(BACKPORTS):
    if mv in xof:
        x=xof[mv]; P.append(f'<path d="M{x},{mY+8} L{x},{lY-8}" stroke="{AMB}" stroke-width="1.3" stroke-dasharray="4 3" fill="none" marker-end="url(#a)"/>')
        rightish = x > (x0+(n-1)*dx)/2
        ly = (mY+lY)//2 - 50 + (_bi%4)*28
        P.append(t(x-8 if rightish else x+6, ly, "backport: "+note, 7.6, AMB, 400, "end" if rightish else "start"))

# legend / parity
P.append(box(40,470,1100,110,PANEL,LINE,12))
P.append(t(58,494,"Parity badges (per legacy entry in CHANGELOG-LEGACY.md):",10,SUB,700))
P.append(t(58,516,"✓ same feature        ~ adapted (Poppler / Tesseract / lite UI)        – N/A (GPU-only — speed, not a feature)",10,SUB,400))
P.append(t(58,544,"Modern history: CHANGELOG.md   ·   Legacy history (starts at the branch point): CHANGELOG-LEGACY.md",9.4,SUB,400))
P.append(t(58,562,"To extend: add to MODERN / LEGACY / BACKPORTS in this generator and re-run (R4/R5/R7).",9,GRN,400))
P.append(t(40,H-12,"Dark (R3) · R7 dual-track changelog · regenerated each release.",9.2,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/CHANGELOG-DUALTRACK"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"), "bytes ->", base+".pdf")
