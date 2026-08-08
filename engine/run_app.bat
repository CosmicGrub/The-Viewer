@echo off
REM ============================================================
REM  THE VIEWER -- launch the offline app (search + document viewer + parts request)
REM ============================================================
setlocal
set "VIEWER_DB=%~dp0..\index\viewer.db"
if not exist "%VIEWER_DB%" set "VIEWER_DB=%~dp0..\index\viewer_index.db"
set "PORT=8765"

set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( echo [ERROR] Python 3 not found on PATH.& pause & goto :eof )

REM Offline-safe package check: touch the network ONLY if a package is actually missing.
REM (Previously this ran `pip install --upgrade pip` on every launch, which hangs retrying when offline.)
echo Checking app packages (offline-safe -- no network unless something is missing)...
%PY% -c "import fitz, reportlab, PIL" 2>nul
if errorlevel 1 (
  echo   A package is missing -- attempting install [first run only; needs internet].
  %PY% -c "import fitz"     2>nul || %PY% -m pip install --user --disable-pip-version-check --timeout 8 --retries 1 pymupdf
  %PY% -c "import reportlab" 2>nul || %PY% -m pip install --user --disable-pip-version-check --timeout 8 --retries 1 reportlab
  %PY% -c "import PIL"      2>nul || %PY% -m pip install --user --disable-pip-version-check --timeout 8 --retries 1 pillow
) else (
  echo   All present -- skipping install [no network touched].
)

echo Preflight health checks...
%PY% "%~dp0preflight.py" --db "%VIEWER_DB%"
if errorlevel 1 ( echo [warn] a preflight check failed -- starting anyway; see above. )

echo Starting THE VIEWER at http://127.0.0.1:%PORT%
start "" http://127.0.0.1:%PORT%
%PY% "%~dp0viewer_app.py" --db "%VIEWER_DB%" --port %PORT%
endlocal
