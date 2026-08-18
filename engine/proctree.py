#!/usr/bin/env python3
"""THE VIEWER -- shared process-tree helpers.

Extracted from engine/ocr_supervisor.py's _kill_tree(proc, wait_after=15) and the inline kill
logic inside engine/tools/run_timeout.py's main() (both were mechanically identical: taskkill
/F /T /PID <pid> on Windows with stdout/stderr suppressed, proc.kill() as the POSIX fallback and
as a fallback-of-fallback if the Windows branch itself raises, then a final proc.wait(timeout=...)
wrapped in try/except-pass) -- along with the CREATE_NEW_PROCESS_GROUP process-group setup both
files duplicated at their Popen() call sites. Callers keep printing their own distinct log banners
immediately before calling kill_tree(); logging is intentionally NOT baked into this module so each
caller's message stays exactly as it was.

Stdlib only; Windows-focused (taskkill /F /T) with a POSIX fallback (proc.kill()).
"""
import os
import subprocess


def new_process_group_flags():
    """Popen(creationflags=...) value for a Windows process's own process group, so a later
    taskkill /T can reap its children too. 0 (no-op) on POSIX."""
    if os.name == "nt":
        return getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    return 0


def kill_tree(proc, wait_after=15):
    """Force-kill proc's whole process tree, then wait up to `wait_after` seconds for it to
    actually die. Shared by ocr_supervisor.py (stale-heartbeat path and KeyboardInterrupt handler)
    and engine/tools/run_timeout.py (timeout handler) -- previously each hand-rolled its own copy
    of this."""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            proc.kill()
    except Exception:
        try: proc.kill()
        except Exception: pass
    try:
        proc.wait(timeout=wait_after)
    except Exception:
        pass


# END OF FILE
