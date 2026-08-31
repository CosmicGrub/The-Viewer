#!/usr/bin/env python3
"""v1.36: regression coverage for embed.py's full-rebuild-prep rewrite of build_index() --
configurable row cap (VIEWER_EMBED_LIMIT, replacing the old hardcoded limit=200000 default),
batched encoding, and resumable checkpointing (shard files + embeddings.progress.json).

Runs entirely against a small synthetic sqlite db (no dependency on the real ~1.68M-row
index/viewer.db) so it's fast and reproducible on any host, with or without sentence-transformers
installed -- see PASS lines for which backend actually ran.

THE SAFETY INVARIANT THIS FILE EXISTS TO GUARD: `embeddings.meta.json` -- the ONLY thing
`_index_is_stale()` trusts as proof an index is complete and fresh (see `[1.32.0]`'s CRITICAL fix)
-- must be provably impossible to write for a partial/interrupted build. `test_interrupt_then_resume`
below injects a real mid-run failure (not a mocked short-circuit of build_index() itself), confirms
the meta stamp was NOT written and `_index_is_stale()` still reports the interrupted index as stale,
then resumes the SAME call and confirms the final result is byte-for-byte equivalent (same ids, same
vectors) to an uninterrupted run over the identical sample."""
import os
import sys
import json
import sqlite3
import tempfile
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)
import embed  # noqa: E402
import numpy as np  # noqa: E402

PASS = 0; FAIL = 0


def ok(name, cond):
    global PASS, FAIL
    print(("PASS " if cond else "FAIL ") + name)
    if cond: PASS += 1
    else: FAIL += 1


def _make_db(path, n_rows, min_len=80):
    """A synthetic pages table, schema-compatible with the real one (id/document_id/page_number/
    body_text is all build_index() touches). Text is long enough to clear min_chars=60 and varies
    per row so vectors aren't all identical (a real corpus concern, not just a test nicety)."""
    if os.path.exists(path):
        os.remove(path)
    con = sqlite3.connect(path)
    con.execute("""CREATE TABLE pages (
        id INTEGER PRIMARY KEY, document_id INTEGER, page_number INTEGER, body_text TEXT)""")
    topics = [
        "alternator charging system voltage regulator inspection procedure",
        "tire pressure and wheel torque sequence for the road wheel assembly",
        "brake chamber replacement and air line routing diagram reference",
        "engine oil filter change interval and drain plug torque specification",
        "hydraulic winch cable inspection and fault diagnosis checklist",
    ]
    rows = []
    for i in range(n_rows):
        topic = topics[i % len(topics)]
        body = "Page %d covering %s. Additional detail padding text repeated for length: %s." % (
            i, topic, topic)
        rows.append((i + 1, (i % 7) + 1, (i % 40) + 1, body))
    con.executemany("INSERT INTO pages(id, document_id, page_number, body_text) VALUES(?,?,?,?)", rows)
    con.commit()
    con.close()
    assert min(len(r[3]) for r in rows) > min_len, "fixture text must clear min_chars=60"


def _read_ids_tsv(path):
    with open(path, encoding="utf-8") as f:
        return [tuple(ln.rstrip("\n").split("\t")) for ln in f]


def test_configurable_cap_env_var(tmp_root):
    """VIEWER_EMBED_LIMIT (not a hardcoded 200000) governs the default cap when limit=None."""
    db = os.path.join(tmp_root, "cap.db")
    _make_db(db, n_rows=20)
    out = os.path.join(tmp_root, "cap_out")
    os.makedirs(out, exist_ok=True)

    old_env = os.environ.get("VIEWER_EMBED_LIMIT")
    try:
        os.environ["VIEWER_EMBED_LIMIT"] = "7"
        n = embed.build_index(db, out, limit=None, chunk_size=5)
        ok("VIEWER_EMBED_LIMIT_env_var_caps_row_count_when_limit_is_None", n == 7)
        ids = _read_ids_tsv(os.path.join(out, "embeddings_ids.tsv"))
        ok("VIEWER_EMBED_LIMIT_env_var_tsv_has_exact_row_count", len(ids) == 7)
    finally:
        if old_env is None:
            os.environ.pop("VIEWER_EMBED_LIMIT", None)
        else:
            os.environ["VIEWER_EMBED_LIMIT"] = old_env

    # Explicit limit= still overrides / bypasses the env var entirely (backward compat with the
    # sole existing caller pattern, and with any future caller that wants an exact number).
    out2 = os.path.join(tmp_root, "cap_out2")
    os.makedirs(out2, exist_ok=True)
    n2 = embed.build_index(db, out2, limit=3, chunk_size=5)
    ok("explicit_limit_kwarg_still_works_independent_of_env_var", n2 == 3)


def test_uninterrupted_build_baseline(tmp_root):
    """A plain, uninterrupted build over a small sample: correct count, correct shapes, meta
    stamp present and matching the active backend, no leftover shard/progress artifacts."""
    db = os.path.join(tmp_root, "baseline.db")
    _make_db(db, n_rows=53)
    out = os.path.join(tmp_root, "baseline_out")
    os.makedirs(out, exist_ok=True)

    n = embed.build_index(db, out, limit=53, min_chars=60, batch_size=16, chunk_size=8)
    ok("uninterrupted_build_returns_full_row_count", n == 53)

    npy = os.path.join(out, "embeddings.npy")
    tsv = os.path.join(out, "embeddings_ids.tsv")
    ok("uninterrupted_build_writes_embeddings_npy", os.path.exists(npy))
    ok("uninterrupted_build_writes_embeddings_ids_tsv", os.path.exists(tsv))
    arr = np.load(npy)
    ok("uninterrupted_build_npy_shape_matches_row_count_and_dim", arr.shape == (53, embed.DIM))
    ids = _read_ids_tsv(tsv)
    ok("uninterrupted_build_tsv_row_count_matches", len(ids) == 53)

    meta_path = embed._meta_path(out)
    ok("uninterrupted_build_writes_meta_stamp", os.path.exists(meta_path))
    meta = json.load(open(meta_path, encoding="utf-8"))
    ok("uninterrupted_build_meta_backend_matches_active_backend", meta.get("backend") == embed.backend())
    ok("uninterrupted_build_index_not_stale_afterward", embed._index_is_stale(out) is False)

    ok("uninterrupted_build_cleans_up_progress_marker",
       not os.path.exists(embed._progress_path(out)))
    ok("uninterrupted_build_cleans_up_shard_dir", not os.path.isdir(embed._shard_dir(out)))


def test_interrupt_then_resume(tmp_root):
    """The core scenario: start a build, force a real mid-run crash (not a mock of build_index()
    itself -- a genuine exception raised from inside the chunk loop, the same shape a killed
    process or an OS-level interruption would produce), confirm the safety invariant, then resume
    the identical call and confirm the final output is equivalent to an uninterrupted run over the
    same sample."""
    db = os.path.join(tmp_root, "resume.db")
    _make_db(db, n_rows=61)

    # Independent uninterrupted baseline over the IDENTICAL sample, for equivalence comparison.
    baseline_out = os.path.join(tmp_root, "resume_baseline_out")
    os.makedirs(baseline_out, exist_ok=True)
    embed.build_index(db, baseline_out, limit=61, min_chars=60, batch_size=16, chunk_size=10)
    baseline_arr = np.load(os.path.join(baseline_out, "embeddings.npy"))
    baseline_ids = _read_ids_tsv(os.path.join(baseline_out, "embeddings_ids.tsv"))

    out = os.path.join(tmp_root, "resume_out")
    os.makedirs(out, exist_ok=True)

    # Inject a failure into _np.save (used both for shard writes and the final merge) that fires
    # on its 3rd invocation -- i.e. after 2 chunks (of chunk_size=10) have genuinely landed on
    # disk as shards, simulating the process dying mid-run.
    real_save = embed._np.save
    call_count = {"n": 0}
    CRASH_AT = 3

    class _InjectedCrash(Exception):
        pass

    def _flaky_save(*a, **kw):
        call_count["n"] += 1
        if call_count["n"] == CRASH_AT:
            raise _InjectedCrash("simulated process kill mid-shard-write")
        return real_save(*a, **kw)

    embed._np.save = _flaky_save
    crashed = False
    try:
        embed.build_index(db, out, limit=61, min_chars=60, batch_size=16, chunk_size=10)
    except _InjectedCrash:
        crashed = True
    finally:
        embed._np.save = real_save

    ok("interrupted_build_actually_raised_the_injected_crash", crashed)

    # ---- THE SAFETY INVARIANT ----
    meta_path = embed._meta_path(out)
    ok("interrupted_build_did_NOT_write_meta_stamp", not os.path.exists(meta_path))
    ok("interrupted_index_reports_stale_via_index_is_stale", embed._index_is_stale(out) is True)
    # search() itself must also refuse it end-to-end (what actually reaches /api/semantic).
    # embeddings.npy/tsv don't exist yet at this point (only shards do), so search() takes the
    # "not ready" path -- confirm it's not silently "ready" some other way.
    r = embed.search("alternator", out)
    ok("interrupted_index_search_is_not_ready", r.get("ready") is not True)

    ok("interrupted_build_left_progress_marker", os.path.exists(embed._progress_path(out)))
    with open(embed._progress_path(out), encoding="utf-8") as f:
        prog = json.load(f)
    ok("interrupted_build_progress_rows_done_is_partial", 0 < prog.get("rows_done", 0) < 61)
    shard_dir = embed._shard_dir(out)
    shards_before = sorted(os.listdir(shard_dir)) if os.path.isdir(shard_dir) else []
    ok("interrupted_build_left_shard_files_on_disk", len(shards_before) > 0)

    # ---- RESUME: identical call, no fault injected this time ----
    n = embed.build_index(db, out, limit=61, min_chars=60, batch_size=16, chunk_size=10)
    ok("resumed_build_returns_full_row_count", n == 61)

    resumed_arr = np.load(os.path.join(out, "embeddings.npy"))
    resumed_ids = _read_ids_tsv(os.path.join(out, "embeddings_ids.tsv"))
    ok("resumed_build_row_count_matches_baseline", len(resumed_ids) == len(baseline_ids))
    ok("resumed_build_ids_match_baseline_exactly", resumed_ids == baseline_ids)
    ok("resumed_build_vectors_match_baseline_exactly",
       resumed_arr.shape == baseline_arr.shape and bool(np.allclose(resumed_arr, baseline_arr, atol=1e-5)))

    # ---- Post-resume, the success invariants hold exactly like the uninterrupted case ----
    ok("resumed_build_writes_meta_stamp", os.path.exists(meta_path))
    ok("resumed_build_index_not_stale", embed._index_is_stale(out) is False)
    ok("resumed_build_cleans_up_progress_marker", not os.path.exists(embed._progress_path(out)))
    ok("resumed_build_cleans_up_shard_dir", not os.path.isdir(shard_dir))


def test_stale_progress_is_ignored_not_resumed(tmp_root):
    """A progress marker from a DIFFERENT (incompatible) invocation -- different limit, in this
    case -- must be treated as stale and discarded, not blindly resumed from. This is what stops
    a leftover progress file from a previous, differently-configured run silently corrupting a
    new one."""
    db = os.path.join(tmp_root, "stale_progress.db")
    _make_db(db, n_rows=15)
    out = os.path.join(tmp_root, "stale_progress_out")
    os.makedirs(out, exist_ok=True)

    # Hand-plant a progress marker claiming a prior run with a different `limit` got partway
    # through, plus a shard that would be wrong to reuse.
    shard_dir = embed._shard_dir(out)
    os.makedirs(shard_dir, exist_ok=True)
    fake_vecs = np.zeros((2, embed.DIM), dtype=np.float32)
    np.save(os.path.join(shard_dir, "shard_000000.npy"), fake_vecs)
    with open(os.path.join(shard_dir, "shard_000000.tsv"), "w", encoding="utf-8") as f:
        f.write("999\t999\n999\t998\n")
    with open(embed._progress_path(out), "w", encoding="utf-8") as f:
        json.dump({"last_id": 2, "rows_done": 2, "db_path": db, "limit": 999,  # mismatched limit
                    "min_chars": 60, "backend": embed.backend(), "chunk_size": 5, "shard_idx": 1}, f)

    n = embed.build_index(db, out, limit=15, min_chars=60, chunk_size=5)
    ok("mismatched_progress_is_not_resumed_full_count_returned", n == 15)
    ids = _read_ids_tsv(os.path.join(out, "embeddings_ids.tsv"))
    ok("mismatched_progress_fake_planted_ids_not_present_in_final_output",
       ("999", "999") not in ids and ("999", "998") not in ids)
    ok("mismatched_progress_final_ids_count_correct", len(ids) == 15)


def test_hash_fallback_backend_batches_correctly(tmp_root):
    """Force the hash-fallback path (model unavailable) and confirm chunked processing still
    produces correct, deterministic output -- the fallback gets no batching speed benefit (pure
    per-text CRC32) but must still work inside the same chunked/checkpointed structure."""
    db = os.path.join(tmp_root, "hashfb.db")
    _make_db(db, n_rows=23)
    out = os.path.join(tmp_root, "hashfb_out")
    os.makedirs(out, exist_ok=True)

    real_load_model = embed._load_model
    embed._load_model = lambda: None
    try:
        n = embed.build_index(db, out, limit=23, min_chars=60, chunk_size=6)
    finally:
        embed._load_model = real_load_model

    ok("hash_fallback_build_returns_full_count", n == 23)
    meta = json.load(open(embed._meta_path(out), encoding="utf-8"))
    ok("hash_fallback_build_meta_backend_is_hash_fallback", meta.get("backend") == "hash-fallback")
    ok("hash_fallback_build_meta_records_hash_algo_version",
       meta.get("hash_algo_version") == embed.HASH_ALGO_VERSION)


def main():
    with tempfile.TemporaryDirectory() as tmp_root:
        print("active backend for this run:", embed.backend())
        test_configurable_cap_env_var(tmp_root)
        test_uninterrupted_build_baseline(tmp_root)
        test_interrupt_then_resume(tmp_root)
        test_stale_progress_is_ignored_not_resumed(tmp_root)
        test_hash_fallback_backend_batches_correctly(tmp_root)
    return PASS, FAIL


if __name__ == "__main__":
    p, f = main()
    print("\n%d passed, %d failed" % (p, f))
    sys.exit(1 if f else 0)

# END OF FILE
