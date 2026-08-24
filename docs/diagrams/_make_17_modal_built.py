#!/usr/bin/env python3
"""Built result + data-flow: modal aligned to 104th header (dark R3)."""
import cairosvg, html, os
def esc(s): return html.escape(s)
W,H=1180,760
BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"; ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; RED="#e0564f"
PAPER="#f4f1ea"; INK="#1c1a17"; PRED="#c01a1a"; PLINE="#b9b2a3"
def box(x,y,w,h,fill=P2,stroke=LINE,rx=9,sw=1): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def t(x,y,s,size=12,fill=TXT,w=400,anchor="start"): return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'
def fld(x,y,w,label,val):
    o=[box(x,y,w,40,"#232c39",LINE,7)]
    o.append(t(x+9,y+15,label,8.5,SUB,700))
    o.append(t(x+9,y+31,val,11,TXT,400) if val else t(x+9,y+31,"—",11,"#5d6675",400))
    return "".join(o)
P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
P.append(box(0,0,W,H,BG,BG,0))
P.append(t(40,46,"Modal aligned to the 104th sheet header — built",22,TXT,700))
P.append(t(40,70,"v0.15.0 · 1:1 field order & labels · header fields always shown · live preview · required = Bumper# + Fault. Additive (R1).",11.5,SUB,400))
P.append(f'<line x1="40" y1="86" x2="{W-40}" y2="86" stroke="{LINE}"/>')

# LEFT: the modal mockup
mx,mw=40,560; my=104
P.append(box(mx,my,mw,620,PANEL,LINE,12))
P.append(t(mx+20,my+30,"Start a maintenance session",15,TXT,700))
P.append(t(mx+20,my+50,"Header fields match the 104th sheet — what you fill is what prints.",10,SUB,400))
# search sec
sx,sw=mx+20,mw-40; sy=my+62
P.append(box(sx,sy,sw,62,"#16223a","#2c3f5e",9))
P.append(t(sx+12,sy+18,"FIND A PART · SEARCH ONLY — DOES NOT PRINT ON THE SHEET",8.5,"#9bc0ff",700))
P.append(fld(sx+12,sy+24,sw-24,"WHAT DO YOU NEED?","gasket water pump"))
# header sec
hy=sy+78
P.append(box(sx,hy,sw,300,"#141a23",LINE,9))
P.append(t(sx+12,hy+18,"PARTS REQUEST SHEET HEADER · FILLS THE 104TH BLOCKS",8.5,AMB,700))
gx=sx+12; gw=sw-24; yy=hy+26
P.append(fld(gx,yy,gw,"MECHANIC'S NAME (PRINT/SIGN)","SPC R. Alvarez")); yy+=48
half=(gw-10)/2
P.append(fld(gx,yy,half,"BUMPER#  *","B-14")); P.append(fld(gx+half+10,yy,half,"FAULT  *","No-start; alt not charging")); yy+=48
third=(gw-20)/3
P.append(fld(gx,yy,third,"TM","TM 9-2320-280-20-2")); P.append(fld(gx+third+10,yy,third,"UOC","")); P.append(fld(gx+2*third+20,yy,third,"TECH STATUS","NMC")); yy+=48
P.append(fld(gx,yy,gw,"MOTOR SERGEANT / SENIOR MECHANIC","SFC J. Doe")); yy+=44
# live preview paper
py=hy+312
P.append(t(sx+2,py-4,"LIVE SHEET-HEADER PREVIEW",8.5,SUB,700))
P.append(box(sx,py,sw,118,PAPER,PLINE,5))
cxp=sx+sw/2
P.append(t(cxp,py+18,"104TH ECC PARTS REQUEST SHEET",10,INK,700,"middle"))
P.append(t(cxp,py+31,"(FILL OUT ALL BLOCKS)",7.5,PRED,700,"middle"))
P.append(t(sx+12,py+50,"MECHANIC’S NAME (PRINT/SIGN): SPC R. Alvarez",8.5,INK,400))
P.append(t(sx+12,py+66,"BUMPER#: B-14    FAULT: No-start; alt not charging",8.5,INK,400))
P.append(t(sx+12,py+82,"TM: TM 9-2320-280-20-2   UOC: —   TECH STATUS: NMC",8.5,INK,400))
P.append(t(sx+12,py+101,"MOTOR SERGEANT / SENIOR MECHANIC: SFC J. Doe",8.5,INK,400))
P.append(box(sx,py+128,sw,34,GRN,GRN,7)); P.append(t(cxp,py+150,"Start session & search",12,"#eafff0",700,"middle"))

# RIGHT: data-flow mapping
rx,rw=632,508; ry=104
P.append(box(rx,ry,rw,400,PANEL,LINE,12))
P.append(f'<rect x="{rx}" y="{ry}" width="{rw}" height="30" rx="12" fill="{P2}" stroke="{LINE}"/>')
P.append(t(rx+14,ry+20,"DATA FLOW · modal field → SESSION → sheet block",12,ACC,700))
maps=[("#m_mechanic","mechanic","MECHANIC'S NAME (PRINT/SIGN)"),
      ("#m_bumper *","bumper","BUMPER#"),
      ("#m_fault *","fault","FAULT"),
      ("#m_tm","tm","TM"),
      ("#m_uoc","uoc","UOC"),
      ("#m_tech","tech_status","TECH STATUS"),
      ("#m_motor","motor_sergeant","MOTOR SERGEANT / SR MECH")]
yy=ry+46
P.append(t(rx+20,yy,"modal id",8.5,SUB,700)); P.append(t(rx+185,yy,"SESSION key",8.5,SUB,700)); P.append(t(rx+330,yy,"104th block",8.5,SUB,700)); yy+=6
for mid,sk,blk in maps:
    P.append(box(rx+18,yy,rw-36,40,P2,LINE,7))
    P.append(t(rx+30,yy+24,mid,10.5,"#cfe0ff",700))
    P.append(t(rx+150,yy+24,"→",11,SUB,400)); P.append(t(rx+170,yy+24,sk,10.5,TXT,400))
    P.append(t(rx+300,yy+24,"→",11,SUB,400)); P.append(t(rx+320,yy+24,blk,9.5,"#bfe6c5",400))
    yy+=46
# notes
ny=ry+416
P.append(box(rx,ny,rw,240,PANEL,LINE,12))
P.append(t(rx+18,ny+26,"WHAT CHANGED",12,ACC,700))
notes=[
 ("1:1 order & exact labels","Modal rows now mirror the sheet (Mechanic → Bumper|Fault → TM|UOC|Tech → Motor sergeant), using the sheet's wording."),
 ("Header always visible","UOC / Tech status / Motor sergeant no longer hidden in Simple view — they're header blocks ('fill all blocks'). Simple now only hides cart FEDLOG."),
 ("Live preview","A paper-style header replica fills in as you type — what you enter = what prints (mirrors parts_request_pdf.py)."),
 ("Required = Bumper# + Fault","Unchanged; the rest are recommended. Search/express field set apart — it never prints."),
]
yy=ny+44
for h,d in notes:
    P.append(t(rx+18,yy,"• "+h,10.5,TXT,700)); yy+=15
    words=d.split(); line=""; 
    for wd in words:
        if len(line)+len(wd)+1>74: P.append(t(rx+28,yy,line,9.3,SUB,400)); yy+=14; line=wd
        else: line=(line+" "+wd).strip()
    if line: P.append(t(rx+28,yy,line,9.3,SUB,400)); yy+=20
P.append(t(40,H-12,"No schema change; field IDs/SESSION keys unchanged → 104th PDF output identical. Dark (R3) · CHANGELOG 0.15.0 (R4) · visual panel (R5).",10,"#6b7280",400))
P.append("</svg>")
svg="\n".join(P)
base="/sessions/beautiful-admiring-dirac/mnt/THE VIEWER/docs/diagrams/17-modal-header-aligned"
open(base+".svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
# (PNG preview removed 2026-08-18: redundant with the .svg above; see docs/diagrams/_common.py render() note)
print("wrote", os.path.getsize(base+".pdf"),"bytes")
