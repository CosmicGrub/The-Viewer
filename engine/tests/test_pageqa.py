#!/usr/bin/env python3
"""THE VIEWER -- e2e coverage for Phase 2 vision-language page QA (catalog SS10.1 + SS3.12, design doc
docs/superpowers/specs/2026-08-24-vision-language-page-qa-design.md, plan item 15):
engine/pageqa.py's mode="structured"/strict=True verification path, engine/build_pageqa.py's batch driver,
and masterfile.py's pageqa.db pickup, run against REAL fixtures (a real tiny PDF via pymupdf with known
torque text, ingested through the REAL viewer_ingest.py crawl pipeline -- same convention
test_barcode_wiring.py/test_dedup.py already establish for this suite) rather than synthetic dicts.

CRITICAL CI-SAFETY (read before changing anything here): this file NEVER imports torch/transformers and
NEVER attempts a real Florence-2 model load -- confirmed neither package is importable in this repo's own
dev/CI environment (matches the design spec's explicit "CI runners have neither a GPU nor downloaded model
weights" statement). The mocked vision-language backend is a REAL, separate, importable Python module
(satisfying vlm.py's own `hasattr(mod, "ask")` pluggable-backend contract exactly as a genuine backend
would) written to a temp dir and selected via the SAME `VIEWER_VLM` env-var mechanism vlm.py's own module
docstring documents ("set the env var VIEWER_VLM to a module name implementing the same ask") -- not a
`_backend=` injection, because build_pageqa.py's own call to pageqa.ask() never passes one (see
build_pageqa.py's main(): `pageqa.ask(doc_id, page, DEFAULT_QUESTION, mode="structured", strict=True,
db_path=DB)` -- no `_backend` kwarg at all), so this is the ONLY real way to hand it a fake backend and
still be exercising build_pageqa.py's ACTUAL resolution path, not a shortcut around it.

WHY THIS RUNS build_pageqa.py IN-PROCESS (import + real function calls), NOT as a spawned OS subprocess,
for the mocked-backend cases -- traced through exactly, not guessed:
    pageqa.available() = vlm.available() AND pageqa._gpu_tier() (engine/pageqa.py). vlm.available() is
    satisfiable from an external process via the VIEWER_VLM env var above (real backend resolution, no
    trickery). pageqa._gpu_tier() is NOT: it does
        here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here); import sysprobe
    which UNCONDITIONALLY inserts pageqa.py's own directory (engine/) at sys.path[0] before importing
    "sysprobe" -- and when `python build_pageqa.py` is invoked directly, engine/ is ALREADY sys.path[0]
    (the interpreter's own script-directory rule), ahead of any PYTHONPATH entry. There is no environment
    variable _gpu_tier() consults, no override hook -- a real spawned subprocess on a real no-GPU/no-CUDA
    machine (this repo's own CI runners, and this dev sandbox: no nvidia-smi, no CUDAExecutionProvider)
    would report pageqa.available()=False regardless of VIEWER_VLM, never reaching pageqa.ask() at all, no
    matter how good the mock is. The only ways around that are (a) writing to the real, SHARED, non-test-
    isolated index/hardware_profile.json sysprobe.py hardcodes -- rejected, that pollutes the actual repo
    environment outside any tempdir this suite otherwise confines itself to, or (b) monkeypatching the one
    genuinely untestable-in-CI hardware probe directly, exactly the fallback the plan item's own text
    permits ("or that pageqa.available()/vlm.available() is monkeypatched to bypass the real availability
    gate for this test's purposes") and exactly test_barcode_wiring.py's own technique for a different
    optional backend (`VI.barcodes.available = lambda: False`, its Section 3) -- mirrored here as
    `pageqa._gpu_tier = lambda: True` (restored in the outer try/finally below). Once that one hardware-
    only gate is bypassed, build_pageqa.py's REAL, UNMODIFIED main()/_candidate_pages()/SCHEMA/INSERT-OR-
    REPLACE logic runs for real, against real tempfile-based sqlite3 DBs, calling the REAL pageqa.ask() ->
    the REAL vlm.ask()/vlm.ground() -> the REAL (env-var-selected) mock backend -> the REAL measures.py
    extraction -> the REAL OCR cross-check against a REAL page's REAL stored body_text. Only the one
    hardware probe is faked; everything else genuinely executes.

    Section 0 below is the one case that genuinely IS a spawned `python build_pageqa.py` OS subprocess --
    the "no backend installed at all" degrade path needs no mock and no GPU-tier bypass (vlm.available()
    is False first, short-circuiting the `and` before _gpu_tier() is ever even called), so it is exercised
    for real, unmocked, exactly as CI itself will run it.

Run: `python tests/test_pageqa.py`"""
import importlib
import os
import sqlite3
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
MIGDIR = os.path.join(ENGINE, "migrations")
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)

import pymupdf as fitz  # noqa: E402
import viewer_ingest as VI  # noqa: E402
import pageqa  # noqa: E402
import build_pageqa  # noqa: E402
import masterfile  # noqa: E402

passed, failed = [], []
def ok(name, cond):
    (passed if cond else failed).append(name)


# =====================================================================================================
# Fixture helpers
# =====================================================================================================
_FAKEVLM_DIR = tempfile.mkdtemp(prefix="pageqa_fakevlm_")
sys.path.insert(0, _FAKEVLM_DIR)


def _write_fake_backend(name, answer_text, ground_region):
    """A REAL, separate, importable module -- e.g. `def ask(image, question): return "..."` -- satisfying
    vlm.py's pluggable `ask(image, question) -> str` contract (and `ground(image, phrase) -> dict|None` for
    the self-grounding re-check) exactly like a genuine backend would. Each case gets its OWN module NAME
    (never reused) specifically so __import__()'s sys.modules caching can never hand a later case a stale,
    earlier case's cached functions."""
    path = os.path.join(_FAKEVLM_DIR, name + ".py")
    with open(path, "w", encoding="utf-8") as f:
        f.write("def ask(image, question):\n    return %r\n\n\ndef ground(image, phrase):\n    return %r\n"
                 % (answer_text, ground_region))
    return name


def _make_fixture(tag, vehicle, body_text, ocr_confidence=0.9):
    """A real, single-page PDF with a REAL extractable text layer (pymupdf insert_text -- same convention
    test_ingest_routes.py's own text-layer fixtures already use), ingested through the REAL
    viewer_ingest.py crawl pipeline (upsert_document + index_pdf), exactly like test_barcode_wiring.py's
    own _new_db() helper. This lands `body_text` for real via PyMuPDF's own text extraction -- pageqa.py's
    OCR cross-check (_page_ocr_text()) then reads this SAME real, independently-derived text, not a value
    this test fabricated to match. ocr_confidence is set directly via SQL afterward: a text-layer-indexed
    page (source='text') never goes through viewer_ingest.py's real OCR pass at all -- ocr_confidence is
    only ever set on the OCR UPDATE path (ocr()/ocr_one()) -- so this simulates the confidence score a real
    OCR pass would have stamped, without this test needing tesseract/rapidocr installed anywhere (the same
    "don't depend on an optional native engine this test doesn't actually need to prove" discipline this
    file's own CI-safety section applies to the VLM backend). Returns (fixture_dir, viewer_db_path, doc_id)."""
    d = tempfile.mkdtemp(prefix="pageqa_fixture_%s_" % tag)
    dbp = os.path.join(d, "viewer.db")
    con = VI.connect(dbp)
    VI.migrate(con, MIGDIR, db_path=dbp)

    vdir = os.path.join(d, vehicle)
    os.makedirs(vdir, exist_ok=True)
    pdf_path = os.path.join(vdir, "TM-%s.pdf" % tag)
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 72), body_text)
    doc.save(pdf_path)
    doc.close()

    doc_id, _kind = VI.upsert_document(con, pdf_path, d)
    indexed, queued = VI.index_pdf(con, doc_id, pdf_path)
    con.commit()
    ok("%s_fixture_real_text_layer_indexed_no_ocr_needed" % tag, indexed == 1 and queued == 0)

    con.execute("UPDATE pages SET ocr_confidence=? WHERE document_id=? AND page_number=1",
                (ocr_confidence, doc_id))
    con.commit()
    stored = con.execute("SELECT body_text FROM pages WHERE document_id=? AND page_number=1",
                          (doc_id,)).fetchone()
    ok("%s_fixture_real_body_text_stored" % tag,
       stored is not None and body_text.split(".")[0] in (stored[0] or ""))
    con.close()
    return d, dbp, doc_id


def _run_build_pageqa(viewer_db, pageqa_db, vlm_module_name, max_pages=5):
    """Sets build_pageqa.py's OWN documented env-var configuration surface (VIEWER_DB/PAGEQA_DB/
    MEASURES_DB/TABLES_DB/RPSTL_DB/VIEWER_VLM), reloads the real module so its module-level DB-path
    constants (computed once at import time from those exact env vars) pick up the fresh values, then
    calls its REAL, unmodified main(). MEASURES_DB/TABLES_DB/RPSTL_DB point at paths that never exist --
    deliberately: this test's fixture PDF's real text ALSO gets auto-extracted by measures.py's own regex
    into viewer_ingest.py's real per-corpus measures.db as a side effect of the real ingest pipeline
    _make_fixture() runs (viewer_ingest.py's index_pdf() always does this for any indexed text page) --
    pointing build_pageqa's own MEASURES_DB env var somewhere that ingest never touches keeps this test's
    candidate-page selection decoupled from that unrelated side effect, rather than accidentally excluding
    the very page this test wants sampled."""
    d = os.path.dirname(viewer_db)
    os.environ["VIEWER_DB"] = viewer_db
    os.environ["PAGEQA_DB"] = pageqa_db
    os.environ["MEASURES_DB"] = os.path.join(d, "unused_measures.db")
    os.environ["TABLES_DB"] = os.path.join(d, "unused_tables.db")
    os.environ["RPSTL_DB"] = os.path.join(d, "unused_rpstl.db")
    os.environ["VIEWER_VLM"] = vlm_module_name
    importlib.reload(build_pageqa)
    return build_pageqa.main(max_pages)


def _pageqa_rows(pageqa_db):
    if not os.path.exists(pageqa_db):
        return []
    con = sqlite3.connect(pageqa_db)
    try:
        return con.execute(
            "SELECT document_id,page_number,type,value,value2,unit,verified,backend "
            "FROM pageqa_extractions").fetchall()
    finally:
        con.close()


TORQUE_TEXT = "Bolt torque is 35 N-m. Torque wrench required for reassembly."
UNRELATED_TEXT = "This page covers coolant capacity, fan belt replacement, and battery service."


# =====================================================================================================
# Section 0 -- a REAL, genuinely spawned `python build_pageqa.py` OS subprocess, completely unmocked:
# no VIEWER_VLM set, and neither transformers nor torch importable in this environment (confirmed by
# vlm_backend.py's own module docstring's isolation-boundary design -- its two heavy imports are
# unguarded on purpose, so importing it is the CI-safety gate itself). pageqa.available() must report
# False cleanly (vlm.available() is False first -- _gpu_tier() is never even reached) and build_pageqa.py
# must exit 2 with a clear message, writing nothing -- exactly what this repo's own CI runners do today.
# =====================================================================================================
try:
    d0 = tempfile.mkdtemp(prefix="pageqa_nobackend_")
    env0 = dict(os.environ)
    env0.pop("VIEWER_VLM", None)
    env0["VIEWER_DB"] = os.path.join(d0, "viewer.db")      # never actually touched -- available() gates first
    env0["PAGEQA_DB"] = os.path.join(d0, "pageqa.db")
    p0 = subprocess.run([sys.executable, os.path.join(ENGINE, "build_pageqa.py"), "--max-pages", "0"],
                         capture_output=True, text=True, timeout=60, env=env0, cwd=ENGINE)
    ok("section0_no_backend_exits_2", p0.returncode == 2)
    ok("section0_no_backend_clean_message", "Vision-language backend unavailable" in p0.stdout)
    ok("section0_no_backend_writes_nothing", not os.path.exists(env0["PAGEQA_DB"]))
except Exception as e:
    failed.append("section0_no_backend_real_subprocess(%s)" % e)


# =====================================================================================================
# Bypass the ONE genuinely untestable-in-CI gate (the hardware GPU-tier probe -- see module docstring)
# for the remainder of this file. Restored in the outer finally below.
# =====================================================================================================
_orig_gpu_tier = pageqa._gpu_tier
pageqa._gpu_tier = lambda: True
_env_keys = ("VIEWER_DB", "PAGEQA_DB", "MEASURES_DB", "TABLES_DB", "RPSTL_DB", "VIEWER_VLM")
_orig_env = {k: os.environ.get(k) for k in _env_keys}

d1 = dbp1 = doc1 = pqdb1 = None   # populated by case 1, reused by case 4

try:
    # =================================================================================================
    # Case 1 -- mocked ask() and ground() AGREE with each other AND with the page's real, independently
    # extracted stored text -> a verified row must land in pageqa.db with the right document_id/
    # page_number/type/value.
    # =================================================================================================
    try:
        d1, dbp1, doc1 = _make_fixture("case1", "HMMWV", TORQUE_TEXT)
        pqdb1 = os.path.join(d1, "pageqa.db")
        backend1 = _write_fake_backend("fakevlm_case1_verified", TORQUE_TEXT,
                                        {"x0": 0.1, "y0": 0.2, "x1": 0.4, "y1": 0.3})
        rc1 = _run_build_pageqa(dbp1, pqdb1, backend1)
        ok("case1_main_exits_0", rc1 == 0)
        rows1 = _pageqa_rows(pqdb1)
        ok("case1_exactly_one_row_written", len(rows1) == 1)
        if rows1:
            r = rows1[0]
            ok("case1_document_id_correct", r[0] == doc1)
            ok("case1_page_number_correct", r[1] == 1)
            ok("case1_type_correct", r[2] == "torque")
            ok("case1_value_correct", r[3] == "35")
            ok("case1_unit_correct", r[5] == "N-m")
            ok("case1_verified_flag_set", r[6] == 1)
            ok("case1_backend_provenance_recorded", r[7] == backend1)
    except Exception as e:
        failed.append("case1_verified_row_written(%s)" % e)

    # =================================================================================================
    # Case 2 -- grounding fails (ground() returns None) even though the claimed text genuinely matches
    # this page's own real stored text -> NOTHING must be written for that page.
    # =================================================================================================
    try:
        d2, dbp2, doc2 = _make_fixture("case2", "HMMWV", TORQUE_TEXT)
        pqdb2 = os.path.join(d2, "pageqa.db")
        backend2 = _write_fake_backend("fakevlm_case2_groundfail", TORQUE_TEXT, None)
        rc2 = _run_build_pageqa(dbp2, pqdb2, backend2)
        ok("case2_main_exits_0", rc2 == 0)
        rows2 = _pageqa_rows(pqdb2)
        ok("case2_nothing_written_when_self_grounding_fails", rows2 == [])
    except Exception as e:
        failed.append("case2_ground_fails_writes_nothing(%s)" % e)

    # =================================================================================================
    # Case 3 -- self-grounding succeeds (a real region is returned), but the claimed text does NOT
    # substantially overlap this page's own real stored OCR/text content -> NOTHING must be written.
    # =================================================================================================
    try:
        d3, dbp3, doc3 = _make_fixture("case3", "HMMWV", UNRELATED_TEXT)
        pqdb3 = os.path.join(d3, "pageqa.db")
        backend3 = _write_fake_backend("fakevlm_case3_ocrmismatch", TORQUE_TEXT,
                                        {"x0": 0.1, "y0": 0.2, "x1": 0.4, "y1": 0.3})
        rc3 = _run_build_pageqa(dbp3, pqdb3, backend3)
        ok("case3_main_exits_0", rc3 == 0)
        rows3 = _pageqa_rows(pqdb3)
        ok("case3_nothing_written_when_ocr_crosscheck_fails", rows3 == [])
    except Exception as e:
        failed.append("case3_ocr_mismatch_writes_nothing(%s)" % e)

    # =================================================================================================
    # Case 4 -- a subsequent masterfile.py build() picks up case 1's verified row as a corroborating
    # 'vlm-verified' source, correctly cited to the real document/page.
    # =================================================================================================
    try:
        ok("case4_prereq_case1_produced_a_pageqa_db", pqdb1 is not None and os.path.exists(pqdb1))
        master_db4 = os.path.join(d1, "masterfile.db")
        summ4 = masterfile.build(dbp1, None, None, master_db4, pageqa_db=pqdb1)
        ok("case4_masterfile_build_succeeds", isinstance(summ4, dict))
        res4 = masterfile.for_subject(master_db4, "HMMWV")
        torque4 = next((f for f in res4["filtered"]
                         if f["type"] == "torque" and f["origin"] == "vlm-verified"), None)
        ok("case4_vlm_verified_filtered_row_present", torque4 is not None)
        if torque4:
            ok("case4_value_correct", torque4["value"] == "35")
            ok("case4_unit_correct", torque4["unit"] == "N-m")
        raw4 = [r for r in res4["raw"] if r["origin"] == "vlm-verified"]
        ok("case4_raw_row_cited_to_real_doc_page",
           any(r["doc"] == doc1 and r["page"] == 1 for r in raw4))
    except Exception as e:
        failed.append("case4_masterfile_picks_up_verified_row(%s)" % e)

finally:
    pageqa._gpu_tier = _orig_gpu_tier
    for k, v in _orig_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    try:
        importlib.reload(build_pageqa)   # restore its module-level DB-path constants to real defaults too
    except Exception:
        pass


for n in passed: print("PASS", n)
for n in failed: print("FAIL", n)
print("\n%d passed, %d failed (of %d checks for pageqa.py strict verification / build_pageqa.py / "
      "masterfile.py's pageqa.db pickup)" % (len(passed), len(failed), len(passed) + len(failed)))
sys.exit(1 if failed else 0)

# END OF FILE
