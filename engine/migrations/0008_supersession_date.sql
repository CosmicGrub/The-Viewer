-- THE VIEWER -- schema migration 0008 (FLIS supersession / vintage / multiple-choice)
-- Additive (R1) + append-only (R6). Records, per NSN: the FLIS data vintage (so the UI can show the year
-- the info was last effective in FLIS), supersession / interchangeable cross-reference, and additional
-- reference part numbers (when an NSN has more than one -> "multiple choice, verify").

ALTER TABLE ref_nsn ADD COLUMN data_date  TEXT;   -- FLIS effective date (latest); UI shows the year
ALTER TABLE ref_nsn ADD COLUMN superseded TEXT;   -- cancellation / interchangeable / current-NSN cross-ref
ALTER TABLE ref_nsn ADD COLUMN alt_parts  TEXT;   -- additional reference part numbers for this NSN

ALTER TABLE ref_nsn_log ADD COLUMN data_date  TEXT;
ALTER TABLE ref_nsn_log ADD COLUMN superseded TEXT;
ALTER TABLE ref_nsn_log ADD COLUMN alt_parts  TEXT;
