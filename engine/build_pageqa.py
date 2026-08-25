#!/usr/bin/env python3
"""THE VIEWER -- VISION-LANGUAGE PAGE-QA BATCH BUILDER (v1.0, catalog §10.1 + §3.12, design doc
docs/superpowers/specs/2026-08-24-vision-language-page-qa-design.md, plan item 12). The Phase 2 "Automatic
consumer" the design spec describes: samples pages the corpus's OWN regex/geometry extractors
(measures.py/tables.py/RPSTL) found NOTHING on, asks pageqa.py's shared core a generic sweep question in
mode="structured", strict=True, and writes ONLY verified=True rows into a new standalone sidecar,
index/pageqa.db -- own schema, own CREATE TABLE IF NOT EXISTS init, exactly like dedup.db/kg.db/masterfile.db
(R1: additive/rollbackable; R6: append-only, never touches the corpus or any existing sidecar). Read-only on
viewer.db/measures.db/tables.db/rpstl.db; the only thing ever written is pageqa.db. Never runs automatically
during ingest -- an operator runs BUILD-PAGEQA.bat / `python build_pageqa.py --max-pages N` host-side, same
posture as DEDUP.bat/build_dedup.py.

WHY "structurally mirrors build_dedup.py" but ISN'T byte-for-byte identical to it (read before changing
either file -- three deliberate departures, each because build_dedup.py's own actual code, not the plan
prose describing it, doesn't do what a surface reading might suggest):

  1. NO safeguard.snapshot()/safeguard.atomic_sqlite_build() here. build_dedup.py itself has no
     safeguard.snapshot() call at all (checked directly -- it only guards on `os.path.exists(DB)`); the
     safeguard.atomic_sqlite_build() scaffold IS used one layer down, inside dedup.py's own build(), but
     that fits a "recompute the WHOLE sidecar from scratch every run" tool (dedup.py's clustering has no
     notion of a partial/incremental run -- same shape as kg.py/build_publog.py/build_rpstl.py, all of
     which also fully rebuild their sidecar every invocation via that same scaffold). This tool is the
     OPPOSITE shape on purpose: --max-pages is a per-run BUDGET, meant to be re-run repeatedly to make
     gradual, resumable progress across a huge corpus without ever re-deriving or discarding rows a prior
     run already verified and wrote. That incremental-accumulation shape already has a real, better-
     fitting precedent in THIS codebase -- build_measures.py/build_tables.py, which open their sidecar
     directly (`sqlite3.connect(SIDE)`), `executescript(CREATE TABLE IF NOT EXISTS ...)`, and commit
     incrementally rather than building an entire fresh copy to a temp file and swapping it in. This file
     follows THAT precedent, not the atomic-rebuild one, because it is the one that actually matches this
     tool's own run shape.
  2. Idempotent re-run, concretely: pageqa_extractions has a UNIQUE(document_id, page_number) constraint
     and every write is `INSERT OR REPLACE` keyed on exactly that pair -- the design spec's own suggested
     fallback ("if none [do], use an INSERT OR REPLACE / delete-then-insert keyed on document_id+page_number")
     since no existing build_*.py driver's own idempotency shape (measures/tables' per-DOCUMENT skip-if-
     already-done ledger) maps directly onto a per-PAGE sampler like this one. Belt AND suspenders: the
     candidate query below (_candidate_pages) ALSO excludes any (document_id, page_number) already present
     in pageqa.db from an earlier run, so a plain re-run with the same --max-pages naturally samples NEW
     pages rather than re-asking the model about ones it already verified -- the UNIQUE/INSERT-OR-REPLACE
     is defense-in-depth for the (currently theoretical, future-proofing) case where a later version of
     this tool re-asks an already-answered page on purpose (e.g. a changed question template) and must
     still never leave two rows for the same page.
  3. Availability-gate exit code: build_dedup.py itself has no optional-dependency gate to mirror (dedup.py
     is pure stdlib -- nothing to be "unavailable"). The real sibling precedent for "checks an optional
     backend's own available() up front and exits cleanly, never crashing, when it's False" is
     build_tables.py's `if not tables.available(): print(...); return 2` -- matched here verbatim
     (pageqa.available() gates on vlm.available() + the GPU-tier probe; see pageqa.py's own module
     docstring). This repo's CI runners (no GPU, no downloaded Florence-2 weights) always take this path.

QUESTION TEMPLATE (plan's own "Open items" -- deliberately resolved here, not design-blocking): ONE generic
sweep question per sampled page, not one templated question per candidate field type. measures.py's own
extract() (which pageqa.py's strict path calls on the free-text answer) already recognizes the full
dimension-type taxonomy -- torque/length/pressure/electrical/capacity/weight/temperature/area/angle/flow/
speed/force -- from whatever text comes back, so a single open question that invites ANY of those is enough
signal for this phase; a per-field-type sweep (multiple ask() calls per page) is a plausible later
refinement the design spec explicitly leaves open, not required to ship Phase 2.

USAGE (host):
    python build_pageqa.py --max-pages 200
    python build_pageqa.py --max-pages 0      # dry run: prints candidate count, writes nothing
"""
import os
import sys
import sqlite3
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pageqa  # noqa: E402

ROOT = os.path.dirname(HERE)
DB = os.environ.get("VIEWER_DB", os.path.join(ROOT, "index", "viewer.db"))
PAGEQA_DB = os.environ.get("PAGEQA_DB", os.path.join(ROOT, "index", "pageqa.db"))
MEASURES_DB = os.environ.get("MEASURES_DB", os.path.join(ROOT, "index", "measures.db"))
TABLES_DB = os.environ.get("TABLES_DB", os.path.join(ROOT, "index", "tables.db"))
RPSTL_DB = os.environ.get("RPSTL_DB", os.path.join(ROOT, "index", "rpstl.db"))

# coverage.py's own "too garbled to be worth a look" bar (see coverage.py's `ocr_confidence < 0.5` literal
# in overview()) -- reused verbatim, not a fresh guess. A page below this is skipped entirely: too garbled
# for a human to read is also not worth asking the model (design spec, "Automatic consumer" step 2).
OCR_CONFIDENCE_FLOOR = 0.5

DEFAULT_QUESTION = (
    "What measurement, dimension, torque value, capacity, weight, pressure, electrical rating, or other "
    "numeric specification is shown on this page? Quote the exact value and unit as written.")

SCHEMA = """
CREATE TABLE IF NOT EXISTS pageqa_extractions(
  id INTEGER PRIMARY KEY,
  document_id INTEGER NOT NULL,
  page_number INTEGER NOT NULL,
  type TEXT,
  value TEXT,
  value2 TEXT,
  unit TEXT,
  region_x0 REAL, region_y0 REAL, region_x1 REAL, region_y1 REAL,
  source_text TEXT,
  answer_text TEXT,
  verified INTEGER NOT NULL DEFAULT 0,
  backend TEXT,
  extracted_at REAL,
  UNIQUE(document_id, page_number)
);
CREATE INDEX IF NOT EXISTS ix_pageqa_doc  ON pageqa_extractions(document_id);
CREATE INDEX IF NOT EXISTS ix_pageqa_type ON pageqa_extractions(type);
"""
# Schema notes (documenting the "your call" fields the task left open):
#   - id: plain autoincrement surrogate key -- nothing else here is a natural single-column key.
#   - UNIQUE(document_id, page_number): this tool asks at most ONE question per sampled page (see module
#     docstring's "one generic sweep question" decision above), so a page can have at most one verified
#     row; this constraint is what makes INSERT OR REPLACE below a real idempotency guarantee rather than
#     just a convention.
#   - region_x0/y0/x1/y1 (4 REAL columns, not a nested blob): matches how every other numeric/typed sidecar
#     in this codebase (meas, tbl, parts_rows) stores flat columns, not embedded JSON -- keeps this sidecar
#     queryable with plain SQL, consistent with its siblings.
#   - verified INTEGER NOT NULL DEFAULT 0: always 1 in every row this tool actually writes (only
#     verified=True rows are ever inserted -- see main() below) -- kept as an explicit column rather than
#     assumed because it's part of the design spec's documented data model and lets a future reader of
#     pageqa.db confirm the invariant directly rather than trusting this docstring.
#   - backend/extracted_at: provenance -- which vlm_backend answered, and when; mirrors meas/tbl's own
#     doc/page provenance columns plus the timestamp convention build_measures.py's meas_done.ts already uses.


def _connect_ro(path):
    return sqlite3.connect("file:%s?mode=ro" % path, uri=True)


def _existing_pairs(db_path, table, doc_col, page_col):
    """(doc,page) pairs already present in some other sidecar's table -- used both to exclude pages
    measures.py/tables.py/RPSTL already found something on, and (same helper, pageqa.db itself) to exclude
    pages this tool already verified-and-wrote on an earlier run (see module docstring, idempotency point
    #2). Degrades to an empty set on ANY failure -- sidecar not built yet, corrupt, wrong schema -- never
    raises; a sidecar that doesn't exist yet correctly excludes NOTHING rather than blocking every page."""
    if not os.path.exists(db_path):
        return set()
    try:
        con = _connect_ro(db_path)
        try:
            rows = con.execute("SELECT DISTINCT %s, %s FROM %s" % (doc_col, page_col, table)).fetchall()
            return {(r[0], r[1]) for r in rows}
        finally:
            con.close()
    except Exception:
        return set()


def _candidate_pages(max_pages):
    """Pages where measures.py/tables.py/RPSTL extraction found NOTHING, ocr_confidence>=OCR_CONFIDENCE_FLOOR,
    and not already verified-and-written to pageqa.db from an earlier run -- capped at max_pages. Ordered
    deterministically (document_id, page_number), NOT randomly: same "cheap, reproducible sample, not a
    statistically-random one" reasoning build_dedup.py's own first-N-pages prefix sample already uses --
    re-running with the same or a larger --max-pages makes forward, repeatable progress across the corpus
    (already-verified pages are excluded, so nothing is ever re-asked for no reason)."""
    if max_pages <= 0:
        return []
    if not os.path.exists(DB):
        return []

    have_measures = _existing_pairs(MEASURES_DB, "meas", "doc", "page")
    have_tables = _existing_pairs(TABLES_DB, "tbl", "doc", "page")
    have_rpstl = _existing_pairs(RPSTL_DB, "parts_rows", "doc_id", "page")
    already_done = _existing_pairs(PAGEQA_DB, "pageqa_extractions", "document_id", "page_number")

    con = _connect_ro(DB)
    try:
        # coverage.py's own precedent (overview()'s `scalar()` gate around its ocr_confidence AVG query):
        # on a viewer.db where migration 0009 hasn't run yet, `ocr_confidence` doesn't exist as a column at
        # all and this query raises OperationalError -- that's "nothing scored yet", not a crash, same as
        # coverage.py already treats it (ocr_conf_scored=0 -> avg reported as null, never as a false zero).
        # This tool mirrors that: no scored pages means no eligible candidates this run, reported as an
        # empty list rather than an uncaught exception.
        rows = con.execute(
            "SELECT document_id, page_number FROM pages WHERE ocr_confidence IS NOT NULL "
            "AND ocr_confidence >= ? ORDER BY document_id, page_number", (OCR_CONFIDENCE_FLOOR,)).fetchall()
    except sqlite3.OperationalError:
        rows = []
    finally:
        con.close()

    out = []
    for doc_id, page in rows:
        key = (doc_id, page)
        if key in have_measures or key in have_tables or key in have_rpstl or key in already_done:
            continue
        out.append(key)
        if len(out) >= max_pages:
            break
    return out


def main(max_pages):
    # available() checked BEFORE any model-load attempt or DB touch (design spec's error-handling section;
    # matches build_tables.py's own `if not tables.available(): ...; return 2` for its optional dependency
    # -- see module docstring point #3 for why THIS is the real sibling precedent, not build_dedup.py,
    # which has no optional dependency of its own to gate on).
    if not pageqa.available():
        print("Vision-language backend unavailable -- no GPU-capable backend installed (need "
              "engine/vlm_backend.py's dependencies: transformers + torch) or this machine isn't on the "
              "GPU-capable tier catalog §10.1 needs. Nothing to do -- exiting cleanly. "
              "See docs/SYSTEM-REQUIREMENTS.md.")
        return 2
    if not os.path.exists(DB):
        print("viewer.db not found at", DB)
        return 2

    candidates = _candidate_pages(max_pages)
    print("build_pageqa: %d candidate page(s) (ocr_confidence>=%.1f, no measures/tables/RPSTL hit, not "
          "already verified) -- asking up to --max-pages=%d of them." %
          (len(candidates), OCR_CONFIDENCE_FLOOR, max_pages))
    if not candidates:
        print("Nothing to do (no eligible pages, or --max-pages 0). Exiting cleanly.")
        return 0

    side = sqlite3.connect(PAGEQA_DB)
    side.executescript(SCHEMA)

    asked = verified_n = 0
    t0 = time.time()
    for doc_id, page in candidates:
        asked += 1
        res = pageqa.ask(doc_id, page, DEFAULT_QUESTION, mode="structured", strict=True, db_path=DB)
        if res.get("verified"):
            s = res.get("structured") or {}
            region = res.get("region") or {}
            side.execute(
                "INSERT OR REPLACE INTO pageqa_extractions("
                "document_id,page_number,type,value,value2,unit,"
                "region_x0,region_y0,region_x1,region_y1,source_text,answer_text,verified,backend,extracted_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (doc_id, page, s.get("type"), s.get("value"), s.get("value2"), s.get("unit"),
                 region.get("x0"), region.get("y0"), region.get("x1"), region.get("y1"),
                 res.get("source_text"), res.get("answer_text"), 1, res.get("backend"), time.time()))
            side.commit()
            verified_n += 1
        # Only verified=True rows are EVER written (design spec: "verification ... both must pass, or the
        # row is silently discarded -- never written, never surfaced as 'review' either"). An unverified
        # result is neither persisted nor logged per-page here (would be corpus-scale noise); the run
        # summary below reports the asked/verified totals instead.
        if asked % 10 == 0 or asked == len(candidates):
            print("  %d/%d pages asked (%d verified, %.0fs)" %
                  (asked, len(candidates), verified_n, time.time() - t0), flush=True)

    tot = side.execute("SELECT COUNT(*) FROM pageqa_extractions").fetchone()[0]
    side.close()
    print("DONE: asked %d page(s), %d verified and written this run. Sidecar total: %d row(s) -> %s" %
          (asked, verified_n, tot, PAGEQA_DB))
    print("Read-only on viewer.db/measures.db/tables.db/rpstl.db; append-only sidecar (R1/R6). "
          "masterfile.py's next build can pick these rows up as source='vlm-verified'.")
    return 0


def _cli_int(flag, argv, default=None):
    """Same "--flag N" / "--flag=N" parsing style as build_dedup.py's own _cli_float."""
    for a in argv:
        if a == flag or a.startswith(flag + "="):
            try:
                return int(a.split("=", 1)[1]) if "=" in a else int(argv[argv.index(a) + 1])
            except Exception:
                return default
    return default


def _has_flag(flag, argv):
    return any(a == flag or a.startswith(flag + "=") for a in argv)


if __name__ == "__main__":
    _argv = sys.argv[1:]
    # --max-pages is REQUIRED -- no unbounded default (design spec + plan item 12: this is a budget cap,
    # never an accidental whole-corpus sweep). --max-pages 0 is a valid, accepted value (an explicit dry
    # run: reports the candidate count and writes nothing) -- only a MISSING flag is rejected.
    if not _has_flag("--max-pages", _argv):
        print("Usage: python build_pageqa.py --max-pages N")
        print("  --max-pages is required (budget cap on how many candidate pages this run asks the model")
        print("  about -- no unbounded default). Pass --max-pages 0 for a dry run (reports the candidate")
        print("  count against viewer.db/measures.db/tables.db/rpstl.db and writes nothing).")
        raise SystemExit(2)
    _max_pages = _cli_int("--max-pages", _argv, None)
    if _max_pages is None or _max_pages < 0:
        print("--max-pages must be a non-negative integer")
        raise SystemExit(2)
    raise SystemExit(main(_max_pages))
# END OF FILE
