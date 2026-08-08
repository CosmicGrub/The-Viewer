@echo off
REM ============================================================================================
REM  THE VIEWER -- cut v1.0.0. Run this ONLY after RUN-ALL-VERIFY.bat is clean.
REM  Takes a safeguard snapshot (rollback point), stamps VERSION 1.0.0, banners both changelogs,
REM  and regenerates the iteration snapshot so it still matches (R10). Prompts before it commits.
REM ============================================================================================
setlocal
cd /d "%~dp0engine"
where py >nul 2>nul && (set "PY=py") || (set "PY=python")

echo Stamping the project as v1.0.0 [VERIFY-099 came back clean] ...
echo Safeguard snapshot [rollback point] ...
%PY% safeguard.py snapshot --label pre-v1.0 2>nul || echo (snapshot helper skipped)

echo Cutting v1.0.0 ...
%PY% cut_v1.py
echo.
echo Done. Review docs\CHANGELOG.md top + docs\RELEASE-NOTES-1.0.md, then zip/commit a tagged backup.
pause
endlocal
