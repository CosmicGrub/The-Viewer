#!/usr/bin/env python3
"""THE VIEWER -- VISUAL PART SEARCH via perceptual hash (v0.99.28). Snap/point a photo at a part and find the closest
figure crops (index/figcache) by 64-bit DCT perceptual hash + Hamming distance. Pure numpy + Pillow (no model, offline).
Build the index host-side (BUILD-VISUAL-INDEX.bat -> index/phash.tsv), then /api/visualmatch queries it. Read-only."""
import os, re

try:
    import numpy as _np
    from PIL import Image as _Image
    _OK = True
except Exception:
    _np = None; _Image = None; _OK = False

HASH_TSV = "phash.tsv"


def available():
    return _OK


def phash(pil_img, hash_size=8, highfreq=4):
    """64-bit DCT perceptual hash as a 16-char hex string, or None."""
    if not _OK or pil_img is None:
        return None
    img = pil_img.convert("L").resize((hash_size * highfreq, hash_size * highfreq), _Image.LANCZOS)
    a = _np.asarray(img, dtype=_np.float64)
    d = _dct2(a)  # 2-D DCT-II via numpy (no scipy)
    block = d[:hash_size, :hash_size]
    med = _np.median(block[1:, 1:])  # skip the DC term
    bits = (block > med).flatten()
    v = 0
    for b in bits:
        v = (v << 1) | int(bool(b))
    return "%016x" % v


def _dct(vec):
    N = len(vec); n = _np.arange(N)
    M = _np.cos(_np.pi * (2 * n[:, None] + 1) * n[None, :] / (2 * N))
    return M.dot(vec)


def _dct2(mat):
    return _dct(_dct(mat.T).T)


def hamming(h1, h2):
    if not h1 or not h2:
        return 64
    try:
        return bin(int(h1, 16) ^ int(h2, 16)).count("1")
    except Exception:
        return 64


def phash_file(path):
    try:
        return phash(_Image.open(path))
    except Exception:
        return None


def build_index(figcache_dir, out_path):
    """Hash every crop in figcache -> TSV (name<TAB>hash). Host-side; returns count."""
    n = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for fn in sorted(os.listdir(figcache_dir)):
            if not re.search(r"\.(png|jpg|jpeg)$", fn, re.I):
                continue
            h = phash_file(os.path.join(figcache_dir, fn))
            if h:
                f.write("%s\t%s\n" % (fn, h)); n += 1
    return n


def match(query_img, index_dir, top=12, max_dist=22):
    """Return [{name, distance, crop_url}] nearest to the query image, from the prebuilt phash.tsv."""
    p = os.path.join(index_dir, HASH_TSV)
    qh = phash(query_img)
    if not qh or not os.path.exists(p):
        return {"ready": os.path.exists(p), "results": []}
    scored = []
    with open(p, encoding="utf-8", errors="replace") as f:
        for ln in f:
            parts = ln.rstrip("\n").split("\t")
            if len(parts) != 2:
                continue
            d = hamming(qh, parts[1])
            if d <= max_dist:
                scored.append((d, parts[0]))
    scored.sort()
    return {"ready": True, "query_hash": qh,
            "results": [{"name": nm, "distance": d, "crop_url": "/figcrop?name=" + nm} for d, nm in scored[:top]]}


if __name__ == "__main__":
    if not _OK:
        print("numpy/PIL unavailable; skipping"); raise SystemExit(0)
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (200, 200), "white"); d = ImageDraw.Draw(im)
    d.rectangle([40, 40, 160, 120], outline="black", width=4); d.ellipse([70, 130, 130, 180], fill="black")
    h1 = phash(im)
    im2 = im.copy().resize((150, 150)).rotate(0)  # same image, resized -> near-identical hash
    h2 = phash(im2)
    im3 = Image.new("RGB", (200, 200), "black"); h3 = phash(im3)  # totally different
    print("hash1:", h1, "| resized dist:", hamming(h1, h2), "| different dist:", hamming(h1, h3))
    assert hamming(h1, h1) == 0, "self distance not 0"
    assert hamming(h1, h2) <= 6, "resized copy should be close"
    assert hamming(h1, h3) >= 12, "different image should be far"
    print("phash self-test OK")
# END OF FILE
