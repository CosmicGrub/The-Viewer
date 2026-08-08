@echo off
REM ============================================================================================
REM  VERIFY-099.bat -- THIN FORWARDER (since v1.13.0).
REM  The ONE authoritative verification gate now lives in VERIFY.bat at the project root:
REM  it is the union of the old VERIFY-099 body and engine\tests\verify_all.py, rebuilt on
REM  exit-code truth (per-step `if errorlevel 1` accounting; no &&-chains, no log-grep summary).
REM  This file is KEPT because other launchers/docs reference it by name (R6 append-only):
REM  START-HERE.bat, VIEWER-MENU.bat, RUN-ALL-VERIFY.bat, INSTALL.bat, CUT-V1.0.bat.
REM  NOTE: this file MUST keep Windows (CRLF) line endings.
REM ============================================================================================
call "%~dp0VERIFY.bat" %*
exit /b %ERRORLEVEL%
