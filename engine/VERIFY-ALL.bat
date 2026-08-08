@echo off
REM ============================================================
REM  THE VIEWER -- one-command health check (RUN ON WINDOWS).
REM  Runs the regression suites + the safeguard truncation/corruption
REM  verify, and prints a single PASS/FAIL.
REM    VERIFY-ALL.bat            -> run the checks vs the latest snapshot
REM    VERIFY-ALL.bat /snapshot  -> take a fresh snapshot first, then check
REM ============================================================
setlocal
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( echo [ERROR] Python 3 not found on PATH.& pause & goto :eof )
set "ARG="
if /I "%~1"=="/snapshot" set "ARG=--snapshot"
%PY% "%~dp0tests\verify_all.py" %ARG%
pause
endlocal
