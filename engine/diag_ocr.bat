@echo off
setlocal
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
echo Running OCR diagnostic...
echo.
%PY% "%~dp0ocr_diag.py"
echo.
echo ===== diagnostic complete =====
pause
endlocal
