#!/usr/bin/env python3
"""BUILT 0.55.0: UX consolidation — visual steps, torque, Ctrl+K palette, help guide (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,610
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"
ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"; TEAL="#1d9e75"; PUR="#7f77dd"
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
P.append(t(40,46,"BUILT — UX consolidation  (v0.55.0)",19,TXT,700))
P.append(t(40,70,"Four small additions that make the depth feel SIMPLE, not sprawling — and one integration instead of a new page. All ES5-safe + rps.js (true parallel compatibility).",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
def panel(x,y,w,h,ic,title,color,rows,foot):
    out=[box(x,y,w,h,PANEL,LINE,12), f'<rect x="{x}" y="{y}" width="6" height="{h}" rx="3" fill="{color}"/>']
    out.append(t(x+20,y+26,ic+"  "+title,13,TXT,700)); yy=y+48
    for r in rows:
        out.append(f'<circle cx="{x+24}" cy="{yy-3}" r="3" fill="{color}"/>'); s,n=wrap(x+36,yy,r,int((w-58)/5.2),8.8,SUB,11); out.append(s); yy+=4+n*11
    fs,_=wrap(x+20,y+h-20,foot,int((w-40)/5.0),8.4,GRN,11); out.append(fs); return "".join(out)
P.append(panel(40,108,552,184,"📐","Visual steps  (/stepflow)",TEAL,
  ["The parsed procedure as a big follow-along FLOW: numbered nodes + connectors, WARNINGs/CAUTIONs as colour-coded banners, tools staged at the top.",
   "The 'simple' visual for junior mechanics (the detailed list stays the 'advanced' view). Client-side from /api/procedure; print-friendly.",
   "Serves mission goal D (dynamic graphics for all levels)."],
  "Read-only; built from existing data (R1/R6)."))
P.append(panel(604,108,552,184,"🔩","Torque specs — integrated, not a new page",AMB,
  ["torque_specs() parses stated torque values (ft-lb / in-lb / N·m, incl. ranges) from the procedure pages, each cited.",
   "Surfaced as a PANEL inside the existing Part dossier — integration over sprawl, the opposite of a new standalone tab.",
   "Regex validated on 5 phrasings; /api/torque endpoint."],
  "Restraint by design: fold into what exists (R1/R6)."))
P.append(panel(40,304,552,184,"⌨","Command palette  (Ctrl+K, everywhere)",PUR,
  ["Press Ctrl+K on ANY page → one launcher to jump to any feature, or look up a part/vehicle via /api/suggest. Arrow keys + Enter.",
   "Loaded once by rps.js (already universal) — so it's global with a single include, no per-page edits.",
   "Tames the ~14-feature nav into one keystroke."],
  "ES5-safe; self-contained; works on legacy via polyfills."))
P.append(panel(604,304,552,184,"❔","Help & guide  (/help)",ACC,
  ["A 'what do you want to do?' map of every feature, grouped by the workshop workflow, plus a 30-second first-run tour.",
   "Makes the depth discoverable; the home nav now keeps the essentials and points to Ctrl+K / Help for the rest.",
   "Mostly static; honest 'the manual is the source of truth' footer."],
  "The antidote to 'overbuilt' — discoverability, not more features."))
P.append(box(40,506,1116,86,PANEL,GRN,12,1))
P.append(t(58,530,"COHERENT & COMPATIBLE (the point of this version)",12,GRN,700))
s,_=wrap(58,550,"This wave adds NO new heavy machinery — it consolidates. Every page this session is ES5-safe and carries rps.js, so the whole core workflow runs identically on modern, lite and legacy (down to IE11 via polyfills); only the rich-graphics pages (3-D / Circuit Lab / schematic tilt) stay modern-by-design. No full scans, keep-alive + gzip + page cache keep it fast. 44/44 tests green. Architecture stays modular & additive — every feature is one removable route.",188,9.4,SUB,13);P.append(s)
P.append(t(40,H-12,"BUILT diagram. Dark (R3). v0.55.0 · 2026-06-02 · stepflow.html · torque in dossier · palette.js (via rps.js) · help.html. Additive/ES5-safe (R1/R6).",9,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/69-ux-consolidation-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"), "bytes")
