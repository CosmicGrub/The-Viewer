@echo off
setlocal
cd /d "%~dp0engine"
set "PY=python"
where python >nul 2>nul || set "PY=py"
%PY% -c "import PIL,numpy" 2>nul || %PY% -m pip install pillow numpy
echo Rendering the 10-image CAD contact sheet...
%PY% make_contact.py
echo Saved to docs\cad_contact_sheet.png
endlocal
