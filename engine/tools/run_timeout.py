#!/usr/bin/env python3
"""run_timeout.py -- run a command with a hard wall-clock timeout so a single hung step can never stall
VERIFY-099 for hours. Usage:  python run_timeout.py <seconds> <program> [args...]

It launches the child, lets its output stream straight through, and if the child has not finished within
<seconds> it kills the whole child process tree and exits 124 with a clear banner. On normal completion it
returns the child's own exit code, so `&& echo [PASS]` chains behave exactly as before. Stdlib only; ASCII
output (cp1252-safe console); works on Windows and POSIX."""
import os
import subprocess
import sys


def main():
    if len(sys.argv) < 3:
        sys.stderr.write("usage: run_timeout.py <seconds> <program> [args...]\n")
        return 2
    try:
        secs = float(sys.argv[1])
    except ValueError:
        sys.stderr.write("run_timeout: first argument must be a number of seconds\n")
        return 2
    cmd = sys.argv[2:]

    flags = 0
    if os.name == "nt":
        # own process group so taskkill /T can reap children (e.g. a spawned server thread/proc)
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    try:
        proc = subprocess.Popen(cmd, creationflags=flags)
    except FileNotFoundError:
        sys.stderr.write("run_timeout: command not found: %s\n" % " ".join(cmd))
        return 2

    try:
        return proc.wait(timeout=secs)
    except subprocess.TimeoutExpired:
        sys.stdout.flush()
        sys.stderr.write("\n!!! TIMEOUT after %gs -- killing hung step: %s !!!\n" % (secs, " ".join(cmd)))
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                proc.kill()
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        try:
            proc.wait(timeout=15)
        except Exception:
            pass
        return 124


if __name__ == "__main__":
    sys.exit(main())

# END OF FILE
