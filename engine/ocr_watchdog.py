#!/usr/bin/env python3
"""THE VIEWER -- OCR stall watchdog.  Stdlib-only, RPS-safe.

The OCR runner writes index/ocr_heartbeat.txt every few seconds while a pass is working. This reads it
and reports how long since the last progress: a fresh heartbeat = healthy; a stale one while the runner
is still open = a hung pass that should be restarted. (The auto-runner already restarts a pass that
*ends* early; this catches one that *hangs*.)

  python ocr_watchdog.py [--db PATH] [--max-age SEC]    # report; exit 0 = ok/idle, 2 = stalled
"""
import os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

def _hb_path(db):
    d = os.path.dirname(os.path.abspath(db)) if db else os.path.join(ROOT, "index")
    return os.path.join(d, "ocr_heartbeat.txt")

def main():
    db = os.path.join(ROOT, "index", "viewer.db"); max_age = 600
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--db" and i + 1 < len(args): db = args[i + 1]
        if a == "--max-age" and i + 1 < len(args):
            try: max_age = int(args[i + 1])
            except Exception: pass
    p = _hb_path(db)
    if not os.path.exists(p):
        print("no heartbeat file yet (%s) -- OCR hasn't started a pass." % p)
        return 0
    age = time.time() - os.path.getmtime(p)
    try: line = open(p).read().strip()
    except Exception: line = "(unreadable)"
    print("last OCR heartbeat %.0fs ago:  %s" % (age, line))
    if age > max_age:
        print("[STALL] no OCR progress for %.0fs (> %ds). If run_ocr_auto is still open, the pass may be"
              " hung -- close that window and re-run run_ocr_auto.bat (it resumes safely)." % (age, max_age))
        return 2
    print("OK -- OCR is progressing.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
