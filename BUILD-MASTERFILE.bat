@echo off
REM ============================================================================================
REM  BUILD THE MASTERFILE  --  the single, all-encompassing consolidation of dimensional data.
REM
REM  Merges the corpus measurements (index\measures.db, AUTHORITATIVE, page-cited to the real TMs)
REM  with the external gap-fills (index\enrich.db, supplemental) into ONE congruent dataset:
REM     index\masterfile.db   +   docs\MASTERFILE.md  (human-readable)
REM  No external links are carried in; corpus rows keep their authoritative page cite. Read-only on
REM  the sources; the Masterfile is a rebuildable append-only sidecar (R1/R6). No internet needed.
REM
REM  ORDER: run BUILD-MEASURES.bat first (corpus). Optionally ENRICH.bat (external). Then this.
REM  /master serves the consolidated view (raw + filtered), correlated to the authoritative files.
REM ============================================================================================
cd /d "%~dp0engine"
where py >nul 2>nul && (set "PY=py") || (set "PY=python")
echo Consolidating corpus + external into the Masterfile...
%PY% -B build_masterfile.py
echo.
echo Done. Open docs\MASTERFILE.md or browse /master in the app.
pause
