@echo off
REM ============================================================================================
REM  THE VIEWER -- ONE-CLICK: run every host-side VERIFICATION + the quick index build, logging to
REM  docs\run-all.log. The "green-light everything" button. Does NOT start the long jobs
REM  (OCR / embeddings / installer) -- run those separately: RESUME-OCR.bat, BUILD-EMBEDDINGS.bat,
REM  BUILD-INSTALLER.bat.
REM ============================================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"
set "LOG=%~dp0docs\run-all.log"
where py >nul 2>nul && (set "PY=py") || (set "PY=python")
echo === THE VIEWER -- RUN-ALL-VERIFY  %DATE% %TIME% === > "%LOG%"
set "FAILED="

REM Medium finding #35: this used to report its final result via `type LOG | find /I "PASS"/"FAIL"`
REM -- exactly the keyword-grep-summary pattern VERIFY.bat's own header explicitly rejects ("produced
REM false positives on docstrings and could miss silent skips"). Rebuilt on the same exit-code-truth
REM idiom VERIFY.bat itself uses: every step's real ERRORLEVEL is checked and named on failure.

echo [1/4] VERIFY-099 ...
call "%~dp0VERIFY-099.bat" >> "%LOG%" 2>&1
if errorlevel 1 set "FAILED=!FAILED! VERIFY-099"

echo [2/4] HTTP integration/fuzz ...
cd /d "%~dp0engine"
%PY% tests\test_http.py 2000 >> "%LOG%" 2>&1
if errorlevel 1 set "FAILED=!FAILED! test_http"

echo [3/4] Mutation testing [slow; close the window to skip] ...
call "%~dp0RUN-MUTATION.bat" >> "%LOG%" 2>&1
if errorlevel 1 set "FAILED=!FAILED! mutation"

echo [4/4] Build visual-search index [figure crops -> phash.tsv] ...
cd /d "%~dp0engine"
%PY% -c "import phash,os; d=os.path.join('..','index','figcache'); print('visual index hashes:', phash.build_index(d, os.path.join('..','index','phash.tsv')) if os.path.isdir(d) else 0)" >> "%LOG%" 2>&1
if errorlevel 1 set "FAILED=!FAILED! phash-index"

echo.
echo ============================================================
if not defined FAILED (
  set "RC=0"
  echo   RESULT: ALL GREEN -- every step exited 0.
) else (
  set "RC=1"
  echo   RESULT: the following step^(s^) FAILED ^(full context in %LOG%^):
  for %%F in (!FAILED!) do echo     - %%F
)
echo  Full log: docs\run-all.log
echo  If it's clean, run  CUT-V1.0.bat  to stamp v1.0.0.
echo ============================================================
echo.
pause
REM `endlocal` discards every variable set since `setlocal` above (including FAILED/RC) -- %RC%
REM is expanded to its literal value HERE, before endlocal runs, so the exit code survives the
REM scope pop (the standard batch idiom for returning a real exit code out of a setlocal block).
endlocal & exit /b %RC%
