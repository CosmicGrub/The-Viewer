#!/usr/bin/env python3
"""THE VIEWER — one-command health check.  RUN THIS ON WINDOWS (the host), where the files are
coherent — NOT inside a sandbox whose mount can serve a truncated view.

It runs the regression suites + the safeguard's truncation/corruption verify and prints a single
consolidated PASS/FAIL, so after any change you have one button that says "everything is intact."

  py engine\\tests\\verify_all.py             # run the suites + verify vs the latest snapshot
  py engine\\tests\\verify_all.py --snapshot  # take a fresh safeguard snapshot first, then verify

Exit code 0 = all green; non-zero = something failed (see the FAILED list)."""
import os, sys, subprocess, time

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
PY = sys.executable or "python"

def _run(label, args, timeout=900):
    t = time.time()
    try:
        r = subprocess.run([PY] + args, cwd=ENGINE, capture_output=True, text=True, timeout=timeout)
        ok = (r.returncode == 0)
        out = (r.stdout or "").strip().splitlines()
        tail = "\n   ".join(out[-3:]) if out else ""
        print(("PASS " if ok else "FAIL ") + label + ("  (%.1fs)" % (time.time() - t)))
        if tail: print("   " + tail)
        if not ok:
            err = (r.stderr or "").strip().splitlines()
            if err: print("   stderr: " + err[-1])
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
    for fn in ("test_pillars.py", "test_features.py", "test_patterns.py", "test_routes.py", "test_truncation.py", "test_hardening.py", "test_search_quality.py", "rps_lint.py"):
        p = os.path.join(HERE, fn)
        if os.path.exists(p):
            results.append((fn, _run(fn, [p])))
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
