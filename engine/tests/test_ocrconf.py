#!/usr/bin/env python3
"""THE VIEWER -- regression coverage for engine/ocrconf.py's wiring into viewer_ingest.py's OCR pass
(catalog §1.9, design doc docs/superpowers/specs/2026-08-25-per-line-ocr-confidence-design.md).

ocrconf.py has its own round-trip self-test (`python ocrconf.py`) for the sidecar module in isolation --
this file instead proves the WIRING: a real crawl -> index -> ocr() pass through viewer_ingest.py actually
ends up with one row per line in ocr_lines, correctly keyed to document_id/page_number, on the RapidOCR
success path; that the identical-page dedup cache (`_DEDUP`) replays a cache hit's `lines` too, not just
its text/confidence (a repeated boilerplate page must not silently lose its per-line data); and that the
Tesseract-fallback path writes nothing to the sidecar without raising.

No real rapidocr_onnxruntime is installed in this environment (same "Advanced/GPU-fork-only, not built or
verified here" posture as every other RapidOCR-dependent piece of this project -- confirmed live below,
`VI._have_rapid()` reports False here). Same technique test_barcode_wiring.py's section 9 already
established for forcing a specific OCR-engine branch deterministically: monkeypatch `VI._have_rapid`/
`VI._get_rapid` directly rather than requiring the real dependency -- this is the actual pattern this
codebase's own ingest tests use for exercising an OCR-engine branch without the real backend installed
(there is no existing test that fakes RapidOCR's real per-line `res` shape to check on; this file is that
test). Real tesseract IS on PATH in this dev environment (confirmed at import time below) so the fallback
section runs for real by default, but also proves determinism works via a monkeypatched subprocess.run,
matching test_barcode_wiring.py's own `_boom`-style stub.

Run: python tests/test_ocrconf.py"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
MIGDIR = os.path.join(ENGINE, "migrations")
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)

import viewer_ingest as VI
import ocrconf

passed, failed = [], []
def ok(name, cond):
    (passed if cond else failed).append(name)


CAN_OCR_TESSERACT = shutil.which("tesseract") is not None
print("test_ocrconf: running (real _have_rapid()=%s here; RapidOCR path below is always mocked -- see "
      "module docstring; tesseract on PATH=%s)" % (VI._have_rapid(), CAN_OCR_TESSERACT))


def _new_db(prefix):
    d = tempfile.mkdtemp(prefix=prefix)
    db = os.path.join(d, "viewer.db")
    con = VI.connect(db)
    VI.migrate(con, MIGDIR, db_path=db)
    return d, con


def _pdf_n_pages(pdf_path, image_path, n=1):
    """An n-page PDF, every page showing the SAME image at the SAME position -- no extractable text
    layer (queues every page for OCR), and (when n>1) every page renders to byte-identical PNG bytes,
    which is exactly what viewer_ingest.py's _DEDUP cache keys on."""
    import pymupdf as fitz
    doc = fitz.open()
    for _ in range(n):
        page = doc.new_page(width=8.5 * 72, height=11 * 72)
        page.insert_image(fitz.Rect(1.25 * 72, 3 * 72, 7.25 * 72, 8.5 * 72), filename=image_path)
    doc.save(pdf_path); doc.close()


def _stub_png(out_path):
    """Content is irrelevant to the mocked RapidOCR result -- but it must NOT be a blank/near-blank
    page: ocr_one()'s own density gate (`_page_density(path, page_number) < 0.004`) skips full OCR
    entirely on a page that thin, before ever calling into the (mocked) text engine at all -- same trap
    test_barcode_wiring.py's own `_non_barcode_page_image()` helper already documents and avoids with a
    ruled grid. Reused here for the same reason (a plain white square measured 0 calls into the mock
    during this file's own dry run)."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (600, 600), "white")
    dr = ImageDraw.Draw(im)
    for i in range(0, 600, 40):
        dr.line([(i, 0), (i, 600)], fill="black", width=3)
        dr.line([(0, i), (600, i)], fill="black", width=3)
    im.save(out_path)


class _FakeRapidEngine:
    """Stands in for _get_rapid()'s returned callable -- ocr_one() calls it as `res, _ =
    _get_rapid()(ocr_input)` and reads `r[1]` (text) / `r[2]` (score) off each entry of `res`, exactly
    like the real RapidOCR adapter's own [box, text, score] triples (box content is never read by
    ocr_one(), so None stands in for it here). Counts calls so the dedup test can assert a cache hit
    skipped a second real inference, not just that the final text matched."""
    def __init__(self, res):
        self.res = res
        self.calls = 0

    def __call__(self, ocr_input):
        self.calls += 1
        return self.res, None


_KNOWN_LINES = [
    ("REMOVE THE FOUR MOUNTING BOLTS", 0.972),
    ("TORQUE TO 30 FOOT POUNDS", 0.905),
    ("SEE FIGURE 4-2 FOR DETAIL", 0.611),
]
_KNOWN_RES = [[None, t, s] for t, s in _KNOWN_LINES]


# =====================================================================================================
# Section 1 -- basic wiring: a mocked-RapidOCR page lands one row per line in ocr_lines, correct text/
# confidence, correctly keyed to document_id/page_number -- and an unrelated doc/page still returns [].
# =====================================================================================================
try:
    d1, con1 = _new_db("ocrconf_basic_")
    png1 = os.path.join(d1, "src.png"); _stub_png(png1)
    vdir1 = os.path.join(d1, "HMMWV"); os.makedirs(vdir1)
    pdf1 = os.path.join(vdir1, "TM-9-2320-BOLT-24P.pdf")
    _pdf_n_pages(pdf1, png1, n=1)

    doc_id1, _ = VI.upsert_document(con1, pdf1, d1)
    VI.index_pdf(con1, doc_id1, pdf1); con1.commit()

    orig_have_rapid, orig_get_rapid, orig_dedup = VI._have_rapid, VI._get_rapid, VI._DEDUP
    engine1 = _FakeRapidEngine(_KNOWN_RES)
    try:
        VI._DEDUP = {}   # every section's fixture image renders identically (same grid helper) --
        VI._have_rapid = lambda: True   # isolate _DEDUP per section so an earlier section's cached
        VI._get_rapid = lambda workers=1: engine1   # result can't leak into this one (or the next).
        remaining1 = VI.ocr(con1, 10, workers=1)
    finally:
        VI._have_rapid, VI._get_rapid, VI._DEDUP = orig_have_rapid, orig_get_rapid, orig_dedup

    ok("basic_ocr_drained_queue", remaining1 == 0)
    page1 = con1.execute("SELECT ocr_status, ocr_confidence FROM pages WHERE document_id=?", (doc_id1,)).fetchone()
    ok("basic_page_marked_done", page1 is not None and page1[0] == "done")
    expected_conf = round(sum(s for _, s in _KNOWN_LINES) / len(_KNOWN_LINES), 4)
    ok("basic_page_confidence_is_average_unchanged", page1 is not None and page1[1] == expected_conf)

    ocrconf_db1 = os.path.join(d1, "ocrconf.db")
    ok("basic_sidecar_available", ocrconf.available(ocrconf_db1))
    rows1 = ocrconf.lines_for_page(ocrconf_db1, doc_id1, 1)
    ok("basic_one_row_per_line", len(rows1) == len(_KNOWN_LINES))
    ok("basic_rows_correct_text_and_confidence", rows1 == [
        {"line_index": i, "text": t, "confidence": s} for i, (t, s) in enumerate(_KNOWN_LINES)])
    ok("basic_unrelated_page_empty", ocrconf.lines_for_page(ocrconf_db1, doc_id1, 2) == [])
    ok("basic_unrelated_doc_empty", ocrconf.lines_for_page(ocrconf_db1, doc_id1 + 999, 1) == [])
    con1.close()
except Exception as e:
    failed.append("section1_basic_wiring(%s)" % e)


# =====================================================================================================
# Section 2 -- identical-page dedup cache (_DEDUP) replays `lines` on a cache hit, not just text/conf.
# Two pages rendering to byte-identical PNGs (same image, same position) -- only the FIRST triggers a
# real engine call; the SECOND must still end up with the very same per-line rows in the sidecar.
# =====================================================================================================
try:
    d2, con2 = _new_db("ocrconf_dedup_")
    png2 = os.path.join(d2, "src.png"); _stub_png(png2)
    vdir2 = os.path.join(d2, "M35A2"); os.makedirs(vdir2)
    pdf2 = os.path.join(vdir2, "doc.pdf")
    _pdf_n_pages(pdf2, png2, n=2)   # two byte-identical pages

    doc_id2, _ = VI.upsert_document(con2, pdf2, d2)
    VI.index_pdf(con2, doc_id2, pdf2); con2.commit()

    orig_have_rapid, orig_get_rapid, orig_dedup = VI._have_rapid, VI._get_rapid, VI._DEDUP
    engine2 = _FakeRapidEngine(_KNOWN_RES)
    try:
        VI._DEDUP = {}   # isolate from anything section 1 (or a prior run) left behind
        VI._have_rapid = lambda: True
        VI._get_rapid = lambda workers=1: engine2
        remaining2 = VI.ocr(con2, 10, workers=1)
    finally:
        VI._have_rapid, VI._get_rapid, VI._DEDUP = orig_have_rapid, orig_get_rapid, orig_dedup

    ok("dedup_ocr_drained_queue", remaining2 == 0)
    ok("dedup_engine_called_exactly_once", engine2.calls == 1)   # page 2 must hit the cache, not re-infer

    ocrconf_db2 = os.path.join(d2, "ocrconf.db")
    rows2a = ocrconf.lines_for_page(ocrconf_db2, doc_id2, 1)
    rows2b = ocrconf.lines_for_page(ocrconf_db2, doc_id2, 2)
    expected_rows = [{"line_index": i, "text": t, "confidence": s} for i, (t, s) in enumerate(_KNOWN_LINES)]
    ok("dedup_page1_rows_correct", rows2a == expected_rows)
    ok("dedup_page2_cache_hit_replayed_same_rows", rows2b == expected_rows)

    pages2 = con2.execute("SELECT page_number, ocr_status, ocr_confidence FROM pages WHERE document_id=? "
                           "ORDER BY page_number", (doc_id2,)).fetchall()
    ok("dedup_both_pages_done", all(p[1] == "done" for p in pages2))
    ok("dedup_both_pages_same_confidence", pages2[0][2] == pages2[1][2] == round(
        sum(s for _, s in _KNOWN_LINES) / len(_KNOWN_LINES), 4))
    con2.close()
except Exception as e:
    failed.append("section2_dedup_cache_replay(%s)" % e)


# =====================================================================================================
# Section 3 -- Tesseract-fallback path writes NOTHING to the sidecar, and never raises. Forces the
# fallback branch deterministically (same _boom-style subprocess.run monkeypatch technique
# test_barcode_wiring.py's section 9 already established) so this doesn't depend on whether a real OCR
# text engine happens to be on PATH in whatever environment runs this file.
# =====================================================================================================
try:
    d3, con3 = _new_db("ocrconf_tesseract_fallback_")
    png3 = os.path.join(d3, "src.png"); _stub_png(png3)
    vdir3 = os.path.join(d3, "M1078"); os.makedirs(vdir3)
    pdf3 = os.path.join(vdir3, "doc.pdf")
    _pdf_n_pages(pdf3, png3, n=1)

    doc_id3, _ = VI.upsert_document(con3, pdf3, d3)
    VI.index_pdf(con3, doc_id3, pdf3); con3.commit()

    class _FakeCompleted:
        stdout = b"FALLBACK TESSERACT TEXT"

    def _fake_tesseract_run(*a, **kw):
        return _FakeCompleted()

    orig_have_rapid, orig_run, orig_dedup = VI._have_rapid, VI.subprocess.run, VI._DEDUP
    try:
        VI._DEDUP = {}   # same isolation as section 1/2 -- this section's grid image renders
                          # byte-identical to theirs; without a fresh cache this page would hit their
                          # leftover _DEDUP entry and never actually exercise the fallback branch at all.
        VI._have_rapid = lambda: False        # force the tesseract-subprocess branch...
        VI.subprocess.run = _fake_tesseract_run   # ...deterministically, no real tesseract needed
        remaining3 = VI.ocr(con3, 10, workers=1)
    finally:
        VI._have_rapid, VI.subprocess.run, VI._DEDUP = orig_have_rapid, orig_run, orig_dedup

    ok("fallback_ocr_drained_queue", remaining3 == 0)
    page3 = con3.execute("SELECT ocr_status, ocr_confidence, body_text FROM pages WHERE document_id=?",
                          (doc_id3,)).fetchone()
    ok("fallback_page_marked_done", page3 is not None and page3[0] == "done")
    ok("fallback_confidence_is_none", page3 is not None and page3[1] is None)
    ok("fallback_text_captured", page3 is not None and page3[2] == "FALLBACK TESSERACT TEXT")

    ocrconf_db3 = os.path.join(d3, "ocrconf.db")
    # No RapidOCR ever ran on this page -- record_lines() must never have been called, so the sidecar
    # either doesn't exist at all, or (if some earlier section's file happened to share the same temp
    # root -- it never does here, separate tempdir per section) has no rows for this page either way.
    ok("fallback_sidecar_not_created_or_empty",
       (not ocrconf.available(ocrconf_db3)) or ocrconf.lines_for_page(ocrconf_db3, doc_id3, 1) == [])
    ok("fallback_lines_for_page_empty", ocrconf.lines_for_page(ocrconf_db3, doc_id3, 1) == [])
    con3.close()
except Exception as e:
    failed.append("section3_tesseract_fallback_no_sidecar_write(%s)" % e)


# =====================================================================================================
# Section 4 -- adversarial-review regression: a RapidOCR res entry with no numeric score (rare but real
# -- the detection stage can emit a box the recognition stage couldn't score at all) must be KEPT, not
# silently dropped, and every later line's line_index must still match its TRUE position in `res`. The
# first draft of this fix reused `scores`' own filter (drop any unscored entry) before building `lines`
# -- safe for an AVERAGE (an unscored entry just doesn't contribute), but wrong here: filtering `res`
# itself, rather than only the score, both lost that line's text entirely and shifted every subsequent
# line's index. Caught by adversarial review, verified directly against the real code before fixing;
# this is the permanent regression test for it.
# =====================================================================================================
try:
    d4, con4 = _new_db("ocrconf_unscored_line_")
    png4 = os.path.join(d4, "src.png"); _stub_png(png4)
    vdir4 = os.path.join(d4, "M35A2"); os.makedirs(vdir4)
    pdf4 = os.path.join(vdir4, "doc.pdf")
    _pdf_n_pages(pdf4, png4, n=1)

    doc_id4, _ = VI.upsert_document(con4, pdf4, d4)
    VI.index_pdf(con4, doc_id4, pdf4); con4.commit()

    # middle entry has no 3rd element at all (len(r) <= 2, the exact shape ocr_one()'s own guard checks
    # for) -- a real RapidOCR box the recognition stage couldn't score. Must still be recorded, at its
    # true index 1, with confidence=None -- not dropped, and not causing "TORQUE..." to land at index 1
    # (where the unscored line belongs) instead of its real index 2.
    res4 = [[None, "REMOVE FOUR BOLTS", 0.97], [None, "CAUTION: HOT SURFACE"],
            [None, "TORQUE TO 30 FT-LB", 0.91]]

    orig_have_rapid, orig_get_rapid, orig_dedup = VI._have_rapid, VI._get_rapid, VI._DEDUP
    engine4 = _FakeRapidEngine(res4)
    try:
        VI._DEDUP = {}
        VI._have_rapid = lambda: True
        VI._get_rapid = lambda workers=1: engine4
        remaining4 = VI.ocr(con4, 10, workers=1)
    finally:
        VI._have_rapid, VI._get_rapid, VI._DEDUP = orig_have_rapid, orig_get_rapid, orig_dedup

    ok("unscored_ocr_drained_queue", remaining4 == 0)
    ocrconf_db4 = os.path.join(d4, "ocrconf.db")
    rows4 = ocrconf.lines_for_page(ocrconf_db4, doc_id4, 1)
    ok("unscored_all_three_lines_present_not_dropped", len(rows4) == 3)
    ok("unscored_line_kept_with_none_confidence",
       len(rows4) == 3 and rows4[1] == {"line_index": 1, "text": "CAUTION: HOT SURFACE", "confidence": None})
    ok("unscored_later_line_index_not_shifted",
       len(rows4) == 3 and rows4[2] == {"line_index": 2, "text": "TORQUE TO 30 FT-LB", "confidence": 0.91})
    ok("unscored_first_line_unaffected",
       len(rows4) == 3 and rows4[0] == {"line_index": 0, "text": "REMOVE FOUR BOLTS", "confidence": 0.97})
    con4.close()
except Exception as e:
    failed.append("section4_unscored_line_kept_not_dropped(%s)" % e)


# =====================================================================================================
print("\ntest_ocrconf: %d passed, %d failed" % (len(passed), len(failed)))
if failed:
    print("FAILED: " + ", ".join(failed))
    sys.exit(1)
print("PASSED: " + ", ".join(passed))
sys.exit(0)
# END OF FILE
