#!/usr/bin/env python3
"""v1.29 (search-latency fix): regression coverage for the fuzzy_terms() de-duplication.

THE BUG (confirmed live before fixing, see docs/CHANGELOG.md [1.29.0]): search_feature.py's
fuzzy_terms() is a real vocabulary scan against pages_vocab (5-49ms measured per word on the real
corpus, not free). build_match() (via _alts()) and _token_alts() each called it fresh on the
IDENTICAL tokens within one search() request -- unconditionally doubling the cost of every fuzzy
query for zero behavior difference. A third call site (build_match()'s nomenclature-variant widening
pass) could add a third redundant scan on overlapping tokens.

THE FIX: a request-scoped `fuzzy_cache` dict, created once per search() call and threaded through
every build_match()/_alts()/_token_alts() call in that request via _cached_fuzzy_terms(). Backward
compatible: fuzzy_cache=None (the default for any caller that doesn't opt in, e.g. this file's own
direct calls to _alts()/build_match() without a cache) preserves the exact old always-call-fresh
behavior.

This test proves the mechanism directly (counts real calls to the underlying fuzzy_terms(), not
just "search() doesn't crash"), and proves it's not vacuous by first showing the OLD (uncached)
call pattern really does double-count, then showing the NEW pattern (via search()'s own internal
fuzzy_cache) does not."""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)
import fixture                                            # noqa: E402

PASS = 0; FAIL = 0


def ok(name, cond):
    global PASS, FAIL
    print(("PASS " if cond else "FAIL ") + name)
    if cond: PASS += 1
    else: FAIL += 1


def main():
    tmp = tempfile.mkdtemp()
    db, _corr = fixture.build(tmp)
    import viewer_app as V
    V.DB_PATH = db; V.INDEX_DIR = os.path.dirname(db)
    V._VOCAB_READY = False
    from features import search_feature as SF

    con = V.db()

    # A query whose words are real, indexed, fuzzy-eligible tokens in the fixture (>=5 chars,
    # alphabetic) -- "brake" and "valve" both appear verbatim in fixture.py's page text, and a
    # near-miss (edit-distance-1) alternative existing in the SAME vocab is what makes
    # fuzzy_terms() actually do scan work rather than short-circuiting on an empty vocab.
    Q = "brake valve"

    # ---- sanity: fuzzy_terms() itself is real, callable, and returns something for this query's
    # words against this fixture (not asserting non-empty -- the fixture is tiny -- just that the
    # underlying scan runs without error, so a later zero call-count isn't hiding a silent no-op).
    try:
        SF.fuzzy_terms(con, "brake")
        ok("sanity_fuzzy_terms_callable_no_error", True)
    except Exception as e:
        ok("sanity_fuzzy_terms_callable_no_error(%s)" % e, False)

    # ---- prove the OLD pattern (no shared cache) really does call fuzzy_terms() twice on the
    # identical tokens -- this is what build_match()+_token_alts() did before the fix, and it's
    # what any caller still gets today if it doesn't opt into fuzzy_cache (backward compat check).
    calls = []
    real_fuzzy_terms = SF.fuzzy_terms

    def counting_fuzzy_terms(con_, word, *a, **kw):
        calls.append(word)
        return real_fuzzy_terms(con_, word, *a, **kw)

    SF.fuzzy_terms = counting_fuzzy_terms
    try:
        toks = ["brake", "valve"]
        calls[:] = []
        m1 = SF.build_match(con, Q, False, True)                       # no fuzzy_cache -> old behavior
        talts1 = SF._token_alts(con, toks, True)                       # no fuzzy_cache -> old behavior
        ok("uncached_build_match_and_token_alts_each_call_fuzzy_terms_per_token",
           sorted(calls) == sorted(toks + toks))  # each of the 2 tokens scanned twice = 4 calls total

        # ---- prove the NEW pattern (shared fuzzy_cache) calls fuzzy_terms() exactly once per
        # distinct token, even across build_match() + _token_alts() in the same "request".
        calls[:] = []
        cache = {}
        m2 = SF.build_match(con, Q, False, True, cache)
        talts2 = SF._token_alts(con, toks, True, cache)
        ok("cached_build_match_and_token_alts_call_fuzzy_terms_once_per_token",
           sorted(calls) == sorted(toks))  # each of the 2 tokens scanned exactly once = 2 calls total
        ok("cached_and_uncached_build_match_produce_identical_expression", m1 == m2)
        ok("cached_and_uncached_token_alts_produce_identical_result", talts1 == talts2)

        # ---- prove search() itself (the real, live code path) uses the shared-cache pattern --
        # not by re-deriving the exact count (search() also runs a nomenclature-widening variant
        # pass that may add its own tokens), but by confirming NO token is scanned more than once
        # despite search() internally calling build_match() at least once and _token_alts() once
        # on the same q_toks. Single-word query ("brake valve"'s AND semantics genuinely matches
        # zero fixture pages -- confirmed directly, not a bug in this fix -- so use just "brake",
        # which real fixture text ("Operating the brake system...") does match, to also confirm
        # search() returns real rows post-fix, not just that no token double-scans.
        calls[:] = []
        rows = SF.search("brake", limit=20)
        from collections import Counter
        counts = Counter(calls)
        dupes = {w: n for w, n in counts.items() if n > 1}
        ok("search_end_to_end_never_scans_the_same_token_twice", not dupes)
        ok("search_still_returns_real_rows", bool(rows))
    finally:
        SF.fuzzy_terms = real_fuzzy_terms

    # ---- backward compatibility: no caller anywhere breaks if it never passes fuzzy_cache at all
    # (the exact shape of every pre-existing call site in this codebase, e.g. core_pillars.py's own
    # independent mirror, and this test file's own calls above).
    try:
        m3 = SF.build_match(con, Q)                # positional-only, matches every old call site
        ok("build_match_still_works_with_no_fuzzy_cache_arg_at_all", m3 is not None)
    except Exception as e:
        ok("build_match_still_works_with_no_fuzzy_cache_arg_at_all(%s)" % e, False)

    con.close()
    return PASS, FAIL


if __name__ == "__main__":
    p, f = main()
    print("\n%d passed, %d failed" % (p, f))
    sys.exit(1 if f else 0)

# END OF FILE
