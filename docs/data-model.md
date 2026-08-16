# Data model

Two related-but-distinct schemas: the **extraction result** (what `extract_*.py` produce, and what's in `extraction_test_results.json`), and the **Meilisearch document** (what `search_index.to_document()` derives from an extraction result and actually indexes). See [architecture.md](architecture.md) for how they fit into the pipeline.

## Extraction result

One object per source file, produced by `extract_pdf_text.py` / `extract_docx_text.py` / `extract_image_text.py`, all three returning the same shape so `index_documents.py`/`search_index.py` don't need to care which extractor produced a given result.

```jsonc
{
  "status": "success",              // or "error" — see below
  "filename": "hydraulic_pump_manual.pdf",
  "filepath": "K:\\ALL MILITARY TMS\\hydraulic_pump_manual.pdf",
  "file_size": 4213765,
  "num_pages": 42,                  // null for DOCX (no fixed page count outside a layout renderer)
  "metadata": {                     // "N/A" per-field when the source file has no such metadata
    "title": "Hydraulic Pump Manual",
    "author": "Dept. of the Army",
    "subject": "N/A"
  },
  "text": "\n--- PAGE 1 ---\n...",   // full extracted text; PDFs are page-delimited, DOCX/images are not
  "text_length": 128340,
  "ocr_pages_used": [3, 4],         // 1-indexed PDF pages that needed OCR; images use [1] or []
  "ocr_unavailable_reason": "...",  // present only if `tesseract` wasn't found on PATH
  "extracted_at": "2026-08-16T12:00:00+00:00"  // UTC, ISO 8601
}
```

A failed extraction is much smaller and has no `text`:
```jsonc
{ "status": "error", "filename": "...", "filepath": "...", "error": "..." }
```
`index_documents.py` skips `status: "error"` entries — there's no text to search.

## Meilisearch document

`search_index.to_document()` derives this from a *successful* extraction result. This is what's actually searched/filtered/sorted/returned by `/api/search`.

| Field | Type | Notes |
|---|---|---|
| `id` | string | `sha1` hex digest — see "Document identity" below. Meilisearch's primary key. |
| `filename` | string | Searchable. |
| `filepath` | string | Not searchable — display/reference only. |
| `title` | string | From PDF/DOCX metadata, `""` if absent (normalizes the `"N/A"` placeholder). Searchable, weighted above `filename`/`text` (see "Ranking" below). |
| `author` | string | From metadata, `""` if absent. Not searchable — display only. |
| `text` | string | The full extracted text. Searchable. |
| `num_pages` | int \| null | Filterable (`min_pages`/`max_pages` on `/api/search`), not sortable. |
| `file_size` | int | Sortable (not currently exposed via the API — see Roadmap). |
| `ocr_pages_used` | int[] | Display only. |
| `extracted_at` | string (ISO 8601, UTC) | Filterable and sortable (`sort=newest`/`oldest` on `/api/search`). |

`INDEX_SETTINGS` in `search_index.py` is the single source of truth for which fields are searchable/filterable/sortable, plus ranking tuning — see that file's comments for the current settings and why. `search_index.ensure_index()` only pushes a settings update to Meilisearch when the live settings actually differ from `INDEX_SETTINGS`, so redeploying with unchanged settings doesn't trigger a needless reprocessing task.

## Document identity

A document's `id` is `sha1(<key>)`, where `<key>` is:
- the file's path **relative to `TM_SOURCE_DIR`** (forward-slash-normalized), if the file is under it — the common case; or
- the raw absolute path, for files extracted outside `TM_SOURCE_DIR` (e.g. passed directly to a script).

Hashing the *relative* path (not the absolute one) is deliberate: it's what makes a document's id survive `TM_SOURCE_DIR` being remounted at a different absolute location — a different drive letter, a different mount point, moved to another machine. Only the relative directory structure has to stay the same. Re-extracting and re-indexing the same relative file always updates the same document rather than creating a duplicate, even across that kind of move.

This also means **renaming or moving a file within `TM_SOURCE_DIR` produces a new id** — from the index's point of view that's a different document (the old id is now orphaned, the new relative path gets a fresh one). `index_documents.py --prune` (see below) is how an orphaned entry actually gets removed rather than lingering forever.

## Reconciling deletions (`--prune`)

Indexing (`index_documents.py`, no flags) only adds/updates documents — it never removes anything, because a single run's input JSON might only cover a partial batch (`extract_documents.py --max-files N`), and treating "not in this batch" as "delete it" would wipe out everything not just processed. `--prune` is the explicit, separate reconciliation step: it does a **full** scan of `--source-dir`/`TM_SOURCE_DIR` (not just the current results JSON) to get the true current file set, then deletes any indexed document whose id doesn't correspond to one of those files. Only run it once you're confident the source directory scan is complete and representative — e.g. not mid-way through populating `TM_SOURCE_DIR` from a slow network copy.

## Relevance tuning notes

- **`rankingRules`** promotes `exactness` ahead of `typo` (default order has `typo` second). Technical manuals are dense with part numbers and NSN-style codes (`5310-01-234-5678`) where a fuzzy/typo-tolerant match is usually a *wrong* result, not a helpful one.
- **`typoTolerance.minWordSizeForTypos`** is raised (6/10 chars vs. the 5/9 default) so short alphanumeric code segments (hyphen-tokenized, so a code like the one above becomes several short segments) aren't typo-"corrected" into a different code, while genuine prose words still get reasonable typo tolerance.
- **`searchableAttributes` order** (`title`, `filename`, `text`) sets Meilisearch's attribute-ranking priority — a match in a manual's title/filename ranks above the same term buried somewhere in a few hundred pages of body text.

None of this has been validated against real query logs yet (there aren't any — see the Roadmap in the top-level README). Treat it as a reasoned starting point, not a tuned-and-measured result.
