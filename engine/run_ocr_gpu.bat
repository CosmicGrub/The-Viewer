@echo off
REM ============================================================
REM  THE VIEWER -- GPU OCR pass (Advanced / production build)
REM  Uses RapidOCR on your NVIDIA GPU via onnxruntime-gpu -- typically 10-30x
REM  faster than CPU. Falls back to CPU automatically if the GPU runtime isn't ready.
REM  Resumable: stop and re-run anytime.
REM
REM  Requirements: NVIDIA GPU + recent driver. CUDA/cuDNN are pulled in by
REM  onnxruntime-gpu's wheels for most setups; see docs\SETUP-GPU.md if it falls back.
REM ============================================================
setlocal

set "VIEWER_DB=%~dp0..\index\viewer.db"
if not exist "%VIEWER_DB%" set "VIEWER_DB=%~dp0..\index\viewer_index.db"

set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( echo [ERROR] Python 3 not found on PATH.& goto :end )

REM (skipped unconditional 'pip install --upgrade pip' -- it hangs retrying when offline; installs below are import-guarded)
echo Checking packages for GPU OCR (offline-safe -- no network unless something is missing)...
%PY% -c "import fitz" 2>nul || %PY% -m pip install --user pymupdf
%PY% -c "import rapidocr_onnxruntime" 2>nul || %PY% -m pip install --user rapidocr-onnxruntime
REM Swap CPU onnxruntime for the GPU build (safe to re-run)
%PY% -c "import onnxruntime as o,sys; sys.exit(0 if 'CUDAExecutionProvider' in o.get_available_providers() else 1)" 2>nul || (
  echo Installing onnxruntime-gpu ...
  %PY% -m pip uninstall -y onnxruntime >nul 2>nul
  %PY% -m pip install --user onnxruntime-gpu
)

echo.
echo Safeguard: snapshot critical files before the OCR run (restore point)...
%PY% "%~dp0safeguard.py" snapshot --label pre-ocr 2>nul || echo (safeguard snapshot skipped)

echo.
echo Cleanup: drop dead rows and requeue any previously-failed pages...
%PY% "%~dp0viewer_ingest.py" cleanup --db "%VIEWER_DB%"

echo.
echo GPU OCR pass (RapidOCR + CUDA, LIVE). Resumable. Will fall back to CPU if CUDA isn't available.
echo.
%PY% "%~dp0viewer_ingest.py" ocrall --gpu --workers 8 --dpi 200 --db "%VIEWER_DB%"

echo.
echo OCR COMPLETE. Index status:
%PY% "%~dp0viewer_ingest.py" status --db "%VIEWER_DB%"

:end
echo.
pause
endlocal
