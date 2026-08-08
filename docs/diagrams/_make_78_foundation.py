#!/usr/bin/env python3
"""BUILT 0.64.0: Foundation batch part 1 — the RPS retroactive test gate (rps_lint), the bug it caught
(status.html -> ES5), /healthz, and RUN-ALL-TESTS orchestrator. (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,560
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
P.append(t(40,46,"BUILT — Foundation batch, part 1: the test + RPS gate  (v0.64.0)",19,TXT,700))
P.append(t(40,70,"From the 90-item backlog. Builds the harness that auto-verifies every later change — and on first run it caught a real legacy-parity bug.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
def panel(x,y,w,h,ic,title,color,rows,metric):
    out=[box(x,y,w,h,PANEL,LINE,12), f'<rect x="{x}" y="{y}" width="6" height="{h}" rx="3" fill="{color}"/>']
    out.append(t(x+20,y+24,ic+"  "+title,12.5,TXT,700)); yy=y+44
    for r in rows:
        out.append(f'<circle cx="{x+24}" cy="{yy-3}" r="3" fill="{color}"/>'); s,n=wrap(x+36,yy,r,int((w-58)/5.2),8.7,SUB,11); out.append(s); yy+=3+n*11
    out.append(box(x+16,y+h-30,w-32,22,P2,color,6,1)); out.append(t(x+26,y+h-15,metric,8.8,color,700))
    return "".join(out)
P.append(panel(40,108,553,192,"🧪","RPS lint — the 'does legacy still work?' gate",ACC,
  ["tests/rps_lint.py scans every ui/*.html + *.js for ES6 SYNTAX (arrow, const/let, template, spread, for-of, class, async/await) that polyfills can't fix.",
   "ES5-required pages (mechanic-facing tools) FAIL the gate on any ES6; rich pages (3D/WebGL/loupe/circuit sim) are modern-by-design and exempt (reported).",
   "Run by RUN-ALL-TESTS.bat alongside the regression suites."],
  "A change isn't done until legacy still runs."))
P.append(panel(604,108,553,192,"🐞","...and it caught one immediately",AMB,
  ["First run flagged status.html (the OCR/system dashboard, a legacy tool) as containing ES6: arrow x5, const x13, let x3 + async/await.",
   "On IE11 / Win7 that page would have thrown a SyntaxError and shown nothing.",
   "Rewrote its script in clean ES5 (var / function / XHR). Re-verified: 0 arrow/const/let/template/async/await."],
  "Real RPS bug found and fixed on day one."))
P.append(panel(40,316,553,170,"🩺","/healthz endpoint",TEAL,
  ["New GET /healthz returns the preflight checks as JSON (python/disk/DB integrity/schema/GPU).",
   "Feeds the watchdog and a future ops status badge; 503 when a fatal check fails.",
   "Stdlib, RPS-safe."],
  "Machine-readable health in one call."))
P.append(panel(604,316,553,170,"▶","RUN-ALL-TESTS.bat",PUR,
  ["One host-side command = regression suites + safeguard truncation/integrity verify + the RPS lint.",
   "Exit 0 only when additives pass AND legacy parity holds. /snapshot baselines first.",
   "This is the 'test all additives and the retroactive' loop, automated."],
  "One button: additives + retroactive, green or not."))
P.append(box(40,502,1116,44,PANEL,GRN,12,1))
s,_=wrap(58,528,"VERIFIED: rps_lint compiles + ran against the real 20 UI files (all ES5-tier pages clean except the status.html it caught; modern pages correctly exempt). status.html re-checked ES5-clean. /healthz + RUN-ALL-TESTS confirmed on host. Backlog items #2-4/#6/#8 (shared.js, base.css, patterns.py, diagram _common) + the route smoke test are the next Foundation increment.",196,9,SUB,12);P.append(s)
P.append(t(40,H-8,"BUILT diagram. Dark (R3). v0.64.0 · 2026-06-03 · tests/rps_lint.py · ui/status.html (ES5) · viewer_app.py /healthz · RUN-ALL-TESTS.bat. Additive (R1/R6).",9,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/78-foundation-testgate-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1180)
print("wrote", os.path.getsize(base+".pdf"), "bytes")
