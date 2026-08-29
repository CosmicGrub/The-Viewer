# Per-Line OCR Confidence Capture — Design Spec

**Status:** approved (brainstorm, lightweight — Tier 1, single well-bounded item); implementation plan to follow —
`docs/superpowers/plans/2026-08-25-per-line-ocr-confidence-plan.md`
**Catalog reference:** `docs/EXTRACTION-METHODS-CATALOG.md` §1.9, "Per-word OCR confidence capture."
**Standing rules in effect:** R1 (additive/rollbackable — `ocr_one()`'s callers all still work unmodified in
shape), R6 (append-only, new sidecar, never touches `pages`/corpus).

## Why / corrected premise

The catalog phrases this as "per-word" (S effort). On inspection, that doesn't match what's actually available:
`ocr_one()`'s own docstring already states RapidOCR returns confidence **per detected line**, not per word —
standard PP-OCR-family behavior (the detection stage groups text into line/phrase boxes; the public API doesn't
expose per-word or per-character confidence). Genuinely per-word would mean reconfiguring RapidOCR's detection
model for word-level boxes, a materially bigger, GPU-hardware-dependent task this environment can't build or
verify (`rapidocr_onnxruntime` isn't installed here — same Advanced/GPU-fork-only posture as every other
RapidOCR-dependent piece of this project).

What ships instead, chosen with the user: capture the **per-line** confidence that RapidOCR already computes
(today it's averaged into one page-wide number and the per-line detail is discarded) and attribute each line's
score down to the words it contains — honest about what it is (line-level measurement, word-level *attribution*,
not independent per-word confidence).

## Non-goals (explicitly deferred)

- True independent per-word/per-character confidence (needs RapidOCR reconfigured for word-level detection —
  a GPU-hardware-dependent follow-on, not this pass).
- Bounding-box geometry for each line (only text + confidence are captured; no visual highlighting consumer
  exists yet to need it — YAGNI, add later if a real consumer needs it).
- Migrating existing consumers (`cautions.py`'s `textquality.annotate()`, `coverage.py`'s aggregate stats) to
  use the new per-line data — they keep reading `pages.ocr_confidence` exactly as before (R1: purely additive).
  A future pass can upgrade `cautions.py` to cite the specific line a caution's text came from instead of the
  whole page's average; not required for this data to exist and be useful.
- Tesseract-fallback per-line capture — Tesseract's confidence isn't exposed the same way today (`conf=None`
  on that path already); out of scope, matches the existing page-level gap.

## Architecture

New sidecar, new capture point in the existing OCR pipeline, zero new routes this round.

- **`engine/ocrconf.py`** (new, thin module — mirrors `dedup.py`/`pageqa.py`'s "own sidecar, own schema"
  pattern). `available()`, `record_lines(db_path, document_id, page_number, lines)` (INSERT OR REPLACE, one row
  per line), `lines_for_page(db_path, document_id, page_number) -> [{"line_index", "text", "confidence"}]`.
  Pure sidecar I/O; no extraction logic lives here.
- **New sidecar `index/ocrconf.db`** — one table, `ocr_lines(document_id INT, page_number INT, line_index INT,
  text TEXT, confidence REAL, PRIMARY KEY(document_id, page_number, line_index))`. Own `CREATE TABLE IF NOT
  EXISTS` init, matching `dedup.db`/`kg.db`/`pageqa.db` — not a `viewer.db` migration.
- **`engine/viewer_ingest.py`** — `ocr_one()`'s return widens from `(text, confidence, barcode)` to `(text,
  confidence, barcode, lines)`, where `lines` is `[(text, score), ...]` from RapidOCR's own per-line results
  (already computed at `res`/`scores` today, just discarded after being averaged into `conf`) or `None` on the
  Tesseract-fallback / blank-skip paths (matches `conf=None`'s existing "no scoring available" signal on those
  same paths). The identical-page dedup cache (`_DEDUP`) widens the same way — a cache hit on a repeated
  boilerplate page must replay its `lines` too, not just `text`/`conf`/`barcode`.
- **`_ocr_task()`** — return tuple widens `(pid, text, conf, barcode, err)` → `(pid, text, conf, barcode, lines,
  err)`. Both call sites (`handle(*_ocr_task(r))`, `handle(*fut.result())`) already splat the tuple — zero
  changes needed there.
- **`ocr()`'s `handle()` callback** — signature widens to accept `lines`; on the success path (`err is None`),
  after the existing `UPDATE pages SET ...` call, writes `lines` to `ocrconf.py` (only when `lines` is truthy)
  using the same `document_id`/`page_number` already resolved from `_labels` a few lines below in that same
  function for the measures.db call.

## Data flow

1. `ocr()` batch-processes a page → `_ocr_task()` → `ocr_one()`.
2. `ocr_one()`'s existing RapidOCR call already has `res` (per-line `[box, text, score]` triples) before
   collapsing to `scores`/`conf`. Additionally builds `lines = [(r[1], round(r[2], 4)) for r in res if len(r) >
   2 and isinstance(r[2], (int, float))]` — same filtering discipline `scores` already uses, just keeping the
   text alongside instead of discarding it.
3. `lines` flows back through `_ocr_task()` → `handle()` unchanged in shape at both call sites.
4. `handle()` still does its existing page-level `UPDATE pages ... ocr_confidence=?` (unchanged — every
   existing consumer of that column keeps working exactly as before), then additionally calls
   `ocrconf.record_lines(ocrconf_db_path, document_id, page_number, lines)` when `lines` is present.
5. Any future consumer reads via `ocrconf.lines_for_page()` and does its own substring/position match against
   the returned lines to find which line (and therefore what confidence) a given word or phrase came from —
   this module stays a thin, generic sidecar; word-position lookup logic belongs to whichever consumer needs
   it, not baked in here (YAGNI until a real second consumer exists).

## Error handling & degradation

Matches this pipeline's existing discipline exactly: `ocrconf.record_lines()` never raises (best-effort, same
posture as every other sidecar writer in `viewer_ingest.py`) — a failure to write per-line data must never
turn a successful page OCR into a failed one; the page-level `UPDATE` (source of truth for `ocr_status`) already
happens first and independently. `ocrconf.available()` lets a future route/consumer check for the sidecar's
existence before querying it, matching `dedup.py`/`pageqa.py`'s existing convention. Tesseract-only environments
(no RapidOCR) simply never populate this sidecar — `lines_for_page()` returns `[]`, not an error.

## Testing

- **`engine/ocrconf.py` self-test** (`__main__`, matching this project's per-module convention): round-trips
  `record_lines()`/`lines_for_page()` against a temp sidecar; confirms `available()` is `False` before any
  write and `True` after; confirms `INSERT OR REPLACE` semantics (re-recording the same page's lines replaces,
  not duplicates).
- **Extend `engine/tests/test_ingest_routes.py`** (or a new `test_ocrconf.py`, matching however similarly-sized
  sidecar tests are structured elsewhere) — real e2e: OCR a real tiny fixture PDF with a mocked RapidOCR
  backend returning known multi-line results, confirm the sidecar ends up with one row per line, correct
  text/confidence, correctly keyed to document/page. Separately: confirm the identical-page dedup cache replays
  `lines` correctly on a cache-hit (a repeated boilerplate page must not silently lose its per-line data).
- **CI-safety**: this only ever runs down the RapidOCR path, which CI already doesn't have installed
  (`_have_rapid()` is `False` there) — the test above must mock the RapidOCR call the same way existing
  ingest tests already do, not require the real dependency.

## Open items for the implementation plan (not design-blocking)

- Exact `ocrconf.py` module name/location (proposed above, could instead live inside `viewer_ingest.py` itself
  if that turns out cleaner — implementation detail).
- Whether a future `/api/ocrconf` read route or a UI affordance (e.g. a per-line confidence heatmap on the
  page viewer) ever gets built — explicitly out of scope for this pass; this spec only covers capture +
  storage + a generic read function.
