#!/usr/bin/env python3
"""BUILT 0.36.0: hardware probe + autonomous adaptive GPU OCR runner (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,820
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"; TEAL="#1d9e75"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def arrow(x1,y1,x2,y2,col="#9aa5b1"): return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="1.6" fill="none" marker-end="url(#a)"/>'
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
P.append(t(40,46,"BUILT — Hardware probe + autonomous adaptive OCR  (v0.36.0)",20,TXT,700))
P.append(t(40,70,"Win11-first, best-effort back to Win7. The app scans your PC, grants the right resources, then runs OCR to 100% unattended on the best engine your hardware supports.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# Panel 1: probe -> profile
P.append(t(56,116,"1 · CAPABILITY PROBE (before onboarding) -> sysprobe.py",12,ACC,700))
P.append(box(40,126,1100,210,PANEL,LINE,12))
P.append(box(60,150,200,150,P2,LINE,8)); P.append(t(160,170,"detect",10,ACC,700,"middle"))
for i,d in enumerate(["OS + build (Win7..11)","Python version","CPU cores","RAM","NVIDIA GPU / CUDA","laptop + battery","free disk"]):
    P.append(t(74,190+i*15,"• "+d,8.6,SUB,400))
P.append(arrow(260,225,290,225,TEAL))
P.append(box(294,150,250,150,"#13241c",GRN,8)); P.append(t(419,170,"hardware_profile.json",10,"#bfe6cf",700,"middle"))
for i,d in enumerate(["tier","use_gpu","ocr_workers","ocr_dpi","hd_render_cap","feature availability"]):
    P.append(t(312,192+i*16,"• "+d,8.8,"#8fbf9f",400))
P.append(arrow(544,225,574,225,TEAL))
P.append(box(578,150,260,150,P2,LINE,8)); P.append(t(708,170,"launchers read it",10,TXT,700,"middle"))
P.append(t(594,196,"sysprobe.py --get ocr_workers",8.4,SUB,400)); P.append(t(594,214,"--get ocr_dpi / use_gpu",8.4,SUB,400))
s,_=wrap(594,238,"so run_ocr_auto.bat / run_app size themselves to the machine.",36,8.6,SUB,11); P.append(s)
P.append(box(858,150,262,150,PANEL,AMB,8,1)); P.append(t(989,170,"your Acer Nitro 5",10,AMB,700,"middle"))
s,_=wrap(874,192,"NVIDIA GPU (GTX/RTX) -> GPU laptop tier: PP-OCRv5 on GPU, ~5 workers (thermal headroom), 220 dpi. Plug in + vents clear for the long run.",38,8.6,SUB,11); P.append(s)

# Panel 2: tiers
P.append(t(56,360,"2 · TIERS — RESOURCES SCALE TO THE PC (Win11-first, incomplete back to Win7)",12,ACC,700))
P.append(box(40,370,1100,140,PANEL,LINE,12))
rows=[("GPU laptop / workstation","NVIDIA+CUDA, Win10/11","GPU PP-OCRv5","5-8","220",GRN),
      ("Strong CPU","8+ cores, 16GB+","CPU","6","200",ACC),
      ("Modest CPU","4 cores, 8GB","CPU","3","165",AMB),
      ("Legacy / low-power","2 cores / <8GB / Win7-8","CPU (best-effort)","1-2","130",SUB)]
P.append(t(60,392,"tier",9,SUB,700)); P.append(t(330,392,"looks like",9,SUB,700)); P.append(t(640,392,"OCR",9,SUB,700)); P.append(t(840,392,"workers",9,SUB,700)); P.append(t(960,392,"dpi",9,SUB,700))
y=404
for tier,desc,ocr,w,dpi,c in rows:
    P.append(f'<rect x="60" y="{y}" width="8" height="8" rx="2" fill="{c}"/>')
    P.append(t(74,y+8,tier,9.2,TXT,700)); P.append(t(330,y+8,desc,9,SUB,400)); P.append(t(640,y+8,ocr,9,SUB,400)); P.append(t(850,y+8,w,9,TXT,700)); P.append(t(960,y+8,dpi,9,TXT,700)); y+=25
P.append(t(60,500,"Workers also capped by RAM (~1.2 GB each); laptop = thermal headroom; battery = throttled. GPU OCR is Win10+ (CUDA); Win7/8 -> CPU.",8.8,SUB,400))

# Panel 3: autonomous runner
P.append(t(56,534,"3 · AUTONOMOUS RUNNER -> run_ocr_auto.bat (unattended to 100%)",12,ACC,700))
P.append(box(40,544,1100,200,PANEL,LINE,12))
steps=[("probe","pick workers/dpi/gpu"),("install","GPU stack + PP-OCRv5 (+v4 fallback)"),("gpu_check","verify CUDA active"),
       ("snapshot","pre-ocr restore point"),("ocrall loop","auto-restart on crash -> 0 pending"),("report + open","detailed OCR report")]
x=58
for i,(h,d) in enumerate(steps):
    P.append(box(x,566,168,56,P2,LINE,8)); P.append(t(x+10,586,str(i+1)+" "+h,9.4,TXT,700)); s,_=wrap(x+10,602,d,28,8.0,SUB,10); P.append(s)
    if i<5: P.append(arrow(x+168,594,x+178,594,ACC))
    x+=180
P.append(t(58,648,"Self-healing: if a pass crashes with pages left, it waits 8s and resumes. /auto registers a logon task so it resumes after reboots (safe no-op once 100%).",9,SUB,400))
P.append(t(58,668,"Accuracy: PP-OCRv5 (~13 pts over v4) guarded by a self-test that auto-falls back to the proven PP-OCRv4 if the newer API differs -- never silently breaks extraction.",9,GRN,400))
s,_=wrap(58,692,"Honest: the OCR compute runs on YOUR GPU (the assistant has no GPU and can't run a multi-day job). I made it the fastest, most accurate, most autonomous it can be. When it hits 100% it writes docs/OCR-COMPLETION-REPORT.md and opens it; a daily reminder also tracks progress.",184,9,SUB,13); P.append(s)
P.append(t(40,H-12,"BUILT diagram. Dark (R3). v0.36.0 · 2026-06-02 · companions: SYSTEM-REQUIREMENTS.md, OCR-RUN-GUIDE.md, SETUP-GPU.md.",9.2,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/50-adaptive-ocr-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1180)
print("wrote", os.path.getsize(base+".pdf"), "bytes ->", base+".pdf")
