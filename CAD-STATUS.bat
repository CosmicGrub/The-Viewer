@echo off
setlocal
cd /d "%~dp0engine"
set "PY=python"
where python >nul 2>nul || set "PY=py"
%PY% cad_status.py
echo.
pause
endlocal
