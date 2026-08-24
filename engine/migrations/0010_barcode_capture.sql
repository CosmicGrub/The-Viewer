-- THE VIEWER -- schema migration 0010 (barcode/QR capture on OCR'd pages)
-- Additive (R1): barcodes.py (catalog §4.9) has had a fully-built, self-tested, dual-backend
-- (pyzbar/OpenCV) barcode/QR/Data-Matrix detect() since it was written, but nothing in the ingest
-- pipeline ever called it -- it had no caller anywhere except its own self-test and the module
-- import-check in verifystate.py. Wired into viewer_ingest.ocr_one() (reuses the PNG _render_png()
-- already produces for OCR -- never a second render), opt-in + cheap via VIEWER_BARCODE_SCAN
-- (default on) and barcodes.available() (no-ops instantly when neither pyzbar nor OpenCV is
-- installed, same graceful degradation barcodes.py already has).
--
-- Some TMs print NSNs/part numbers as barcodes; a machine-decoded value has no character-recognition
-- ambiguity, so it is higher-trust provenance than OCR text. These three nullable columns are the
-- per-page capture (mirrors migration 0009's ocr_confidence: additive signal alongside body_text,
-- NULL for every page OCR'd before this migration -- not backfilled, would require a full re-OCR
-- pass). extract_parts() (viewer_ingest.py) reads barcode_nsn back out on its next full rebuild and
-- inserts a parts row tagged confidence='barcode' -- distinguishable from the existing 'page'/
-- 'aligned' regex-extracted rows, and picked up for free by every existing confidence-IS-NOT-NULL
-- consumer (features/parts_feature.py's part_lookup()/part_differences()).
ALTER TABLE pages ADD COLUMN barcode_type TEXT;   -- decoded symbology, e.g. 'QRCODE' | 'EAN13' | 'CODE128'
ALTER TABLE pages ADD COLUMN barcode_data TEXT;   -- raw decoded payload (truncated; first barcode found)
ALTER TABLE pages ADD COLUMN barcode_nsn  TEXT;   -- NSN scraped from the payload, if any -- feeds parts

CREATE INDEX IF NOT EXISTS ix_pages_barcode_nsn ON pages(barcode_nsn);
