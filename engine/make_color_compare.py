#!/usr/bin/env python3
"""BEFORE / AFTER: colour now renders on EVERY CAD tier (was v3-only). Each cell = old (grey on v1/v2) | new
(coloured). Host-side (full cad_render.py). -> docs/cad_color_before_after.png"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import cad_render
from PIL import Image, ImageDraw, ImageFont

DOCS = os.path.join(os.path.dirname(HERE), "docs"); os.makedirs(DOCS, exist_ok=True)

PARTS = [
    ("BRACKET, MOUNTING", "LENGTH 5.0 IN; WIDTH 3.0 IN; HEIGHT 1.0 IN; COLOR OLIVE DRAB", "5340-00-100-0010"),
    ("BEARING, BALL",     "OUTSIDE DIAMETER 52 MM; INSIDE DIAMETER 25 MM; WIDTH 15 MM",    "3110-00-100-0001"),
    ("GEAR, SPUR",        "OUTSIDE DIAMETER 4.0 IN; FACE WIDTH 0.75 IN; 24 TEETH",          "3020-00-100-0003"),
    ("GASKET",            "OUTSIDE DIAMETER 3.0 IN; INSIDE DIAMETER 2.2 IN; THICKNESS 0.10 IN; RUBBER", "5330-00-100-0004"),
    ("HANDLE",            "LENGTH 6.0 IN; DIAMETER 0.9 IN; COLOR BLACK",                    "5340-00-100-0011"),
]
TIERS = [("v1", "LEGACY · v1", (210, 120, 110)), ("v2", "LITE · v2", (224, 178, 92)), ("v3", "MODERN · v3", (92, 200, 140))]

SW, CH = 205, 244            # each sub-render
GAPin = 8                    # gap between before|after
CW = SW*2 + GAPin            # cell width
LG = 122; MARGIN = 22; GAP = 14
HEAD = 92; COLHDR = 30; FOOT = 38
cols, rows = len(TIERS), len(PARTS)
GW = MARGIN*2 + LG + cols*CW + (cols-1)*GAP
GH = HEAD + COLHDR + rows*CH + (rows-1)*GAP + FOOT
BG = (14, 19, 25); PANEL = (22, 28, 36); LINE = (44, 54, 66)

def font(sz, bold=True):
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    try: return ImageFont.truetype(p, sz)
    except Exception: return ImageFont.load_default()

img = Image.new("RGB", (GW, GH), BG); d = ImageDraw.Draw(img)
d.text((MARGIN, 22), "CAD colour + material texture — now on EVERY tier  (before / after)", fill=(232, 238, 245), font=font(26))
d.text((MARGIN, 58), "Each cell:  LEFT = before (grey, untextured on v1/v2)   |   RIGHT = after (FLIS colour + material texture on every tier).",
       fill=(150, 200, 255), font=font(14, False))
d.line([(MARGIN, HEAD-6), (GW-MARGIN, HEAD-6)], fill=LINE, width=1)
gx0 = MARGIN + LG
for ci, (st, lbl, col) in enumerate(TIERS):
    x = gx0 + ci*(CW+GAP)
    d.rounded_rectangle([x, HEAD-2, x+CW, HEAD+COLHDR-8], radius=8, fill=PANEL, outline=col, width=2)
    d.text((x+12, HEAD+3), lbl, fill=col, font=font(15))
    d.text((x+SW-30, HEAD+5), "before", fill=(150, 162, 176), font=font(11, False))
    d.text((x+SW+GAPin+SW-26, HEAD+5), "after", fill=(150, 162, 176), font=font(11, False))
y0 = HEAD + COLHDR
for ri, (name, chars, nsn) in enumerate(PARTS):
    y = y0 + ri*(CH+GAP)
    d.text((MARGIN+6, y + CH//2 - 8), name, fill=(214, 222, 232), font=font(13))
    for ci, (st, lbl, col) in enumerate(TIERS):
        x = gx0 + ci*(CW+GAP)
        before = cad_render.render(name, chars, nsn, w=SW, h=CH, style=st, title=False, colorize=(st == "v3"), texturize=(st == "v3"))
        after  = cad_render.render(name, chars, nsn, w=SW, h=CH, style=st, title=False, colorize=True, texturize=True)
        img.paste(before, (x, y)); img.paste(after, (x+SW+GAPin, y))
        d.line([(x+SW+GAPin//2, y), (x+SW+GAPin//2, y+CH)], fill=(70, 80, 92), width=2)
        d.rectangle([x, y, x+CW-1, y+CH-1], outline=LINE, width=1)
d.text((MARGIN, GH-30), "FLIS colour + procedural material texture (brushed metal / rubber grain / wood / CARC) now applies at v1, v2 and v3 (max-quality SS4).",
       fill=(120, 132, 146), font=font(12, False))
op = os.path.join(DOCS, "cad_color_texture_before_after.png"); img.save(op)
print("WROTE", op, img.size)
