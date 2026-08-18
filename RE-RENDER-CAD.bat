@echo off
REM Force-re-render the WHOLE CAD library at the current CAD_VERSION (v7: colour+texture on every tier),
REM in PARALLEL across CPU cores. --force clears each tier's old files then renders fresh.
REM If interrupted: resume with RUN-CAD-TIERS.bat (no --force) — it fills only the missing files.
setlocal enabledelayedexpansion
cd /d "%~dp0engine"
echo === Re-rendering ALL CAD tiers at CAD_VERSION 7 (parallel) ===
set "FAILED="
python make_cad.py --force --style v3
if errorlevel 1 set "FAILED=!FAILED! v3"
python make_cad.py --force --style v2
if errorlevel 1 set "FAILED=!FAILED! v2"
python make_cad.py --force --style v1
if errorlevel 1 set "FAILED=!FAILED! v1"
echo.
REM Medium finding #37: this used to print an unconditional success message even if a tier
REM outright failed (make_cad.py's main() returns 1 on a real error -- no errorlevel check
REM existed here before). Keep running all three tiers (each is independent, resumable) rather
REM than aborting mid-run; only the final message is now conditional on what actually happened.
if not defined FAILED (
  echo === All three tiers re-rendered. Spin sheets regenerate on demand. ===
) else (
  echo === FAILED tiers:!FAILED! -- see output above, then re-run RE-RENDER-CAD.bat or RUN-CAD-TIERS.bat to retry ===
)
pause
endlocal
