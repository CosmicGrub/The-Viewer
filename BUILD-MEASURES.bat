@echo off
REM ============================================================================================
REM  Build the MEASUREMENTS sidecar: every measured quantity (dimensions, clearances, torque,
REM  pressure, capacity, electrical, temperature, flow, weight, angle) pulled from the OCR/text
REM  layer -> index\measures.db. READ-ONLY on viewer.db; append-only sidecar (R1/R6). Resumable.
REM
REM  NOTE: the /measures page ALREADY works without this (on-the-fly FTS). This sidecar just
REM  enables corpus-wide browsing/counts. Best run while OCR is paused. No internet needed.
REM ============================================================================================
cd /d "%~dp0engine"
where py >nul 2>nul && (set "PY=py") || (set "PY=python")
%PY% -c "import re,sqlite3" 2>nul || (echo Python stdlib missing? & pause & exit /b 1)
echo Building measurements sidecar over the corpus (this can take a while)...
%PY% -B build_measures.py
echo.
echo Done. /measures uses live FTS; the sidecar (index\measures.db) powers corpus-wide counts.
pause
