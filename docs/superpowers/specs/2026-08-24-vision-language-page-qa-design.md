# Vision-Language Page QA — Design Spec

**Status:** approved (brainstorm); implementation plan written —
`docs/superpowers/plans/2026-08-24-vision-language-page-qa-plan.md`
**Catalog reference:** `docs/EXTRACTION-METHODS-CATALOG.md` §10.1 (vision-language document QA) + §3.12 (local-LLM
structured extraction) — this design explicitly subsumes both into one system, since the batch consumer needs
structured output either way.
**Standing rules in effect:** R1 (additive/rollbackable), R6 (append-only, never touches the corpus or existing
sidecars), R13 (extractive+cited, fail loud, an AI tier must never visually pass as authoritative).

## Why

The extraction-methods catalog itself flags §10.1 as the single highest-ceiling item on the whole list: every
other extractor (`measures.py`, `tables.py`, RPSTL, etc.) is a regex/geometry pipeline that can only find what
it was specifically built to look for. A vision-language model can be asked a page directly — "what's the
torque value here?" — and answer questions no existing extractor covers. The existing `engine/vlm.py` already
has the pluggable interface (`ask(image, question) -> str`) but ships with **no backend**, no structured output,
no grounding, and no integration into the app's trust vocabulary — it's an unused stub. This design completes
it into a real, two-consumer system.

## Non-goals (explicitly deferred, not blocking this design)

- Exact prompt-template wording for each extraction type (torque/length/etc.) — an implementation detail, not
  an architectural one.
- Exact Florence-2 quantization/precision level — a tuning decision made against real hardware during
  implementation, not a design fork.
- The exact fuzzy-match parameters for the OCR cross-check (edit distance threshold, etc.) — implementation
  detail; the *existence* of the check is the design decision, not its tuning.
- Visual polish of the "Ask this page" control beyond the wired mockup already reviewed — cosmetic, not
  architectural.
- Upgrading to a two-model split (a larger conversational model alongside Florence-2) — explicitly deferred to
  a later iteration per the approach discussion; nothing in this design blocks it.

## Architecture

Two new modules layer on top of the existing pluggable interface — nothing about `vlm.py`'s current contract
is removed, only widened:

- **`engine/vlm.py`** (extended). `ask()`'s return contract widens: a backend may return either a bare string
  (today's shape — stays fully backward-compatible with the existing `/api/vlm` route) or a
  `{"text": ..., "region": {...}}` dict for backends that support native grounding. A backend that can't ground
  simply omits `region`; callers must treat it as optional, never assume its presence.
- **`engine/pageqa.py`** (new). The shared core. Single entry point:

  ```
  ask(doc_id, page, question, mode="text"|"structured", strict=False) -> {
      available, answer_text, structured?, region?, trust_tier, verified, backend, note
  }
  ```

  Both consumers call this — neither the interactive route nor the batch tool reimplements trust-tier logic
  or verification. This mirrors how `cautions.py`/`_parse_procedure()` already share `textquality.annotate()`
  rather than each computing quality independently.
- **`engine/vlm_backend.py`** (new — the real shipped default, not just an interface). The actual Florence-2
  integration: lazy model load (never loaded until first real call — matches `embed.py`'s lazy-load
  convention), grounded-task prompting (Florence-2's `<CAPTION_TO_PHRASE_GROUNDING>`-style task vocabulary),
  response parsing into the shape `vlm.py`/`pageqa.py` expect. Advanced/GPU-fork-only optional dependency,
  same posture as RapidOCR-on-`onnxruntime-gpu` — the Lite/portable fork never needs to load it.
- **`engine/build_pageqa.py`** + **`BUILD-PAGEQA.bat`** (new). The batch tool, structurally identical to
  `build_dedup.py`/`DEDUP.bat`: a real host-run driver, not an ingest-time stage.

## Data model

Structured output reuses `measures.py`'s existing row shape (`type`/`value`/`value2`/`unit`) rather than
inventing a parallel one — this is the decision that makes the batch path actually useful to `masterfile.py`,
which already knows how to aggregate that shape from every other extractor.

```
{
  "type": "torque",              # same taxonomy measures.py already uses -- no new vocabulary
  "value": "35", "value2": null, # matches measures.py's range shape
  "unit": "N·m",
  "region": {"x0":0.27,"y0":0.44,"x1":0.56,"y1":0.60},   # normalized 0-1, the model's grounding claim
  "source_text": "Install alternator bracket ... torque bolts to 35 N·m",  # the model's claimed page content
  "answer_text": "Alternator bracket bolts torque to 35 N·m (26 ft-lb).",  # free-text, for display
  "verified": true,              # meaningful only when strict=True; false/absent for interactive calls
  "backend": "vlm_backend"
}
```

**New sidecar: `index/pageqa.db`** — its own database (R1/R6: never touches the corpus, never touches any
existing sidecar). One table, `pageqa_extractions`, shaped like the fields above plus `document_id`,
`page_number`, `extracted_at`. `masterfile.py`'s `build()` gains this as one more corroborating source
alongside `measures.db`/`tables.db`, tagged `source='vlm-verified'` — the same distinguishable-provenance
pattern barcode-decoded NSN rows already use (`confidence='barcode'`) in the `parts` table, so an operator can
always tell which pipeline produced a given value.

No new migration to `viewer.db` (next would be `0013_*.sql`) is needed — `pageqa.db` is a standalone sidecar
with its own `CREATE TABLE IF NOT EXISTS` schema-init, matching `dedup.db`/`kg.db`/`masterfile.db`'s existing
pattern, not the `viewer.db` migration pattern.

## Data flow

### Interactive consumer (soft ceiling, ephemeral, no writes)

Two entry points into the same core, per the earlier UI-surface decision:

1. **Page-viewer control** — `engine/ui/deepzoom.html` gains a floating "🔎 Ask this page" control (same
   pattern that page already uses for the Editions/Symbols buttons added earlier this project). Calls
   `pageqa.ask(doc, page, question, mode="text", strict=False)`.
2. **`/ask` fallback** — `engine/ui/ask.html` / `engine/ask.py`'s existing retrieve-then-answer flow falls
   through to `pageqa.ask()` on the top retrieved page when its own extractive sentence-scoring finds nothing.

Either way: Florence-2 returns `{text, region}` → trust is **hard-capped at "review"** regardless of anything
else (no verification run — a human is looking at the actual page right there) → the region renders as a
highlight box on the page image, the answer shows with the review badge (`trust.py`'s existing amber
"check" tier — no new badge vocabulary) and a disclaimer ("AI-read — verify on page," mirroring the AI-3D
model's non-authoritative framing) → **nothing is persisted**, matching `ask.py`'s existing answer-and-forget
contract.

### Automatic consumer (hard verification, batch, persists to the sidecar)

1. Operator runs `BUILD-PAGEQA.bat` (wraps `python build_pageqa.py --max-pages N`), same invocation shape as
   `DEDUP.bat`. Never runs automatically during ingest.
2. The tool samples pages where `measures.py`/`tables.py`/RPSTL extraction found nothing, **excluding** pages
   below `coverage.py`'s existing low-confidence threshold (`ocr_confidence < 0.5`) — a page too garbled for a
   human to read is also not worth asking the model; reusing this threshold rather than inventing a new one.
3. Each sampled page: `pageqa.ask(doc, page, question=<template per field type>, mode="structured",
   strict=True)`.
4. Verification (both must pass, or the row is silently discarded — never written, never surfaced as "review"
   either):
   - **Self-grounding** — a second Florence-2 call asks the model to ground its own claimed `source_text` back
     onto the image; an empty/low-confidence detection is treated as a real hallucination signal.
   - **OCR cross-check** — the claimed region is compared against that page's own already-trusted stored OCR
     text via fuzzy substring match — independent of the model's self-consistency, checked against
     ground truth already in the DB rather than the model's own say-so.
5. Only `verified=True` rows are written to `pageqa.db`, tagged `source='vlm-verified'`.
6. The next `masterfile.py` rebuild picks these rows up as an additional corroborating source automatically —
   no changes needed to `masterfile.py`'s consumer side beyond adding `pageqa.db` to its source list.

## Error handling & degradation

Follows `vlm.py`'s existing contract exactly: never raises, always returns a dict carrying `available`/`note`.
`pageqa.available()` is checked **before** any model-load attempt and returns `False` immediately on lite/legacy
RPS tier or when no GPU is present — the UI hides "Ask this page" entirely in that case (same pattern other
GPU-tier-only features already use to gate their own visibility, e.g. RPS Premium). This matters concretely
for CI: this repo's CI runners have neither a GPU nor downloaded model weights, and the CI-hardening work
earlier this same session (installing `tesseract`, fixing a Windows-only test font) is a direct, recent
reminder of what happens when a feature's environment assumptions go unverified — `available()` must report
`False` cleanly there, and neither `/api/pageqa` nor `build_pageqa.py` may ever attempt a real model load
when it does. `build_pageqa.py` checks availability up front and exits cleanly with a message if unavailable,
matching `build_dedup.py`'s existing pattern for a missing optional dependency.

## Routes

- **`/api/vlm`** — unchanged, stays a thin wrapper (R1: never break an existing route's contract).
- **`/api/pageqa`** (new) — the capable route; calls `pageqa.ask()` directly, exposes `mode`/`strict` params
  for the interactive consumer's use (always `mode=text, strict=False` from the shipped UI, but the param
  exists so the route itself doesn't hardcode the caller's intent).

## Testing

- **`pageqa.py` self-test** (module `__main__`, mirroring `vlm.py`'s own convention) with an injectable fake
  backend (same `_backend` injection pattern `vlm.py` already has): covers structured-response parsing, the
  `strict=False` hard cap at "review," and both verification pass/fail paths via mocked grounded/ungrounded/
  textually-mismatched responses.
- **New `test_pageqa.py`** — e2e style, matching `test_dedup.py`/`test_symbols_routes.py`'s established
  pattern: a real tiny PDF fixture with known torque text, a mocked backend, run through the real
  `build_pageqa.py` as an actual subprocess. Confirms a verified row lands in `pageqa.db` and is picked up by
  the next `masterfile.py` build; separately confirms a rejected (ungrounded or textually-mismatched) claim
  writes nothing.
- **Extend `test_routes.py`'s blanket GET/POST sweep** to cover `/api/pageqa` degrading cleanly (`available:
  false`, no crash) with no backend installed — directly exercised by CI, which has neither.

## Open items for the implementation plan (not design-blocking)

- Exact prompt templates per extraction type.
- Florence-2 model size (base vs. large) and quantization, tuned against real hardware.
- Fuzzy-match algorithm/threshold for the OCR cross-check.
- Whether `masterfile.py`'s `_confidence()` badge text needs a new label for `vlm-verified` provenance, or
  reuses "high — cited & corroborated" unchanged once ≥1 other source agrees.
- Whether `build_pageqa.py` asks one generic sweep question per sampled page or one templated question per
  candidate field type (multiple `ask()` calls) — the core interface is unaffected either way; this is purely
  how the batch tool drives it.
