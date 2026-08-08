@echo off
cd /d "%~dp0engine"
set LOG=..\docs\boost_verify.log
(
echo === Syntax checks ===
python -c "import ast; ast.parse(open('cad_render.py',encoding='utf-8').read()); print('cad_render.py OK')"
python -c "import ast; ast.parse(open('make_cad.py',encoding='utf-8').read()); print('make_cad.py OK')"
python -c "import ast; ast.parse(open('viewer_app.py',encoding='utf-8').read()); print('viewer_app.py OK')"
node --check ui\gl3d.js && echo gl3d.js OK
python verify_ui.py
echo.
echo === Parallel CAD batch benchmark ^(your CPU^) ===
python bench_cad_parallel.py --n 120
) > "%LOG%" 2>&1
echo Done. Wrote %LOG%
