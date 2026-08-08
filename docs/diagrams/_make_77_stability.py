#!/usr/bin/env python3
"""BUILT 0.63.0: RPS-safe stability suite — preflight health gate, disk-space guard, off-disk backup
mirror, and server/OCR watchdogs. Stdlib-only; GPU never fatal; works on modern/lite/legacy. (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,600
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"
ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; TEAL="#1d9e75"; PUR="#7f77dd"; RED="#c4585a"
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
P.append(t(40,46,"BUILT — RPS-safe stability suite  (v0.63.0)",19,TXT,700))
P.append(t(40,70,"The data 'treasure vault' protects FILES; this adds a thin HEALTH layer that keeps the program running. All stdlib, no new deps, GPU never fatal — identical on modern / lite / legacy.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')
def panel(x,y,w,h,ic,title,color,rows,metric):
    out=[box(x,y,w,h,PANEL,LINE,12), f'<rect x="{x}" y="{y}" width="6" height="{h}" rx="3" fill="{color}"/>']
    out.append(t(x+20,y+24,ic+"  "+title,12.5,TXT,700)); yy=y+44
    for r in rows:
        out.append(f'<circle cx="{x+24}" cy="{yy-3}" r="3" fill="{color}"/>'); s,n=wrap(x+36,yy,r,int((w-58)/5.2),8.7,SUB,11); out.append(s); yy+=3+n*11
    out.append(box(x+16,y+h-30,w-32,22,P2,color,6,1)); out.append(t(x+26,y+h-15,metric,8.8,color,700))
    return "".join(out)
P.append(panel(40,108,553,184,"🚦","Preflight health gate (fail-fast)",ACC,
  ["preflight.py checks python / free disk / DB quick_check / schema-vs-migrations BEFORE the server or OCR start.",
   "A real problem (disk full, corrupt index) STOPS with a clear message instead of crash-looping; schema drift -> WARN (run fix_schema_version).",
   "GPU is INFO only — absent on lite/legacy is fine, never a FAIL. Wired into run_ocr_auto.bat + run_app.bat."],
  "Kills the crash-loop class of failure at the door."))
P.append(panel(604,108,553,184,"💾","Disk-space guard",AMB,
  ["disk_ok() watches free space on the index drive (default 1 GB floor; env VIEWER_MIN_FREE_MB).",
   "OCR PAUSES a pass cleanly when low (the auto-runner retries); the page-render cache stops writing.",
   "Fail-OPEN: if free space can't be read, work continues — a probe glitch never halts the app."],
  "The disk can't silently fill on a laptop."))
P.append(panel(40,300,553,184,"🗄","Off-disk backup mirror",TEAL,
  ["safeguard.py mirror --to <USB/external/network> copies the vault to a SECOND location, verifying every file by SHA-256.",
   "One disk failure can no longer lose both the data and its backups. BACKUP-OFFDISK.bat wraps it.",
   "Daily snapshot+verify task already exists (register_snapshot_task.bat); this closes the single-disk gap."],
  "Backups survive a dead drive."))
P.append(panel(604,300,553,184,"🐕","Watchdog + stall detection",PUR,
  ["watchdog_app.bat supervises the web server and AUTO-RESTARTS it if it ever crashes (kiosk/shop machine stays up).",
   "OCR now writes a heartbeat every batch; ocr_watchdog.py flags a hung pass (stale heartbeat) vs a healthy one.",
   "The auto-runner already restarts a pass that ENDS early; this catches one that HANGS."],
  "Server stays up; a hung OCR pass is visible."))
P.append(box(40,504,1116,72,PANEL,GRN,12,1))
P.append(t(58,526,"VERIFIED  ·  RPS PARITY PRESERVED",11.5,GRN,700))
s,_=wrap(58,544,"preflight.py and ocr_watchdog.py compile + pass functional tests (gate goes no-go only on fatal checks; GPU stays INFO; watchdog flags fresh vs 2-hour-stale heartbeat). Off-disk mirror verified by SHA-256 in an isolation test (latest + all snapshots). Disk guard fails open. All server/OCR edits confirmed intact on the host via authoritative tools. Nothing here assumes a modern OS or GPU — lite/legacy behave identically. Run host-side VERIFY-ALL.bat to compile-check the whole tree.",190,9.2,SUB,12.5);P.append(s)
P.append(t(40,H-12,"BUILT diagram. Dark (R3). v0.63.0 · 2026-06-02 · preflight.py · ocr_watchdog.py · safeguard.py mirror · viewer_ingest/rps disk-guard+heartbeat · run_ocr_auto/run_app/watchdog_app/BACKUP-OFFDISK.bat. Additive (R1/R6).",9,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/77-stability-suite-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1180)
print("wrote", os.path.getsize(base+".pdf"), "bytes")
