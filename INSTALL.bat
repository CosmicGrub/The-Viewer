@echo off
setlocal enableextensions
REM ============================================================================================
REM  THE VIEWER -- dependency installer.  Double-click this ONCE to install the Python packages
REM  the app needs. Requires an internet connection WHILE THIS RUNS. Safe to re-run.
REM  Core packages must install; "recommended" are best-effort (a failure just self-skips a feature).
REM  After this: run VERIFY-099.bat to check, then RUN-VIEWER.bat to launch.
REM  NOTE: this file must keep Windows (CRLF) line endings.
REM ============================================================================================
cd /d "%~dp0"

set "PY=python"
where python >nul 2>&1 || set "PY=py"
where %PY% >nul 2>&1 || (
  echo [ERROR] Python was not found on PATH. Install Python 3.11 or 3.12 from python.org
  echo         ^(tick "Add Python to PATH" in the installer^), then re-run INSTALL.bat.
  pause
  exit /b 1
)
echo Using Python: %PY%
%PY% --version
echo.

echo Upgrading pip ^(needs internet^)...
%PY% -m pip install --upgrade pip --timeout 30 --retries 2
echo.

echo ============ CORE packages (required) ============
%PY% -m pip install --timeout 90 --retries 2 pymupdf reportlab numpy pillow
if errorlevel 1 (
  echo.
  echo [ERROR] Core packages failed to install. Check your internet connection and try again.
  pause
  exit /b 1
)
echo.

echo ============ RECOMMENDED packages (best-effort) ============
for %%P in (opencv-python pytesseract pdfplumber segno) do (
  echo Installing %%P ...
  %PY% -m pip install --timeout 90 --retries 2 %%P || echo    [skip] %%P not installed ^-- that feature will self-skip
)
echo.

echo ============ OPTIONAL (install by hand only if you need them) ============
echo   GPU OCR for scanned pages : %PY% -m pip install easyocr
echo   Faster OCR (RapidOCR)     : %PY% -m pip install rapidocr-onnxruntime
echo   True semantic search      : %PY% -m pip install sentence-transformers
echo   1-D barcodes / DataMatrix : %PY% -m pip install pyzbar
echo   HTTPS on the LAN (self-signed cert generation) : %PY% -m pip install cryptography
echo.
echo NOTE: pytesseract also needs the Tesseract PROGRAM on PATH ^(separate from the Python package^):
echo   https://github.com/UB-Mannheim/tesseract/wiki  ^(Windows installer^)
echo.
echo ============================================================
echo Done. Next:  VERIFY-099.bat  to check, then  RUN-VIEWER.bat  to launch THE VIEWER.
echo ============================================================
pause
