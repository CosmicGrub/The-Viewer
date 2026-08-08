@echo off
setlocal
cd /d "%~dp0engine"
set "PY=python"
where python >nul 2>nul || set "PY=py"
echo Diagnosing the 3-D pipeline on your live data...
echo.
%PY% diag_3d.py
echo.
echo Saved to index\diag_3d.txt . Copy the output above back to Claude.
pause
endlocal
