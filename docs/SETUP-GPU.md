# SETUP — Advanced / GPU production build

Goal: run OCR on your NVIDIA GPU for a large speedup over CPU.

## Status / honest notes
- The engine **requests** GPU via a version-proof config (`use_cuda: true`), with **automatic CPU
  fallback** — it never crashes if the GPU isn't ready. (Earlier a `det_use_cuda` kwarg crashed on
  some RapidOCR versions with `'model_path'`; that's fixed.)
- **Whether the GPU actually engages depends on the CUDA runtime** being installed and matching the
  `onnxruntime-gpu` version. If it isn't, you'll see
  `CUDAExecutionProvider is not in available providers …` and it runs on CPU.

## Requirements for real GPU acceleration
- NVIDIA GPU + recent driver (you have one).
- **CUDA Toolkit + cuDNN** versions matching the installed `onnxruntime-gpu`
  (check `python -c "import onnxruntime; print(onnxruntime.__version__)"` and ONNX Runtime's
  CUDA compatibility table at https://onnxruntime.ai/docs/execution-providers/CUDA-EP.html).

## One-command readiness check
Before (or after) a run, get a clear verdict:
```
python engine\gpu_check.py
```
It prints `nvidia-smi`, the onnxruntime providers, and **GPU READY ✓** or **CPU ONLY** with the exact
fix for your case.

## Current OCR status (as of the last check)
- **1.6% done** (1,896 of 121,135 scanned pages); **93.5% of all pages already searchable** (the rest are
  born-digital text). The 275 previously-stuck pages were recovered and the queue is **prioritized**:
  parts catalogs (RPSTL/24P) first (25,516 pages at priority 0), then troubleshooting, maintenance,
  operator, then the rest — so a partial run helps the most-searched pages immediately.

## Steps
1. Close any running OCR window.
2. (Optional) `python engine\gpu_check.py` to confirm the GPU path.
3. Double-click **`engine\run_ocr_gpu.bat`** (installs `onnxruntime-gpu`, requests CUDA, runs OCR).
4. Watch the first lines:
   - `OCR engine: RapidOCR with CUDA requested …` then no provider warning → **on GPU**.
   - `CUDAExecutionProvider is not in available providers …` → on CPU; install CUDA/cuDNN (above) and re-run.

## Alternative GPU path (RapidOCR's own recommendation)
RapidOCR suggests `rapidocr_paddle` for GPU inference. If the onnxruntime-gpu route won't engage, we
can switch the engine to `rapidocr_paddle` (PaddlePaddle-GPU) — ask and I'll wire it in.

## Console tip (Windows QuickEdit)
If you ever **click inside the black OCR window**, Windows may enter "Select" mode and **pause** the
output (the title shows "Select"). Press **Esc** or **Enter**, or click another window, to resume.

## Tuning
- `--workers` = parallel OCR streams (8 by default for GPU). `--dpi 200` balances quality/speed.
- Fully **resumable** — stop and re-run anytime.
