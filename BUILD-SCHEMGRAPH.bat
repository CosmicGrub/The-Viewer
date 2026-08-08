@echo off
REM Precompute Living-Schematic netlists for every vector schematic page -> index\schemcache\ + coverage TSV.
REM Resumable + parallel. Read-only on the index (R1). Safe to re-run; stop with Ctrl+C and resume anytime.
cd /d "%~dp0engine"
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( echo [ERROR] Python 3 not found on PATH.& pause & goto :eof )
echo Building schematic netlists (this scans PDF pages for vector wiring; resumable)...
%PY% build_schemgraph.py %*
echo.
echo Coverage report: index\schemgraph_coverage.tsv
pause
