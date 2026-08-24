#!/usr/bin/env python3
"""THE VIEWER -- schematic highlighter: extract a vector page's drawing geometry + text boxes so the UI can
overlay a clickable/highlightable layer (Phase 1). Pure read of the PDF via PyMuPDF on demand -- NO conversion,
never touches the corpus (R1). Returns normalized 0..1 coords so the overlay scales to any rendered size.

  schem_paths(pdf_path, page=1) -> {has_vector, w, h, paths:[...], words:[...]}
    paths items: {"t":"l", x1,y1,x2,y2}        line segment
                 {"t":"r", x,y,w,h}            rectangle
                 {"t":"p", pts:[[x,y],...]}    polyline (curve sampled)  -- all coords normalized 0..1
"""
import os

def _fitz():
    try:
        import pymupdf as fitz; return fitz
    except Exception:
        return None

def _bez(p0, p1, p2, p3, n=6):
    out = []
    for i in range(n + 1):
        t = i / n; u = 1 - t
        x = u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0]
        y = u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1]
        out.append([x, y])
    return out

def schem_paths(pdf_path, page=1, max_paths=6000, max_words=1500):
    fitz = _fitz()
    if not fitz or not pdf_path or not str(pdf_path).lower().endswith(".pdf") or not os.path.exists(pdf_path):
        return {"has_vector": False, "w": 0, "h": 0, "paths": [], "words": []}
    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return {"has_vector": False, "w": 0, "h": 0, "paths": [], "words": []}
    page = max(1, min(int(page), doc.page_count)); pg = doc[page - 1]
    W = pg.rect.width or 1; H = pg.rect.height or 1
    def nx(x): return round(max(0.0, min(1.0, x / W)), 5)
    def ny(y): return round(max(0.0, min(1.0, y / H)), 5)
    paths = []
    try:
        for dr in pg.get_drawings():
            for it in dr.get("items", []):
                op = it[0]
                if op == "l":
                    p1, p2 = it[1], it[2]
                    paths.append({"t": "l", "x1": nx(p1.x), "y1": ny(p1.y), "x2": nx(p2.x), "y2": ny(p2.y)})
                elif op == "re":
                    r = it[1]
                    paths.append({"t": "r", "x": nx(r.x0), "y": ny(r.y0), "w": nx(r.x1) - nx(r.x0), "h": ny(r.y1) - ny(r.y0)})
                elif op == "qu":
                    q = it[1]
                    pts = [[nx(q.ul.x), ny(q.ul.y)], [nx(q.ur.x), ny(q.ur.y)], [nx(q.lr.x), ny(q.lr.y)], [nx(q.ll.x), ny(q.ll.y)], [nx(q.ul.x), ny(q.ul.y)]]
                    paths.append({"t": "p", "pts": pts})
                elif op == "c":
                    pts = [[nx(x), ny(y)] for x, y in _bez(it[1], it[2], it[3], it[4])]
                    paths.append({"t": "p", "pts": pts})
                if len(paths) >= max_paths: break
            if len(paths) >= max_paths: break
    except Exception:
        pass
    words = []
    try:
        for w in pg.get_text("words"):
            if not (w[4] or "").strip(): continue
            words.append({"x0": nx(w[0]), "y0": ny(w[1]), "x1": nx(w[2]), "y1": ny(w[3]), "t": w[4]})
            if len(words) >= max_words: break
    except Exception:
        pass
    doc.close()
    return {"has_vector": len(paths) >= 12, "w": round(W, 1), "h": round(H, 1), "paths": paths, "words": words}
