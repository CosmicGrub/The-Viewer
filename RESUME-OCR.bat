@echo off
REM ============================================================================================
REM  THE VIEWER -- RESUME THE GPU OCR SCAN (self-restarting watchdog runner).
REM
REM  The scan stalled at ~43.8% (53,016 done / ~68,119 scanned pages still pending). This resumes
REM  it to 100%. It delegates to the proven autonomous runner, which:
REM    * probes the GPU + installs the RapidOCR / onnxruntime-gpu stack,
REM    * requeues any half-finished pages (resets the stale 'running' locks to 'pending'),
REM    * runs OCR in a LOOP -- if a pass stops early or crashes it auto-restarts until 0 remain,
REM    * writes docs\OCR-COMPLETION-REPORT.md and snapshots when it finishes.
REM
REM  Usage:
REM    RESUME-OCR.bat          resume now, GPU auto-detected (recommended)
REM    RESUME-OCR.bat /max     full-throughput -- use more CPU cores to feed the GPU
REM    RESUME-OCR.bat /auto    also register auto-resume at each Windows logon
REM    RESUME-OCR.bat /stop    remove the auto-resume logon task
REM
REM  Tip (Acer Nitro 5 / laptop): plug into AC, keep the vents clear and fans high -- this is a
REM  multi-hour run (~68k pages; roughly 15-20 hours of GPU time). It is safe to stop and re-run.
REM ============================================================================================
title THE VIEWER - Resume GPU OCR
cd /d "%~dp0engine"
if not exist "run_ocr_auto.bat" (
  echo [ERROR] engine\run_ocr_auto.bat not found -- cannot resume. Check the project is intact.
  pause & exit /b 1
)
echo Resuming the GPU OCR scan (self-restarting). This window must stay open while it runs.
echo.
call "run_ocr_auto.bat" %*
