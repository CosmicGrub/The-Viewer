@echo off
REM ============================================================
REM  THE VIEWER -- data safeguard (the treasure vault).
REM  Run this ON WINDOWS (not in any sandbox) so it reads the real, intact files.
REM    run_safeguard.bat snapshot          -> save a versioned copy of every critical file
REM    run_safeguard.bat snapshot /withdb  -> also store a consistent copy of viewer.db (large)
REM    run_safeguard.bat verify            -> check current files vs the latest snapshot
REM    run_safeguard.bat recover /all      -> restore everything from the latest snapshot
REM    run_safeguard.bat list              -> list snapshots in the vault
REM  Snapshots live in  backups\vault\SNAP_<timestamp>\
REM ============================================================
setlocal
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( echo [ERROR] Python 3 not found on PATH.& pause & goto :eof )
set "CMD=%~1"
if "%CMD%"=="" set "CMD=verify"
set "ARG2="
if /I "%~2"=="/withdb" set "ARG2=--with-db"
if /I "%~2"=="/all" set "ARG2=--all"
%PY% "%~dp0safeguard.py" %CMD% %ARG2%
pause
endlocal
