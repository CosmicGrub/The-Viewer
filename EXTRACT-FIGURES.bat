@echo off
REM ============================================================
REM  THE VIEWER -- pre-extract every part's cited figure crop
REM  into index\figcache\ so 3D previews + the "Manual
REM  illustration" tab are instant. Read-only on the index.
REM ============================================================
setlocal
cd /d "%~dp0engine"
set "PY=python"
where python >nul 2>nul || set "PY=py"

echo Checking PyMuPDF...
%PY% -c "import fitz" 2>nul
if errorlevel 1 (
  echo Installing PyMuPDF one-time, please wait...
  %PY% -m pip install pymupdf
)

echo.
echo Extracting figure crops from the manuals. This can take a while on a big corpus...
echo.
%PY% extract_figures.py --dpi 150

echo.
echo Done. Crops are cached in index\figcache\ and the 3D collection now shows real cited figures.
pause
endlocal
