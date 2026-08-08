@echo off
REM Proves the RUN-VIEWER launch path works: boot the server (thin shell + features/) on a THROWAWAY
REM port 8799 (leaves any live 8765 alone), hit /healthz + /api/status, then stop it.
cd /d "%~dp0"
set "LOG=docs\run_viewer_check.log"
> "%LOG%" echo === RUN-VIEWER launch check  %DATE% %TIME% ===
>> "%LOG%" echo (starting engine\viewer_app.py on throwaway port 8799)

start "VIEWER_CHECK_8799" /min cmd /c "cd /d "%~dp0engine" ^&^& python viewer_app.py --db "%~dp0index\viewer.db" --port 8799 >> "%~dp0%LOG%" 2>&1"
powershell -NoProfile -Command "Start-Sleep -Seconds 9"
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8799/healthz' -TimeoutSec 10; 'HEALTHZ  HTTP ' + $r.StatusCode } catch { 'HEALTHZ  FAILED: ' + $_.Exception.Message }" >> "%LOG%" 2>&1
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8799/api/status' -TimeoutSec 10; 'STATUS   HTTP ' + $r.StatusCode } catch { 'STATUS   FAILED: ' + $_.Exception.Message }" >> "%LOG%" 2>&1
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8799/3d' -TimeoutSec 10; '3D-PAGE  HTTP ' + $r.StatusCode } catch { '3D-PAGE  FAILED: ' + $_.Exception.Message }" >> "%LOG%" 2>&1
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'viewer_app\.py' -and $_.CommandLine -match '8799' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
>> "%LOG%" echo === done (throwaway server stopped) ===
type "%LOG%"
