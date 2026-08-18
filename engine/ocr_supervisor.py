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

Review findings fixed here (against the first version of this file):
  * A leftover ocr_heartbeat.txt from a PRIOR run/session never gets reset when a NEW child starts,
    and viewer_ingest.py only refreshes it every 5 completed pages or at batch end -- so every
    restart (which only happens after a prior crash/kill, i.e. exactly when the leftover heartbeat
    is already stale) was getting immediately re-killed on the very first poll, before the new,
    healthy child had any chance to write its own heartbeat. Fixed by tracking this process's own
    start time as a baseline "sign of life" -- a heartbeat file only counts as evidence THIS child
    is alive if it was written AFTER this child started; otherwise staleness is measured from
    proc_start, which also means a hang before the first-ever heartbeat write is now correctly
    detected too (same fix covers both bugs).
  * A killed batch used to leave its in-flight pages stuck at ocr_status='running' forever (only
    `cleanup` resets those, and run_ocr_auto.bat only calls it once, before the loop begins) --
    fixed by requeuing them to 'pending' immediately after a kill, best-effort, so the next restart
    picks them back up instead of silently losing them.

Usage:
    python ocr_supervisor.py --db PATH [--max-age SEC] [--poll SEC] -- <command> [args...]

Stdlib only; Windows-focused (taskkill /F /T) with a POSIX fallback (proc.kill()).
"""
import argparse
import os
import sqlite3
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ocr_watchdog  # noqa: E402  -- reuse its exact heartbeat-path logic, not a reimplementation
import proctree  # noqa: E402  -- shared process-tree kill/flags logic (also used by tools/run_timeout.py)


def _heartbeat_mtime(db_path):
    """mtime of the OCR heartbeat file, or None if it doesn't exist yet."""
    p = ocr_watchdog._hb_path(db_path)
    try:
        return os.path.getmtime(p)
    except OSError:
        return None


def _kill_tree(proc, wait_after=15):
    """Force-kill proc's whole process tree (same mechanism run_timeout.py uses), then wait up to
    `wait_after` seconds for it to actually die. Used from both the stale-heartbeat path and the
    KeyboardInterrupt handler below -- previously each hand-rolled its own copy of this; now both
    this module and engine/tools/run_timeout.py delegate to the shared engine/proctree.py."""
    proctree.kill_tree(proc, wait_after=wait_after)


def _requeue_stuck_pages(db_path):
    """Best-effort: after killing a batch mid-flight, its pages are left at ocr_status='running'
    (ocr() bulk-marks a whole batch 'running' up front, per-page rows only flip to 'done'/'failed'
    on completion) -- requeue them to 'pending' so the very next restart picks them back up instead
    of silently dropping them from every future OCR pass until someone remembers to run
    `viewer_ingest.py cleanup` by hand. Mirrors cleanup()'s own reset logic (viewer_ingest.py)."""
    try:
        con = sqlite3.connect(db_path, timeout=30)
        try:
            n = con.execute("UPDATE pages SET ocr_status='pending' WHERE ocr_status='running'").rowcount
            con.commit()
            if n:
                sys.stderr.write("ocr_supervisor: requeued %d page(s) stuck 'running' by the kill\n" % n)
        finally:
            con.close()
    except Exception as e:
        sys.stderr.write("ocr_supervisor: could not requeue stuck pages after kill (%s)\n" % e)


def supervise(cmd, db_path, max_age, poll_interval):
    proc = subprocess.Popen(cmd, creationflags=proctree.new_process_group_flags())
    proc_start = time.time()
    print("ocr_supervisor: watching PID %d (heartbeat max-age %ds, polling every %ds)"
          % (proc.pid, max_age, poll_interval))

    try:
        while True:
            try:
                return proc.wait(timeout=poll_interval)
            except subprocess.TimeoutExpired:
                pass
            hb_mtime = _heartbeat_mtime(db_path)
            # "Last sign of life": the heartbeat file only counts if THIS child could have written
            # it (mtime >= proc_start) -- a heartbeat left over from a previous session/crash is
            # exactly as stale as "no heartbeat yet" and must never be read as current progress.
            last_sign_of_life = hb_mtime if (hb_mtime is not None and hb_mtime >= proc_start) else proc_start
            age = time.time() - last_sign_of_life
            if age > max_age:
                sys.stdout.flush()
                sys.stderr.write(
                    "\n!!! ocr_supervisor: no OCR progress for %.0fs (> %ds) -- killing hung pass "
                    "(PID %d) and letting run_ocr_auto.bat's restart loop pick it back up !!!\n"
                    % (age, max_age, proc.pid))
                _kill_tree(proc)
                _requeue_stuck_pages(db_path)
                return 124   # same sentinel run_timeout.py uses for "killed after a timeout"
    except KeyboardInterrupt:
        _kill_tree(proc)
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
