@echo off
setlocal
cd /d "%~dp0engine"
set "PY=python"
where python >nul 2>nul || set "PY=py"
set "PORT=8766"
echo === Starting a CLEAN test server on port %PORT% (does not touch 8765) ===
start "VIEWER E2E TEST :8766" cmd /c "%PY% viewer_app.py --db "%~dp0index\viewer.db" --port %PORT%"
echo Waiting 12s for it to prime...
timeout /t 12 /nobreak >nul
echo.
echo === Running end-to-end smoke test ===
%PY% diag_e2e.py http://127.0.0.1:%PORT%
set "RC=%ERRORLEVEL%"
echo.
echo === Stopping the test server (port %PORT% only) ===
for /f "tokens=5" %%P in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do taskkill /F /PID %%P >nul 2>&1
echo Done. %RC% checks failed. Full report: index\diag_e2e.txt
endlocal
