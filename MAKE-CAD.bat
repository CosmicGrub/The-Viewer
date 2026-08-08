@echo off
setlocal
cd /d "%~dp0engine"
set "PY=python"
where python >nul 2>nul || set "PY=py"
echo Checking Pillow...
%PY% -c "import PIL" 2>nul
if errorlevel 1 (
  echo Installing Pillow one-time, please wait...
  %PY% -m pip install pillow
)
echo.
echo Rendering CAD images for the whole representative 3-D library into index\cadcache\ ...
echo (Resumable — re-run anytime; it skips parts already rendered. Ctrl+C to stop.)
echo.
%PY% make_cad.py %*
echo.
pause
endlocal
