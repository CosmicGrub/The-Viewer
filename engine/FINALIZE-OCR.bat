@echo off
REM ============================================================
REM  THE VIEWER -- FINALIZE the completed OCR scan into the program.  RUN ON WINDOWS.
REM  The OCR text has been wiring itself in as it finished (search, find-in-manual, collections,
REM  callouts, 3D refs all read the FTS index live). This locks in the now-COMPLETE scan:
REM    1) refresh the structured parts index from the full text
REM    2) optimize the index  (type-ahead vocabulary, planner stats, WAL)
REM    3) milestone backup     (consistent copy of the completed index)
REM    4) OCR completion report
REM    5) most common part nomenclatures
REM    6) health check
REM ============================================================
setlocal
set "DB=%~dp0..\index\viewer.db"
if not exist "%DB%" set "DB=%~dp0..\index\viewer_index.db"
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( echo [ERROR] Python 3 not found on PATH.& pause & goto :eof )

echo ============================================================
echo  THE VIEWER -- finalizing the COMPLETED OCR scan
echo ============================================================

echo.
echo [1/6] Refreshing the structured parts index from the full text...
%PY% "%~dp0viewer_ingest.py" parts --db "%DB%"

echo.
echo [2/6] Optimizing the index (type-ahead vocabulary, planner stats, WAL)...
%PY% "%~dp0optimize_index.py" --db "%DB%"

echo.
echo [3/6] Milestone backup (consistent copy of the completed index)...
%PY% "%~dp0safeguard.py" snapshot --with-db --label post-ocr-complete

echo.
echo [4/6] OCR completion report...
%PY% "%~dp0ocr_report.py" --full --db "%DB%"

echo.
echo [5/6] Most common part nomenclatures...
%PY% "%~dp0top_nomenclature.py" --db "%DB%" --n 30

echo.
echo [6/6] Health check...
%PY% "%~dp0tests\verify_all.py"

echo.
echo ============================================================
echo  DONE -- the complete scan is wired in: search, find-in-manual,
echo  Smart Collections, page/schematic callouts, 3D references,
echo  the structured parts index, and fast predictive type-ahead
echo  now all cover the ENTIRE corpus.
echo  Tip: also run  BACKUP-OFFDISK.bat E:\some-backup-folder  to copy the milestone backup off-disk.
echo ============================================================
pause
endlocal
