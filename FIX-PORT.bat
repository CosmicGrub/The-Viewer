@echo off
setlocal enabledelayedexpansion
set "LOG=%~dp0index\fixport.txt"
REM Medium finding #38: this used to kill WHATEVER PID netstat found listening on 8765 with no
REM check that it was actually THE VIEWER -- a blind port-kill risks taking down an unrelated
REM process that happens to be reusing that port. Filtered by command line instead, same safe
REM pattern RESTART-CLEAN.bat already uses (only viewer_app.py / run_app.bat processes are killed).
echo === Killing THE VIEWER server processes (command-line filtered: viewer_app.py / run_app.bat) === > "%LOG%"
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'viewer_app\.py' -or $_.CommandLine -match 'run_app\.bat' } | ForEach-Object { Write-Output ('  killing PID ' + $_.ProcessId + '  ' + $_.Name); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >> "%LOG%"
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
