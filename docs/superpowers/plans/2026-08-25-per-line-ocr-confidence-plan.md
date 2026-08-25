# Per-Line OCR Confidence Capture — Implementation Plan

**Spec:** `docs/superpowers/specs/2026-08-25-per-line-ocr-confidence-design.md`
**Status:** planned, not started

No "writing-plans" skill available in this environment — written directly, following this project's own
established conventions.

## Sequencing rationale

One phase, one PR. Small, bounded surface (one new thin module, one widened function contract with exactly one
real call site to update), fully traced against the actual current code before writing this plan (not
estimated from the catalog's one-line description, which this spec's "Why" section already corrected once).

## Steps

1. **`engine/ocrconf.py`** (new) — `available(db_path)`, `record_lines(db_path, document_id, page_number,
   lines)` (`lines` = `[(text, score), ...]`; `INSERT OR REPLACE` into `ocr_lines`, own `CREATE TABLE IF NOT
   EXISTS` schema init, best-effort/never-raises matching every other sidecar writer in this codebase),
   `lines_for_page(db_path, document_id, page_number)` (SELECT ordered by `line_index`, returns `[]` on a
   missing/empty sidecar, never an error). `__main__` self-test per the spec's Testing section.

2. **`engine/viewer_ingest.py` — `ocr_one()`** (around line 872-968):
   - RapidOCR success path (~line 941-944): alongside the existing `scores`/`conf` computation from `res`,
     also build `lines = [(r[1], round(r[2], 4)) for r in res if len(r) > 2 and isinstance(r[2], (int, float))]
     or None`.
   - Tesseract-fallback path (~line 945-950): `lines = None` (matches `conf = None` on this same path).
   - Blank-skip early-return (~line 901): `return "", None, barcode` → `return "", None, barcode, None`.
   - `result = (text, conf, barcode)` (line 964) → `result = (text, conf, barcode, lines)`. The `_DEDUP` cache
     write/read at lines 913-916 and 965-967 need no code changes — they already store/replay whatever tuple
     `result` is, so this widening flows through them automatically; just confirm this directly (read the
     surrounding code again after the edit, don't assume).
   - Update the docstring (lines 872-880) to describe the new 4th return value and the per-line vs. per-word
     distinction from the spec's "Why" section, so a future reader isn't misled the way the catalog's own
     one-line description was.

3. **`engine/viewer_ingest.py` — `_ocr_task()`** (line 977-1004):
   - `box["text"], box["conf"], box["barcode"], box["lines"] = ocr_one(path, pno)` (line 992).
   - Timeout return (line 1001): `return pid, None, None, None, "timeout after %ds" % ...` → `return pid, None,
     None, None, None, "timeout after %ds" % ...`.
   - Exception-path return (line 1003): `return pid, None, None, box.get("barcode"), box["err"]` → `return pid,
     None, None, box.get("barcode"), None, box["err"]`.
   - Success return (line 1004): `return pid, box.get("text"), box.get("conf"), box.get("barcode"), None` →
     `return pid, box.get("text"), box.get("conf"), box.get("barcode"), box.get("lines"), None`.
   - Update the function's own docstring's "(pid, None, None, None, err)" shape description to match.

4. **`engine/viewer_ingest.py` — `ocr()`'s `handle()` callback** (line 1176 area):
   - Signature: `def handle(pid, text, conf, barcode, err):` → `def handle(pid, text, conf, barcode, lines,
     err):`. Both call sites (`handle(*_ocr_task(r))`, `handle(*fut.result())`) already splat — confirm no
     other change needed there (read again after editing, don't assume).
   - After the existing `UPDATE pages SET ... ocr_confidence=? ...` call and after `_lbl_pno`/`_lbl_doc_id`
     are resolved from `_labels` a few lines below (need to reorder slightly so those are available at the
     point `ocrconf.record_lines()` is called, or resolve them earlier in `handle()` — check the real code
     order and pick whichever is the smaller, cleaner diff): call `ocrconf.record_lines(ocrconf_db_path,
     _lbl_doc_id, _lbl_pno, lines)` when `lines` is truthy and `_lbl_doc_id is not None`. `ocrconf_db_path`
     resolved once outside `handle()` (near `dbdir`/`meas_con`, matching how `meas_con` is already opened
     once before the loop, not per-page).

5. **Tests**:
   - `engine/ocrconf.py` self-test (covered in step 1).
   - New `engine/tests/test_ocrconf.py` (or extend `test_ingest_routes.py` if that turns out to be the more
     natural home once the real ingest-test fixture/mocking pattern is in front of me) — real e2e through a
     mocked-RapidOCR OCR pass on a tiny fixture PDF: confirms `ocr_lines` gets one row per line with correct
     text/confidence/keys; confirms a cache-hit on an identical repeated page (the `_DEDUP` path) still writes
     the same per-line data, not an empty/missing set; confirms a Tesseract-fallback run writes nothing (no
     error) to the sidecar.
   - Confirm `engine/tests/test_ingest_routes.py`'s existing RapidOCR-mocking pattern (if one exists) is reused
     rather than re-invented — read that file's current mocking approach first.

6. **Docs**: `CHANGELOG.md` entry (dense/specific voice, includes the corrected "per-line not per-word" framing
   from the spec's "Why" section); `docs/EXTRACTION-METHODS-CATALOG.md` §1.9 status `◐` → `◐` with an updated
   Approach/library cell (per-line now captured, per-word explicitly noted as the remaining, GPU-dependent
   gap) — not `✅`, since true per-word is still open by design; `docs/SYSTEM-REQUIREMENTS.md` unaffected (no
   new dependency, `ocrconf.py` has none).

7. **Verify**: `python -m py_compile` on every touched file; the new test run directly (not just claimed);
   `engine/tests/verify_all.py --snapshot` full run, output inspected directly, before opening the PR. Given
   this touches `viewer_ingest.py`'s core OCR path, also directly re-run `test_ingest_routes.py` and any other
   existing test file that already exercises `ocr_one()`/`_ocr_task()`/`ocr()` to confirm zero behavior change
   for every existing caller/consumer of the 3 widened function contracts.

## Open decisions carried from the spec (resolve during implementation, not blocking)

Exact `ocrconf.py` location/name; whether `test_ocrconf.py` is a new file or an extension of
`test_ingest_routes.py` — resolve by reading the existing ingest-test fixture/mocking pattern first, follow
whichever is the more natural fit, don't guess.
