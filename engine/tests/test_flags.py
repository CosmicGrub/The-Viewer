#!/usr/bin/env python3
"""Unit tests for engine/flags.py -- the central registry for viewer_ingest.py's extraction-pipeline
opt-out toggles (VIEWER_*_SCAN family + VIEWER_OCR_PREPROCESS), added alongside the full-codebase
audit that also wired in RPSTL/pagetrim/keywords. Two things matter here:
  1. scan_toggle() resolves the exact same opt-out semantics every VIEWER_*_SCAN toggle already used
     (unset or anything but "0" -> True; "0" -> False).
  2. The registry is LIVE, not a snapshot -- disabled()/report() must reflect a toggle's CURRENT
     value even if something reassigns the module-level attribute after registration (the whole
     reason attr=/ns= exist; see flags.py's own module docstring for the drift this prevents).
Pure stdlib runner. Uses a private, throwaway registry (not the real one viewer_ingest.py populates
at import) so these checks never depend on import order or interfere with the real 8-toggle set."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import flags as F


def run():
    passed, failed = [], []
    def check(name, cond):
        (passed if cond else failed).append(name)

    # Work against a private registry list so these checks are hermetic -- they must not see (or
    # pollute) the real registry viewer_ingest.py populates when IT gets imported elsewhere in the
    # same test process (verify_all.py runs every test_*.py in one interpreter per file, but other
    # suites in the same run may have already imported viewer_ingest.py first).
    orig_registry = F._REGISTRY
    F._REGISTRY = []
    try:
        fake_ns = {}

        # --- opt-out semantics: unset / "1" / anything-but-"0" -> True; "0" -> False ---
        os.environ.pop("FLAGTEST_A", None)
        v_unset = F.scan_toggle("FLAGTEST_A", "stage_a", "note a", attr="A", ns=fake_ns)
        fake_ns["A"] = v_unset
        check("scan_toggle(): unset env -> True (default on)", v_unset is True)

        os.environ["FLAGTEST_B"] = "0"
        v_off = F.scan_toggle("FLAGTEST_B", "stage_b", "note b", attr="B", ns=fake_ns)
        fake_ns["B"] = v_off
        check("scan_toggle(): env=\"0\" -> False", v_off is False)

        os.environ["FLAGTEST_C"] = "anything-else"
        v_on = F.scan_toggle("FLAGTEST_C", "stage_c", "note c", attr="C", ns=fake_ns)
        fake_ns["C"] = v_on
        check("scan_toggle(): env=<non-\"0\" string> -> True", v_on is True)
        os.environ.pop("FLAGTEST_B", None); os.environ.pop("FLAGTEST_C", None)

        # --- registry bookkeeping ---
        check("all_toggles(): 3 entries registered, in declaration order",
              [t["env"] for t in F.all_toggles()] == ["FLAGTEST_A", "FLAGTEST_B", "FLAGTEST_C"])
        check("disabled(): only the one resolved OFF", [t["env"] for t in F.disabled()] == ["FLAGTEST_B"])
        check("disabled_stage_names(): matches disabled()'s stage label", F.disabled_stage_names() == ["stage_b"])

        # --- THE core guarantee: live, not a snapshot. Flip fake_ns["A"] directly (simulating a
        # test doing `viewer_ingest.RPSTL_SCAN = False`) WITHOUT touching the env var at all. ---
        fake_ns["A"] = False
        check("disabled(): reflects a direct namespace mutation, not just the env var "
              "(the live-lookback guarantee scan_toggle()'s attr=/ns= exist for)",
              "FLAGTEST_A" in [t["env"] for t in F.disabled()])
        check("disabled_stage_names(): the flipped toggle's stage now appears",
              "stage_a" in F.disabled_stage_names())
        fake_ns["A"] = True   # flip back
        check("disabled(): reflects flipping back on, live, same mechanism", "FLAGTEST_A" not in
              [t["env"] for t in F.disabled()])

        # --- fails safe: a broken/missing namespace entry never raises, falls back to the env-var
        # value computed at registration time ---
        os.environ.pop("FLAGTEST_D", None)
        broken_ns = {}   # deliberately never set "D" in here
        F.scan_toggle("FLAGTEST_D", "stage_d", "note d", attr="D", ns=broken_ns)
        try:
            d_disabled = F.disabled_stage_names()
            ok = True
        except Exception:
            ok = False
        check("disabled(): a missing namespace key never raises (fails safe to the env-var default)", ok)
        check("disabled(): the fail-safe default for an unset env var is ON (not in disabled())",
              "stage_d" not in d_disabled)

        # --- report() text sanity ---
        txt = F.report()
        check("report(): mentions every registered env var", all(
            e in txt for e in ("FLAGTEST_A", "FLAGTEST_B", "FLAGTEST_C", "FLAGTEST_D")))
        check("report(): marks the OFF one as OFF", "[OFF] FLAGTEST_B" in txt)
        check("report(): marks an ON one as ON", "[ON ] FLAGTEST_A" in txt)
        check("report(): summary line reflects the live count (3 of 4 on)", "3 of 4 toggles active" in txt)

        # --- empty-registry edge case ---
        F._REGISTRY = []
        empty_txt = F.report()
        check("report(): empty registry doesn't crash, says so plainly", "none registered" in empty_txt)
        check("all_toggles(): empty registry -> empty list", F.all_toggles() == [])
        check("disabled(): empty registry -> empty list", F.disabled() == [])
    finally:
        F._REGISTRY = orig_registry
        for k in ("FLAGTEST_A", "FLAGTEST_B", "FLAGTEST_C", "FLAGTEST_D"):
            os.environ.pop(k, None)

    # --- integration sanity: importing viewer_ingest.py actually registers the real 8 toggles,
    # through the real attr=/ns=globals() call sites, not a hand-rolled fake ---
    import viewer_ingest as VI   # noqa: F401 -- import alone triggers registration (module-level code)
    real = F.all_toggles()
    real_envs = {t["env"] for t in real}
    expected = {"VIEWER_OCR_PREPROCESS", "VIEWER_BARCODE_SCAN", "VIEWER_MEASURES_SCAN",
                "VIEWER_SCHEMATIC_SCAN", "VIEWER_TABLES_SCAN", "VIEWER_RPSTL_SCAN",
                "VIEWER_CAGEC_CORRELATE_SCAN", "VIEWER_PAGETRIM_SCAN", "VIEWER_KEYWORDS_SCAN",
                "VIEWER_OFFICE_SCAN"}
    check("viewer_ingest.py import registers all 10 real extraction toggles", expected <= real_envs)
    # live-lookback against the REAL module, not a fake namespace this time
    orig = VI.RPSTL_SCAN
    try:
        VI.RPSTL_SCAN = False
        check("real module: flags.disabled_stage_names() picks up VI.RPSTL_SCAN=False live",
              "rpstl" in F.disabled_stage_names())
    finally:
        VI.RPSTL_SCAN = orig
    check("real module: restoring RPSTL_SCAN removes it from disabled() again",
          "rpstl" not in F.disabled_stage_names())

    return passed, failed


if __name__ == "__main__":
    p, f = run()
    for n in p: print("PASS", n)
    for n in f: print("FAIL", n)
    print("\n%d passed, %d failed" % (len(p), len(f)))
    sys.exit(1 if f else 0)

# END OF FILE
