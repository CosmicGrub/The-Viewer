@echo off
setlocal
echo === Stopping any running CAD batch first ===
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'make_cad\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 2 /nobreak >nul
cd /d "%~dp0engine"
set "PY=python"
where python >nul 2>nul || set "PY=py"
%PY% -c "import PIL,numpy" 2>nul || %PY% -m pip install pillow numpy
echo.
echo === [1/3] Filling any missing MODERN (v3) renders ===
%PY% make_cad.py --style v3
echo.
echo === [2/3] Rendering LITE tier (v2) for the whole set ===
%PY% make_cad.py --style v2
echo.
echo === [3/3] Rendering LEGACY tier (v1) for the whole set ===
%PY% make_cad.py --style v1
echo.
echo === All three tiers rendered. ===
pause
endlocal
