@echo off
setlocal
cd /d "%~dp0engine"
set "PY=python"
where python >nul 2>nul || set "PY=py"
set "PORT=8766"
echo Starting a clean test server on %PORT%...
start "VIEWER ASSET PROBE :8766" cmd /c "%PY% viewer_app.py --db "%~dp0index\viewer.db" --port %PORT%"
timeout /t 12 /nobreak >nul
echo Probing asset endpoint shapes...
%PY% diag_assets.py http://127.0.0.1:%PORT%
for /f "tokens=5" %%P in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do taskkill /F /PID %%P >nul 2>&1
echo Done. See index\diag_assets.txt
endlocal
