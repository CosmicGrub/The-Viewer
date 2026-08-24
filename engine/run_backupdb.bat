@echo off
REM ============================================================
REM  THE VIEWER -- full consistent backup of the big index DB (viewer.db).
REM  Recommendations annex #1 (backup-dr): the daily snapshot task protects code/docs/small
REM  sidecars, but NOT viewer.db itself (multi-GB, only --with-db opts a snapshot into copying it).
REM  This is the dedicated full-DB backup path -- run it directly, or let
REM  register_snapshot_task.bat's weekly task run it automatically.
REM  Run this ON WINDOWS (not in any sandbox) so it reads the real, intact file.
REM    run_backupdb.bat            -> backup index\viewer.db to backups\db\, keep newest 2 copies
REM    run_backupdb.bat /auto      -> same, then also prune old snapshots (safeguard.py gc --keep 10)
REM  Backups live in  backups\db\viewer-<timestamp>.db
REM ============================================================
setlocal
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( echo [ERROR] Python 3 not found on PATH.& pause & goto :eof )
set "ARG="
if /I "%~1"=="/auto" set "ARG=--auto"
%PY% "%~dp0safeguard.py" backupdb %ARG%
pause
endlocal
