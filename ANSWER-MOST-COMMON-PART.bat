@echo off
REM ============================================================
REM  THE VIEWER -- which part nomenclature comes up THE MOST?
REM  Double-click this. It reads the live index on THIS PC
REM  (the sandbox can't), prints the answer, saves it to
REM  index\MOST-COMMON-PART.txt, and opens it.
REM ============================================================
setlocal
cd /d "%~dp0"

set "PY=python"
where python >nul 2>nul || set "PY=py"

echo.
echo  Counting part nomenclatures across the whole corpus...
echo  (this reads index\viewer.db -- give it a moment on a big index)
echo.

%PY% "engine\top_nomenclature.py" --n 40 --flis
set RC=%ERRORLEVEL%

echo.
if exist "index\MOST-COMMON-PART.txt" (
  echo  Saved: index\MOST-COMMON-PART.txt  -- opening it now.
  start "" notepad "index\MOST-COMMON-PART.txt"
) else (
  echo  [No output file was written -- see any error above.]
)

echo.
echo  Done (exit code %RC%). Copy the line that starts with ">>> ANSWER" back to Claude.
echo.
pause
endlocal
