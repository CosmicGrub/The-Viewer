@echo off
cd /d "%~dp0engine"
echo === Syntax-check edited modules ===
python -c "import ast; ast.parse(open('cad_render.py',encoding='utf-8').read()); print('cad_render.py OK')"
python verify_ui.py
echo.
echo === Render the CAD quality grid (all tiers) ===
python verify_cadquality.py
echo.
echo Proof image: docs\cad_quality_v5.png
pause
