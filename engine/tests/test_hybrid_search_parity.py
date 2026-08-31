#!/usr/bin/env python3
"""v1.31 (gap-sweep item 2): regression coverage for hybrid.hybrid_search()'s parameter parity fix.

THE BUG: hybrid_search(q, core, index_dir, limit=25) called core.search(exp["expanded"], limit*2) with
ONLY 2 positional args -- mode/match_any/use_fuzzy/tm/vehicle/nsn were silently dropped regardless of
what the caller passed. /api/search_hybrid (the route wrapping this) inherited the same gap: it read
only q/limit from the querystring, so switching the UI from /api/search to this route (as the gap-sweep
report recommended) would have broken the SIDE toggle, tm:/vehicle:/nsn: operator syntax, and the
MATCH_ANY/fuzzy toggle outright, and mode="text" would have been silently unsupported.

THE FIX: hybrid_search() gained mode/match_any/use_fuzzy/tm/vehicle/nsn keyword params (defaults match
search_feature.search()'s own, so an un-migrated caller is unaffected) and now forwards every one of
them into its own core.search() call.

This test proves the mechanism directly -- a fake `core` object records the EXACT arguments
hybrid_search() actually passes to .search(), so this fails loudly if a future edit silently drops a
parameter again, not just "hybrid_search() doesn't crash"."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)
import hybrid                                              # noqa: E402

PASS = 0; FAIL = 0


def ok(name, cond):
    global PASS, FAIL
    print(("PASS " if cond else "FAIL ") + name)
    if cond: PASS += 1
    else: FAIL += 1


class _FakeCore:
    """Records the exact call hybrid_search() makes to .search(), instead of hitting a real DB --
    this test is about parameter THREADING, not search result correctness (already covered by
    test_search_quality.py / test_search_fuzzy_cache.py / the live verification in CHANGELOG [1.31.0])."""
    DB_PATH = ""

    def __init__(self):
        self.calls = []

    def search(self, q, limit, mode=None, match_any=False, use_fuzzy=True, tm=None, vehicle=None, nsn=None):
        self.calls.append({"q": q, "limit": limit, "mode": mode, "match_any": match_any,
                            "use_fuzzy": use_fuzzy, "tm": tm, "vehicle": vehicle, "nsn": nsn})
        return []


def main():
    core = _FakeCore()

    # Default-params call (no mode/match_any/etc passed) -- must behave exactly like the pre-fix
    # signature: everything defaults to what search_feature.search() itself defaults to.
    hybrid.hybrid_search("brake", core, "index", limit=10)
    ok("default_call_made_exactly_one_search_call", len(core.calls) == 1)
    c = core.calls[-1]
    ok("default_mode_is_none", c["mode"] is None)
    ok("default_match_any_is_false", c["match_any"] is False)
    ok("default_use_fuzzy_is_true", c["use_fuzzy"] is True)
    ok("default_tm_vehicle_nsn_are_none", c["tm"] is None and c["vehicle"] is None and c["nsn"] is None)
    ok("limit_doubled_for_the_fusion_candidate_pool_unchanged_behavior", c["limit"] == 20)

    # Every non-default param, all at once -- the actual bug this fix closes: NONE of these reached
    # core.search() before this fix, regardless of what was passed to hybrid_search().
    core2 = _FakeCore()
    hybrid.hybrid_search("gasket", core2, "index", limit=15, mode="text", match_any=True,
                         use_fuzzy=False, tm="TM 9-2320-280-24P", vehicle="HMMWV", nsn="5305-01-674-1467")
    c2 = core2.calls[-1]
    ok("mode_text_variant_reaches_core_search", c2["mode"] == "text")
    ok("match_any_true_reaches_core_search", c2["match_any"] is True)
    ok("use_fuzzy_false_reaches_core_search", c2["use_fuzzy"] is False)
    ok("tm_operator_reaches_core_search", c2["tm"] == "TM 9-2320-280-24P")
    ok("vehicle_operator_reaches_core_search", c2["vehicle"] == "HMMWV")
    ok("nsn_operator_reaches_core_search", c2["nsn"] == "5305-01-674-1467")

    # Backward compatibility: the ORIGINAL (q, core, index_dir, limit) positional-only call shape --
    # every pre-existing call site anywhere in the repo used exactly this -- must still work unchanged.
    core3 = _FakeCore()
    try:
        hybrid.hybrid_search("torque", core3, "index", 25)
        ok("original_positional_only_call_shape_still_works", len(core3.calls) == 1)
    except Exception as e:
        ok("original_positional_only_call_shape_still_works(%s)" % e, False)

    return PASS, FAIL


if __name__ == "__main__":
    p, f = main()
    print("\n%d passed, %d failed" % (p, f))
    sys.exit(1 if f else 0)

# END OF FILE
