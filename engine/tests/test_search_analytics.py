#!/usr/bin/env python3
"""v1.31 (gap-sweep item 5): regression coverage for the "search" analytics event kind.

THE BUG: "search" has been a declared-valid analytics kind since engine/analytics.py's _VALID set was
first written -- summary()'s own top_searches panel has always called top(index_dir, "search", 8) --
but nothing anywhere ever actually logged one (confirmed live via grep of the whole engine/ tree for
analytics.log( before this fix: exactly 2 real call sites existed, "gap" on zero-result queries and
the client-posted "click" beacon; "search" itself was write-side dead despite being read-side wired).

THE FIX: engine/features/routes/search.py's r_search now logs one "search" event per real (non-cached)
/api/search call, with the raw query text and the final result count -- and engine/analytics.py's
log() gained a matching "n" extra-field whitelist entry to carry that count.

This test proves the mechanism directly: build a real index/analytics.jsonl via analytics.log() itself
(the same function the route now calls) and confirm top()/summary() actually read "search" events back,
not just that logging "doesn't crash"."""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)
import analytics                                          # noqa: E402

PASS = 0; FAIL = 0


def ok(name, cond):
    global PASS, FAIL
    print(("PASS " if cond else "FAIL ") + name)
    if cond: PASS += 1
    else: FAIL += 1


def main():
    tmp = tempfile.mkdtemp()

    # "search" was already declared valid before this fix -- the bug was that nothing ever called
    # log(..., "search", ...). Confirm the kind itself isn't silently remapped to "tool".
    ok("search_is_a_declared_valid_kind", "search" in analytics._VALID)

    # Log 3 "search" events the same way routes/search.py's r_search now does: raw query text + a
    # result count via the extra={"n": ...} whitelist this fix added.
    r1 = analytics.log(tmp, "search", "alternator", {"n": 5})
    r2 = analytics.log(tmp, "search", "alternator", {"n": 5})
    r3 = analytics.log(tmp, "search", "water pump gasket", {"n": 3})
    ok("log_returns_true_for_every_call", r1 and r2 and r3)

    lines = open(os.path.join(tmp, analytics.FNAME), encoding="utf-8").read().splitlines()
    ok("three_real_lines_written", len(lines) == 3)

    import json
    rec = json.loads(lines[0])
    ok("record_kind_is_search_not_remapped_to_tool", rec.get("k") == "search")
    ok("record_carries_the_raw_query_text", rec.get("q") == "alternator")
    ok("record_carries_the_new_n_field_as_a_real_int_not_a_string",
       rec.get("n") == 5 and isinstance(rec.get("n"), int))

    # A non-numeric "n" must be silently dropped, never raise -- matches every other extra field's
    # "best-effort, never breaks logging" contract (rank's own int-coercion guard right above it).
    r4 = analytics.log(tmp, "search", "bad n test", {"n": "not-a-number"})
    ok("non_numeric_n_does_not_raise_and_still_logs_the_event", r4)
    last = json.loads(open(os.path.join(tmp, analytics.FNAME), encoding="utf-8").read().splitlines()[-1])
    ok("non_numeric_n_is_silently_omitted_not_stored_as_a_string", "n" not in last)

    # The read side (top()/summary()) must actually surface these -- this is the panel that was
    # silently empty before this fix (top(index_dir, "search", 8) always returned [] with zero writers).
    tops = analytics.top(tmp, "search", 8)
    ok("top_searches_now_returns_real_aggregated_data", bool(tops))
    top_keys = [t.get("key") for t in tops]
    ok("alternator_is_the_most_frequent_logged_search_2x", top_keys and top_keys[0] == "alternator")

    summ = analytics.summary(tmp)
    ok("summary_by_kind_counts_search_events", summ.get("by_kind", {}).get("search", 0) >= 4)

    return PASS, FAIL


if __name__ == "__main__":
    p, f = main()
    print("\n%d passed, %d failed" % (p, f))
    sys.exit(1 if f else 0)

# END OF FILE
