@echo off
REM Force-re-render the WHOLE CAD library at the current CAD_VERSION (v7: colour+texture on every tier),
REM in PARALLEL across CPU cores. --force clears each tier's old files then renders fresh.
REM If interrupted: resume with RUN-CAD-TIERS.bat (no --force) — it fills only the missing files.
cd /d "%~dp0engine"
echo === Re-rendering ALL CAD tiers at CAD_VERSION 7 (parallel) ===
python make_cad.py --force --style v3
python make_cad.py --force --style v2
python make_cad.py --force --style v1
echo.
echo === All three tiers re-rendered. Spin sheets regenerate on demand. ===
pause
