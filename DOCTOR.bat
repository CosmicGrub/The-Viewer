@echo off
REM THE VIEWER -- one-shot health + inventory report (deps, corpus paths, coverage, caches, disk).
cd /d "%~dp0engine"
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( echo [ERROR] Python 3 not found on PATH.& pause & goto :eof )
%PY% doctor.py %*
echo.
echo Report saved to docs\doctor_report.txt
pause
