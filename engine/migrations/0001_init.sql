-- THE VIEWER -- schema migration 0001 (initial)
-- Backwards-compatibility rule R1: additive only. New migrations add columns/tables;
-- they never repurpose or destructively drop. Old readers keep working.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
    id                INTEGER PRIMARY KEY CHECK (id = 1),
    schema_version    INTEGER NOT NULL,
    migration_history TEXT    NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS documents (
    id          INTEGER PRIMARY KEY,
    path        TEXT NOT NULL UNIQUE,
    rel_path    TEXT,
    fingerprint TEXT,                 -- size:mtime:headhash  (cheap, change-detect)
    type        TEXT,                 -- pdf_text | pdf_scanned | image | office | other
    tm_number   TEXT,
    nsn         TEXT,
    title       TEXT,
    vehicle     TEXT,                 -- top-level category folder
    page_count  INTEGER DEFAULT 0,
    size_bytes  INTEGER,
    mtime       REAL,
    status      TEXT DEFAULT 'discovered',
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_documents_vehicle ON documents(vehicle);
CREATE INDEX IF NOT EXISTS ix_documents_status  ON documents(status);

CREATE TABLE IF NOT EXISTS pages (
    id          INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    body_text   TEXT DEFAULT '',
    char_count  INTEGER DEFAULT 0,
    source      TEXT DEFAULT 'none',  -- text | ocr | none
    ocr_status  TEXT DEFAULT 'none',  -- none | pending | running | done | failed
    UNIQUE(document_id, page_number)
);
CREATE INDEX IF NOT EXISTS ix_pages_ocr ON pages(ocr_status);

-- Full-text index over page text (external content -> no duplication).
CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
    body_text,
    content='pages',
    content_rowid='id',
    tokenize='unicode61'
);

-- Keep FTS in sync (also handles OCR updates that rewrite body_text).
CREATE TRIGGER IF NOT EXISTS pages_ai AFTER INSERT ON pages BEGIN
    INSERT INTO pages_fts(rowid, body_text) VALUES (new.id, new.body_text);
END;
CREATE TRIGGER IF NOT EXISTS pages_ad AFTER DELETE ON pages BEGIN
    INSERT INTO pages_fts(pages_fts, rowid, body_text) VALUES('delete', old.id, old.body_text);
END;
CREATE TRIGGER IF NOT EXISTS pages_au AFTER UPDATE ON pages BEGIN
    INSERT INTO pages_fts(pages_fts, rowid, body_text) VALUES('delete', old.id, old.body_text);
    INSERT INTO pages_fts(rowid, body_text) VALUES (new.id, new.body_text);
END;

-- The durable ingestion / OCR job queue.
CREATE TABLE IF NOT EXISTS jobs (
    id          INTEGER PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    page_id     INTEGER REFERENCES pages(id) ON DELETE CASCADE,
    stage       TEXT,                 -- extract | ocr
    state       TEXT DEFAULT 'pending', -- pending | running | done | failed
    attempts    INTEGER DEFAULT 0,
    last_error  TEXT,
    updated_at  TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_jobs_state ON jobs(stage, state);

CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY,
    started_at  TEXT DEFAULT (datetime('now')),
    finished_at TEXT,
    kind        TEXT,                 -- crawl | ocr
    files_seen  INTEGER DEFAULT 0,
    new_docs    INTEGER DEFAULT 0,
    pages_indexed INTEGER DEFAULT 0,
    ocr_queued  INTEGER DEFAULT 0,
    ocr_done    INTEGER DEFAULT 0,
    failed      INTEGER DEFAULT 0
);

-- Forward-compat placeholders (filled in later milestones, additively).
CREATE TABLE IF NOT EXISTS parts (
    id INTEGER PRIMARY KEY, name TEXT, part_number TEXT, nsn TEXT
);
CREATE TABLE IF NOT EXISTS part_variants (
    id INTEGER PRIMARY KEY, part_id INTEGER REFERENCES parts(id),
    differs_how TEXT, how_to_tell_apart TEXT
);
CREATE TABLE IF NOT EXISTS procedures (
    id INTEGER PRIMARY KEY, part_id INTEGER REFERENCES parts(id),
    kind TEXT, steps TEXT, tools_required TEXT
);
CREATE TABLE IF NOT EXISTS figures (
    id INTEGER PRIMARY KEY, document_id INTEGER REFERENCES documents(id),
    page_number INTEGER, source_ref TEXT
);

INSERT OR IGNORE INTO schema_meta(id, schema_version, migration_history)
VALUES (1, 1, json_array(json_object('version',1,'applied_at',datetime('now'),'note','initial schema')));
