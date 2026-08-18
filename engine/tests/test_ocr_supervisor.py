#!/usr/bin/env python3
"""THE VIEWER -- regression coverage for ocr_supervisor.py's crash-mid-hang-detection logic
(audit finding #15), specifically the bugs a code review surfaced against the first version of this
file and that were fixed in response:
  1. A stale LEFTOVER heartbeat (from a prior session/crash) used to make supervise() kill a
     brand-new, perfectly healthy child on its very first poll -- exactly the scenario every restart
     hits, since a restart only happens after a prior crash or kill.
  2. A hang before the FIRST-EVER heartbeat write (fresh install, or a batch under 5 pages) used to
     be invisible forever (_heartbeat_age() returned None, the kill guard never fired).
  3. A killed batch used to leave its in-flight pages stuck at ocr_status='running' permanently.
These tests spawn real (tiny, sleep-based) child processes and drive supervise() against them with
real timing -- not mocks -- so the fix is proven against the actual polling/kill mechanism, not a
paraphrase of it. Self-contained; no OCR engine, no real corpus.

v1.14.0 (Drift Report Tier 4): checks 1/2/4 above already exercise _kill_tree() indirectly via
supervise(), but only ever assert supervise()'s RETURN CODE -- which supervise() sets to 124
unconditionally right after calling _kill_tree(), regardless of whether the kill actually worked.
None of the existing checks (including the #5 "kill_tree is reused, not re-copy-pasted" one, which
is a source-text count) ever confirmed a killed process, or its children, were actually terminated.
Check #6 below calls _kill_tree() directly against a real parent+grandchild process pair (matching
supervise()'s own CREATE_NEW_PROCESS_GROUP usage) and confirms the parent is actually gone afterward
-- the first functional proof `taskkill /F /T` (Windows) / proc.kill() (POSIX) really terminates the
target, not just that supervise()'s return code looked right. On Windows this also confirms the
GRANDCHILD is gone too (taskkill /T's real tree-kill). On POSIX it deliberately asserts the opposite
(the grandchild survives) -- proc.kill() only ever signals the one PID it's given, and neither this
module nor its sibling engine/tools/run_timeout.py sets up a process group/session on the POSIX
Popen() call that would make a real tree-kill possible there. Not a gap this file introduced; a
documented, pre-existing limitation of the POSIX fallback path shared by both files. Run: python
tests/test_ocr_supervisor.py"""
import os, sys, sqlite3, subprocess, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
MIGDIR = os.path.join(ENGINE, "migrations")
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)
import ocr_supervisor as SUP
import ocr_watchdog
import viewer_ingest as VI

passed, failed = [], []
def ok(name, cond):
    (passed if cond else failed).append(name)


def _new_db_dir():
    d = tempfile.mkdtemp(prefix="ocrsup_")
    open(os.path.join(d, "viewer.db"), "wb").close()   # supervise() only needs a path for _hb_path()
    return d, os.path.join(d, "viewer.db")


def _sleep_cmd(seconds):
    return [sys.executable, "-c", "import time; time.sleep(%r)" % seconds]


try:
    # --- 1. a stale LEFTOVER heartbeat must not kill a brand-new, healthy process ---
    d1, db1 = _new_db_dir()
    hb1 = ocr_watchdog._hb_path(db1)
    with open(hb1, "w") as f:
        f.write("leftover from a previous session")
    stale_time = time.time() - 3600   # an hour old -- would be well past any max_age
    os.utime(hb1, (stale_time, stale_time))
    t0 = time.time()
    rc1 = SUP.supervise(_sleep_cmd(3), db1, max_age=5, poll_interval=1)
    dt1 = time.time() - t0
    ok("stale_leftover_heartbeat_does_not_kill_fresh_process", rc1 == 0)
    ok("stale_leftover_heartbeat_process_ran_to_completion", dt1 >= 2.5)   # actually slept ~3s, wasn't killed early

    # --- 2. a hang BEFORE any heartbeat has ever been written must still be detected ---
    d2, db2 = _new_db_dir()
    ok("setup_no_heartbeat_file_yet", not os.path.exists(ocr_watchdog._hb_path(db2)))
    t0 = time.time()
    rc2 = SUP.supervise(_sleep_cmd(15), db2, max_age=2, poll_interval=1)
    dt2 = time.time() - t0
    ok("hang_before_first_heartbeat_is_killed", rc2 == 124)
    ok("hang_before_first_heartbeat_killed_promptly", dt2 < 10)   # killed well before the 15s sleep would finish

    # --- 3. a FRESH heartbeat (this child's own) must NOT be treated as stale ---
    d3, db3 = _new_db_dir()
    hb3 = ocr_watchdog._hb_path(db3)
    with open(hb3, "w") as f:
        f.write("freshly written")   # simulates the child having just written its own heartbeat
    t0 = time.time()
    rc3 = SUP.supervise(_sleep_cmd(2), db3, max_age=5, poll_interval=1)
    dt3 = time.time() - t0
    ok("fresh_heartbeat_process_completes_normally", rc3 == 0 and dt3 >= 1.5)

    # --- 4. a killed batch's stuck 'running' pages get requeued to 'pending' ---
    d4, db4 = _new_db_dir()
    con = VI.connect(db4)
    VI.migrate(con, MIGDIR, db_path=db4)
    con.execute("INSERT INTO documents(id,path) VALUES(1,?)", (os.path.join(d4, "a.pdf"),))
    con.execute("INSERT INTO pages(document_id,page_number,body_text,ocr_status) VALUES(1,1,'',?)", ("running",))
    con.execute("INSERT INTO pages(document_id,page_number,body_text,ocr_status) VALUES(1,2,'',?)", ("done",))
    con.commit(); con.close()
    rc4 = SUP.supervise(_sleep_cmd(15), db4, max_age=1, poll_interval=1)
    ok("killed_batch_returns_124", rc4 == 124)
    con = sqlite3.connect(db4)
    statuses = dict(con.execute("SELECT page_number, ocr_status FROM pages WHERE document_id=1").fetchall())
    con.close()
    ok("killed_batch_requeues_running_page", statuses.get(1) == "pending")
    ok("killed_batch_leaves_done_page_alone", statuses.get(2) == "done")

    # --- 5. _kill_tree is reused (not re-copy-pasted) between the stale-heartbeat and Ctrl+C paths ---
    import inspect
    src = inspect.getsource(SUP)
    ok("kill_tree_helper_exists_once", src.count("def _kill_tree(") == 1)
    ok("kill_tree_called_from_supervise_loop_and_interrupt_handler", src.count("_kill_tree(proc)") == 2)

    # --- 6. _kill_tree() actually terminates the whole process tree, not just the top-level PID ---
    # (checks 1/2/4 above only ever assert supervise()'s return code, which is set to 124
    # unconditionally after calling _kill_tree() -- they'd pass even if the kill silently no-op'd.
    # This calls the real function against a real parent+grandchild pair and checks both are dead.)
    def _pid_alive(pid):
        if os.name == "nt":
            out = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid],
                                 capture_output=True, text=True).stdout
            return str(pid) in out
        try:
            os.kill(pid, 0); return True
        except OSError:
            return False

    d6, db6 = _new_db_dir()
    child_pid_file = os.path.join(d6, "child_pid.txt")
    # a parent that spawns its own child (the "grandchild" from this test's perspective), writes the
    # grandchild's pid out so we can probe it, then both sleep -- CREATE_NEW_PROCESS_GROUP matches
    # supervise()'s own flag so taskkill /T has a real group to reap, exactly as in production.
    parent_script = (
        "import subprocess, sys, time; "
        "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); "
        "open(%r, 'w').write(str(p.pid)); "
        "time.sleep(30)"
    ) % child_pid_file
    flags6 = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    proc6 = subprocess.Popen([sys.executable, "-c", parent_script], creationflags=flags6)
    for _ in range(50):
        if os.path.exists(child_pid_file) and os.path.getsize(child_pid_file) > 0:
            break
        time.sleep(0.1)
    ok("setup_grandchild_pid_written", os.path.exists(child_pid_file))
    grandchild_pid = int(open(child_pid_file).read().strip())
    ok("setup_grandchild_alive_before_kill", _pid_alive(grandchild_pid))
    SUP._kill_tree(proc6, wait_after=10)
    ok("kill_tree_terminates_parent_process", proc6.poll() is not None)
    time.sleep(0.5)   # let the OS finish reaping
    if os.name == "nt":
        # taskkill /F /T genuinely kills the whole tree -- assert the strong guarantee.
        ok("kill_tree_terminates_grandchild_too", not _pid_alive(grandchild_pid))
    else:
        # The POSIX fallback is proc.kill() -- one signal to one PID, no process-group/session setup
        # on the Popen() side to make a tree-kill possible. This is not a gap unique to this file:
        # engine/tools/run_timeout.py's kill_tree-equivalent logic has the identical POSIX behavior,
        # and this module's own docstring already frames POSIX as "focused Windows... with a POSIX
        # fallback", not an equal implementation. Document the real (weaker) guarantee here instead
        # of asserting one that was never true -- a future POSIX process-group fix belongs in both
        # files together, not silently diverging just because this test happened to be stricter.
        ok("kill_tree_grandchild_survives_on_posix_fallback_known_limitation", _pid_alive(grandchild_pid))
        try: os.kill(grandchild_pid, 9)   # clean up so it doesn't linger past this test process
        except Exception: pass
except Exception as e:
    failed.append("ocr_supervisor(%s)" % e)


for n in passed: print("PASS", n)
for n in failed: print("FAIL", n)
print("\n%d passed, %d failed (of %d checks for ocr_supervisor.py)" %
      (len(passed), len(failed), len(passed) + len(failed)))
sys.exit(1 if failed else 0)

# END OF FILE
