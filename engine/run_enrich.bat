@echo off
REM ============================================================
REM  THE VIEWER -- one-time reference enrichment (PUB LOG / GSA), OFFLINE after.
REM  Usage: drag your exported PUB LOG file (CSV or XLSX) ONTO this .bat,
REM         or run:  run_enrich.bat "C:\path\to\publog_export.csv"
REM  It loads the public-domain hardware reference too, and is append-only (R6).
REM ============================================================
setlocal
set "VIEWER_DB=%~dp0..\index\viewer.db"
if not exist "%VIEWER_DB%" set "VIEWER_DB=%~dp0..\index\viewer_index.db"
set "EXPORT=%~1"

set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( echo [ERROR] Python 3 not found on PATH.& pause & goto :eof )

REM (skipped unconditional 'pip install --upgrade pip' -- hangs retrying when offline; installs below are import-guarded)
echo Ensuring packages (openpyxl for .xlsx)...
%PY% -c "import openpyxl" 2>nul || %PY% -m pip install --user openpyxl

echo Safeguard: snapshot critical files before enrichment (restore point; enrich is also rollbackable)...
%PY% "%~dp0safeguard.py" snapshot --label pre-enrich 2>nul || echo (safeguard snapshot skipped)

if "%EXPORT%"=="" (
  echo.
  echo No export file given -- loading the public-domain hardware reference only.
  echo To fill NSNs, re-run and drag your PUB LOG export ^(CSV/XLSX^) onto this file.
  %PY% "%~dp0viewer_ingest.py" enrich --db "%VIEWER_DB%"
) else (
  echo Enriching from: %EXPORT%
  %PY% "%~dp0viewer_ingest.py" enrich --db "%VIEWER_DB%" --publog "%EXPORT%"
)
echo.
echo Done. The data is now in your OFFLINE index. Nothing else goes online.
pause
endlocal
