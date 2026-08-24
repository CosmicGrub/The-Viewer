#!/usr/bin/env python3
"""THE VIEWER -- regression coverage for the Medium-tier audit fixes (findings #21-#32) that touch
Python code: xref.py's NSN truncation bug, dedup.py's process-randomized hash(), the OCR DPI/
megapixel ceiling, kg.py's coverage-meta + indexed lookup, masterfile.py's streaming rewrite
(verified for exact output-equivalence against the original list-materializing algorithm on
randomized data, including null-value edge cases), cad_render.py/dimscad.py's deduped _box() mesh
builder (now shared via cad_mesh.box_mesh(), checked for outward-facing winding on every face), and
make_cad.py's error-detail capture. #33-#34 add coverage a follow-up xhigh code review of that same
_box()-dedup/atomic-build-extraction diff found missing: the OCR_LOCK_TIMEOUT_SECONDS/
OCR_PAGE_TIMEOUT_SECONDS cross-clamp, and proctree.py's kill_tree()/new_process_group_flags() (which
previously had only indirect coverage via ocr_supervisor.py's _kill_tree wrapper). #35-#37 cover the
v2/v3 CAD-tier bit-rot fix: TIER_STYLE collapsing 'lite' onto 'modern's 'v3' style (v2 and v3 render
byte-identical pixels since CAD_VERSION 7 unified colour+texture across every tier) so the two tiers
share one render + one ensure()/cache_path() cache entry instead of independently rendering AND
disk-caching a visually-identical copy; render_spin()'s shared-texture optimization (the deterministic
per-material surface texture computed once per spin sheet instead of once per frame, verified against
the pre-optimization per-frame-independent computation for no visual regression); and TIER_FRAMES, the
tier-keyed spin-frame-count fallback that keeps 'lite' defaulting to fewer turntable frames than
'modern' even though the two tiers' render *style* collapsed together.
Self-contained; no real corpus. Run:  python tests/test_medium_fixes.py"""
import os, sys, sqlite3, subprocess, tempfile, random
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
    import pymupdf as fitz
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

    # Review finding: the old 100-DPI floor could itself push a sufficiently large page's raster
    # back OVER the cap (defeating the fix's own guarantee) -- reproduced by reviewers with a
    # 100x150in page (150,000 sq in -> forced-100-DPI raster = 150MP, 6x over a 25MP cap).
    huge_pdf = os.path.join(d, "huge.pdf")
    doc = fitz.open(); doc.new_page(width=100 * 72, height=150 * 72); doc.save(huge_pdf); doc.close()
    png_huge = VI._render_png(huge_pdf, 1, dpi=200)
    mp_huge = (Image.open(png_huge).size[0] * Image.open(png_huge).size[1]) / 1e6
    ok("ocr_dpi_floor_never_exceeds_cap", mp_huge <= VI.OCR_MAX_MEGAPIXELS / 1e6 + 0.5)

    # _capped_dpi() is the shared helper both render backends now use (review finding: the
    # original fix lived only in the PyMuPDF branch, leaving the pdftoppm fallback -- the
    # documented path for machines without PyMuPDF -- completely uncapped).
    ok("capped_dpi_zero_dims_unchanged", VI._capped_dpi(0, 0, 200) == 200)
    ok("capped_dpi_small_page_unchanged", VI._capped_dpi(8.5, 11, 200) == 200)
    ok("capped_dpi_matches_huge_page_case", VI._capped_dpi(100, 150, 200) == 40)

    # _pdftoppm_page_size_in() degrades gracefully (fail-open) when pdfinfo is unavailable/fails
    w, h = VI._pdftoppm_page_size_in("/no/such/file.pdf", 1)
    ok("pdftoppm_page_size_graceful_on_missing_file", w is None and h is None)
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
        # a mid-string match COEXISTING with an exact match for the same query -- review finding:
        # the first version of #28's fix silently dropped this.
        ("part", "M998 HMMWV Bracket", "on_figure", "figure", "FIG 9-1"),
        # literal SQL LIKE wildcards in a label -- review finding: unescaped, these corrupted matching.
        ("part", "50% Duty Solenoid", "has_spec", "spec", "12V"),
        ("part", "50-999 Widget", "on_figure", "figure", "FIG 2-1"),
    ]
    r = kg.build(kgdb, triples, meta={"figureparts_docs_sampled": "400", "figureparts_docs_total": "7300"})
    ok("kg_build_ok", r["nodes"] == 10 and r["edges"] == 6)

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

    # regression: an exact match must NOT suppress a coexisting mid-string match (the bug caught
    # during review -- the first version of this fix dropped "M998 HMMWV Bracket" whenever the
    # exact "HMMWV" node also existed, since the substring fallback only ran when the fast path
    # found NOTHING at all).
    nb_both = kg.neighbors(kgdb, "HMMWV")
    both_lower = {m.lower() for m in nb_both["matched"]}
    ok("kg_exact_and_midstring_coexist", "hmmwv" in both_lower and "m998 hmmwv bracket" in both_lower)

    # regression: a literal "%" in the query must not act as an unescaped SQL LIKE wildcard
    nb_wild = kg.neighbors(kgdb, "50%")
    wild_lower = {m.lower() for m in nb_wild["matched"]}
    ok("kg_wildcard_query_matches_literal", "50% duty solenoid" in wild_lower)
    ok("kg_wildcard_query_no_false_match", "50-999 widget" not in wild_lower)

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
        # corroboration-count fix (masterfile.py): build() now dedupes corpus rows by (tm-or-doc,
        # page) identity per group before counting them -- mirrored here too so this oracle stays a
        # true diff reference for the NEW behavior, not just an accidental pass because this seed's
        # synthetic rows never collide on (doc,page) within a group. This test's synthetic documents
        # table has no tm_number column, so identity always falls back to "doc%s"%doc, same as
        # build()'s own fallback path.
        dedup_seen = set()
        for subj, label, doc, page, ty, unit, val, val2, tol, ctx, origin in raw:
            labels[subj] = label
            key = (subj, ty, unit, origin)
            if origin == "corpus":
                dkey = (key, "doc%s" % doc, page)
                if dkey in dedup_seen:
                    continue
                dedup_seen.add(dkey)
            groups[key].append(val)
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

    # a dedicated, deterministic (doc,page) collision case (corroboration-count fix), spelled out
    # rather than relying on the random trials above to happen to hit it: two rows sharing the exact
    # same doc+page must dedupe to n=1, both in build() and in the oracle mirrored above.
    d3 = tempfile.mkdtemp(prefix="masterfile_corrob_")
    dbp3 = os.path.join(d3, "viewer.db"); mdb3 = os.path.join(d3, "measures.db"); mf3 = os.path.join(d3, "m.db")
    a = sqlite3.connect(dbp3); a.execute("CREATE TABLE documents(id INTEGER PRIMARY KEY, vehicle TEXT)")
    a.execute("INSERT INTO documents VALUES(1,'HMMWV')"); a.commit(); a.close()
    m = sqlite3.connect(mdb3)
    m.execute("CREATE TABLE meas(doc INT,page INT,type TEXT,unit TEXT,value TEXT,value2 TEXT,tolerance TEXT,context TEXT)")
    m.executemany("INSERT INTO meas VALUES(?,?,?,?,?,?,?,?)", [
        (1, 9, "capacity", "gal", "25", None, None, "Fuel 25 gal"),
        (1, 9, "capacity", "gal", "25", None, None, "same doc+page re-cited (dup)")])
    m.commit(); m.close()
    masterfile.build(dbp3, mdb3, None, mf3)
    c3 = sqlite3.connect(mf3)
    cap_row = c3.execute("SELECT value,n FROM master_filtered WHERE type='capacity'").fetchone()
    c3.close()
    ok("masterfile_same_doc_page_collision_dedupes_to_n1", cap_row == ("25", 1))
except Exception as e:
    failed.append("masterfile_streaming_equivalence(%s)" % e)


# =====================================================================================================
# #29 -- cad_render.py's and dimscad.py's duplicate _box() mesh builders are deduped onto one shared
# cad_mesh.box_mesh() (0-based V/F, cad_render.py's existing internal convention). The concrete,
# code-computable regression guard for the winding/normal-flip risk the original audit finding raised:
# every face of BOTH flavors used through the shared function (cad_render's centered box, dimscad's
# corner-anchored box with its l->x / h->y / w->z axis-mapping gotcha) must wind with its outward
# right-hand-rule normal pointing away from the box centroid.
# =====================================================================================================
try:
    import cad_mesh, cad_render, dimscad

    def _face_normal(V, f):
        # Deliberately re-derives the same cross-product formula cad_render.to_stl() already implements
        # for its own STL facet-normal output -- NOT shared with it on purpose. A winding/normal-flip bug
        # here should be caught independently of whatever cad_render.py itself does; sharing one helper
        # between the code under test and the test verifying it would make this check circular (review
        # finding: flag the duplication as deliberate so a future "simplify" pass doesn't merge them).
        a, b, c = V[f[0]], V[f[1]], V[f[2]]
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        return (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)

    def _all_faces_outward(V, F):
        cx = sum(v[0] for v in V) / len(V); cy = sum(v[1] for v in V) / len(V); cz = sum(v[2] for v in V) / len(V)
        for f in F:
            nx, ny, nz = _face_normal(V, f)
            fcx = sum(V[i][0] for i in f) / len(f); fcy = sum(V[i][1] for i in f) / len(f); fcz = sum(V[i][2] for i in f) / len(f)
            if nx * (fcx - cx) + ny * (fcy - cy) + nz * (fcz - cz) <= 0:
                return False
        return True

    dims_cases = [(2, 3, 4), (1, 1, 1), (0.3, 9.4, 2.0), (5.0, 0.1, 5.0)]
    for i, (a, b, c) in enumerate(dims_cases):
        ok("cad_mesh_box_center_outward_%d" % i, _all_faces_outward(*cad_mesh.box_mesh(a, b, c, origin="center")))
        ok("cad_mesh_box_corner_outward_%d" % i, _all_faces_outward(*cad_mesh.box_mesh(a, b, c, origin="corner")))

    # cad_render._box() is the SAME code, just relocated: byte-identical (V, F, and to_obj() text) for any
    # (w,h,d), proving this half of the dedup is a pure, zero-behavior-change refactor.
    def _old_cad_box(w, h, d):
        x, y, z = w / 2, h / 2, d / 2
        V = [[-x, -y, -z], [x, -y, -z], [x, y, -z], [-x, y, -z], [-x, -y, z], [x, -y, z], [x, y, z], [-x, y, z]]
        F = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [2, 3, 7, 6], [1, 2, 6, 5], [0, 4, 7, 3]]
        return V, F
    for i, args in enumerate([(2, 3, 4), (1, 1, 1), (0.5, 7.25, 0.001)]):
        Vn, Fn = cad_render._box(*args); Vo, Fo = _old_cad_box(*args)
        ok("cad_render_box_byte_identical_%d" % i, Vn == Vo and Fn == Fo)
        ok("cad_render_box_to_obj_byte_identical_%d" % i, cad_render.to_obj(Vn, Fn) == cad_render.to_obj(Vo, Fo))
        ok("cad_render_box_outward_%d" % i, _all_faces_outward(Vn, Fn))

    # dimscad._box() is geometrically identical to the original hand-rolled version: same 8 corners (as a
    # set) at the same l/w/h extents (its axis-mapping gotcha -- the 2nd positional arg 'w' controls the
    # mesh's z-extent, NOT y -- preserved exactly), same face count, outward-consistent winding. (Literal
    # vertex ENUMERATION order legitimately changes -- it was never part of any external contract: no
    # consumer of dimscad's OBJ parses vertex order, only that it is a well-formed box.)
    def _old_dims_box(l, w, h):
        l = max(l, 0.05); w = max(w, 0.05); h = max(h, 0.05)
        V = [(0, 0, 0), (l, 0, 0), (l, 0, w), (0, 0, w), (0, h, 0), (l, h, 0), (l, h, w), (0, h, w)]
        F = [(1, 2, 3, 4), (5, 8, 7, 6), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 8, 4), (4, 8, 5, 1)]
        return V, F
    for i, args in enumerate([(2, 1, 0.5), (4.0, 2.0, 0.25), (0.01, 0.01, 0.01)]):
        Vn, Fn = dimscad._box(*args); Vo, Fo = _old_dims_box(*args)
        l, w, h = args; l = max(l, 0.05); w = max(w, 0.05); h = max(h, 0.05)
        same_corners = (sorted(tuple(round(x, 6) for x in v) for v in Vn) ==
                         sorted(tuple(round(x, 6) for x in v) for v in Vo))
        extents_ok = (min(v[0] for v in Vn) == 0 and max(v[0] for v in Vn) == l and
                      min(v[1] for v in Vn) == 0 and max(v[1] for v in Vn) == h and
                      min(v[2] for v in Vn) == 0 and max(v[2] for v in Vn) == w)
        ok("dimscad_box_same_corner_set_%d" % i, same_corners)
        ok("dimscad_box_axis_mapping_preserved_%d" % i, extents_ok)
        ok("dimscad_box_outward_and_facecount_%d" % i, _all_faces_outward(Vn, Fn) and len(Fn) == 6 == len(Fo))

    # dimscad.build_obj()'s box path moved from literal-1-based F tuples to computed 0-based-plus-1 emission
    # at write time (matching cad_render.to_obj()'s pattern) -- confirm the emitted OBJ is well-formed
    # (every face index inside [1, vertex_count]), i.e. the +1 conversion actually happened.
    obj = dimscad.build_obj("box", {"length": 4.0, "width": 2.0, "height": 0.25})
    vcount = obj.count("\nv ")
    idxs = [int(tok) for ln in obj.splitlines() if ln.startswith("f ") for tok in ln.split()[1:]]
    ok("dimscad_build_obj_box_indices_1_based_in_range", vcount == 8 and idxs and min(idxs) == 1 and max(idxs) == 8)
    # non-box primitives (cylinder/washer/hex) still hand-roll literal 1-based F and must be untouched --
    # asserted the same way as the box check above (indices in [1, vcount]), not just "the OBJ is non-empty":
    # that weaker check would still pass even if the zero_based bookkeeping this diff replaced (or its
    # per-call-site replacement) ever leaked a 0-based conversion onto a non-box primitive.
    cyl_obj = dimscad.build_obj("cylinder", {"diameter": 0.5, "length": 2.0})
    cyl_vcount = cyl_obj.count("\nv ")
    cyl_idxs = [int(tok) for ln in cyl_obj.splitlines() if ln.startswith("f ") for tok in ln.split()[1:]]
    ok("dimscad_build_obj_cylinder_unaffected",
       cyl_vcount > 0 and bool(cyl_idxs) and min(cyl_idxs) == 1 and max(cyl_idxs) == cyl_vcount)

    # both files delegate to cad_mesh; neither imports the other (no new circular-import surface)
    ok("cad_render_delegates_to_cad_mesh", cad_render.cad_mesh is cad_mesh)
    ok("dimscad_delegates_to_cad_mesh", dimscad.cad_mesh is cad_mesh)
    ok("cad_mesh_has_no_reverse_dependency", not hasattr(cad_mesh, "cad_render") and not hasattr(cad_mesh, "dimscad"))
except Exception as e:
    failed.append("box_mesh_dedup(%s)" % e)


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


# =====================================================================================================
# #33 -- viewer_ingest.py's OCR_LOCK_TIMEOUT_SECONDS is clamped to never exceed OCR_PAGE_TIMEOUT_SECONDS.
# Review finding: the two are independently operator-configurable via env vars with no cross-check: if
# VIEWER_OCR_PAGE_TIMEOUT is set below OCR_LOCK_TIMEOUT_SECONDS's 20s default, a single lock-acquire
# could outlast the whole page's outer deadline, defeating the split's "fail fast on a busy lock" intent.
# Module-level constants are computed at import time, so the only faithful way to test an env-var
# override is a fresh subprocess -- re-importing an already-imported module in this process wouldn't
# re-run the top-level os.environ.get() calls.
# =====================================================================================================
try:
    default_check = subprocess.run(
        [sys.executable, "-c", "import sys; sys.path.insert(0, %r); import viewer_ingest as V; "
         "print(V.OCR_LOCK_TIMEOUT_SECONDS, V.OCR_PAGE_TIMEOUT_SECONDS)" % ENGINE],
        capture_output=True, text=True, timeout=30)
    lock_default, page_default = (int(x) for x in default_check.stdout.split())
    ok("ocr_lock_timeout_default_under_page_timeout", lock_default == 20 and page_default == 120 and lock_default < page_default)

    clamp_env = dict(os.environ); clamp_env["VIEWER_OCR_PAGE_TIMEOUT"] = "5"; clamp_env.pop("VIEWER_OCR_LOCK_TIMEOUT", None)
    clamp_check = subprocess.run(
        [sys.executable, "-c", "import sys; sys.path.insert(0, %r); import viewer_ingest as V; "
         "print(V.OCR_LOCK_TIMEOUT_SECONDS, V.OCR_PAGE_TIMEOUT_SECONDS)" % ENGINE],
        capture_output=True, text=True, timeout=30, env=clamp_env)
    lock_clamped, page_tight = (int(x) for x in clamp_check.stdout.split())
    # Without the clamp this would print "20 5" -- the exact misconfiguration the review flagged, where
    # a lock-acquire wait (20s) can outlast the outer per-page deadline (5s) it's supposed to live inside.
    ok("ocr_lock_timeout_clamped_to_tighter_page_timeout", page_tight == 5 and lock_clamped == 5)

    unclamped_env = dict(os.environ); unclamped_env["VIEWER_OCR_PAGE_TIMEOUT"] = "300"; unclamped_env.pop("VIEWER_OCR_LOCK_TIMEOUT", None)
    unclamped_check = subprocess.run(
        [sys.executable, "-c", "import sys; sys.path.insert(0, %r); import viewer_ingest as V; "
         "print(V.OCR_LOCK_TIMEOUT_SECONDS, V.OCR_PAGE_TIMEOUT_SECONDS)" % ENGINE],
        capture_output=True, text=True, timeout=30, env=unclamped_env)
    lock_unclamped, page_loose = (int(x) for x in unclamped_check.stdout.split())
    # A page timeout well above the lock-timeout default must NOT be clamped down -- the fix is a min(),
    # not a hardcoded override; the lock timeout should stay at its own 20s default here.
    ok("ocr_lock_timeout_not_clamped_when_page_timeout_generous", page_loose == 300 and lock_unclamped == 20)
except Exception as e:
    failed.append("ocr_lock_timeout_clamp(%s)" % e)


# =====================================================================================================
# #34 -- proctree.py (extracted from ocr_supervisor.py's _kill_tree + run_timeout.py's inline kill logic)
# gets direct unit coverage. Previously only exercised indirectly through ocr_supervisor.py's own
# _kill_tree wrapper (test_ocr_supervisor.py) -- run_timeout.py's half of the delegation, and
# new_process_group_flags(), had zero coverage of their own (xhigh review finding).
# =====================================================================================================
try:
    import proctree, subprocess as _sp, time as _time

    flags = proctree.new_process_group_flags()
    if os.name == "nt":
        ok("proctree_flags_windows_process_group", flags == getattr(_sp, "CREATE_NEW_PROCESS_GROUP", 0) and flags != 0)
    else:
        ok("proctree_flags_posix_noop", flags == 0)

    # A live, real child process (and, on Windows, a grandchild it spawns) actually dies, not just its
    # immediate pid -- kill_tree()'s whole reason to exist over a bare proc.kill().
    if os.name == "nt":
        parent = _sp.Popen(["cmd", "/c", "start", "/min", "cmd", "/c", "ping -n 30 127.0.0.1 >nul"],
                            creationflags=proctree.new_process_group_flags())
    else:
        parent = _sp.Popen(["sh", "-c", "sleep 30"])
    _time.sleep(0.6)
    proctree.kill_tree(parent, wait_after=10)
    try:
        rc = parent.wait(timeout=5)
        ok("proctree_kill_tree_parent_terminates", rc is not None)
    except _sp.TimeoutExpired:
        ok("proctree_kill_tree_parent_terminates", False)

    # kill_tree() must not raise even against an already-dead process (both internal try/excepts covering it).
    already_dead = _sp.Popen([sys.executable, "-c", "pass"])
    already_dead.wait(timeout=5)
    raised = False
    try:
        proctree.kill_tree(already_dead, wait_after=2)
    except Exception:
        raised = True
    ok("proctree_kill_tree_tolerates_already_dead_process", not raised)
except Exception as e:
    failed.append("proctree_direct_coverage(%s)" % e)


# =====================================================================================================
# #35 -- cad_render.py: 'lite' (v2) and 'modern' (v3) render BYTE-IDENTICAL pixels (the only style
# branches left in render() -- y-flip, specular -- both key off `style != "v1"`), so TIER_STYLE now
# routes 'lite' onto the same 'v3' style as 'modern' instead of independently rendering AND
# disk-caching a visually-identical copy. Checked through the REAL ensure()/cache_path() path (not
# just render()'s raw pixels): the cache KEY collapses too, and a second tier's request reuses the
# first tier's already-warm cache entry without a second render() call.
# =====================================================================================================
try:
    import cad_render as CR
    import unittest.mock as mock, shutil, re as _re

    nsn_t, nm_t, ch_t = "3110-01-777-7001", "BEARING, BALL", "OUTSIDE DIAMETER: 2.0 IN WIDTH: 0.6 IN"

    # TIER_STYLE: 'lite' now resolves to the same style as 'modern'; 'legacy' is untouched.
    ok("tier_style_lite_collapsed_onto_modern", CR.TIER_STYLE["lite"] == CR.TIER_STYLE["modern"] == "v3")
    ok("tier_style_legacy_still_v1", CR.TIER_STYLE["legacy"] == "v1")

    if CR.Image is not None:
        # raw render() pixels: v2 and v3 are byte-identical for the same part; v1 is NOT (still distinct).
        im_v2 = CR.render(nm_t, ch_t, nsn_t, w=160, h=120, style="v2")
        im_v3 = CR.render(nm_t, ch_t, nsn_t, w=160, h=120, style="v3")
        im_v1 = CR.render(nm_t, ch_t, nsn_t, w=160, h=120, style="v1")
        ok("render_v2_v3_byte_identical_pixels", im_v2.tobytes() == im_v3.tobytes())
        ok("render_v1_still_visually_distinct", im_v1.tobytes() != im_v3.tobytes())

        # cache_path(): the two styles TIER_STYLE now maps 'lite'/'modern' onto resolve to the SAME file.
        cdir = tempfile.mkdtemp(prefix="cad_cachekey_")
        try:
            p_modern = CR.cache_path(cdir, nsn_t, CR.TIER_STYLE["modern"])
            p_lite = CR.cache_path(cdir, nsn_t, CR.TIER_STYLE["lite"])
            p_legacy = CR.cache_path(cdir, nsn_t, CR.TIER_STYLE["legacy"])
            ok("cache_path_lite_and_modern_share_key", p_modern == p_lite)
            ok("cache_path_legacy_still_separate_key", p_legacy != p_modern)

            # ensure(): a 'lite'-tier request after a 'modern'-tier request finds the cache already warm
            # (same path, no second render() call) -- the actual dollars-and-cents fix for the mixed-fleet
            # double-render/double-cache the audit finding described.
            call_count = {"n": 0}
            real_render = CR.render
            def _counting_render(*a, **kw):
                call_count["n"] += 1
                return real_render(*a, **kw)
            with mock.patch.object(CR, "render", side_effect=_counting_render):
                out_modern = CR.ensure(nsn_t, nm_t, ch_t, cdir, style=CR.TIER_STYLE["modern"])
                out_lite = CR.ensure(nsn_t, nm_t, ch_t, cdir, style=CR.TIER_STYLE["lite"])
            ok("ensure_lite_reuses_modern_cache_path", out_modern is not None and out_modern == out_lite)
            ok("ensure_lite_after_modern_renders_only_once", call_count["n"] == 1)

            # only ONE cached PNG exists for this nsn (not a "_v2.png" + "_v3.png" pair)
            files = sorted(f for f in os.listdir(cdir) if f.startswith(_re.sub(r"[^0-9A-Za-z]", "", nsn_t)))
            ok("only_one_cache_file_written_for_lite_and_modern", files == [os.path.basename(out_modern)])
        finally:
            shutil.rmtree(cdir, ignore_errors=True)
    else:
        failed.append("PIL_unavailable_35")
except Exception as e:
    failed.append("cad_render_v2_v3_cache_collapse(%s)" % e)


# =====================================================================================================
# #36 -- cad_render.py's render_spin(): the deterministic material surface texture is computed ONCE per
# spin sheet (not once per frame) and shared across all N frames via render()'s new surface_texture=
# parameter. Verified two ways: (a) _surface_texture() is actually called only once for an N-frame
# sheet (the real performance fix), and (b) a couple of the sheet's frames are pixel-identical to the
# SAME frame rendered independently the pre-optimization way (render() computing its own texture
# internally, i.e. no surface_texture= passed) -- proving the shared-texture optimization introduced no
# visual regression. Also: render()'s existing single-image callers (no surface_texture= passed) are
# unaffected -- they still compute the texture internally exactly as before.
# =====================================================================================================
try:
    import cad_render as CR
    import unittest.mock as mock, math

    nsn_s, nm_s, ch_s = "3110-01-777-7002", "BEARING, BALL", "OUTSIDE DIAMETER: 2.0 IN WIDTH: 0.6 IN"

    if CR.Image is not None:
        n, fw, fh = 8, 140, 110
        tex_calls = {"n": 0}
        real_tex = CR._surface_texture
        def _counting_tex(*a, **kw):
            tex_calls["n"] += 1
            return real_tex(*a, **kw)
        with mock.patch.object(CR, "_surface_texture", side_effect=_counting_tex):
            sheet, frames = CR.render_spin(nm_s, ch_s, nsn_s, n=n, style="v3", fw=fw, fh=fh)
        ok("render_spin_frame_count_and_sheet_size_correct",
           frames == n and sheet.size == (fw * n, fh))
        ok("render_spin_computes_surface_texture_exactly_once", tex_calls["n"] == 1)

        # a couple of frames must be pixel-identical to the pre-optimization independent-per-frame
        # computation (render() with no surface_texture= -> computes its own internally, same seed/klass).
        for i in (0, n - 1):
            ya = (i / n) * (2 * math.pi)
            expected = CR.render(nm_s, ch_s, nsn_s, w=fw, h=fh, style="v3", yaw=ya, title=False)
            got = sheet.crop((i * fw, 0, (i + 1) * fw, fh))
            ok("render_spin_frame_%d_matches_pre_optimization_independent_render" % i,
               got.tobytes() == expected.tobytes())

        # render()'s single-image call sites are unaffected: no surface_texture= passed -> computes
        # internally exactly as before (surface_texture defaults to None).
        im_direct = CR.render(nm_s, ch_s, nsn_s, w=fw, h=fh, style="v3", title=False)
        im_direct2 = CR.render(nm_s, ch_s, nsn_s, w=fw, h=fh, style="v3", title=False)
        ok("render_direct_call_unaffected_by_optimization", im_direct.tobytes() == im_direct2.tobytes())
    else:
        failed.append("PIL_unavailable_36")
except Exception as e:
    failed.append("render_spin_shared_texture(%s)" % e)


# =====================================================================================================
# #37 -- SPIN_FRAMES vs TIER_FRAMES: frame COUNT still legitimately differs by tier ('lite' stays at 16,
# 'modern' at 24) even though 'lite' and 'modern' now share the identical v3 render *style* -- exercised
# through the real /cadspin route (features/routes/parts_media.py) so the fix is checked end-to-end, not
# just as isolated dict values. Style now matches ('v3') for both tiers; frame COUNT does not.
# =====================================================================================================
try:
    import viewer_app  # triggers features/routes registration + `core` DI into parts_media
    from features.routes import parts_media as PM
    import cad_render as CR
    import unittest.mock as mock, shutil

    # the module-level knobs themselves: still tier-differentiated, decoupled from the collapsed style
    ok("tier_frames_legacy_lite_modern_distinct", CR.TIER_FRAMES == {"legacy": 12, "lite": 16, "modern": 24})
    ok("spin_frames_unchanged_style_keyed", CR.SPIN_FRAMES == {"v1": 12, "v2": 16, "v3": 24})

    class _FakeHandler:
        def __init__(self): self.sent = None
        def _send(self, status, body, ctype=None, headers=None): self.sent = (status, body, ctype, headers)

    if CR.Image is not None:
        tdir = tempfile.mkdtemp(prefix="cadspin_tierframes_")
        try:
            with mock.patch.object(PM.core, "DB_PATH", os.path.join(tdir, "viewer.db")):
                nsn_r, nm_r, ch_r = "3110-01-777-7003", "BEARING, BALL", "OUTSIDE DIAMETER: 2.0 IN WIDTH: 0.6 IN"

                h_lite = _FakeHandler()
                PM.r_cadspin(h_lite, {"nsn": [nsn_r], "name": [nm_r], "chars": [ch_r], "tier": ["lite"]})
                _, _, _, hdr_lite = h_lite.sent
                ok("cadspin_lite_tier_style_is_v3", hdr_lite["X-CAD-Style"] == "v3")
                ok("cadspin_lite_tier_frame_count_stays_16", hdr_lite["X-CAD-Frames"] == "16")

                h_modern = _FakeHandler()
                PM.r_cadspin(h_modern, {"nsn": [nsn_r], "name": [nm_r], "chars": [ch_r], "tier": ["modern"]})
                _, _, _, hdr_modern = h_modern.sent
                ok("cadspin_modern_tier_style_is_v3", hdr_modern["X-CAD-Style"] == "v3")
                ok("cadspin_modern_tier_frame_count_stays_24", hdr_modern["X-CAD-Frames"] == "24")

                # explicit ?style= override (no tier) keeps the OLD style-keyed default -- unchanged behavior
                h_style = _FakeHandler()
                PM.r_cadspin(h_style, {"nsn": [nsn_r], "name": [nm_r], "chars": [ch_r], "style": ["v2"]})
                _, _, _, hdr_style = h_style.sent
                ok("cadspin_explicit_style_override_keeps_style_keyed_frames", hdr_style["X-CAD-Frames"] == "16")
        finally:
            shutil.rmtree(tdir, ignore_errors=True)
    else:
        failed.append("PIL_unavailable_37")
except Exception as e:
    failed.append("cadspin_tier_frames(%s)" % e)


for n in passed: print("PASS", n)
for n in failed: print("FAIL", n)
print("\n%d passed, %d failed (of %d checks for Medium-tier audit fixes #21-#37)" %
      (len(passed), len(failed), len(passed) + len(failed)))
sys.exit(1 if failed else 0)

# END OF FILE
