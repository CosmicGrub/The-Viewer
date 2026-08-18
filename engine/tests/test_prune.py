#!/usr/bin/env python3
"""THE VIEWER -- coverage for viewer_ingest.py's `prune` subcommand (audit finding #11): reconciles
documents whose source file was deleted or renamed/moved off disk since the last crawl. Exercises the
REAL migrated schema (via viewer_ingest.connect()+migrate()) so the cascade-delete / foreign-key
behavior the feature depends on (pages/jobs cascade automatically; figures/parts/request_items do
not, and get explicit non-cascading cleanup) is proven against the actual schema, not a hand-rolled
approximation of it. Self-contained; no real corpus. Run:  python tests/test_prune.py"""
import os, sys, sqlite3, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
MIGDIR = os.path.join(ENGINE, "migrations")
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)
import viewer_ingest as VI

passed, failed = [], []
def ok(name, cond):
    (passed if cond else failed).append(name)


def _write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _new_db(prefix):
    d = tempfile.mkdtemp(prefix=prefix)
    db = os.path.join(d, "viewer.db")
    con = VI.connect(db)
    VI.migrate(con, MIGDIR, db_path=db)
    return d, con


# =====================================================================================================
# Scenario A: safety valves + dry-run (no mutation) -- one shared tiny corpus, escalating missing count
# =====================================================================================================
try:
    dA, conA = _new_db("prune_valves_")
    f1 = os.path.join(dA, "f1.txt"); _write(f1, "AAA")
    f2 = os.path.join(dA, "f2.txt"); _write(f2, "BBB")
    f3 = os.path.join(dA, "f3.txt"); _write(f3, "CCC")
    for i, p in ((1, f1), (2, f2), (3, f3)):
        fp = VI.fingerprint(p, os.stat(p))
        conA.execute("INSERT INTO documents(id,path,fingerprint,type,vehicle,status) VALUES(?,?,?,?,?,?)",
                     (i, p, fp, "text", "V1", "indexed"))
    conA.commit()

    # root given but unreachable -> abort before looking at a single document
    r = VI.prune(conA, root=os.path.join(dA, "definitely-not-mounted"), confirm=False)
    ok("prune_root_unreachable_aborts", r == {"ok": False, "aborted": "root_unreachable",
                                               "root": os.path.join(dA, "definitely-not-mounted")})

    # nothing missing yet
    r = VI.prune(conA, confirm=False)
    ok("prune_nothing_missing", r == {"ok": True, "total": 3, "missing": 0, "deleted": 0, "renamed": 0, "removed_ids": []})

    # one file gone -> dry run reports it but changes nothing
    os.remove(f1)
    r = VI.prune(conA, confirm=False)
    ok("prune_dry_run_reports_one_missing", r["ok"] is True and r["missing"] == 1 and r["deleted"] == 1
       and r["renamed"] == 0 and r["removed_ids"] == [1])
    ok("prune_dry_run_no_mutation", conA.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 3)

    # a second file gone -> 2/3 = 67%, over the default 50% safety threshold -> abort
    os.remove(f2)
    r = VI.prune(conA, confirm=False)
    ok("prune_missing_fraction_aborts", r["ok"] is False and r["aborted"] == "missing_fraction"
       and r["missing"] == 2 and r["total"] == 3)
    ok("prune_missing_fraction_still_no_mutation", conA.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 3)

    # explicit higher threshold overrides the abort
    r = VI.prune(conA, confirm=False, missing_threshold=0.9)
    ok("prune_higher_threshold_proceeds", r["ok"] is True and r["missing"] == 2)

    conA.close()
except Exception as e:
    failed.append("prune_scenario_A(%s)" % e)


# =====================================================================================================
# Scenario B: confirmed prune -- rename detection, cascade delete, non-cascading cleanup, sidecars
# =====================================================================================================
try:
    dB, conB = _new_db("prune_confirm_")

    # a genuinely deleted document (no sibling with a matching fingerprint anywhere)
    gone = os.path.join(dB, "gone.txt"); _write(gone, "GONE-CONTENT")
    fp_gone = VI.fingerprint(gone, os.stat(gone))
    os.remove(gone)   # actually gone from disk -- this is the "deleted" case, not "renamed"

    # a renamed/moved document: crawl already re-discovered it under a new path (same fingerprint,
    # since a same-filesystem rename preserves size+mtime -- the exact basis of fingerprint()).
    old_name = os.path.join(dB, "old_name.txt"); _write(old_name, "MOVED-CONTENT")
    fp_moved = VI.fingerprint(old_name, os.stat(old_name))
    new_name = os.path.join(dB, "new_name.txt")
    os.replace(old_name, new_name)
    ok("prune_setup_rename_preserves_fingerprint", VI.fingerprint(new_name, os.stat(new_name)) == fp_moved)

    # three untouched, present documents so missing (2) stays under the default 50% threshold (2/5=40%)
    keep_paths = []
    for i in range(3):
        p = os.path.join(dB, "keep%d.txt" % i); _write(p, "KEEP-%d" % i); keep_paths.append(p)

    rows = [
        (10, old_name, fp_moved, "V1"),              # missing, renamed (dup fingerprint on doc 11)
        (11, new_name, fp_moved, "V1"),               # present -- the renamed file's new row
        (12, gone, fp_gone, "V1"),                     # missing, genuinely deleted
        (13, keep_paths[0], VI.fingerprint(keep_paths[0], os.stat(keep_paths[0])), "V2"),
        (14, keep_paths[1], VI.fingerprint(keep_paths[1], os.stat(keep_paths[1])), "V2"),
        (15, keep_paths[2], VI.fingerprint(keep_paths[2], os.stat(keep_paths[2])), "V2"),
    ]
    for did, p, fp, veh in rows:
        conB.execute("INSERT INTO documents(id,path,fingerprint,type,vehicle,status) VALUES(?,?,?,?,?,?)",
                     (did, p, fp, "text", veh, "indexed"))
    conB.execute("INSERT INTO pages(document_id,page_number,body_text) VALUES(10,1,'UNIQUEWORD12345 body text')")
    conB.execute("INSERT INTO figures(document_id,page_number,source_ref) VALUES(10,1,'fig1')")
    conB.execute("INSERT INTO parts(document_id,name) VALUES(10,'BOLT')")
    conB.execute("INSERT INTO sessions(id) VALUES(1)")
    conB.execute("INSERT INTO request_items(id,session_id,item_name,source_document_id) VALUES(1,1,'need a bolt',12)")
    conB.commit()
    ok("prune_setup_fts_indexed", conB.execute(
        "SELECT COUNT(*) FROM pages_fts WHERE pages_fts MATCH 'UNIQUEWORD12345'").fetchone()[0] == 1)

    r_dry = VI.prune(conB, confirm=False)
    ok("prune_dry_run_detects_rename_and_delete", r_dry["ok"] is True and r_dry["missing"] == 2
       and r_dry["renamed"] == 1 and r_dry["deleted"] == 1 and set(r_dry["removed_ids"]) == {10, 12})
    ok("prune_dry_run_scenario_b_no_mutation", conB.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 6)

    # sidecars to prove the best-effort cleanup pass
    meas_db = os.path.join(dB, "measures.db")
    mc = sqlite3.connect(meas_db)
    mc.execute("CREATE TABLE meas(id INTEGER PRIMARY KEY, doc INT, page INT, type TEXT)")
    mc.execute("CREATE TABLE meas_done(doc INTEGER PRIMARY KEY, pages INT, ts REAL)")
    mc.executemany("INSERT INTO meas(doc,page,type) VALUES(?,?,?)", [(10, 1, "torque"), (11, 1, "torque")])
    mc.execute("INSERT INTO meas_done(doc,pages,ts) VALUES(10,1,0.0)")
    mc.commit(); mc.close()
    figcache = os.path.join(dB, "figcache"); os.makedirs(figcache)
    survivor = os.path.join(figcache, "11_1_150.png"); doomed = os.path.join(figcache, "10_1_150.png")
    _write(survivor, "x"); _write(doomed, "x")
    # callout_crop() output doesn't start with the doc_id (review finding) -- the doomed one must
    # still be swept, and a same-doc-prefix-but-different-item survivor must not be over-matched.
    callout_doomed = os.path.join(figcache, "callout_10_1_A_150.png")
    callout_survivor = os.path.join(figcache, "callout_11_1_A_150.png")
    _write(callout_doomed, "x"); _write(callout_survivor, "x")
    # tables.db (build_tables.py's real schema: tbl/tbl_done -- a review finding caught an earlier
    # version of this code targeting nonexistent table names, a permanent silent no-op)
    tab_db = os.path.join(dB, "tables.db")
    tb = sqlite3.connect(tab_db)
    tb.execute("CREATE TABLE tbl(id INTEGER PRIMARY KEY, doc INT, page INT, kind TEXT)")
    tb.execute("CREATE TABLE tbl_done(doc INTEGER PRIMARY KEY, ts REAL)")
    tb.executemany("INSERT INTO tbl(doc,page,kind) VALUES(?,?,?)", [(10, 1, "grid"), (11, 1, "grid")])
    tb.execute("INSERT INTO tbl_done(doc,ts) VALUES(10,0.0)")
    tb.commit(); tb.close()
    # pagecache (rps.py): HYPHEN-separated naming ("<doc>-<page>-d<dpi>.png"), unlike the other
    # three caches' underscore naming -- a review finding caught an earlier version of this code
    # omitting pagecache entirely.
    pagecache = os.path.join(dB, "pagecache"); os.makedirs(pagecache)
    pc_survivor = os.path.join(pagecache, "11-1-d150.png"); pc_doomed = os.path.join(pagecache, "10-1-d150.png")
    _write(pc_survivor, "x"); _write(pc_doomed, "x")

    r_confirm = VI.prune(conB, confirm=True, index_dir=dB)
    ok("prune_confirm_ok", r_confirm["ok"] is True and set(r_confirm["removed_ids"]) == {10, 12})

    remaining = {r[0] for r in conB.execute("SELECT id FROM documents")}
    ok("prune_confirm_removed_rows", remaining == {11, 13, 14, 15})
    ok("prune_confirm_pages_cascaded", conB.execute("SELECT COUNT(*) FROM pages WHERE document_id=10").fetchone()[0] == 0)
    ok("prune_confirm_fts_synced", conB.execute(
        "SELECT COUNT(*) FROM pages_fts WHERE pages_fts MATCH 'UNIQUEWORD12345'").fetchone()[0] == 0)
    ok("prune_confirm_figures_cleared", conB.execute("SELECT COUNT(*) FROM figures WHERE document_id=10").fetchone()[0] == 0)
    ok("prune_confirm_parts_cleared", conB.execute("SELECT COUNT(*) FROM parts WHERE document_id=10").fetchone()[0] == 0)
    ri = conB.execute("SELECT source_document_id FROM request_items WHERE id=1").fetchone()
    ok("prune_confirm_request_item_nulled_not_deleted", ri is not None and ri[0] is None)

    mc = sqlite3.connect(meas_db)
    left_meas = {r[0] for r in mc.execute("SELECT doc FROM meas")}
    left_done = {r[0] for r in mc.execute("SELECT doc FROM meas_done")}
    mc.close()
    ok("prune_sidecar_measures_pruned", left_meas == {11} and left_done == set())
    ok("prune_sidecar_figcache_pruned", not os.path.exists(doomed) and os.path.exists(survivor))
    ok("prune_sidecar_figcache_callout_pruned",
       not os.path.exists(callout_doomed) and os.path.exists(callout_survivor))

    tb = sqlite3.connect(tab_db)
    left_tbl = {r[0] for r in tb.execute("SELECT doc FROM tbl")}
    left_tbl_done = {r[0] for r in tb.execute("SELECT doc FROM tbl_done")}
    tb.close()
    ok("prune_sidecar_tables_db_pruned", left_tbl == {11} and left_tbl_done == set())
    ok("prune_sidecar_pagecache_pruned", not os.path.exists(pc_doomed) and os.path.exists(pc_survivor))

    # idempotent: running again finds nothing left to prune
    r_again = VI.prune(conB, confirm=True, index_dir=dB)
    ok("prune_idempotent_second_run", r_again == {"ok": True, "total": 4, "missing": 0, "deleted": 0,
                                                    "renamed": 0, "removed_ids": []})
    conB.close()
except Exception as e:
    failed.append("prune_scenario_B(%s)" % e)


# =====================================================================================================
# migrate()'s pre-migration backup must never write into (or rotate) the REAL repo's backups/db/
# vault for a throwaway/alternate --db path -- only the canonical safeguard.DB_DEFAULT does that.
# A review finding caught the original version of this doing exactly that: reproduced live,
# running this very test suite was silently rotating real backups out of the checked-out repo.
# =====================================================================================================
try:
    import safeguard
    real_vault_before = set(os.listdir(safeguard.DB_BACKUP_DIR)) if os.path.isdir(safeguard.DB_BACKUP_DIR) else None

    dD, conD = _new_db("prune_migrate_dest_")   # a throwaway tempdir db -- NOT safeguard.DB_DEFAULT
    conD.close()

    real_vault_after = set(os.listdir(safeguard.DB_BACKUP_DIR)) if os.path.isdir(safeguard.DB_BACKUP_DIR) else None
    ok("migrate_backup_does_not_touch_real_vault", real_vault_after == real_vault_before)

    own_backup_dir = os.path.join(dD, "backups", "db")
    ok("migrate_backup_lands_next_to_its_own_db", os.path.isdir(own_backup_dir)
       and len(os.listdir(own_backup_dir)) >= 1)
except Exception as e:
    failed.append("prune_migrate_backup_dest(%s)" % e)


# =====================================================================================================
# extract_parts(): a pre-existing bug (predates this diff, found + fixed during review verification)
# -- dict-style row access against a connection that returns plain tuples raised a TypeError on the
# very first RPSTL-shaped page. Reproduced live before the fix; this proves it stays fixed.
# =====================================================================================================
try:
    dE, conE = _new_db("prune_extract_parts_")
    conE.execute("INSERT INTO documents(id,path,vehicle) VALUES(1,?,?)", (os.path.join(dE, "a.pdf"), "V1"))
    conE.execute(
        "INSERT INTO pages(document_id,page_number,body_text) VALUES(1,1,?)",
        ("PART NUMBER USABLE ON CODE A FIG 3: BRACKET NSN 5305-01-674-1467",))
    conE.commit()
    n = VI.extract_parts(conE)
    ok("extract_parts_no_longer_raises", n == 1)
    row = conE.execute("SELECT nsn, document_id, page, vehicle, fig_no FROM parts").fetchone()
    ok("extract_parts_row_correct", row == ("5305-01-674-1467", 1, 1, "V1", "3"))
    conE.close()
except Exception as e:
    failed.append("prune_extract_parts_regression(%s)" % e)


# =====================================================================================================
# CLI wiring: `python viewer_ingest.py prune --db ... --yes` really dispatches to prune() end-to-end
# =====================================================================================================
try:
    dC = tempfile.mkdtemp(prefix="prune_cli_")
    dbC = os.path.join(dC, "viewer.db")
    real_argv = sys.argv
    sys.argv = ["viewer_ingest.py", "prune", "--db", dbC, "--yes"]
    try:
        VI.main()   # fresh db (no documents yet) -> migrate() creates the schema, prune() finds nothing to do
    finally:
        sys.argv = real_argv
    conC = sqlite3.connect(dbC)
    ok("prune_cli_dispatch_ran_migrations", conC.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='documents'").fetchone() is not None)
    conC.close()
except Exception as e:
    failed.append("prune_cli_wiring(%s)" % e)


for n in passed: print("PASS", n)
for n in failed: print("FAIL", n)
print("\n%d passed, %d failed (of %d checks for viewer_ingest.py's `prune` subcommand)" %
      (len(passed), len(failed), len(passed) + len(failed)))
sys.exit(1 if failed else 0)

# END OF FILE
