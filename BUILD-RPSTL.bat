@echo off
REM ============================================================
REM  THE VIEWER -- build the part-number correlation sidecar.
REM  Parses the RPSTL parts-list rows (part# -> item -> NSN ->
REM  nomenclature -> figure) and validates names against PUB
REM  LOG/FLIS. Read-only on the index; writes index\rpstl.db.
REM ============================================================
setlocal
cd /d "%~dp0engine"
set "PY=python"
where python >nul 2>nul || set "PY=py"

echo Building the part-number -> figure correlation sidecar...
echo (reads the OCR'd parts pages; validates nomenclature against FLIS)
echo.
%PY% build_rpstl.py
echo.
echo Done. Part-number lookup is now live: search a part number, or use the Part# box.
echo Low-confidence rows can be corrected in the app's Review panel.
pause
endlocal
