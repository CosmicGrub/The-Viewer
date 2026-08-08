@echo off
REM ============================================================
REM  THE VIEWER -- OFF-DISK backup. Copies the safeguard vault to a SECOND location (USB / external /
REM  network share) and verifies every file by SHA-256, so one disk failure can't lose both the data
REM  and its backups. Run after a snapshot (run_safeguard.bat snapshot).
REM    BACKUP-OFFDISK.bat E:\viewer-backups         mirror the LATEST snapshot there
REM    BACKUP-OFFDISK.bat E:\viewer-backups /all     mirror ALL snapshots
REM ============================================================
setlocal
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( echo [ERROR] Python 3 not found on PATH.& pause & goto :eof )
set "DEST=%~1"
if "%DEST%"=="" ( echo Usage: BACKUP-OFFDISK.bat ^<destination folder^> [/all]   e.g.  BACKUP-OFFDISK.bat E:\viewer-backups & pause & goto :eof )
set "ALL="
if /I "%~2"=="/all" set "ALL=--all"
%PY% "%~dp0safeguard.py" mirror --to "%DEST%" %ALL%
pause
endlocal
