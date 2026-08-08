@echo off
:: Removes the stuck/elevated VIEWER server that is holding port 8765, then starts ONE clean server.
:: Self-elevates (you'll get a "Do you want to allow..." prompt -> click Yes).
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo Requesting administrator rights to remove the stuck server...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)
set "LOG=%~dp0index\zombie.txt"
echo === [admin] killing EVERY listener on 8765 === > "%LOG%"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr :8765 ^| findstr LISTENING') do (
  echo killing PID %%P >> "%LOG%"
  taskkill /F /PID %%P >> "%LOG%" 2>>&1
)
timeout /t 3 /nobreak >nul
echo. >> "%LOG%"
echo === listeners on 8765 after kill (should be empty) === >> "%LOG%"
netstat -ano | findstr :8765 | findstr LISTENING >> "%LOG%"
echo (end) >> "%LOG%"
echo. >> "%LOG%"
echo === starting ONE fresh NON-elevated server (via explorer so it is killable later) === >> "%LOG%"
explorer "%~dp0engine\run_app.bat"
echo started >> "%LOG%"
echo.
echo Done. A new server window will open. You can close this window.
timeout /t 6 /nobreak >nul
