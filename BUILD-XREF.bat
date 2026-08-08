@echo off
REM ============================================================
REM  THE VIEWER -- cross-reference enrichment from PUB LOG.
REM  Adds manufacturer names (CAGEC->company) and recovers
REM  missing NSNs (part#+CAGEC->NSN) into small JSON sidecars.
REM  Run AFTER BUILD-RPSTL.bat. Read-only on the index.
REM ============================================================
setlocal
cd /d "%~dp0engine"
set "PY=python"
where python >nul 2>nul || set "PY=py"

echo Enriching part records from PUB LOG (manufacturer names + NSN recovery)...
echo.
%PY% build_xref.py
echo.
echo Done. Part-number lookups now show the manufacturer and recover NSNs the OCR missed.
pause
endlocal
