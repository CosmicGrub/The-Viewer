@echo off
setlocal
set "OUT=%~dp0index\diag_procs.txt"
echo === who is listening on 8765 === > "%OUT%"
netstat -ano | findstr :8765 >> "%OUT%"
echo. >> "%OUT%"
echo === all python processes (PID + full command line) === >> "%OUT%"
wmic process where "name='python.exe' or name='pythonw.exe'" get ProcessId,CommandLine /format:list >> "%OUT%" 2>>&1
echo. >> "%OUT%"
echo === cmd windows running our bats (watchdog?) === >> "%OUT%"
wmic process where "name='cmd.exe'" get ProcessId,CommandLine /format:list >> "%OUT%" 2>>&1
echo Saved to %OUT%
type "%OUT%"
endlocal
