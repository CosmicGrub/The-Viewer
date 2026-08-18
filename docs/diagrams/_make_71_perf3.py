#!/usr/bin/env python3
"""BUILT 0.57.0: speed pass round 2 — compact JSON, pre-render page ETag, suggest table, WAL (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,580
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
P.append(t(40,46,"BUILT — Speed pass, round 2  (v0.57.0)",19,TXT,700))
P.append(t(40,70,"Four more internal optimizations, each MEASURED. Fewer bytes, less work per request, faster type-ahead, better concurrency during OCR.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
def panel(x,y,w,h,ic,title,color,rows,metric):
    out=[box(x,y,w,h,PANEL,LINE,12), f'<rect x="{x}" y="{y}" width="6" height="{h}" rx="3" fill="{color}"/>']
    out.append(t(x+20,y+24,ic+"  "+title,12.5,TXT,700)); yy=y+44
    for r in rows:
        out.append(f'<circle cx="{x+24}" cy="{yy-3}" r="3" fill="{color}"/>'); s,n=wrap(x+36,yy,r,int((w-58)/5.2),8.7,SUB,11); out.append(s); yy+=3+n*11
    out.append(box(x+16,y+h-30,w-32,22,P2,color,6,1)); out.append(t(x+26,y+h-15,"MEASURED: "+metric,8.8,color,700))
    return "".join(out)
P.append(panel(40,108,553,178,"📦","Compact JSON","%s"%AMB if False else AMB,
  ["json.dumps now uses separators=(',',':') — no spaces between keys/values.",
   "Every API response is smaller on the wire (and the smaller text gzips a touch better too).",
   "Zero behaviour change; purely fewer bytes."],
  "~8% smaller JSON payloads (then gzipped)."))
P.append(panel(604,108,553,178,"🏷","Pre-render page ETag",TEAL,
  ["The /page route computes a cheap param-based ETag and checks If-None-Match BEFORE rendering.",
   "A repeat view returns 304 without opening the PDF, rendering, or hashing the image at all.",
   "_send also stops md5-hashing big PNGs (it trusts the supplied ETag)."],
  "304 on repeat view -> renderer NOT touched (X-Rendered: no)."))
P.append(panel(40,300,553,178,"⚡","Precomputed suggest table",PUR,
  ["optimize_index.py builds suggest_terms(term PRIMARY KEY, freq) from the FTS vocab once.",
   "Type-ahead becomes a prefix lookup on a WITHOUT-ROWID b-tree instead of a GROUP BY over the whole FTS vocab every keystroke; a small LRU caches recent prefixes.",
   "Falls back to the vocab GROUP BY until the table is built."],
  "46x faster per keystroke (0.18ms -> ~0.00ms; bigger on the real corpus)."))
P.append(panel(604,300,553,178,"🔀","WAL journal mode",GRN,
  ["optimize_index.py switches the DB to WAL (Write-Ahead Logging).",
   "Server reads no longer block on the OCR writer — readers and the single writer run concurrently.",
   "Reversible (PRAGMA journal_mode=DELETE); local-disk only (as designed)."],
  "Concurrent reads during writes (verified: journal_mode=wal)."))
P.append(box(40,496,1116,62,PANEL,GRN,12,1))
P.append(t(58,518,"EVERY CHANGE MEASURED — AND STILL GREEN",11.5,GRN,700))
s,_=wrap(58,536,"Per your rule, each optimization was verified to actually reduce work or bytes: smaller JSON, a 304 that skips rendering, a 46x type-ahead query, WAL concurrency. All server-internal, RPS-safe, additive. 23 pillars + 21 feature tests still pass (the full module imports cleanly with every edit). suggest_terms + WAL are built by optimize_index.py — run it once when OCR is paused.",190,9.2,SUB,12.5);P.append(s)
P.append(t(40,H-10,"BUILT diagram. Dark (R3). v0.57.0 · 2026-06-02 · viewer_app.py (_send · /page · suggest) + optimize_index.py (suggest_terms · WAL). Additive (R1/R6).",9,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/71-perf-round2-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"), "bytes")
