@echo off
REM ============================================================
REM  THE VIEWER -- one-click launcher (project-root button).
REM  Starts the offline app: dependency check + preflight + opens
REM  the browser + serves at http://127.0.0.1:8765.
REM
REM  Delegates to engine\run_app.bat (the maintained launcher) so
REM  there is ONE source of truth; falls back to a direct start if
REM  that file is ever missing, so this button always works.
REM ============================================================
setlocal
set "ROOT=%~dp0"

if exist "%ROOT%engine\run_app.bat" (
  call "%ROOT%engine\run_app.bat"
  goto :end
)

echo [warn] engine\run_app.bat not found -- starting the server directly.
set "VIEWER_DB=%ROOT%index\viewer.db"
if not exist "%VIEWER_DB%" set "VIEWER_DB=%ROOT%index\viewer_index.db"
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( echo [ERROR] Python 3 not found on PATH.& pause & goto :end )
if not exist "%ROOT%engine\viewer_app.py" ( echo [ERROR] engine\viewer_app.py not found -- is this the THE VIEWER root folder?& pause & goto :end )
echo Starting THE VIEWER at http://127.0.0.1:8765 ...
start "" http://127.0.0.1:8765
%PY% "%ROOT%engine\viewer_app.py" --db "%VIEWER_DB%" --port 8765

:end
endlocal
