#!/usr/bin/env python3
"""v1.30 (roadmap Next-tier item 9): regression coverage for search()'s ocr_confidence SELECT.

THE BUG: p.ocr_confidence has existed on the `pages` table since migration 0009 and corpus.py's own
FTS query already selects it (engine/features/corpus.py:20), but search_feature.py's search() -- the
actual /api/search backend, what every real query on the home page hits -- never selected it in
either of its two real row-building SELECTs (_meta_rows()'s FTS path, and the LIKE fallback path).
Confirmed live against the real corpus before fixing: querying pages.ocr_confidence directly showed
53,391 pages with source="ocr" in this deployment, and every search() result row was silently missing
the column regardless -- a mechanic never saw a low-OCR-confidence warning on a search result, only on
the separate part-match card (renderPartMatch()) and part-info drawer (pdRenderMatches()).

THE FIX: p.ocr_confidence added to both SELECTs. dict(r) (sqlite3.Row column-name mapping) picks up
the new column automatically -- no other Python code needed to change for the key to reach the
returned row; engine/ui/index.html's renderList() reads r.ocr_confidence directly (see its own
comment) once this fix lands.

This test builds the shared fixture DB, then UPDATEs one page's ocr_confidence directly (the fixture
itself leaves this NULL on every row, matching the real corpus's default-unpopulated state confirmed
above) so the assertion is meaningful: proves search() returns the real value now, not just "search()
doesn't crash"."""
import os
import sys
import tempfile
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)
import fixture                                            # noqa: E402

PASS = 0; FAIL = 0


def ok(name, cond):
    global PASS, FAIL
    print(("PASS " if cond else "FAIL ") + name)
    if cond: PASS += 1
    else: FAIL += 1


def main():
    tmp = tempfile.mkdtemp()
    db, _corr = fixture.build(tmp)

    # Set a real, known ocr_confidence on the fixture's one OCR page (id=5, "Forklift bolt ...") --
    # the fixture itself leaves every row NULL (matching the real corpus's unpopulated-today state,
    # confirmed live), so this UPDATE is what makes the assertion below meaningful rather than vacuous.
    con = sqlite3.connect(db)
    con.execute("UPDATE pages SET ocr_confidence=0.42 WHERE id=5")
    con.commit(); con.close()

    import viewer_app as V
    V.DB_PATH = db; V.INDEX_DIR = os.path.dirname(db)
    V._VOCAB_READY = False
    from features import search_feature as SF

    # "forklift" (single, real, indexed token) matches page id=5 via the FTS path (_meta_rows()).
    rows = SF.search("forklift", limit=20)
    ok("search_still_returns_real_rows_for_forklift", bool(rows))
    hit = next((r for r in rows if r.get("page_number") == 9 and r.get("doc_id") == 3), None)
    ok("the_ocr_page_is_actually_in_the_result_set", hit is not None)
    if hit is not None:
        ok("ocr_confidence_key_present_on_the_row", "ocr_confidence" in hit)
        ok("ocr_confidence_value_is_the_real_stored_number_not_missing",
           hit.get("ocr_confidence") == 0.42)
        ok("source_is_ocr_on_this_row_confirming_it_is_the_right_page",
           hit.get("source") == "ocr")

    # A text-layer page (no ocr_confidence set, matching the fixture's default) should come back
    # with ocr_confidence present-but-None, not silently absent from the dict either way.
    rows2 = SF.search("brake", limit=20)
    text_hit = next((r for r in rows2 if r.get("source") == "text"), None)
    ok("a_text_layer_hit_exists_for_brake", text_hit is not None)
    if text_hit is not None:
        ok("ocr_confidence_key_present_even_when_null",
           "ocr_confidence" in text_hit and text_hit.get("ocr_confidence") is None)

    return PASS, FAIL


if __name__ == "__main__":
    p, f = main()
    print("\n%d passed, %d failed" % (p, f))
    sys.exit(1 if f else 0)

# END OF FILE
