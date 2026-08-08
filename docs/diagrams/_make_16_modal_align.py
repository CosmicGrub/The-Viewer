#!/usr/bin/env python3
"""Markup: aligning the onboarding modal to the 104th sheet header (proposal, dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,860
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"
PAPER="#f4f1ea"; INK="#1c1a17"; PRED="#c01a1a"; PLINE="#b9b2a3"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start",ff=None): 
    f=f' font-family="{ff}"' if ff else ''
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}"{f}>{esc(s)}</text>'
def uline(x,y,x2,col=PLINE): return f'<line x1="{x}" y1="{y}" x2="{x2}" y2="{y}" stroke="{col}" stroke-width="1"/>'
def field(x,y,w,label,req=False,tint=None):
    out=[box(x,y,w,42,tint or "#232c39",LINE,7)]
    out.append(t(x+10,y+16,label,9.5,SUB if not req else "#cfe0ff",700))
    if req: out.append(t(x+w-12,y+16,"required",8.5,RED,700,"end"))
    out.append(uline(x+10,y+33,x+w-10,"#3a4452"))
    return "".join(out)
P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
P.append(box(0,0,W,H,BG,BG,0))
P.append(t(40,48,"Matching the onboarding modal to the 104th sheet header",23,TXT,700))
P.append(t(40,73,"Proposal & markup — the modal already collects every header field; this is about fidelity (order, labels, grouping) and one conflict. Decide before we build.",11.5,SUB,400))
P.append(f'<line x1="40" y1="90" x2="{W-40}" y2="90" stroke="{LINE}"/>')

# ---- LEFT: the sheet header (paper) ----
lx,lw=40,530; ly=110
P.append(box(lx,ly,lw,400,PANEL,LINE,12))
P.append(f'<rect x="{lx}" y="{ly}" width="{lw}" height="30" rx="12" fill="{P2}" stroke="{LINE}"/>')
P.append(t(lx+14,ly+20,"THE 104TH SHEET HEADER  ·  source of truth",12,ACC,700))
# paper card
px,py,pw=lx+20,ly+46,lw-40
P.append(box(px,py,pw,320,PAPER,PLINE,6))
cx=px+pw/2
P.append(t(cx,py+30,"104TH ECC PARTS REQUEST SHEET",13,INK,700,"middle"))
P.append(t(cx,py+46,"(FILL OUT ALL BLOCKS)",9,PRED,700,"middle"))
yy=py+78
P.append(t(px+16,yy,"MECHANIC'S NAME (PRINT/SIGN):",9.5,INK,700)); P.append(uline(px+200,yy+3,px+pw-16)); yy+=24
P.append(t(px+16,yy,"BUMPER#:",9.5,INK,700)); P.append(uline(px+75,yy+3,px+200)); 
P.append(t(px+220,yy,"FAULT:",9.5,INK,700)); P.append(uline(px+265,yy+3,px+pw-16)); yy+=24
P.append(t(px+16,yy,"TM:",9.5,INK,700)); P.append(uline(px+42,yy+3,px+170));
P.append(t(px+185,yy,"UOC:",9.5,INK,700)); P.append(uline(px+222,yy+3,px+320));
P.append(t(px+335,yy,"TECH STATUS:",9.5,INK,700)); P.append(uline(px+420,yy+3,px+pw-16)); yy+=22
# item block hint
P.append(box(px+16,yy,pw-32,52,"#ece8df",PLINE,4,1))
P.append(t(px+26,yy+18,"ITEM NAME: ______________   NSN: ____________",8.5,INK,400))
P.append(t(px+26,yy+32,"QTY:__  FIG#:__  PART#:______",8.5,INK,400))
P.append(t(px+26,yy+46,"(FEDLOG) UNIT PRICE:__  AAC:__  ARC:__",8,PRED,400))
P.append(t(px+pw-26,yy+30,"× 6",10,SUB,700,"end"))
yy+=66
P.append(t(px+16,yy,"MOTOR SERGEANT / SENIOR MECHANIC:",9.5,INK,700)); P.append(uline(px+250,yy+3,px+pw-16))
P.append(t(lx+20,ly+390,"7 header blocks total (incl. footer). No DATE / UNIT / DODAAC blocks on this sheet.",10,SUB,400))

# ---- RIGHT: proposed modal ----
rx,rw=600,540; ry=110
P.append(box(rx,ry,rw,400,PANEL,LINE,12))
P.append(f'<rect x="{rx}" y="{ry}" width="{rw}" height="30" rx="12" fill="{P2}" stroke="{LINE}"/>')
P.append(t(rx+14,ry+20,"PROPOSED MODAL  ·  mirrors the header 1:1",12,GRN,700))
mx=rx+18; mw=rw-36
P.append(t(mx,ry+52,"Start a maintenance session",14,TXT,700))
# search section (set apart)
P.append(box(mx,ry+62,mw,58,"#16223a","#2c3f5e",8))
P.append(t(mx+10,ry+80,"FIND A PART  ·  search only — does not print on the sheet",9,"#9bc0ff",700))
P.append(field(mx+10,ry+86,mw-20,"What do you need?  (part name · part # · NSN · 4-digit last-4)"))
# header section
hy=ry+132
P.append(t(mx,hy,"PARTS REQUEST SHEET HEADER  ·  fills the blocks at left",9.5,AMB,700))
hy+=8
P.append(field(mx,hy,mw,"MECHANIC'S NAME (PRINT/SIGN)")); hy+=50
half=(mw-12)/2
P.append(field(mx,hy,half,"BUMPER#",req=True)); P.append(field(mx+half+12,hy,half,"FAULT",req=True)); hy+=50
third=(mw-24)/3
P.append(field(mx,hy,third,"TM")); P.append(field(mx+third+12,hy,third,"UOC")); P.append(field(mx+2*third+24,hy,third,"TECH STATUS")); hy+=50
P.append(field(mx,hy,mw,"MOTOR SERGEANT / SENIOR MECHANIC")); hy+=50
P.append(t(mx,hy+4,"Live mini-preview of the header updates as you type (what you fill = what prints).",9.5,SUB,400))

# ---- recommendation cards ----
cy=540
P.append(t(40,cy-4,"RECOMMENDATIONS",12,ACC,700))
recs=[
 ("1 · Exact labels & order","Modal rows match the sheet 1:1: Mechanic → Bumper|Fault → TM|UOC|Tech → Motor sergeant. Use the sheet's exact wording.",GRN),
 ("2 · Group + separate search","Put the 7 header fields in one labelled group; set the search/express field visually apart (it never prints).",GRN),
 ("3 · Honor 'FILL OUT ALL BLOCKS'","Conflict today: Simple mode hides UOC/Tech/Motor — but they're header blocks. Fix: always show header fields; Simple only hides per-item FEDLOG.",AMB),
 ("4 · Live header preview","Render a small replica of the sheet header inside the modal that fills in as you type — true visual parity.",ACC),
 ("5 · Required = Bumper# + Fault","Keep just those two required (most critical); mark the rest 'recommended' so a quick request isn't blocked.",GRN),
 ("6 · Don't invent fields","This sheet has no DATE/UNIT/DODAAC — we won't add blocks it doesn't have. Stays a faithful replica (R1).",GRN),
]
cw=362; gap=15; x0=40
for i,(h,d,acc) in enumerate(recs):
    col=i%3; row=i//3
    x=x0+col*(cw+gap); y=cy+10+row*138
    P.append(box(x,y,cw,124,PANEL,LINE,10))
    P.append(f'<rect x="{x}" y="{y}" width="5" height="124" rx="2" fill="{acc}"/>')
    P.append(t(x+18,y+26,h,12,TXT,700))
    # wrap desc
    words=d.split(); line=""; ln=0
    for wd in words:
        if len(line)+len(wd)+1>52:
            P.append(t(x+18,y+50+ln*17,line,10,SUB,400)); line=wd; ln+=1
        else: line=(line+" "+wd).strip()
    if line: P.append(t(x+18,y+50+ln*17,line,10,SUB,400))
P.append(t(40,H-14,"Proposal only — nothing built yet. Dark (R3). On approval: ships with a data-flow diagram (R2), CHANGELOG (R4) + visual panel (R5).",10,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/16-modal-sheet-alignment"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base+"_preview.png", output_width=1180)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
