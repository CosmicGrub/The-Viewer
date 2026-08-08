@echo off
setlocal enableextensions
REM ============================================================================================
REM  BULK-INGEST.bat -- add a whole FOLDER of manuals to THE VIEWER at once (brief-req E).
REM  Scans a folder, plans new vs already-in-corpus, and prints the plan. Then run your normal
REM  ingest/OCR step on the 'new' files. Read-only over the source folder. Keep CRLF line endings.
REM  Usage:  BULK-INGEST.bat "D:\path\to\manuals"
REM ============================================================================================
cd /d "%~dp0engine"
set "PY=python"
where python >nul 2>&1 || set "PY=py"
where %PY% >nul 2>&1 || ( echo [ERROR] Python not on PATH. & pause & exit /b 1 )
set "SRC=%~1"
if "%SRC%"=="" set /p "SRC=Folder of manuals to scan: "
if not exist "%SRC%\" ( echo [ERROR] Folder not found: %SRC% & pause & exit /b 2 )
echo Scanning %SRC% ...
%PY% -B -c "import ingestpipe,sys; f=ingestpipe.scan_folder(r'%SRC%'); p=ingestpipe.plan(f); print('found',len(f),'supported files'); print('NEW:',p['counts']['new'],'(',p['new_mb'],'MB)   DUPLICATE:',p['counts']['duplicate']); [print('  +',x['name']) for x in p['new'][:50]]"
echo.
echo Next: run your ingest/OCR step (e.g. RESUME-OCR.bat / the /ingest page) to process the NEW files.
echo.
pause
