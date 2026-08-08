-- THE VIEWER -- schema migration 0003 (OCR skip-junk + prioritization)
-- Backwards-compatibility rule R1: additive. Adds a priority column + index, and narrows the
-- FTS sync trigger to fire only when body_text actually changes (so status/priority updates no
-- longer trigger a full-text reindex -- big speedup for cleanup/requeue and prioritization).

ALTER TABLE pages ADD COLUMN ocr_priority INTEGER DEFAULT 5;   -- lower = OCR sooner
CREATE INDEX IF NOT EXISTS ix_pages_ocr_pri ON pages(ocr_status, ocr_priority, id);

DROP TRIGGER IF EXISTS pages_au;
CREATE TRIGGER pages_au AFTER UPDATE OF body_text ON pages BEGIN
    INSERT INTO pages_fts(pages_fts, rowid, body_text) VALUES('delete', old.id, old.body_text);
    INSERT INTO pages_fts(rowid, body_text) VALUES (new.id, new.body_text);
END;
