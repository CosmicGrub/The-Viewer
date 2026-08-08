@echo off
REM ============================================================
REM  THE VIEWER -- install the 3-D / part-imagery prerequisites.
REM  The 3-D viewer itself needs NOTHING (it's browser WebGL).
REM  These are for the imagery pipeline: figure/breakdown crops
REM  and scanned-page tightening. Safe to re-run (idempotent).
REM ============================================================
setlocal
cd /d "%~dp0engine"

set "PY=python"
where python >nul 2>nul || set "PY=py"
%PY% --version >nul 2>nul || (
  echo [ERROR] Python was not found on PATH.
  echo Install Python 3 from https://www.python.org/downloads/ ^(tick "Add to PATH"^), then re-run this.
  pause & exit /b 1
)

echo Using Python:
%PY% --version
echo.
echo Installing: PyMuPDF, Pillow, numpy, pytesseract  (from PyPI)...
echo.
%PY% -m pip install --upgrade pip
%PY% -m pip install pymupdf pillow numpy pytesseract
echo.
echo ----- Verifying -----
%PY% verify_3d_deps.py
set RC=%ERRORLEVEL%
echo.

where tesseract >nul 2>nul
if errorlevel 1 (
  echo NOTE: Tesseract OCR engine is OPTIONAL ^(used only for the precise caption/callout crop^).
  echo   Without it, the density fallback still tightens scanned crops.
  echo   To add it, install the Windows build from:
  echo       https://github.com/UB-Mannheim/tesseract/wiki
  echo   then re-run this script.
)

echo.
if "%RC%"=="0" (
  echo DONE: required prerequisites are installed. Figure/breakdown crops will work.
  echo Next: run BUILD-RPSTL.bat then EXTRACT-FIGURES.bat to warm the imagery.
) else (
  echo Some REQUIRED packages are still missing -- see the lines marked MISS* above.
)
echo.
pause
endlocal
