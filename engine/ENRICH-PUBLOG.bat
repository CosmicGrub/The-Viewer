@echo off
REM ============================================================
REM  THE VIEWER -- cross-reference your scans against the FULL PUB LOG / FLIS reference set.  RUN ON WINDOWS.
REM  Matches every NSN found in your index against the DLA FLIS tables (in the publog folder) and adds, for
REM  each match: official item name, part numbers, MANUFACTURER (from CAGE), characteristics, colloquial
REM  name, interchangeable NSNs, and supersession -- APPEND-ONLY (R6), fully cited to PUB LOG. Offline.
REM    ENRICH-PUBLOG.bat                        use the default publog folder (Desktop\publog)
REM    ENRICH-PUBLOG.bat "D:\path\to\publog"    use a custom folder
REM  Streaming reader -- the multi-GB tables take a few minutes. Safe to re-run (refreshes; keeps history).
REM ============================================================
setlocal
set "DB=%~dp0..\index\viewer.db"
if not exist "%DB%" set "DB=%~dp0..\index\viewer_index.db"
set "PUBLOG=%~1"
if "%PUBLOG%"=="" set "PUBLOG=%USERPROFILE%\Desktop\publog"
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( echo [ERROR] Python 3 not found on PATH.& pause & goto :eof )
if not exist "%PUBLOG%\V_FLIS_IDENTIFICATION.CSV" (
  echo [ERROR] PUB LOG tables not found in "%PUBLOG%".
  echo         Pass the folder explicitly:  ENRICH-PUBLOG.bat "C:\path\to\publog"
  pause & goto :eof
)

echo Safeguard snapshot before enrichment (restore point; enrich is append-only + rollbackable)...
%PY% "%~dp0safeguard.py" snapshot --label pre-publog 2>nul || echo (snapshot skipped)

echo.
echo Cross-referencing your scans against PUB LOG in:
echo   "%PUBLOG%"
echo (streaming; the large FLIS tables take a few minutes)...
%PY% "%~dp0viewer_ingest.py" enrich --db "%DB%" --publog-dir "%PUBLOG%"

echo.
echo ============================================================
echo  Done. Part dossiers now show, from PUB LOG (offline, cited, append-only):
echo    official item name . part numbers . MANUFACTURER (CAGE) . characteristics
echo    . colloquial name . interchangeable NSNs . supersession.
echo ============================================================
pause
endlocal
