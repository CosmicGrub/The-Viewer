@echo off
setlocal enableextensions
REM ============================================================================================
REM  BUILD-AIRGAP-MANIFEST.bat -- sign a folder of manuals for air-gapped transfer to another unit
REM  (recommendations annex #17: airgap-multiunit). Run this on the SENDING machine, before
REM  copying files to removable media. Prints a signed manifest JSON to the console -- redirect it
REM  to a file and carry both the files and the manifest to the receiving unit.
REM  Read-only over the source folder. Keep CRLF line endings.
REM  Usage:  BUILD-AIRGAP-MANIFEST.bat "D:\path\to\manuals" "shared-secret" > manifest.json
REM ============================================================================================
cd /d "%~dp0engine"
set "PY=python"
where python >nul 2>&1 || set "PY=py"
where %PY% >nul 2>&1 || ( echo [ERROR] Python not on PATH. & pause & exit /b 1 )
set "SRC=%~1"
set "SECRET=%~2"
if "%SRC%"=="" set /p "SRC=Folder of manuals to send: "
if not exist "%SRC%\" ( echo [ERROR] Folder not found: %SRC% & pause & exit /b 2 )
if "%SECRET%"=="" set /p "SECRET=Shared secret (agree on this with the receiving unit beforehand): "
if "%SECRET%"=="" ( echo [ERROR] A shared secret is required. & pause & exit /b 2 )
%PY% -B -c "import airgap,ingestpipe,json,os; folder=r'%SRC%'; found=ingestpipe.scan_folder(folder); rels=[os.path.relpath(f['path'],folder) for f in found]; man=airgap.make_manifest(folder,rels,'%SECRET%'); print(json.dumps(man))"
endlocal
