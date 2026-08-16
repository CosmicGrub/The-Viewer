# TM Search Engine

A search engine for indexing and searching Technical Manuals (TMs) — extracting text from PDFs, Word docs, and scanned images, and making them searchable via Meilisearch.

## Status

Early-stage. Extraction scripts are functional (including OCR fallback); a FastAPI app skeleton is now in place but not yet backed by a real search index — `/api/search` intentionally returns 501 until the Meilisearch indexing pipeline is wired up.

## Project structure

```
backend/
  main.py                 # FastAPI app: liveness/status endpoints, mounts routers/
  config.py                # Shared config (source/output paths, UTF-8 stdio fix)
  detect_format.py       # Classifies files (pdf/docx/image/unsupported) by scanning a directory
  extract_pdf_text.py     # Extracts text from PDFs via pdfplumber, with OCR fallback (PyMuPDF + pytesseract)
  routers/
    search.py              # /api/search — stubbed out (501) until indexing exists
  tests/
    conftest.py             # Puts backend/ on sys.path for pytest
    test_extraction.py      # Basic import/sanity check for extraction dependencies
    test_main.py            # FastAPI TestClient tests for main.py
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
4. Run the environment validator:
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
| `GET /api/search?q=...` | Stubbed — returns `501` until the Meilisearch indexing pipeline exists |

## Testing

```bash
pytest backend/tests
```

## Roadmap

- [x] Make source/output paths configurable (CLI args or `.env`) instead of hardcoded
- [x] Add OCR fallback for image-only PDFs (pdfplumber pages with no extractable text are rasterized via PyMuPDF and run through pytesseract)
- [x] Stand up the FastAPI backend skeleton (liveness/status endpoints, stubbed search route)
- [ ] Wire up the Meilisearch indexing pipeline behind `/api/search`
- [ ] Scaffold the frontend
- [ ] Expand `backend/tests/` with real coverage (currently a smoke test + API skeleton tests only)

## Tech stack

- **Extraction:** pdfplumber, PyMuPDF (page rasterization for OCR), pytesseract, python-docx, Pillow, opencv-python
- **Search:** Meilisearch
- **Backend:** FastAPI, uvicorn, pydantic
- **Testing:** pytest, httpx (for FastAPI's TestClient)
