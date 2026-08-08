#!/usr/bin/env python3
"""THE VIEWER -- one-time, reversible reconciliation of the schema-version counter.

Why: migration 0008 (data_date / superseded / alt_parts on ref_nsn + ref_nsn_log) was already
applied to the live index, but schema_meta.schema_version was never bumped past 7. So migrate()
keeps trying to re-apply 0008 -> "duplicate column name" -> crash before OCR can run.

This script ONLY bumps the counter 7 -> 8, and ONLY after verifying 0008's columns truly exist.
Additive + reversible (R1), append-only (R6). Revert with: UPDATE schema_meta SET schema_version=7.
Safe to run more than once.
"""
import os, sqlite3, time, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "index", "viewer.db")
if not os.path.exists(DB):
    DB = os.path.join(HERE, "..", "index", "viewer_index.db")

NEED = {"data_date", "superseded", "alt_parts"}
LOG = os.path.join(HERE, "..", "index", "schema_fix_result.txt")

def out(msg):
    line = "[%s] %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line)
    try:
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass

def main():
    out("DB = %s" % os.path.abspath(DB))
    con = sqlite3.connect(DB, timeout=60)
    try:
        before = con.execute("SELECT schema_version FROM schema_meta WHERE id=1").fetchone()[0]
        out("schema_version before = %s" % before)

        # Guard: only bump if 0008's columns are genuinely present on BOTH tables.
        for t in ("ref_nsn", "ref_nsn_log"):
            cols = {r[1] for r in con.execute("PRAGMA table_info(%s)" % t)}
            missing = NEED - cols
            if missing:
                out("ABORT: %s is missing %s -- 0008 not fully applied; not bumping. "
                    "Run the real migration instead." % (t, sorted(missing)))
                return 2
            out("%s has all 0008 columns: OK" % t)

        if before >= 8:
            out("Already at version %s -- nothing to do." % before)
            return 0

        con.execute("UPDATE schema_meta SET schema_version=8 WHERE id=1")
        con.commit()
        after = con.execute("SELECT schema_version FROM schema_meta WHERE id=1").fetchone()[0]
        out("schema_version after  = %s  (revert: UPDATE schema_meta SET schema_version=7)" % after)
        out("DONE -- migrate() will now skip 0008. Safe to launch OCR.")
        return 0
    finally:
        con.close()

if __name__ == "__main__":
    sys.exit(main())
