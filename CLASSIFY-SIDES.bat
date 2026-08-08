@echo off
REM ============================================================
REM  THE VIEWER -- sort EVERY document into its side of the house
REM  (operator/10 vs mechanic/20). Reads the live index on THIS
REM  PC, prints the split, writes index\sides.json, opens it.
REM ============================================================
setlocal
cd /d "%~dp0engine"
set "PY=python"
where python >nul 2>nul || set "PY=py"

echo Sorting documents by side of the house (operator vs mechanic)...
echo.
%PY% classify_sides.py
echo.
if exist "..\index\sides.json" (
  echo Wrote index\sides.json -- opening it.
  start "" notepad "..\index\sides.json"
)
echo Done. Copy the count lines back to Claude if you'd like them reviewed.
pause
endlocal
