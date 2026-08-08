@echo off
setlocal
cd /d "%~dp0engine"
set "PY=python"
where python >nul 2>nul || set "PY=py"
echo Probing the figures-first 3-D library on your live data...
echo.
%PY% diag_threed.py
echo.
echo Saved to index\diag_threed.txt
endlocal
