#!/usr/bin/env python3
"""THE VIEWER — one-command health check.  RUN THIS ON WINDOWS (the host), where the files are
coherent — NOT inside a sandbox whose mount can serve a truncated view.

It runs the regression suites + the safeguard's truncation/corruption verify and prints a single
consolidated PASS/FAIL, so after any change you have one button that says "everything is intact."

  py engine\\tests\\verify_all.py             # run the suites + verify vs the latest snapshot
  py engine\\tests\\verify_all.py --snapshot  # take a fresh safeguard snapshot first, then verify

Exit code 0 = all green; non-zero = something failed (see the FAILED list)."""
import glob, os, sys, subprocess, time

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
PY = sys.executable or "python"

def _run(label, args, timeout=900):
    t = time.time()
    try:
        r = subprocess.run([PY] + args, cwd=ENGINE, capture_output=True, text=True, timeout=timeout)
        ok = (r.returncode == 0)
        out = (r.stdout or "").strip().splitlines()
        print(("PASS " if ok else "FAIL ") + label + ("  (%.1fs)" % (time.time() - t)))
        if ok:
            # Compact on success -- a passing suite's individual checks aren't interesting, just
            # its closing summary line(s).
            tail = "\n   ".join(out[-3:]) if out else ""
            if tail: print("   " + tail)
        else:
            # Full output on failure. This used to be the same last-3-lines tail as the success
            # case, which is exactly wrong: verify_all's own per-suite FAIL/PASS check() lines
            # (which name the specific thing that broke) sort BEFORE the suite's closing
            # "N passed, M failed" line, so they fell outside that window and were silently
            # discarded -- never written anywhere, not just unprinted. Confirmed live: a CI run
            # that failed 5 checks in test_ingest_routes.py surfaced only "170 passed, 5 failed"
            # in the log, with no way to tell which 5 without reproducing locally. Print
            # everything a failing suite said; a few dozen extra lines in CI output is cheap next
            # to a failure nobody can diagnose from the log.
            if out: print("   " + "\n   ".join(out))
            err = (r.stderr or "").strip().splitlines()
            if err: print("   stderr: " + "\n   stderr: ".join(err))
        return ok
    except Exception as e:
        print("FAIL  " + label + "  -> " + str(e))
        return False

def main():
    take_snap = "--snapshot" in sys.argv
    print("THE VIEWER -- verify_all  (host-side health check)")
    print("=" * 56)
    results = []
    if take_snap:
        results.append(("safeguard snapshot",
                        _run("safeguard snapshot", [os.path.join(ENGINE, "safeguard.py"), "snapshot", "--label", "verify_all"])))
    # regression suites (import viewer_app directly -> a passing run proves the module compiles whole)
    # v0.96.0 (backlog K71/K73/K77): rps_lint (the ES5/legacy gate) + test_hardening (B/J defenses)
    # run with every verify.
    #
    # Auto-discovered (glob), NOT a hand-maintained list of names: this used to be a hardcoded
    # tuple, and test_procedure.py -- the one suite that would have caught procedure_feature.py's
    # i -= 1 infinite-loop typo -- was simply never added to it, so "the one authoritative gate"
    # never ran it and the bug shipped undetected. Adding that one filename to the same hardcoded
    # tuple would have "fixed" only that one instance of the pattern: at the time of that fix, 9
    # OTHER real test_*.py files in this directory (test_accuracy.py, test_congruency.py,
    # test_extraction.py, test_features_integration.py, test_features_modules.py, test_http.py,
    # test_jobcard.py, test_newmodules.py, test_property_fuzz.py -- ~1,200 lines combined) were
    # ALSO silently never run here, for the identical reason. Every test_*.py file in this
    # directory now runs automatically; a new test file joins the gate the moment it's added, with
    # nothing else to remember. The _run() subprocess timeout (900s per suite) means a hang in any
    # of them (the same failure mode test_procedure.py's bug caused) now fails loudly instead of
    # blocking the gate forever.
    test_files = sorted(
        os.path.basename(p) for p in glob.glob(os.path.join(HERE, "test_*.py"))
    )
    for fn in test_files:
        results.append((fn, _run(fn, [os.path.join(HERE, fn)])))
    rps_lint = os.path.join(HERE, "rps_lint.py")
    if os.path.exists(rps_lint):
        results.append(("rps_lint.py", _run("rps_lint.py", [rps_lint])))
    # safeguard verify: classifies any TRUNCATED / SHRUNK / CORRUPTED / MISSING file vs the last snapshot.
    # (exit 2 if damage found, 1 if no snapshot yet -> both count as not-OK here.)
    results.append(("safeguard verify",
                    _run("safeguard verify", [os.path.join(ENGINE, "safeguard.py"), "verify"])))
    print("=" * 56)
    bad = [n for n, ok in results if not ok]
    print("%d checks  |  %d ok  |  %d FAILED" % (len(results), len(results) - len(bad), len(bad)))
    if bad:
        print("FAILED: " + ", ".join(bad))
        if "safeguard verify" in bad:
            print("  -> if files show TRUNCATED/SHRUNK, restore with:  run_safeguard.bat recover /all")
            print("  -> if this is the first run, baseline first:       py engine\\tests\\verify_all.py --snapshot")
    else:
        print("ALL GREEN -- suites pass and every protected file matches the vault.")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
