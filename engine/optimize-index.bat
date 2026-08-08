@echo off
REM ============================================================
REM  THE VIEWER -- one-time index optimizer (run when OCR is PAUSED).
REM  Adds the missing indexes + ANALYZE so Look-Alike / Find-in-manual /
REM  procedure / torque lookups are fast. Idempotent; safe to re-run.
REM ============================================================
cd /d "%~dp0"
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( echo [ERROR] Python 3 not found on PATH. & pause & goto :eof )
%PY% "%~dp0optimize_index.py"
echo.
pause
