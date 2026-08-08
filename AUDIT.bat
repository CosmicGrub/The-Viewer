@echo off
REM Feature audit: cross-check the live route registry against the UI folder (host-side; the sandbox mount
REM truncates grown files). Writes docs\feature_audit.txt and prints the summary. Exits non-zero on any FAIL.
cd /d "%~dp0engine"
python audit_features.py
echo.
echo (full report: docs\feature_audit.txt)
