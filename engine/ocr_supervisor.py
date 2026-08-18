#!/usr/bin/env python3
"""THE VIEWER -- OCR hang supervisor (finding #15). Connects two already-existing, already-tested
pieces that were never wired together: ocr_watchdog.py's heartbeat-staleness detector, and the
kill-the-whole-tree mechanism engine/tools/run_timeout.py already uses for the same class of
problem (a single hung step must never stall a run forever).

run_ocr_auto.bat's own `:ocrloop` already restarts a pass that *ends* early (crash/normal exit,
nonzero pending -> `goto ocrloop`) -- its banner comment ("auto-restarting if it ever crashes") was
only ever true for that case. A pass that *hangs* (viewer_ingest.py ocrall never returns) blocks
that same `cmd.exe` loop forever: nothing detects it, nothing kills it, nothing restarts it.

This wraps the `ocrall` command: launch it, then instead of a single blocking wait, poll on an
interval and check ocr_heartbeat.txt's staleness (the same file/logic ocr_watchdog.py already
uses -- imported directly, not shelled out to). If the heartbeat goes stale while the child is
still alive, kill the whole process tree (taskkill /F /T, same mechanism run_timeout.py uses) and
exit non-zero -- run_ocr_auto.bat's existing `:ocrloop` restart-on-nonzero-pending logic then picks
it back up on its own. On normal completion (or a real crash), this just returns the child's exit
code, so `%PY% ocr_supervisor.py ... -- viewer_ingest.py ocrall ...` behaves like a drop-in
replacement for calling `ocrall` directly.

Usage:
    python ocr_supervisor.py --db PATH [--max-age SEC] [--poll SEC] -- <command> [args...]

Stdlib only; Windows-focused (taskkill /F /T) with a POSIX fallback (proc.kill()).
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ocr_watchdog  # noqa: E402  -- reuse its exact heartbeat-path/staleness logic, not a reimplementation


def _heartbeat_age(db_path):
    """Seconds since the last OCR heartbeat, or None if no heartbeat file exists yet (OCR hasn't
    started a pass -- not stale, just not started)."""
    p = ocr_watchdog._hb_path(db_path)
    if not os.path.exists(p):
        return None
    return time.time() - os.path.getmtime(p)


def supervise(cmd, db_path, max_age, poll_interval):
    flags = 0
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)  # own process group so taskkill /T can reap children
    proc = subprocess.Popen(cmd, creationflags=flags)
    print("ocr_supervisor: watching PID %d (heartbeat max-age %ds, polling every %ds)"
          % (proc.pid, max_age, poll_interval))

    try:
        while True:
            try:
                return proc.wait(timeout=poll_interval)
            except subprocess.TimeoutExpired:
                pass
            age = _heartbeat_age(db_path)
            if age is not None and age > max_age:
                sys.stdout.flush()
                sys.stderr.write(
                    "\n!!! ocr_supervisor: no OCR progress for %.0fs (> %ds) -- killing hung pass "
                    "(PID %d) and letting run_ocr_auto.bat's restart loop pick it back up !!!\n"
                    % (age, max_age, proc.pid))
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
                    proc.wait(timeout=15)
                except Exception:
                    pass
                return 124   # same sentinel run_timeout.py uses for "killed after a timeout"
    except KeyboardInterrupt:
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                proc.kill()
        except Exception:
            pass
        raise


def main():
    ap = argparse.ArgumentParser(usage="%(prog)s --db PATH [--max-age SEC] [--poll SEC] -- <command> [args...]")
    ap.add_argument("--db", required=True)
    ap.add_argument("--max-age", type=int, default=600)
    ap.add_argument("--poll", type=int, default=30)
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    args = ap.parse_args()
    cmd = args.cmd[1:] if args.cmd and args.cmd[0] == "--" else args.cmd
    if not cmd:
        ap.error("no command given after --")
    return supervise(cmd, args.db, args.max_age, args.poll)


if __name__ == "__main__":
    sys.exit(main())

# END OF FILE
