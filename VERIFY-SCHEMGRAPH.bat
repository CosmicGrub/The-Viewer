@echo off
REM Quick host-side check of build_schemgraph on a bounded slice of the real corpus -> log.
cd /d "%~dp0engine"
set "LOG=..\docs\schemgraph_verify.log"
> "%LOG%" echo === build_schemgraph --limit 200 check  %DATE% %TIME% ===
python build_schemgraph.py --limit 200 --workers 8 >> "%LOG%" 2>&1
echo. >> "%LOG%"
echo --- coverage tail (last 12 schematic pages found) --- >> "%LOG%"
powershell -NoProfile -Command "if (Test-Path '..\index\schemgraph_coverage.tsv') { Get-Content '..\index\schemgraph_coverage.tsv' | Select-Object -Last 12 } else { 'no coverage file' }" >> "%LOG%" 2>&1
echo Done. Wrote %LOG%
type "%LOG%"
