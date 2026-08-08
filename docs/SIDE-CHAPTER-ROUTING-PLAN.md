# Phase-2 plan — chapter-level routing inside combined manuals

*Status: **BUILT in v0.75.0** (engine/chapters_feature.py + /api/chapters,/api/chapter_jump,/api/chapter_override
+ viewer routing/banner). This document is the original design; it matches what shipped. Companion to the
v0.73/0.74 "side of the house" split.*

## The problem this solves
A combined manual (TM …-**12** / **13** / **14**) is genuinely two books in one cover: operator chapters
**and** maintenance chapters, on different pages. Today the split is correct at the **document** level — a
-12 shows on **both** sides — but an operator who opens it still lands on page 1 of the whole book and has to
find the operator section themselves. Chapter-level routing would drop each side into *its own* chapters.

## The idea (one line)
Use the manual's own **table of contents / chapter headers** (already captured by OCR) to tag page ranges as
operator vs maintenance, so a combined manual opens to the right section for the side you're on.

## How it would work
1. **Find the structure.** For combined manuals only, parse the OCR'd front matter for the TOC and the
   chapter/section headings (e.g. "CHAPTER 1 — OPERATING INSTRUCTIONS", "CHAPTER 4 — UNIT MAINTENANCE",
   "OPERATOR PMCS", "MAINTENANCE ALLOCATION CHART"). These already sit in `pages.body_text`.
2. **Map page ranges to a side.** Build `chapter_sides` (a **sidecar**, never the main index): for each
   combined doc, a list of `{start_page, end_page, side, heading}`. Operator headings → operator range;
   maintenance/DS/GS/RPSTL/MAC headings → mechanic range; ambiguous → both.
3. **Route on open.** When a combined manual is opened from a side, jump to that side's first chapter and
   show a slim "this book also has a <other-side> section →" affordance. Search hits already carry a page, so
   a hit can be labelled with the chapter's side too.

## Why it's safe (RPS + speed + accuracy)
- **Sidecar only** — `chapter_sides.json` (or a small sidecar DB); the 3.65 GB index is never written (R1/R6).
- **Built once, cached** — like the side map, keyed on doc set; rebuild only when combined docs change. No
  per-request cost.
- **Pure stdlib parsing** (regex over OCR text) — no new dependency, runs on the legacy/RPS build.
- **Append-only + override-able** — reuse the same `sides_override.json` pattern at page-range granularity, so
  a wrong split can be corrected by hand. Falls back cleanly to whole-book (current behaviour) when no TOC is
  found, so it can never be *worse* than today.

## Risks / open questions
- **OCR TOC quality varies.** Older scans may lack a clean TOC; the fallback (whole-book on both sides) covers
  these, and they'd surface in an "uncertain chapters" review list like the document-level one.
- **Heading vocabulary.** Needs a vetted heading→side lexicon (operator/PMCS vs unit/DS/GS/MAC/RPSTL); start
  from the same coverage vocabulary `tm_side()` already uses.
- **Multi-volume sets.** A -12 split across physical volumes (-12-1, -12-2) may already be operator vs
  maintenance by volume — cheap win to detect first.

## Effort estimate
Medium. Reuses the OCR text, the sidecar/cache/override patterns, and the `tm_side` vocabulary already built.
Bulk is the TOC/heading parser + a small "review chapter splits" UI.

## Suggested trigger
Build after the document-level split has run on the real corpus (via `CLASSIFY-SIDES.bat`) and the
`uncertain` list is reviewed — that tells us how many combined manuals exist and whether their TOCs OCR'd
cleanly enough to make chapter routing worthwhile.
