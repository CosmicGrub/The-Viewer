@echo off
setlocal
cd /d "%~dp0engine"
set "PY=python"
where python >nul 2>nul || set "PY=py"
echo Analyzing 3-D shape coverage against your live index...
echo.
%PY% analyze_shapes.py
echo.
echo Saved to index\shape_analysis.txt
endlocal
