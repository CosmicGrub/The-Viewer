@echo off
REM ============================================================================================
REM  BUILD EDITION / DUPLICATE CLUSTERS -> index\dedup.db  (catalog §7.1)
REM  Finds near-identical documents (same TM, different change/edition) via word-shingle Jaccard
REM  similarity, so /api/editions can surface "other editions of this manual" in Deep Zoom.
REM  READ-ONLY on viewer.db; append-only sidecar (R1/R6). O(n^2) -- a large corpus can take a
REM  while. Override the sampling with --sample-pages N / --max-chars N / --threshold F, e.g.:
REM    DEDUP.bat --sample-pages 8 --threshold 0.75
REM ============================================================================================
cd /d "%~dp0engine"
where py >nul 2>nul && (set "PY=py") || (set "PY=python")
echo Clustering editions/duplicates across the corpus...
%PY% -B build_dedup.py %*
echo.
echo Done. index\dedup.db built. /api/editions?doc=ID queries it offline.
pause
