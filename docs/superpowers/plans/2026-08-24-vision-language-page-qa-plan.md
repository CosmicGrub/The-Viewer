# Vision-Language Page QA — Implementation Plan

**Spec:** `docs/superpowers/specs/2026-08-24-vision-language-page-qa-design.md`
**Status:** planned, not started

No "writing-plans" skill was available in this environment to generate this mechanically — written directly,
following this project's own established conventions (phased, independently-testable, verify-gated at every
step, R1-R13 discipline) rather than a generic template.

## Sequencing rationale

Two phases, each shippable and mergeable on its own — mirrors how this project already ships large features
(e.g. "Discovery Engine phase 1"). Phase 1 gets something real and useful in front of a mechanic fast, with
zero risk to the corpus or any sidecar (the interactive path never writes anything). Phase 2 is the higher-risk
half — anything that writes unattended gets the hard-verification discipline, and it's easier to review that
in isolation once Phase 1's core (`pageqa.py`, the backend) is already proven working.

---

## Phase 1 — Core + interactive consumer

Ships "ask this page" as a real, usable feature. No batch tool, no sidecar writes, no Masterfile change.

1. **`engine/vlm.py`** — widen `ask()`'s return contract to accept `{"text":..., "region":...}` in addition to
   today's bare string. Backward-compatible: existing `/api/vlm` callers unaffected, `region` always optional.
2. **`engine/vlm_backend.py`** (new) — the real Florence-2 integration: lazy model load, grounded-task
   prompting, response parsing. New optional dependency, Advanced/GPU-fork only (document in
   `docs/SYSTEM-REQUIREMENTS.md` and `requirements.txt`'s RECOMMENDED tier, matching `office.py`'s precedent).
3. **`engine/pageqa.py`** (new) — the shared core. This phase only needs the `mode="text", strict=False` path:
   call the backend, hard-cap trust at "review", return `{answer_text, region, trust_tier}`. (`mode="structured"`
   and the verification algorithm are Phase 2 — the function signature should already accept both params so
   Phase 2 is additive, not a breaking rework.)
4. **`/api/pageqa`** (new route) — thin wrapper calling `pageqa.ask()`. `/api/vlm` stays untouched.
5. **`engine/ui/deepzoom.html`** — the "🔎 Ask this page" floating control (matches the mockup already
   reviewed): question input, region highlight box, review badge + disclaimer. Gated on `pageqa.available()`
   client-side so it's simply absent on lite/legacy tier or no-GPU machines.
6. **`engine/ask.py` / `engine/ui/ask.html`** — VLM fallback: when `extract_answer()` returns no sentences for
   the top retrieved page, fall through to `pageqa.ask()` on that page.
7. **Tests:**
   - `pageqa.py` self-test (`__main__`, injectable fake backend mirroring `vlm.py`'s own pattern) — covers the
     text-mode path and the "review" hard cap.
   - Extend `test_routes.py`'s blanket sweep: `/api/pageqa` degrades to `available:false` cleanly with no
     backend installed (this is what actually runs in CI).
   - `rps_lint.py` pass on the two touched UI files.
8. **Docs:** `CHANGELOG.md` entry; `docs/EXTRACTION-METHODS-CATALOG.md` §10.1 status `○` → `◐` (QA works,
   structured/verified extraction still Phase 2); `docs/SYSTEM-REQUIREMENTS.md` gets the new optional
   dependency section.
9. **Verify:** `engine/tests/verify_all.py --snapshot` green before merge, matching every other change this
   project has shipped.

## Phase 2 — Structured extraction, verification, and the batch tool

The higher-stakes half: anything here can write to a sidecar unattended, so nothing here ships without the
verification discipline the spec requires.

10. **`engine/pageqa.py`** — add `mode="structured"` (typed `{type, value, value2, unit, region, source_text}`
    output, reusing `measures.py`'s existing type taxonomy) and the two-part `strict=True` verification:
    self-grounding re-check + OCR cross-check against the page's own stored text. Returns `verified: bool`;
    never writes anything itself — verification is a pure function, persistence stays the caller's job (matches
    `dedup.py`'s build()-does-the-writing-not-the-library-function convention).
11. **New sidecar `index/pageqa.db`** — own schema, own `CREATE TABLE IF NOT EXISTS` init (matching
    `dedup.db`/`kg.db`, not a `viewer.db` migration). One table, `pageqa_extractions`, shaped per the spec's
    data model.
12. **`engine/build_pageqa.py` + `BUILD-PAGEQA.bat`** (new) — the batch driver, structurally mirroring
    `build_dedup.py`/`DEDUP.bat`: samples pages where `measures.py`/`tables.py`/RPSTL found nothing and
    `ocr_confidence >= 0.5` (reusing `coverage.py`'s existing threshold), calls `pageqa.ask(mode="structured",
    strict=True)`, writes only `verified=True` rows, respects `--max-pages`. Checks `pageqa.available()` up
    front and exits cleanly if unavailable (matches `build_dedup.py`'s missing-dependency precedent).
13. **`engine/masterfile.py`** — add `pageqa.db` to `build()`'s source list, tagged `source='vlm-verified'`
    (same distinguishable-provenance pattern as barcode-decoded `parts` rows).
14. **`engine/verifystate.py`** — add `pageqa.py`/`build_pageqa.py` to `SELFTEST_MODULES` (matching how
    `office.py`/`flags.py` were added when they shipped); `VERIFY.bat` gate list updated to match.
15. **Tests:**
    - `test_pageqa.py` (new) — e2e: real tiny PDF fixture with known torque text, mocked backend returning a
      grounded/matching claim → confirms a verified row lands in `pageqa.db` and a subsequent `masterfile.py`
      rebuild picks it up; separately, a mocked backend returning an ungrounded or textually-mismatched claim
      → confirms nothing is written.
    - Extend `test_masterfile_robustness.py` or add a targeted case: `pageqa.db` missing/torn degrades cleanly
      (matches `dedup.db`'s existing degrade contract).
16. **Docs:** `CHANGELOG.md` entry; `docs/EXTRACTION-METHODS-CATALOG.md` §10.1 → `✅`, §3.12 → `✅`;
    `docs/MASTER-RECONCILIATION.md` §4 feature-inventory line for the extraction/enrichment category.
17. **Verify:** `engine/tests/verify_all.py --snapshot` green before merge.

## Open decisions carried from the spec (resolve during implementation, not blocking either phase)

Exact prompt templates, Florence-2 quantization level, the OCR cross-check's fuzzy-match parameters, whether
`masterfile._confidence()` needs a new label for `vlm-verified` provenance, and whether the batch tool asks one
generic question per page or one per candidate field type — see the spec's own "Open items" section.
