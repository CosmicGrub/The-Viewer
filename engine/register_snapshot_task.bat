@echo off
REM ============================================================
REM  THE VIEWER -- register a DAILY automatic safeguard snapshot (Windows Task Scheduler).
REM  Runs engine\safeguard.py snapshot every day at 06:00 so your critical files are protected
REM  without you remembering. Re-run to update; use /remove to delete the task.
REM    register_snapshot_task.bat            -> create/update the daily task
REM    register_snapshot_task.bat /remove    -> remove the task
REM ============================================================
setlocal
set "TASK=THE_VIEWER_DailySnapshot"
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( echo [ERROR] Python 3 not found on PATH.& pause & goto :eof )

if /I "%~1"=="/remove" (
  schtasks /Delete /TN "%TASK%" /F
  echo Removed scheduled task "%TASK%".
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
  echo   Remove:    register_snapshot_task.bat /remove
) else (
  echo [WARN] Could not register the task ^(admin rights may be required^). You can still snapshot manually with run_safeguard.bat.
)
pause
endlocal
