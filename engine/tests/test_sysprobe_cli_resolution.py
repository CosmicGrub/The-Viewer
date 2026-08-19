#!/usr/bin/env python3
"""THE VIEWER -- coverage for viewer_ingest.py's --workers/--dpi/--gpu sysprobe-aware CLI resolution.

Audit finding: --workers/--dpi/--gpu argparse defaults were hardcoded (os.cpu_count(), 200, False via
a plain store_true) and 100% blind to sysprobe.py's build_profile() -- which already computes a
RAM-headroom-aware, GPU-aware, laptop/battery-aware ocr_workers/ocr_dpi/use_gpu per machine, cached to
index/hardware_profile.json. Fixed by defaulting the three flags to sentinels (None / "auto") and
resolving them AFTER argparse.parse_args(), ONLY for the subcommands that actually run OCR (ocr/
ocrall/run) -- status/search/crawl/etc. never pay the probe cost -- against sysprobe.load_or_build().
Fail-open (same precedent as the existing --adaptive handling): any sysprobe exception, or a profile
missing the keys we need, falls straight back to the exact prior hardcoded defaults. An explicit
--workers/--dpi/--gpu on the command line always wins over the sysprobe-resolved value.

This monkeypatches sysprobe.load_or_build() to return a synthetic profile (never touches the real
machine or writes index/hardware_profile.json) and viewer_ingest.ocr() to a stub that just records the
`workers` value main() called it with, so no real OCR pass runs against the throwaway empty index.
Run:  python tests/test_sysprobe_cli_resolution.py"""
import os, sys, tempfile
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)
import viewer_ingest as VI
import sysprobe

passed, failed = [], []
def ok(name, cond):
    (passed if cond else failed).append(name)


# Synthetic low-RAM/low-core profile, deliberately DIFFERENT from any plausible
# os.cpu_count()/200/False hardcoded default (and from the second profile below) so a test that
# accidentally exercised the OLD hardcoded path (or picked up the wrong profile) shows up as a clear
# mismatch instead of a coincidental match.
FAKE_PROFILE = {"ocr_workers": 2, "ocr_dpi": 130, "use_gpu": True}
# A second profile with use_gpu=False, used by the "bare --gpu wins over profile" scenario so a True
# result there can only have come from the explicit flag, never from the profile.
FAKE_PROFILE_CPU = {"ocr_workers": 3, "ocr_dpi": 150, "use_gpu": False}


def _run_main(argv_tail, profile_or_exc):
    """Runs `viewer_ingest.py <argv_tail> --db <fresh temp db>` via VI.main(), with
    sysprobe.load_or_build() monkeypatched to return profile_or_exc (or raise it, if it's an
    Exception instance) and viewer_ingest.ocr() stubbed to capture the `workers` arg it's called
    with instead of running a real OCR pass (the fresh db has no pending pages anyway -- this also
    avoids requiring a real OCR engine in the test env). Returns (captured_workers_or_None,
    VI.OCR_DPI, VI.USE_CUDA, load_or_build_call_count)."""
    d = tempfile.mkdtemp(prefix="sysprobe_cli_")
    db = os.path.join(d, "viewer.db")
    captured = {}
    def fake_ocr(con, limit, workers=1):
        captured["workers"] = workers
        return 0
    calls = {"n": 0}
    def fake_load_or_build():
        calls["n"] += 1
        if isinstance(profile_or_exc, Exception):
            raise profile_or_exc
        return profile_or_exc
    real_argv, real_ocr = sys.argv, VI.ocr
    try:
        sys.argv = ["viewer_ingest.py"] + list(argv_tail) + ["--db", db]
        VI.ocr = fake_ocr
        with mock.patch.object(sysprobe, "load_or_build", side_effect=fake_load_or_build):
            VI.main()
    finally:
        sys.argv = real_argv
        VI.ocr = real_ocr
    return captured.get("workers"), VI.OCR_DPI, VI.USE_CUDA, calls["n"]


# =====================================================================================================
# No explicit --workers/--dpi/--gpu on an OCR-driving subcommand -> resolved from the (mocked) profile.
# =====================================================================================================
try:
    workers, dpi, gpu, n_calls = _run_main(["ocr"], FAKE_PROFILE)
    ok("auto_workers_from_profile", workers == FAKE_PROFILE["ocr_workers"])
    ok("auto_dpi_from_profile", dpi == FAKE_PROFILE["ocr_dpi"])
    ok("auto_gpu_from_profile", gpu == FAKE_PROFILE["use_gpu"])
    ok("auto_resolution_actually_probed", n_calls >= 1)
except Exception as e:
    failed.append("auto_resolution_from_profile(%s)" % e)


# =====================================================================================================
# Explicit --workers/--dpi/--gpu always win over the profile, even when a profile is available.
# =====================================================================================================
try:
    workers, dpi, gpu, n_calls = _run_main(
        ["ocr", "--workers", "7", "--dpi", "111", "--gpu", "off"], FAKE_PROFILE)
    ok("explicit_workers_wins", workers == 7)
    ok("explicit_dpi_wins", dpi == 111)
    ok("explicit_gpu_off_wins", gpu is False)
    # all three sentinels were filled explicitly -> the probe should never even run (cost avoidance).
    ok("explicit_all_three_skips_probe", n_calls == 0)
except Exception as e:
    failed.append("explicit_flags_win_over_profile(%s)" % e)


# =====================================================================================================
# Mixed: one explicit flag (--workers) alongside two sentinels (--dpi/--gpu absent) -> the explicit one
# wins, the other two still resolve from the profile. Proves resolution is per-flag, not all-or-nothing.
# =====================================================================================================
try:
    workers, dpi, gpu, n_calls = _run_main(["ocr", "--workers", "9"], FAKE_PROFILE)
    ok("partial_explicit_workers_wins", workers == 9)
    ok("partial_sentinel_dpi_from_profile", dpi == FAKE_PROFILE["ocr_dpi"])
    ok("partial_sentinel_gpu_from_profile", gpu == FAKE_PROFILE["use_gpu"])
except Exception as e:
    failed.append("partial_explicit_flags(%s)" % e)


# =====================================================================================================
# Bare --gpu (no value) means "on", matching the old store_true flag's back-compat behavior (e.g.
# run_ocr_gpu.bat's `--gpu`) -- and wins over a profile that says use_gpu=False.
# =====================================================================================================
try:
    workers, dpi, gpu, n_calls = _run_main(["ocr", "--gpu"], FAKE_PROFILE_CPU)
    ok("bare_gpu_flag_means_on", gpu is True)
    ok("bare_gpu_still_resolves_other_sentinels", workers == FAKE_PROFILE_CPU["ocr_workers"]
       and dpi == FAKE_PROFILE_CPU["ocr_dpi"])
except Exception as e:
    failed.append("bare_gpu_flag(%s)" % e)


# =====================================================================================================
# Fail-open: sysprobe.load_or_build() raising falls straight back to today's EXACT prior hardcoded
# defaults (os.cpu_count(), 200, False) -- same precedent as the file's existing --adaptive handling.
# =====================================================================================================
try:
    workers, dpi, gpu, n_calls = _run_main(["ocr"], RuntimeError("sysprobe boom"))
    ok("fail_open_workers_matches_prior_default", workers == max(1, (os.cpu_count() or 2)))
    ok("fail_open_dpi_matches_prior_default", dpi == 200)
    ok("fail_open_gpu_matches_prior_default", gpu is False)
except Exception as e:
    failed.append("fail_open_sysprobe_raises(%s)" % e)


# =====================================================================================================
# A profile missing the keys we need (e.g. a stale/partial index/hardware_profile.json) is treated the
# same as fail-open, per-key -- never a crash from a missing dict key.
# =====================================================================================================
try:
    workers, dpi, gpu, n_calls = _run_main(["ocr"], {})
    ok("empty_profile_workers_falls_back", workers == max(1, (os.cpu_count() or 2)))
    ok("empty_profile_dpi_falls_back", dpi == 200)
    ok("empty_profile_gpu_falls_back", gpu is False)
except Exception as e:
    failed.append("empty_profile_fails_open(%s)" % e)


# =====================================================================================================
# Subcommands that never run OCR (status/search/crawl/prefilter/...) must NEVER pay the sysprobe probe
# cost, even with --workers/--dpi/--gpu left at their sentinels.
# =====================================================================================================
try:
    _, _, _, n_calls = _run_main(["status"], FAKE_PROFILE)
    ok("non_ocr_subcommand_skips_probe", n_calls == 0)
except Exception as e:
    failed.append("non_ocr_subcommand_skips_probe(%s)" % e)


for n in passed: print("PASS", n)
for n in failed: print("FAIL", n)
print("\n%d passed, %d failed (of %d checks for viewer_ingest.py's sysprobe-aware CLI resolution)" %
      (len(passed), len(failed), len(passed) + len(failed)))
sys.exit(1 if failed else 0)

# END OF FILE
