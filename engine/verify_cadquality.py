#!/usr/bin/env python3
"""Prove the CAD q-pass: render every TIER (v1/v2/v3) for several parts into one grid so the quality + the
tier ladder are both visible. Host-side (full cad_render.py). -> docs/cad_quality_v4.png"""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import cad_render
from PIL import Image, ImageDraw, ImageFont

DOCS = os.path.join(os.path.dirname(HERE), "docs"); os.makedirs(DOCS, exist_ok=True)
SAMPLES = [
    ("BEARING, BALL", "OUTSIDE DIAMETER 52 MM; INSIDE DIAMETER 25 MM; WIDTH 15 MM", "3110-00-100-0001"),
    ("BOLT, MACHINE", "THREAD 0.50 IN; LENGTH 3.0 IN; HEX HEAD", "5305-00-100-0002"),
    ("GEAR, SPUR", "OUTSIDE DIAMETER 4.0 IN; FACE WIDTH 0.75 IN; 24 TEETH", "3020-00-100-0003"),
    ("GASKET", "OUTSIDE DIAMETER 3.0 IN; INSIDE DIAMETER 2.2 IN; THICKNESS 0.10 IN", "5330-00-100-0004"),
]
TIERS = [("v1", "LEGACY (v1) — flat"), ("v2", "LITE (v2) — +specular/metallic"), ("v3", "MODERN (v3) — +colour/texture")]
W, Hc = 430, 330
def font(sz):
    try: return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", sz)
    except Exception: return ImageFont.load_default()

cols = len(TIERS); rows = len(SAMPLES)
pad, head = 8, 30
GW = cols*W + (cols+1)*pad; GH = head + rows*(Hc+18) + pad
big = Image.new("RGB", (GW, GH), (16, 20, 26)); d = ImageDraw.Draw(big)
d.text((pad, 8), "CAD q-pass (CAD_VERSION %s): every tier, SS3 + finer mesh + silhouette + contact shadow" % cad_render.CAD_VERSION,
       fill=(150, 200, 255), font=font(15))
for ci, (st, lbl) in enumerate(TIERS):
    d.text((pad + ci*(W+pad) + 6, head-2), lbl, fill=(120, 200, 255), font=font(12))
y = head + 14; times = []
for name, chars, nsn in SAMPLES:
    for ci, (st, lbl) in enumerate(TIERS):
        t0 = time.time()
        im = cad_render.render(name, chars, nsn, w=W, h=Hc, style=st)
        times.append(time.time()-t0)
        big.paste(im, (pad + ci*(W+pad), y))
    y += Hc + 18
op = os.path.join(DOCS, "cad_quality_v5.png"); big.save(op)
print("WROTE", op, big.size)
print("tiers rendered for:", ", ".join(s[0] for s in SAMPLES))
print("render time: avg %.2fs  max %.2fs  (per image, SS=%d)" % (sum(times)/len(times), max(times), 4))
