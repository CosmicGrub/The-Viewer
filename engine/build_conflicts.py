#!/usr/bin/env python3
"""build_conflicts.py -- PRECOMPUTED CONFLICT SWEEP (roadmap #88-lite, v1.13.0).

Batch-runs the cross-manual conflict checker (conflicts.check_query) over the most frequent part
subjects in the corpus and stores every result -- including the clean "no conflict" ones -- in the
append-only sidecar index/conflicts.db. The /api/conflicts route then answers a swept subject
INSTANTLY from the sidecar ("precomputed": true + build timestamp) instead of re-scanning measures
live; unswept or stale subjects fall back to the live scan unchanged (R1: purely additive).

Append-only style (R6): every sweep is a new run_id; old rows are never updated or deleted, so the
history of what each sweep found is retained. Read-only on viewer.db. Best run while OCR is paused
(it hammers the measures FTS path). Stdlib only.

Usage:
    python build_conflicts.py [--limit 2000] [--tol 0.05] [--db path\\to\\viewer.db] [--note "..."]
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DEFAULT_DB = os.environ.get("VIEWER_DB", os.path.join(os.path.dirname(HERE), "index", "viewer.db"))

_SUBJECTS_SQL = ("SELECT COALESCE(NULLIF(TRIM(fig_title),''), NULLIF(TRIM(name),'')) AS subject, "
                 "COUNT(*) AS c FROM parts GROUP BY subject "
                 "HAVING subject IS NOT NULL AND LENGTH(subject) >= 3 "
                 "ORDER BY c DESC, subject LIMIT ?")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs(
    run_id INTEGER PRIMARY KEY,
    started TEXT, finished TEXT,
    n_subjects INT, n_with_conflicts INT,
    rel_tol REAL, note TEXT);
CREATE TABLE IF NOT EXISTS results(
    id INTEGER PRIMARY KEY,
    run_id INT, subject TEXT,
    n_values INT, quarantined INT, n_conflicts INT,
    conflicts_json TEXT,
    ts TEXT DEFAULT (datetime('now')));
CREATE INDEX IF NOT EXISTS idx_results_subject ON results(subject, id);
"""


def subjects(db_path, limit):
    """Distinct part subjects (fig_title, else name) from the READ-ONLY parts table, most frequent
    first -- the parts people actually look up get swept first."""
    con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
    try:
        return [r[0] for r in con.execute(_SUBJECTS_SQL, (int(limit),)).fetchall()]
    finally:
        con.close()


def sweep(db_path, limit=2000, rel_tol=0.05, note=""):
    import conflicts
    side = conflicts._sidecar_path(db_path)
    subs = subjects(db_path, limit)
    print("[build_conflicts] corpus db : %s" % db_path)
    print("[build_conflicts] sidecar   : %s" % side)
    print("[build_conflicts] subjects  : %d (top by parts-table frequency, --limit %d)" % (len(subs), limit))
    scon = sqlite3.connect(side)
    scon.executescript(_SCHEMA)
    cur = scon.execute("INSERT INTO runs(started, n_subjects, rel_tol, note) VALUES(datetime('now'),?,?,?)",
                       (len(subs), rel_tol, note or ""))
    run_id = cur.lastrowid
    scon.commit()
    n_hit = 0
    t0 = time.time()
    for i, subj in enumerate(subs, 1):
        try:
            # live scan ALWAYS (use_precomputed=False): a sweep must never read its own output
            res = conflicts.check_query(db_path, subj, rel_tol=rel_tol, use_precomputed=False)
        except Exception as e:
            print("[build_conflicts] ERROR on %r: %s" % (subj, e))
            continue
        cs = res.get("conflicts") or []
        if cs:
            n_hit += 1
        scon.execute("INSERT INTO results(run_id, subject, n_values, quarantined, n_conflicts, conflicts_json) "
                     "VALUES(?,?,?,?,?,?)",
                     (run_id, subj, int(res.get("n_values") or 0), int(res.get("quarantined") or 0),
                      len(cs), json.dumps(cs, ensure_ascii=False)))
        if i % 25 == 0 or i == len(subs):
            scon.commit()
            rate = i / max(time.time() - t0, 0.001)
            print("[build_conflicts] %d/%d swept  (%d with conflicts, %.1f subj/s, ~%ds left)"
                  % (i, len(subs), n_hit, rate, int((len(subs) - i) / max(rate, 0.001))))
    scon.execute("UPDATE runs SET finished=datetime('now'), n_with_conflicts=? WHERE run_id=?", (n_hit, run_id))
    scon.commit(); scon.close()
    print("[build_conflicts] DONE run %d: %d subject(s) swept, %d with conflicts, in %.0fs"
          % (run_id, len(subs), n_hit, time.time() - t0))
    print("[build_conflicts] /api/conflicts now answers swept subjects instantly (precomputed: true).")
    return {"run_id": run_id, "subjects": len(subs), "with_conflicts": n_hit}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Precompute the cross-manual conflict sweep into index/conflicts.db")
    ap.add_argument("--db", default=DEFAULT_DB, help="corpus index db (default: index/viewer.db)")
    ap.add_argument("--limit", type=int, default=2000, help="sweep the top N most frequent part subjects (default 2000)")
    ap.add_argument("--tol", type=float, default=0.05, help="relative disagreement tolerance (default 0.05 = 5%%)")
    ap.add_argument("--note", default="", help="free-text note stored on the run row")
    args = ap.parse_args(argv)
    if not os.path.exists(args.db):
        print("[build_conflicts] FAIL: index db not found at %s" % args.db)
        return 1
    sweep(args.db, limit=max(1, args.limit), rel_tol=args.tol, note=args.note)
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        # synthetic end-to-end: tiny parts table -> sweep -> sidecar row -> precomputed_for serves it
        import tempfile
        d = tempfile.mkdtemp(); db = os.path.join(d, "viewer.db")
        c = sqlite3.connect(db)
        c.execute("CREATE TABLE parts(id INTEGER PRIMARY KEY, name TEXT, fig_title TEXT)")
        c.executemany("INSERT INTO parts(name, fig_title) VALUES(?,?)",
                      [("", "BOLT, MACHINE"), ("", "BOLT, MACHINE"), ("valve", ""), ("", None)])
        c.commit(); c.close()
        subs = subjects(db, 10)
        assert subs[0] == "BOLT, MACHINE" and "valve" in subs and len(subs) == 2, subs
        out = sweep(db, limit=10)                     # measures likely errors per-subject -> rows may be 0..2
        assert out["run_id"] == 1, out
        import conflicts as _c
        scon = sqlite3.connect(_c._sidecar_path(db))
        runs = scon.execute("SELECT run_id, n_subjects, finished FROM runs").fetchall(); scon.close()
        assert len(runs) == 1 and runs[0][1] == 2 and runs[0][2], runs
        print("build_conflicts self-test PASS (subjects ranked, run recorded append-only)")
        sys.exit(0)
    sys.exit(main())

# END OF FILE
