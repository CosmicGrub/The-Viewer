@echo off
setlocal
cd /d "%~dp0engine"
set "PY=python"
where python >nul 2>nul || set "PY=py"
%PY% -c "import PIL,numpy" 2>nul || %PY% -m pip install pillow numpy
echo Rendering the 50-part v1-vs-v2 CAD comparison sheet...
%PY% make_compare.py
echo Saved to docs\cad_v1_vs_v2.png
endlocal
