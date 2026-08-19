# SETUP — Lite / portable build (weaker PC)

A self-contained folder you copy to another Windows PC. Ships the finished index, so it searches
instantly; can also index/OCR slowly if you want (both modes).

## Build the portable folder (on the production box)
1. Finish (or get far enough with) indexing/OCR on the GPU machine.
2. Double-click **`engine\make_portable.bat`**.
   - Creates **`THE VIEWER PORTABLE`** next to the project (or pass a path:
     `make_portable.bat "D:\Out"`).
   - Copies the app + the finished `index\viewer.db` + a one-click `SETUP.bat`.

## Move it
- Copy the whole **`THE VIEWER PORTABLE`** folder to the other PC (USB, network, etc.).
  (Most of the size is `index\viewer.db`.)

## On the weaker PC
1. Install **Python 3** (python.org or Microsoft Store) if it isn't already.
2. Double-click **`SETUP.bat`** once — installs `pymupdf`, `rapidocr-onnxruntime`, `reportlab` (CPU).
3. Double-click **`START.bat`** — opens the search + document viewer + parts-request app in the browser.

That's it for search-only. Everything is already indexed; nothing heavy runs.

## Optional — full mode on the weak PC (slow)
- Add new manuals to a folder, edit `VIEWER_ROOT` inside `engine\run_indexing.bat`, run it to index them.
- `engine\run_ocr_lite.bat` OCRs scanned pages. It delegates to `engine\run_ocr_auto.bat`, which
  probes the actual PC (`sysprobe.py`) and picks threads/DPI/GPU for it at runtime, instead of a
  fixed low profile — so a weak PC gets a low, safe plan automatically, and a portable copy that
  happens to land on a stronger PC (or one with a working NVIDIA GPU) isn't held back by numbers
  guessed on the production box. Slow on genuinely weak hardware but resumable.

## Notes
- Fully offline after `SETUP.bat`.
- No GPU or drivers needed.
- Same data and features as the production build (search, viewer, 104th parts request).
