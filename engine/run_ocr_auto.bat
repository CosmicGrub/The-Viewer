@echo off
REM ============================================================
REM  THE VIEWER -- AUTONOMOUS, HARDWARE-ADAPTIVE OCR runner.
REM  Probes your PC, installs the right (GPU or CPU) OCR stack, then runs OCR to 100% UNATTENDED,
REM  auto-restarting if it ever crashes. Tuned to your machine (e.g. Acer Nitro 5 = GPU + thermal
REM  headroom). When it finishes it writes a detailed report and opens it.
REM
REM    run_ocr_auto.bat          run once, to completion (resumable)
REM    run_ocr_auto.bat /auto    also register it to resume automatically at each logon
REM    run_ocr_auto.bat /stop    remove the auto-resume logon task
REM  Tip (laptop): plug into AC power and keep the vents clear / fans high for the long run.
REM ============================================================
setlocal enabledelayedexpansion
title THE VIEWER - Autonomous OCR
set "DB=%~dp0..\index\viewer.db"
if not exist "%DB%" set "DB=%~dp0..\index\viewer_index.db"

set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( echo [ERROR] Python 3 not found on PATH. Install Python 3.8+ and re-run.& pause & goto :eof )

REM parse flags: /auto (resume at logon), /stop (remove), /max (full-throughput: GPU max-perf mode)
set "OPT_AUTO="
set "OPT_STOP="
set "REGFLAGS="
for %%a in (%*) do (
  if /I "%%a"=="/auto" set "OPT_AUTO=1"
  if /I "%%a"=="/stop" set "OPT_STOP=1"
  if /I "%%a"=="/max"  ( set "VIEWER_OCR_MAX=1" & set "REGFLAGS=/max" )
)
if defined OPT_STOP ( schtasks /Delete /TN "THE_VIEWER_OCR_Auto" /F & echo Removed auto-resume task. & pause & goto :eof )
if "%VIEWER_OCR_MAX%"=="1" echo  [MAX PERFORMANCE] using most cores to feed the GPU.

echo ============================================================
echo  Probing this PC to pick the right resources...
echo ============================================================
%PY% "%~dp0sysprobe.py"
for /f "delims=" %%i in ('%PY% "%~dp0sysprobe.py" --get ocr_workers') do set "W=%%i"
for /f "delims=" %%i in ('%PY% "%~dp0sysprobe.py" --get ocr_dpi')     do set "DPI=%%i"
for /f "delims=" %%i in ('%PY% "%~dp0sysprobe.py" --get use_gpu')     do set "GPU=%%i"
if not defined W set "W=2"
if not defined DPI set "DPI=160"
set "GPUFLAG="
if "%GPU%"=="1" set "GPUFLAG=--gpu"
echo.
echo  Plan: workers=%W%  dpi=%DPI%  gpu=%GPU%
echo.

echo Ensuring OCR packages (PyMuPDF, Pillow, RapidOCR PP-OCRv5 + v4 fallback)...
REM (skipped unconditional 'pip install --upgrade pip' -- it hangs retrying when offline; installs below are import-guarded)
%PY% -c "import fitz" 2>nul || %PY% -m pip install --user --disable-pip-version-check --timeout 8 --retries 1 pymupdf
%PY% -c "import PIL" 2>nul || %PY% -m pip install --user pillow
%PY% -c "import rapidocr_onnxruntime" 2>nul || %PY% -m pip install --user rapidocr-onnxruntime
%PY% -c "import rapidocr" 2>nul || %PY% -m pip install --user rapidocr
if "%GPU%"=="1" (
  echo Ensuring GPU runtime ^(onnxruntime-gpu^)...
  %PY% -c "import onnxruntime as o,sys;sys.exit(0 if 'CUDAExecutionProvider' in o.get_available_providers() else 1)" 2>nul || (
    %PY% -m pip uninstall -y onnxruntime >nul 2>nul
    %PY% -m pip install --user onnxruntime-gpu
  )
)
echo.
%PY% "%~dp0gpu_check.py"

echo.
echo Preflight health checks (disk / index integrity / schema / python)...
%PY% "%~dp0preflight.py" --db "%DB%"
if errorlevel 1 ( echo. & echo [STOP] Preflight failed -- fix the issue above before the unattended run. & pause & goto :eof )

REM engine marker for the report
> "%~dp0..\index\ocr_engine.txt" echo RapidOCR (PP-OCRv5 if available) - %GPU:0=CPU% - workers %W% - dpi %DPI%
if "%GPU%"=="1" ( >"%~dp0..\index\ocr_engine.txt" echo RapidOCR PP-OCRv5/v4 - GPU - workers %W% - dpi %DPI% ) else ( >"%~dp0..\index\ocr_engine.txt" echo RapidOCR PP-OCRv5/v4 - CPU - workers %W% - dpi %DPI% )

REM how many remain at the start (so we only open the report when it actually finishes this run)
for /f "delims=" %%n in ('%PY% "%~dp0ocr_pending.py" --db "%DB%"') do set "START=%%n"
if "%START%"=="0" ( echo OCR is already at 100%% -- nothing to do. & %PY% "%~dp0ocr_report.py" --db "%DB%" & pause & goto :register )

echo Safeguard snapshot before the run...
%PY% "%~dp0safeguard.py" snapshot --label pre-ocr 2>nul || echo (snapshot skipped)
echo Cleanup: requeue any half-finished pages...
%PY% "%~dp0viewer_ingest.py" cleanup --db "%DB%"

:ocrloop
echo.
echo ============================================================
echo  OCR pass (workers=%W%, dpi=%DPI%, gpu=%GPU%). Resumable. %DATE% %TIME%
echo ============================================================
%PY% "%~dp0viewer_ingest.py" ocrall %GPUFLAG% --workers %W% --dpi %DPI% --db "%DB%"
for /f "delims=" %%n in ('%PY% "%~dp0ocr_pending.py" --db "%DB%"') do set "REMAIN=%%n"
if "%REMAIN%"=="-1" ( echo [warn] could not read the index; retrying in 15s & timeout /t 15 /nobreak >nul & goto ocrloop )
if not "%REMAIN%"=="0" (
  echo [auto] %REMAIN% pages still pending -- the pass stopped early; restarting in 8s...
  timeout /t 8 /nobreak >nul
  goto ocrloop
)

echo.
echo ============================================================
echo  OCR COMPLETE. Generating the detailed report...
echo ============================================================
%PY% "%~dp0ocr_report.py" --full --db "%DB%"
%PY% "%~dp0safeguard.py" snapshot --label post-ocr 2>nul
REM v1.13.0: prune old safeguard snapshots after the pass so the vault never grows without bound.
REM NOTE: the full 3.65GB index-DB backup is intentionally MANUAL (too heavy to run unattended
REM here). When you want one, run:   python "%~dp0safeguard.py" backupdb
REM   -> VACUUM INTO ..\backups\db\viewer-YYYYMMDD-HHMM.db (verified, keeps the newest 2 copies,
REM      refuses to start unless free disk > 1.3x the DB size). See also VERIFY.bat's header.
%PY% "%~dp0safeguard.py" gc --keep 10
start "" "%~dp0..\docs\OCR-COMPLETION-REPORT.md"

:register
if defined OPT_AUTO (
  schtasks /Create /TN "THE_VIEWER_OCR_Auto" /TR "\"%~f0\" %REGFLAGS%" /SC ONLOGON /F
  echo Registered auto-resume at logon ^(safe no-op once OCR is 100%%; remove with run_ocr_auto.bat /stop^).
)
echo.
echo Done.
pause
endlocal
