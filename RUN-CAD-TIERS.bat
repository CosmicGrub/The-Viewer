@echo off
setlocal enabledelayedexpansion
echo === Stopping any running CAD batch first ===
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'make_cad\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 2 /nobreak >nul
cd /d "%~dp0engine"
set "PY=python"
where python >nul 2>nul || set "PY=py"
%PY% -c "import PIL,numpy" 2>nul || %PY% -m pip install pillow numpy
echo.
set "FAILED="
echo === [1/3] Filling any missing MODERN (v3) renders ===
%PY% make_cad.py --style v3
if errorlevel 1 set "FAILED=!FAILED! v3"
echo.
echo === [2/3] Rendering LITE tier (v2) for the whole set ===
%PY% make_cad.py --style v2
if errorlevel 1 set "FAILED=!FAILED! v2"
echo.
echo === [3/3] Rendering LEGACY tier (v1) for the whole set ===
%PY% make_cad.py --style v1
if errorlevel 1 set "FAILED=!FAILED! v1"
echo.
REM Medium finding #37: unconditional success message before, even if a tier actually failed.
if not defined FAILED (
  echo === All three tiers rendered. ===
) else (
  echo === FAILED tiers:!FAILED! -- check output above, then re-run this script to retry the missing ones ===
)
pause
endlocal
