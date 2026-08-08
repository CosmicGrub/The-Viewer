@echo off
REM ============================================================
REM  THE VIEWER -- SUPERVISED server. Runs the app and AUTO-RESTARTS it if it ever crashes,
REM  so an unattended kiosk / shop machine stays up. Preflight gates the first start.
REM  (For a normal one-shot launch use run_app.bat. Press Ctrl+C here to stop the supervisor.)
REM ============================================================
setlocal enabledelayedexpansion
title THE VIEWER - supervised server
set "VIEWER_DB=%~dp0..\index\viewer.db"
if not exist "%VIEWER_DB%" set "VIEWER_DB=%~dp0..\index\viewer_index.db"
set "PORT=8765"
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( echo [ERROR] Python 3 not found on PATH.& pause & goto :eof )

echo Preflight health checks...
%PY% "%~dp0preflight.py" --db "%VIEWER_DB%"
if errorlevel 1 ( echo. & echo [STOP] Preflight failed -- fix the issue above before serving. & pause & goto :eof )

start "" http://127.0.0.1:%PORT%
:loop
echo [watchdog] starting server  %DATE% %TIME%
%PY% "%~dp0viewer_app.py" --db "%VIEWER_DB%" --port %PORT%
echo [watchdog] server exited (code %ERRORLEVEL%). Restarting in 5s...  (Ctrl+C to stop the supervisor)
timeout /t 5 /nobreak >nul
goto loop
endlocal
