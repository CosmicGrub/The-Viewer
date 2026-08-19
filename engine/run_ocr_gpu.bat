@echo off
REM ============================================================
REM  THE VIEWER -- GPU OCR pass (Advanced / production build)
REM  Uses RapidOCR on your NVIDIA GPU via onnxruntime-gpu -- typically 10-30x
REM  faster than CPU. Falls back to CPU automatically if the GPU runtime isn't ready.
REM  Resumable: stop and re-run anytime.
REM
REM  Requirements: NVIDIA GPU + recent driver. CUDA/cuDNN are pulled in by
REM  onnxruntime-gpu's wheels for most setups; see docs\SETUP-GPU.md if it falls back.
REM
REM  Used to run its own hardcoded `ocrall --gpu --workers 8 --dpi 200` pass --
REM  fixed numbers that assumed the exact GPU production box this script was
REM  written on. run_ocr_auto.bat already probes the actual machine at runtime
REM  via sysprobe.py and self-corrects workers/dpi/gpu/battery-throttling, but
REM  this script bypassed that probe entirely -- so a GPU build installed on
REM  different-than-assumed hardware (weaker/no GPU, laptop on battery) got none
REM  of that correction. Now a thin wrapper that delegates to the one adaptive
REM  launcher instead of drifting out of sync with it as a second hardcoded
REM  copy. Same familiar double-click entry point (run_ocr_gpu.bat).
REM ============================================================
cd /d "%~dp0"
call "%~dp0run_ocr_auto.bat"
