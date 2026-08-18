#!/usr/bin/env python3
"""THE VIEWER -- the page-render pipeline (extracted verbatim from viewer_app, v0.96.0).

PDF page -> PNG via PyMuPDF (modern) or Poppler (legacy), legibility cleanup, the open-document
LRU, the RPS disk page-cache + warm-on-view prefetch, word boxes, and OCR-driven page callouts.
Documents are addressed ONLY by their id in the documents table -- the path comes from the index,
never from the client, so /page cannot be steered to an arbitrary file (B12). DI via `core`."""
import os
import re
import threading as _threading

from patterns import NSN_RE, FIG_RE as _FIG_RE, PN_RE as _PN_RE, norm_nsn, digits as _digits

try:
    import pymupdf as fitz
except Exception:
    fitz = None

core = None          # injected by viewer_app at startup


def _clean_png(data, contrast=0, binarize=False):
    """Legibility enhancement of a rendered page (grounded: same drawing, more readable).
    Grayscale + auto-contrast + unsharp + de-speckle (+ optional contrast boost / binarize).
    No content invented. Returns the original bytes unchanged if Pillow isn't available."""
    try:
        import io
        from PIL import Image, ImageOps, ImageFilter, ImageEnhance
    except Exception:
        return data
    try:
        im = Image.open(io.BytesIO(data)).convert("L")
        im = ImageOps.autocontrast(im, cutoff=2)
        im = im.filter(ImageFilter.MedianFilter(size=3))          # de-speckle
        im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=2))
        if contrast:
            im = ImageEnhance.Contrast(im).enhance(1.0 + min(max(int(contrast), 0), 100) / 100.0)
        if binarize:
            im = im.point(lambda p: 255 if p > 160 else 0)
        else:
            im = im.point(lambda p: 255 if p > 212 else p)        # gentle background whitening
        buf = io.BytesIO(); im.convert("RGB").save(buf, "PNG"); return buf.getvalue()
    except Exception:
        return data


def _which(name):
    import shutil as _sh; return _sh.which(name)


def _poppler_png(path, page, dpi):
    """Render one PDF page to PNG via Poppler's pdftoppm — the legacy/compat path (Win7/Vista) that
    needs no PyMuPDF. Returns full-page bytes; clip/highlight degrade gracefully on this path."""
    import subprocess, glob, tempfile, shutil as _sh
    page = max(1, int(page)); d = tempfile.mkdtemp(); base = os.path.join(d, "pg")
    try:
        exe = "pdftocairo" if (not _which("pdftoppm") and _which("pdftocairo")) else "pdftoppm"
        subprocess.run([exe, "-png", "-r", str(int(dpi)), "-f", str(page), "-l", str(page), path, base],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        files = sorted(glob.glob(base + "*"))
        if not files:
            raise FileNotFoundError("page render needs PyMuPDF or Poppler (install Poppler for Windows and add bin\\ to PATH)")
        return open(files[0], "rb").read()
    finally:
        _sh.rmtree(d, ignore_errors=True)


_DOC_CACHE = {}                 # path -> (fitz.Document, per-doc lock)
_DOC_ORDER = []                 # LRU order of paths
_DOC_LRU_LOCK = _threading.Lock()
_DOC_MAX = 8


def _get_doc(path):
    """Return a cached open fitz.Document (+ its render lock), opening + LRU-evicting as needed. Reusing
    open documents makes paging/loupe fast (no re-parse per page). PyMuPDF isn't thread-safe, so each doc
    carries a lock the caller holds during get_pixmap; the highlight path never uses this (it mutates)."""
    with _DOC_LRU_LOCK:
        ent = _DOC_CACHE.get(path)
        if ent is not None:
            try: _DOC_ORDER.remove(path)
            except ValueError: pass
            _DOC_ORDER.append(path); return ent
    d = fitz.open(path); lk = _threading.Lock()
    with _DOC_LRU_LOCK:
        if path in _DOC_CACHE:                  # another thread won the race
            try: d.close()
            except Exception: pass
            return _DOC_CACHE[path]
        _DOC_CACHE[path] = (d, lk); _DOC_ORDER.append(path)
        cap = (core.RPS_FLAGS or {}).get("doc_cache") or _DOC_MAX     # scale open-PDF cache with the RPS mode (memory)
        while len(_DOC_ORDER) > cap:
            old = _DOC_ORDER.pop(0); od = _DOC_CACHE.pop(old, None)
            if od is not None:
                try: od[0].close()
                except Exception: pass
        return (d, lk)


def _clip_rect_for(pg, clip):
    if not clip: return None
    try:
        xs = [max(0.0, min(1.0, float(v))) for v in clip]
        if len(xs) == 4:
            pr = pg.rect; x0 = pr.x0 + xs[0]*pr.width; y0 = pr.y0 + xs[1]*pr.height
            x1 = pr.x0 + xs[2]*pr.width; y1 = pr.y0 + xs[3]*pr.height
            if x1 - x0 > 0.5 and y1 - y0 > 0.5: return fitz.Rect(x0, y0, x1, y1)
    except Exception: pass
    return None


def render_page_png(doc_id, page, dpi=130, hl=None, clean=False, contrast=0, binarize=False, clip=None):
    """Render a PDF page (or a sub-rectangle of it) to PNG.

    clip = (x0,y0,x1,y1) as fractions [0..1] of the page. When set, only that region is
    rasterised — at the requested (high) dpi — so the loupe/magnifier gets a genuinely
    high-fidelity crop (the real vector page re-rasterised at higher resolution; for scanned
    pages it is the best honest interpolation of the embedded image, nothing invented)."""
    con = core.db(); r = con.execute("SELECT path FROM documents WHERE id=?", (doc_id,)).fetchone(); con.close()
    if not r: raise FileNotFoundError("document not found")
    path = r["path"]
    if not (path or "").lower().endswith(".pdf") or not os.path.exists(path): raise FileNotFoundError("page image not available")
    if fitz is None:
        # Legacy/compat path (e.g. Win7/Vista without PyMuPDF): render via Poppler. clip/highlight are
        # not available here, but the page renders so the viewer works; cleanup applies if Pillow exists.
        data = _poppler_png(path, page, min(int(dpi), 300))
        if clean or binarize or contrast: data = _clean_png(data, contrast=contrast, binarize=binarize)
        return data
    if hl:
        # Highlight-the-hit mutates the page (adds annotations) -> always a FRESH doc, never the shared cache.
        doc = fitz.open(path); page = max(1, min(int(page), doc.page_count)); pg = doc[page-1]
        try:
            terms = [t for t in re.split(r"\s+", str(hl).strip()) if len(t) >= 3][:6]
            for term in ([str(hl).strip()] + terms):
                for rect in (pg.search_for(term) or [])[:60]:
                    a = pg.add_highlight_annot(rect); a.set_colors(stroke=(1, 0.85, 0.2)); a.update()
        except Exception: pass
        clip_rect = _clip_rect_for(pg, clip)
        pm = pg.get_pixmap(dpi=int(dpi), clip=clip_rect) if clip_rect is not None else pg.get_pixmap(dpi=int(dpi))
        data = pm.tobytes("png"); doc.close()
    else:
        # Plain / loupe (clip) render -> reuse a cached open document (Tier-1 perf), under its render lock.
        d, lk = _get_doc(path)
        with lk:
            page = max(1, min(int(page), d.page_count)); pg = d[page-1]
            clip_rect = _clip_rect_for(pg, clip)
            pm = pg.get_pixmap(dpi=int(dpi), clip=clip_rect) if clip_rect is not None else pg.get_pixmap(dpi=int(dpi))
            data = pm.tobytes("png")
    if clean or binarize or contrast:
        data = _clean_png(data, contrast=contrast, binarize=binarize)
    return data


def cached_page_render(doc_id, page, dpi, clean=False, contrast=0, binarize=False):
    """RPS page cache: full-page renders are served from disk (index/pagecache) when present, else
    rendered once and stored. Big win on slow PCs / HDDs. Loupe (clip) & highlight renders bypass this."""
    if not (core._rps and (core.RPS_FLAGS or {}).get("page_cache")):
        return render_page_png(doc_id, page, dpi, None, clean=clean, contrast=contrast, binarize=binarize)
    hit = core._rps.cache_read(core.INDEX_DIR, doc_id, page, dpi, clean=clean, contrast=contrast, binarize=binarize)
    if hit is not None: return hit
    data = render_page_png(doc_id, page, dpi, None, clean=clean, contrast=contrast, binarize=binarize)
    core._rps.cache_write(core.INDEX_DIR, doc_id, page, dpi, data, clean=clean, contrast=contrast, binarize=binarize)
    return data


def _warm_adjacent(doc_id, page, dpi, clean=False, contrast=0, binarize=False):
    """Warm-on-view: render the next/prev page(s) into the cache in the background so paging feels instant."""
    if not (core._rps and (core.RPS_FLAGS or {}).get("page_cache")): return
    span = int((core.RPS_FLAGS or {}).get("prefetch") or 0)
    if span <= 0: return
    def work():
        for d in list(range(1, span+1)) + list(range(-1, -span-1, -1)):
            p = page + d
            if p < 1: continue
            try:
                if core._rps.cache_read(core.INDEX_DIR, doc_id, p, dpi, clean=clean, contrast=contrast, binarize=binarize) is None:
                    data = render_page_png(doc_id, p, dpi, None, clean=clean, contrast=contrast, binarize=binarize)
                    core._rps.cache_write(core.INDEX_DIR, doc_id, p, dpi, data, clean=clean, contrast=contrast, binarize=binarize)
            except Exception: pass
    try:
        import threading; threading.Thread(target=work, daemon=True).start()
    except Exception: pass


def page_words(doc_id, page):
    """Word boxes for a page (normalized 0..1), from the PDF text layer (PyMuPDF get_text('words')).
    Powers readable label re-orientation in Mirror mode. Returns [] when the page has no text layer
    (e.g. a scanned image not yet OCR'd into the PDF) — honest: we only reorient labels we can locate."""
    if fitz is None: return {"words": [], "has_text": False}
    con = core.db(); r = con.execute("SELECT path FROM documents WHERE id=?", (doc_id,)).fetchone(); con.close()
    if not r: return {"words": [], "has_text": False}
    path = r["path"]
    if not (path or "").lower().endswith(".pdf") or not os.path.exists(path): return {"words": [], "has_text": False}
    doc = fitz.open(path); page = max(1, min(int(page), doc.page_count)); pg = doc[page-1]
    W = pg.rect.width or 1; H = pg.rect.height or 1
    out = []
    try:
        for w in pg.get_text("words"):   # (x0,y0,x1,y1, word, block, line, word_no)
            x0, y0, x1, y1, txt = w[0], w[1], w[2], w[3], w[4]
            if not (txt or "").strip(): continue
            out.append({"x0": round(x0/W, 5), "y0": round(y0/H, 5), "x1": round(x1/W, 5),
                        "y1": round(y1/H, 5), "t": txt})
            if len(out) >= 1200: break
    except Exception:
        out = []
    doc.close()
    return {"words": out, "has_text": bool(out)}


# ---- OCR-driven page callouts (read-only): part#/NSN/figure tokens on ONE page -> clickable jumps -----
# Extracts high-precision callouts from a single page's body_text (works for native-text AND OCR'd pages,
# since OCR fills body_text). When the page has a PDF text layer we also attach normalized word-box coords
# so the UI can place positioned hotspots; OCR-only pages (no word boxes) fall back to a chip list. This is
# the shared extractor Batch 3 (3D) reuses. Pure read on the index (one indexed row) — never writes (R1).
# The FIG/PN regexes now come from patterns.py (A6: one source of truth).


def _locate_box(words, token):
    """Find the word box whose text matches a callout token (by NSN digits or substring). Returns
    [x0,y0,x1,y1] or None. words = list of {x0,y0,x1,y1,t} (normalized 0..1)."""
    if not words: return None
    tok = (token or "").upper(); tokd = _digits(token)
    for w in words:
        wt = (w.get("t") or "").upper()
        if not wt: continue
        if tokd and len(tokd) >= 6 and tokd in _digits(wt):
            return [w["x0"], w["y0"], w["x1"], w["y1"]]
        if len(tok) >= 4 and (tok in wt or wt in tok):
            return [w["x0"], w["y0"], w["x1"], w["y1"]]
    return None


def page_callouts(doc_id, page):
    """Callouts for one page: NSNs -> part dossier, labeled part numbers -> Look-Alike Parts, FIG refs ->
    find-in-manual. Read-only; coords attached where a text layer exists."""
    con = core.db()
    r = con.execute("SELECT p.body_text, p.source FROM pages p WHERE p.document_id=? AND p.page_number=?",
                    (doc_id, int(page))).fetchone()
    con.close()
    body = (r["body_text"] if r else "") or ""
    if not body.strip():
        return {"doc": doc_id, "page": int(page), "has_text": False, "anchored": False, "callouts": []}
    wb = page_words(doc_id, page)                  # boxes only on native-text pages
    words = wb.get("words") or []
    seen = set(); calls = []
    for m in NSN_RE.finditer(body):                # NSNs (most precise)
        nsn = norm_nsn(m.group(0))
        if not nsn or ("nsn:" + nsn) in seen: continue
        seen.add("nsn:" + nsn)
        calls.append({"kind": "nsn", "text": nsn, "label": "NSN " + nsn,
                      "url": "/dossier?q=" + nsn, "box": _locate_box(words, nsn)})
    for m in _PN_RE.finditer(body):                # labeled part numbers (P/N: …)
        pn = (m.group(1) or "").strip().upper().strip("-")
        if len(pn) < 4 or _digits(pn) == "" or ("pn:" + pn) in seen: continue
        seen.add("pn:" + pn)
        calls.append({"kind": "part", "text": pn, "label": "P/N " + pn,
                      "url": "/partdiff?q=" + pn, "box": _locate_box(words, pn)})
    for m in _FIG_RE.finditer(body):               # figure references -> find within this doc
        fig = (m.group(1) or "").strip()
        if not fig or ("fig:" + fig) in seen: continue
        seen.add("fig:" + fig)
        calls.append({"kind": "fig", "text": fig, "label": "FIG " + fig,
                      "find": "FIG " + fig, "box": _locate_box(words, "FIG")})
    calls = calls[:60]
    anchored = any(c.get("box") for c in calls)
    return {"doc": doc_id, "page": int(page), "source": (r["source"] if r else None),
            "has_text": bool(words), "anchored": anchored, "count": len(calls), "callouts": calls}
