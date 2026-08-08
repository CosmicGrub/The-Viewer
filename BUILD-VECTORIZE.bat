@echo off
REM Pre-vectorize every figure-bearing page -> crisp cached SVGs (index\veccache) + coverage TSV.
REM Resumable + parallel. Read-only on the index (R1). Needs OpenCV (ships with the OCR stack).
cd /d "%~dp0engine"
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( echo [ERROR] Python 3 not found on PATH.& pause & goto :eof )
echo Pre-vectorizing figure pages (resumable; Ctrl+C to stop and resume later)...
%PY% build_vectorize.py %*
echo.
echo Coverage: index\vectorize_coverage.tsv   ·   SVGs: index\veccache\
pause
