#!/usr/bin/env python3
"""BUILT 0.46.0: gzip + keep-alive transport + RPS mode toggle in Settings (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,660
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"
ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"; TEAL="#1d9e75"; PUR="#7f77dd"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def arrow(x1,y1,x2,y2,col="#9aa5b1"): return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="1.7" fill="none" marker-end="url(#a)"/>'
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
P.append(t(40,46,"BUILT — Faster transport + a Performance toggle  (v0.46.0)",19,TXT,700))
P.append(t(40,70,"Two RPS finishers: gzip + keep-alive on the wire, and a Modern/Lite/Legacy switch in Settings. Both additive; data, search and the 104th sheet are untouched.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# gzip + keepalive
P.append(t(56,116,"1 · gzip + KEEP-ALIVE (every page load, automatically)",12,ACC,700))
P.append(box(40,126,1100,180,PANEL,LINE,12))
P.append(box(60,150,210,135,P2,TEAL,10,1));P.append(t(75,172,"Keep-alive (HTTP/1.1)",9.6,TEAL,700))
for i,d in enumerate(["one TCP connection reused","across every request","(Content-Length on all","responses) — less handshake","latency on slow links"]):P.append(t(75,192+i*16,d,8.2,SUB,400))
P.append(box(290,150,300,135,P2,ACC,10,1));P.append(t(305,172,"gzip (Accept-Encoding aware)",9.6,ACC,700))
for i,d in enumerate(["compresses JSON / HTML / JS / SVG","when the browser sends gzip","skips < 512 B (overhead) and","already-compressed PNG / PDF","sets Vary: Accept-Encoding"]):P.append(t(305,192+i*16,d,8.2,SUB,400))
P.append(box(610,150,530,135,P2,GRN,10,1));P.append(t(625,172,"Verified (curl)",9.6,GRN,700))
for i,d in enumerate(["2 KB JSON → 45 B gzipped (Content-Encoding: gzip)","two requests served on ONE connection (keep-alive)","small JSON (<512 B) left uncompressed","image/png left uncompressed even when gzip offered","no Accept-Encoding → full uncompressed body"]):P.append(f'<circle cx="628" cy="{191+i*16-3}" r="3" fill="{GRN}"/>'),P.append(t(640,191+i*16,d,8.2,SUB,400))
P.append(t(60,300,"Biggest win for the large home page + JSON results on a slow connection or an old box; zero UI change — it's in _send().",8.8,GRN,400))

# RPS toggle
P.append(t(56,338,"2 · PERFORMANCE TOGGLE IN SETTINGS (manual override)",12,ACC,700))
P.append(box(40,348,1100,210,PANEL,LINE,12))
P.append(t(58,372,"⚙ Settings → Performance (Retroactive Post-Support)",10.5,AMB,700))
opts=[("Auto","match this PC (the probe decides) — the default",ACC),
      ("Modern","full effects, server hi-fi loupe",GRN),
      ("Lite","effects off, lighter rendering",AMB),
      ("Legacy","Win 7 / Vista friendly",PUR)]
x=58
for nm,d,c in opts:
    P.append(box(x,386,262,56,P2,c,9,1));P.append(t(x+12,408,nm,10.5,c,700));s,_=wrap(x+12,424,d,40,8.2,SUB,11);P.append(s);x+=272
P.append(t(58,470,"How it works:",10,TXT,700))
for i,d in enumerate(["the choice is saved per-browser (localStorage 'rps.mode'); rps.js reads it and re-applies live — no reload",
                      "it asks /api/rps?mode=… for that mode's flags, then toggles lite-effects + default DPI on the client",
                      "the SERVER's mode (SQLite tuning + page cache) stays auto-picked from the real hardware — you can't mis-tune the DB by choosing a UI mode",
                      "force the whole server at launch instead with  viewer_app.py --mode legacy  (or ?mode= in the URL)"]):
    P.append(t(58,490+i*16,"• "+d,8.6,SUB,400))

P.append(t(40,H-14,"BUILT diagram. Dark (R3). v0.46.0 · 2026-06-02 · viewer_app.py (_send gzip+keep-alive) + engine/ui/rps.js + index.html Settings. Additive/rollbackable (R1).",9,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/63-perf-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1180)
print("wrote", os.path.getsize(base+".pdf"), "bytes")
