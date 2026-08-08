@echo off
REM ============================================================
REM  THE VIEWER -- OCR pass for scanned pages (RapidOCR, no admin)
REM  Run AFTER the text-first crawl. Reads every queued scanned page and
REM  writes recovered text into the index. Resumable: stop and re-run anytime.
REM  Shows LIVE progress (done / failed counts) as it works.
REM ============================================================
setlocal

set "VIEWER_DB=%~dp0..\index\viewer.db"
if not exist "%VIEWER_DB%" set "VIEWER_DB=%~dp0..\index\viewer_index.db"

set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( echo [ERROR] Python 3 not found on PATH.& goto :end )

REM (skipped unconditional 'pip install --upgrade pip' -- hangs retrying when offline; installs below are import-guarded)

echo Ensuring OCR packages (PyMuPDF + RapidOCR)...
%PY% -c "import fitz" 2>nul || %PY% -m pip install --user pymupdf
%PY% -c "import rapidocr_onnxruntime" 2>nul || %PY% -m pip install --user rapidocr-onnxruntime

echo.
echo Cleanup: drop dead rows and requeue any previously-failed pages...
%PY% "%~dp0viewer_ingest.py" cleanup --db "%VIEWER_DB%"

echo.
echo OCR pass (RapidOCR, multi-threaded, LIVE). Slow but fully resumable.
echo (You will see "ocr: done=N failed=N" tick up as pages are read.)
echo.
%PY% "%~dp0viewer_ingest.py" ocrall --limit 200 --workers 4 --db "%VIEWER_DB%"

echo.
echo OCR COMPLETE. Index status:
%PY% "%~dp0viewer_ingest.py" status --db "%VIEWER_DB%"

:end
echo.
pause
endlocal
