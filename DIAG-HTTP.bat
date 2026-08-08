@echo off
setlocal
cd /d "%~dp0engine"
set "PY=python"
where python >nul 2>nul || set "PY=py"
echo Probing the LIVE running server over HTTP (the app must be running)...
echo.
%PY% diag_http.py
echo.
echo Saved to index\diag_http.txt
endlocal
