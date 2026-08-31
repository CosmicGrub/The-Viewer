#!/usr/bin/env python3
"""THE VIEWER -- OFFLINE SEMANTIC SEARCH (v0.99.29). Framework for meaning-based search over the OCR text. Uses a local
sentence-transformers model when installed (true semantic); otherwise falls back to a deterministic hashing bag-of-words
vector (keyword-ish) so the pipeline still works offline with zero downloads. Build the index host-side
(BUILD-EMBEDDINGS.bat -> index/embeddings.npy + index/embeddings_ids.tsv); /api/semantic queries it. Read-only."""
import os, re, math, zlib, threading as _threading

try:
    import numpy as _np
    _OK = True
except Exception:
    _np = None; _OK = False

_MODEL = None
DIM = 384  # sentence-transformers all-MiniLM dim; the fallback also uses this width

core = None  # injected by viewer_app at startup, same DI pattern as features/render_feature.py etc.
             # (viewer_app.py: `import embed as _embed; _embed.core = sys.modules[__name__]`).
             # Stays None when embed.py is used standalone -- BUILD-EMBEDDINGS.bat, this file's own
             # `__main__` self-test, or a bare `import embed` in a script/test -- in which case
             # _load_arrays() below treats it exactly like "modern" tier (full in-memory load,
             # today's behavior, zero change).

# search() used to _np.load(npy) fresh from disk on EVERY call -- unlike the keyword-search path's
# TTL'd LRU (features/routes.py's _SEARCH_LRU, ~line 134), the embeddings array (which can be tens of
# MB) was re-read off disk on every single /api/semantic request. Cached here instead, keyed by
# index_dir + both files' mtimes so a rebuild (BUILD-EMBEDDINGS.bat reran) is picked up immediately
# rather than silently serving a stale in-memory array forever. viewer_app.py runs a
# ThreadingHTTPServer, so the load-if-missing-or-stale path is guarded by a lock -- this app's real
# concurrency is low, so a single plain lock (mirroring _SEARCH_LRU_LOCK) is enough; no per-key
# locking or double-checked-locking complexity needed.
_ARR_CACHE = {}   # index_dir -> (npy_mtime, tsv_mtime, arr, ids)
_ARR_CACHE_LOCK = _threading.Lock()

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
    """True if embeddings.npy needs a rebuild before it can be trusted.

    v1.32 fix -- a real, live bug caught and reproduced in this exact session: the previous version
    of this function only ever checked `backend() == "hash-fallback"` (current-backend-only, both for
    the no-meta-stamp case and, via the hash_algo_version branch, implicitly for the meta-stamped
    case too) -- it never compared the CURRENT active backend against what the index was actually
    BUILT with. The moment `pip install sentence-transformers` succeeded mid-session, `backend()`
    started returning "sentence-transformers", which silently reclassified a pre-existing, meta-less
    200,000-row index -- built under the OLD hash-fallback bucket math, since sentence-transformers
    had never been installed before -- as "not stale". That index then started being served through
    hybrid_search()'s RRF fusion on the live PRIMARY search endpoint: real hash-bucket vectors
    compared against real sentence-transformer query embeddings, producing near-noise cosine scores
    (~0.18-0.19, confirmed live) that got blended into real search results as if they were a
    legitimate corroborating semantic signal. The correct invariant is: an index is trustworthy ONLY
    if we have a stamp proving it was built by the SAME backend that is currently active -- not just
    "some backend was active when we happened to check just now"."""
    meta_path = _meta_path(index_dir)
    cur = backend()
    if not os.path.exists(meta_path):
        # No stamp at all: either predates this version-tracking entirely, or a build that never
        # finished. Unverifiable provenance -- always stale, regardless of which backend is active
        # right now (the bug above was specifically this branch returning False once the active
        # backend happened to no longer be "hash-fallback").
        return True
    try:
        import json
        meta = json.load(open(meta_path, encoding="utf-8"))
    except Exception:
        return True
    built = meta.get("backend")
    if built != cur:
        # Built under a DIFFERENT backend than is active now -- its vectors live in a different,
        # incompatible embedding space from whatever embed_text() would compute for a fresh query
        # today. Always stale, regardless of which direction the mismatch runs.
        return True
    if built == "hash-fallback":
        return meta.get("hash_algo_version") != HASH_ALGO_VERSION
    return False   # built with, and currently running, the same real model backend -- trust it


def _load_arrays(index_dir, npy, tsv):
    """Return (arr, ids) for this index_dir, loading from disk only when there's no cached copy yet
    or either file's mtime has moved on (i.e. a rebuild happened). See _ARR_CACHE above.

    RPS-aware load: on lite/legacy tier (low-RAM / legacy hardware -- see rps.py), the embeddings
    array is memory-mapped from disk (_np.load(..., mmap_mode='r')) instead of fully copied into
    RAM. At THE VIEWER's documented default index cap (200,000 rows x 384 dims x float32) a full
    load pins ~293MB of resident RAM for the server's entire process lifetime, from just one
    /api/semantic or /api/search_hybrid hit -- on the <4GB machines sysprobe.py's own tier profile
    already flags as "Legacy / low-power", that is 10-15%+ of total system RAM, and two orders of
    magnitude past what feature_flags() already bothers tuning for this same tier elsewhere
    (SQLite cache_kb 8MB->1MB, doc_cache 8->2 open PDFs). numpy's dot()/linalg.norm() (search()'s
    cosine ranking) work unchanged against a memmap'd array -- the OS pages it in from disk on
    demand, correct but slower on first touch, an acceptable trade on hardware RPS already treats
    as slow. Modern tier (and the no-`core`-injected standalone case) is completely unchanged: a
    full in-memory _np.load(npy), same as before this cache existed."""
    npy_mtime = os.path.getmtime(npy)
    tsv_mtime = os.path.getmtime(tsv)
    with _ARR_CACHE_LOCK:
        ent = _ARR_CACHE.get(index_dir)
        if ent is not None and ent[0] == npy_mtime and ent[1] == tsv_mtime:
            return ent[2], ent[3]
        rps_mode = getattr(core, "RPS_MODE", "modern")     # None-safe: getattr(None, ..., default) is fine
        if rps_mode in ("lite", "legacy"):
            arr = _np.load(npy, mmap_mode="r")
        else:
            arr = _np.load(npy)
        ids = [ln.rstrip("\n").split("\t") for ln in open(tsv, encoding="utf-8")]
        _ARR_CACHE[index_dir] = (npy_mtime, tsv_mtime, arr, ids)
        return arr, ids


def search(query, index_dir, top=15):
    npy = os.path.join(index_dir, "embeddings.npy"); tsv = os.path.join(index_dir, "embeddings_ids.tsv")
    if not _OK or not os.path.exists(npy) or not os.path.exists(tsv):
        return {"ready": os.path.exists(npy), "backend": backend(), "results": []}
    if _index_is_stale(index_dir):
        return {"ready": False, "backend": backend(), "results": [], "stale": True,
                "error": "embeddings index was built under an old/incompatible hash algorithm -- "
                         "rebuild it via BUILD-EMBEDDINGS.bat"}
    arr, ids = _load_arrays(index_dir, npy, tsv)
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

    # Staleness detection -- runs UNCONDITIONALLY now (previously gated on `backend()=="hash-fallback"`,
    # which meant this whole block silently stopped running the moment sentence-transformers became
    # available -- exactly the environment change that let the real bug below ship undetected by this
    # same self-test earlier in this session). A meta-less index (predates version tracking, or a build
    # that never finished) must be treated as stale; a meta-stamped index whose recorded build-backend
    # no longer matches the CURRENTLY active backend must also be stale (the actual live bug: installing
    # sentence-transformers mid-session silently reclassified an old hash-fallback index as fresh); once
    # build_index() stamps an index with the backend that's actually running, search() must accept it.
    import tempfile, json as _json
    with tempfile.TemporaryDirectory() as td:
        _np.save(os.path.join(td, "embeddings.npy"), _np.zeros((1, DIM), dtype=_np.float32))
        open(os.path.join(td, "embeddings_ids.tsv"), "w").write("doc1\t1\n")

        r_missing_meta = search("alternator", td)
        assert r_missing_meta.get("stale") is True and r_missing_meta["ready"] is False, r_missing_meta
        print("staleness check (no meta stamp) OK -> ready=False, regardless of active backend")

        other_backend = "sentence-transformers" if backend() == "hash-fallback" else "hash-fallback"
        with open(_meta_path(td), "w") as f:
            _json.dump({"backend": other_backend, "hash_algo_version": HASH_ALGO_VERSION}, f)
        r_wrong_backend = search("alternator", td)
        assert r_wrong_backend.get("stale") is True, r_wrong_backend
        print("staleness check (meta backend != active backend) OK -> ready=False "
              "(this is the exact live bug this fix closes)")

        if backend() == "hash-fallback":
            with open(_meta_path(td), "w") as f:
                _json.dump({"backend": "hash-fallback", "hash_algo_version": "some-old-version"}, f)
            r_old_version = search("alternator", td)
            assert r_old_version.get("stale") is True, r_old_version
            print("staleness check (mismatched hash version) OK -> ready=False")

        with open(_meta_path(td), "w") as f:
            _json.dump({"backend": backend(), "hash_algo_version": HASH_ALGO_VERSION}, f)
        r_current = search("alternator", td)
        assert r_current.get("stale") is not True and r_current["ready"] is True, r_current
        print("staleness check (meta backend == active backend, current version) OK -> ready=True")
    print("embed self-test OK")
# END OF FILE
