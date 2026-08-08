@echo off
REM ============================================================
REM  THE VIEWER -- run the pillar tests + mutation testing.
REM  Tests run against a deterministic fixture (no live corpus needed).
REM ============================================================
setlocal
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( echo [ERROR] Python 3 not found on PATH.& pause & goto :eof )
%PY% -c "import reportlab" 2>nul || %PY% -m pip install --user reportlab
echo === Pillar tests (engine logic) ===
%PY% "%~dp0tests\test_pillars.py"
echo.
echo === Truncation / recovery tests (data protection) ===
%PY% "%~dp0tests\test_truncation.py"
echo.
echo === Mutation testing: 2 rounds (engine logic + safeguard) ===
%PY% "%~dp0tests\mutation_xl.py"
pause
endlocal
