@echo off
REM Verify the interactive-CAD turntable host-side (full cad_render.py, no sandbox truncation).
cd /d "%~dp0engine"
echo === Rendering turntable proof (this exercises render_spin + ensure_spin) ===
python verify_cadspin.py
echo.
echo === Syntax-check the edited modules ===
python -c "import ast; ast.parse(open('cad_render.py',encoding='utf-8').read()); print('cad_render.py OK')"
python -c "import ast; ast.parse(open('viewer_app.py',encoding='utf-8').read()); print('viewer_app.py OK')"
echo.
echo Proof image: docs\cadspin_proof.png
pause
