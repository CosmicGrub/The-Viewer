-- THE VIEWER -- schema migration 0007 (PUB LOG reference fields)
-- Additive (R1) + append-only friendly (R6): extend the external NSN reference tables with the fields
-- PUB LOG (DLA) provides -- authoritative part number / CAGE (MCRD), characteristics (size/thread for
-- Tier 2.5), AAC and substitutes (MDI&S). Nothing existing is changed or removed.

ALTER TABLE ref_nsn ADD COLUMN part_no         TEXT;
ALTER TABLE ref_nsn ADD COLUMN cagec           TEXT;
ALTER TABLE ref_nsn ADD COLUMN characteristics TEXT;
ALTER TABLE ref_nsn ADD COLUMN aac             TEXT;
ALTER TABLE ref_nsn ADD COLUMN substitutes     TEXT;

ALTER TABLE ref_nsn_log ADD COLUMN part_no         TEXT;
ALTER TABLE ref_nsn_log ADD COLUMN cagec           TEXT;
ALTER TABLE ref_nsn_log ADD COLUMN characteristics TEXT;
ALTER TABLE ref_nsn_log ADD COLUMN aac             TEXT;
ALTER TABLE ref_nsn_log ADD COLUMN substitutes     TEXT;
