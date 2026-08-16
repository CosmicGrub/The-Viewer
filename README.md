# TM Search Engine

A search engine for indexing and searching Technical Manuals (TMs) — extracting text from PDFs, Word docs, and scanned images, and making them searchable via Meilisearch.

## Status

Early-stage, but the core pipeline works end to end: extract text (with OCR fallback) → index into Meilisearch → search it via the API. `/api/search` is live, not stubbed.

## Project structure

```
backend/
  main.py                 # FastAPI app: liveness/status endpoints, request logging, mounts routers/
  config.py                # Shared config (paths, Meilisearch/CORS/auth/rate-limit settings, UTF-8 stdio fix, shared logger)
  security.py               # API-key auth + per-IP rate limiting (FastAPI dependencies used by routers/search.py)
  detect_format.py       # Classifies files (pdf/docx/image/unsupported) by scanning a directory
  extract_pdf_text.py     # Extracts text from PDFs via pdfplumber, with OCR fallback (PyMuPDF + pytesseract, preprocessed via OpenCV)
  extract_docx_text.py     # Extracts text (incl. table cells) from Word documents via python-docx
  extract_image_text.py    # OCRs standalone image files, reusing extract_pdf_text.py's preprocessing/tuning
  extract_documents.py     # Orchestrator: dispatches pdf/docx/image by type, incremental + resumable across runs
  search_index.py          # Meilisearch client/index helpers shared by index_documents.py and routers/search.py
  index_documents.py        # CLI: pushes extraction JSON into Meilisearch; --prune reconciles deletions
  backup_index.py           # CLI: triggers + waits on a full Meilisearch dump (see "Backing up the search index")
  Dockerfile                # Backend container image (built from the repo root — see docker-compose.yml)
  routers/
    search.py              # /api/search — real Meilisearch-backed search
  tests/
    conftest.py             # Puts backend/ on sys.path for pytest
    test_extraction.py      # Basic import/sanity check for extraction dependencies
    test_main.py            # FastAPI TestClient tests (Meilisearch client mocked — hermetic, no live server needed)
    test_search_index.py     # document_id stability, index-creation race handling, pruning, metadata indexing
    test_extract_docx.py     # DOCX extraction (paragraphs, tables, core metadata)
    test_extract_pdf_ocr.py  # PDF OCR-fallback control flow, with the pdfplumber/PyMuPDF/pytesseract stack stubbed
    test_backup_index.py     # backup_index.py's dump-polling logic
bin/                        # Local Meilisearch server binary (downloaded, gitignored — see Setup)
frontend/                   # Vite + React + TypeScript + Tailwind CSS UI (see Frontend section)
  src/
    App.tsx                 # Search UI: results list + detail pane (snippet/full text tabs)
    api.ts                  # Typed client for the backend API
    format.ts                # Byte/date formatting utilities (unit-tested separately — format.test.ts)
    highlight.tsx             # Query-term highlighting (unit-tested separately — highlight.test.tsx)
    App.test.tsx              # App.tsx's search state machine (idle/loading/ready/error), Vitest + RTL
  eslint.config.js          # Real ESLint flat config (react-hooks/react-refresh/typescript-eslint)
  Dockerfile                 # Static build served by nginx (see nginx.conf, docker-compose.yml)
data/
  extracted/                # Extraction output (gitignored except .gitkeep)
  meilisearch/               # Meilisearch data directory (gitignored except .gitkeep)
  ocr_output/
docs/                      # architecture.md, data-model.md — see docs/README.md
docker-compose.yml         # Cross-platform (Linux/Mac/Windows) deployment: Meilisearch + backend + frontend
.github/workflows/ci.yml    # pytest + tsc + eslint + vitest + build, on every push/PR
validate_environment.py    # Checks required Python modules, external tools, folders, and files
validate_day1.bat          # Windows batch wrapper for Day 1 validation
requirements.txt           # Python dependencies
```

## Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install external tools required for OCR: [Tesseract](https://github.com/tesseract-ocr/tesseract) must be on your `PATH`. On Windows:
   ```bash
   winget install --id UB-Mannheim.TesseractOCR
   ```
   The installer doesn't always add itself to `PATH` automatically — if `tesseract --version` doesn't work afterward, add `C:\Program Files\Tesseract-OCR` to your user `PATH` and open a new terminal.
4. Download a local Meilisearch server binary (no official Windows package manager entry — this is the standard way to run it on Windows outside Docker). Pinned to a specific version rather than `latest` — an unpinned URL means "the same setup command" silently fetches a different server over time, which isn't reproducible across machines or reinstalls:
   ```bash
   mkdir bin
   curl -L -o bin/meilisearch.exe https://github.com/meilisearch/meilisearch/releases/download/v1.11.3/meilisearch-windows-amd64.exe
   ```
   `bin/` is gitignored — each machine downloads its own copy. Check [Meilisearch's releases](https://github.com/meilisearch/meilisearch/releases) before bumping this version, and update it here (and in `docker-compose.yml`'s `image:` tag) together so local and containerized setups stay on the same server version.
5. Run the environment validator:
   ```bash
   python validate_environment.py
   ```

## Usage

Source/output paths are configurable via `.env`, environment variables, or CLI arguments (in that order of precedence, CLI wins):

1. Copy `.env.example` to `.env` and set `TM_SOURCE_DIR` (and optionally `TM_OUTPUT_DIR`) for your machine, **or**
2. Pass a directory directly as an argument:
   ```bash
   python backend/detect_format.py "K:\ALL MILITARY TMS"
   python backend/extract_documents.py "K:\ALL MILITARY TMS" --output-dir data/extracted
   ```

With `.env` configured, both scripts can be run with no arguments:
```bash
python backend/detect_format.py
python backend/extract_documents.py
```

`extract_documents.py` is the recommended entry point for a real corpus — it extracts PDFs, DOCX, and standalone images (`extract_pdf_text.py`'s own CLI only handles PDFs, and always reprocesses everything from scratch). It's also incremental and resumable: files that haven't changed since their last successful extraction (tracked in `TM_OUTPUT_DIR/extraction_manifest.json`) are skipped, and results are written to disk after every file — so interrupting a large run and re-running later picks up where it left off, rather than starting over.
```bash
python backend/extract_documents.py                       # everything under TM_SOURCE_DIR
python backend/extract_documents.py --max-files 200        # process at most 200 *new* files this run
python backend/extract_documents.py --force                # ignore the manifest, redo everything
```

## Running Meilisearch

Start the local server (in its own terminal, or backgrounded — it needs to keep running):
```bash
bin/meilisearch.exe --db-path data/meilisearch --http-addr 127.0.0.1:7700 --env development --no-analytics
```
`--env development` runs without a master key (no auth), which is fine for a local machine but **not** for anything reachable over a network — see Meilisearch's docs on production master keys before deploying this anywhere. Check it's up with:
```bash
curl http://127.0.0.1:7700/health
```

## Building the search index

Once documents are extracted (see Usage above), push them into Meilisearch:
```bash
python backend/index_documents.py
```
This reads `TM_OUTPUT_DIR/extraction_test_results.json` (the file `extract_pdf_text.py` produces) by default, or accepts a path explicitly:
```bash
python backend/index_documents.py path/to/extraction_test_results.json
```
It's safe to re-run — documents are keyed by a hash of their filepath *relative to `TM_SOURCE_DIR`*, so re-indexing the same file updates its existing entry instead of duplicating it, and the id stays stable even if the source drive is remounted or moved.

Deleting or moving a source file doesn't remove it from the index on its own — pass `--prune` to reconcile the index against what's actually on disk (does a full scan of `--source-dir`/`TM_SOURCE_DIR` first, so it's safe to run even after a partial `--max-files` batch):
```bash
python backend/index_documents.py --prune
```

## Running the API

From the repo root:
```bash
uvicorn main:app --reload --app-dir backend
```
or from `backend/`:
```bash
cd backend
uvicorn main:app --reload
```

Then visit `http://127.0.0.1:8000/docs` for interactive Swagger docs.

**Access control** (see `.env.example`): with no configuration, the API is open — fine on a single developer machine, not fine anywhere reachable over a network.
- Set `CORS_ORIGINS` to the frontend origin(s) you're actually serving from (defaults to the local Vite dev server).
- Set `TM_API_KEY` to require an `X-API-Key: <value>` header on every `/api/*` request.
- `/api/search` is rate-limited to `TM_SEARCH_RATE_LIMIT` requests per client IP per `TM_SEARCH_RATE_LIMIT_WINDOW_SECONDS` (default 60/60s; set to `0` to disable, e.g. for tests).
- If `MEILISEARCH_URL` isn't localhost, a `MEILISEARCH_API_KEY` is required — the app refuses to start against an unauthenticated remote Meilisearch unless you explicitly set `TM_ALLOW_INSECURE_MEILISEARCH=1`.

Available routes right now:

| Route | Purpose |
|---|---|
| `GET /` | Basic info + link to docs |
| `GET /health` | Health check |
| `GET /api/status` | Reports whether `TM_SOURCE_DIR`/`TM_OUTPUT_DIR` are configured |
| `GET /api/search?q=...&limit=&offset=` | Full-text search over indexed documents. Returns `503` (with a specific message) if Meilisearch is unreachable or the index hasn't been built yet — not a fake empty result set |
| `GET /api/search/documents/{document_id}` | Full text + metadata for one document (search results only carry a cropped snippet, to keep responses small). `404` if the id doesn't exist |

## Testing

```bash
pytest backend/tests
```

## Frontend

A Vite + React + TypeScript UI in `frontend/`, styled with Tailwind CSS and [lucide-react](https://lucide.dev) icons. Its visual language (dark slate theme, sky-blue accent, search bar with a live-narrowing results list on the left and a tabbed detail pane on the right) is modeled after [CosmicGrub/The-Viewer](https://github.com/CosmicGrub/The-Viewer)'s `react/TheViewer.jsx` reference component — adapted from that project's parts/NSN catalog UI to this project's document search domain.

Setup:
```bash
cd frontend
npm install
npm run dev
```
Then visit the printed `http://localhost:3000` (or whatever port Vite falls back to if that one's busy). The dev server proxies `/api/*` and `/health` to the backend at `127.0.0.1:8000` (see `vite.config.ts`), so no CORS setup is needed in dev — just make sure the backend (and Meilisearch, and a built index) are running first.

What it does:
- Debounced search-as-you-type (300ms) against `GET /api/search`, with `Ctrl`/`Cmd`+`K` to focus the search box, and a "Load more" control that pages through results past the first 20 via `offset`
- Left sidebar lists results (title if the source file has one, else filename; id; match score); selecting one loads its full text + metadata on demand from `GET /api/search/documents/{id}` (cached per document for the session)
- Detail pane has "Matched snippet" and "Full text" tabs, both with query-term highlighting; full text is paginated in ~8,000-character chunks rather than rendered as one giant block, so opening a long OCR'd manual doesn't jank the tab
- A backend-status indicator in the header (`GET /health`), polled every 15s so it reflects the backend actually going down mid-session, not just its state at page load
- An in-flight search is aborted as soon as a newer one starts, so a slow earlier response can't land after (and overwrite) a faster later one
- Distinguishes real states honestly: idle / loading / no matches / a 503 from the backend (Meilisearch down or index not built) — no fake empty results

`npm run build` type-checks (`tsc -b`) and produces a static `dist/` you could serve separately.

Other frontend commands:
```bash
npm run typecheck   # tsc -b --noEmit
npm run lint        # eslint . (real ESLint, not a tsc alias — see eslint.config.js)
npm run test        # vitest run — App.tsx's search state machine (format.test.ts, highlight.test.tsx, App.test.tsx)
```
`format.ts` (byte/date formatting) and `highlight.tsx` (query-term highlighting) are split out of `App.tsx` specifically so they're unit-testable on their own, separate from the component tests in `App.test.tsx`.

## Deployment (Docker)

Everything above assumes a Windows dev machine running each piece by hand. `docker-compose.yml` at the repo root runs Meilisearch, the backend, and the frontend together, and works the same on Linux/Mac/Windows:
```bash
cp .env.example .env   # set MEILI_MASTER_KEY, TM_SOURCE_DIR_HOST, etc.
docker compose up --build
```
Then visit `http://localhost:3000`. Extraction/indexing are one-off commands run inside the backend container:
```bash
docker compose run --rm backend python extract_documents.py
docker compose run --rm backend python index_documents.py --prune
```
See `backend/Dockerfile`, `frontend/Dockerfile` (built as a static `nginx` image — `frontend/nginx.conf` proxies `/api` and `/health` the same way `vite.config.ts`'s dev-server proxy does), and the comments in `docker-compose.yml` for details.

## Backing up the search index

The Meilisearch index can represent days of extraction work across a large corpus, and `data/meilisearch/` is gitignored — there's no copy of it anywhere else. Trigger a [Meilisearch dump](https://www.meilisearch.com/docs/learn/data_backup/dumps) (a full snapshot of every index, restorable into a fresh Meilisearch instance of the same or later version) with:
```bash
python backend/backup_index.py
```
This writes a `.dump` file into Meilisearch's configured `dumps` directory (next to `data/meilisearch/` by default) and prints its path. Restore by starting Meilisearch with `--import-dump path/to/the.dump` instead of `--db-path`. Run this on a schedule (cron/Task Scheduler) for anything beyond a personal dev index — there's no automatic backup here.

## Roadmap

- [x] Make source/output paths configurable (CLI args or `.env`) instead of hardcoded
- [x] Add OCR fallback for image-only PDFs (pdfplumber pages with no extractable text are rasterized via PyMuPDF and run through pytesseract), with image preprocessing (deskew, adaptive threshold) and tuned Tesseract page-segmentation settings
- [x] Stand up the FastAPI backend skeleton (liveness/status endpoints, stubbed search route)
- [x] Wire up the Meilisearch indexing pipeline behind `/api/search`
- [x] Scaffold the frontend (search UI, modeled after CosmicGrub/The-Viewer's design language)
- [x] Index DOCX/image documents too (`extract_docx_text.py`, `extract_image_text.py`, unified via `extract_documents.py`)
- [x] Incremental/resumable extraction across a large corpus (`extract_documents.py`'s manifest — see Usage)
- [x] Access control (`TM_API_KEY`, configurable `CORS_ORIGINS`, rate limiting) and index-integrity fixes (stable document ids across a relocated source drive, `--prune` reconciliation) — see commit history for the full audit-driven pass
- [ ] Expand `backend/tests/` further (search_index.py/index_documents.py/extract_*.py now have real unit coverage; still no test against a *live* Meilisearch server, and extract_pdf_text.py's PDF/OCR path itself is still untested — it needs a real PDF fixture)
- [ ] Production deployment for the frontend (currently dev-server-only; no static hosting / reverse-proxy config yet)
- [x] Automated frontend tests (Vitest + React Testing Library — `npm run test`; format/highlight utilities unit-tested separately from the App.tsx state machine)
- [ ] Domain-specific search relevance tuning (part-number/NSN-aware tokenization, synonym handling) — `INDEX_SETTINGS` is tuned for exactness over typo-tolerance as a first pass, not fully validated against real queries yet

## Tech stack

- **Extraction:** pdfplumber, PyMuPDF (page rasterization for OCR), pytesseract, python-docx, Pillow, opencv-python
- **Search:** Meilisearch (server binary run locally; `meilisearch` Python package as the client)
- **Backend:** FastAPI, uvicorn, pydantic
- **Frontend:** Vite, React, TypeScript, Tailwind CSS, lucide-react
- **Testing:** pytest, httpx (for FastAPI's TestClient)
