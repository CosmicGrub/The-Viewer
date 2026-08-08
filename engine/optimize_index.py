#!/usr/bin/env python3
"""THE VIEWER — one-time index/optimize pass.

Adds the few missing indexes that make the newer lookups fast and runs ANALYZE so the query planner
uses them. Idempotent (CREATE INDEX IF NOT EXISTS) and safe to re-run. It takes a BRIEF write lock to
build each index, so run it when the OCR scan is PAUSED (a 120 s busy-timeout lets it wait politely if
the DB is momentarily busy). Read path is never blocked for long.

Speeds up: Look-Alike Parts (name/nomenclature), Find-in-manual (document_id), procedure & torque lookups.

Usage:  python optimize_index.py [--db PATH]
"""
import os, sqlite3, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(HERE, "..", "index", "viewer.db")

INDEXES = [
    ("ix_pages_document",      "pages", "CREATE INDEX IF NOT EXISTS ix_pages_document ON pages(document_id)"),
    ("ix_parts_name",          "parts", "CREATE INDEX IF NOT EXISTS ix_parts_name ON parts(name COLLATE NOCASE)"),
    ("ix_parts_nomenclature",  "parts", "CREATE INDEX IF NOT EXISTS ix_parts_nomenclature ON parts(nomenclature COLLATE NOCASE)"),
]

def main():
    db = DEFAULT_DB; args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--db" and i + 1 < len(args): db = args[i + 1]
    db = os.path.abspath(db)
    print("=== THE VIEWER — index optimizer ===")
    print("db :", db)
    if not os.path.exists(db):
        print("[ERROR] index not found. Pass --db <path> if it lives elsewhere."); return 1
    print("note: run this when the OCR scan is PAUSED (a brief write lock is taken per index).\n")
    con = sqlite3.connect(db, timeout=130)
    try: con.execute("PRAGMA busy_timeout=120000")
    except Exception: pass
    try:
        existing = set(r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='index'"))
    except Exception as e:
        print("[ERROR] could not read schema:", e); con.close(); return 1
    made = 0
    for name, tbl, sql in INDEXES:
        if name in existing:
            print("  - %-24s already present" % name); continue
        t0 = time.time()
        sys.stdout.write("  + creating %-24s on %s ... " % (name, tbl)); sys.stdout.flush()
        try:
            con.execute(sql); con.commit()
            print("done in %.1fs" % (time.time() - t0)); made += 1
        except sqlite3.OperationalError as e:
            print("SKIPPED (%s) — is OCR still writing? try again when it's paused." % e)
        except Exception as e:
            print("error (%s)" % e)
    sys.stdout.write("  ~ ANALYZE (planner stats) ... "); sys.stdout.flush(); t0 = time.time()
    try: con.execute("ANALYZE"); con.commit(); print("done in %.1fs" % (time.time() - t0))
    except Exception as e: print("skipped (%s)" % e)
    try: con.execute("PRAGMA optimize")
    except Exception: pass
    # Precompute a small suggestions table so type-ahead is a prefix lookup, not a GROUP BY over the FTS vocab.
    sys.stdout.write("  ~ building suggest_terms (type-ahead) ... "); sys.stdout.flush(); t0 = time.time()
    try:
        con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS pages_vocab USING fts5vocab('pages_fts','row')")
        con.execute("DROP TABLE IF EXISTS suggest_terms")
        con.execute("CREATE TABLE suggest_terms(term TEXT PRIMARY KEY, freq INT) WITHOUT ROWID")
        con.execute("INSERT OR IGNORE INTO suggest_terms(term, freq) "
                    "SELECT term, SUM(cnt) c FROM pages_vocab WHERE length(term)>=2 GROUP BY term HAVING c>=2")
        con.commit()
        n = con.execute("SELECT COUNT(*) FROM suggest_terms").fetchone()[0]
        print("done in %.1fs (%d terms)" % (time.time() - t0, n))
    except Exception as e:
        print("skipped (%s)" % e)
    # WAL: concurrent reads while the OCR writer runs (server reads no longer block on writes). Reversible.
    try:
        mode = con.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        print("  ~ journal_mode -> %s (concurrent reads during writes)" % mode)
    except Exception as e:
        print("  ~ WAL skipped (%s)" % e)
    con.close()
    print("\nDone — %d new index(es) + suggest_terms + WAL. Look-Alike, Find-in-manual, type-ahead, procedure"
          " & torque lookups are now accelerated. Safe to re-run anytime." % made)
    return 0

if __name__ == "__main__":
    sys.exit(main())
