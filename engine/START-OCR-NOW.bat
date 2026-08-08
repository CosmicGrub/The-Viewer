@echo off
REM ============================================================
REM  THE VIEWER -- one-click OCR launcher (max throughput + auto-resume).
REM  Calls the autonomous runner with /max (feed the GPU hard) and
REM  /auto (resume at each logon until the scan hits 100%).
REM  Created for "run it tonight" -- just double-click.
REM ============================================================
cd /d "%~dp0"
call "%~dp0run_ocr_auto.bat" /max /auto
