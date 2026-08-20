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
echo    0.  Add your unit's manuals     (put PDFs in the "corpus" folder -- see below)
echo    1.  Install dependencies        (INSTALL.bat)
echo    2.  Verify everything           (VERIFY-099.bat)
echo    3.  Build the PUBLOG catalog    (BUILD-PUBLOG.bat)   [big, ~minutes]
echo    4.  Resume OCR                  (RESUME-OCR.bat)     [runs in background]
echo    5.  Launch THE VIEWER           (RUN-VIEWER.bat)
echo    6.  More tasks                  (VIEWER-MENU.bat)
echo    9.  Exit
echo.
set "C="
set /p "C=Pick a number and press Enter: "
if "%C%"=="0" goto corpushelp
if "%C%"=="1" call :step "INSTALL.bat"
if "%C%"=="2" call :step "VERIFY-099.bat"
if "%C%"=="3" call :step "BUILD-PUBLOG.bat"
if "%C%"=="4" call :step "RESUME-OCR.bat"
if "%C%"=="5" call :step "RUN-VIEWER.bat"
if "%C%"=="6" call :step "VIEWER-MENU.bat"
if "%C%"=="9" goto :eof
goto menu

:corpushelp
REM Recommendations annex #16 (onboarding-sourcing): the old menu never mentioned this at all -- a
REM first-time user could install/verify/build/launch in order and never be told where TM PDFs go.
cls
echo ================================================================
echo                Add your unit's manuals
echo ================================================================
echo.
echo   THE VIEWER reads PDF manuals from a folder named "corpus", next to this
echo   script (at %~dp0corpus).
echo.
echo   To add your manuals:
echo     1. Copy your TM/parts-manual PDF files into that "corpus" folder.
echo        (If you don't have one yet, just create a folder here named "corpus"
echo         and copy the PDFs into it.)
echo     2. If your PDFs already live somewhere else on this PC and you'd rather
echo        not copy them, ask your IT/S6 support to set up a shortcut folder
echo        (a "junction") pointing "corpus" at that location instead.
echo     3. Come back here and choose 1 (Install) then 5 (Launch) to start
echo        scanning them in.
echo.
echo   Where do the PDFs themselves come from? THE VIEWER does not ship or
echo   download any manuals -- see docs\REFERENCE-SOURCING.md for where to get
echo   them through your unit's normal publications channel.
echo.
pause
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
