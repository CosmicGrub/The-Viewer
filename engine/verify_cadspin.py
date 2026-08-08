#!/usr/bin/env python3
"""Verify the interactive-CAD turntable: render a spin sheet with cad_render.render_spin() and prove the part
actually ROTATES by laying a few frames side by side into docs/cadspin_proof.png. Host-side (full cad_render.py)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cad_render
from PIL import Image, ImageDraw

DOCS = os.path.join(os.path.dirname(HERE), "docs")
os.makedirs(DOCS, exist_ok=True)

# a few representative parts (name, characteristics, fake nsn) — clear, recognisable rotation
SAMPLES = [
    ("BEARING, BALL", "OUTSIDE DIAMETER 52 MM; INSIDE DIAMETER 25 MM; WIDTH 15 MM", "3110-00-100-0001"),
    ("BOLT, MACHINE", "THREAD 0.50 IN; LENGTH 3.0 IN; HEX HEAD", "5305-00-100-0002"),
    ("GEAR, SPUR", "OUTSIDE DIAMETER 4.0 IN; FACE WIDTH 0.75 IN; 24 TEETH", "3020-00-100-0003"),
]

def montage_of(name, chars, nsn, n=12, picks=(0, 3, 6, 9)):
    sheet, frames = cad_render.render_spin(name, chars, nsn, n=n, style="v3")
    fw = sheet.width // frames; fh = sheet.height
    out = Image.new("RGB", (fw*len(picks), fh+26), (20, 26, 34))
    d = ImageDraw.Draw(out)
    d.text((8, 6), "%s  —  %d-frame turntable, showing frames %s (rotation about the vertical axis)" %
           (name, frames, ",".join(str(p) for p in picks)), fill=(150, 200, 255))
    for i, p in enumerate(picks):
        fr = sheet.crop((p*fw, 0, (p+1)*fw, fh))
        out.paste(fr, (i*fw, 26))
    return out, frames

def main():
    rows = []
    for name, chars, nsn in SAMPLES:
        m, frames = montage_of(name, chars, nsn)
        rows.append(m)
        print("rendered %-16s frames=%d  frame=%dx%d" % (name, frames, m.width//4, m.height-26))
    W = max(r.width for r in rows); Htot = sum(r.height for r in rows) + 8*len(rows)
    big = Image.new("RGB", (W, Htot), (12, 16, 22)); y = 0
    for r in rows:
        big.paste(r, (0, y)); y += r.height + 8
    op = os.path.join(DOCS, "cadspin_proof.png")
    big.save(op)
    print("WROTE", op, big.size)
    # confirm frames differ (rotation actually happened): compare frame 0 vs frame 6 of the first sample
    sheet, frames = cad_render.render_spin(*SAMPLES[0][:2], SAMPLES[0][2], n=12, style="v3")
    fw = sheet.width // frames
    import hashlib
    h0 = hashlib.md5(sheet.crop((0, 0, fw, sheet.height)).tobytes()).hexdigest()
    h6 = hashlib.md5(sheet.crop((6*fw, 0, 7*fw, sheet.height)).tobytes()).hexdigest()
    print("frame0 != frame6 (rotates):", h0 != h6)

if __name__ == "__main__":
    main()
