@echo off
REM ============================================================================================
REM  THE VIEWER -- build a standalone package (no Python needed on the target shop PC).
REM  Produces dist\THE_VIEWER\THE_VIEWER.exe (+ bundled ui\). The corpus/index stay external;
REM  FIRST-RUN.bat points the exe at them. Host-side; needs internet the first time (PyInstaller).
REM ============================================================================================
cd /d "%~dp0"
where py >nul 2>nul && (set "PY=py") || (set "PY=python")
echo Ensuring PyInstaller (first build only; needs internet)...
%PY% -c "import PyInstaller" 2>nul || %PY% -m pip install --user --disable-pip-version-check --timeout 20 --retries 2 pyinstaller
echo.
echo Building THE VIEWER package from viewer.spec ...
%PY% -m PyInstaller --noconfirm --clean viewer.spec
echo.
echo Done. Package: dist\THE_VIEWER\  (run THE_VIEWER.exe, or use FIRST-RUN.bat to set up the corpus).
pause
