# Multi-Column Reading-Order Reconstruction — Design Spec

**Status:** approved (brainstorm, lightweight — Tier 1, single well-bounded item); implementation plan to
follow — `docs/superpowers/plans/2026-08-25-layout-reading-order-plan.md`
**Catalog reference:** `docs/EXTRACTION-METHODS-CATALOG.md` §2.5, "Reading-order reconstruction (multi-column
TMs)."
**Standing rules in effect:** R1 (additive/rollbackable), R6 (read-only on the corpus — this only touches
`layout.py`'s in-memory block ordering, never `pages.body_text` or any indexed/persisted data).

## Why / scope check (this one holds up, unlike the last two)

Verified directly before designing (the same check that corrected the re-ranker and OCR-confidence pitches):
`engine/layout.py:76` really does sort blocks with a flat `key=lambda r: (r["bbox"][1], r["bbox"][0])` —
top-to-bottom, left-to-right on raw coordinates, no column awareness. On a genuine 2-column page this
interleaves the two columns line-by-line instead of reading one column fully before the next — exactly the
"scrambled order" the catalog describes. The module's own self-test never exercises this: every fixture block
is inserted at the same `x=40`, so a single-column layout is the only case ever tested.

Also verified: `layout.py` has exactly one consumer, `doc_extractors.py`'s `/api/layout` route (a local
`import layout`, checked via a repo-wide grep — nothing else imports it, nothing persists its output). This
makes the fix fully isolated: it changes what `/api/layout` returns, never `pages.body_text`, never search
indexing, never any extraction pipeline that already runs corpus-wide. No re-processing of the existing
corpus is needed for this to take effect, and there is no corpus-frequency judgment call the way the
measures.py unlabeled-unit gap has — this is a deterministic geometry algorithm, testable entirely with
synthetic fixture PDFs.

**Explicitly out of scope for this pass** (a materially different, much bigger, corpus-wide risk class):
reordering the actual text `pages.body_text` is built from (both the native-PDF `get_text("text")` path and
the OCR path) — that would need re-processing the whole corpus and real-corpus validation that extraction/
search behavior doesn't regress, the same category of risk that made the measures.py unlabeled-unit gap a
Tier-3/blocked item. `layout.py`'s reading order is a presentation-layer concern only; fixing it is safe
precisely because nothing depends on it yet.

## Approach

A single-level column split, not full recursive XY-cut — deliberately scoped to this corpus's actual layouts
(Army TM pages are either single-column body text, or a simple 2-column layout with full-width headers/
footers/titles/section headings; not complex multi-region magazine layouts a deeper recursive cut would be
needed for). If a future page shape needs more than one cut level, this can be revisited additively.

1. **Classify each block as full-width or narrow.** A block whose bbox spans more than ~65% of the page's
   own content width (the union of all non-header/footer block x-ranges — not the raw page width, so margins
   don't skew the threshold) is full-width: titles, section headings, running headers/footers, and any
   full-width table or figure. Everything else is narrow (candidate column content).
2. **Detect a genuine 2-column split among the narrow blocks.** Look for a vertical gap in x-coverage wide
   enough (a real gutter, not two blocks that just happen not to touch) that a clear majority of narrow
   blocks fall entirely on one side or the other. A weak/ambiguous split (few blocks, no real gap, or most
   blocks straddling the gap) means "this isn't actually 2-column" — fall back to today's exact behavior
   (plain `(y, x)` sort), so a single-column page is never affected and never misdetected into fake columns.
3. **Reading order when a real split is found**: walk the page top-to-bottom in bands delimited by full-width
   blocks (each full-width block sits in the sequence exactly where its own y-position puts it, unaffected by
   column logic). Within each band between two such delimiters (or from the top of the page / bottom of the
   page to the nearest one), every narrow block in the LEFT column sorts before every narrow block in the
   RIGHT column, each column internally still ordered top-to-bottom. This is the actual "read the whole left
   column, then the whole right column" fix — the flat sort silently produces the interleaved wrong order today.

## Data model

None — `analyze()`'s return shape (`[{type, bbox, text, size}]`) is unchanged; only the *order* of that list
changes for genuinely multi-column pages. No new fields, no new sidecar, no schema of any kind.

## Error handling & degradation

Matches `layout.py`'s existing posture exactly: the whole function already degrades to `[]` on any exception
(`except Exception: return out`) or when `fitz`/the PDF path is unavailable. The new column-detection logic is
itself just plain-Python geometry over an in-memory list already built by the existing code — nothing new can
raise that the existing `try/except` doesn't already catch. A page where column detection is ambiguous or
ends up wrong in an edge case degrades to the current flat sort, never a crash, never a hang.

## Testing

- **`layout.py`'s own `__main__` self-test** (existing convention) — extend with a genuine 2-column fixture:
  a full-width header, a full-width title, two columns of paragraph blocks (left column's y-range overlapping
  the right column's, the exact shape that breaks a flat sort), a full-width footer. Assert the returned
  order is header → title → every left-column block (in order) → every right-column block (in order) →
  footer — not interleaved. Keep the existing single-column fixture/assertions unchanged (regression
  coverage: a single-column page's order must be byte-identical to before this change).
- **A second synthetic case**: a page with narrow blocks that do NOT form a real 2-column layout (e.g., a
  handful of short captions scattered around a mostly single-column page) — assert the fallback flat sort is
  used, not a misdetected fake column split.
- **Extend whatever test file already exercises `/api/layout`** (find it first, don't assume it doesn't
  exist) with the same multi-column assertion through the real route, not just the module function directly.

## Open items for the implementation plan (not design-blocking)

- Exact numeric thresholds (the "65% full-width" cutoff, the minimum gutter width, the minimum block-count/
  majority-fraction for "this is really 2 columns") — tuned during implementation against the synthetic
  fixtures above; the *existence* and *shape* of these thresholds is the design decision, not their exact
  values.
- Whether a 3+ column layout is worth detecting — not seen as a real TM page shape in this project's own
  document set per the catalog's own framing ("multi-column TMs," not general documents); deferred unless a
  real example surfaces.
