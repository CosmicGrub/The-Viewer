@echo off
REM ============================================================================================
REM  THE VIEWER -- first-run setup on a new / shop PC.
REM   * points the app at the corpus + index (edit the two paths below if they differ),
REM   * deletes index\hardware_profile.json so the app RE-TUNES to THIS machine's CPU/GPU,
REM   * launches the app (RUN-VIEWER.bat).
REM  Safe to re-run. Read-only on the corpus (R1).
REM ============================================================================================
setlocal
cd /d "%~dp0"

REM --- edit if your corpus / index live elsewhere on this PC (medium finding #34: the old
REM     default here was the original developer's own E:\ drive -- meaningless on any other
REM     machine. Default is now project-relative: put/link your corpus at a "corpus" folder
REM     next to this script, or edit the line below to point at wherever it actually lives.) ---
set "CORPUS=%~dp0corpus"
set "INDEX=%~dp0index"

echo Corpus : %CORPUS%
echo Index  : %INDEX%
echo.

if not exist "%CORPUS%" (
  echo [warn] Corpus folder not found at "%CORPUS%".
  echo        Copy/junction your TMs there, or edit CORPUS in this file, then re-run.
)
if not exist "%INDEX%\viewer.db" (
  echo [warn] No index found at "%INDEX%\viewer.db" -- copy your index\ folder here first ^(see docs\PORTING.md^).
)

echo Re-tuning to THIS machine ^(removing stale hardware profile^)...
if exist "%INDEX%\hardware_profile.json" del /q "%INDEX%\hardware_profile.json"

echo Running the project doctor ^(deps + corpus-path reachability^)...
where py >nul 2>nul && (set "PY=py") || (set "PY=python")
%PY% "engine\doctor.py" 2>nul || echo (doctor skipped)

echo.
echo Launching THE VIEWER ...
call "RUN-VIEWER.bat"
endlocal
