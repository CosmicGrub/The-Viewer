@echo off
setlocal enabledelayedexpansion
set "LOG=%~dp0index\fixport.txt"
echo === Killing EVERY process listening on 8765 (by PID, ignores command line) === > "%LOG%"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr :8765 ^| findstr LISTENING') do (
  echo   taskkill /F /PID %%P >> "%LOG%"
  taskkill /F /PID %%P >> "%LOG%" 2>>&1
)
echo Waiting for sockets to release... >> "%LOG%"
timeout /t 3 /nobreak >nul
echo. >> "%LOG%"
echo === Listeners on 8765 after kill (should be NONE) === >> "%LOG%"
netstat -ano | findstr :8765 | findstr LISTENING >> "%LOG%"
echo (end of listener list) >> "%LOG%"
echo. >> "%LOG%"
echo === Starting ONE fresh server === >> "%LOG%"
start "THE VIEWER" "%~dp0engine\run_app.bat"
echo Started run_app.bat in a new window. >> "%LOG%"
type "%LOG%"
endlocal
