# THE VIEWER — Two builds, one core

THE VIEWER ships as **one shared codebase** that runs in two deploy profiles. There is no
divergent code to maintain — the difference is configuration (profile flags) and packaging.
This keeps the backwards-compatibility rule (R1) intact: same `viewer.db` schema, same engine.

## ★ Advanced / GPU production build — *the priority*

The master project (`THE VIEWER`) **is** the production build. It uses your NVIDIA GPU for OCR
(RapidOCR on `onnxruntime-gpu`), which is typically **10–30× faster** than CPU.

- OCR: `engine\run_ocr_gpu.bat` → delegates to `engine\run_ocr_auto.bat`, the hardware-adaptive
  runner (`sysprobe.py` probes the actual machine and picks `--gpu`/`--workers`/`--dpi` at runtime,
  instead of the old hardcoded `ocrall --gpu --workers 8 --dpi 200`).
- Indexing: `engine\run_indexing.bat`  ·  App: `engine\run_app.bat`
- Falls back to CPU automatically if CUDA isn't ready, so it never hard-fails.
- Setup: see `SETUP-GPU.md`.

## Lite / portable build — for a weaker PC

Generated from the master with one command. Produces a **self-contained `THE VIEWER PORTABLE`
folder** you copy to any Windows PC.

- Build it: `engine\make_portable.bat` (run on the production box after indexing).
- Ships the **finished index**, so the weak PC searches instantly — no heavy processing.
- **Both modes:** search-only by default; can also index/OCR slowly (`run_ocr_lite.bat`, which
  delegates to `run_ocr_auto.bat` so it self-corrects workers/DPI/GPU to whatever PC it lands on,
  instead of a fixed `--workers 2 --dpi 150`).
- One-click: `SETUP.bat` (installs CPU packages once) → `START.bat` (open the app).
- Setup: see `SETUP-LITE.md`.

## How the profile is selected

`viewer_ingest.py` takes additive flags (defaults unchanged → R1 safe): `--gpu`, `--workers N`,
`--dpi N`. Both builds' OCR entry points (`run_ocr_gpu.bat`, `run_ocr_lite.bat`) now delegate to
`run_ocr_auto.bat`, which fills these in at runtime from `sysprobe.py`'s probe of the actual
machine — not fixed per-build numbers. Old fixed defaults for reference (still what a strong-GPU
or bare-minimum-CPU box lands on today): GPU-class hardware → `--gpu --workers 8 --dpi 200`-ish;
legacy/low-power CPU → `--workers 2 --dpi 130`-ish. Run `engine\sysprobe.py` on any machine to see
exactly what it picks there.

Diagram: `docs/diagrams/09-forks` (dark, + PDF).

## Workflow

1. Index + OCR fast on the **GPU box** (`run_ocr_gpu.bat`).
2. `make_portable.bat` → carry **`THE VIEWER PORTABLE`** to the weak PC.
3. On the weak PC: `SETUP.bat` once, then `START.bat`.
