#!/usr/bin/env python3
"""Regression coverage for the two robustness fixes from the Masterfile comparison audit that
test_medium_fixes.py's existing streaming-equivalence/null-group tests don't cover:

  1. Atomic writes -- masterfile.py's build() used to DROP+CREATE directly against the live
     master_db with a single commit() at the end (the exact pre-fix bug kg.py's own comments
     describe fixing in itself). Now it builds via safeguard.atomic_sqlite_build(), matching
     kg.py/dedup.py: a crash/exception anywhere mid-build must leave the last-good master_db file
     completely untouched, with no stray temp file left behind.
  2. Read-side degrade contract -- for_subject()/coverage() used to have no try/except around their
     SQL, so a master_db that EXISTS but is torn/mid-build/pre-schema (a real reachable state, since
     the on-disk file always existed even before fix #1 -- and even after it, a corrupted disk write
     could still produce a garbage file) raised sqlite3.OperationalError straight out of the
     function and leaked the connection. Now both degrade to an empty result, matching kg.py's/
     dedup.py's own "sidecar not built yet / mid-build -- degrade, never 500" contract.

masterfile.py's own __main__ self-test (part of verifystate.py's SELFTEST_MODULES / VERIFY.bat's
gate-6 roster) separately proves the THIRD audit fix (numeric-median representative value) with a
real 4-value torque group -- not duplicated here.

Pure stdlib test runner."""
import glob
import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import masterfile


def _build_tiny_corpus(d):
    """One document, one real length measurement -- just enough for a real, non-empty build()."""
    dbp = os.path.join(d, "viewer.db"); mdb = os.path.join(d, "measures.db")
    a = sqlite3.connect(dbp)
    a.execute("CREATE TABLE documents(id INTEGER PRIMARY KEY, vehicle TEXT)")
    a.execute("INSERT INTO documents VALUES(1,'HMMWV')"); a.commit(); a.close()
    m = sqlite3.connect(mdb)
    m.execute("CREATE TABLE meas(doc INT,page INT,type TEXT,unit TEXT,value TEXT,value2 TEXT,tolerance TEXT,context TEXT)")
    m.execute("INSERT INTO meas VALUES(1,12,'length','in','180',NULL,NULL,'Overall length 180 in')")
    m.commit(); m.close()
    return dbp, mdb


def run():
    passed, failed = [], []
    def check(name, cond):
        (passed if cond else failed).append(name)

    d = tempfile.mkdtemp(prefix="masterfile_robustness_")
    dbp, mdb = _build_tiny_corpus(d)
    master_db = os.path.join(d, "masterfile.db")

    # ---- fix 1: atomic writes -----------------------------------------------------------------
    summ0 = masterfile.build(dbp, mdb, None, master_db)
    check("baseline build() succeeds against a fresh path", summ0["filtered"] == 1)
    check("baseline build() actually wrote the file", os.path.exists(master_db))
    baseline_bytes = open(master_db, "rb").read()
    baseline_mtime = os.path.getmtime(master_db)

    orig_canonical_core = masterfile._canonical_core
    def _boom(*a, **kw):
        raise RuntimeError("simulated mid-build crash (test_masterfile_robustness.py)")
    masterfile._canonical_core = _boom
    try:
        raised = False
        try:
            # SAME master_db path as the baseline -- this is the case that matters: does a failed
            # REBUILD corrupt/replace an already-good file, or leave it exactly as it was?
            masterfile.build(dbp, mdb, None, master_db)
        except RuntimeError:
            raised = True
        check("a mid-build exception actually propagates out of build() (not silently swallowed)", raised)
    finally:
        masterfile._canonical_core = orig_canonical_core

    after_bytes = open(master_db, "rb").read()
    after_mtime = os.path.getmtime(master_db)
    check("the ORIGINAL master_db is byte-identical after a failed rebuild attempt "
          "(the atomic swap never happened)", after_bytes == baseline_bytes)
    check("the ORIGINAL master_db's mtime is unchanged (it was never even opened for writing, "
          "only the temp file was)", after_mtime == baseline_mtime)
    stray = glob.glob(master_db + ".building-*")
    check("no stray .building-<pid> temp file left behind after the failed build", stray == [])

    # a build into a path that DOESN'T exist yet must also leave nothing behind on failure
    fresh_path = os.path.join(d, "never_existed.db")
    masterfile._canonical_core = _boom
    try:
        raised2 = False
        try:
            masterfile.build(dbp, mdb, None, fresh_path)
        except RuntimeError:
            raised2 = True
        check("a mid-build exception on a brand-new path also propagates", raised2)
    finally:
        masterfile._canonical_core = orig_canonical_core
    check("a brand-new path is never created at all if the build never completed successfully",
          not os.path.exists(fresh_path))
    check("no stray temp file for the brand-new path either", glob.glob(fresh_path + ".building-*") == [])

    # a real, un-sabotaged rebuild against the SAME path afterward must still work normally
    summ1 = masterfile.build(dbp, mdb, None, master_db)
    check("a genuine (non-sabotaged) rebuild after a prior failure still succeeds normally",
          summ1["filtered"] == 1)

    # ---- fix 2: read-side degrade contract -----------------------------------------------------
    torn_db = os.path.join(d, "torn.db")
    tcon = sqlite3.connect(torn_db)
    tcon.execute("CREATE TABLE something_unrelated(x INTEGER)")   # master_filtered/master_raw genuinely absent
    tcon.commit(); tcon.close()

    res = masterfile.for_subject(torn_db, "HMMWV")
    check("for_subject() on a torn/pre-schema db degrades to an empty result, not a raise",
          res == {"query": "HMMWV", "filtered": [], "raw": [], "counts": {}})

    cov = masterfile.coverage(torn_db)
    check("coverage() on a torn/pre-schema db degrades to an empty list, not a raise", cov == [])

    # a genuinely missing file still behaves the same as before (the os.path.exists() gate was
    # already correct pre-fix -- confirming it still is, now that a try/except sits around it too)
    missing_db = os.path.join(d, "does_not_exist.db")
    check("for_subject() on a missing db still degrades cleanly",
          masterfile.for_subject(missing_db, "HMMWV") == {"query": "HMMWV", "filtered": [], "raw": [], "counts": {}})
    check("coverage() on a missing db still degrades cleanly", masterfile.coverage(missing_db) == [])

    # the real, valid master_db built above must still read back normally (the fix didn't break
    # the success path)
    res_ok = masterfile.for_subject(master_db, "HMMWV")
    check("for_subject() on a genuinely valid db still returns real data",
          any(f["type"] == "length" for f in res_ok["filtered"]))
    cov_ok = masterfile.coverage(master_db)
    check("coverage() on a genuinely valid db still returns real data", len(cov_ok) == 1 and cov_ok[0]["subject"] == "hmmwv")

    # ---- fix 3 (plan item 15): pageqa.db source degrades cleanly, missing OR torn -----------------
    # masterfile.py's own __main__ self-test (v1.2.0, plan item 13) already proves pageqa_db OMITTED
    # entirely and pageqa_db pointing at a path that does not exist yet both contribute nothing without
    # raising. What it does NOT cover -- the third reachable state -- is a pageqa.db file that EXISTS on
    # disk but is torn/pre-schema (a real possibility if BUILD-PAGEQA.bat is killed mid-run before its own
    # `CREATE TABLE IF NOT EXISTS pageqa_extractions` + first INSERT ever completes, or the file is
    # corrupted on disk). Mirrors THIS file's own torn_db pattern above (a db that exists but lacks the
    # expected schema) applied to pageqa_db as one of build()'s optional SOURCES rather than to master_db
    # itself -- same degrade contract dedup.db's own read side already guarantees for "sidecar not built
    # yet" (test_dedup.py's "a dedup.db that was never built returns [] cleanly" case).
    missing_pageqa = os.path.join(d, "never_built_pageqa.db")
    summ_missing_pq = masterfile.build(dbp, mdb, None, master_db, pageqa_db=missing_pageqa)
    check("build() with a pageqa_db path that doesn't exist yet succeeds normally (measures still land)",
          summ_missing_pq["filtered"] == 1)
    res_missing_pq = masterfile.for_subject(master_db, "HMMWV")
    check("a missing pageqa_db contributes no vlm-verified rows",
          not any(f["origin"] == "vlm-verified" for f in res_missing_pq["filtered"]))

    torn_pageqa = os.path.join(d, "torn_pageqa.db")
    tpq = sqlite3.connect(torn_pageqa)
    tpq.execute("CREATE TABLE something_unrelated(x INTEGER)")   # pageqa_extractions genuinely absent
    tpq.commit(); tpq.close()
    summ_torn_pq = masterfile.build(dbp, mdb, None, master_db, pageqa_db=torn_pageqa)
    check("build() with a torn/pre-schema pageqa_db degrades cleanly (no raise, rest of build still succeeds)",
          summ_torn_pq["filtered"] == 1)
    res_torn_pq = masterfile.for_subject(master_db, "HMMWV")
    check("a torn pageqa_db contributes no vlm-verified rows either",
          not any(f["origin"] == "vlm-verified" for f in res_torn_pq["filtered"]))
    check("a torn pageqa_db still leaves the corpus's own length group intact",
          any(f["type"] == "length" and f["origin"] == "corpus" for f in res_torn_pq["filtered"]))

    return passed, failed


if __name__ == "__main__":
    p, f = run()
    for n in p: print("PASS", n)
    for n in f: print("FAIL", n)
    print("\n%d passed, %d failed" % (len(p), len(f)))
    sys.exit(1 if f else 0)

# END OF FILE
