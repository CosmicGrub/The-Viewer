#!/usr/bin/env python3
"""
THE VIEWER -- build the Lite / portable package.

Assembles a self-contained "THE VIEWER PORTABLE" folder you can copy to another
(even weak) PC: the app, the FINISHED index (viewer.db), one-click SETUP.bat, and
both-mode CPU launchers (search by default; can also crawl/OCR slowly if needed).

Run on the machine that has the built index (your GPU/production box):
    python make_portable.py            # creates ..\..\THE VIEWER PORTABLE
    python make_portable.py "D:\Out"   # custom destination
"""
import os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))           # THE VIEWER
INDEX = os.path.join(ROOT, "index", "viewer.db")

SETUP_BAT = r"""@echo off
REM THE VIEWER (Lite) -- one-time setup. Installs the few CPU packages.
setlocal
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( echo [ERROR] Install Python 3 from python.org or the Microsoft Store, then re-run.& pause & exit /b )
echo Upgrading pip (so package installs never fail)...
%PY% -m pip install --upgrade pip
echo Installing THE VIEWER (Lite) packages (PyMuPDF, RapidOCR, reportlab)...
%PY% -m pip install --user pymupdf rapidocr-onnxruntime reportlab
echo.
echo Setup complete. Double-click START.bat to open THE VIEWER.
pause
endlocal
"""

START_BAT = r"""@echo off
REM Open THE VIEWER (Lite) search app in your browser.
call "%~dp0engine\run_app.bat"
"""

RUN_OCR_LITE = r"""@echo off
REM ============================================================
REM  THE VIEWER (Lite) -- OCR pass for this portable copy. Optional, resumable.
REM
REM  Used to run its own hardcoded `ocrall --workers 2 --dpi 150` pass -- fixed
REM  "safe for any weak PC" numbers guessed at build time on the GPU production
REM  box, not measured on whatever PC this portable copy actually lands on.
REM  run_ocr_auto.bat (plus sysprobe.py/rps.py it depends on) ships into every
REM  build unmodified, and already probes the real machine at runtime --
REM  workers/dpi/gpu/battery-throttling all self-corrected -- so this is now a
REM  thin wrapper that delegates to it instead of drifting out of sync as a
REM  second hardcoded copy. Same familiar double-click entry point
REM  (run_ocr_lite.bat); the plan it prints just reflects this PC's actual
REM  capability (including using a GPU here too, if one turns out to be
REM  available) rather than a worst-case guess.
REM ============================================================
cd /d "%~dp0"
call "%~dp0run_ocr_auto.bat"
"""

README = """THE VIEWER -- Lite / Portable build
====================================

This folder is self-contained. Copy it to any Windows PC and use it.

FIRST TIME ON A NEW PC
  1. Make sure Python 3 is installed (python.org or Microsoft Store).
  2. Double-click  SETUP.bat   (installs a few packages, one time).
  3. Double-click  START.bat   to open the search app in your browser.

WHAT'S INSIDE
  index\\viewer.db      The finished search index (already built -- no processing needed to search).
  engine\\              The app + tools.
  SETUP.bat            One-time package install.
  START.bat            Launch the search + document viewer + parts-request app.

BOTH MODES
  - Search-only (default): just use START.bat. Everything is already indexed; nothing heavy runs.
  - Full (optional, slow on weak PCs):
      engine\\run_indexing.bat   crawl/extract new files you add to the corpus
      engine\\run_ocr_lite.bat   OCR scanned pages (auto-tunes threads/DPI/GPU to THIS pc) -- resumable

NOTES
  - Fully offline. No internet needed after SETUP.
  - If you add new manuals, point engine\\run_indexing.bat at their folder (edit VIEWER_ROOT inside it).
  - The heavy GPU build lives on the production machine; this Lite build is for portability.
"""

def main():
    dest = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(ROOT), "THE VIEWER PORTABLE")
    print("Building portable package at:", dest)
    eng_dest = os.path.join(dest, "engine")
    os.makedirs(os.path.join(dest, "index"), exist_ok=True)
    # copy engine (skip caches, GPU-only launcher, and the portable builder itself)
    skip = {"__pycache__", "run_ocr_gpu.bat", "make_portable.py", "make_portable.bat",
            "ocr_diag.py", "diag_ocr.bat"}
    if os.path.exists(eng_dest): shutil.rmtree(eng_dest)
    shutil.copytree(HERE, eng_dest, ignore=lambda d, names: [n for n in names if n in skip or n.endswith(".pyc")])
    # write the lite OCR launcher
    open(os.path.join(eng_dest, "run_ocr_lite.bat"), "w").write(RUN_OCR_LITE)
    # copy the finished index
    if os.path.exists(INDEX):
        size = os.path.getsize(INDEX) / 1e9
        print(f"Copying index ({size:.2f} GB) -- this can take a minute...")
        shutil.copy2(INDEX, os.path.join(dest, "index", "viewer.db"))
    else:
        print("[WARN] index/viewer.db not found -- the portable build will have no data until you index.")
    # top-level setup + launchers + readme
    open(os.path.join(dest, "SETUP.bat"), "w").write(SETUP_BAT)
    open(os.path.join(dest, "START.bat"), "w").write(START_BAT)
    open(os.path.join(dest, "README.txt"), "w").write(README)
    print("DONE. Portable build ready:", dest)
    print("Copy that whole folder to the other PC, run SETUP.bat once, then START.bat.")

if __name__ == "__main__":
    main()
