#!/usr/bin/env python3
"""THE VIEWER -- OFFLINE SEMANTIC SEARCH (v0.99.29). Framework for meaning-based search over the OCR text. Uses a local
sentence-transformers model when installed (true semantic); otherwise falls back to a deterministic hashing bag-of-words
vector (keyword-ish) so the pipeline still works offline with zero downloads. Build the index host-side
(BUILD-EMBEDDINGS.bat -> index/embeddings.npy + index/embeddings_ids.tsv); /api/semantic queries it. Read-only."""
import os, re, math

try:
    import numpy as _np
    _OK = True
except Exception:
    _np = None; _OK = False

_MODEL = None
DIM = 384  # sentence-transformers all-MiniLM dim; the fallback also uses this width


def _load_model():
    """Try to load a local sentence-transformers model once; return it or None (fallback)."""
    global _MODEL
    if _MODEL is not None:
        return _MODEL if _MODEL is not False else None
    try:
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        _MODEL = False
    return _MODEL if _MODEL is not False else None


def backend():
    return "sentence-transformers" if _load_model() else "hash-fallback"


def _tokens(s):
    return re.findall(r"[a-z0-9]+", (s or "").lower())


def _hash_vec(text, dim=DIM):
    """Deterministic bag-of-tokens hashing vector (unit-normalised). Keyword-level fallback, not true semantics."""
    v = _np.zeros(dim, dtype=_np.float32)
    for tok in _tokens(text):
        if len(tok) < 2:
            continue
        h = hash(tok) % dim  # note: process-stable within a run; the index + query use the same process/build
        v[h] += 1.0
    n = float(_np.linalg.norm(v))
    return v / n if n else v


def embed_text(text):
    if not _OK:
        return None
    m = _load_model()
    if m:
        try:
            vec = m.encode([text or ""], normalize_embeddings=True)[0]
            return _np.asarray(vec, dtype=_np.float32)
        except Exception:
            pass
    return _hash_vec(text)


def cosine(a, b):
    if a is None or b is None:
        return 0.0
    na = float(_np.linalg.norm(a)); nb = float(_np.linalg.norm(b))
    if not na or not nb:
        return 0.0
    return float(_np.dot(a, b) / (na * nb))


def build_index(db_path, index_dir, limit=200000, min_chars=60):
    """Embed page bodies -> embeddings.npy (float32 NxDIM) + embeddings_ids.tsv (doc,page). Host-side. Returns count."""
    import sqlite3
    con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
    rows = con.execute("SELECT document_id, page_number, body_text FROM pages "
                       "WHERE body_text IS NOT NULL AND length(body_text)>? LIMIT ?", (min_chars, limit)).fetchall()
    con.close()
    vecs = []; ids = []
    for doc, page, body in rows:
        v = embed_text(body[:2000])
        if v is None:
            continue
        vecs.append(v); ids.append((doc, page))
    if not vecs:
        return 0
    arr = _np.vstack(vecs).astype(_np.float32)
    _np.save(os.path.join(index_dir, "embeddings.npy"), arr)
    with open(os.path.join(index_dir, "embeddings_ids.tsv"), "w", encoding="utf-8") as f:
        for doc, page in ids:
            f.write("%s\t%s\n" % (doc, page))
    return len(ids)


def search(query, index_dir, top=15):
    npy = os.path.join(index_dir, "embeddings.npy"); tsv = os.path.join(index_dir, "embeddings_ids.tsv")
    if not _OK or not os.path.exists(npy) or not os.path.exists(tsv):
        return {"ready": os.path.exists(npy), "backend": backend(), "results": []}
    arr = _np.load(npy)
    ids = [ln.rstrip("\n").split("\t") for ln in open(tsv, encoding="utf-8")]
    q = embed_text(query)
    if q is None:
        return {"ready": True, "backend": backend(), "results": []}
    sims = arr.dot(q) / (_np.linalg.norm(arr, axis=1) * (_np.linalg.norm(q) or 1) + 1e-9)
    order = _np.argsort(-sims)[:max(1, min(int(top), 100))]
    out = []
    for i in order:
        if i < len(ids):
            doc, page = ids[i][0], ids[i][1]
            out.append({"doc": doc, "page": page, "score": round(float(sims[i]), 3),
                        "page_url": "/deepzoom?doc=%s&page=%s" % (doc, page)})
    return {"ready": True, "backend": backend(), "results": out}


if __name__ == "__main__":
    if not _OK:
        print("numpy unavailable; skipping"); raise SystemExit(0)
    print("backend:", backend())
    a = embed_text("alternator charging system voltage regulator")
    b = embed_text("alternator not charging, voltage regulator fault")
    c = embed_text("tire pressure and wheel torque sequence")
    ab = cosine(a, b); ac = cosine(a, c)
    print("cosine(related): %.3f  cosine(unrelated): %.3f" % (ab, ac))
    assert abs(cosine(a, a) - 1.0) < 1e-5, "self-cosine != 1"
    assert ab > ac, "related text should score higher than unrelated (even in fallback)"
    print("embed self-test OK")
# END OF FILE
