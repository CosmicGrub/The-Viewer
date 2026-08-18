@echo off
setlocal enableextensions enabledelayedexpansion
REM ============================================================================================
REM  VERIFY.bat -- THE one authoritative verification gate for THE VIEWER (v1.13.0).
REM
REM  It is the UNION of the old VERIFY-099.bat body and engine\tests\verify_all.py, rebuilt on
REM  EXIT-CODE TRUTH: every test/self-test runs on its own line (or its own loop iteration)
REM  followed by an explicit `if errorlevel 1 set FAILED=...` --
REM    * NO &&-chaining (one failure used to silently skip every later test in the chain),
REM    * NO keyword-grep summaries (exit codes are the truth; grepping the log for FAIL words
REM      produced false positives on docstrings and could miss silent skips).
REM
REM  Console-hang lessons inherited from VERIFY-099 (keep them):
REM    * the body runs as a :body subroutine redirected to ONE log (avoids the CMD "( )" bug),
REM    * the summary NEVER `type`s whole logs, and ends with `pause >nul` -- a bare `pause` or a
REM      full-log `type` under console QuickEdit froze the window for hours,
REM    * long-running suites are wrapped in engine\tools\run_timeout.py (hard wall-clock kill),
REM    * this file MUST keep Windows (CRLF) line endings or cmd.exe cannot parse the :labels.
REM
REM  MANUAL, not run here (the index DB is ~3.65GB): full DB backup with rotation --
REM      python engine\safeguard.py backupdb
REM  -> VACUUM INTO backups\db\viewer-YYYYMMDD-HHMM.db, verifies quick_check, keeps the newest 2,
REM     refuses to start unless free disk > 1.3x the DB size. Add --auto to also gc snapshots.
REM
REM  Exit code: 0 only if EVERY step passed; 1 otherwise (each FAILED step listed by name).
REM ============================================================================================
cd /d "%~dp0"
if not exist "engine\" (
  echo [ERROR] Cannot find the "engine" folder next to this script.
  echo         Keep VERIFY.bat in the THE VIEWER project root ^(the folder with engine\ and docs\^).
  echo         Current folder: %CD%
  goto :fail
)
cd /d "%~dp0engine"

set "PY=python"
where python >nul 2>&1 || set "PY=py"
where %PY% >nul 2>&1 || (
  echo [ERROR] Python was not found on PATH.
  echo         Install Python 3 ^(python.org^) or add it to PATH, then re-run this script.
  goto :fail
)

if not exist "..\docs\" mkdir "..\docs" >nul 2>&1
set "LOG=..\docs\verify.log"
del "%LOG%" >nul 2>&1
if exist "%LOG%" (
  echo [NOTE] %LOG% is locked ^(another verify is still running^) -- writing to a separate log.
  set "LOG=..\docs\verify_%RANDOM%.log"
)

set "FAILED="
echo Running the FULL verification gate with "%PY%"... this takes several minutes.
echo Full output is saved to %LOG%
echo.
call :body > "%LOG%" 2>&1

echo ===================== RESULT =====================
if not defined FAILED (
  echo   RESULT: ALL GREEN -- every step exited 0.
) else (
  echo   RESULT: the following step^(s^) FAILED ^(full context in the log^):
  for %%F in (!FAILED!) do echo     - %%F
)
echo.
echo Full log saved to: %LOG%
echo.
echo VERIFY COMPLETE.  Press any key to close this window . . .
pause >nul
if defined FAILED exit /b 1
exit /b 0

:fail
echo.
echo Verification did not run. See the message above.
echo.
pause >nul
exit /b 1

REM ============================================================================================
:body
echo === VERIFY v1.13.0  %DATE% %TIME% ===

echo.
echo --- [gate 0] .bat CRLF line-ending check ^(LF-only bats blink-crash on Windows^) ---
%PY% tools\check_crlf.py
if errorlevel 1 set "FAILED=!FAILED! crlf-check"

echo.
echo --- [gate 1] syntax: shell + features + new modules ---
%PY% -c "import ast,glob; [ast.parse(open(f,encoding='utf-8').read()) for f in ['viewer_app.py','schemreview.py','build_schemgraph.py','vectorize.py','build_vectorize.py','coverage.py','partlocate.py','doctor.py','figuresheet.py','figureparts.py','jobcard.py','audit_features.py','pmcs.py','build_iteration_snapshot.py','analytics.py','xref.py','partspdf.py','phash.py','embed.py','cut_v1.py','measures.py','tables.py','build_measures.py','build_tables.py','enrich.py','build_enrich.py','masterfile.py','build_masterfile.py','units.py','leadingspecs.py','specparse.py','pdfmeta.py','barcodes.py','cautions.py','textquality.py','acronyms.py','pagetrim.py','tables_plus.py','ietm.py','kg.py','build_kg.py','dimscan.py','ocrprep.py','layout.py','dedup.py','crossval.py','callouts.py','symbols.py','vlm.py','specsheet.py','qrgen.py','publog.py','build_publog.py','hybrid.py','publogdiff.py','dimscad.py','cad_render.py','make_cad.py','image3d_experiment.py','verify_3d_deps.py','jobpack.py','conflicts.py','faulttree.py','ask.py','validate.py','trust.py','integrity.py','signoff.py','tmrev.py','verifystate.py','serviceability.py','torqueseq.py','bom.py','pinouts.py','training.py','fieldnotes.py','crossmethod.py','rpstl.py','intervals.py','fluidsmatrix.py','commonality.py','handover.py','forms.py','ingestpipe.py','airgap.py','standards.py','nsndecode.py','smrdecode.py','cage.py','harnesstrace.py','macchart.py','safeguard.py','tools/run_timeout.py','tools/check_crlf.py']+glob.glob('features/*.py')]; print('py parse OK')"
if errorlevel 1 set "FAILED=!FAILED! py-syntax"

echo.
echo --- [gate 2] feature audit [dead-wiring / orphan-page / broken-link / duplicate-route] ---
%PY% audit_features.py
if errorlevel 1 set "FAILED=!FAILED! audit_features"

echo.
echo --- [gate 3] iteration snapshot [R10: regenerate + assert it matches CHANGELOG] ---
%PY% -B build_iteration_snapshot.py
if errorlevel 1 set "FAILED=!FAILED! iteration-snapshot"

echo.
echo --- [gate 4] completeness / no-truncation [R9; host-side true files] ---
%PY% tools\notrunc\verify_complete.py tests\test_property_fuzz.py --expect-tail "# END OF FILE"
if errorlevel 1 set "FAILED=!FAILED! notrunc:tests\test_property_fuzz.py"
%PY% tools\notrunc\verify_complete.py tests\test_congruency.py --expect-tail "# END OF FILE"
if errorlevel 1 set "FAILED=!FAILED! notrunc:tests\test_congruency.py"
%PY% tools\notrunc\verify_complete.py tests\test_extraction.py --expect-tail "# END OF FILE"
if errorlevel 1 set "FAILED=!FAILED! notrunc:tests\test_extraction.py"
for %%F in (jobcard.py figureparts.py vectorize.py audit_features.py tests\test_jobcard.py measures.py tables.py build_measures.py build_tables.py enrich.py build_enrich.py masterfile.py build_masterfile.py units.py leadingspecs.py specparse.py pdfmeta.py barcodes.py cautions.py textquality.py acronyms.py pagetrim.py tables_plus.py ietm.py kg.py build_kg.py dimscan.py ocrprep.py layout.py dedup.py crossval.py callouts.py symbols.py vlm.py specsheet.py qrgen.py publog.py build_publog.py hybrid.py publogdiff.py dimscad.py cad_render.py make_cad.py image3d_experiment.py jobpack.py conflicts.py faulttree.py ask.py validate.py trust.py integrity.py signoff.py tmrev.py verifystate.py serviceability.py torqueseq.py bom.py pinouts.py training.py fieldnotes.py crossmethod.py rpstl.py intervals.py fluidsmatrix.py commonality.py handover.py forms.py ingestpipe.py airgap.py standards.py nsndecode.py smrdecode.py cage.py harnesstrace.py macchart.py features\corpus.py tools\run_timeout.py tools\check_crlf.py) do (
  %PY% tools\notrunc\verify_complete.py %%F
  if errorlevel 1 set "FAILED=!FAILED! notrunc:%%F"
)

echo.
echo --- [gate 5] UI inline JS + external scripts ---
%PY% verify_ui.py
if errorlevel 1 set "FAILED=!FAILED! verify_ui"

echo.
echo --- [gate 5b] 3-D / CAD dependency check ^(medium finding #31: was orphaned from every entry point^) ---
%PY% verify_3d_deps.py
if errorlevel 1 set "FAILED=!FAILED! verify_3d_deps"

echo.
echo --- [gate 6] module self-tests ^(one loop iteration per module = one exit code each^) ---
for %%M in (analytics.py xref.py phash.py embed.py measures.py tables.py enrich.py masterfile.py units.py leadingspecs.py specparse.py pdfmeta.py barcodes.py cautions.py textquality.py acronyms.py pagetrim.py tables_plus.py ietm.py kg.py dimscan.py ocrprep.py layout.py dedup.py crossval.py callouts.py symbols.py vlm.py specsheet.py qrgen.py publog.py hybrid.py publogdiff.py dimscad.py conflicts.py faulttree.py ask.py jobpack.py validate.py trust.py integrity.py signoff.py tmrev.py verifystate.py serviceability.py torqueseq.py bom.py pinouts.py training.py fieldnotes.py crossmethod.py rpstl.py intervals.py fluidsmatrix.py commonality.py handover.py forms.py ingestpipe.py airgap.py standards.py nsndecode.py smrdecode.py cage.py harnesstrace.py macchart.py features\corpus.py) do (
  %PY% -B %%M
  if errorlevel 1 set "FAILED=!FAILED! selftest:%%M"
)

echo.
echo --- [gate 7] regression + quality suites ---
%PY% tests\test_pillars.py
if errorlevel 1 set "FAILED=!FAILED! test_pillars"
%PY% tests\test_features.py
if errorlevel 1 set "FAILED=!FAILED! test_features"
%PY% tests\test_features_integration.py
if errorlevel 1 set "FAILED=!FAILED! test_features_integration"
%PY% tests\test_features_modules.py
if errorlevel 1 set "FAILED=!FAILED! test_features_modules"
%PY% tests\test_patterns.py
if errorlevel 1 set "FAILED=!FAILED! test_patterns"
%PY% tests\test_jobcard.py
if errorlevel 1 set "FAILED=!FAILED! test_jobcard"
REM test_truncation quick_checks the real 3.65GB index via snapshot()'s default arg -- give it a
REM hard wall-clock cap so a locked/slow disk can never stall the whole gate (VERIFY-099 lesson).
%PY% tools\run_timeout.py 900 %PY% tests\test_truncation.py
if errorlevel 1 set "FAILED=!FAILED! test_truncation"
%PY% tests\test_hardening.py
if errorlevel 1 set "FAILED=!FAILED! test_hardening"
%PY% tests\test_search_quality.py
if errorlevel 1 set "FAILED=!FAILED! test_search_quality"
%PY% tests\test_accuracy.py
if errorlevel 1 set "FAILED=!FAILED! test_accuracy"
%PY% tests\test_extraction.py
if errorlevel 1 set "FAILED=!FAILED! test_extraction"
%PY% tests\test_congruency.py
if errorlevel 1 set "FAILED=!FAILED! test_congruency"
%PY% tests\rps_lint.py
if errorlevel 1 set "FAILED=!FAILED! rps_lint"

echo.
echo --- [gate 8] long-running suites ^(hard wall-clock timeouts via run_timeout.py^) ---
%PY% tools\run_timeout.py 600 %PY% tests\test_routes.py
if errorlevel 1 set "FAILED=!FAILED! test_routes"
%PY% tools\run_timeout.py 900 %PY% tests\test_newmodules.py 4000
if errorlevel 1 set "FAILED=!FAILED! test_newmodules"
%PY% tools\run_timeout.py 900 %PY% tests\test_property_fuzz.py 3000
if errorlevel 1 set "FAILED=!FAILED! test_property_fuzz"

echo.
echo --- [gate 9] safeguard verify ^(current files vs the latest vault snapshot^) ---
%PY% safeguard.py verify
if errorlevel 1 set "FAILED=!FAILED! safeguard-verify"

echo.
echo === body complete  %DATE% %TIME% ===
goto :eof
