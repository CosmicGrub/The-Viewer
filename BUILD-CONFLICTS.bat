@echo off
REM ============================================================================================
REM  PRECOMPUTED CONFLICT SWEEP (v1.13.0, roadmap #88-lite): batch-run the cross-manual conflict
REM  checker over the top part subjects -> index\conflicts.db sidecar. /api/conflicts then answers
REM  swept subjects INSTANTLY ("precomputed": true); everything else falls back to the live scan.
REM
REM  READ-ONLY on viewer.db; the sidecar is append-only (R1/R6 - every sweep is a new run_id).
REM  NOTE: best run while OCR is PAUSED - the sweep hammers the same FTS index the OCR writer
REM  feeds. No internet needed. Re-run after big ingests to refresh (entries expire at 45 days).
REM ============================================================================================
cd /d "%~dp0engine"
where py >nul 2>nul && (set "PY=py") || (set "PY=python")
%PY% -c "import re,sqlite3,json" 2>nul || (echo Python stdlib missing? & pause & exit /b 1)
echo Sweeping the top 2000 part subjects for cross-manual conflicts (can take a while)...
%PY% -B build_conflicts.py --limit 2000 --tol 0.05
echo.
echo Done. Swept subjects answer instantly on /api/conflicts and the /part page.
pause
