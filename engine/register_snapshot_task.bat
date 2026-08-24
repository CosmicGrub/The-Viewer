@echo off
REM ============================================================
REM  THE VIEWER -- register automatic safeguard tasks (Windows Task Scheduler):
REM    1) a DAILY snapshot of code/docs/small sidecars (critical files, cheap, seconds not minutes)
REM    2) a WEEKLY full backup of the big index DB (viewer.db, via VACUUM INTO -- minutes, not seconds)
REM  Recommendations annex #1 (backup-dr): #1 alone does NOT protect viewer.db -- the multi-GB index
REM  that represents potentially days of OCR work is only copied by a snapshot when --with-db is
REM  passed, which the daily task deliberately does NOT do (daily VACUUM INTO of a multi-GB DB is
REM  expensive for the ~2-day retention `snapshot --with-db`'s own rotation would buy). Weekly is the
REM  right cadence for that cost; #2 below is the fix -- without it, viewer.db was never backed up by
REM  anything this task registers.
REM  Re-run to update either task; use /remove to delete BOTH.
REM    register_snapshot_task.bat            -> create/update both tasks
REM    register_snapshot_task.bat /remove    -> remove both tasks
REM ============================================================
setlocal
set "TASK=THE_VIEWER_DailySnapshot"
set "DBTASK=THE_VIEWER_WeeklyDBBackup"
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( echo [ERROR] Python 3 not found on PATH.& pause & goto :eof )

if /I "%~1"=="/remove" (
  schtasks /Delete /TN "%TASK%" /F
  schtasks /Delete /TN "%DBTASK%" /F
  echo Removed scheduled tasks "%TASK%" and "%DBTASK%".
  pause & goto :eof
)

set "SG=%~dp0safeguard.py"
REM Snapshot then verify; quoting handles spaces in the path.
set "ACTION=cmd /c \"%PY% \"\"%SG%\"\" snapshot --label daily ^&^& %PY% \"\"%SG%\"\" verify\""
schtasks /Create /TN "%TASK%" /TR "%ACTION%" /SC DAILY /ST 06:00 /F
if %ERRORLEVEL%==0 (
  echo.
  echo Registered "%TASK%": a snapshot + verify runs daily at 06:00.
  echo   View it:   schtasks /Query /TN "%TASK%"
  echo   Run now:   schtasks /Run   /TN "%TASK%"
) else (
  echo [WARN] Could not register the daily task ^(admin rights may be required^). You can still snapshot manually with run_safeguard.bat.
)

REM Weekly full-DB backup: Sunday 03:00, off-peak from the daily 06:00 snapshot+verify above.
REM --auto also prunes old code/docs snapshots (gc --keep 10) in the same run.
set "DBACTION=%PY% \"%SG%\" backupdb --auto"
schtasks /Create /TN "%DBTASK%" /TR "%DBACTION%" /SC WEEKLY /D SUN /ST 03:00 /F
if %ERRORLEVEL%==0 (
  echo.
  echo Registered "%DBTASK%": a full viewer.db backup runs weekly, Sunday at 03:00.
  echo   View it:   schtasks /Query /TN "%DBTASK%"
  echo   Run now:   schtasks /Run   /TN "%DBTASK%"
  echo   Backups land in backups\db\ -- newest 2 copies kept ^(run_backupdb.bat to run by hand^).
) else (
  echo [WARN] Could not register the weekly DB-backup task ^(admin rights may be required^). You can still back up viewer.db manually with run_backupdb.bat.
)

echo.
echo Remove both:  register_snapshot_task.bat /remove
pause
endlocal
