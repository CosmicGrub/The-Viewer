@echo off
REM Post-restructure health check: core suites + the new integration test, against the real v0.98 tree.
cd /d "%~dp0engine"
set LOG=..\docs\verify_v098.log
(
echo === v0.98 verification  %DATE% %TIME% ===
echo.
echo --- syntax: thin shell + features package ---
python -c "import ast,glob; [ast.parse(open(f,encoding='utf-8').read()) for f in ['viewer_app.py']+glob.glob('features/*.py')]; print('shell + features/*.py parse OK')"
echo.
echo --- regression suites ---
python tests\test_features.py            && echo [test_features PASS]
python tests\test_features_integration.py && echo [test_features_integration PASS]
python tests\test_routes.py              && echo [test_routes PASS]
python tests\test_search_quality.py      && echo [test_search_quality PASS]
python tests\test_hardening.py           && echo [test_hardening PASS]
) > "%LOG%" 2>&1
echo Done. Wrote %LOG%
type "%LOG%"
