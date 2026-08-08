@echo off
cd /d "%~dp0engine"
echo === Rendering the 5-part x 3-tier CAD comparison page ===
python make_tier_compare.py
echo.
echo Output: docs\cad_tier_comparison.png
pause
