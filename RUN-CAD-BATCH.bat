@echo off
setlocal
echo === Stopping any running CAD batch (make_cad.py) ===
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'make_cad\.py' } | ForEach-Object { Write-Host ('  stopping PID ' + $_.ProcessId); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 2 /nobreak >nul
echo === Removing orphaned older-version renders (kept only the current version) ===
del /q "%~dp0index\cadcache\*_v1.png" 2>nul
del /q "%~dp0index\cadcache\*_v2.png" 2>nul
echo === Starting a fresh TEXTURED (v3) render of the whole representative set ===
echo (Resumable. Ctrl+C to stop. Leave it running.)
echo.
cd /d "%~dp0engine"
set "PY=python"
where python >nul 2>nul || set "PY=py"
%PY% -c "import PIL,numpy" 2>nul || %PY% -m pip install pillow numpy
%PY% make_cad.py
echo.
pause
endlocal
