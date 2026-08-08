@echo off
setlocal
echo === Stopping ALL stale VIEWER servers (only viewer_app.py / run_app.bat; OCR untouched) ===
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'viewer_app\.py' -or $_.CommandLine -match 'run_app\.bat' } | ForEach-Object { Write-Host ('  killing PID ' + $_.ProcessId + '  ' + $_.Name); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
echo Waiting for sockets to release...
timeout /t 3 /nobreak >nul
echo.
echo === Port 8765 should now be empty (no LISTENING lines below) ===
netstat -ano | findstr :8765
echo.
echo === Starting ONE fresh server ===
start "THE VIEWER" cmd /k "cd /d "%~dp0engine" ^&^& python viewer_app.py --db "%~dp0index\viewer.db" --port 8765"
echo Launched. Give it ~10 seconds to prime, then hard-reload the 3-D page.
timeout /t 2 /nobreak >nul
endlocal
