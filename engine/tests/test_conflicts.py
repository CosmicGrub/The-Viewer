#!/usr/bin/env python3
"""THE VIEWER -- regression coverage for engine/conflicts.py's vehicle-scoped grouping fix.

conflicts.py's own inline self-test (`python conflicts.py`) already covers detect()'s core math in
isolation, but that self-test is NOT run by verify_all.py -- verify_all.py auto-discovers this
directory's test_*.py files by glob, it does not separately invoke arbitrary modules' __main__ blocks.
This file is the real regression-suite coverage for the fix, so it's part of that gate going forward.

THE BUG (confirmed against real production data): detect() used to group extracted measurement values
purely by (type, unit), with no regard for which vehicle/document family each value came from. A
generic FTS-matched subject (e.g. "WINCH INSTALLATION") could pool numeric readings from completely
unrelated vehicles into one group and flag their natural disagreement as a "conflict", when it's really
just different real specs for different real equipment. Confirmed on the real corpus, a "WINCH
INSTALLATION" sweep pooled 4 documents from 3 different vehicles:
    doc 983   vehicle="5 TON"              tm="TM 9-2320-272-24-4"
    doc 13781 vehicle="TM,S HUMMERS,ALL"   tm="TM 9-2320-387-24-1"
    doc 14105 vehicle="TM,S HUMMERS,ALL"   tm="TM 9-2320-387-24-2"
    doc 870   vehicle="2.5 Ton Truck"      tm="TM 9-2320-361-34"

THE FIX: group by (type, unit, vehicle) instead, where vehicle = (row["vehicle"] or "").strip().upper().
This separates unrelated vehicles into distinct buckets while still correctly keeping genuine
same-vehicle disagreements (two manuals, same vehicle, different values) grouped and flagged -- the
real, intended positive case. Section 1 below is the exact bug being fixed: it must FAIL against the
OLD (type,unit)-only grouping and PASS after the fix (verified by hand while writing this file, see
the task notes -- temporarily reverting conflicts.py's grouping key reproduces the failure).

KNOWN REMAINING LIMITATION (conflicts.py's module docstring and detect()'s own docstring say this too):
vehicle-scoping does NOT fully solve same-vehicle-different-part collisions -- many different bolts on
ONE HMMWV sharing "BOLT" as their FTS-matched subject could still falsely pool. Narrower than before
(corpus-wide -> vehicle-wide), not a complete fix. This file does not claim otherwise.

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
# Section 1 -- THE bug being fixed. Same (type, unit), two DIFFERENT vehicles, values that disagree well
# past rel_tol. Under the OLD (type,unit)-only grouping this pools into a single false "conflict";
# after the fix, each vehicle only contributes one row to its own bucket, so nothing is flagged at all.
# This is the exact regression guard: it must fail against the old grouping key and pass against the
# new one (confirmed by hand: temporarily reverting the grouping key to (t, u) reproduces the failure --
# len(detect(rows)) == 1 instead of 0 -- then re-applying the (t, u, veh) key fixes it).
# =====================================================================================================
try:
    cross_vehicle_rows = [
        _row("torque", "ft-lb", "35 ft-lb", doc="500", vehicle="HMMWV"),
        _row("torque", "ft-lb", "70 ft-lb", doc="600", vehicle="M35A2"),
    ]
    cross_cs = conflicts.detect(cross_vehicle_rows)
    ok("cross_vehicle_regression_guard_no_conflict", cross_cs == [])
except Exception as e:
    failed.append("section1_cross_vehicle_regression_guard(%s)" % e)


# =====================================================================================================
# Section 2 -- same-vehicle positive case must keep working: same (type, unit), SAME vehicle, 2+
# distinct documents, disagreeing beyond tolerance -> exactly 1 conflict, with correct min/max/
# spread_pct/severity/n_docs, and its "vehicle" field matches.
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
except Exception as e:
    failed.append("section2_same_vehicle_positive_case(%s)" % e)


# =====================================================================================================
# Section 3 -- missing-vehicle rows (vehicle="" or None, or the key entirely absent) still bucket
# together and can still be compared/flagged -- never silently dropped from all output just because
# the vehicle field is blank.
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
        ok("missing_vehicle_n_docs_correct", missing_cs[0].get("n_docs") == 2)

    # a row with no "vehicle" key at all (not just a blank one) must behave identically
    no_key_rows = [
        {"type": "pressure", "unit": "psi", "value": "30 psi", "doc": "900", "tm": "TM-1", "page": 1},
        {"type": "pressure", "unit": "psi", "value": "45 psi", "doc": "901", "tm": "TM-2", "page": 2},
    ]
    no_key_cs = conflicts.detect(no_key_rows)
    ok("missing_vehicle_key_entirely_absent_still_flagged", len(no_key_cs) == 1)
except Exception as e:
    failed.append("section3_missing_vehicle_not_dropped(%s)" % e)


# =====================================================================================================
# Section 4 -- R13 "never fabricate" survives untouched: values validate.py QUARANTINES (garbled OCR /
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
    failed.append("section4_quarantine_survives_vehicle_scoping(%s)" % e)


# =====================================================================================================
# Section 5 -- realistic scenario mirroring the REAL "WINCH INSTALLATION" corpus example. 4 synthetic
# rows with the exact real vehicle strings and TM numbers from the bug report, disagreeing electrical
# readings. Asserts the 3 cross-vehicle pairings are NOT flagged, and the one genuine same-vehicle
# (HUMMERS) pairing IS flagged.
# =====================================================================================================
try:
    winch_rows = [
        _row("electrical", "V", "24 V", doc="983", vehicle="5 TON", tm="TM 9-2320-272-24-4"),
        _row("electrical", "V", "12 V", doc="13781", vehicle="TM,S HUMMERS,ALL", tm="TM 9-2320-387-24-1"),
        _row("electrical", "V", "24 V", doc="14105", vehicle="TM,S HUMMERS,ALL", tm="TM 9-2320-387-24-2"),
        _row("electrical", "V", "6 V", doc="870", vehicle="2.5 Ton Truck", tm="TM 9-2320-361-34"),
    ]
    winch_cs = conflicts.detect(winch_rows)
    ok("winch_exactly_one_conflict_survives_scoping", len(winch_cs) == 1)
    if winch_cs:
        wc = winch_cs[0]
        ok("winch_surviving_conflict_is_hummers_only", wc.get("vehicle") == "TM,S HUMMERS,ALL")
        ok("winch_hummers_min_max", wc.get("min") == 12 and wc.get("max") == 24)
        ok("winch_hummers_n_docs", wc.get("n_docs") == 2)
        cited_docs = {v["doc"] for v in wc.get("values", [])}
        ok("winch_hummers_citations_are_the_two_hummers_docs", cited_docs == {"13781", "14105"})
        ok("winch_5ton_not_cited", "983" not in cited_docs)
        ok("winch_2_5ton_not_cited", "870" not in cited_docs)
except Exception as e:
    failed.append("section5_realistic_winch_installation_scenario(%s)" % e)


# =====================================================================================================
print("\ntest_conflicts: %d passed, %d failed" % (len(passed), len(failed)))
if failed:
    print("FAILED: " + ", ".join(failed))
    sys.exit(1)
print("PASSED: " + ", ".join(passed))
sys.exit(0)
# END OF FILE
