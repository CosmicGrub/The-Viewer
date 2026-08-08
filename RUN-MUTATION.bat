@echo off
REM ============================================================
REM  THE VIEWER -- full mutation testing (run on THIS PC)
REM  Deliberately breaks small pieces of code one at a time and
REM  checks the tests catch each break. Survivors = test blind
REM  spots. Writes index\MUTATION-RESULTS.txt.
REM ============================================================
setlocal
cd /d "%~dp0engine"
set "PY=python"
where python >nul 2>nul || set "PY=py"
set "OUT=..\index\MUTATION-RESULTS.txt"

echo THE VIEWER -- mutation testing  > "%OUT%"
echo Started %DATE% %TIME%           >> "%OUT%"
echo.

echo [1/4] Curated engine + safeguard mutations (core_pillars, safeguard)...
%PY% tests\mutation_xl.py            >> "%OUT%" 2>&1

echo [2/4] Auto-mutation: patterns.py ...
%PY% tests\mutate.py --target patterns.py        --test "%PY% tests\test_patterns.py"  --cwd . --timeout 60 >> "%OUT%" 2>&1

echo [3/4] Auto-mutation: procedure_feature.py ...
%PY% tests\mutate.py --target procedure_feature.py --test "%PY% tests\test_procedure.py" --cwd . --timeout 60 >> "%OUT%" 2>&1

echo [4/7] Auto-mutation: rps.py (legacy-mode logic) ...
%PY% tests\mutate.py --target rps.py             --test "%PY% tests\test_features.py"  --cwd . --timeout 90 >> "%OUT%" 2>&1

echo [5/7] Auto-mutation: figureparts.py (test_jobcard as oracle) ...
%PY% tests\mutate.py --target figureparts.py     --test "%PY% tests\test_jobcard.py"   --cwd . --timeout 60 >> "%OUT%" 2>&1

echo [6/7] Auto-mutation: jobcard.py (test_jobcard as oracle) ...
%PY% tests\mutate.py --target jobcard.py         --test "%PY% tests\test_jobcard.py"   --cwd . --timeout 90 >> "%OUT%" 2>&1

echo [7/7] Auto-mutation: coverage.py (property fuzz as oracle) ...
%PY% tests\mutate.py --target coverage.py        --test "%PY% tests\test_property_fuzz.py 1500" --cwd . --timeout 120 >> "%OUT%" 2>&1

echo.>> "%OUT%"
echo Finished %DATE% %TIME% >> "%OUT%"
echo.
echo Done. Results saved to index\MUTATION-RESULTS.txt -- opening it.
start "" notepad "%OUT%"
echo Copy the SUMMARY lines back to Claude if you want them reviewed.
pause
endlocal
