-- THE VIEWER -- schema migration 0009 (OCR confidence capture)
-- Additive (R1): RapidOCR computes a per-line confidence score for every text detection, but ocr_one()
-- in viewer_ingest.py discarded it -- only the recognized text was ever kept. This adds a nullable
-- column to store the page-level average confidence (0.0-1.0) alongside the text, so OCR quality becomes
-- a real, measurable, corpus-wide signal instead of an unmeasured guess (docs/CHANGELOG.md [1.13.5]).
-- NULL for: pages OCR'd before this migration (not backfilled -- would require a full re-OCR pass),
-- pages indexed via native PDF text extraction (source='text', never touched by OCR at all), and pages
-- OCR'd via the Tesseract fallback path (doesn't expose per-line confidence the same way RapidOCR does).
ALTER TABLE pages ADD COLUMN ocr_confidence REAL;
