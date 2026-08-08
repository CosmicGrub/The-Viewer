@echo off
REM ============================================================================================
REM  BUILD THE KNOWLEDGE GRAPH -> index\kg.db  (catalog §3.11/§7.4)
REM  Ties parts, figures, vehicles, NSNs, and Masterfile dimensions into one graph so "everything
REM  about X" is one hop. READ-ONLY on viewer.db + the sidecars; append-only sidecar (R1/R6).
REM  Run AFTER BUILD-MASTERFILE.bat for the richest graph. No internet needed. /kg + /api/kg query it.
REM ============================================================================================
cd /d "%~dp0engine"
where py >nul 2>nul && (set "PY=py") || (set "PY=python")
echo Assembling the knowledge graph from viewer.db + sidecars...
%PY% -B build_kg.py
echo.
echo Done. index\kg.db built. Query it at /api/kg?q=... (offline).
pause
