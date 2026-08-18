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
REM Medium finding #38: this used to kill WHATEVER PID netstat found listening on 8765 with no
REM check that it was actually THE VIEWER -- under an ELEVATED context that's the highest-risk
REM version of the blind-port-kill problem (an admin-privileged kill of an unrelated process
REM reusing that port). Filtered by command line instead, same safe pattern RESTART-CLEAN.bat
REM already uses (only viewer_app.py / run_app.bat processes are killed); Stop-Process still
REM works on the elevated zombie from this elevated context.
echo === [admin] killing THE VIEWER server processes (command-line filtered) === > "%LOG%"
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'viewer_app\.py' -or $_.CommandLine -match 'run_app\.bat' } | ForEach-Object { Write-Output ('  killing PID ' + $_.ProcessId + '  ' + $_.Name); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >> "%LOG%"
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
