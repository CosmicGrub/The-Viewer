# Search Click Instrumentation + Heuristic Re-Rank — Implementation Plan

**Spec:** `docs/superpowers/specs/2026-08-25-search-click-instrumentation-and-heuristic-rerank-design.md`
**Status:** planned, not started

No "writing-plans" skill is available in this environment (confirmed absent when the same gap was hit on the
VLM feature) — written directly, following this project's own established conventions.

## Sequencing rationale

One phase, one PR — the spec's Approach 1. The two halves are small and the ranking half is provably inert
with zero click data (empty set → no-op sort key → identical output to today), so there is no real dependency
risk to hedge against by splitting into two PRs; splitting would only add review overhead. Steps below are
ordered so each one is independently checkable as it lands, even though they ship together.

---

## Steps

1. **`engine/analytics.py`**
   - Add `"click"` to `_VALID`.
   - `log()`'s `extra` allowlist: `("doc", "page", "nsn")` → `("doc", "page", "nsn", "rank")`. `rank` stored as
     `str(int(...))` if present and coercible, silently dropped (not error-raised) if not — matches this
     function's existing "never raises, best-effort" contract for every other field.
   - New function `clicked_pages(index_dir) -> set[str]`: reads all `"click"` events via the existing `_read()`
     helper, builds `{f"{r['doc']}:{r['page']}" for r in rows if r.get('doc') and r.get('page')}`, cached 60s —
     copy `parts_feature.popular_nsns()`'s `_POP_CACHE`-style module-level cache dict pattern verbatim (same
     TTL, same shape), named distinctly (e.g. `_CLICK_CACHE`) so the two caches never collide.
   - Extend the `__main__` self-test: log a few `"click"` events (including one with no `rank`, one with a
     non-numeric `rank` to prove it's dropped, not fatal), assert `clicked_pages()` returns the right key set,
     assert it returns `set()` against an empty/missing dir.

2. **`engine/features/search_feature.py`**
   - Add `import analytics` near the top (local import, matching `routes/search.py`'s existing pattern of
     importing `analytics` at call-site rather than module scope, to avoid import-order/circular-import risk
     with whatever already imports `search_feature`).
   - Immediately after the existing `pop = core.popular_nsns(con)` / `boosted` block (around line 599-602): call
     `clicked = analytics.clicked_pages(core.INDEX_DIR)`, then tag
     `r["clicked"] = True` for rows where `f"{r.get('doc_id')}:{r.get('page_number')}"` is in `clicked` —
     mirror the existing `boosted` loop's structure exactly (same guard style, same "only set when true" — never
     set `r["clicked"] = False`, matching how `exact`/`approx`/`boosted` are only ever added, never explicitly
     falsed, elsewhere in this same function).
   - Extend the sort key at line 603 from
     `(0 if r.get("exact") else 1, 1 if r.get("approx") else 0, 0 if r.get("boosted") else 1)` to add a fourth
     element `0 if r.get("clicked") else 1`.

3. **`engine/ui/index.html`**
   - In `renderList()`'s row-build loop, after the existing badge list (`vbadge`/`fav`/`ty`/`tm`/`nsn`/`pg`/
     `ocr`/`approx`), add a `clicked` badge conditioned on `r.clicked`, styled/sized like the existing `.fav`
     badge (`★ requested`) — new class e.g. `.opened`, label `↺ opened before`, with a `title` attribute
     explaining the source ("Opened from a search result before") so it never reads as unexplained authority
     (R13).
   - In the same function's `d.onclick=()=>openViewer(r);` line (and the `.vbtn` button's click handler, which
     calls the same `openViewer(r)`): before calling `openViewer(r)`, fire the beacon —
     `try{ var _rk=shown.indexOf(r); window.fetch("/api/analytics_log",{method:"POST",
     headers:{"Content-Type":"application/json"}, body:JSON.stringify({kind:"click", key:(LAST_QUERY||q||""),
     doc:r.doc_id, page:r.page_number, rank:(_rk>=0?_rk:null)})}); }catch(_){}` — wrapped exactly like the
     existing beacon in `palette.js`, fire-and-forget, never awaited, never blocks navigation.
   - Confirm `shown` (the array `renderList(shown)` is called with) is in scope / passed through to where the
     click handlers are attached — if `renderList(rows)`'s parameter name shadows the outer `shown`, use
     `rows.indexOf(r)` instead (the array actually being rendered) so rank always matches what's on screen.

4. **Tests**
   - `engine/analytics.py` — self-test extended per step 1.
   - `engine/tests/test_search_quality.py`:
     - Extend the existing `/api/analytics_log` → `/api/analytics_top` round-trip block with a `kind:"click"`
       case carrying `rank`, confirming it logs and round-trips (`ok:true`, appears in `by_kind`).
     - New case: seed `V.INDEX_DIR`'s `analytics.jsonl` directly (isolated fixture dir, same pattern already
       used in that file) with a `"click"` event for a specific `(doc, page)` that's a real hit for some fixture
       query; run that query through `/api/search`; assert the clicked row now sorts ahead of an otherwise-equal
       unclicked row that matches the same query. This is the actual regression test for the new sort key, not
       just a schema round-trip.
   - `engine/tests/test_routes.py` — no new route; confirm the existing blanket sweep still passes with the
     widened `_VALID`/allowlist (should require no changes, just re-run as a checkpoint).
   - `engine/tools/rps_lint.py` pass on `index.html` (touched UI file, matches this project's existing habit of
     lint-checking any touched `.html`/`.js`).

5. **Docs**
   - `docs/CHANGELOG.md` — new entry (version bump), following this file's established dense/specific voice:
     what shipped, why (the corrected-premise framing from the spec's "Why" section), what's explicitly
     deferred (query-aware weighting, decay, the actual learned model).
   - `docs/HANDOFF-NOTE.md` / `docs/PROJECT-SUMMARY.md` / `docs/MASTER-RECONCILIATION.md` — update the Tier-2
     "learned search re-ranker" line to reflect "Phase 1 (instrumentation + heuristic) shipped; learned model
     still open, now has real data to train on."
   - `docs/ITERATION-SNAPSHOTS.md` / `docs/ITERATION-DASHBOARD.html` — regenerate via
     `python engine/build_iteration_snapshot.py` after the CHANGELOG entry lands (never hand-edited).

6. **Verify**
   - `python -m py_compile` on every touched `.py` file.
   - Direct reproduction of the new regression test locally (not just "tests pass" — actually confirm the
     clicked row's position changes when the seeded event is present vs. absent, same discipline used for the
     hallucination-bypass fix earlier this project).
   - `engine/tests/verify_all.py --snapshot` green, full output inspected (not just exit code), before opening
     the PR.
   - `engine/tools/check_crlf.py` — no new `.bat` file this time, but run it anyway as a cheap checkpoint since
     `index.html` line endings have occasionally drifted in this repo before.

## Open decisions carried from the spec (resolve during implementation, not blocking)

Exact badge wording/icon, whether `clicked_pages()`'s cache key should be process-global or per-`INDEX_DIR`
(matters only if this app is ever pointed at multiple index dirs in one process — `popular_nsns()`'s existing
cache is already process-global/single-dir, so matching that precedent is the default unless implementation
reveals a concrete problem), and the `/api/searchclicks` read-only visibility endpoint mentioned as a future
nice-to-have in the spec — not built this round.
