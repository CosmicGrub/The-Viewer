# System requirements & adaptive resources

THE VIEWER is built **Windows-11-first** with **COMPLETE backward compatibility down to Windows 7 and
Windows Vista**: every user-facing feature — search, the vehicle hub, the document viewer, the 104th
parts-request sheet, and OCR — works on all of them. The engine **substitutes the right tool per OS**
(PyMuPDF on modern Windows ↔ **Poppler** on legacy; RapidOCR on modern ↔ **Tesseract** on legacy; the
server and search are pure Python standard library + SQLite, which run everywhere).

The **only** thing that is Windows-10+ is **NVIDIA GPU acceleration** — and that's a *speed booster, not
a feature*: CUDA/onnxruntime don't exist for Vista/7, so on those OSes OCR runs on the CPU via Tesseract
and still finishes; the resulting searchable index is identical. On first launch a **capability probe**
detects your machine and picks the right engines + resource budget automatically.

## The probe (`engine\sysprobe.py`)

Run it any time (the autonomous OCR runner runs it for you):
```
python engine\sysprobe.py
```
It detects **OS + build, Python, CPU cores, RAM, GPU (NVIDIA/CUDA), free disk, and laptop/battery**,
then writes `index\hardware_profile.json` with a recommended profile. The launchers read it
automatically (`sysprobe.py --get ocr_workers|ocr_dpi|use_gpu`).

## Capability tiers (how resources are granted)

| Tier | Looks like | OCR | Workers | DPI |
|------|------------|-----|--------:|----:|
| **GPU laptop / workstation** | NVIDIA GPU + CUDA, Win10/11 (e.g. **Acer Nitro 5**) | GPU (PP-OCRv5) | up to 5 (laptop) / 8 | 220 |
| **Strong CPU** | 8+ cores, 16 GB+ | CPU | up to 6 | 200 |
| **Modest CPU** | 4 cores, 8 GB | CPU | 3 | 165 |
| **Legacy / low-power** | 2 cores / <8 GB / Win7-8 | CPU | 1–2 | 130 |

Workers are also capped by RAM (~1.2 GB each), and on a **laptop** they're held back to leave thermal
headroom; on **battery** they drop further (plug in for full speed).

## OS support matrix — complete features, per-OS engines

| Feature | Win 11/10 | Win 8/8.1 | Win 7 | Vista |
|---|:--:|:--:|:--:|:--:|
| Core search · vehicle hub · 104th sheet | ✅ | ✅ | ✅ | ✅ |
| Document viewer · HD · loupe · tilt · zoom | ✅ | ✅ | ✅ | ✅ |
| Page render engine | PyMuPDF | PyMuPDF / Poppler | PyMuPDF / Poppler | **Poppler** |
| **OCR (text recovery)** | RapidOCR PP-OCRv5 | RapidOCR / Tesseract | RapidOCR / Tesseract | **Tesseract** |
| Auto-snapshots (Task Scheduler) | ✅ | ✅ | ✅ | ✅ |
| GPU *acceleration* (speed only) | ✅ | — | — | — |

Every feature works on every listed OS — only the **engine** changes. GPU acceleration is the lone
Win10+ extra (it makes OCR faster; it isn't required to finish OCR).

**Legacy toolchain (Win7 / Vista):**
- **Python:** Win7 → use **Python 3.8** (last to support it). Vista → **Python 3.4**, or simply run a
  **pre-built index** (the portable build) since search/viewer/104th need only the standard library.
- **Page render:** install **Poppler for Windows** and add its `bin\` to PATH — the viewer auto-uses
  `pdftoppm` when PyMuPDF can't be installed.
- **OCR:** install **Tesseract-OCR for Windows** (or OCR once on a newer PC and copy the finished index).
- The probe detects these (`render_backend`, `ocr_backend` in the profile) and tells you what's missing.

## Your machine — Acer Nitro 5

The Nitro 5 line ships with an **NVIDIA GPU** (GTX 1650 → RTX 30/40-series), 6–8 core CPU, 8–32 GB RAM,
and Win10/11 — so it lands in the **GPU laptop** tier: hardware-accelerated PP-OCRv5, ~5 feeder workers
(thermal headroom), 220 dpi. For the long OCR run:

1. **Plug into AC power** and keep vents clear (cooling pad / NitroSense fans high) — the probe tunes
   workers to avoid throttling, but airflow still helps.
2. Run `engine\run_ocr_auto.bat` — it probes, installs the GPU stack, and runs to 100% unattended.
3. `python engine\gpu_check.py` confirms the GPU path is active.

The exact numbers (cores/RAM/GPU model) are read from *your* unit by the probe — it adapts to whatever
your specific Nitro 5 configuration is.
