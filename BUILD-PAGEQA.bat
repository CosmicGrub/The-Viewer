@echo off
REM ============================================================================================
REM  BUILD VISION-LANGUAGE PAGE-QA SIDECAR -> index\pageqa.db  (catalog §10.1 + §3.12)
REM  Samples pages where measures.py/tables.py/RPSTL extraction found NOTHING (and ocr_confidence
REM  is high enough to be worth asking), asks a vision-language model a generic sweep question, and
REM  writes ONLY self-grounded + OCR-cross-checked (verified=True) answers to the sidecar.
REM  READ-ONLY on viewer.db/measures.db/tables.db/rpstl.db; append-only sidecar (R1/R6). Requires a
REM  GPU-capable machine with engine/vlm_backend.py's optional dependencies (transformers + torch)
REM  installed -- on any other machine this prints why and exits cleanly, writing nothing.
REM
REM  --max-pages N is REQUIRED (a budget cap, not an unbounded corpus sweep) -- re-run repeatedly
REM  to make gradual, resumable progress; an already-verified page is never re-asked. Example:
REM    BUILD-PAGEQA.bat --max-pages 200
REM ============================================================================================
cd /d "%~dp0engine"
where py >nul 2>nul && (set "PY=py") || (set "PY=python")
echo Sampling no-extraction pages and asking the vision-language model...
%PY% -B build_pageqa.py %*
echo.
echo Done. index\pageqa.db built (verified rows only). Next masterfile.py rebuild picks them up.
pause
