#!/usr/bin/env python3
"""THE VIEWER -- OFFLINE SEMANTIC SEARCH (v0.99.29). Framework for meaning-based search over the OCR text. Uses a local
sentence-transformers model when installed (true semantic); otherwise falls back to a deterministic hashing bag-of-words
vector (keyword-ish) so the pipeline still works offline with zero downloads. Build the index host-side
(BUILD-EMBEDDINGS.bat -> index/embeddings.npy + index/embeddings_ids.tsv); /api/semantic queries it. Read-only."""
import os, re, math, zlib

try:
    import numpy as _np
    _OK = True
except Exception:
    _np = None; _OK = False

_MODEL = None
DIM = 384  # sentence-transformers all-MiniLM dim; the fallback also uses this width

# Bump this whenever _hash_vec()'s bucket-assignment algorithm changes. Lets search() tell a
# hash-fallback index built under an OLD, incompatible mapping (e.g. the pre-fix, process-random
# hash()) apart from a current one -- see build_index()/_index_is_stale() below. Only meaningful
# for the hash-fallback backend; a sentence-transformers-built index doesn't use this at all.
HASH_ALGO_VERSION = "crc32-v1"


def _meta_path(index_dir):
    return os.path.join(index_dir, "embeddings.meta.json")


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
    """Deterministic bag-of-tokens hashing vector (unit-normalised). Keyword-level fallback, not true semantics.

    Uses zlib.crc32, NOT Python's built-in hash(): str hashing is randomized per process by default
    (PYTHONHASHSEED) specifically to resist hash-flooding DoS attacks, which means hash(tok) % dim
    produces a DIFFERENT token->bucket mapping every time a fresh Python process starts. That's fatal
    here because build_index() runs once, standalone, from BUILD-EMBEDDINGS.bat, while search() runs
    later inside the long-running server process -- a different process, almost always with a
    different hash seed. The index-build buckets and query-time buckets never actually agreed, so
    /api/semantic silently returned near-random cosine similarity with no error, on every install
    that doesn't have sentence-transformers (the documented default, zero-download offline path).
    crc32 is a well-defined, non-randomized algorithm -- identical across processes, platforms, and
    Python versions, so index-build and query time finally hash the same token to the same bucket.

    NOTE: this changes the token->bucket mapping from whatever a given process's hash() happened to
    produce, to a fixed one. Any embeddings.npy built before this fix was hashed against a mapping
    that (per the bug above) was already useless across process boundaries -- re-run
    BUILD-EMBEDDINGS.bat after upgrading to rebuild it against the now-stable mapping.
    """
    v = _np.zeros(dim, dtype=_np.float32)
    for tok in _tokens(text):
        if len(tok) < 2:
            continue
        h = zlib.crc32(tok.encode("utf-8")) % dim
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
    # Stamp which backend (and, for hash-fallback, which bucket-mapping version) built this index.
    # Without this, an operator who upgrades but forgets to re-run BUILD-EMBEDDINGS.bat gets no
    # signal at all -- search() previously only checked file existence, so a pre-crc32-fix index
    # (built under the old, process-random hash() mapping) kept being served forever with no error,
    # silently returning the exact near-random similarity results the fix was meant to eliminate.
    import json
    used_backend = backend()
    with open(_meta_path(index_dir), "w", encoding="utf-8") as f:
        json.dump({
            "backend": used_backend,
            "hash_algo_version": HASH_ALGO_VERSION if used_backend == "hash-fallback" else None,
        }, f)
    return len(ids)


def _index_is_stale(index_dir):
    """True if embeddings.npy needs a rebuild before it can be trusted: it was built by the
    hash-fallback backend under a different (or unrecorded/unknown) bucket-mapping version than
    HASH_ALGO_VERSION. A sentence-transformers-built index is never considered stale by this check
    -- the hash-bucket versioning doesn't apply to it."""
    meta_path = _meta_path(index_dir)
    if not os.path.exists(meta_path):
        # No stamp at all: either predates this version-tracking entirely, or a build that never
        # finished. Can't assume it's fine -- only the hash-fallback backend is actually at risk,
        # so that's the only case treated as stale-by-default (conservative: forces a rebuild
        # rather than silently trusting unverifiable old data).
        return backend() == "hash-fallback"
    try:
        import json
        meta = json.load(open(meta_path, encoding="utf-8"))
    except Exception:
        return backend() == "hash-fallback"
    if meta.get("backend") != "hash-fallback":
        return False   # built with sentence-transformers -- the hash-bucket change doesn't apply
    return meta.get("hash_algo_version") != HASH_ALGO_VERSION


def search(query, index_dir, top=15):
    npy = os.path.join(index_dir, "embeddings.npy"); tsv = os.path.join(index_dir, "embeddings_ids.tsv")
    if not _OK or not os.path.exists(npy) or not os.path.exists(tsv):
        return {"ready": os.path.exists(npy), "backend": backend(), "results": []}
    if _index_is_stale(index_dir):
        return {"ready": False, "backend": backend(), "results": [], "stale": True,
                "error": "embeddings index was built under an old/incompatible hash algorithm -- "
                         "rebuild it via BUILD-EMBEDDINGS.bat"}
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
    # Regression guard for the process-instability bug: a canary token must always land in the
    # same bucket, regardless of which process/run computes it. Before the crc32 fix, this would
    # have been a different number on essentially every fresh `python embed.py` invocation
    # (verified manually: three separate processes previously produced three different buckets for
    # the same token, via Python's per-process-randomized built-in hash()).
    assert zlib.crc32(b"alternator") % DIM == 212, "hash bucket for a fixed token must be process-stable"
    print("hash-bucket stability check OK (bucket=212, process-independent)")
    print("backend:", backend())
    a = embed_text("alternator charging system voltage regulator")
    b = embed_text("alternator not charging, voltage regulator fault")
    c = embed_text("tire pressure and wheel torque sequence")
    ab = cosine(a, b); ac = cosine(a, c)
    print("cosine(related): %.3f  cosine(unrelated): %.3f" % (ab, ac))
    assert abs(cosine(a, a) - 1.0) < 1e-5, "self-cosine != 1"
    assert ab > ac, "related text should score higher than unrelated (even in fallback)"

    # Staleness detection: a hash-fallback index with no meta stamp at all (predates version
    # tracking, or the exact shape a pre-crc32-fix index would have) must be treated as stale;
    # once build_index() stamps it, search() must accept it.
    import tempfile, json as _json
    with tempfile.TemporaryDirectory() as td:
        _np.save(os.path.join(td, "embeddings.npy"), _np.zeros((1, DIM), dtype=_np.float32))
        open(os.path.join(td, "embeddings_ids.tsv"), "w").write("doc1\t1\n")
        if backend() == "hash-fallback":
            r_missing_meta = search("alternator", td)
            assert r_missing_meta.get("stale") is True and r_missing_meta["ready"] is False, r_missing_meta
            print("staleness check (no meta stamp) OK -> ready=False")

            with open(_meta_path(td), "w") as f:
                _json.dump({"backend": "hash-fallback", "hash_algo_version": "some-old-version"}, f)
            r_old_version = search("alternator", td)
            assert r_old_version.get("stale") is True, r_old_version
            print("staleness check (mismatched version) OK -> ready=False")

            with open(_meta_path(td), "w") as f:
                _json.dump({"backend": "hash-fallback", "hash_algo_version": HASH_ALGO_VERSION}, f)
            r_current = search("alternator", td)
            assert r_current.get("stale") is not True and r_current["ready"] is True, r_current
            print("staleness check (current version) OK -> ready=True")
    print("embed self-test OK")
# END OF FILE
