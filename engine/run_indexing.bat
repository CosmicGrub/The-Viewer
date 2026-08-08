@echo off
REM ============================================================
REM  THE VIEWER -- full indexing launcher (Windows)
REM  Text-first crawl of the whole corpus, then OCR (if Tesseract present).
REM  Resumable: stop anytime (Ctrl+C) and re-run -- it continues where it left off.
REM
REM  Only hard requirement: Python 3. PyMuPDF is installed automatically below.
REM  Tesseract is OPTIONAL and only used for the scanned-page OCR pass.
REM ============================================================
setlocal

REM --- EDIT THESE TWO PATHS IF NEEDED ---------------------------------
set "VIEWER_ROOT=E:\ALL MILITARY TMS"
set "VIEWER_DB=%~dp0..\index\viewer.db"
REM -------------------------------------------------------------------

REM Find Python: prefer the 'py' launcher, then 'python'
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY (
  echo [ERROR] Python 3 not found on PATH. Open "Python 3.11" once or reinstall with "Add to PATH", then re-run.
  goto :end
)

echo.
echo THE VIEWER -- full indexing
echo   python : %PY%
echo   corpus : %VIEWER_ROOT%
echo   index  : %VIEWER_DB%
echo.

REM (skipped unconditional 'pip install --upgrade pip' -- hangs retrying when offline; installs below are import-guarded)

echo Ensuring Python packages (PyMuPDF, reportlab)...
%PY% -c "import fitz" 2>nul || %PY% -m pip install --user pymupdf
%PY% -c "import reportlab" 2>nul || %PY% -m pip install --user reportlab

echo.
echo Step 1/2 : text-first crawl of the entire corpus (fast, resumable)
%PY% "%~dp0viewer_ingest.py" crawl --root "%VIEWER_ROOT%" --db "%VIEWER_DB%"

echo.
where tesseract >nul 2>nul
if errorlevel 1 (
  echo Step 2/2 : OCR SKIPPED -- Tesseract not installed.
  echo            Scanned pages are queued; install Tesseract-OCR later and re-run to fill them in.
) else (
  echo Step 2/2 : OCR the scanned pages ^(resumable^)
  :ocrloop
  %PY% "%~dp0viewer_ingest.py" ocr --limit 500 --db "%VIEWER_DB%" > "%TEMP%\viewer_ocr_last.txt"
  type "%TEMP%\viewer_ocr_last.txt"
  findstr /C:"remaining_pending=0" "%TEMP%\viewer_ocr_last.txt" >nul || goto ocrloop
)

echo.
echo DONE. Current index status:
%PY% "%~dp0viewer_ingest.py" status --db "%VIEWER_DB%"

:end
echo.
pause
endlocal
