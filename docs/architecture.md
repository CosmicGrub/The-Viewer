# Architecture

How the extraction pipeline, search index, backend API, and frontend fit together — see [data-model.md](data-model.md) for the actual document schema, and the top-level [README](../README.md) for setup/usage commands.

## Pipeline overview

```
TM_SOURCE_DIR (PDFs, DOCX, images)
        │
        ▼
  detect_format.py            classifies every file: pdf / docx / image / unsupported
        │
        ▼
  extract_documents.py        dispatches each file by type, incrementally + resumably
   ├─ extract_pdf_text.py     pdfplumber, OCR fallback via PyMuPDF + pytesseract
   ├─ extract_docx_text.py    python-docx (paragraphs + table cells)
   └─ extract_image_text.py   pytesseract directly (standalone scans)
        │
        ▼  writes after every file, not just at the end
  TM_OUTPUT_DIR/
   ├─ extraction_test_results.json   one JSON object per source file (see data-model.md)
   └─ extraction_manifest.json       {filepath: {mtime, size, status}} — drives incremental re-runs
        │
        ▼
  index_documents.py          reads the results JSON, pushes it into Meilisearch
        │                     (search_index.py owns the actual client/index logic)
        ▼
  Meilisearch (documents index)
        │
        ▼
  backend/main.py + routers/search.py    FastAPI, serves /api/search + /api/search/documents/{id}
        │
        ▼
  frontend/ (React)           search UI, calls the API directly (dev: via Vite's proxy)
```

Extraction and indexing are deliberately separate, offline steps you run yourself (CLI scripts), not something the API triggers — there's no "upload a file and it appears in search results" path. That keeps the API surface small and means indexing a large corpus never blocks (or times out) an HTTP request.

## Why extraction and indexing are separate scripts

`extract_documents.py` and `index_documents.py` could have been one step. They're split because:
- Extraction (especially OCR) is slow and CPU-bound; indexing is fast. Re-running extraction after a code change to `index_documents.py`/`search_index.py` (index settings, ranking rules, etc.) would be wasteful if they were coupled.
- The extraction results JSON is a useful inspection point on its own — worth checking before trusting it into the index.
- `index_documents.py --prune` needs to run independently of any particular extraction batch (see [data-model.md](data-model.md#document-identity) on why pruning needs a full directory scan, not just the last batch's results).

## Incremental extraction (extract_documents.py)

`extract_documents.py` is the entry point for a real corpus (as opposed to `extract_pdf_text.py`'s own CLI, which is PDF-only and always reprocesses everything — useful for a quick manual test, not a full run). It tracks progress in `extraction_manifest.json`, keyed by filepath, recording each file's `mtime`/`size`/`status` as of its last successful extraction. On each run:
1. Scan `TM_SOURCE_DIR` via `detect_format.scan_directory()`.
2. For each file, compare its current `mtime`/`size` against the manifest. Unchanged → skip (its result from a prior run is still in `extraction_test_results.json`).
3. Otherwise, extract it and immediately flush both the manifest and the results file to disk.

That last point is what makes it resumable — interrupting a 10,000-file run at file 4,000 costs nothing on re-run; it picks up where it left off. `--force` bypasses the manifest and redoes everything.

## OCR fallback

`extract_pdf_text.py` tries `pdfplumber`'s native text extraction first. When a page has no extractable text (a scanned/image-only page), it falls back to OCR:
1. Rasterize the page via PyMuPDF at `OCR_DPI` (300).
2. Preprocess the image (`preprocess_for_ocr`): grayscale → deskew → adaptive threshold, via OpenCV. Falls back to the untouched image if OpenCV/numpy aren't importable or the image is degenerate — this is a quality improvement, never a hard requirement.
3. Run `pytesseract.image_to_string` with tuned settings (`--oem 3 --psm 6`, English).

Whether the `tesseract` binary is even on `PATH` is checked once, at import time (`TESSERACT_AVAILABLE`) — not inferred from the first OCR attempt failing. A single page's OCR failing (a corrupt rasterization, a transient error) is logged and skipped; it does not disable OCR for the rest of that file, unlike an earlier version of this pipeline.

## Search request flow

`GET /api/search?q=...` → `routers/search.py` → `search_index.get_client()` → Meilisearch's own `/indexes/{index}/search`. The response is reshaped into `SearchResponse`/`SearchResult` (see [data-model.md](data-model.md)) — notably, **search results carry only a cropped snippet, not the full document text**. Full text is fetched separately, on demand, via `GET /api/search/documents/{id}` when a user actually opens a result. Indexing full text into every search hit would bloat every response for the (usually rare) case a result is opened at all.

## Access control

With no configuration, the API is open — appropriate only on a single developer machine. `backend/security.py` provides two independent, opt-in controls, both wired as FastAPI dependencies on the search router:
- **`TM_API_KEY`** — if set, every `/api/*` request must carry a matching `X-API-Key` header.
- **Rate limiting** — an in-memory sliding-window limiter, per client IP, on `/api/search` specifically (`TM_SEARCH_RATE_LIMIT` / `TM_SEARCH_RATE_LIMIT_WINDOW_SECONDS`). In-memory means this doesn't coordinate across multiple backend replicas — fine for the single-instance deployment this project currently targets (see `docker-compose.yml`), but would need to move to something shared (Redis, etc.) before running multiple backend instances behind a load balancer.

Separately, `config.py` refuses to even start if `MEILISEARCH_URL` isn't localhost and no `MEILISEARCH_API_KEY` is set (override with `TM_ALLOW_INSECURE_MEILISEARCH=1`) — this catches the specific mistake of pointing a deployed backend at an unauthenticated remote Meilisearch.

## Deployment

`docker-compose.yml` runs Meilisearch, the backend, and the frontend as three containers (see the file's own comments for the details): the frontend is a static build served by `nginx`, which proxies `/api` and `/health` to the backend container — mirroring what `vite.config.ts`'s dev-server proxy does locally, so there's no separate CORS configuration needed for the containerized deployment either.
