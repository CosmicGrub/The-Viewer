@echo off
REM Build the Lite / portable package (THE VIEWER PORTABLE) next to this project.
setlocal
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( echo [ERROR] Python 3 not found on PATH.& pause & exit /b )
%PY% "%~dp0make_portable.py" %*
echo.
pause
endlocal
