-- THE VIEWER -- schema migration 0005 (online -> offline reference enrichment)
-- Backwards-compatibility rule R1: additive only. New tables hold EXTERNAL reference data fetched
-- once online (public-domain standards + official GSA NSN extract) and used offline thereafter. They
-- are kept SEPARATE from the manual-derived tables and carry full provenance (source + url + date)
-- so external data can never masquerade as TM-sourced.

-- Public-domain standard-hardware dimensions (threads/fasteners). Facts; cited to the source standard.
CREATE TABLE IF NOT EXISTS ref_hardware (
    id              INTEGER PRIMARY KEY,
    size            TEXT,        -- e.g. "1/2-13 UNC"
    series          TEXT,        -- UNC | UNF | metric
    major_in        REAL,        -- major diameter (inches; metric stored as mm in major_mm)
    major_mm        REAL,
    tpi_or_pitch    TEXT,        -- threads-per-inch (inch) or pitch mm (metric)
    tap_drill       TEXT,
    torque_ref_lbft TEXT,        -- GENERAL reference (grade 5 / 8.8, dry). The TM's stated torque GOVERNS.
    source          TEXT,
    source_url      TEXT,
    fetched_at      TEXT
);
CREATE INDEX IF NOT EXISTS ix_ref_hardware_size ON ref_hardware(size);

-- Official NSN -> item name / description (+ public GSA price). Filtered to NSNs already in the index.
CREATE TABLE IF NOT EXISTS ref_nsn (
    nsn         TEXT PRIMARY KEY,
    item_name   TEXT,
    description TEXT,
    gsa_price   TEXT,            -- public GSA list price (NOT FEDLOG); clearly labeled in the UI
    source      TEXT,
    source_url  TEXT,
    fetched_at  TEXT,
    official    INTEGER DEFAULT 1
);
