# Multi-Column Reading-Order Reconstruction — Implementation Plan

**Spec:** `docs/superpowers/specs/2026-08-25-layout-reading-order-design.md`
**Status:** planned, not started

No "writing-plans" skill available in this environment — written directly, following this project's own
established conventions.

## Sequencing rationale

One phase, one PR. Fully isolated (single consumer, `/api/layout`, confirmed via a repo-wide grep before this
plan was written), no corpus/index touched, no new data model — the whole change lives inside `layout.py`'s
existing `analyze()` function plus its own test coverage.

## Steps

1. **`engine/layout.py`** — after the existing per-block classification loop (which stays completely
   unchanged) and before the final `return out`, replace the flat `out.sort(...)` with the column-aware
   ordering from the spec:
   - Classify each block as full-width vs. narrow using the page's own content-width union (not raw page
     width) as the spec describes.
   - Detect a genuine 2-column split among narrow blocks (real gutter + a clear majority on one side or the
     other) — anything weaker falls back to exactly today's `(y, x)` flat sort, unchanged output for every
     single-column page.
   - When a real split is found: band the page by full-width blocks' y-positions, and within each band sort
     all left-column narrow blocks (by y) before all right-column narrow blocks (by y).
   - Keep this as a small number of well-named local helper functions/lambdas inside or alongside `analyze()`
     — match this module's existing plain, dependency-free style (no new imports; `statistics` is already
     used, nothing else should be needed).

2. **`layout.py`'s `__main__` self-test** — keep the existing single-column fixture/assertions completely
   unchanged (regression coverage: byte-identical order for a single-column page). Add:
   - A genuine 2-column fixture (full-width header + title, two columns of paragraph blocks with overlapping
     y-ranges, full-width footer) asserting the exact order described in the spec's Testing section.
   - A "narrow blocks that don't actually form 2 columns" fixture (e.g., a couple of small captions scattered
     around an otherwise single-column page) asserting the fallback flat sort is used, not a false-positive
     column split.

3. **Route-level coverage** — a repo-wide check found no existing test file exercises `/api/layout` at all
   (not even a blanket-sweep 200-check in `test_routes.py`). Confirm this is really true by re-checking
   directly (don't just trust this plan's own claim), then either extend `test_routes.py`'s existing route
   sweep to include `/api/layout` (if that sweep is a manually-enumerated list route-by-route) or add a
   small, focused test exercising the real route end-to-end against a 2-column fixture PDF, matching whatever
   pattern `test_routes.py`/other route tests already use for a route with real assertions (not just a
   blanket 200-check).

4. **Docs** — `CHANGELOG.md` entry (dense/specific voice, matching this project's established style,
   including the "why this is safe/isolated" framing from the spec's "Why" section); `docs/
   EXTRACTION-METHODS-CATALOG.md` §2.5 status `○` → `✅` with an updated Approach/library cell describing the
   single-level column-split heuristic (not full recursive XY-cut, and why that's the right scope for this
   corpus's actual page shapes).

5. **Verify**: `python -m py_compile engine/layout.py`; run `layout.py`'s own self-test directly; run
   whatever new/extended route test directly; full `engine/tests/verify_all.py --snapshot`, output inspected
   directly, before opening the PR. Since `layout.py` has exactly one consumer and no other module imports
   it, no other existing test file should be affected — confirm this is genuinely true (grep again after the
   change, don't assume the pre-plan grep is still accurate) rather than skipping the check.

## Open decisions carried from the spec (resolve during implementation, not blocking)

Exact numeric thresholds (full-width cutoff fraction, minimum gutter width, minimum majority fraction for a
"real" column split) — tune against the synthetic fixtures built in step 2, not guessed in advance.
