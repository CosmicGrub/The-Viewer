@echo off
setlocal
rem THE VIEWER -- open the interactive demo / onboarding tour.
rem Self-contained: no server needed. Double-click to run.
set "DEMO=%~dp0engine\ui\demo.html"
if not exist "%DEMO%" (
  echo Could not find the demo file:
  echo   %DEMO%
  echo Make sure this .bat is in the THE VIEWER root folder.
  pause
  exit /b 1
)
echo Opening THE VIEWER interactive demo in your browser...
start "" "%DEMO%"
endlocal
