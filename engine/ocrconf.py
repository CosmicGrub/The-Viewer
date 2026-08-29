#!/usr/bin/env python3
"""THE VIEWER -- PER-LINE OCR CONFIDENCE SIDECAR (v1.0, catalog §1.9, design doc
docs/superpowers/specs/2026-08-25-per-line-ocr-confidence-design.md). `pages.ocr_confidence` already stores
ONE number per page -- RapidOCR's own per-line detection scores averaged together and the per-line detail
discarded (viewer_ingest.py's `ocr_one()`, previously). This is genuinely per-LINE confidence (RapidOCR's
detection stage groups text into line/phrase boxes; its public API has no per-word or per-character score --
see the design doc's "Why / corrected premise" for why the catalog's original "per-word" phrasing didn't
match what the engine actually returns). A consumer that wants "which words does this apply to" attributes
a line's score down to the words IN that line -- honest framing: line-level measurement, word-level
*attribution*, not independent per-word confidence.

Own sidecar (index/ocrconf.db), own schema, own `CREATE TABLE IF NOT EXISTS` init -- mirrors dedup.py's/
pageqa.py's "own sidecar, own schema, never touches viewer.db" pattern (R6: append-only, corpus
authoritative). Unlike dedup.py/pageqa.py this has no batch driver: `record_lines()` is called INLINE, once
per OCR'd page, straight out of viewer_ingest.py's `ocr()` (see that module's `handle()` callback) --
matches how BARCODE_SCAN/MEASURES_SCAN already write their own per-page results live during ingest rather
than as a separate host-run pass. Never blocks or fails a page's OCR: `record_lines()` is best-effort and
never raises (same posture as every other sidecar writer in viewer_ingest.py) -- the page-level
`UPDATE pages ... ocr_status='done'` already happens first and independently; a failure to persist per-line
detail must never turn a successful page OCR into a failed one.

Pure sidecar I/O -- no extraction logic lives here. `lines` is always `[(text, score), ...]`, already
computed by RapidOCR and handed in by the caller; this module only ever writes/reads it.

Only ever populated on the RapidOCR path -- the Tesseract fallback has no per-line score exposed the same
way (`conf=None` already signals this at the page level; this sidecar is just never written to on that
path -- `lines_for_page()` still returns `[]`, not an error, exactly like a corpus with no RapidOCR pages
at all)."""
from __future__ import annotations

import os
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS ocr_lines(
  document_id INTEGER NOT NULL,
  page_number INTEGER NOT NULL,
  line_index  INTEGER NOT NULL,
  text        TEXT,
  confidence  REAL,
  PRIMARY KEY(document_id, page_number, line_index)
);
"""


def available(db_path):
    """True only when db_path exists and is a non-empty file -- same "sidecar hasn't been built/
    populated yet" signal publogdiff.py's own available(db_path=None) already uses. Lets a future
    route/consumer check for the sidecar's existence before querying it without opening a connection
    first; never raises (a bad/None path is just False, not an exception)."""
    try:
        return bool(db_path and os.path.exists(db_path) and os.path.getsize(db_path) > 0)
    except OSError:
        return False


def record_lines(db_path, document_id, page_number, lines):
    """Writes one row per (text, score) pair in `lines` for this document_id/page_number, replacing
    whatever was previously stored for that page (a retried/re-OCR'd page must never leave stale or
    duplicate rows behind -- delete-then-insert in one transaction, not a bare INSERT OR REPLACE, so a
    re-run that produces FEWER lines than before doesn't leave the old page's extra trailing rows
    orphaned; a re-run with the same or more lines is just as correct either way). `lines` entries with
    a non-numeric/missing score are skipped (never written as a fabricated confidence) but the row's
    text is still recorded with confidence=NULL, matching how measures.py/tables.py already tolerate a
    partially-usable record rather than discarding the whole page's rows over one bad entry.

    Best-effort, NEVER RAISES (matches every other sidecar writer in viewer_ingest.py -- barcode/
    measures/schematics all degrade the same way): creates the sidecar directory + schema on first use;
    returns True on a successful write, False on ANY failure (bad db_path, locked/corrupt file, no
    `lines` to write, missing document_id/page_number) -- the caller (ocr()'s handle()) already treats
    this as pure enrichment and never lets it affect the page's own ocr_status."""
    if not db_path or not lines or document_id is None or page_number is None:
        return False
    try:
        d = os.path.dirname(os.path.abspath(db_path))
        if d:
            os.makedirs(d, exist_ok=True)
        con = sqlite3.connect(db_path, timeout=30)
        try:
            con.executescript(SCHEMA)
            con.execute("DELETE FROM ocr_lines WHERE document_id=? AND page_number=?",
                        (document_id, page_number))
            rows = []
            for i, item in enumerate(lines):
                try:
                    text, score = item[0], item[1]
                except (TypeError, IndexError):
                    continue
                conf = float(score) if isinstance(score, (int, float)) else None
                rows.append((document_id, page_number, i, text, conf))
            if not rows:
                con.commit()
                return False
            con.executemany(
                "INSERT OR REPLACE INTO ocr_lines(document_id,page_number,line_index,text,confidence) "
                "VALUES(?,?,?,?,?)", rows)
            con.commit()
            return True
        finally:
            con.close()
    except Exception:
        return False


def lines_for_page(db_path, document_id, page_number):
    """[{"line_index", "text", "confidence"}, ...] for this page, ordered by line_index -- [] on a
    missing/empty sidecar, a bad db_path, or any read failure, NEVER an error (same missing-sidecar-
    degrades-to-empty contract dedup.py's editions_for()/pageqa.py already guarantee). Read-only
    connection -- this module writes only via record_lines()."""
    if not available(db_path) or document_id is None or page_number is None:
        return []
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
        try:
            rows = con.execute(
                "SELECT line_index, text, confidence FROM ocr_lines WHERE document_id=? AND page_number=? "
                "ORDER BY line_index", (document_id, page_number)).fetchall()
            return [{"line_index": r[0], "text": r[1], "confidence": r[2]} for r in rows]
        finally:
            con.close()
    except sqlite3.OperationalError:
        return []   # an ocrconf.db from before this schema existed, or mid-write -- degrade, never 500
    except Exception:
        return []


if __name__ == "__main__":
    import tempfile

    tmp = os.path.join(tempfile.mkdtemp(prefix="ocrconf_selftest_"), "ocrconf.db")

    # available() is False before any write -- the sidecar doesn't exist yet.
    assert available(tmp) is False, "available() must be False before the sidecar has ever been written"

    lines = [("REMOVE THE FOUR MOUNTING BOLTS", 0.97), ("TORQUE TO 30 FOOT POUNDS", 0.91),
              ("SEE FIGURE 4-2 FOR DETAIL", 0.62)]
    ok = record_lines(tmp, document_id=1, page_number=5, lines=lines)
    assert ok is True, "record_lines() should report success for a well-formed write"
    assert available(tmp) is True, "available() must be True once the sidecar has real rows"

    got = lines_for_page(tmp, 1, 5)
    assert len(got) == 3, got
    assert got[0] == {"line_index": 0, "text": "REMOVE THE FOUR MOUNTING BOLTS", "confidence": 0.97}, got[0]
    assert got[2]["confidence"] == 0.62, got[2]

    # a different page/document must not see these rows.
    assert lines_for_page(tmp, 1, 6) == [], "an unrelated page must return empty, not leak another page's lines"
    assert lines_for_page(tmp, 2, 5) == [], "an unrelated document must return empty, not leak another doc's lines"

    # INSERT OR REPLACE / re-record semantics: re-recording the SAME page (e.g. a retried OCR job)
    # replaces its rows, never duplicates or leaves stale trailing rows from a longer prior write.
    ok2 = record_lines(tmp, document_id=1, page_number=5, lines=[("JUST ONE LINE NOW", 0.5)])
    assert ok2 is True, ok2
    got2 = lines_for_page(tmp, 1, 5)
    assert got2 == [{"line_index": 0, "text": "JUST ONE LINE NOW", "confidence": 0.5}], got2

    # a line whose score isn't numeric is kept (text preserved) with confidence=None, not dropped or
    # fabricated -- matches ocr_one()'s own "None means no scoring available" convention.
    record_lines(tmp, document_id=9, page_number=1, lines=[("NO SCORE HERE", None), ("HAS SCORE", 0.8)])
    got3 = lines_for_page(tmp, 9, 1)
    assert got3[0] == {"line_index": 0, "text": "NO SCORE HERE", "confidence": None}, got3
    assert got3[1]["confidence"] == 0.8, got3

    # degrade-to-empty contract: an unbuilt/missing sidecar, and a bad/None db_path, never raise.
    never_built = os.path.join(tempfile.mkdtemp(prefix="ocrconf_never_built_"), "ocrconf.db")
    assert available(never_built) is False, "a never-built sidecar must report unavailable"
    assert lines_for_page(never_built, 1, 1) == [], "a never-built sidecar must degrade to [], not raise"
    assert record_lines(None, 1, 1, [("x", 0.5)]) is False, "a None db_path must fail closed, never raise"
    assert record_lines(tmp, 1, 5, []) is False, "an empty lines list is a no-op failure, not a crash"
    assert lines_for_page(tmp, None, None) == [], "missing keys must degrade to [], never raise"

    print("ocrconf self-test OK  (available() False->True across a real write; round-trip text/confidence "
          "correct; keyed strictly to document_id+page_number, no cross-page/doc leakage; INSERT OR REPLACE "
          "re-record replaces rather than duplicates or leaves stale rows; a non-numeric score keeps its "
          "text with confidence=None; missing/never-built sidecar and bad inputs all degrade to []/False, "
          "never raise)")
# END OF FILE
