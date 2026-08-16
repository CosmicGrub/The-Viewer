# TM Search Engine

A search engine for indexing and searching Technical Manuals (TMs) — extracting text from PDFs, Word docs, and scanned images, and making them searchable via Meilisearch.

## Status

Early-stage, but the core pipeline works end to end: extract text (with OCR fallback) → index into Meilisearch → search it via the API. `/api/search` is live, not stubbed.

## Project structure

```
backend/
  main.py                 # FastAPI app: liveness/status endpoints, mounts routers/
  config.py                # Shared config (source/output paths, Meilisearch settings, UTF-8 stdio fix)
  detect_format.py       # Classifies files (pdf/docx/image/unsupported) by scanning a directory
  extract_pdf_text.py     # Extracts text from PDFs via pdfplumber, with OCR fallback (PyMuPDF + pytesseract)
  search_index.py          # Meilisearch client/index helpers shared by index_documents.py and routers/search.py
  index_documents.py        # CLI: pushes extract_pdf_text.py's JSON output into Meilisearch
  routers/
    search.py              # /api/search — real Meilisearch-backed search
  tests/
    conftest.py             # Puts backend/ on sys.path for pytest
    test_extraction.py      # Basic import/sanity check for extraction dependencies
    test_main.py            # FastAPI TestClient tests (Meilisearch client mocked — hermetic, no live server needed)
bin/                        # Local Meilisearch server binary (downloaded, gitignored — see Setup)
frontend/
  src/, public/            # Placeholder — not yet scaffolded
data/
  extracted/                # Extraction output (gitignored except .gitkeep)
  meilisearch/               # Meilisearch data directory (gitignored except .gitkeep)
  ocr_output/
docs/                      # Architecture/data-model/setup notes (placeholder)
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
4. Download a local Meilisearch server binary (no official Windows package manager entry — this is the standard way to run it on Windows outside Docker):
   ```bash
   mkdir bin
   curl -L -o bin/meilisearch.exe https://github.com/meilisearch/meilisearch/releases/latest/download/meilisearch-windows-amd64.exe
   ```
   `bin/` is gitignored — each machine downloads its own copy.
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
   python backend/extract_pdf_text.py "K:\ALL MILITARY TMS" --output-dir data/extracted --max-files 5
   ```

With `.env` configured, both scripts can be run with no arguments:
```bash
python backend/detect_format.py
python backend/extract_pdf_text.py
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
It's safe to re-run — documents are keyed by a hash of their filepath, so re-indexing the same file updates its existing entry instead of duplicating it.

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

Then visit `http://127.0.0.1:8000/docs` for interactive Swagger docs. Available routes right now:

| Route | Purpose |
|---|---|
| `GET /` | Basic info + link to docs |
| `GET /health` | Health check |
| `GET /api/status` | Reports whether `TM_SOURCE_DIR`/`TM_OUTPUT_DIR` are configured |
| `GET /api/search?q=...&limit=&offset=` | Full-text search over indexed documents. Returns `503` (with a specific message) if Meilisearch is unreachable or the index hasn't been built yet — not a fake empty result set |

## Testing

```bash
pytest backend/tests
```

## Roadmap

- [x] Make source/output paths configurable (CLI args or `.env`) instead of hardcoded
- [x] Add OCR fallback for image-only PDFs (pdfplumber pages with no extractable text are rasterized via PyMuPDF and run through pytesseract)
- [x] Stand up the FastAPI backend skeleton (liveness/status endpoints, stubbed search route)
- [x] Wire up the Meilisearch indexing pipeline behind `/api/search`
- [ ] Scaffold the frontend
- [ ] Expand `backend/tests/` with real coverage (search endpoint tests mock Meilisearch — still no automated coverage of search_index.py/index_documents.py against a live server)
- [ ] Index DOCX/image documents too (currently PDF-only — detect_format.py already classifies them, extraction doesn't handle them yet)

## Tech stack

- **Extraction:** pdfplumber, PyMuPDF (page rasterization for OCR), pytesseract, python-docx, Pillow, opencv-python
- **Search:** Meilisearch (server binary run locally; `meilisearch` Python package as the client)
- **Backend:** FastAPI, uvicorn, pydantic
- **Testing:** pytest, httpx (for FastAPI's TestClient)
