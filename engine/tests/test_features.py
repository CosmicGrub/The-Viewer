#!/usr/bin/env python3
"""Regression tests for the v0.42-0.50 features (procedure parser, suggest, look-alike, ingest preview,
RPS mode). Self-contained: spins up a tiny synthetic index and monkeypatches viewer_app.db so it never
touches the real corpus. Run:  python test_features.py   (exit 0 = all pass)."""
import os, sys, tempfile, sqlite3, threading, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import viewer_app as V

TMP = tempfile.mkdtemp(prefix="viewer_feat_")
DBP = os.path.join(TMP, "t.db")

def _build_db():
    c = sqlite3.connect(DBP)
    c.executescript("""
      CREATE TABLE documents(id INTEGER PRIMARY KEY, path TEXT, vehicle TEXT, tm_number TEXT, title TEXT, page_count INT);
      CREATE TABLE pages(id INTEGER PRIMARY KEY, document_id INT, page_number INT, body_text TEXT, source TEXT, ocr_confidence REAL);
      CREATE VIRTUAL TABLE pages_fts USING fts5(body_text, content='pages', content_rowid='id');
      CREATE TABLE request_items(id INTEGER PRIMARY KEY, item_name TEXT, nsn TEXT, session_id INT, created_at TEXT);
      CREATE TABLE parts(id INTEGER PRIMARY KEY, name TEXT, part_number TEXT, nsn TEXT, document_id INT, page INT,
                         vehicle TEXT, nomenclature TEXT, cagec TEXT, smr TEXT, fig_no TEXT, fig_title TEXT, uoc TEXT, confidence TEXT);
    """)
    c.execute("INSERT INTO documents(id,path,vehicle,tm_number,title,page_count) VALUES(1,?,?,?,?,?)",
              (os.path.join(TMP, "old.pdf"), "HMMWV M998", "TM 9-2320", "HMMWV maint", 50))
    proc = ("ALTERNATOR\n\nREMOVAL\n\nTOOLS REQUIRED\nWrench, Torque, 0-150 ft-lb\n\n"
            "WARNING\nDisconnect the battery first.\n\n1. Disconnect the negative battery cable.\n"
            "2. Remove the drive belt.\n3. Remove the alternator bolts.\n")
    c.execute("INSERT INTO pages(id,document_id,page_number,body_text,source) VALUES(1,1,12,?,'text')", (proc,))
    c.execute("INSERT INTO pages(id,document_id,page_number,body_text,source) VALUES(2,1,40,'alternator wiring schematic','text')")
    # recommendations annex #2 (torque-measures-confidence): a torque-bearing page with a real, LOW
    # ocr_confidence -- proves torque_specs() actually threads pages.ocr_confidence through to each
    # spec's confidence/quality flag, not just that the column exists.
    torque_txt = "ALTERNATOR MOUNTING. Torque the mounting bolts to 30 to 35 foot-pounds, then verify seating."
    c.execute("INSERT INTO pages(id,document_id,page_number,body_text,source,ocr_confidence) VALUES(3,1,13,?,'ocr',0.15)", (torque_txt,))
    c.execute("INSERT INTO pages_fts(rowid,body_text) SELECT id,body_text FROM pages")
    c.executemany("INSERT INTO request_items(item_name,nsn) VALUES(?,?)",
                  [("ALTERNATOR ASSEMBLY", "2920-01-111-1111"), ("BRAKE CALIPER", "2530-01-222-2222")])
    c.executemany("INSERT INTO parts(name,nsn,uoc,cagec,fig_title,confidence) VALUES(?,?,?,?,?,?)",
                  [("ALTERNATOR", "2920-01-111-1111", "AB1", "19207", "FIG 5", "page"),
                   ("ALTERNATOR", "2920-01-333-3333", "AB2", "19207", "FIG 5", "page"),
                   ("ALTERNATOR", "5340-01-444-4444", "AB1", "81337", "FIG 5", "page")])
    c.commit(); c.close()

_build_db()
V.DB_PATH = DBP
def _db():
    c = sqlite3.connect(DBP); c.row_factory = sqlite3.Row; return c
V.db = _db
V.correlations_for = lambda nsn: {}     # no sidecar in the test
V._VOCAB_READY = False

passed, failed = [], []
def ok(name, cond):
    (passed if cond else failed).append(name)

# --- procedure parser ---
pr = V._parse_procedure("ALTERNATOR\n\nREMOVAL\n\nTOOLS REQUIRED\nWrench, Torque\n\nWARNING\nHeavy.\n\n1. Disconnect battery.\n2. Drain coolant.\n")
ok("parse_kind_removal", bool(pr) and pr["kind"] == "Removal")
ok("parse_steps>=2", bool(pr) and len(pr["steps"]) >= 2)
ok("parse_tools_wrench", bool(pr) and any("Wrench" in t for t in pr["tools"]))
ok("parse_warning", bool(pr) and any(c["kind"] == "WARNING" for c in pr["cautions"]))
pr2 = V._parse_procedure("ENGINE ASSEMBLY\n1. step one goes here clearly\n")     # group title must NOT be the kind
ok("parse_group_title_not_kind", (pr2 is None) or pr2["kind"] != "Assembly")

# --- procedure_for (FTS over the synthetic page) ---
pf = V.procedure_for("alternator")
ok("procedure_for_found", pf["found"] and pf["n"] >= 1)
ok("procedure_for_cites_page", bool(pf["procedures"]) and pf["procedures"][0]["page"] == 12)

# --- real OCR-engine confidence wired into the quality-flag consumers (pages.ocr_confidence,
# migration 0009, previously computed but siloed -- see textquality.annotate()'s real_confidence,
# features/corpus.py's fts_pages(), and _parse_procedure()'s ocr_confidence parameter) ---
import textquality as TQ
CLEAN_TXT = "Torque the mounting bolts to 30 to 35 foot-pounds, then verify seating."
GARBLED_TXT = "Tqrq7e th3 m0un+1ng b0l+s |o 3O f7-|b. Bxk zzz tttt vwxq mnbb kkkk ~~|| ^^^^"
heuristic_clean_q = TQ.score(CLEAN_TXT)
heuristic_garbled_q = TQ.score(GARBLED_TXT)

# a low real confidence can PULL DOWN a heuristically-clean score...
r1 = TQ.annotate({"text": CLEAN_TXT}, context_key="text", real_confidence=0.2)
ok("annotate_low_real_confidence_downgrades_clean_text", r1["quality"] <= 0.2 and r1["confidence"] in ("suspect", "poor"))
# ...but a high real confidence must NEVER pull UP a heuristically-garbled score (a confidently-wrong
# OCR read is exactly the failure mode this exists to catch)
r2 = TQ.annotate({"text": GARBLED_TXT}, context_key="text", real_confidence=0.99)
ok("annotate_high_real_confidence_never_upgrades_garbled_text", r2["quality"] == heuristic_garbled_q and r2["confidence"] == TQ.flag(GARBLED_TXT))
# None (the overwhelming majority of pages: Tesseract fallback, native text, pre-migration rows) is
# a complete no-op -- byte-identical to calling annotate() without the parameter at all
r3 = TQ.annotate({"text": CLEAN_TXT}, context_key="text", real_confidence=None)
ok("annotate_none_real_confidence_is_noop", r3["quality"] == heuristic_clean_q)
# an unparsable/out-of-range value degrades safely to "ignore it", never a crash
r4 = TQ.annotate({"text": CLEAN_TXT}, context_key="text", real_confidence="not-a-number")
r5 = TQ.annotate({"text": CLEAN_TXT}, context_key="text", real_confidence=5.0)
ok("annotate_unparsable_real_confidence_ignored", r4["quality"] == heuristic_clean_q)
ok("annotate_out_of_range_real_confidence_ignored", r5["quality"] == heuristic_clean_q)

# _parse_procedure() threads ocr_confidence through to every caution's confidence flag
proc_with_warning = "ALTERNATOR\n\nREMOVAL\n\nWARNING\nDisconnect the battery first, verify no charge remains.\n\n1. Disconnect the negative battery cable.\n2. Remove the drive belt.\n"
pr_no_conf = V._parse_procedure(proc_with_warning)
pr_low_conf = V._parse_procedure(proc_with_warning, ocr_confidence=0.15)
ok("parse_procedure_default_ocr_confidence_is_none_noop", bool(pr_no_conf) and bool(pr_no_conf["cautions"]))
ok("parse_procedure_low_ocr_confidence_downgrades_caution",
   bool(pr_low_conf) and bool(pr_low_conf["cautions"]) and pr_low_conf["cautions"][0]["confidence"] in ("suspect", "poor")
   and pr_low_conf["cautions"][0]["quality"] < pr_no_conf["cautions"][0]["quality"])

# features/corpus.py's fts_pages() carries ocr_confidence through for every consumer (cautions.py,
# procedures_feature.py) to actually use -- the plumbing this whole fix depends on
from features import corpus as _corpus_mod
corpus_rows = _corpus_mod.fts_pages("alternator", limit=5, with_body=True, db_path=DBP)
ok("fts_pages_carries_ocr_confidence_key", bool(corpus_rows) and "ocr_confidence" in corpus_rows[0])
ok("fts_pages_ocr_confidence_none_for_synthetic_page", corpus_rows[0]["ocr_confidence"] is None)  # not set in this fixture -> real NULL, handled gracefully

# torque_specs() (recommendations annex #2): now threads pages.ocr_confidence through to each spec
# the same way _parse_procedure() already does for cautions -- was previously computing NOTHING here.
ts = V.torque_specs("alternator")
ok("torque_specs_found", ts["found"] and ts["n"] >= 1)
ts_low_conf_specs = [s for s in ts["specs"] if s.get("page") == 13]
ok("torque_specs_cites_the_low_confidence_page", bool(ts_low_conf_specs))
ok("torque_specs_low_ocr_confidence_downgrades_the_spec",
   bool(ts_low_conf_specs) and ts_low_conf_specs[0].get("confidence") in ("suspect", "poor")
   and ts_low_conf_specs[0].get("quality") is not None and ts_low_conf_specs[0]["quality"] <= 0.15)
ok("torque_specs_every_spec_carries_a_confidence_field",
   all("confidence" in s and "quality" in s for s in ts["specs"]))

# measures.find_for_query() (recommendations annex #2): m["trust_badge"] is a NEW additive field
# ({level,color,label,show} via trust.badge()) so measures.html can render it directly without
# reimplementing trust.py's color/label tables client-side. m["trust"] (the bare level string) is
# left UNCHANGED -- the aggregate trust.worst([m["trust"] for m in out]) call a few lines below it
# in measures.py still needs a list of strings, not dicts, so this must stay additive, not a rename.
import measures as _measures_mod
mq = _measures_mod.find_for_query(DBP, "alternator")
ok("measures_find_for_query_found_the_torque_value",
   mq["count"] >= 1 and any(r["type"] == "torque" for r in mq["results"]))
torque_rows = [r for r in mq["results"] if r["type"] == "torque"]
ok("measures_result_trust_is_still_a_bare_string (backward-compat for trust.worst())",
   bool(torque_rows) and isinstance(torque_rows[0].get("trust"), str))
ok("measures_result_trust_badge_is_the_new_dict_shape",
   bool(torque_rows) and isinstance(torque_rows[0].get("trust_badge"), dict)
   and {"level", "color", "label", "show"} <= set(torque_rows[0]["trust_badge"].keys()))
ok("measures_result_trust_badge_level_matches_the_bare_trust_string",
   bool(torque_rows) and torque_rows[0]["trust_badge"]["level"] == torque_rows[0]["trust"])
ok("measures_aggregate_trust_still_computed_from_bare_strings_not_dicts", mq.get("trust") in
   ("high", "medium", "review", "low", "quarantined", None))

# --- suggest ---
sg = V.suggest("alt")
texts = [s["text"].lower() for s in sg["suggestions"]]
ok("suggest_has_part", any("alternator assembly" in t for t in texts))
ok("suggest_has_term", any(t == "alternator" for t in texts))
sv = V.suggest("hmmwv")
ok("suggest_vehicle", any(s["kind"] == "vehicle" for s in sv["suggestions"]))
ok("suggest_short_empty", V.suggest("a")["suggestions"] == [])

# --- part_differences ---
pd = V.part_differences("ALTERNATOR")
ok("partdiff_found", pd["found"] and pd["n_variants"] == 3)
fields = [d["field"] for d in pd["discriminators"]]
ok("partdiff_uoc_disc", "UOC" in fields)
ok("partdiff_fsc_disc", "FSC" in fields)
rels = {v["relation"] for v in pd["variants"]}
ok("partdiff_diff_class", "different item class" in rels)   # the 5340 FSC item
# document_id/page are NULL on every ALTERNATOR fixture row above (this file's own hand-rolled
# `parts` INSERT never sets them) -- part_differences()'s new dimensional-comparison step must
# degrade cleanly to "no dimensions" rather than raise, exactly the shape a real corpus's
# barcode-only or metadata-only parts rows can also have.
ok("partdiff_no_page_ref_means_no_dimensions_not_a_crash", all(v["dimensions"] == [] for v in pd["variants"]))

# --- part_differences: dimensional-difference discriminator (a SEPARATE nomenclature+fixture,
# with real document_id/page refs and real dimensional text on each variant's own cited page --
# proves the new "different measured dimensions" discriminator/tell actually fires when it should,
# not just that it stays silent when there's nothing to compare). ---
try:
    _dc = sqlite3.connect(DBP)
    _dc.executescript("""
      INSERT INTO documents(id,path,vehicle,tm_number,title,page_count) VALUES
        (901,'/x/GASKET-A.pdf','M915','TM 9-9001','Gasket doc A',5),
        (902,'/x/GASKET-B.pdf','Forklift','TM 9-9002','Gasket doc B',5);
    """)
    _dc.execute("INSERT INTO pages(id,document_id,page_number,body_text,source) VALUES(901,901,3,?,'text')",
               ("Gasket length 2.0 in, diameter .500 in.",))
    _dc.execute("INSERT INTO pages(id,document_id,page_number,body_text,source) VALUES(902,902,4,?,'text')",
               ("Gasket length 3.5 in, diameter .625 in.",))
    _dc.executemany("INSERT INTO parts(name,nomenclature,nsn,document_id,page,vehicle,confidence) VALUES(?,?,?,?,?,?,?)", [
        ("GASKET SET", "GASKET SET", "5330-01-777-1111", 901, 3, "M915", "page"),
        ("GASKET SET", "GASKET SET", "5330-01-777-2222", 902, 4, "Forklift", "page"),
    ])
    _dc.commit(); _dc.close()
    pd_dim = V.part_differences("5330-01-777-1111")
    ok("partdiff_dims_found", pd_dim["found"] and pd_dim["n_variants"] == 2)
    dim_fields = [d["field"] for d in pd_dim["discriminators"]]
    ok("partdiff_dims_discriminator_fires", "dimensions" in dim_fields)
    ref_v = next(v for v in pd_dim["variants"] if v["relation"] == "reference")
    other_v = next(v for v in pd_dim["variants"] if v["relation"] != "reference")
    ok("partdiff_dims_reference_has_own_page_dimensions", any("2.0" in d for d in ref_v["dimensions"]))
    ok("partdiff_dims_other_variant_has_its_own_different_dimensions", any("3.5" in d for d in other_v["dimensions"]))
    ok("partdiff_dims_tell_cites_the_actual_values",
       any("3.5" in t and "2.0" in t for t in other_v["how_to_tell_apart"]))
except Exception as e:
    failed.append("partdiff_dimensions(%s)" % e)

# --- ingest_preview ---
for f in ("old.pdf", "new1.pdf", "new2.pdf"): open(os.path.join(TMP, f), "w").write("x")
os.makedirs(os.path.join(TMP, "sub"), exist_ok=True); open(os.path.join(TMP, "sub", "new3.pdf"), "w").write("x")
ip = V.ingest_preview(TMP)
ok("ingest_total_4", ip["ok"] and ip["total_pdfs"] == 4)
ok("ingest_new_3", ip["new_pdfs"] == 3)            # old.pdf already in documents
ok("ingest_bad_path", V.ingest_preview("/no/such/folder")["ok"] is False)

# --- ingest_preview: a documents.path row recorded via a DIFFERENT (but equivalent) string for the
# same on-disk folder must still be recognized as "already indexed", not double-counted as new.
# Found live on a GitHub Actions Windows runner (%TEMP% resolves to an 8.3 short-name alias there,
# e.g. RUNNER~1 vs the long form) -- ingest_preview() realpath()s the folder it walks but previously
# compared the result against RAW documents.path strings, so an aliased path silently miscounted.
# Reproduced here with an OS-native alias (a Windows junction / POSIX symlink) instead, since that's
# reproducible on any machine, not just a GHA runner's specific temp-dir quirk.
try:
    alias_target = tempfile.mkdtemp(prefix="viewer_feat_alias_target_")
    open(os.path.join(alias_target, "aliased.pdf"), "w").write("x")
    alias_link = os.path.join(tempfile.mkdtemp(prefix="viewer_feat_alias_link_"), "alias")
    if os.name == "nt":
        import subprocess
        subprocess.run(["cmd", "/c", "mklink", "/J", alias_link, alias_target], check=True, capture_output=True)
    else:
        os.symlink(alias_target, alias_link)
    # record the document via the ALIAS path (simulating however it was originally aliased at ingest
    # time), then preview via the REAL (unaliased) path -- realpath() must reconcile the two.
    _con = sqlite3.connect(DBP)
    _con.execute("INSERT INTO documents(id,path) VALUES(99,?)", (os.path.join(alias_link, "aliased.pdf"),))
    _con.commit(); _con.close()
    ip2 = V.ingest_preview(alias_target)
    ok("ingest_alias_total_1", ip2["ok"] and ip2["total_pdfs"] == 1)
    ok("ingest_alias_recognized_not_new", ip2["new_pdfs"] == 0)
except Exception as e:
    failed.append("ingest_alias_setup(%s)" % e)

# --- ingest_start: concurrent POST /api/ingest must not race. ingest_start()'s "already running?"
# check and the write that records the new subprocess are serialized under a module lock (see
# features/ingest_feature.py's _INGEST_LOCK) -- without it, two threads can both observe no run in
# progress and both launch a crawl. Mock subprocess.Popen with an artificial delay to widen the
# window between the check and the write (mirroring the real cost of spawning a subprocess), so a
# regression that narrows/removes the lock shows up as MULTIPLE "started" winners here, not a flake.
from features import ingest_feature as _ingest_mod
_real_popen = __import__("subprocess").Popen
_real_sg_mod = sys.modules.get("safeguard")
_popen_calls = []
_popen_lock = threading.Lock()

class _FakeProc:
    def poll(self): return None      # "still running" for the lifetime of this test

class _FakeSafeguard:
    def snapshot(self, *a, **kw): return ("SNAP_test", {})

def _fake_popen(cmd, **kw):
    with _popen_lock: _popen_calls.append(cmd)
    time.sleep(0.05)                 # simulate real subprocess-launch cost -> widens any unlocked race window
    return _FakeProc()

try:
    import subprocess as _subprocess_mod
    _subprocess_mod.Popen = _fake_popen
    sys.modules["safeguard"] = _FakeSafeguard()
    N = 8
    barrier = threading.Barrier(N)
    results = [None] * N
    def _race_worker(i):
        barrier.wait()
        results[i] = V.ingest_start(TMP)
    threads = [threading.Thread(target=_race_worker, args=(i,)) for i in range(N)]
    for t in threads: t.start()
    for t in threads: t.join()
    started = [r for r in results if r and r.get("ok") and r.get("started")]
    blocked = [r for r in results if r and not r.get("ok") and "already in progress" in (r.get("error") or "")]
    ok("ingest_start_race_single_winner", len(started) == 1)
    ok("ingest_start_race_rest_blocked", len(blocked) == N - 1)
    ok("ingest_start_race_single_subprocess_launch", len(_popen_calls) == 1)
finally:
    _subprocess_mod.Popen = _real_popen
    if _real_sg_mod is not None: sys.modules["safeguard"] = _real_sg_mod
    else: sys.modules.pop("safeguard", None)
    _ingest_mod._INGEST = {"proc": None, "path": "", "started": 0.0, "kind": None}   # reset for any later use in-process

# --- RPS mode (via the rps module) ---
try:
    import rps
    ok("rps_modern", rps.mode_for({"python_ok": True, "modern_os": True, "render_backend": "pymupdf", "ram_gb": 16, "tier": "GPU laptop"})[0] == "modern")
    ok("rps_legacy", rps.mode_for({"modern_os": False, "render_backend": "poppler", "ram_gb": 4, "tier": "Legacy / low-power"})[0] == "legacy")
    ok("rps_flags_legacy", rps.feature_flags("legacy")["polyfills"] is True and rps.feature_flags("legacy")["default_dpi"] == 100)
except Exception as e:
    failed.append("rps_import(%s)" % e)

# --- RPS "premium" tier: opt-in, hardware-gated, additive, never auto-selected ---
try:
    import rps, settings as _settings_mod

    _capable = {"python_ok": True, "modern_os": True, "render_backend": "pymupdf", "ram_gb": 16, "tier": "GPU laptop"}
    _weak = {"modern_os": False, "render_backend": "poppler", "ram_gb": 4, "tier": "Legacy / low-power"}

    ok("rps_premium_label_present", rps.RUN_MODE_LABELS.get("premium") == "Premium (visual effects)")
    ok("settings_normalize_premium", _settings_mod.normalize_run_mode("premium") == "premium")
    ok("settings_normalize_premium_case_insensitive", _settings_mod.normalize_run_mode("PREMIUM") == "premium")
    ok("settings_normalize_unknown_still_auto", _settings_mod.normalize_run_mode("nonsense") == "auto")

    m_cap, why_cap = rps.mode_for_setting(_capable, "premium")
    ok("rps_premium_capable_resolves_modern", m_cap == "modern")
    ok("rps_premium_active_on_capable_hw", rps.premium_active(_capable, "premium") is True)
    flags_cap = rps.feature_flags(m_cap, rps.premium_active(_capable, "premium"))
    ok("rps_premium_flag_set_on_capable_hw", flags_cap["premium_ui"] is True)
    # premium must never change backend behavior vs. plain modern -- purely a UI-facing marker
    ok("rps_premium_backend_flags_match_plain_modern",
       {k: v for k, v in flags_cap.items() if k != "premium_ui"} ==
       {k: v for k, v in rps.feature_flags("modern").items() if k != "premium_ui"})

    m_weak, why_weak = rps.mode_for_setting(_weak, "premium")
    ok("rps_premium_weak_hw_falls_back_not_forced", m_weak == "legacy")
    ok("rps_premium_weak_hw_reason_explains_fallback", "falling back" in why_weak.lower())
    ok("rps_premium_inactive_on_weak_hw", rps.premium_active(_weak, "premium") is False)
    ok("rps_premium_flag_unset_on_weak_hw",
       rps.feature_flags(m_weak, rps.premium_active(_weak, "premium"))["premium_ui"] is False)

    # VALID_MODES (the concrete engine tier set) must stay exactly 3 values -- premium is a Settings-panel
    # intent layered on top, never a 4th concrete mode, so every existing modern/lite/legacy-only consumer
    # keeps working unchanged.
    ok("rps_valid_modes_unchanged_by_premium", rps.VALID_MODES == ("modern", "lite", "legacy"))

    # feature_flags()/profile_summary() stay fully backward-compatible for every caller not passing premium
    ok("rps_feature_flags_default_premium_false", rps.feature_flags("modern")["premium_ui"] is False)
    ps = rps.profile_summary(_capable, "modern", "test")
    ok("rps_profile_summary_default_premium_false", ps["flags"]["premium_ui"] is False)
    ps2 = rps.profile_summary(_capable, "modern", "test", premium=True)
    ok("rps_profile_summary_premium_arg_threads_through", ps2["flags"]["premium_ui"] is True)
except Exception as e:
    failed.append("rps_premium(%s)" % e)

for n in passed: print("PASS", n)
for n in failed: print("FAIL", n)
print("\n%d passed, %d failed (of %d feature tests)" % (len(passed), len(failed), len(passed) + len(failed)))
sys.exit(1 if failed else 0)
