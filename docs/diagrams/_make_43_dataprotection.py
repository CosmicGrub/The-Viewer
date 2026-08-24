#!/usr/bin/env python3
"""BUILT 0.29.0: truncation root cause + safeguard (snapshot/verify/recover) + tests (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,900
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
P.append(t(40,46,"BUILT — Data protection: root cause · safeguard · recovery  (v0.29.0)",20,TXT,700))
P.append(t(40,70,"The 'truncation' was a sandbox read-cache artifact (your files were never damaged). We still built real protection: atomic writes, a snapshot vault, damage detection, and byte-for-byte recovery.",11,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# Panel 1: root cause
P.append(t(56,116,"1 · ROOT CAUSE (reproduced)",12,ACC,700))
P.append(box(40,126,1100,118,PANEL,LINE,12))
P.append(box(60,144,470,84,"#13241c",GRN,8))
P.append(t(80,166,"guest writes -> guest reads",10.5,"#bfe6cf",700)); s,_=wrap(80,184,"the Linux sandbox reading its own writes is ALWAYS coherent (47,843 bytes out = in, even short->long re-edits).",70,9,"#8fbf9f",12); P.append(s)
P.append(t(80,224,"= NOT the problem",9.4,GRN,700))
P.append(box(650,144,470,84,"#2a1a1a",RED,8))
P.append(t(670,166,"host writes -> guest reads",10.5,"#f0b3b0",700)); s,_=wrap(670,184,"after the editor (host) rewrites a file, the sandbox page cache serves a STALE shorter length until it revalidates. Host file stays intact.",72,9,"#cf9a98",12); P.append(s)
P.append(t(670,224,"= the artifact (read-side only)",9.4,RED,700))

# Panel 2: safeguard
P.append(t(56,274,"2 · SAFEGUARD (engine/safeguard.py)  — atomic writes · snapshot vault · verify · recover",12,ACC,700))
P.append(box(40,284,1100,176,PANEL,LINE,12))
P.append(box(60,304,150,60,P2,LINE,8)); P.append(t(135,328,"critical files",10,TXT,700,"middle")); P.append(t(135,344,"engine/ui/docs/db",8.6,SUB,400,"middle"))
P.append(arrow(210,334,236,334,TEAL))
P.append(box(240,304,200,60,"#13241c",GRN,8)); P.append(t(340,326,"snapshot",10.5,"#bfe6cf",700,"middle")); P.append(t(340,342,"SHA-256 per file",8.6,"#8fbf9f",400,"middle")); P.append(t(340,356,"-> vault/SNAP_<ts>",8.4,"#8fbf9f",400,"middle"))
P.append(arrow(440,334,466,334,TEAL))
P.append(box(470,304,200,60,P2,LINE,8)); P.append(t(570,326,"verify",10.5,AMB,700,"middle")); P.append(t(570,342,"classify damage vs",8.6,SUB,400,"middle")); P.append(t(570,356,"last good snapshot",8.4,SUB,400,"middle"))
P.append(arrow(670,334,696,334,TEAL))
P.append(box(700,304,200,60,"#13241c",GRN,8)); P.append(t(800,326,"recover",10.5,"#bfe6cf",700,"middle")); P.append(t(800,342,"restore + re-hash",8.6,"#8fbf9f",400,"middle")); P.append(t(800,356,"(the archaeologist)",8.4,"#8fbf9f",400,"middle"))
P.append(box(930,304,190,60,PANEL,ACC,8,1)); P.append(t(1025,326,"atomic write",9.6,ACC,700,"middle")); P.append(t(1025,342,"temp+fsync+replace",8.4,SUB,400,"middle")); P.append(t(1025,356,"no half-written files",8.4,SUB,400,"middle"))
# status legend
P.append(t(60,392,"verify classifies:",9.4,SUB,700))
for i,(lab,c) in enumerate([("OK",GRN),("TRUNCATED",AMB),("CORRUPTED",RED),("EMPTY",AMB),("MISSING",RED),("MODIFIED",ACC)]):
    P.append(f'<rect x="{180+i*150}" y="382" width="10" height="10" rx="2" fill="{c}"/>'); P.append(t(196+i*150,391,lab,9,SUB,400))
s,_=wrap(60,418,"Heavy viewer.db: SQLite integrity_check always; consistent online-backup copy only on demand (/withdb). Corpus (E:\\) is read-only source, not snapshotted. Snapshots are additive (R6); main index never modified (R1).",184,9,SUB,12); P.append(s)

# Panel 3: tests
P.append(t(56,490,"3 · TESTED TO A STRANGLEHOLD",12,ACC,700))
P.append(box(40,500,1100,330,PANEL,LINE,12))
# three stat tiles
tiles=[("19 / 19","pillar tests pass",GRN),("11 / 11","truncation + recovery tests pass",GRN),("36 / 38","mutants killed (95%) — 2 equivalent",GRN)]
x=60
for big,lab,c in tiles:
    P.append(box(x,518,346,58,P2,c,10,1)); P.append(t(x+18,548,big,18,TXT,700)); P.append(t(x+150,548,lab,9.6,SUB,400))
    x+=360
# damage matrix
P.append(t(60,604,"Damage deliberately injected & recovered byte-for-byte:",10.5,TXT,700))
dmg=["last line (light)","50% (medium)","10 bytes (hard)","0 bytes (empty)","partial UTF-8","byte-flip corrupt","deleted (missing)","multi-file","corrupted vault relic","corrupted DB header"]
for i,d in enumerate(dmg):
    cx=60+(i%5)*220; cy=624+(i//5)*20
    P.append(t(cx,cy,"✓ "+d,9.2,SUB,400))
# mutation rounds
P.append(t(60,684,"Mutation testing — 2 rounds:",10.5,TXT,700))
P.append(box(60,696,520,52,P2,LINE,8)); P.append(t(74,716,"Round 1 · engine logic (core_pillars)",10,TXT,700)); P.append(t(74,733,"26 faults injected -> 25 killed (96%)",9,SUB,400))
P.append(box(600,696,520,52,P2,LINE,8)); P.append(t(614,716,"Round 2 · safeguard itself",10,TXT,700)); P.append(t(614,733,"12 faults injected -> 11 killed (92%)",9,SUB,400))
s,_=wrap(60,772,"Round 2 mutates the protection layer (blind-to-missing, trunc->ok, skip-write, hash-blind, dbcheck-always-ok ...) and confirms the truncation suite catches them — the safeguard guards are themselves guarded. Survivors are provably equivalent mutants.",184,9.2,SUB,13); P.append(s)

P.append(t(40,H-12,"BUILT diagram. Dark (R3). v0.29.0 · 2026-06-02 · companion: DATA-PROTECTION.md · run via run_safeguard.bat / run_tests.bat.",9.2,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/43-data-protection-built"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"), "bytes ->", base+".pdf")
