@echo off
REM ============================================================================================
REM  THE VIEWER -- ONE-CLICK: run every host-side VERIFICATION + the quick index build, logging to
REM  docs\run-all.log. The "green-light everything" button. Does NOT start the long jobs
REM  (OCR / embeddings / installer) -- run those separately: RESUME-OCR.bat, BUILD-EMBEDDINGS.bat,
REM  BUILD-INSTALLER.bat.
REM ============================================================================================
setlocal
cd /d "%~dp0"
set "LOG=%~dp0docs\run-all.log"
where py >nul 2>nul && (set "PY=py") || (set "PY=python")
echo === THE VIEWER -- RUN-ALL-VERIFY  %DATE% %TIME% === > "%LOG%"

echo [1/4] VERIFY-099 ...
call "%~dp0VERIFY-099.bat" >> "%LOG%" 2>&1

echo [2/4] HTTP integration/fuzz ...
cd /d "%~dp0engine"
%PY% tests\test_http.py 2000 >> "%LOG%" 2>&1

echo [3/4] Mutation testing [slow; close the window to skip] ...
call "%~dp0RUN-MUTATION.bat" >> "%LOG%" 2>&1

echo [4/4] Build visual-search index [figure crops -> phash.tsv] ...
cd /d "%~dp0engine"
%PY% -c "import phash,os; d=os.path.join('..','index','figcache'); print('visual index hashes:', phash.build_index(d, os.path.join('..','index','phash.tsv')) if os.path.isdir(d) else 0)" >> "%LOG%" 2>&1

echo.
echo ============================================================
echo  Done. Full log: docs\run-all.log
echo  Search it for  FAIL  /  5xx  /  survived  -- paste any hits to Claude.
echo  If it's clean, run  CUT-V1.0.bat  to stamp v1.0.0.
echo ============================================================
echo.
echo --- PASS lines ---
type "%LOG%" | find /I "PASS"
echo --- any FAIL lines ---
type "%LOG%" | find /I "FAIL"
pause
endlocal
