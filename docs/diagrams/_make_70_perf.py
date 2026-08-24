#!/usr/bin/env python3
"""BUILT 0.56.0: speed & efficiency pass — Tier 1 + Tier 2 (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,640
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
P.append(t(40,46,"BUILT — Speed & efficiency pass  (v0.56.0)",19,TXT,700))
P.append(t(40,70,"Five internal optimizations — no new UI, no new surface area. Faster paging, faster lookups, fewer bytes on the wire. All RPS-safe and additive.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
def panel(x,y,w,h,ic,title,color,rows,foot):
    out=[box(x,y,w,h,PANEL,LINE,12), f'<rect x="{x}" y="{y}" width="6" height="{h}" rx="3" fill="{color}"/>']
    out.append(t(x+20,y+24,ic+"  "+title,12.5,TXT,700)); yy=y+44
    for r in rows:
        out.append(f'<circle cx="{x+24}" cy="{yy-3}" r="3" fill="{color}"/>'); s,n=wrap(x+36,yy,r,int((w-58)/5.2),8.6,SUB,11); out.append(s); yy+=3+n*11
    fs,_=wrap(x+20,y+h-18,foot,int((w-40)/5.0),8.2,GRN,11); out.append(fs); return "".join(out)
P.append(t(56,112,"TIER 1 — the big wins",12,ACC,700))
P.append(panel(40,122,366,178,"📄","Open-PDF LRU cache",TEAL,
  ["render_page_png re-opened + re-parsed the PDF on EVERY page. Now an LRU of 8 open fitz.Documents is reused.",
   "PyMuPDF isn't thread-safe -> each doc carries a render lock; the highlight path still uses a fresh doc (it mutates).",
   "Big win for paging + the loupe."],
  "Verified: LRU reuse + evict + close."))
P.append(panel(414,122,366,178,"🔌","Thread-local DB connections",PUR,
  ["db() opened a new SQLite connection + re-applied PRAGMAs on every request (the dossier fires 6+).",
   "Now a per-thread connection is reused; callers' .close() is a harmless no-op; rebuilds if it goes bad.",
   "Relaxed/OCR mode still gets a fresh conn (no shared locks)."],
  "Verified: reuse, Row-factory, 5-thread x20, 0 errors."))
P.append(panel(788,122,368,178,"🔤","Indexed look-alike (NOCASE)",AMB,
  ["Look-Alike scanned the whole parts table via UPPER(name)=UPPER(?).",
   "Now name/nomenclature are matched with COLLATE NOCASE so the new NOCASE indexes apply.",
   "EXPLAIN: MULTI-INDEX OR across ix_parts_name + ix_parts_nomenclature on real (selective) data."],
  "Index built by optimize_index.py."))
P.append(t(56,330,"TIER 2 — cheap & worth it",12,ACC,700))
P.append(panel(40,340,553,150,"🏷","ETag / 304 Not-Modified",GRN,
  ["_send now sends an ETag (md5 of the body, stable across gzip). A matching If-None-Match returns 304 with an empty body.",
   "Repeat views of a page image, the JS, or JSON skip re-sending the bytes entirely — big on slow links."],
  "Verified by curl: 304 on match, 200 on stale, Cache-Control preserved."))
P.append(panel(604,340,553,150,"🗂","Index maintenance + ANALYZE",ACC,
  ["optimize_index.py (+ .bat): idempotent CREATE INDEX IF NOT EXISTS for pages(document_id) and parts(name/nomenclature NOCASE), then ANALYZE so the planner uses them.",
   "EXPLAIN confirms find-in-manual now SEARCHes via ix_pages_document instead of scanning the biggest table."],
  "Run once when OCR is paused (brief write lock; 120s busy-timeout)."))
P.append(box(40,508,1116,86,PANEL,GRN,12,1))
P.append(t(58,532,"SAFE, MEASURED, NO BLOAT",12,GRN,700))
s,_=wrap(58,552,"Every change is server-internal — no new pages, no API surface, nothing for the user to learn. All RPS-safe (pure Python, ES-agnostic). 44/44 tests still green; the connection-reuse db() is exercised by the passing pillar suite. The two index builds are the only DB writes and are a one-time, idempotent maintenance step — kept out of the live server so they never contend with the running OCR. This is efficiency by tightening hot paths, not by adding machinery.",188,9.4,SUB,13);P.append(s)
P.append(t(40,H-12,"BUILT diagram. Dark (R3). v0.56.0 · 2026-06-02 · viewer_app.py (db reuse · fitz LRU · _send ETag · NOCASE) + optimize_index.py. Additive (R1/R6).",9,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/70-perf-pass-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"), "bytes")
