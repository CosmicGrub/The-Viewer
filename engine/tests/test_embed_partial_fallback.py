#!/usr/bin/env python3
"""v1.37: regression coverage for build_index()'s SAFETY INVARIANT #2 -- a real, confirmed defect
found during adversarial verification of `[1.36.0]`'s full-rebuild-prep rewrite (pre-existing, not
introduced by that PR: the original unbatched embed_text() had the identical bare per-row fallback,
and the old build_index() also stamped the backend after the fact with no per-row correlation --
`[1.36.0]` just enlarged the blast radius of one failure event from 1 row to up to `chunk_size`, and
made it a live concern given the full-corpus rebuild it gates).

THE BUG: `cur_backend = backend()` is computed ONCE, before the chunk loop, and stamped into
embeddings.meta.json unconditionally at the end. If a chunk's `model.encode()` call throws (bad
input, transient OOM, whatever), the bare `except Exception: vecs = hash-fallback` inside the loop
silently substitutes keyword-hash vectors for THAT CHUNK ONLY -- but the final meta stamp still says
"sentence-transformers" for the whole index. `_index_is_stale()` then trusts the index as fresh,
serving up to `chunk_size` (default 5,000) incompatible hash-fallback rows blended into an otherwise-
real embedding space, undetectable from the outside -- the exact `[1.32.0]` failure mode (near-noise
cosine scores silently trusted), just at row/chunk granularity inside a single build instead of
across a whole rebuild.

THE FIX: every chunk whose real-model encode() call actually raised is tracked in `fallback_events`
(persisted through embeddings.progress.json so it survives an interrupt+resume). If any are recorded
once the shard merge succeeds, embeddings.meta.json is deliberately NOT written (any stale one from a
prior clean build is removed too) -- reusing _index_is_stale()'s existing no-meta-stamp-means-stale
branch rather than new per-row logic -- and embeddings.fallback.json records exactly which rows are
suspect. This file injects a REAL mid-build encode() failure (a stub model, not a mock of
build_index() itself) and confirms: the meta stamp is withheld, the staleness check and search()
both correctly refuse the index end-to-end, the fallback report names the right rows, the array on
disk really does contain hash vectors only in the affected rows (real vectors everywhere else), a
subsequent clean rebuild clears the stale fallback report, and the fallback record survives a
genuine interrupt+resume across the affected chunk."""
import os
import sys
import json
import sqlite3
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)
import embed  # noqa: E402
import numpy as np  # noqa: E402

PASS = 0; FAIL = 0

# Fixed, non-unit-norm value the stub model's successful encode() calls return -- deliberately far
# from _hash_vec()'s always-unit-normalised output (norm 1.0) so a row's actual origin (real model
# call vs. hash fallback) is verifiable straight off the merged embeddings.npy by its norm alone.
_STUB_FILL = 0.01
_STUB_NORM = float(np.linalg.norm(np.full(embed.DIM, _STUB_FILL, dtype=np.float32)))


def ok(name, cond):
    global PASS, FAIL
    print(("PASS " if cond else "FAIL ") + name)
    if cond: PASS += 1
    else: FAIL += 1


def _make_db(path, n_rows, min_len=80):
    """Same fixture shape as test_embed_checkpoint.py's -- schema-compatible with the real `pages`
    table, text long enough to clear min_chars=60 and varied per row."""
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


class _StubModel:
    """A truthy, `_load_model()`-shaped stand-in whose `.encode()` fails on chosen call indices
    (0-based, one call per chunk within a single build_index() invocation) and otherwise returns a
    fixed, easily-distinguished-from-hash-vectors vector. Real defect reproduction, not a mock of
    build_index() itself -- the SAME bare `except Exception` inside build_index()'s chunk loop
    catches this exception and substitutes real _hash_vec() output, exactly as it would for an
    actual transient model failure."""
    def __init__(self, fail_on=frozenset()):
        self.calls = 0
        self.fail_on = set(fail_on)

    def encode(self, texts, normalize_embeddings=True, batch_size=64):
        idx = self.calls
        self.calls += 1
        if idx in self.fail_on:
            raise RuntimeError("simulated model.encode() failure (chunk %d)" % idx)
        return np.full((len(texts), embed.DIM), _STUB_FILL, dtype=np.float32)


def test_partial_encode_failure_leaves_index_untrusted(tmp_root):
    """The core scenario: one chunk's encode() call fails mid-build while the backend is otherwise
    "sentence-transformers". Confirms the meta stamp is withheld, staleness/search() both refuse the
    index end-to-end, the fallback report names the right rows, and the on-disk array genuinely
    contains hash vectors ONLY in the affected rows."""
    db = os.path.join(tmp_root, "partial.db")
    _make_db(db, n_rows=17)
    out = os.path.join(tmp_root, "partial_out")
    os.makedirs(out, exist_ok=True)

    # chunk_size=5 over 17 rows -> shards [0:1-5] [1:6-10] [2:11-15] [3:16-17]; fail chunk 1 only.
    stub = _StubModel(fail_on={1})
    real_load_model = embed._load_model
    embed._load_model = lambda: stub
    try:
        n = embed.build_index(db, out, limit=17, min_chars=60, chunk_size=5)
    finally:
        embed._load_model = real_load_model

    ok("partial_fallback_build_still_returns_full_row_count", n == 17)

    meta_path = embed._meta_path(out)
    ok("partial_fallback_build_does_NOT_write_meta_stamp", not os.path.exists(meta_path))

    fallback_path = embed._fallback_path(out)
    ok("partial_fallback_build_writes_fallback_report", os.path.exists(fallback_path))
    report = json.load(open(fallback_path, encoding="utf-8"))
    ok("fallback_report_backend_intended_is_sentence_transformers",
       report.get("backend_intended") == "sentence-transformers")
    ok("fallback_report_total_rows_matches_build", report.get("total_rows") == 17)
    ok("fallback_report_fallback_rows_matches_the_one_bad_chunk", report.get("fallback_rows") == 5)
    chunks = report.get("fallback_chunks", [])
    ok("fallback_report_names_exactly_one_bad_chunk", len(chunks) == 1)
    if chunks:
        ok("fallback_report_bad_chunk_is_shard_1", chunks[0].get("shard_idx") == 1)
        ok("fallback_report_bad_chunk_row_count_is_5", chunks[0].get("rows") == 5)
        ok("fallback_report_bad_chunk_records_an_error_string",
           isinstance(chunks[0].get("error"), str) and "RuntimeError" in chunks[0]["error"])

    # ---- End-to-end refusal: exactly the [1.32.0] safety mechanism, reused unmodified ----
    ok("partial_fallback_index_reports_stale", embed._index_is_stale(out) is True)
    r = embed.search("alternator", out)
    ok("partial_fallback_index_search_is_not_ready", r.get("ready") is not True)
    ok("partial_fallback_index_search_reports_stale", r.get("stale") is True)

    # ---- The actual on-disk array really is mixed, exactly where expected ----
    arr = np.load(os.path.join(out, "embeddings.npy"))
    ok("partial_fallback_array_row_count_correct", arr.shape == (17, embed.DIM))
    # Rows 0-4 (shard 0) and 10-16 (shards 2,3): real stub-model vectors, norm == _STUB_NORM.
    good_rows = list(range(0, 5)) + list(range(10, 17))
    good_norms_ok = all(abs(float(np.linalg.norm(arr[i])) - _STUB_NORM) < 1e-4 for i in good_rows)
    ok("rows_outside_the_bad_chunk_are_real_stub_model_vectors", good_norms_ok)
    # Rows 5-9 (shard 1, the failed chunk): hash-fallback vectors, unit-normalised (norm ~= 1.0).
    bad_rows = list(range(5, 10))
    bad_norms_ok = all(abs(float(np.linalg.norm(arr[i])) - 1.0) < 1e-4 for i in bad_rows)
    ok("rows_inside_the_bad_chunk_are_unit_normalised_hash_vectors", bad_norms_ok)


def test_clean_rebuild_clears_stale_fallback_report(tmp_root):
    """A clean rebuild over the same index_dir after a partial-fallback build must restore normal
    trust: meta.json written fresh, and the earlier fallback.json removed so it can't be mistaken
    for a report about the CURRENT (actually clean) index."""
    db = os.path.join(tmp_root, "cleanup.db")
    _make_db(db, n_rows=12)
    out = os.path.join(tmp_root, "cleanup_out")
    os.makedirs(out, exist_ok=True)

    stub_bad = _StubModel(fail_on={0})
    real_load_model = embed._load_model
    embed._load_model = lambda: stub_bad
    try:
        embed.build_index(db, out, limit=12, min_chars=60, chunk_size=6)
    finally:
        embed._load_model = real_load_model

    ok("setup_bad_build_left_fallback_report", os.path.exists(embed._fallback_path(out)))
    ok("setup_bad_build_has_no_meta_stamp", not os.path.exists(embed._meta_path(out)))

    stub_good = _StubModel()  # no failures this time
    embed._load_model = lambda: stub_good
    try:
        n = embed.build_index(db, out, limit=12, min_chars=60, chunk_size=6)
    finally:
        embed._load_model = real_load_model

    ok("clean_rebuild_returns_full_row_count", n == 12)
    ok("clean_rebuild_writes_meta_stamp", os.path.exists(embed._meta_path(out)))
    ok("clean_rebuild_removes_stale_fallback_report", not os.path.exists(embed._fallback_path(out)))
    ok("clean_rebuild_index_not_stale", embed._index_is_stale(out) is False)


def test_partial_fallback_survives_interrupt_and_resume(tmp_root):
    """The compound scenario: chunk 0's encode() fails (recorded in fallback_events), the record is
    flushed to embeddings.progress.json, and THEN the process is genuinely killed (a real injected
    exception from _np.save, same technique as test_embed_checkpoint.py's test_interrupt_then_resume)
    while writing the next shard. On resume -- a fresh, non-flaky model this time -- the run must
    finish, but must STILL withhold the meta stamp and report the ORIGINAL chunk-0 fallback, proving
    the safety record survives the interrupt boundary rather than being silently dropped."""
    db = os.path.join(tmp_root, "resume_fb.db")
    _make_db(db, n_rows=20)
    out = os.path.join(tmp_root, "resume_fb_out")
    os.makedirs(out, exist_ok=True)

    # chunk_size=5 over 20 rows -> 4 chunks. Chunk 0 (rows 1-5) fails encode() -> hash fallback,
    # recorded in fallback_events and flushed to progress.json. Then _np.save is made to raise on
    # its 2nd call (shard 1's save) -- i.e. AFTER shard 0 + its progress record already landed.
    stub = _StubModel(fail_on={0})
    real_load_model = embed._load_model
    embed._load_model = lambda: stub

    real_save = embed._np.save
    call_count = {"n": 0}
    CRASH_AT = 2

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
        embed.build_index(db, out, limit=20, min_chars=60, batch_size=16, chunk_size=5)
    except _InjectedCrash:
        crashed = True
    finally:
        embed._np.save = real_save
        embed._load_model = real_load_model

    ok("resume_fb_interrupted_build_actually_raised_the_injected_crash", crashed)
    ok("resume_fb_interrupted_build_has_no_meta_stamp", not os.path.exists(embed._meta_path(out)))

    progress_path = embed._progress_path(out)
    ok("resume_fb_interrupted_build_left_progress_marker", os.path.exists(progress_path))
    with open(progress_path, encoding="utf-8") as f:
        prog = json.load(f)
    prog_fallback = prog.get("fallback_events", [])
    ok("resume_fb_progress_marker_recorded_the_chunk_0_fallback_before_the_crash",
       len(prog_fallback) == 1 and prog_fallback[0].get("shard_idx") == 0)

    # ---- RESUME: a fresh, non-flaky stub model; no fault injected this time ----
    stub2 = _StubModel()  # no failures
    embed._load_model = lambda: stub2
    try:
        n = embed.build_index(db, out, limit=20, min_chars=60, batch_size=16, chunk_size=5)
    finally:
        embed._load_model = real_load_model

    ok("resume_fb_resumed_build_returns_full_row_count", n == 20)

    # ---- The whole point: the ORIGINAL chunk-0 fallback must still be honored post-resume ----
    ok("resume_fb_resumed_build_STILL_has_no_meta_stamp", not os.path.exists(embed._meta_path(out)))
    fallback_path = embed._fallback_path(out)
    ok("resume_fb_resumed_build_writes_fallback_report", os.path.exists(fallback_path))
    report = json.load(open(fallback_path, encoding="utf-8"))
    chunks = report.get("fallback_chunks", [])
    ok("resume_fb_final_report_has_exactly_the_one_original_bad_chunk",
       len(chunks) == 1 and chunks[0].get("shard_idx") == 0 and chunks[0].get("rows") == 5)
    ok("resume_fb_final_index_reports_stale", embed._index_is_stale(out) is True)
    r = embed.search("alternator", out)
    ok("resume_fb_final_index_search_is_not_ready", r.get("ready") is not True)


def main():
    with tempfile.TemporaryDirectory() as tmp_root:
        print("active backend for this run (unused -- all tests here stub _load_model directly):",
              embed.backend())
        test_partial_encode_failure_leaves_index_untrusted(tmp_root)
        test_clean_rebuild_clears_stale_fallback_report(tmp_root)
        test_partial_fallback_survives_interrupt_and_resume(tmp_root)
    return PASS, FAIL


if __name__ == "__main__":
    p, f = main()
    print("\n%d passed, %d failed" % (p, f))
    sys.exit(1 if f else 0)

# END OF FILE
