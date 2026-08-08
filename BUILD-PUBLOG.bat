@echo off
setlocal enableextensions
REM ============================================================================================
REM  BUILD-PUBLOG.bat -- HOST-SIDE: index the DLA PUBLOG / FLIS CSV export into index\publog.db
REM  (authoritative offline federal-catalog part data: nomenclature, part numbers + CAGE,
REM  characteristics, weight/cube, cancelled/replaced NIIN). Read-only over the CSVs and the corpus.
REM  Big job (~17M NSNs) -> takes a few minutes and produces a multi-GB db. Safe to re-run (rebuilds).
REM  NOTE: keep Windows (CRLF) line endings.
REM ============================================================================================
cd /d "%~dp0engine"

set "PY=python"
where python >nul 2>&1 || set "PY=py"
where %PY% >nul 2>&1 || (
  echo [ERROR] Python was not found on PATH. Install it, then re-run.
  pause & exit /b 1
)

REM  Default PUBLOG source folder. Override by passing a path:  BUILD-PUBLOG.bat "D:\path\to\publog"
set "SRC=%~1"
if "%SRC%"=="" set "SRC=C:\Users\User\Desktop\publog"
if not exist "%SRC%\" (
  echo [ERROR] PUBLOG source folder not found: %SRC%
  echo         Pass the folder that holds P_FLIS_NSN.CSV etc:  BUILD-PUBLOG.bat "D:\path\to\publog"
  pause & exit /b 2
)

echo Building PUBLOG sidecar from: %SRC%
echo (this can take several minutes and will write a multi-GB index\publog.db)
echo.
%PY% -B build_publog.py "%SRC%"
if errorlevel 1 (
  echo.
  echo [ERROR] Build failed. See the message above.
  pause & exit /b 1
)
echo.
echo Done. The app now serves /publog and the PUBLOG card on /dossier.
echo Tip: run a quick test build first with:  %PY% build_publog.py "%SRC%" --sample 20000
echo.
pause
