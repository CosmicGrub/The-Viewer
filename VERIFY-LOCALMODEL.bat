@echo off
cd /d "%~dp0engine"
echo === Syntax-check modules ===
python -c "import ast; ast.parse(open('localmodel.py',encoding='utf-8').read()); print('localmodel.py OK')"
python -c "import ast; ast.parse(open('viewer_app.py',encoding='utf-8').read()); print('viewer_app.py OK')"
python verify_ui.py
echo.
echo === Parse OBJ + ASCII STL + binary STL through localmodel ===
python verify_localmodel.py
echo.
pause
