@echo off
cd /d "%~dp0engine"
echo === Syntax-checking UI inline scripts (threed.html, schematics.html) ===
python verify_ui.py
echo.
echo (exit code 0 = both pages' inline JS parse clean)
pause
