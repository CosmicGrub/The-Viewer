@echo off
REM HTTP-level integration + fuzz: spins the app on a test port against a synthetic index and hammers every GET
REM route (benign + adversarial params), asserting no 5xx and parseable JSON from /api. Host-side.
REM   RUN-HTTP-FUZZ.bat         (200 fuzz requests)     RUN-HTTP-FUZZ.bat 5000   (more)
cd /d "%~dp0engine"
where py >nul 2>nul && (set "PY=py") || (set "PY=python")
%PY% tests\test_http.py %1
echo.
pause
