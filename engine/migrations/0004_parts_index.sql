-- THE VIEWER -- schema migration 0004 (structured parts index + tech-status capture)
-- Backwards-compatibility rule R1: additive only. Extends the reserved `parts` table with the
-- columns the RPSTL extractor fills, and records the tech-status suggestion alongside the confirmed
-- one (so the learning signal can measure accept vs override). Nothing existing is changed.

ALTER TABLE parts ADD COLUMN document_id INTEGER;
ALTER TABLE parts ADD COLUMN page        INTEGER;
ALTER TABLE parts ADD COLUMN vehicle     TEXT;
ALTER TABLE parts ADD COLUMN nomenclature TEXT;   -- best-effort / figure-title context
ALTER TABLE parts ADD COLUMN cagec       TEXT;
ALTER TABLE parts ADD COLUMN smr         TEXT;
ALTER TABLE parts ADD COLUMN fig_no      TEXT;
ALTER TABLE parts ADD COLUMN fig_title   TEXT;
ALTER TABLE parts ADD COLUMN uoc         TEXT;
ALTER TABLE parts ADD COLUMN confidence  TEXT;     -- 'page' (NSN+fig+cite, reliable) | 'aligned' (row-aligned)
ALTER TABLE parts ADD COLUMN created_at  TEXT;

CREATE INDEX IF NOT EXISTS ix_parts_nsn     ON parts(nsn);
CREATE INDEX IF NOT EXISTS ix_parts_vehicle ON parts(vehicle);
CREATE INDEX IF NOT EXISTS ix_parts_fig     ON parts(vehicle, fig_no);

-- Capture the suggested status + its basis next to the confirmed sessions.tech_status.
ALTER TABLE sessions ADD COLUMN tech_status_suggested TEXT;
ALTER TABLE sessions ADD COLUMN tech_status_basis     TEXT;  -- pmcs | history | none
