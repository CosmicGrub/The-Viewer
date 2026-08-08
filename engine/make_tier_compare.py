#!/usr/bin/env python3
"""Presentation page: 5 representative parts (rows) x the 3 CAD tiers (columns: v1 legacy / v2 lite / v3 modern),
rendered at the current max quality. Host-side (full cad_render.py). -> docs/cad_tier_comparison.png"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import cad_render
from PIL import Image, ImageDraw, ImageFont

DOCS = os.path.join(os.path.dirname(HERE), "docs"); os.makedirs(DOCS, exist_ok=True)

PARTS = [
    ("BEARING, BALL",   "OUTSIDE DIAMETER 52 MM; INSIDE DIAMETER 25 MM; WIDTH 15 MM", "3110-00-100-0001"),
    ("BOLT, MACHINE",   "THREAD 0.50 IN; LENGTH 3.0 IN; HEX HEAD",                    "5305-00-100-0002"),
    ("GEAR, SPUR",      "OUTSIDE DIAMETER 4.0 IN; FACE WIDTH 0.75 IN; 24 TEETH",      "3020-00-100-0003"),
    ("BUSHING, SLEEVE", "OUTSIDE DIAMETER 1.5 IN; INSIDE DIAMETER 1.0 IN; LENGTH 2.0 IN", "3120-00-100-0005"),
    ("SPRING, HELICAL", "OUTSIDE DIAMETER 1.2 IN; FREE LENGTH 3.5 IN; WIRE 0.12 IN",  "5360-00-100-0006"),
]
TIERS = [
    ("v1", "LEGACY · v1", "flat shading", (210, 120, 110)),
    ("v2", "LITE · v2", "+ specular / metallic", (224, 178, 92)),
    ("v3", "MODERN · v3", "+ FLIS colour / texture", (92, 200, 140)),
]

CW, CH = 460, 348            # cell size
GAP = 16; MARGIN = 26
HEAD = 96; COLHDR = 40; FOOT = 40
cols, rows = len(TIERS), len(PARTS)
GW = MARGIN*2 + cols*CW + (cols-1)*GAP
GH = HEAD + COLHDR + rows*CH + (rows-1)*GAP + FOOT
BG = (14, 19, 25); PANEL = (22, 28, 36); LINE = (44, 54, 66)

def font(sz, bold=True):
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    try: return ImageFont.truetype(p, sz)
    except Exception: return ImageFont.load_default()

img = Image.new("RGB", (GW, GH), BG); d = ImageDraw.Draw(img)
# header
d.text((MARGIN, 26), "THE VIEWER — CAD Tier Comparison", fill=(232, 238, 245), font=font(30))
d.text((MARGIN, 66), "The same five parts rendered at each RPS tier · auto-CAD v%s (max-quality) · scaled to FLIS dimensions" % cad_render.CAD_VERSION,
       fill=(150, 200, 255), font=font(15, False))
d.line([(MARGIN, HEAD-8), (GW-MARGIN, HEAD-8)], fill=LINE, width=1)
# column headers (tier badges)
cx0 = MARGIN
for ci, (st, lbl, sub, col) in enumerate(TIERS):
    x = cx0 + ci*(CW+GAP)
    d.rounded_rectangle([x, HEAD-2, x+CW, HEAD+COLHDR-10], radius=8, fill=PANEL, outline=col, width=2)
    d.text((x+14, HEAD+4), lbl, fill=col, font=font(16))
    tw = d.textlength(sub, font=font(12, False))
    d.text((x+CW-14-tw, HEAD+7), sub, fill=(150, 162, 176), font=font(12, False))
# grid of renders
y0 = HEAD + COLHDR
for ri, (name, chars, nsn) in enumerate(PARTS):
    y = y0 + ri*(CH+GAP)
    for ci, (st, lbl, sub, col) in enumerate(TIERS):
        x = cx0 + ci*(CW+GAP)
        im = cad_render.render(name, chars, nsn, w=CW, h=CH, style=st)
        img.paste(im, (x, y))
        d.rectangle([x, y, x+CW-1, y+CH-1], outline=LINE, width=1)
# footer
d.text((MARGIN, GH-30), "Representative CAD approximations — not manufacturing drawings. Tiers follow the RPS build (legacy / lite / modern).",
       fill=(120, 132, 146), font=font(12, False))
op = os.path.join(DOCS, "cad_tier_comparison.png"); img.save(op)
print("WROTE", op, img.size)
