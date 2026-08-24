-- THE VIEWER -- schema migration 0011 (page-level schematic detection, DB-backed)
-- Before this migration, "schematic" identification was purely a DOCUMENT-level filename/title
-- LIKE match (browse_feature.py's _SCHEM_WHERE, matching '%SCHEMATIC%'/'%WIRING%'/'%SCHEM%'
-- against documents.path/title/tm_number) -- it never looked at PDF content and could not say
-- which PAGE(S) of a manual are actually schematic sheets. A real per-page circuit-netlist
-- extraction engine already existed (schem_overlay.py + schemgraph.py) but only ran as a separate,
-- manual batch tool (BUILD-SCHEMGRAPH.bat) -- and even that only works on VECTOR-native PDF pages
-- (>=12 native drawing paths); a scanned/photographed schematic page produced nothing at all,
-- with no fallback.
--
-- This table is the first PAGE-level, DB-backed schematic record, populated live during the
-- in-app scan job (viewer_ingest.py) via two independent detection signals:
--   'vector'  -- schem_overlay.schem_paths() found real vector drawing geometry; schemgraph.py's
--               existing netlist inference ran and its JSON graph was cached to the SAME
--               index/schemcache/<doc>_<page>.json location BUILD-SCHEMGRAPH.bat already writes,
--               so /schemflow.js and Circuit Lab's read-only reference panel pick it up with zero
--               changes of their own.
--   'keyword' -- the page's own text (direct-extracted or OCR'd -- whichever the ingest pipeline
--               already produced) contains a schematic/wiring/circuit/diagram caption. Catches
--               scanned/raster schematic pages the vector path can never see; no netlist, just a
--               correctly-identified, citable page.
-- A page can match both; 'vector' is recorded when it does, since an actual netlist is the
-- strictly stronger signal.
--
-- Deliberately does NOT touch index/schemgraph_coverage.tsv or index/schemgraph_done.txt --
-- those remain the separate batch tool's own bookkeeping; this table is the richer, page-level,
-- DB-queryable replacement for the document-level LIKE filter, not a takeover of the netlist
-- cache's resumability mechanism.
CREATE TABLE IF NOT EXISTS schematics(
  id INTEGER PRIMARY KEY,
  document_id INTEGER NOT NULL,
  page_number INTEGER NOT NULL,
  vehicle TEXT,
  detected_via TEXT NOT NULL,       -- 'vector' | 'keyword'
  has_netlist INTEGER DEFAULT 0,    -- 1 iff a schemcache/<doc>_<page>.json netlist graph was cached
  net_count INTEGER,
  component_count INTEGER,
  confidence REAL,
  caption TEXT,                     -- matched keyword + surrounding context, for 'keyword' rows
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_schematics_doc ON schematics(document_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_schematics_doc_page ON schematics(document_id, page_number);
