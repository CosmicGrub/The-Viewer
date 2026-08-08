-- THE VIEWER -- schema migration 0006 (append-only NSN reference log)
-- Standing rule R6: always ADD, never take away -- even outdated info is retained. NSN reference data
-- can change over time (re-cataloging, supersession); we keep EVERY fetched version in an append-only
-- log and treat the most recent as "current". Nothing is ever deleted or overwritten without a trace.
-- Additive (R1): new table only; ref_nsn from 0005 is kept as a convenience "current" pointer.

CREATE TABLE IF NOT EXISTS ref_nsn_log (
    id          INTEGER PRIMARY KEY,
    nsn         TEXT,
    item_name   TEXT,
    description TEXT,
    gsa_price   TEXT,
    source      TEXT,
    source_url  TEXT,
    fetched_at  TEXT
);
CREATE INDEX IF NOT EXISTS ix_ref_nsn_log_nsn ON ref_nsn_log(nsn, fetched_at);
