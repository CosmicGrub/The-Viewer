#!/usr/bin/env python3
"""THE VIEWER -- regression coverage for engine/conflicts.py's vehicle-annotation fix.

conflicts.py's own inline self-test (`python conflicts.py`) already covers detect()'s core math in
isolation, but that self-test is NOT run by verify_all.py -- verify_all.py auto-discovers this
directory's test_*.py files by glob, it does not separately invoke arbitrary modules' __main__ blocks.
This file is the real regression-suite coverage for the fix, so it's part of that gate going forward.

TWO PASSES (see conflicts.py's module docstring for the full history):

Pass 1 tried grouping by (type, unit, vehicle) instead of (type, unit), to stop unrelated vehicles'
naturally-different specs from being pooled into a false "conflict" (confirmed on the real corpus: a
"WINCH INSTALLATION" sweep pooled 4 documents from 3 different vehicles into one group). Adversarial
review then caught a serious SAFETY REGRESSION in that design: "vehicle" is a raw ingest-folder name
(viewer_ingest.py), not a canonical vehicle ID, so the SAME real vehicle filed under two different
folder spellings (e.g. "HMMWV" vs "TM,S HUMMERS,ALL", both real folder names in this corpus) got hard-
split into separate buckets of 1 -- a genuine cross-manual disagreement was silently dropped, returning
zero conflicts instead of one. For a module whose whole purpose is catching exactly this class of
disagreement, that is worse than the false positive it replaced.

Pass 2 (the current code, tested here) restores the ORIGINAL (type, unit)-only grouping -- identical
recall to the pre-vehicle-scoping code, nothing is ever silently dropped -- and instead ANNOTATES each
flagged group with "vehicle" (single label if unambiguous, else ""), "vehicles" (sorted distinct labels
seen), and "cross_vehicle" (bool). A caller/UI can de-emphasize cross_vehicle=True conflicts, but they
are always present in the output.

KNOWN REMAINING LIMITATIONS (conflicts.py's module docstring says this too, this file does not claim
otherwise): "vehicle" is a raw ingest-folder name, not a curated identity, so cross_vehicle=False can
still in principle mean "two different real vehicles filed under the same broad folder" (e.g. "WORK",
~65% of this corpus). Same-vehicle-different-part over-pooling (many different bolts on ONE HMMWV
sharing "BOLT" as their FTS-matched subject) also still applies, unchanged from before either pass.

All synthetic rows below are shaped exactly like measures.find_for_query()'s real output: keys type,
unit, value, doc, tm, vehicle, page, page_url.

Run: python tests/test_conflicts.py"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE)

import conflicts
import validate

passed, failed = [], []
def ok(name, cond):
    (passed if cond else failed).append(name)


def _row(type_, unit, value, doc, vehicle, tm=None, page=1, page_url=None):
    """One synthetic measures.find_for_query()-shaped row."""
    return {"type": type_, "unit": unit, "value": value, "doc": doc, "tm": tm or ("TM-%s" % doc),
            "vehicle": vehicle, "page": page, "page_url": page_url}


# =====================================================================================================
# Section 1 -- THE SAFETY REGRESSION Pass 2 fixes. The SAME real vehicle, filed under two different
# ingest-folder spellings ("HMMWV" and "TM,S HUMMERS,ALL" -- both real folder names in this corpus), with
# a genuine cross-manual torque disagreement. Pass 1's hard vehicle split returned [] for this (confirmed
# live against the real corpus before reverting -- see conflicts.py's module docstring). This is the
# core regression guard: it must return exactly 1 conflict (never silently drop a real disagreement),
# marked cross_vehicle=True since the code cannot know these are the same real vehicle.
# =====================================================================================================
try:
    same_real_vehicle_rows = [
        _row("torque", "ft-lb", "35 ft-lb", doc="1", vehicle="HMMWV"),
        _row("torque", "ft-lb", "50 ft-lb", doc="2", vehicle="TM,S HUMMERS,ALL"),
    ]
    srv_cs = conflicts.detect(same_real_vehicle_rows)
    ok("same_real_vehicle_different_spelling_not_silently_dropped", len(srv_cs) == 1)
    if srv_cs:
        ok("same_real_vehicle_marked_cross_vehicle", srv_cs[0].get("cross_vehicle") is True)
        ok("same_real_vehicle_vehicles_list", srv_cs[0].get("vehicles") == ["HMMWV", "TM,S HUMMERS,ALL"])
        ok("same_real_vehicle_ambiguous_vehicle_field_blank", srv_cs[0].get("vehicle") == "")
except Exception as e:
    failed.append("section1_same_real_vehicle_different_spelling(%s)" % e)


# =====================================================================================================
# Section 2 -- a genuinely different-vehicle pooling must still be SURFACED (never silently dropped),
# but marked cross_vehicle=True so a human knows to double-check it before trusting it like a confirmed
# single-vehicle hit. This is Pass 1's own original regression-guard case, re-purposed: Pass 1 asserted
# this returns [], Pass 2 asserts it is surfaced-but-annotated instead.
# =====================================================================================================
try:
    cross_vehicle_rows = [
        _row("torque", "ft-lb", "35 ft-lb", doc="500", vehicle="HMMWV"),
        _row("torque", "ft-lb", "70 ft-lb", doc="600", vehicle="M35A2"),
    ]
    cross_cs = conflicts.detect(cross_vehicle_rows)
    ok("cross_vehicle_surfaced_not_dropped", len(cross_cs) == 1)
    if cross_cs:
        ok("cross_vehicle_flag_true", cross_cs[0].get("cross_vehicle") is True)
        ok("cross_vehicle_vehicles_list", cross_cs[0].get("vehicles") == ["HMMWV", "M35A2"])
except Exception as e:
    failed.append("section2_cross_vehicle_surfaced_not_dropped(%s)" % e)


# =====================================================================================================
# Section 3 -- same-vehicle positive case must keep working: same (type, unit), SAME vehicle, 2+
# distinct documents, disagreeing beyond tolerance -> exactly 1 conflict, with correct min/max/
# spread_pct/severity/n_docs, its "vehicle" field matches, and cross_vehicle is False.
# =====================================================================================================
try:
    same_vehicle_rows = [
        _row("torque", "ft-lb", "35 ft-lb", doc="10", vehicle="HMMWV", tm="TM 9-2320-280-24-1"),
        _row("torque", "ft-lb", "50 ft-lb", doc="22", vehicle="HMMWV", tm="TM 9-2320-280-24-2"),
    ]
    same_cs = conflicts.detect(same_vehicle_rows)
    ok("same_vehicle_exactly_one_conflict", len(same_cs) == 1)
    if same_cs:
        c = same_cs[0]
        ok("same_vehicle_min_max", c.get("min") == 35 and c.get("max") == 50)
        ok("same_vehicle_spread_pct", c.get("spread_pct") == 30.0)   # (50-35)/50 = 0.30
        ok("same_vehicle_severity_high", c.get("severity") == "high")   # torque is safety-critical
        ok("same_vehicle_n_docs", c.get("n_docs") == 2)
        ok("same_vehicle_field_matches", c.get("vehicle") == "HMMWV")
        ok("same_vehicle_not_cross_vehicle", c.get("cross_vehicle") is False)
except Exception as e:
    failed.append("section3_same_vehicle_positive_case(%s)" % e)


# =====================================================================================================
# Section 4 -- missing-vehicle rows (vehicle="" or None, or the key entirely absent) still bucket
# together and can still be compared/flagged -- never silently dropped from all output just because
# the vehicle field is blank. A blank vehicle also must not make an otherwise-single-vehicle group look
# cross_vehicle (blank contributes no identity, it doesn't count as a distinct "vehicle").
# =====================================================================================================
try:
    missing_vehicle_rows = [
        _row("pressure", "psi", "30 psi", doc="700", vehicle=""),
        _row("pressure", "psi", "45 psi", doc="800", vehicle=None),
    ]
    missing_cs = conflicts.detect(missing_vehicle_rows)
    ok("missing_vehicle_still_flagged", len(missing_cs) == 1)
    if missing_cs:
        ok("missing_vehicle_field_is_blank_string", missing_cs[0].get("vehicle") == "")
        ok("missing_vehicle_not_cross_vehicle", missing_cs[0].get("cross_vehicle") is False)
        ok("missing_vehicle_n_docs_correct", missing_cs[0].get("n_docs") == 2)

    # a row with no "vehicle" key at all (not just a blank one) must behave identically
    no_key_rows = [
        {"type": "pressure", "unit": "psi", "value": "30 psi", "doc": "900", "tm": "TM-1", "page": 1},
        {"type": "pressure", "unit": "psi", "value": "45 psi", "doc": "901", "tm": "TM-2", "page": 2},
    ]
    no_key_cs = conflicts.detect(no_key_rows)
    ok("missing_vehicle_key_entirely_absent_still_flagged", len(no_key_cs) == 1)

    # one blank + one populated vehicle: the populated one should NOT be marked cross_vehicle just
    # because a blank row is also present -- blank contributes no identity.
    mixed_rows = [
        _row("pressure", "psi", "30 psi", doc="910", vehicle=""),
        _row("pressure", "psi", "45 psi", doc="911", vehicle="M35A2"),
    ]
    mixed_cs = conflicts.detect(mixed_rows)
    ok("blank_plus_populated_vehicle_still_flagged", len(mixed_cs) == 1)
    if mixed_cs:
        ok("blank_plus_populated_not_cross_vehicle", mixed_cs[0].get("cross_vehicle") is False)
        ok("blank_plus_populated_vehicle_field_is_the_real_one", mixed_cs[0].get("vehicle") == "M35A2")
except Exception as e:
    failed.append("section4_missing_vehicle_not_dropped(%s)" % e)


# =====================================================================================================
# Section 5 -- R13 "never fabricate" survives untouched: values validate.py QUARANTINES (garbled OCR /
# physically impossible) are still excluded BEFORE grouping, regardless of vehicle. Construct a
# genuinely-quarantined value the same way validate.py's own self-test does (an out-of-physical-range
# torque reading) so this actually exercises validate_value()'s quarantine path, not a guessed shape.
# =====================================================================================================
try:
    garbled_value = "35000000 ft-lb"   # validate.py's own self-test: torque this large -> quarantine
    ok("sanity_garbled_value_actually_quarantines",
       validate.validate_value("torque", garbled_value, "ft-lb")["status"] == "quarantine")

    quarantine_rows = [
        _row("torque", "ft-lb", "35 ft-lb", doc="1000", vehicle="HMMWV"),
        _row("torque", "ft-lb", garbled_value, doc="1001", vehicle="HMMWV"),   # would "disagree" wildly
    ]
    # if the quarantined value were NOT dropped pre-grouping, the huge spread between 35 and
    # 35,000,000 would trivially clear rel_tol and manufacture a conflict from garbage.
    q_cs = conflicts.detect(quarantine_rows)
    ok("quarantined_value_excluded_pre_grouping_no_conflict", q_cs == [])
except Exception as e:
    failed.append("section5_quarantine_survives_vehicle_annotation(%s)" % e)


# =====================================================================================================
# Section 6 -- internal-whitespace normalization: repeated internal spaces collapse to the same vehicle
# label ("M35A2  DUMP TRUCK" double space == "M35A2 DUMP TRUCK" single space). This does NOT solve a
# token-boundary difference like "HUMMERS,ALL" (no space) vs "HUMMERS, ALL" (one space) -- that harder
# case is exactly Section 1 above, and is handled by never-dropping + cross_vehicle=True, not by
# normalization.
# =====================================================================================================
try:
    whitespace_rows = [
        _row("torque", "ft-lb", "35 ft-lb", doc="1", vehicle="M35A2  DUMP TRUCK"),
        _row("torque", "ft-lb", "50 ft-lb", doc="2", vehicle="M35A2 DUMP TRUCK"),
    ]
    ws_cs = conflicts.detect(whitespace_rows)
    ok("internal_whitespace_collapsed_same_vehicle", len(ws_cs) == 1)
    if ws_cs:
        ok("internal_whitespace_not_cross_vehicle", ws_cs[0].get("cross_vehicle") is False)
except Exception as e:
    failed.append("section6_internal_whitespace_normalization(%s)" % e)


# =====================================================================================================
# Section 7 -- realistic scenario mirroring the REAL "WINCH INSTALLATION" corpus example. 4 synthetic
# rows with the exact real vehicle strings and TM numbers from the bug report, disagreeing electrical
# readings. Nothing is dropped: all 4 rows land in ONE (type,unit) group (exactly like the pre-fix code),
# but the group is correctly marked cross_vehicle=True with all 3 distinct vehicle labels listed, so a
# human reviewing it can see at a glance that it spans unrelated equipment instead of it being either
# silently absent (Pass 1's bug) or silently presented as a confident single-vehicle hit (the original
# bug this whole effort started from).
# =====================================================================================================
try:
    # 4 distinct values (one per doc) so each doc earns its own representative citation --
    # detect()'s citation dedup keeps one representative per distinct VALUE, not per doc (pre-existing
    # behavior, unrelated to this fix); using 4 distinct values here isolates that from what this
    # section is actually testing (nothing gets dropped for being cross-vehicle).
    winch_rows = [
        _row("electrical", "V", "24 V", doc="983", vehicle="5 TON", tm="TM 9-2320-272-24-4"),
        _row("electrical", "V", "12 V", doc="13781", vehicle="TM,S HUMMERS,ALL", tm="TM 9-2320-387-24-1"),
        _row("electrical", "V", "18 V", doc="14105", vehicle="TM,S HUMMERS,ALL", tm="TM 9-2320-387-24-2"),
        _row("electrical", "V", "6 V", doc="870", vehicle="2.5 Ton Truck", tm="TM 9-2320-361-34"),
    ]
    winch_cs = conflicts.detect(winch_rows)
    ok("winch_one_group_all_4_docs_present", len(winch_cs) == 1)
    if winch_cs:
        wc = winch_cs[0]
        ok("winch_marked_cross_vehicle", wc.get("cross_vehicle") is True)
        ok("winch_vehicles_lists_all_three", wc.get("vehicles") == ["2.5 TON TRUCK", "5 TON", "TM,S HUMMERS,ALL"])
        ok("winch_vehicle_field_blank_when_ambiguous", wc.get("vehicle") == "")
        cited_docs = {v["doc"] for v in wc.get("values", [])}
        ok("winch_all_4_docs_cited_nothing_hidden", cited_docs == {"983", "13781", "14105", "870"})
except Exception as e:
    failed.append("section7_realistic_winch_installation_scenario(%s)" % e)


# =====================================================================================================
# Section 8 -- sort order: a confirmed single-vehicle conflict must not be outranked by an ambiguous
# cross_vehicle=True conflict of the same severity, even if the ambiguous one has a wider spread. A UI
# that only shows the top N (engine/ui/part.html does) would otherwise let a likely-false-positive
# crowd out a real, confirmed safety conflict. Reproduces the exact scenario adversarial review flagged.
# =====================================================================================================
try:
    mixed_rows = [
        _row("torque", "ft-lb", "35", doc="1", vehicle="HMMWV"),
        _row("torque", "ft-lb", "50", doc="2", vehicle="HMMWV"),                       # confirmed, 30% spread
        _row("electrical", "A", "10", doc="3", vehicle="5 TON"),
        _row("electrical", "A", "40", doc="4", vehicle="TM,S HUMMERS,ALL"),            # ambiguous, 75% spread
    ]
    sorted_cs = conflicts.detect(mixed_rows)
    ok("sort_both_conflicts_present", len(sorted_cs) == 2)
    if len(sorted_cs) == 2:
        ok("sort_confirmed_vehicle_ranks_first", sorted_cs[0]["type"] == "torque" and sorted_cs[0]["cross_vehicle"] is False)
        ok("sort_ambiguous_vehicle_ranks_second_despite_wider_spread", sorted_cs[1]["type"] == "electrical" and sorted_cs[1]["cross_vehicle"] is True)
except Exception as e:
    failed.append("section8_sort_order_confirmed_before_ambiguous(%s)" % e)


# =====================================================================================================
print("\ntest_conflicts: %d passed, %d failed" % (len(passed), len(failed)))
if failed:
    print("FAILED: " + ", ".join(failed))
    sys.exit(1)
print("PASSED: " + ", ".join(passed))
sys.exit(0)
# END OF FILE
