@echo off
REM ============================================================================================
REM  Build the TABLES sidecar: locate every structured table in the PDFs (PyMuPDF find_tables),
REM  flag SPEC/dimension tables (cells carrying measurement units) -> index\tables.db.
REM  READ-ONLY on the corpus; append-only sidecar (R1/R6). Resumable per-doc. Best run while OCR
REM  is paused. Needs PyMuPDF (already a project dependency). No internet needed.
REM ============================================================================================
cd /d "%~dp0engine"
where py >nul 2>nul && (set "PY=py") || (set "PY=python")
%PY% -c "import fitz" 2>nul || (echo PyMuPDF not installed -- run FIRST-RUN.bat first. & pause & exit /b 1)
echo Scanning every PDF page for structured tables (slower than OCR; grab a coffee)...
%PY% -B build_tables.py
echo.
echo Done. index\tables.db now records which pages hold spec/dimension tables.
pause
