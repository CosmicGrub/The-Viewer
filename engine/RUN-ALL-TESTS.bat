@echo off
REM ============================================================
REM  THE VIEWER -- run ALL tests (RUN ON WINDOWS, where files are coherent).
REM  1) regression suites + safeguard truncation/integrity verify  (VERIFY-ALL / verify_all.py)
REM  2) RPS (retroactive) lint -- proves the legacy build still runs every ES5-required page
REM  Exit 0 = additives pass AND legacy parity holds.
REM    RUN-ALL-TESTS.bat            run everything vs the latest snapshot
REM    RUN-ALL-TESTS.bat /snapshot  take a fresh snapshot first, then run
REM ============================================================
setlocal
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( echo [ERROR] Python 3 not found on PATH.& pause & goto :eof )
set "ARG="
if /I "%~1"=="/snapshot" set "ARG=--snapshot"
set "RC=0"

echo ============================================================
echo  1/2  Regression suites + truncation/integrity verify
echo ============================================================
%PY% "%~dp0tests\verify_all.py" %ARG%
if errorlevel 1 set "RC=1"

echo.
echo ============================================================
echo  2/2  RPS (retroactive) lint -- does legacy still work?
echo ============================================================
%PY% "%~dp0tests\rps_lint.py"
if errorlevel 1 set "RC=1"

echo.
if "%RC%"=="0" ( echo ALL TESTS GREEN -- additives pass and legacy parity holds. ) else ( echo [FAIL] one or more checks failed -- see above. )
pause
endlocal & exit /b %RC%
