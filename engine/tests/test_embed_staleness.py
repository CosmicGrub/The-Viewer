#!/usr/bin/env python3
"""v1.32: regression coverage for a real, live production bug caught and reproduced in this exact
session -- embed.py's _index_is_stale() only ever compared the CURRENT active backend against itself
(`backend() == "hash-fallback"`), never against what the index was actually BUILT with.

THE BUG, reproduced live: this repo's real index/embeddings.npy predates version tracking (no
embeddings.meta.json stamp) and was built under the old hash-fallback bucket math, since
sentence-transformers had never been installed in this environment before. The moment
`pip install sentence-transformers` succeeded, embed.backend() started returning
"sentence-transformers" instead of "hash-fallback" -- and _index_is_stale()'s old logic
(`return backend() == "hash-fallback"` for the no-meta-stamp case) silently flipped from True to
False, reclassifying that same old, incompatible-vector-space index as "not stale". It then started
being served through hybrid_search()'s RRF fusion on /api/search_hybrid -- THE PRIMARY SEARCH ENDPOINT
as of [1.31.0] -- blending real hash-bucket vectors against real sentence-transformer query embeddings
into live search results. Confirmed live: cosine scores in the 0.18-0.19 range (near-noise, nowhere
near the 0.7+ a real semantic match produces) getting treated as a legitimate corroborating signal.

THE FIX: an index is now stale unless a meta stamp PROVES it was built by the SAME backend that is
CURRENTLY active -- not just "some backend happened to be active when we last checked".

This test proves the exact failure mode directly: a meta-stamped index recording one backend, checked
while a DIFFERENT backend is active, must be stale -- not just "no meta stamp -> stale", which the
original (pre-bug) test coverage already had and which alone would NOT have caught this bug."""
import os
import sys
import json
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)
import embed                                               # noqa: E402

PASS = 0; FAIL = 0


def ok(name, cond):
    global PASS, FAIL
    print(("PASS " if cond else "FAIL ") + name)
    if cond: PASS += 1
    else: FAIL += 1


def main():
    real_backend = embed.backend

    def build_meta(tmp, backend_name, hash_version=None):
        meta = {"backend": backend_name}
        if hash_version is not None:
            meta["hash_algo_version"] = hash_version
        with open(embed._meta_path(tmp), "w", encoding="utf-8") as f:
            json.dump(meta, f)

    try:
        # ---- The exact live bug: meta says "hash-fallback" (what really built this repo's real,
        # pre-existing index), but the CURRENTLY ACTIVE backend is "sentence-transformers" (what a
        # fresh pip install flips it to, mid-session, with zero index rebuild in between).
        with tempfile.TemporaryDirectory() as tmp:
            build_meta(tmp, "hash-fallback", embed.HASH_ALGO_VERSION)
            embed.backend = lambda: "sentence-transformers"
            stale = embed._index_is_stale(tmp)
            ok("built_as_hash_fallback_but_now_running_sentence_transformers_is_stale_THE_LIVE_BUG",
               stale is True)

        # ---- The mirror case: built with sentence-transformers, but the currently active backend
        # somehow reverted to hash-fallback (e.g. the package got uninstalled) -- also stale.
        with tempfile.TemporaryDirectory() as tmp:
            build_meta(tmp, "sentence-transformers")
            embed.backend = lambda: "hash-fallback"
            stale = embed._index_is_stale(tmp)
            ok("built_as_sentence_transformers_but_now_running_hash_fallback_is_stale", stale is True)

        # ---- No meta stamp at all -- always stale, REGARDLESS of which backend is currently active
        # (the original pre-bug behavior only guaranteed this for the hash-fallback case).
        with tempfile.TemporaryDirectory() as tmp:
            embed.backend = lambda: "sentence-transformers"
            ok("no_meta_stamp_is_stale_when_active_backend_is_sentence_transformers",
               embed._index_is_stale(tmp) is True)
            embed.backend = lambda: "hash-fallback"
            ok("no_meta_stamp_is_stale_when_active_backend_is_hash_fallback",
               embed._index_is_stale(tmp) is True)

        # ---- The genuinely-fine case: meta backend matches the currently active backend exactly --
        # must NOT be stale (for sentence-transformers; hash version irrelevant to that backend).
        with tempfile.TemporaryDirectory() as tmp:
            build_meta(tmp, "sentence-transformers")
            embed.backend = lambda: "sentence-transformers"
            ok("matching_backend_sentence_transformers_is_not_stale", embed._index_is_stale(tmp) is False)

        # ---- hash-fallback matching backend, but an OLD hash_algo_version -- still stale (the
        # original, pre-existing check this fix must not have broken).
        with tempfile.TemporaryDirectory() as tmp:
            build_meta(tmp, "hash-fallback", "some-old-version")
            embed.backend = lambda: "hash-fallback"
            ok("matching_hash_fallback_backend_but_old_hash_version_is_still_stale",
               embed._index_is_stale(tmp) is True)

        # ---- hash-fallback matching backend AND current hash version -- genuinely fine.
        with tempfile.TemporaryDirectory() as tmp:
            build_meta(tmp, "hash-fallback", embed.HASH_ALGO_VERSION)
            embed.backend = lambda: "hash-fallback"
            ok("matching_hash_fallback_backend_and_current_hash_version_is_not_stale",
               embed._index_is_stale(tmp) is False)
    finally:
        embed.backend = real_backend

    # ---- End-to-end: search() itself must refuse a mismatched-backend index (this is what actually
    # reaches /api/search_hybrid's hybrid_search() -> embed.search() call in production), not silently
    # serve results computed against an incompatible vector space.
    import numpy as _np
    with tempfile.TemporaryDirectory() as tmp:
        _np.save(os.path.join(tmp, "embeddings.npy"), _np.zeros((1, embed.DIM), dtype=_np.float32))
        open(os.path.join(tmp, "embeddings_ids.tsv"), "w").write("doc1\t1\n")
        build_meta(tmp, "hash-fallback", embed.HASH_ALGO_VERSION)
        real_backend2 = embed.backend
        try:
            embed.backend = lambda: "sentence-transformers"
            r = embed.search("alternator", tmp, top=5)
            ok("search_end_to_end_refuses_a_mismatched_backend_index_ready_false",
               r.get("ready") is False and r.get("stale") is True)
            ok("search_end_to_end_returns_zero_results_for_a_refused_index", r.get("results") == [])
        finally:
            embed.backend = real_backend2

    return PASS, FAIL


if __name__ == "__main__":
    p, f = main()
    print("\n%d passed, %d failed" % (p, f))
    sys.exit(1 if f else 0)

# END OF FILE
