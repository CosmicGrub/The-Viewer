#!/usr/bin/env python3
"""THE VIEWER -- regression coverage for the Medium-tier audit fixes (findings #21-#32) that touch
Python code: xref.py's NSN truncation bug, dedup.py's process-randomized hash(), the OCR DPI/
megapixel ceiling, kg.py's coverage-meta + indexed lookup, masterfile.py's streaming rewrite
(verified for exact output-equivalence against the original list-materializing algorithm on
randomized data, including null-value edge cases), and make_cad.py's error-detail capture.
Self-contained; no real corpus. Run:  python tests/test_medium_fixes.py"""
import os, sys, sqlite3, tempfile, random
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)

passed, failed = [], []
def ok(name, cond):
    (passed if cond else failed).append(name)


# =====================================================================================================
# #21 -- xref.py's _norm_nsn no longer truncates an oversized digit run into a fabricated NSN
# =====================================================================================================
try:
    import xref
    ok("xref_norm_nsn_real_nsn", xref._norm_nsn("5305-01-674-1467") == "5305-01-674-1467")
    ok("xref_norm_nsn_bare_digits", xref._norm_nsn("5305016741467") == "5305-01-674-1467")
    ok("xref_norm_nsn_embedded", xref._norm_nsn("part 5305-01-674-1467 ref") == "5305-01-674-1467")
    # the actual bug: a 17-digit invoice/tracking number used to get silently sliced to a bogus
    # 13-digit "NSN" (len(d) >= 13); now it falls through to the raw string unchanged since no
    # \b-anchored 13-digit run exists inside it.
    oversized = "88123456789012345"
    ok("xref_norm_nsn_rejects_oversized_digit_run", xref._norm_nsn(oversized) == oversized)
    ok("xref_norm_nsn_passthrough_name", xref._norm_nsn("ALTERNATOR") == "ALTERNATOR")
except Exception as e:
    failed.append("xref_norm_nsn(%s)" % e)


# =====================================================================================================
# #22 -- dedup.py's shingle hashes are stable across process boundaries (not the randomized hash())
# =====================================================================================================
try:
    import subprocess
    outs = set()
    for _ in range(3):
        r = subprocess.run(
            [sys.executable, "-c", "import sys; sys.path.insert(0,%r); import dedup; "
             "print(sorted(dedup.shingles('the quick brown fox jumps over'))[:3])" % ENGINE],
            capture_output=True, text=True, timeout=30)
        outs.add(r.stdout.strip())
    ok("dedup_hash_stable_across_processes", len(outs) == 1 and outs != {""})
except Exception as e:
    failed.append("dedup_hash_stability(%s)" % e)


# =====================================================================================================
# #24 -- OCR DPI/megapixel ceiling: an oversized page is downscaled, a normal page is untouched
# =====================================================================================================
try:
    import fitz
    from PIL import Image
    import viewer_ingest as VI

    d = tempfile.mkdtemp(prefix="ocr_dpi_")
    big_pdf = os.path.join(d, "big.pdf")
    doc = fitz.open(); doc.new_page(width=48 * 72, height=36 * 72); doc.save(big_pdf); doc.close()
    png_big = VI._render_png(big_pdf, 1, dpi=200)
    mp_big = (Image.open(png_big).size[0] * Image.open(png_big).size[1]) / 1e6
    ok("ocr_dpi_oversized_page_capped", mp_big <= VI.OCR_MAX_MEGAPIXELS / 1e6 + 0.5)

    normal_pdf = os.path.join(d, "normal.pdf")
    doc = fitz.open(); doc.new_page(width=8.5 * 72, height=11 * 72); doc.save(normal_pdf); doc.close()
    png_normal = VI._render_png(normal_pdf, 1, dpi=200)
    sz = Image.open(png_normal).size
    ok("ocr_dpi_normal_page_unaffected", sz == (int(8.5 * 200), int(11 * 200)))
except Exception as e:
    failed.append("ocr_dpi_ceiling(%s)" % e)


# =====================================================================================================
# #27/#28 -- kg.py: coverage meta round-trips through build()->stats(); substring lookup still works
# via the two-tier (indexed exact/prefix, then slow substring fallback) query
# =====================================================================================================
try:
    import kg
    d = tempfile.mkdtemp(prefix="kg_medium_")
    kgdb = os.path.join(d, "kg.db")
    triples = [
        ("part", "Alternator", "on_figure", "figure", "FIG 4-2"),
        ("part", "Alternator", "in_vehicle", "vehicle", "HMMWV"),
        ("part", "Bracket", "on_figure", "figure", "FIG 4-2"),
    ]
    r = kg.build(kgdb, triples, meta={"figureparts_docs_sampled": "400", "figureparts_docs_total": "7300"})
    ok("kg_build_ok", r["nodes"] == 4 and r["edges"] == 3)   # Alternator, Bracket, FIG 4-2, HMMWV

    st = kg.stats(kgdb)
    ok("kg_coverage_meta_present", st["meta"].get("figureparts_docs_sampled") == "400"
       and st["meta"].get("figureparts_docs_total") == "7300")

    # exact match (indexed fast path)
    nb_exact = kg.neighbors(kgdb, "Alternator")
    ok("kg_exact_match", any(m.lower() == "alternator" for m in nb_exact["matched"]))
    # prefix match (indexed fast path)
    nb_prefix = kg.neighbors(kgdb, "Altern")
    ok("kg_prefix_match", any(m.lower() == "alternator" for m in nb_prefix["matched"]))
    # substring-in-the-middle match (slow fallback path -- "MMW" is not a prefix of "HMMWV")
    nb_mid = kg.neighbors(kgdb, "MMW")
    ok("kg_middle_substring_match_still_works", any(m.lower() == "hmmwv" for m in nb_mid["matched"]))
    # no match at all
    nb_none = kg.neighbors(kgdb, "nonexistent-xyz")
    ok("kg_no_match", nb_none["matched"] == [])

    # empty-db early return is untouched (no "meta" key) -- matches test_build_pipeline.py's own
    # exact-equality assertion on this same call shape
    ok("kg_stats_empty_db_shape_preserved",
       kg.stats(os.path.join(d, "nope.db")) == {"nodes": 0, "edges": 0, "by_type": {}})
except Exception as e:
    failed.append("kg_medium_fixes(%s)" % e)


# =====================================================================================================
# #25 -- masterfile.py's streaming build() is output-equivalent to the original list-materializing
# algorithm, including the null/empty-value edge case (a group whose only rows had val in (None,""))
# =====================================================================================================
try:
    import masterfile

    def _build_reference_oracle(db_path, measures_db, enrich_db, master_db):
        """The ORIGINAL (pre-fix) list-materializing algorithm, kept only as a diff oracle."""
        from collections import defaultdict
        con = sqlite3.connect(master_db)
        con.executescript("DROP TABLE IF EXISTS master_raw; DROP TABLE IF EXISTS master_filtered; "
                          "DROP TABLE IF EXISTS master_meta;")
        con.executescript(masterfile.SCHEMA)
        doc_veh = {}
        v = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
        for did, veh in v.execute("SELECT id, COALESCE(vehicle,'') FROM documents"):
            doc_veh[did] = (veh or "").strip()
        v.close()
        raw = []
        m = sqlite3.connect("file:%s?mode=ro" % measures_db, uri=True)
        for doc, page, ty, unit, val, val2, tol, ctx in m.execute(
                "SELECT doc,page,type,unit,value,value2,tolerance,context FROM meas"):
            label = doc_veh.get(doc, "") or ("doc%s" % doc)
            subj = label.strip().lower()
            raw.append((subj, label, doc, page, ty, unit, val, val2, tol, ctx, "corpus"))
        m.close()
        corpus_have = defaultdict(set)
        for r in raw: corpus_have[r[0]].add(r[4])
        if os.path.exists(enrich_db):
            e = sqlite3.connect("file:%s?mode=ro" % enrich_db, uri=True)
            for subj, label, ty, unit, val, val2, tol, ctx in e.execute(
                    "SELECT subject,subject_label,type,unit,value,value2,tolerance,context FROM ext_meas"):
                subj = (subj or "").strip().lower()
                if ty in corpus_have.get(subj, ()): continue
                raw.append((subj, label or subj, None, None, ty, unit, val, val2, tol, ctx, "external"))
            e.close()
        con.executemany(
            "INSERT INTO master_raw(subject,subject_label,doc,page,type,unit,value,value2,tolerance,context,origin) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)", raw)
        groups = defaultdict(list); labels = {}
        for subj, label, doc, page, ty, unit, val, val2, tol, ctx, origin in raw:
            groups[(subj, ty, unit, origin)].append(val); labels[subj] = label
        filt = []
        for (subj, ty, unit, origin), vals in groups.items():
            rep, low, high, n = masterfile._canonical(vals)
            auth = 1 if origin == "corpus" else 0
            note = "authoritative (corpus)" if auth else "external reference — unconfirmed"
            filt.append((subj, labels.get(subj, subj), ty, unit, rep, low, high, n, origin, auth, note))
        con.executemany(
            "INSERT INTO master_filtered(subject,subject_label,type,unit,value,low,high,n,origin,authoritative,note) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)", filt)
        n_subj = len({r[0] for r in raw})
        meta = {"n_subjects": str(n_subj), "n_raw": str(len(raw)), "n_filtered": str(len(filt)),
                "corpus_raw": str(sum(1 for r in raw if r[10] == "corpus")),
                "external_raw": str(sum(1 for r in raw if r[10] == "external"))}
        con.commit(); con.close()
        return {"subjects": n_subj, "raw": len(raw), "filtered": len(filt),
                "corpus": int(meta["corpus_raw"]), "external": int(meta["external_raw"])}

    def _sortkey(rows):
        return sorted(rows, key=lambda r: tuple("" if x is None else str(x) for x in r))

    random.seed(4242)
    VEHICLES = ["HMMWV", "M915 Truck", "Forklift", None, ""]
    TYPES = ["length", "weight", "torque", "capacity"]
    UNITS = ["in", "lb", "ft-lb", "gal"]

    def _rand_val():
        r = random.random()
        if r < 0.15: return None            # exercises the null-value edge case (finding #25's
        if r < 0.25: return ""               # trickiest correctness detail: a group whose only
        if r < 0.6: return str(random.randint(1, 500))
        return random.choice(["N/A", "approx", "see note", str(random.randint(1, 500))])

    all_trials_ok = True
    for trial in range(10):
        d = tempfile.mkdtemp(prefix="masterfile_eq_")
        dbp = os.path.join(d, "viewer.db"); mdb = os.path.join(d, "measures.db"); edb = os.path.join(d, "enrich.db")
        mf_old = os.path.join(d, "old.db"); mf_new = os.path.join(d, "new.db")

        a = sqlite3.connect(dbp); a.execute("CREATE TABLE documents(id INTEGER PRIMARY KEY, vehicle TEXT)")
        docs = [(i, random.choice(VEHICLES)) for i in range(1, 6)]
        a.executemany("INSERT INTO documents VALUES(?,?)", docs); a.commit(); a.close()

        m = sqlite3.connect(mdb)
        m.execute("CREATE TABLE meas(doc INT,page INT,type TEXT,unit TEXT,value TEXT,value2 TEXT,tolerance TEXT,context TEXT)")
        rows = [(random.choice([x[0] for x in docs]), random.randint(1, 50), random.choice(TYPES), random.choice(UNITS),
                  _rand_val(), None, None, "ctx") for _ in range(random.randint(5, 60))]
        m.executemany("INSERT INTO meas VALUES(?,?,?,?,?,?,?,?)", rows); m.commit(); m.close()

        e = sqlite3.connect(edb)
        e.execute("CREATE TABLE ext_meas(subject TEXT,subject_label TEXT,type TEXT,unit TEXT,value TEXT,value2 TEXT,"
                  "tolerance TEXT,context TEXT,source TEXT,source_url TEXT)")
        erows = [(random.choice(VEHICLES) or "unk", random.choice(VEHICLES) or "unk", random.choice(TYPES),
                   random.choice(UNITS), _rand_val(), None, None, "ectx", "s", "u") for _ in range(random.randint(0, 25))]
        e.executemany("INSERT INTO ext_meas(subject,subject_label,type,unit,value,value2,tolerance,context,source,source_url) "
                     "VALUES(?,?,?,?,?,?,?,?,?,?)", erows); e.commit(); e.close()

        summ_old = _build_reference_oracle(dbp, mdb, edb, mf_old)
        summ_new = masterfile.build(dbp, mdb, edb, mf_new)
        if summ_old != summ_new:
            all_trials_ok = False; break

        co = sqlite3.connect(mf_old); cn = sqlite3.connect(mf_new)
        raw_old = _sortkey(co.execute("SELECT subject,subject_label,doc,page,type,unit,value,value2,tolerance,context,origin FROM master_raw").fetchall())
        raw_new = _sortkey(cn.execute("SELECT subject,subject_label,doc,page,type,unit,value,value2,tolerance,context,origin FROM master_raw").fetchall())
        filt_old = _sortkey(co.execute("SELECT subject,subject_label,type,unit,value,low,high,n,origin,authoritative,note FROM master_filtered").fetchall())
        filt_new = _sortkey(cn.execute("SELECT subject,subject_label,type,unit,value,low,high,n,origin,authoritative,note FROM master_filtered").fetchall())
        co.close(); cn.close()
        if raw_old != raw_new or filt_old != filt_new:
            all_trials_ok = False; break

    ok("masterfile_streaming_equivalent_to_original_10_trials", all_trials_ok)

    # a dedicated, deterministic null-value-only-group case (the trickiest edge case, spelled out
    # rather than relying on random chance to hit it): a (subject,type) whose every row has val=None.
    d2 = tempfile.mkdtemp(prefix="masterfile_nullgroup_")
    dbp2 = os.path.join(d2, "viewer.db"); mdb2 = os.path.join(d2, "measures.db"); mf2 = os.path.join(d2, "m.db")
    a = sqlite3.connect(dbp2); a.execute("CREATE TABLE documents(id INTEGER PRIMARY KEY, vehicle TEXT)")
    a.execute("INSERT INTO documents VALUES(1,'HMMWV')"); a.commit(); a.close()
    m = sqlite3.connect(mdb2)
    m.execute("CREATE TABLE meas(doc INT,page INT,type TEXT,unit TEXT,value TEXT,value2 TEXT,tolerance TEXT,context TEXT)")
    m.executemany("INSERT INTO meas VALUES(?,?,?,?,?,?,?,?)", [
        (1, 1, "torque", "ft-lb", None, None, None, "null val"),
        (1, 2, "torque", "ft-lb", "", None, None, "empty val"),
        (1, 3, "weight", "lb", "500", None, None, "real val")])
    m.commit(); m.close()
    masterfile.build(dbp2, mdb2, None, mf2)
    c2 = sqlite3.connect(mf2)
    torque_row = c2.execute("SELECT value,low,high,n FROM master_filtered WHERE type='torque'").fetchone()
    weight_row = c2.execute("SELECT value,low,high,n FROM master_filtered WHERE type='weight'").fetchone()
    c2.close()
    ok("masterfile_null_only_group_yields_n0_row", torque_row == ("", "", "", 0))
    ok("masterfile_real_value_group_unaffected", weight_row == ("500", "500", "500", 1))
except Exception as e:
    failed.append("masterfile_streaming_equivalence(%s)" % e)


# =====================================================================================================
# #32 -- make_cad.py captures the actual error reason instead of a bare ('fail', nsn)
# =====================================================================================================
try:
    import make_cad, cad_render
    import unittest.mock as mock

    with mock.patch.object(cad_render, "ensure", side_effect=RuntimeError("boom")):
        st, nsn, err = make_cad._render_one(("1234-56-789-0123", "BOLT", "", "v3"))
    ok("make_cad_captures_exception_detail", st == "fail" and "RuntimeError" in err and "boom" in err)

    with mock.patch.object(cad_render, "ensure", return_value=None):
        st, nsn, err = make_cad._render_one(("1234-56-789-0123", "BOLT", "", "v3"))
    ok("make_cad_captures_no_path_reason", st == "fail" and err is not None)

    with mock.patch.object(cad_render, "ensure", return_value="/some/path.png"):
        st, nsn, err = make_cad._render_one(("1234-56-789-0123", "BOLT", "", "v3"))
    ok("make_cad_success_has_no_error", st == "done" and err is None)
except Exception as e:
    failed.append("make_cad_error_capture(%s)" % e)


for n in passed: print("PASS", n)
for n in failed: print("FAIL", n)
print("\n%d passed, %d failed (of %d checks for Medium-tier audit fixes #21-#32)" %
      (len(passed), len(failed), len(passed) + len(failed)))
sys.exit(1 if failed else 0)

# END OF FILE
