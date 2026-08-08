@echo off
setlocal enableextensions
REM ============================================================================================
REM  START-HERE.bat -- guided first-run for THE VIEWER. Walks a new machine through the whole
REM  setup in order: install deps -> verify -> (optional) build the PUBLOG catalog -> launch.
REM  Safe to re-run. Keep Windows (CRLF) line endings.
REM ============================================================================================
cd /d "%~dp0"
title THE VIEWER - Start Here

:menu
cls
echo ================================================================
echo                THE VIEWER  -  guided setup
echo ================================================================
echo.
echo   Do these in order the first time. Each step is safe to re-run.
echo.
echo    1.  Install dependencies        (INSTALL.bat)
echo    2.  Verify everything           (VERIFY-099.bat)
echo    3.  Build the PUBLOG catalog    (BUILD-PUBLOG.bat)   [big, ~minutes]
echo    4.  Resume OCR                  (RESUME-OCR.bat)     [runs in background]
echo    5.  Launch THE VIEWER           (RUN-VIEWER.bat)
echo    6.  More tasks                  (VIEWER-MENU.bat)
echo    0.  Exit
echo.
set "C="
set /p "C=Pick a number and press Enter: "
if "%C%"=="1" call :step "INSTALL.bat"
if "%C%"=="2" call :step "VERIFY-099.bat"
if "%C%"=="3" call :step "BUILD-PUBLOG.bat"
if "%C%"=="4" call :step "RESUME-OCR.bat"
if "%C%"=="5" call :step "RUN-VIEWER.bat"
if "%C%"=="6" call :step "VIEWER-MENU.bat"
if "%C%"=="0" goto :eof
goto menu

:step
if not exist "%~1" (
  echo.
  echo [NOTE] %~1 was not found next to this script.
  echo.
  pause
  goto :eof
)
echo.
echo --- running %~1 ---
call "%~1"
echo.
echo --- done: %~1 ---
pause
goto :eof
