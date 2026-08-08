#!/usr/bin/env python3
"""Render 10 varied parts as textured CAD images and arrange them on ONE contact sheet. RUN ON WINDOWS (host)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cad_render as C
from PIL import Image, ImageDraw, ImageFont

# (name, FLIS-style characteristics, nsn) — chosen to show varied shapes, materials, colours + textures
PARTS = [
    ("BOLT, MACHINE",       "OVERALL LENGTH: 2.0 IN THREAD DIAMETER: 0.375 IN MATERIAL: ALLOY STEEL", "5305-01-111-1111"),
    ("GEAR, SPUR",          "OUTSIDE DIAMETER: 3.0 IN OVERALL HEIGHT: 0.9 IN MATERIAL: BRASS",        "3020-01-222-2222"),
    ("BEARING, BALL",       "OUTSIDE DIAMETER: 2.2 IN WIDTH: 0.7 IN MATERIAL: STEEL",                 "3110-01-333-3333"),
    ("GASKET",              "OUTSIDE DIAMETER: 3.0 IN THICKNESS: 0.10 IN MATERIAL: RUBBER",           "5330-01-444-4444"),
    ("SPRING, HELICAL",     "OVERALL LENGTH: 2.4 IN OUTSIDE DIAMETER: 0.8 IN MATERIAL: STEEL",        "5360-01-555-5555"),
    ("BRACKET, MOUNTING",   "WIDTH: 3.0 IN HEIGHT: 2.5 IN MATERIAL: STEEL COLOR: OLIVE DRAB",         "5340-01-666-6666"),
    ("AIR CLEANER",         "DIAMETER: 6.0 IN LENGTH: 9.0 IN MATERIAL: ALUMINUM",                     "2940-01-777-7777"),
    ("PIN, STRAIGHT",       "OVERALL LENGTH: 2.0 IN DIAMETER: 0.30 IN MATERIAL: STAINLESS STEEL",     "5315-01-888-8888"),
    ("SWITCH, TOGGLE",      "WIDTH: 0.8 IN HEIGHT: 0.7 IN MATERIAL: PLASTIC COLOR: BLACK",            "5930-01-999-9999"),
    ("O-RING",              "OUTSIDE DIAMETER: 1.4 IN MATERIAL: RUBBER COLOR: BLACK",                 "5331-01-000-0000"),
]

def font(sz):
    for f in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "arialbd.ttf", "arial.ttf"):
        try: return ImageFont.truetype(f, sz)
        except Exception: continue
    return ImageFont.load_default()

def main():
    if C.Image is None:
        print("[ERROR] Pillow not available."); return 1
    CW, CH = 372, 300
    cols, rows, pad, head = 5, 2, 12, 56
    W = cols*CW + pad*(cols+1)
    H = head + rows*CH + pad*(rows+1)
    sheet = Image.new("RGB", (W, H), (18, 24, 30))
    dr = ImageDraw.Draw(sheet)
    dr.rectangle([(0, 0), (W, head)], fill=(28, 36, 46))
    dr.text((18, 12), "THE VIEWER — Auto-CAD: textured representative parts (v" + C.CAD_VERSION + ")",
            fill=(235, 238, 242), font=font(22))
    dr.text((18, 38), "Shape from name/NSN · scaled to FLIS dims · wrapped in its material texture + colour. Representative — not a manufacturing drawing.",
            fill=(150, 165, 180), font=font(12))
    for i, (nm, ch, ns) in enumerate(PARTS):
        try:
            im = C.render(nm, ch, ns, w=CW, h=CH)
        except Exception as e:
            im = Image.new("RGB", (CW, CH), (40, 44, 50)); ImageDraw.Draw(im).text((10, 10), "err: %s" % e, fill=(220, 120, 120))
        c, r = i % cols, i // cols
        x = pad + c*(CW+pad); y = head + pad + r*(CH+pad)
        sheet.paste(im, (x, y))
        dr.rectangle([(x, y), (x+CW-1, y+CH-1)], outline=(60, 70, 82))
    out = os.path.join(HERE, "..", "docs", "cad_contact_sheet.png")
    sheet.save(out, "PNG")
    print("wrote", os.path.abspath(out), sheet.size)
    return 0

if __name__ == "__main__":
    sys.exit(main())
