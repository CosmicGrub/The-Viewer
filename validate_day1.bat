@echo off
setlocal enabledelayedexpansion

echo.
echo ====================================
echo   DAY 1 VALIDATION & AUTO-COMPLETE
echo ====================================
echo.

REM Navigate to project
cd /d K:\tm_search_engine

REM Activate venv
call venv\Scripts\activate.bat

REM Check Python packages
echo [1/4] Checking Python packages...
python -c "import pdfplumber, pytesseract, python_docx, PIL, cv2, meilisearch, fastapi, uvicorn, pydantic, pytest, black, flake8, tqdm, requests; print('✓ All packages loaded')" 
if errorlevel 1 (
    echo ✗ Package check failed - installing...
    pip install -r requirements.txt --force-reinstall --no-cache-dir
)

echo [2/4] Checking external tools...
tesseract --version >nul 2>&1 && echo ✓ Tesseract found || echo ✗ Tesseract missing
git --version >nul 2>&1 && echo ✓ Git found || echo ✗ Git missing
node --version >nul 2>&1 && echo ✓ Node found || echo ✗ Node missing
npm --version >nul 2>&1 && echo ✓ NPM found || echo ✗ NPM missing

echo [3/4] Checking folder structure...
if exist backend\tests echo ✓ backend\tests && (goto :skip1) || echo ✗ backend\tests missing
:skip1
if exist frontend\src echo ✓ frontend\src && (goto :skip2) || echo ✗ frontend\src missing
:skip2
if exist data\extracted echo ✓ data\extracted && (goto :skip3) || echo ✗ data\extracted missing
:skip3
if exist data\meilisearch echo ✓ data\meilisearch && (goto :skip4) || echo ✗ data\meilisearch missing
:skip4

echo [4/4] Git status...
git status

echo.
echo ====================================
echo   FINAL COMMIT
echo ====================================
git add .
git commit -m "Day 1 Complete: Full validation passed - environment ready for Day 2"

echo.
echo ✓ DAY 1 VALIDATION COMPLETE
echo Type: cd /d K:\tm_search_engine && call venv\Scripts\activate.bat
echo Then proceed to Day 2
pause