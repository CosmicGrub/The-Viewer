-- THE VIEWER -- schema migration 0012 (barcode vs. OCR NSN conflict detection)
-- Additive (R1): extract_parts() (viewer_ingest.py) already inserts BOTH an OCR-regex-derived NSN
-- row (confidence='page') and a barcode-decoded NSN row (confidence='barcode') for the same page,
-- deliberately with separate dedup keys so a page whose OCR text and barcode encode the SAME NSN
-- keeps both rows (recommendations annex #14: barcode-ocr-conflict). But when they encode DIFFERENT
-- NSNs, nothing ever compared them -- both rows were simply inserted independently, with no way for
-- a downstream consumer (features/parts_feature.py's part_lookup()) or the UI to know the two
-- sources disagreed on the same page.
--
-- This table records that disagreement explicitly. extract_parts() does a full DELETE-then-rebuild
-- of `parts` every run (see its own docstring); this table gets the same full-rebuild contract --
-- DELETE FROM parts_conflicts at the top of extract_parts(), repopulated from scratch each run, so
-- it never accumulates stale conflicts from a page whose OCR/barcode disagreement has since been
-- resolved (better OCR pass, corrected barcode capture, etc.).
CREATE TABLE IF NOT EXISTS parts_conflicts(
  id INTEGER PRIMARY KEY, document_id INTEGER, page INTEGER, vehicle TEXT,
  barcode_nsn TEXT, page_nsn TEXT, created_at TEXT DEFAULT (datetime('now')));
CREATE INDEX IF NOT EXISTS ix_parts_conflicts_nsn ON parts_conflicts(barcode_nsn, page_nsn);
CREATE INDEX IF NOT EXISTS ix_parts_conflicts_doc ON parts_conflicts(document_id, page);
