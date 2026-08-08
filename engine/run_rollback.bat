@echo off
REM ============================================================
REM  THE VIEWER -- roll back the FLIS enrichment + structured parts (R1, backwards-compatible).
REM  Default = DRY RUN (shows what would be removed, changes nothing).
REM  To actually roll back:   run_rollback.bat /yes
REM  This removes the external reference tables (ref_nsn / ref_nsn_log / ref_hardware) and the
REM  extracted parts; it does NOT touch your manuals, pages, or OCR'd text. Search/sheet return to
REM  their pre-enrichment behavior. Re-running the enrichment restores everything.
REM ============================================================
setlocal
set "VIEWER_DB=%~dp0..\index\viewer.db"
if not exist "%VIEWER_DB%" set "VIEWER_DB=%~dp0..\index\viewer_index.db"
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( echo [ERROR] Python 3 not found on PATH.& pause & goto :eof )
set "FLAG="
if /I "%~1"=="/yes" set "FLAG=--yes"
if /I "%~1"=="--yes" set "FLAG=--yes"
if "%FLAG%"=="" echo (DRY RUN -- nothing will change. Pass /yes to actually roll back.)
%PY% "%~dp0viewer_ingest.py" rollback --db "%VIEWER_DB%" %FLAG%
pause
endlocal
