#!/usr/bin/env python3
"""THE VIEWER -- coverage for the Tier-1 corpus-build pipeline (audit finding #20): build_measures.py,
build_masterfile.py (via masterfile.py), build_publog.py, build_conflicts.py, build_kg.py (via kg.py).
These are host-side batch builders that write append-only sidecars (R1/R6); every builder in this file
is exercised against a tiny synthetic source instead of the real multi-GB corpus. Two modules already
carried a well-designed `if __name__ == "__main__":` self-test (kg.py, masterfile.py) and one carried a
`--selftest` flag (build_conflicts.py) -- none of the three were ever picked up by verify_all.py's
test_*.py auto-discovery, so a regression in any of them could ship silently. This file ports each of
those checks into the repo's ok()/PASS-FAIL idiom (so they run in CI) and adds the crash-mid-build
atomicity regression tests the audit specifically called out for build_publog.py and kg.py (finding #9's
build-to-temp-then-atomic_replace fix): a simulated crash partway through a build must leave the last-
good sidecar on disk untouched and must not leak the `.building-<pid>` temp file.
Self-contained; no real corpus, no network, no GPU. Run:  python tests/test_build_pipeline.py"""
import os, sys, sqlite3, tempfile, csv

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)

passed, failed = [], []
def ok(name, cond):
    (passed if cond else failed).append(name)


# =====================================================================================================
# kg.py -- knowledge-graph builder + query (build_kg.py assembles the triples; kg.py IS the pipeline)
# =====================================================================================================
try:
    import kg

    d = tempfile.mkdtemp(prefix="kg_")
    kgdb = os.path.join(d, "kg.db")
    triples = [
        ("part", "Alternator", "on_figure", "figure", "FIG 4-2"),
        ("part", "Alternator", "in_vehicle", "vehicle", "HMMWV"),
        ("procedure", "Replace alternator", "for_part", "part", "Alternator"),
        ("part", "Alternator", "has_spec", "spec", "28 VDC"),
        ("part", "Alternator", "has_nsn", "nsn", "2920-01-371-9577"),
        ("part", "Bracket", "on_figure", "figure", "FIG 4-2"),
    ]
    r = kg.build(kgdb, triples)
    ok("kg_build_counts", r["edges"] == 6 and r["nodes"] == 7)

    nb = kg.neighbors(kgdb, "alternator")
    outrels = {(o["rel"], o["label"]) for o in nb["out"]}
    ok("kg_neighbors_out", ("on_figure", "FIG 4-2") in outrels and ("in_vehicle", "HMMWV") in outrels
       and ("has_nsn", "2920-01-371-9577") in outrels and ("has_spec", "28 VDC") in outrels)
    inrels = {(i["rel"], i["label"]) for i in nb["in"]}
    ok("kg_neighbors_in", ("for_part", "Replace alternator") in inrels)

    st = kg.stats(kgdb)
    ok("kg_stats", st["by_type"].get("part") == 2 and st["edges"] == 6)

    ok("kg_neighbors_empty_db", kg.neighbors(os.path.join(d, "nope.db"), "x") == {"query": "x", "matched": [], "out": [], "in": []})
    ok("kg_stats_empty_db", kg.stats(os.path.join(d, "nope.db")) == {"nodes": 0, "edges": 0, "by_type": {}})

    # --- atomicity: a crash mid-build must leave the last-good kg.db untouched + clean up the temp file ---
    original_bytes = open(kgdb, "rb").read()

    class _BoomConn:
        """Proxies a real sqlite3.Connection but fails commit() -- simulates a crash/kill right after
        every insert has been prepared but before the durable commit that would make it real."""
        def __init__(self, real): self._real = real
        def __getattr__(self, name): return getattr(self._real, name)
        def commit(self): raise RuntimeError("simulated crash before commit")

    real_connect = kg.sqlite3.connect
    def _boom_connect(path, *a, **kw):
        return _BoomConn(real_connect(path, *a, **kw))
    kg.sqlite3.connect = _boom_connect
    raised = False
    try:
        kg.build(kgdb, [("part", "New Part", "on_figure", "figure", "F9")])
    except RuntimeError:
        raised = True
    finally:
        kg.sqlite3.connect = real_connect
    ok("kg_atomicity_crash_propagates", raised)
    ok("kg_atomicity_original_untouched", open(kgdb, "rb").read() == original_bytes)
    tmp_path = kgdb + ".building-%d" % os.getpid()
    ok("kg_atomicity_temp_cleaned_up", not os.path.exists(tmp_path))
    # and the untouched db still answers queries normally after the failed rebuild attempt
    ok("kg_still_queryable_after_failed_rebuild", kg.stats(kgdb)["edges"] == 6)
except Exception as e:
    failed.append("kg.py(%s)" % e)


# =====================================================================================================
# safeguard.atomic_sqlite_build() -- direct coverage of the crash-safety contract kg.py/build_publog.py/
# build_rpstl.py all now share. The atomicity checks above (and build_publog's below) only ever inject a
# plain RuntimeError; xhigh review finding: nothing proved a BaseException subclass that ISN'T an
# Exception (KeyboardInterrupt, SystemExit) still propagates unchanged rather than being narrowed or
# swallowed by the generator's `except BaseException: ... raise`. Tested directly against safeguard, not
# through a caller, since this is a safeguard.py-level contract, not a kg.py/build_publog.py-specific one.
# =====================================================================================================
try:
    import safeguard

    sg_dir = tempfile.mkdtemp(prefix="safeguard_")
    sg_dst = os.path.join(sg_dir, "guarded.db")
    open(sg_dst, "wb").write(b"PREVIOUS-GOOD-BUILD-DO-NOT-TOUCH")
    sg_original = open(sg_dst, "rb").read()

    caught = None
    try:
        with safeguard.atomic_sqlite_build(sg_dst) as (con, tmp_path):
            con.execute("CREATE TABLE t(x)")
            con.execute("INSERT INTO t VALUES(1)")
            con.commit()
            raise KeyboardInterrupt()
    except KeyboardInterrupt as e:
        caught = e
    except BaseException as e:
        caught = e  # wrong type would land here instead -- still recorded, so the type check below fails loudly
    ok("safeguard_atomic_build_keyboardinterrupt_propagates_unchanged", isinstance(caught, KeyboardInterrupt))
    ok("safeguard_atomic_build_keyboardinterrupt_leaves_original_untouched", open(sg_dst, "rb").read() == sg_original)
    sg_tmp = sg_dst + ".building-%d" % os.getpid()
    ok("safeguard_atomic_build_keyboardinterrupt_cleans_up_temp", not os.path.exists(sg_tmp))

    # And the success path: dst_path is genuinely untouched until the `with` block exits cleanly.
    with safeguard.atomic_sqlite_build(sg_dst) as (con, tmp_path):
        con.execute("CREATE TABLE t2(y)")
        con.execute("INSERT INTO t2 VALUES(42)")
        con.commit()
        ok("safeguard_atomic_build_dst_untouched_mid_build", open(sg_dst, "rb").read() == sg_original)
    ok("safeguard_atomic_build_dst_swapped_in_on_clean_exit", sqlite3.connect(sg_dst).execute("SELECT y FROM t2").fetchone()[0] == 42)
except Exception as e:
    failed.append("safeguard.atomic_sqlite_build(%s)" % e)


# =====================================================================================================
# masterfile.py -- consolidates measures.db (authoritative) + enrich.db (supplemental gap-fill)
# =====================================================================================================
try:
    import masterfile

    d = tempfile.mkdtemp(prefix="master_")
    dbp = os.path.join(d, "viewer.db"); mdb = os.path.join(d, "measures.db")
    edb = os.path.join(d, "enrich.db"); mf = os.path.join(d, "masterfile.db")

    a = sqlite3.connect(dbp)
    a.execute("CREATE TABLE documents(id INTEGER PRIMARY KEY, vehicle TEXT)")
    a.execute("INSERT INTO documents VALUES(1,'HMMWV')"); a.commit(); a.close()

    m = sqlite3.connect(mdb)
    m.execute("CREATE TABLE meas(doc INT,page INT,type TEXT,unit TEXT,value TEXT,value2 TEXT,tolerance TEXT,context TEXT)")
    m.executemany("INSERT INTO meas VALUES(?,?,?,?,?,?,?,?)", [
        (1, 12, "length", "in", "180", None, None, "Overall length 180 in"),
        (1, 12, "length", "in", "180", None, None, "len 180 in (dup)"),
        (1, 20, "weight", "lb", "7700", None, None, "Curb weight 7700 lb")])
    m.commit(); m.close()

    e = sqlite3.connect(edb)
    e.execute("CREATE TABLE ext_meas(subject TEXT,subject_label TEXT,type TEXT,unit TEXT,value TEXT,value2 TEXT,"
              "tolerance TEXT,context TEXT,source TEXT,source_url TEXT,orig_url TEXT,wayback_ts TEXT,fetched_ts REAL,"
              "confidence REAL,status TEXT)")
    e.executemany("INSERT INTO ext_meas(subject,subject_label,type,unit,value,context,source_url) VALUES(?,?,?,?,?,?,?)", [
        ("hmmwv", "HMMWV", "capacity", "gal", "25", "Fuel 25 gal", "http://web.archive.org/x"),
        ("hmmwv", "HMMWV", "weight", "lb", "9999", "bogus weight", "http://web.archive.org/y")])
    e.commit(); e.close()

    summ = masterfile.build(dbp, mdb, edb, mf, md_path=os.path.join(d, "MASTERFILE.md"))
    ok("masterfile_summary_shape", summ["subjects"] == 1 and summ["corpus"] == 3 and summ["external"] == 1)

    res = masterfile.for_subject(mf, "HMMWV")
    ftypes = {(f["type"], f["origin"]) for f in res["filtered"]}
    ok("masterfile_corpus_rows_present", ("length", "corpus") in ftypes and ("weight", "corpus") in ftypes)
    ok("masterfile_external_gapfill", ("capacity", "external") in ftypes)
    ok("masterfile_corpus_wins_over_external", ("weight", "external") not in ftypes)

    blob = repr(res["filtered"]) + repr([{k: v for k, v in r.items() if k != "page_url"} for r in res["raw"]])
    ok("masterfile_no_links_leaked", "http://" not in blob and "web.archive" not in blob)
    ok("masterfile_corpus_page_ref_kept", any(r["page_url"] for r in res["raw"] if r["origin"] == "corpus"))
    ok("masterfile_external_no_page_ref", all(not r["page_url"] for r in res["raw"] if r["origin"] == "external"))

    ok("masterfile_md_written", os.path.exists(os.path.join(d, "MASTERFILE.md"))
       and os.path.getsize(os.path.join(d, "MASTERFILE.md")) > 0)

    cov = masterfile.coverage(mf)
    ok("masterfile_coverage_flags_missing", cov and cov[0]["subject"] == "hmmwv"
       and "torque" in cov[0]["missing"] and "length" not in cov[0]["missing"])

    # degrades gracefully with no sources at all
    empty_mf = os.path.join(d, "empty_master.db")
    summ2 = masterfile.build(dbp, os.path.join(d, "nope_measures.db"), os.path.join(d, "nope_enrich.db"), empty_mf)
    ok("masterfile_no_sources_graceful", summ2["subjects"] == 0 and summ2["raw"] == 0)
except Exception as e:
    failed.append("masterfile.py(%s)" % e)


# =====================================================================================================
# build_measures.py -- walks viewer.db pages, runs measures.extract(), writes the measures.db sidecar
# =====================================================================================================
try:
    import build_measures as BM

    d = tempfile.mkdtemp(prefix="measures_")
    vdb = os.path.join(d, "viewer.db"); sdb = os.path.join(d, "measures.db")
    v = sqlite3.connect(vdb)
    v.execute("CREATE TABLE documents(id INTEGER PRIMARY KEY, vehicle TEXT)")
    v.execute("CREATE TABLE pages(id INTEGER PRIMARY KEY, document_id INT, page_number INT, body_text TEXT, ocr_confidence REAL)")
    v.execute("INSERT INTO documents VALUES(1,'HMMWV')")
    v.execute("INSERT INTO pages(document_id,page_number,body_text) VALUES(1,1,?)",
              ("Torque the nut to 25 ft-lb. Overall length is 180 in.",))
    v.commit(); v.close()

    BM.DB = vdb; BM.SIDE = sdb
    rc = BM.main()
    ok("build_measures_exit_ok", rc == 0)
    ok("build_measures_sidecar_created", os.path.exists(sdb))

    s = sqlite3.connect(sdb)
    types1 = [r[0] for r in s.execute("SELECT type FROM meas WHERE doc=1")]
    ids1 = set(r[0] for r in s.execute("SELECT id FROM meas WHERE doc=1"))
    done1 = s.execute("SELECT pages FROM meas_done WHERE doc=1").fetchone()
    s.close()
    ok("build_measures_found_torque_and_length", "torque" in types1 and "length" in types1)
    ok("build_measures_marks_done", done1 is not None and done1[0] == 1)

    # second run, nothing changed -> resumable skip: the SAME rows survive untouched (not deleted+reinserted)
    rc2 = BM.main()
    s = sqlite3.connect(sdb)
    ids2 = set(r[0] for r in s.execute("SELECT id FROM meas WHERE doc=1"))
    s.close()
    ok("build_measures_skip_is_noop", ids1 == ids2 and rc2 == 0)

    # a new page (page count changes) -> the doc is rebuilt, not skipped
    v = sqlite3.connect(vdb)
    v.execute("INSERT INTO pages(document_id,page_number,body_text) VALUES(1,2,?)",
              ("Curb weight 7700 lb.",))
    v.commit(); v.close()
    BM.main()
    s = sqlite3.connect(sdb)
    types3 = [r[0] for r in s.execute("SELECT type FROM meas WHERE doc=1")]
    done3 = s.execute("SELECT pages FROM meas_done WHERE doc=1").fetchone()
    s.close()
    ok("build_measures_rebuilds_on_page_count_change", "weight" in types3 and done3[0] == 2)

    # missing viewer.db -> a clean, non-crashing failure code
    BM.DB = os.path.join(d, "nope.db")
    ok("build_measures_missing_db_graceful", BM.main() == 2)
except Exception as e:
    failed.append("build_measures.py(%s)" % e)


# =====================================================================================================
# build_publog.py -- streams PUBLOG/FLIS CSVs into publog.db; build() is atomic (build-to-temp-then-swap)
# =====================================================================================================
try:
    import build_publog as BP

    d = tempfile.mkdtemp(prefix="publog_")
    src_empty = os.path.join(d, "src_empty"); os.makedirs(src_empty)
    out = os.path.join(d, "publog.db")

    # success path with NO source CSVs present at all: every stream() is a guarded [skip], so the build
    # still succeeds end-to-end with empty (but schema-correct) tables -- proves the plumbing (schema,
    # indexes, meta, atomic swap) doesn't depend on any particular CSV existing.
    ret = BP.build(src_empty, out, sample=0, log=lambda *a: None)
    ok("build_publog_returns_dbpath", ret == out)
    ok("build_publog_output_exists", os.path.exists(out))
    c = sqlite3.connect(out)
    tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    ok("build_publog_schema_created", {"nsn", "part", "cage", "charx", "meta"} <= tables)
    meta = dict(c.execute("SELECT k,v FROM meta").fetchall())
    ok("build_publog_meta_written", meta.get("src") == src_empty and meta.get("sample") == "0")
    c.close()

    # success path WITH real data: one P_FLIS_NSN.CSV row flows through _niin() + the column mapper.
    src_real = os.path.join(d, "src_real"); os.makedirs(src_real)
    with open(os.path.join(src_real, "P_FLIS_NSN.CSV"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["FSC", "NIIN", "INC", "ITEM_NAME", "SOS", "END_ITEM_NAME", "CANCELLED_NIIN"])
        w.writerow(["5305", "016741467", "12345", "BOLT, MACHINE", "D", "", ""])
    out2 = os.path.join(d, "publog2.db")
    BP.build(src_real, out2, sample=0, log=lambda *a: None)
    c = sqlite3.connect(out2)
    row = c.execute("SELECT niin,fsc,inc,item_name,sos FROM nsn").fetchone()
    c.close()
    ok("build_publog_real_row_flows_through", row == ("016741467", "5305", "12345", "BOLT, MACHINE", "D"))

    # the SAME output path rebuilt again must fully REPLACE the old file (old-vs-new content differs,
    # and rebuilding doesn't just append onto stale data).
    with open(os.path.join(src_real, "P_FLIS_NSN.CSV"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["FSC", "NIIN", "INC", "ITEM_NAME", "SOS", "END_ITEM_NAME", "CANCELLED_NIIN"])
        w.writerow(["1005", "011295768", "99999", "RIFLE, 5.56MM", "D", "", ""])
    BP.build(src_real, out2, sample=0, log=lambda *a: None)
    c = sqlite3.connect(out2)
    rows = c.execute("SELECT niin FROM nsn").fetchall()
    c.close()
    ok("build_publog_rebuild_replaces_not_appends", rows == [("011295768",)])

    # --- atomicity: a crash mid-build must leave the last-good publog.db untouched + clean up the temp ---
    guarded_db = os.path.join(d, "guarded.db")
    open(guarded_db, "wb").write(b"PREVIOUS-GOOD-BUILD-DO-NOT-TOUCH")
    real_build_into = BP._build_into
    def _boom_build_into(con, cur, src_dir, sample, log):
        cur.execute("CREATE TABLE marker(x)")   # partial progress that must never reach guarded_db
        con.commit()
        raise RuntimeError("simulated crash mid-build")
    BP._build_into = _boom_build_into
    raised = False
    try:
        BP.build(src_empty, guarded_db, sample=0, log=lambda *a: None)
    except RuntimeError:
        raised = True
    finally:
        BP._build_into = real_build_into
    ok("build_publog_atomicity_crash_propagates", raised)
    ok("build_publog_atomicity_original_untouched", open(guarded_db, "rb").read() == b"PREVIOUS-GOOD-BUILD-DO-NOT-TOUCH")
    tmp_path = guarded_db + ".building-%d" % os.getpid()
    ok("build_publog_atomicity_temp_cleaned_up", not os.path.exists(tmp_path))
except Exception as e:
    failed.append("build_publog.py(%s)" % e)


# =====================================================================================================
# build_conflicts.py -- precomputed conflict sweep over the most-frequent part subjects (append-only)
# =====================================================================================================
try:
    import build_conflicts as BC

    d = tempfile.mkdtemp(prefix="conflicts_")
    db = os.path.join(d, "viewer.db")
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE parts(id INTEGER PRIMARY KEY, name TEXT, fig_title TEXT)")
    c.executemany("INSERT INTO parts(name, fig_title) VALUES(?,?)",
                  [("", "BOLT, MACHINE"), ("", "BOLT, MACHINE"), ("valve", ""), ("", None)])
    c.commit(); c.close()

    subs = BC.subjects(db, 10)
    ok("build_conflicts_subjects_ranked_by_frequency", subs[0] == "BOLT, MACHINE" and "valve" in subs and len(subs) == 2)

    out = BC.sweep(db, limit=10)
    ok("build_conflicts_sweep_run_id", out["run_id"] == 1)
    ok("build_conflicts_sweep_subject_count", out["subjects"] == 2)

    import conflicts as _c
    scon = sqlite3.connect(_c._sidecar_path(db))
    runs = scon.execute("SELECT run_id, n_subjects, finished FROM runs").fetchall()
    results = scon.execute("SELECT subject FROM results WHERE run_id=1").fetchall()
    scon.close()
    ok("build_conflicts_run_recorded", len(runs) == 1 and runs[0][1] == 2 and runs[0][2])
    ok("build_conflicts_results_appended", {r[0] for r in results} == {"BOLT, MACHINE", "valve"})

    # a second sweep is a NEW run_id -- append-only, old rows never touched (R6)
    out2 = BC.sweep(db, limit=10, note="second sweep")
    ok("build_conflicts_second_sweep_new_run", out2["run_id"] == 2)
    scon = sqlite3.connect(_c._sidecar_path(db))
    all_runs = scon.execute("SELECT run_id FROM runs ORDER BY run_id").fetchall()
    scon.close()
    ok("build_conflicts_append_only_both_runs_kept", [r[0] for r in all_runs] == [1, 2])

    ok("build_conflicts_missing_db_arg_error", BC.main(["--db", os.path.join(d, "nope.db")]) == 1)
except Exception as e:
    failed.append("build_conflicts.py(%s)" % e)


for n in passed: print("PASS", n)
for n in failed: print("FAIL", n)
print("\n%d passed, %d failed (of %d checks across the Tier-1 corpus-build pipeline)" %
      (len(passed), len(failed), len(passed) + len(failed)))
sys.exit(1 if failed else 0)

# END OF FILE
