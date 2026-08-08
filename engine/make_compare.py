#!/usr/bin/env python3
"""Render 50 real parts in v1 (original) vs v2 (oriented + specular/metallic) and lay them out side-by-side on one
comparison sheet. Read-only on the index. RUN ON WINDOWS (host). -> docs/cad_v1_vs_v2.png"""
import os, sys, sqlite3
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cad_render as C
from PIL import Image, ImageDraw, ImageFont
DB = os.path.abspath(os.path.join(HERE, "..", "index", "viewer.db"))
_THREED_WHERE = ("characteristics IS NOT NULL AND characteristics<>'' AND ("
                 "upper(characteristics) LIKE '%DIAMETER%' OR upper(characteristics) LIKE '%LENGTH%' OR "
                 "upper(characteristics) LIKE '%HEIGHT%' OR upper(characteristics) LIKE '%WIDTH%' OR "
                 "upper(characteristics) LIKE '%THICKNESS%')")

def font(sz):
    for f in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "arialbd.ttf", "arial.ttf"):
        try: return ImageFont.truetype(f, sz)
        except Exception: continue
    return ImageFont.load_default()

def pick(n=50):
    con = sqlite3.connect("file:%s?mode=ro" % DB, uri=True); con.row_factory = sqlite3.Row
    rows = con.execute("SELECT nsn, item_name, characteristics FROM ref_nsn WHERE " + _THREED_WHERE +
                       " ORDER BY item_name LIMIT 5000").fetchall()
    con.close()
    buckets = defaultdict(list)
    for r in rows:
        nm = r["item_name"] or ""; ch = r["characteristics"] or ""; ns = r["nsn"] or ""
        buckets[C.classify(nm, ch, ns)].append((nm, ch, ns))
    # asymmetric families first (where the orientation fix is most visible)
    order = ["bolt","bracket","lever","canister","cylinder","gear","bearing","shaft","cover","link","switch",
             "spring","plate","tube","rivet","nut","washer","pad","gasket","oring","box","battery"]
    picked, per = [], 3
    for fam in order:
        for item in buckets.get(fam, [])[:per]:
            picked.append(item + (fam,))
    if len(picked) < n:
        for fam, lst in buckets.items():
            for item in lst[per:]:
                if len(picked) >= n: break
                picked.append(item + (fam,))
            if len(picked) >= n: break
    return picked[:n]

def main():
    if C.Image is None: print("[ERROR] Pillow not available."); return 1
    if not os.path.exists(DB): print("[ERROR] index not found:", DB); return 1
    parts = pick(50)
    CW, CH, gap, lblh, pad, head, cols = 210, 168, 8, 20, 10, 60, 5
    cellW = 2*CW + gap; cellH = CH + lblh
    rows = (len(parts) + cols - 1)//cols
    W = cols*cellW + pad*(cols+1); H = head + rows*cellH + pad*(rows+1)
    sheet = Image.new("RGB", (W, H), (18, 24, 30)); dr = ImageDraw.Draw(sheet)
    dr.rectangle([(0, 0), (W, head)], fill=(28, 36, 46))
    dr.text((16, 11), "THE VIEWER — Auto-CAD: v1 (original)  vs  v2 (right-side-up + specular/metallic) — %d parts" % len(parts),
            fill=(235, 238, 242), font=font(21))
    dr.text((16, 37), "Left = v1 (head-down, flat diffuse).  Right = v2 (oriented up, metallic specular highlight).  Same shape + FLIS dimensions — only the renderer changed.",
            fill=(150, 165, 180), font=font(12))
    for i, (nm, ch, ns, fam) in enumerate(parts):
        try: im1 = C.render(nm, ch, ns, w=CW, h=CH, style="v1")
        except Exception: im1 = Image.new("RGB", (CW, CH), (50, 40, 40))
        try: im2 = C.render(nm, ch, ns, w=CW, h=CH, style="v2")
        except Exception: im2 = Image.new("RGB", (CW, CH), (40, 50, 40))
        c, r = i % cols, i // cols
        x = pad + c*(cellW+pad); y = head + pad + r*(cellH+pad)
        sheet.paste(im1, (x, y+lblh)); sheet.paste(im2, (x+CW+gap, y+lblh))
        dr.rectangle([(x, y+lblh), (x+CW-1, y+lblh+CH-1)], outline=(150, 90, 90))
        dr.rectangle([(x+CW+gap, y+lblh), (x+CW+gap+CW-1, y+lblh+CH-1)], outline=(80, 140, 100))
        dr.text((x+2, y+3), ((nm or "(unnamed)")[:28] + "  ·  " + fam), fill=(205, 214, 224), font=font(11))
        dr.text((x+5, y+lblh+3), "v1", fill=(228, 150, 150), font=font(12))
        dr.text((x+CW+gap+5, y+lblh+3), "v2", fill=(150, 214, 176), font=font(12))
    out = os.path.join(HERE, "..", "docs", "cad_v1_vs_v2.png")
    sheet.save(out, "PNG"); print("wrote", os.path.abspath(out), sheet.size)
    return 0

if __name__ == "__main__":
    sys.exit(main())
