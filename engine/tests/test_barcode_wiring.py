#!/usr/bin/env python3
"""THE VIEWER -- regression coverage for wiring barcodes.py (catalog §4.9, dual-backend pyzbar/OpenCV
QR/1-D/Data-Matrix detector) into viewer_ingest.py's OCR pass (migration 0010).

Before this change barcodes.py had a fully-built, self-tested detect() with ZERO callers anywhere in
the codebase -- only its own `__main__` self-test and the module import-check in verifystate.py. Its
own docstring states the intent: some TMs print NSNs/part numbers as barcodes, and a machine-decoded
value is higher-trust than OCR text (no character-recognition ambiguity) -- feed it into the parts
index as a higher-trust-provenance extraction source.

This file proves the wiring end-to-end against a REAL, machine-decodable barcode: a QR code built with
whatever encoder backend is actually installed in this environment (checked at import time -- never
faked), embedded into a synthetic PDF page via PyMuPDF, run through the real crawl -> ocr ->
extract_parts pipeline (viewer_ingest.py, against the actual migrated schema, same harness style as
test_prune.py), and finally through features/parts_feature.py's part_lookup() -- the real downstream
consumer named in the work item -- to confirm the decoded NSN surfaces there with distinguishable,
higher-trust ('barcode') provenance alongside the existing regex-extracted ('page') parts.

Skips cleanly (exit 0, clearly labelled, nothing asserted) instead of faking a pass whenever this
environment can't actually decode a barcode (neither pyzbar nor OpenCV installed -- barcodes.
available() is False) or can't actually generate one to test with (no QR encoder available). Run:
  python tests/test_barcode_wiring.py"""
import os, sys, sqlite3, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
MIGDIR = os.path.join(ENGINE, "migrations")
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)

import viewer_ingest as VI
import barcodes
import features.parts_feature as parts_feature

passed, failed = [], []
def ok(name, cond):
    (passed if cond else failed).append(name)


# =====================================================================================================
# Environment probe: can this run actually decode AND actually build a real barcode image? Both are
# real capabilities, not assumptions -- report exactly what was checked either way (never fake a pass).
# =====================================================================================================
def _qr_png(payload, out_path):
    """Build a REAL, machine-decodable QR PNG at out_path encoding `payload`, using whichever encoder
    backend is actually importable here (checked, not assumed): OpenCV's QRCodeEncoder (ships with
    opencv-python, this project's 'recommended' tier per requirements.txt) first, then the `qrcode`
    package if that's what's present instead. Returns True on success, False if neither is available
    (caller must skip rather than fake a barcode)."""
    try:
        import cv2, numpy as np
        from PIL import Image
        enc = cv2.QRCodeEncoder.create()
        mods = enc.encode(payload)              # small 0/255 module grid (e.g. 29x29 for a short payload)
        scale = 10
        big = np.kron(mods, np.ones((scale, scale), dtype=np.uint8))
        border = 24
        h, w = big.shape
        canvas = np.full((h + 2 * border, w + 2 * border), 255, dtype=np.uint8)
        canvas[border:border + h, border:border + w] = big
        Image.fromarray(canvas).convert("RGB").save(out_path)
        return True
    except Exception:
        pass
    try:
        import qrcode
        img = qrcode.make(payload).convert("RGB")
        img.save(out_path)
        return True
    except Exception:
        return False


def _two_qr_png(payload_a, payload_b, out_path):
    """Two REAL, independently-decodable QR codes side by side on one canvas (OpenCV's
    detectAndDecodeMulti reads both) -- for the 'prefers the NSN-bearing record' check. cv2-only
    (no qrcode-package fallback needed; the multi-barcode check is skipped if cv2 lacks it, same as
    the single-QR path degrading gracefully elsewhere in this file)."""
    try:
        import cv2, numpy as np
        from PIL import Image
        enc = cv2.QRCodeEncoder.create()
        scale = 8
        def block(payload):
            return np.kron(enc.encode(payload), np.ones((scale, scale), dtype=np.uint8))
        b1, b2 = block(payload_a), block(payload_b)
        h = max(b1.shape[0], b2.shape[0]) + 40
        w = b1.shape[1] + b2.shape[1] + 60
        canvas = np.full((h, w), 255, dtype=np.uint8)
        canvas[20:20 + b1.shape[0], 20:20 + b1.shape[1]] = b1
        canvas[20:20 + b2.shape[0], 40 + b1.shape[1]:40 + b1.shape[1] + b2.shape[1]] = b2
        Image.fromarray(canvas).convert("RGB").save(out_path)
        return True
    except Exception:
        return False


def _pdf_with_image(pdf_path, image_path):
    """A single-page, letter-size PDF with `image_path` placed on it and NO extractable text layer --
    exactly the 'scanned page' shape that lands in the OCR queue via index_pdf()'s char-count check."""
    import pymupdf as fitz
    doc = fitz.open()
    page = doc.new_page(width=8.5 * 72, height=11 * 72)
    page.insert_image(fitz.Rect(1.25 * 72, 3 * 72, 7.25 * 72, 8.5 * 72), filename=image_path)
    doc.save(pdf_path); doc.close()


def _non_barcode_page_image(out_path):
    """A busy-but-not-blank, definitely-not-a-barcode page image (ruled grid + text) -- proves the
    'page has real content but no barcode' path decodes to nothing instead of crashing or hallucinating
    a match, while still clearing the blank-page density skip (unlike sparse random noise, which this
    file's own dry run found lands BELOW the 0.4% dark-pixel threshold and would never even reach
    _scan_barcode())."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (600, 600), "white")
    dr = ImageDraw.Draw(im)
    for i in range(0, 600, 40):
        dr.line([(i, 0), (i, 600)], fill="black", width=3)
        dr.line([(0, i), (600, i)], fill="black", width=3)
    dr.text((60, 60), "FIGURE 7 - EXPLODED VIEW - NO BARCODE HERE", fill="black")
    im.save(out_path)


_PROBE_DIR = tempfile.mkdtemp(prefix="barcode_wiring_probe_")
_PROBE_PNG = os.path.join(_PROBE_DIR, "probe.png")
CAN_DECODE = barcodes.available()
CAN_ENCODE = _qr_png("PROBE 0000-00-000-0000", _PROBE_PNG)
SKIP = not (CAN_DECODE and CAN_ENCODE)

if SKIP:
    reason = []
    if not CAN_DECODE:
        reason.append("barcodes.available() is False (neither pyzbar nor OpenCV importable here)")
    if not CAN_ENCODE:
        reason.append("no QR encoder available to build a real test barcode (tried cv2.QRCodeEncoder, then `qrcode`)")
    print("test_barcode_wiring: SKIPPED -- " + "; ".join(reason))
    print("  verified: nothing (environment cannot exercise real barcode decode/encode)")
    print("  NOT verified: the viewer_ingest.py wiring itself (needs a real backend to run against)")
    sys.exit(0)

print("test_barcode_wiring: running for real (decode backend=%s, encode via %s)" %
      (barcodes.backend(), "cv2.QRCodeEncoder" if os.path.exists(_PROBE_PNG) else "qrcode"))


def _new_db(prefix):
    d = tempfile.mkdtemp(prefix=prefix)
    db = os.path.join(d, "viewer.db")
    con = VI.connect(db)
    VI.migrate(con, MIGDIR, db_path=db)
    return d, con


# =====================================================================================================
# Section 1 -- _scan_barcode() reads a REAL, freshly-rendered page PNG correctly (the exact reuse this
# work item asked for: the same PNG _render_png() already produces for OCR, no second render).
# =====================================================================================================
try:
    d1 = tempfile.mkdtemp(prefix="barcode_scan_")
    qr_png = os.path.join(d1, "qr.png")
    payload = "NSN 2530-01-234-5678 BRAKE ASSY"
    ok("qr_build_ok", _qr_png(payload, qr_png))

    pdf1 = os.path.join(d1, "test.pdf")
    _pdf_with_image(pdf1, qr_png)

    dens = VI._page_density(pdf1, 1)
    ok("page_not_blank", dens is not None and dens >= 0.004)   # must clear the blank-skip threshold

    png1 = VI._render_png(pdf1, 1, dpi=200)
    bc = VI._scan_barcode(png1)
    ok("scan_barcode_found_something", bc is not None)
    ok("scan_barcode_type_qrcode", bc and bc.get("type") == "QRCODE")
    ok("scan_barcode_nsn_decoded", bc and bc.get("nsn") == "2530-01-234-5678")
    ok("scan_barcode_data_roundtrips", bc and bc.get("data") == payload)
    if png1 and os.path.exists(png1): os.unlink(png1)
except Exception as e:
    failed.append("section1_scan_barcode_real_roundtrip(%s)" % e)


# =====================================================================================================
# Section 2 -- opt-out toggle: VI.BARCODE_SCAN=False must produce None even with a REAL barcode present
# (proves the wiring is genuinely opt-in, not just gated on availability()).
# =====================================================================================================
try:
    d2 = tempfile.mkdtemp(prefix="barcode_toggle_")
    qr_png2 = os.path.join(d2, "qr.png")
    ok("toggle_qr_build_ok", _qr_png("NSN 1234-56-789-0123 TOGGLE TEST", qr_png2))
    pdf2 = os.path.join(d2, "test.pdf")
    _pdf_with_image(pdf2, qr_png2)
    png2 = VI._render_png(pdf2, 1, dpi=200)

    orig_toggle = VI.BARCODE_SCAN
    try:
        VI.BARCODE_SCAN = False
        ok("toggle_off_returns_none", VI._scan_barcode(png2) is None)
    finally:
        VI.BARCODE_SCAN = orig_toggle
    ok("toggle_restored_decodes_again", VI._scan_barcode(png2) is not None)
    if png2 and os.path.exists(png2): os.unlink(png2)
except Exception as e:
    failed.append("section2_opt_out_toggle(%s)" % e)


# =====================================================================================================
# Section 3 -- graceful degradation: if barcodes.available() were False (simulating an environment
# with neither pyzbar nor OpenCV, mirroring barcodes.py's own contract), _scan_barcode() must no-op to
# None cleanly, never raise, even against a real barcode image.
# =====================================================================================================
try:
    d3 = tempfile.mkdtemp(prefix="barcode_degrade_")
    qr_png3 = os.path.join(d3, "qr.png")
    ok("degrade_qr_build_ok", _qr_png("NSN 5305-01-674-1467 BOLT", qr_png3))
    pdf3 = os.path.join(d3, "test.pdf")
    _pdf_with_image(pdf3, qr_png3)
    png3 = VI._render_png(pdf3, 1, dpi=200)

    orig_avail = VI.barcodes.available
    try:
        VI.barcodes.available = lambda: False
        ok("degrade_unavailable_returns_none", VI._scan_barcode(png3) is None)
    finally:
        VI.barcodes.available = orig_avail
    ok("degrade_restored_decodes_again", VI._scan_barcode(png3) is not None)
    if png3 and os.path.exists(png3): os.unlink(png3)
except Exception as e:
    failed.append("section3_graceful_degrade(%s)" % e)


# =====================================================================================================
# Section 4 -- a real, non-blank page with NO barcode on it must decode to None, not crash and not
# hallucinate a match.
# =====================================================================================================
try:
    d4 = tempfile.mkdtemp(prefix="barcode_none_")
    plain_png = os.path.join(d4, "plain.png")
    _non_barcode_page_image(plain_png)
    pdf4 = os.path.join(d4, "test.pdf")
    _pdf_with_image(pdf4, plain_png)

    dens4 = VI._page_density(pdf4, 1)
    ok("no_barcode_page_not_blank", dens4 is not None and dens4 >= 0.004)
    png4 = VI._render_png(pdf4, 1, dpi=200)
    ok("no_barcode_page_scans_to_none", VI._scan_barcode(png4) is None)
    if png4 and os.path.exists(png4): os.unlink(png4)
except Exception as e:
    failed.append("section4_no_barcode_present(%s)" % e)


# =====================================================================================================
# Section 5 -- a real barcode whose payload carries NO recognizable NSN: type/data must still be
# captured (auditable), but nsn must stay None -- proves the NSN-scrape gate isn't spuriously loose.
# =====================================================================================================
try:
    d5 = tempfile.mkdtemp(prefix="barcode_nonsn_")
    qr_png5 = os.path.join(d5, "qr.png")
    ok("nonsn_qr_build_ok", _qr_png("PART NO MS35338-44 LOCKWASHER", qr_png5))
    pdf5 = os.path.join(d5, "test.pdf")
    _pdf_with_image(pdf5, qr_png5)
    png5 = VI._render_png(pdf5, 1, dpi=200)
    bc5 = VI._scan_barcode(png5)
    ok("nonsn_barcode_found", bc5 is not None)
    ok("nonsn_type_captured", bc5 and bc5.get("type") == "QRCODE")
    ok("nonsn_data_captured", bc5 and "MS35338-44" in (bc5.get("data") or ""))
    ok("nonsn_nsn_stays_none", bc5 and bc5.get("nsn") is None)
    if png5 and os.path.exists(png5): os.unlink(png5)
except Exception as e:
    failed.append("section5_barcode_without_nsn(%s)" % e)


# =====================================================================================================
# Section 6 -- selection logic (deterministic, mocked detect()): given several decoded records on one
# page, _scan_barcode() must prefer the one that actually carries an NSN over an earlier non-NSN one,
# and must truncate an oversized payload to 500 chars rather than store it unbounded.
# =====================================================================================================
try:
    d6 = tempfile.mkdtemp(prefix="barcode_selection_")
    stub_png = os.path.join(d6, "stub.png")
    from PIL import Image
    Image.new("RGB", (10, 10), "white").save(stub_png)   # content irrelevant -- detect() is mocked below

    orig_detect = VI.barcodes.detect
    try:
        VI.barcodes.detect = lambda img: [
            {"type": "CODE128", "data": "no nsn in this one"},
            {"type": "QRCODE", "data": "NSN 9999-88-777-6666 GASKET", "nsn": "9999-88-777-6666"},
        ]
        bc6 = VI._scan_barcode(stub_png)
        ok("selection_prefers_nsn_record", bc6 and bc6.get("nsn") == "9999-88-777-6666")
        ok("selection_type_matches_nsn_record", bc6 and bc6.get("type") == "QRCODE")

        VI.barcodes.detect = lambda img: [{"type": "CODE128", "data": "x" * 1000}]
        bc6b = VI._scan_barcode(stub_png)
        ok("selection_falls_back_to_first_when_none_have_nsn", bc6b and bc6b.get("nsn") is None)
        ok("selection_truncates_oversized_payload", bc6b and len(bc6b.get("data") or "") == 500)

        VI.barcodes.detect = lambda img: []
        ok("selection_empty_list_returns_none", VI._scan_barcode(stub_png) is None)
    finally:
        VI.barcodes.detect = orig_detect
except Exception as e:
    failed.append("section6_selection_logic(%s)" % e)


# =====================================================================================================
# Section 7 -- full pipeline, end to end: crawl/index -> ocr() -> pages.barcode_* columns ->
# extract_parts() -> a parts row tagged confidence='barcode' -> idempotent on rerun -> surfaces through
# features/parts_feature.py's part_lookup(), the real downstream consumer, exactly like an existing
# regex-extracted ('page') row does.
# =====================================================================================================
try:
    d7, con7 = _new_db("barcode_pipeline_")
    vdir = os.path.join(d7, "HMMWV"); os.makedirs(vdir)
    qr_png7 = os.path.join(vdir, "_qr_src.png")
    nsn7 = "5305-01-674-1467"
    payload7 = "NSN %s BOLT,MACHINE HEX HD" % nsn7
    ok("pipeline_qr_build_ok", _qr_png(payload7, qr_png7))
    pdf7 = os.path.join(vdir, "TM-9-2320-BOLT-24P.pdf")
    _pdf_with_image(pdf7, qr_png7)

    res7 = VI.upsert_document(con7, pdf7, d7)
    ok("pipeline_upsert_returned_row", res7 is not None)
    doc_id7, kind7 = res7
    ok("pipeline_kind_is_pdf", kind7 == "pdf")

    indexed7, queued7 = VI.index_pdf(con7, doc_id7, pdf7)
    con7.commit()
    ok("pipeline_page_queued_for_ocr", indexed7 == 0 and queued7 == 1)   # image-only page -> no extractable text
    pre = con7.execute("SELECT ocr_status, barcode_nsn FROM pages WHERE document_id=?", (doc_id7,)).fetchone()
    ok("pipeline_pre_ocr_pending_no_barcode_yet", pre == ("pending", None))

    remaining7 = VI.ocr(con7, 10, workers=1)
    ok("pipeline_ocr_drained_queue", remaining7 == 0)

    post = con7.execute(
        "SELECT ocr_status, barcode_type, barcode_data, barcode_nsn FROM pages WHERE document_id=?",
        (doc_id7,)).fetchone()
    ok("pipeline_page_marked_done", post is not None and post[0] == "done")
    ok("pipeline_barcode_type_stored", post is not None and post[1] == "QRCODE")
    ok("pipeline_barcode_data_stored", post is not None and post[2] == payload7)
    ok("pipeline_barcode_nsn_stored", post is not None and post[3] == nsn7)

    n7 = VI.extract_parts(con7)
    ok("pipeline_extract_parts_found_the_barcode_row", n7 >= 1)
    prow = con7.execute(
        "SELECT nsn, document_id, page, vehicle, fig_no, fig_title, confidence FROM parts WHERE confidence='barcode'"
    ).fetchall()
    ok("pipeline_exactly_one_barcode_part_row", len(prow) == 1)
    if prow:
        r = prow[0]
        ok("pipeline_barcode_part_nsn_correct", r[0] == nsn7)
        ok("pipeline_barcode_part_document_correct", r[1] == doc_id7)
        ok("pipeline_barcode_part_page_correct", r[2] == 1)
        ok("pipeline_barcode_part_vehicle_correct", r[3] == "HMMWV")
        ok("pipeline_barcode_part_confidence_distinguishable", r[6] == "barcode")

    # idempotent rebuild: re-running extract_parts() must reproduce exactly the same barcode row --
    # not duplicate it, not silently drop it in the DELETE-then-rebuild it does at the top of the
    # function (the DELETE removes ALL confidence-tagged rows, 'barcode' included; this proves the
    # barcode-derived rows are regenerated from pages.barcode_nsn every time, same as the regex rows
    # are regenerated from body_text).
    n7b = VI.extract_parts(con7)
    prow2 = con7.execute("SELECT nsn, document_id, page, confidence FROM parts WHERE confidence='barcode'").fetchall()
    ok("pipeline_idempotent_rerun_same_count", n7b == n7)
    ok("pipeline_idempotent_rerun_same_row", prow2 == [(nsn7, doc_id7, 1, "barcode")])

    # downstream consumption: features/parts_feature.py's part_lookup() (named in the work item) --
    # the barcode row must surface through the SAME query every other confidence-tagged row does.
    class _Core:
        DB_PATH = os.path.join(d7, "viewer.db")
        @staticmethod
        def db():
            c = sqlite3.connect(_Core.DB_PATH, timeout=30); c.row_factory = sqlite3.Row; return c
    parts_feature.core = _Core
    looked_up = parts_feature.part_lookup(nsn7)
    ok("pipeline_part_lookup_found", looked_up.get("found") is True)
    ok("pipeline_part_lookup_cites_the_page", any(
        ref.get("document_id") == doc_id7 and ref.get("page") == 1 for ref in looked_up.get("refs", [])))

    con7.close()
except Exception as e:
    failed.append("section7_full_pipeline(%s)" % e)


# =====================================================================================================
# Section 8 -- a page whose barcode carries no NSN must NOT produce a parts row on extract_parts(),
# even though barcode_type/barcode_data got captured on the page itself (section 5's claim, now
# checked through the real pipeline instead of _scan_barcode() in isolation).
# =====================================================================================================
try:
    d8, con8 = _new_db("barcode_no_nsn_pipeline_")
    vdir8 = os.path.join(d8, "M1078"); os.makedirs(vdir8)
    qr_png8 = os.path.join(vdir8, "_qr_src.png")
    ok("no_nsn_pipeline_qr_build_ok", _qr_png("PART NO MS35338-44 LOCKWASHER", qr_png8))
    pdf8 = os.path.join(vdir8, "doc.pdf")
    _pdf_with_image(pdf8, qr_png8)

    doc_id8, _ = VI.upsert_document(con8, pdf8, d8)
    VI.index_pdf(con8, doc_id8, pdf8); con8.commit()
    VI.ocr(con8, 10, workers=1)

    page8 = con8.execute("SELECT barcode_type, barcode_nsn FROM pages WHERE document_id=?", (doc_id8,)).fetchone()
    ok("no_nsn_pipeline_type_captured_on_page", page8 is not None and page8[0] == "QRCODE")
    ok("no_nsn_pipeline_nsn_null_on_page", page8 is not None and page8[1] is None)

    VI.extract_parts(con8)
    n_rows8 = con8.execute("SELECT COUNT(*) FROM parts WHERE confidence='barcode' AND document_id=?",
                           (doc_id8,)).fetchone()[0]
    ok("no_nsn_pipeline_no_parts_row_created", n_rows8 == 0)
    con8.close()
except Exception as e:
    failed.append("section8_no_nsn_no_parts_row(%s)" % e)


for n in passed: print("PASS", n)
for n in failed: print("FAIL", n)
print("\n%d passed, %d failed (of %d checks for barcodes.py's OCR-pass wiring, decode backend=%s)" %
      (len(passed), len(failed), len(passed) + len(failed), barcodes.backend()))
sys.exit(1 if failed else 0)

# END OF FILE
