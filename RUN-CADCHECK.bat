@echo off
setlocal
cd /d "%~dp0engine"
set "PY=python"
where python >nul 2>nul || set "PY=py"
set "PORT=8766"
start "VIEWER CAD CHECK :8766" cmd /c "%PY% viewer_app.py --db "%~dp0index\viewer.db" --port %PORT%"
timeout /t 12 /nobreak >nul
%PY% diag_cad.py http://127.0.0.1:%PORT%
for /f "tokens=5" %%P in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do taskkill /F /PID %%P >nul 2>&1
endlocal
