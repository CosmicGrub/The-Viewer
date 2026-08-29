# Search Click Instrumentation + Heuristic Re-Rank — Design Spec

**Status:** approved (brainstorm); implementation plan to follow —
`docs/superpowers/plans/2026-08-25-search-click-instrumentation-and-heuristic-rerank-plan.md`
**Roadmap reference:** Tier 2, "learned search re-ranker" — this design is the deliberately-scoped Phase 1 of
that item (instrument + modest heuristic), not the learned model itself. See "Why / corrected premise" below.
**Standing rules in effect:** R1 (additive/rollbackable), R6 (append-only, never touches the corpus or existing
sidecars), R13 (a ranking signal must never pass as unexplained authority — if a result floats, the UI says why).

## Why / corrected premise

The original pitch for a "learned search re-ranker" assumed real training data already existed in
`engine/analytics.py`'s event log. On inspection, that was wrong: `analytics.gaps()` only captures **zero-result**
queries — a pure failure list. Nothing in the codebase records which result (by rank) a user actually opened for
a query that *did* return results, so there is no click-through / relevance signal anywhere to learn from. Rather
than build a "learned" re-ranker on top of a made-up signal, this design does two honest things instead:

1. **Instrument real engagement now** — start logging which result gets opened, at what rank, for what query —
   so a genuinely learned re-ranker has real data to train on in a later session.
2. **Ship a modest, hand-tuned ranking improvement now** — extend the existing keyword-search stable sort with
   one more explicit, well-precedented signal, so something concrete improves this round too.

A secondary correction made during design: the main search UI (`engine/ui/index.html`) calls `/api/search`
(`search_feature.search()`, plain FTS + an existing `exact`/`approx`/`boosted` stable sort), **not**
`/api/search_hybrid` (`hybrid.py`'s RRF `fuse()`). `hybrid.py` is a secondary endpoint nothing in the primary UI
calls. The heuristic improvement therefore targets `search_feature.py`'s sort, not `hybrid.py`.

## Non-goals (explicitly deferred, not blocking this design)

- Query-similarity-aware click weighting (only floating a result for the *same* query it was clicked from) —
  deferred; this design uses global per-doc/page click popularity only, mirroring the existing `boosted`
  (`popular_nsns`) precedent exactly. The query-aware version is most of what the deferred learned re-ranker
  would need to do anyway.
- Click recency decay or minimum-click thresholds — `boosted` has neither (any prior part request counts,
  ever); `clicked` matches that precedent for consistency, not because decay is a bad idea later.
- Click-fraud / bot / rapid-repeat-click filtering — this is a single-operator-machine offline tool (R6-style
  trust model already assumes a non-adversarial local user); not a design concern here.
- Wiring this signal into `hybrid.py`'s `fuse()` / `/api/search_hybrid` — out of scope since nothing in the
  shipped UI calls that endpoint today; revisit only if that endpoint gets a real consumer.
- The actual learned re-ranker (a model trained on the accumulated click log) — this design produces the data
  and ships a stopgap; training and deploying a learned model is future Tier-2 work, gated on having enough
  real click volume to be worth it.

## Architecture

No new modules. Both halves extend existing files along existing seams:

- **`engine/analytics.py`** (extended) — new event kind `"click"` added to `_VALID`; `log()`'s `extra` allowlist
  grows from `{doc, page, nsn}` to include `rank` (int, clamped, optional). New function `clicked_pages(index_dir)`
  → a `{"doc_id:page_number"}` string-key set built from every `"click"` event ever logged, cached 60s — the
  same shape and TTL-cache pattern `features/parts_feature.py`'s `popular_nsns()` already uses, just reading
  `analytics.jsonl` instead of the `request_items` SQL table.
- **`engine/ui/index.html`** (extended) — `renderList()`'s existing `d.onclick=()=>openViewer(r)` handler (the
  one place a search result is actually opened) gains one `fetch("/api/analytics_log", ...)` beacon call,
  firing before navigation, using the row's index in the currently-rendered `shown` list as `rank`. No new
  route: `POST /api/analytics_log` already exists and is already called this way from `palette.js` for other
  event kinds.
- **`engine/features/search_feature.py`** (extended) — `search()` already calls `core.popular_nsns(con)`
  immediately before its stable sort at line 603 (`core` here is the injected `viewer_app` module, which
  re-exports `popular_nsns` from `parts_feature` via its own top-level import — `search_feature.py` never
  imports `parts_feature` directly). The new call does **not** chain through that same re-export path; it's
  simpler and matches this file's own existing style (`routes/search.py` already does a local `import
  analytics` before calling it) to add `import analytics` directly in `search_feature.py` and call
  `analytics.clicked_pages(core.INDEX_DIR)` — `core.INDEX_DIR` is already used the same way elsewhere in this
  codebase (e.g. `routes/search.py`'s gap-log call). Matching rows get tagged `r["clicked"] = True`. The sort
  tuple grows one key:
  `(exact, approx, boosted, clicked)` — same shape, same stable-sort discipline, one more tier.
- **`engine/ui/index.html`** `renderList()` (same file as above, different concern) — a small badge, parallel
  to the existing `★ requested` badge, added next to it: e.g. `↺ opened before`, shown when `r.clicked` is set.
  Keeps R13's "never let a ranking signal pass as unexplained authority" honest for this new tier too.

## Data model

**No new sidecar, no new table.** `"click"` events reuse the existing append-only `index/analytics.jsonl` (R6:
same file, no new writer surface). One new record shape, following the file's existing `{t, k, q, doc?, page?,
nsn?}` convention:

```
{"t": 1756... , "k": "click", "q": "alternator bracket torque", "doc": "5", "page": "40", "rank": 2}
```

`rank` is 0-indexed (matches the row's position in the rendered list — "the first result" is `rank: 0`), clamped
the same way `analytics.log()` already clamps `key` to 160 chars and `doc`/`page`/`nsn` to 40 — bounding
malformed/adversarial-length input from ever reaching the sidecar, consistent with the file's existing
defensive posture (never raises, best-effort, silently drops what it can't validate).

`clicked_pages()`'s return shape is a plain `set[str]` of `"doc_id:page_number"` keys — deliberately not a dict
or a count, matching `popular_nsns()`'s own return shape (`set[str]` of NSNs) so `search_feature.py`'s two calls
read as parallel, not bespoke.

## Data flow

### A — Instrumentation (write path)

1. User runs a search in `index.html`; `renderList()` renders `shown` (the filtered, already-ranked results)
   into `#rlist`, one `<div class="result">` per row, in order.
2. User clicks a result (or its "View page" button — both already route through the same `openViewer(r)` call).
3. Before `openViewer(r)` navigates, a fire-and-forget beacon fires:
   `fetch("/api/analytics_log", {method:"POST", body: JSON.stringify({kind:"click", key:LAST_QUERY,
   doc:r.doc_id, page:r.page_number, rank:<index in shown>})})` — matching the existing beacon style already
   in this file (best-effort, wrapped in try/catch, never blocks the click it's attached to).
4. `r_analytics_log()` (`features/routes/search.py`, unchanged route, already generic over `kind`) calls
   `analytics.log(core.INDEX_DIR, "click", key, {doc, page, rank})` — the existing route needs no changes at
   all; only `analytics.py`'s `_VALID` set and `extra` allowlist grow to accept the new kind/field.
5. The event lands in `analytics.jsonl` exactly like every other kind, append-only, one line, best-effort.

### B — Heuristic re-rank (read path)

1. A search request hits `search_feature.search()`.
2. Immediately after the existing `pop = core.popular_nsns(con)` / `boosted` block, a parallel block calls
   `analytics.clicked_pages(core.INDEX_DIR)` and tags `r["clicked"] = True` for any row whose
   `f"{doc_id}:{page_number}"` is in that set.
3. The existing stable sort gains the fourth key. Rows that are exact matches still win outright; among
   otherwise-equal rows, one that's been opened from a search before now edges above one that hasn't — same
   spirit as `boosted`, just fed by a different (browsing, not requesting) success signal.
4. `renderList()` shows the `↺ opened before` badge on any row carrying `r.clicked`.

With zero click history (a fresh index, or before this change had time to accumulate any data), step 2 returns
an empty set, step 3's fourth sort key is a no-op for every row, and ranking is byte-for-byte identical to
today's behavior — the ranking half is inert until the instrumentation half has actually produced data, by
construction, not by any special-cased guard.

## Error handling & degradation

Both halves follow this codebase's established analytics posture exactly: `analytics.log()` never raises
(already true, unchanged); `clicked_pages()` is a new read path with the same discipline —
`try/except sqlite3.OperationalError` isn\'t relevant here (it reads a JSONL file, not SQL) but it reuses
`analytics._read()`'s existing `try/except Exception: pass` wrapping, so a missing or corrupt `analytics.jsonl`
degrades to an empty set, never a crash, never a broken search response. The client-side beacon is wrapped in
the same `try{...}catch(_){}` pattern every other beacon in `index.html`/`palette.js` already uses — a blocked
`fetch` (e.g. a strict CSP in some future embedding context) can never break the actual navigation it's attached
to.

## Testing

- **`engine/analytics.py` self-test** (`__main__`, existing convention) — extend with `clicked_pages()`
  coverage: log a few `"click"` events, assert the returned set contains the expected `"doc:page"` keys and
  excludes events for other kinds; assert an unset/missing `analytics.jsonl` returns an empty set, not an
  error.
- **`engine/tests/test_search_quality.py`** — extend the existing `/api/analytics_log` → `/api/analytics_top`
  round-trip section (the one that already guards against schema drift between the writer and readers) with a
  `kind:"click"` case, confirming `rank` round-trips. Separately, a new case: pre-seed `V.INDEX_DIR`'s
  `analytics.jsonl` with a synthetic click event for a specific `(doc, page)`, run a query where that row and
  an otherwise-equal unclicked row both match, and assert the clicked one now sorts first — a direct,
  reproducible regression test for the new sort key, not just a schema check.
- **`engine/tests/test_routes.py`** — no new route to add to the blanket sweep (both endpoints already exist
  and are already covered); confirm the existing `/api/analytics_log` coverage still passes with the widened
  `_VALID`/allowlist.

## Open items for the implementation plan (not design-blocking)

- Exact wording/icon for the `↺ opened before` badge — cosmetic, not architectural.
- Whether `clicked_pages()` lives in `analytics.py` (recommended — co-located with the log it reads) or
  `search_feature.py` (rejected in favor of the former, for the same reason `popular_nsns()` lives in
  `parts_feature.py` next to `request_items` rather than in `search_feature.py`).
- Whether a future pass adds a `/api/searchclicks` read-only endpoint (mirroring `/api/searchgaps`) for
  visibility into the accumulating click log before a learned re-ranker is built — not needed for this design
  to be useful, purely a nice-to-have for later inspection.
