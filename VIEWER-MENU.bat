@echo off
setlocal enableextensions
REM ============================================================================================
REM  THE VIEWER -- one menu for every common task. Double-click this instead of hunting for the
REM  right .bat. Each choice just calls the matching script. Safe to re-run.
REM  NOTE: keep Windows (CRLF) line endings.
REM ============================================================================================
cd /d "%~dp0"
:menu
cls
echo ================= THE VIEWER =================
echo   SETUP
echo    1. Install / update Python dependencies   (INSTALL.bat)
echo    2. Project doctor -- deps + corpus check   (DOCTOR.bat)
echo.
echo   RUN
echo    3. Launch THE VIEWER                        (RUN-VIEWER.bat)
echo    4. First-run setup + launch                 (FIRST-RUN.bat)
echo.
echo   VERIFY
echo    5. Full verification suite                  (VERIFY-099.bat)
echo.
echo   BUILD THE DATA  (run in this order)
echo    6. Resume / continue OCR                    (RESUME-OCR.bat)
echo    7. Build measurements sidecar               (BUILD-MEASURES.bat)
echo    8. Build tables sidecar                     (BUILD-TABLES.bat)
echo    9. Enrich from the web ^(online^)             (ENRICH.bat)
echo   10. Build the Masterfile                     (BUILD-MASTERFILE.bat)
echo   11. Build the knowledge graph                (BUILD-KG.bat)
echo   12. Find duplicate/edition documents         (DEDUP.bat)
echo   13. Bulk-ingest a folder of manuals           (BULK-INGEST.bat)
echo.
echo   CHECK
echo   14. Audit routes/scripts/reachability        (AUDIT.bat)
echo.
echo   15. Browse every other tool in this folder...
echo    0. Exit
echo =============================================
set "c="
set /p "c=Choose a number, then press Enter: "
if "%c%"=="1"  call "INSTALL.bat"
if "%c%"=="2"  call "DOCTOR.bat"
if "%c%"=="3"  call "RUN-VIEWER.bat"
if "%c%"=="4"  call "FIRST-RUN.bat"
if "%c%"=="5"  call "VERIFY-099.bat"
if "%c%"=="6"  call "RESUME-OCR.bat"
if "%c%"=="7"  call "BUILD-MEASURES.bat"
if "%c%"=="8"  call "BUILD-TABLES.bat"
if "%c%"=="9"  call "ENRICH.bat"
if "%c%"=="10" call "BUILD-MASTERFILE.bat"
if "%c%"=="11" call "BUILD-KG.bat"
if "%c%"=="12" call "DEDUP.bat"
if "%c%"=="13" call "BULK-INGEST.bat"
if "%c%"=="14" call "AUDIT.bat"
if "%c%"=="15" goto allbats
if "%c%"=="0"  goto :eof
echo.
goto menu

:allbats
REM Recommendations annex #15 (architecture-reachability): this list is generated from the actual
REM *.bat files in this folder every time the menu runs, not hand-maintained -- the curated numbered
REM list above already covers the common workflow (11-19%% of the repo's .bat files by hand-picked
REM choice), but a HAND-MAINTAINED "everything else" list would just recreate the same coverage-drift
REM problem this whole fix exists to close (a new root .bat silently never appearing here). This
REM block can't drift: it always reflects what's actually on disk.
cls
echo ================= EVERY TOOL IN THIS FOLDER =================
for %%F in (*.bat) do echo    %%F
echo ===============================================================
echo   Type a filename exactly as shown above ^(e.g. AUDIT.bat^), or press Enter to go back.
set "bf="
set /p "bf=Run which .bat? "
if "%bf%"=="" goto menu
if exist "%bf%" (call "%bf%") else (echo [not found: %bf%] & pause)
goto menu
