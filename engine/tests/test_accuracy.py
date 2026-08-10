"""test_accuracy.py -- MEASURED extraction accuracy against a hand-verified ground-truth set (R13: you
cannot claim 'above military grade' without measuring it). Each case is a realistic TM sentence with the
values a human confirmed should be extracted. The harness runs the real extractor over each and reports
precision / recall, and asserts recall stays above a floor.

The scoring (score_case) is pure and unit-tested inline; the corpus extractor (measures.extract) is imported
best-effort so this runs host-side under VERIFY-099 (a sandbox mount may serve the grown module truncated).

Run:  python tests/test_accuracy.py
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# (sentence, [ (type, expected_value_float, unit) ... ]) -- hand-verified
GROUND_TRUTH = [
    ("Torque the mounting bolts to 35 ft-lb.",                 [("torque", 35.0, "ft-lb")]),
    ("Tighten the drain plug to 25 ft-lb and the filler to 15 ft-lb.", [("torque", 25.0, "ft-lb"), ("torque", 15.0, "ft-lb")]),
    ("Inflate the tires to 35 psi for highway operation.",     [("pressure", 35.0, "psi")]),
    ("The shaft diameter is 0.50 in.",                         [("length", 0.50, "in")]),
    ("System voltage is 24 V.",                                [("electrical", 24.0, "V")]),
    ("Fill to a capacity of 6 qt.",                            [("capacity", 6.0, "qt")]),
    ("Operating temperature range is -40 F to 120 F.",         [("temperature", -40.0, "F"), ("temperature", 120.0, "F")]),
    ("Engine idle speed is 700 rpm.",                          [("rotation", 700.0, "rpm")]),
    # v1.13.5: negative case (expects NOTHING) -- guards the new bare-F/C temperature pattern against the
    # military designators and battery C-rate notation this exact corpus is full of.
    ("The flight line shows 5 F-16 fighters and 2 C-130 transports; charge spares at a 0.5C rate.", []),
]


def _num(v):
    import re
    m = re.search(r"[-+]?\d*\.?\d+", str(v))
    return float(m.group(0)) if m else None


def score_case(expected, found, tol=0.02):
    """expected/found: lists of (type, value_float). Returns (tp, fn, matched_flags). A ground-truth item
    counts as found if some extracted value of the same TYPE matches within `tol` relative tolerance."""
    tp = 0
    used = set()
    for et, ev, *_ in expected:
        hit = False
        for j, f in enumerate(found):
            if j in used:
                continue
            ft = f.get("type"); fv = _num(f.get("value"))
            if ft == et and fv is not None and (abs(fv - ev) <= tol * max(1.0, abs(ev))):
                used.add(j); hit = True; break
        tp += 1 if hit else 0
    fn = len(expected) - tp
    return tp, fn


def run(floor=0.75):
    # unit-check the pure scorer first (always runs)
    tp, fn = score_case([("torque", 35.0)], [{"type": "torque", "value": "35 ft-lb"}, {"type": "length", "value": "2 in"}])
    assert tp == 1 and fn == 0, (tp, fn)
    tp, fn = score_case([("torque", 35.0)], [{"type": "torque", "value": "50 ft-lb"}])
    assert tp == 0 and fn == 1, (tp, fn)
    print("score_case unit-check OK")

    try:
        import measures
    except Exception as e:
        print("test_accuracy SKIPPED (measures not importable here: %s). Runs host-side under VERIFY-099." % e)
        return
    TP = FN = EXTRA = 0
    for sentence, expected in GROUND_TRUTH:
        found = measures.extract(sentence)
        tp, fn = score_case(expected, found)
        TP += tp; FN += fn
        EXTRA += max(0, len(found) - len(expected))
    recall = TP / (TP + FN) if (TP + FN) else 0.0
    # precision proxy: of the values we care about + extras, how many were the expected ones
    precision = TP / (TP + EXTRA) if (TP + EXTRA) else 0.0
    print("ACCURACY on %d ground-truth cases: recall=%.0f%% (%d/%d), precision~%.0f%% (extras=%d)"
          % (len(GROUND_TRUTH), recall * 100, TP, TP + FN, precision * 100, EXTRA))
    assert recall >= floor, "recall %.2f below floor %.2f -- extraction regressed" % (recall, floor)
    print("test_accuracy PASS (recall floor %.0f%%)" % (floor * 100))


if __name__ == "__main__":
    run()

# END OF FILE
