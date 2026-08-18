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

REM --- EDIT THESE TWO PATHS IF NEEDED (medium finding #34: default corpus path below used to
REM     be the original developer's own E:\ drive -- meaningless on any other machine. Now
REM     project-relative, matching FIRST-RUN.bat's own "corpus" folder convention; either
REM     put/link your corpus there or edit the line below.) ------------------------------
set "VIEWER_ROOT=%~dp0..\corpus"
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
  set "OCR_FAIL_COUNT=0"
  goto :ocrloop
)
goto :ocr_section_done

REM Medium finding #36: this loop used to check ONLY a stdout substring match, never the real
REM ERRORLEVEL -- a persistently crashing OCR pass (corrupt index, missing dependency, etc.) just
REM re-invoked the same failing command forever with no backoff and no cap. Now the real exit code
REM is captured (before `type`/`findstr`, both of which would reset it) and a run of 3 consecutive
REM non-zero exits aborts with a clear message instead of busy-looping.
:ocrloop
%PY% "%~dp0viewer_ingest.py" ocr --limit 500 --db "%VIEWER_DB%" > "%TEMP%\viewer_ocr_last.txt"
set "OCR_RC=%ERRORLEVEL%"
type "%TEMP%\viewer_ocr_last.txt"
if not "%OCR_RC%"=="0" goto :ocr_failed
set "OCR_FAIL_COUNT=0"
findstr /C:"remaining_pending=0" "%TEMP%\viewer_ocr_last.txt" >nul || goto :ocrloop
goto :ocr_section_done
:ocr_failed
set /a OCR_FAIL_COUNT+=1
echo [ERROR] OCR pass exited with code %OCR_RC% ^(failure #%OCR_FAIL_COUNT% of 3^).
if %OCR_FAIL_COUNT% GEQ 3 (
  echo [ABORT] OCR failed 3 times in a row -- stopping to avoid looping forever. Fix the error above, then re-run.
  goto :end
)
goto :ocrloop
:ocr_section_done

echo.
echo DONE. Current index status:
%PY% "%~dp0viewer_ingest.py" status --db "%VIEWER_DB%"

:end
echo.
pause
endlocal
