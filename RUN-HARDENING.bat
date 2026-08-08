@echo off
REM ============================================================================================
REM  THE VIEWER — v1.0 hardening pass (host-side; the sandbox mount truncates the grown modules).
REM  Property-based + large-N fuzz over the pure helpers. Optional Hypothesis for smart shrinking.
REM
REM  Usage:   RUN-HARDENING.bat            (default 40,000 iters/property  ~=160k+ cases)
REM           RUN-HARDENING.bat 200000     (custom iteration count)
REM           RUN-HARDENING.bat --max      (1,000,000 iters/property — the full million+ run)
REM ============================================================================================
cd /d "%~dp0engine"
set "N=%~1"
if "%N%"=="" set "N=40000"

echo.
echo === Optional: install Hypothesis for property shrinking (skips if offline) ===
python -m pip install --quiet hypothesis 2>nul && echo   hypothesis ready || echo   (hypothesis not installed - stdlib fuzz will still run)

echo.
echo === Regression suite (fast, must be green before fuzzing) ===
python tests\test_jobcard.py && echo   [test_jobcard PASS]

echo.
echo === Feature audit (dead-wiring / orphan-page / broken-link) ===
python audit_features.py

echo.
echo === Property / fuzz harness  (N=%N% per property) ===
python tests\test_property_fuzz.py %N% > "..\docs\hardening_report.txt" 2>&1
type "..\docs\hardening_report.txt"

echo.
echo Done. Full report: docs\hardening_report.txt
