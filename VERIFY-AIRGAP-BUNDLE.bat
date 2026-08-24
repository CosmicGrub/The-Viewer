@echo off
setlocal enableextensions
REM ============================================================================================
REM  VERIFY-AIRGAP-BUNDLE.bat -- verify a signed manifest against files copied off removable media
REM  (recommendations annex #17: airgap-multiunit). Run this on the RECEIVING machine, after
REM  copying the files AND the manifest.json the sender gave you. Fail-closed: prints ACCEPT only
REM  if every file is present, unmodified, and the signature checks out with your shared secret.
REM  Read-only over the destination folder -- never ingests anything itself; run your normal
REM  ingest step afterward once this says ACCEPT.
REM  Usage:  VERIFY-AIRGAP-BUNDLE.bat manifest.json "D:\path\to\received" "shared-secret"
REM ============================================================================================
cd /d "%~dp0engine"
set "PY=python"
where python >nul 2>&1 || set "PY=py"
where %PY% >nul 2>&1 || ( echo [ERROR] Python not on PATH. & pause & exit /b 1 )
set "MANFILE=%~1"
set "DST=%~2"
set "SECRET=%~3"
if "%MANFILE%"=="" set /p "MANFILE=Path to the manifest.json you received: "
if not exist "%MANFILE%" ( echo [ERROR] Manifest file not found: %MANFILE% & pause & exit /b 2 )
if "%DST%"=="" set /p "DST=Folder where you copied the received files: "
if not exist "%DST%\" ( echo [ERROR] Folder not found: %DST% & pause & exit /b 2 )
if "%SECRET%"=="" set /p "SECRET=Shared secret (the same one the sender used): "
if "%SECRET%"=="" ( echo [ERROR] A shared secret is required. & pause & exit /b 2 )
REM utf-8-sig (not utf-8): redirecting BUILD-AIRGAP-MANIFEST.bat's output with PowerShell's ">"
REM writes a UTF-8 BOM by default -- utf-8-sig strips a BOM if present and is a harmless no-op if
REM not, so this reads the manifest correctly regardless of which shell/redirect produced the file.
%PY% -B -c "import airgap,json; man=json.load(open(r'%MANFILE%',encoding='utf-8-sig')); r=airgap.verify(man,r'%DST%','%SECRET%'); print('VERDICT:',r['verdict']); print('signature_valid:',r['signature_valid']); print('missing:',r['missing']); print('tampered:',r['tampered']); raise SystemExit(0 if r['ok'] else 1)"
REM Capture the real verdict's exit code IMMEDIATELY -- the echo/if/pause commands below would
REM otherwise reset %ERRORLEVEL% before we get to report our own exit code, and a caller/script
REM checking THIS .bat's exit code (not just reading its printed text) needs it to be accurate.
set "VERIFY_RC=%ERRORLEVEL%"
if "%VERIFY_RC%"=="0" (
  echo.
  echo [ACCEPT] Every file present and unmodified. Safe to run your normal ingest step on %DST%.
) else (
  echo.
  echo [REJECT] Do not trust this transfer -- see missing/tampered above, or re-check the shared secret.
)
pause
REM endlocal clears variables set in this scope, including VERIFY_RC -- both must happen on ONE
REM line so %VERIFY_RC% is expanded (at parse time, before either command runs) using the value
REM from BEFORE endlocal reverts it, not after.
endlocal & exit /b %VERIFY_RC%
