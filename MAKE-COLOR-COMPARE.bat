@echo off
cd /d "%~dp0engine"
echo === Syntax-check cad_render ===
python -c "import ast; ast.parse(open('cad_render.py',encoding='utf-8').read()); print('cad_render.py OK')"
echo.
echo === Preserve the previous (grey v1/v2) tier comparison as the BEFORE ===
if exist "..\docs\cad_tier_comparison.png" copy /Y "..\docs\cad_tier_comparison.png" "..\docs\cad_tier_comparison_grey_before.png" >nul
echo.
echo === Render the before/after colour page + refresh the all-colour tier comparison ===
python make_color_compare.py
python make_tier_compare.py
echo.
echo Outputs: docs\cad_color_texture_before_after.png  +  docs\cad_tier_comparison.png (colour + texture)
pause
