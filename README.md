# TM Search Engine

A search engine for indexing and searching Technical Manuals (TMs) — extracting text from PDFs, Word docs, and scanned images, and making them searchable via Meilisearch.

## Status

Early-stage / Day 1 scaffolding. Core pieces exist as standalone scripts; not yet wired into a running API or indexing pipeline.

## Project structure

```
backend/
  detect_format.py       # Classifies files (pdf/docx/image/unsupported) by scanning a directory
  extract_pdf_text.py     # Extracts text from PDFs via pdfplumber, saves results to JSON
  tests/
    test_extraction.py    # Basic import/sanity check for extraction dependencies
frontend/
  src/, public/            # Placeholder — not yet scaffolded
data/
  extracted/                # Extraction output (gitignored except .gitkeep)
  meilisearch/               # Meilisearch data directory (gitignored except .gitkeep)
  ocr_output/
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
3. Install external tools required for OCR: [Tesseract](https://github.com/tesseract-ocr/tesseract) must be on your `PATH`.
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

## Roadmap

- [ ] Make source/output paths configurable (CLI args or `.env`) instead of hardcoded
- [ ] Add OCR fallback for image-only PDFs (pytesseract is a dependency but not yet wired up)
- [ ] Stand up the FastAPI backend and Meilisearch indexing pipeline
- [ ] Scaffold the frontend
- [ ] Expand `backend/tests/` with real coverage (currently a smoke test only)

## Tech stack

- **Extraction:** pdfplumber, pytesseract, python-docx, Pillow, opencv-python
- **Search:** Meilisearch
- **Backend:** FastAPI, uvicorn, pydantic
- **Testing:** pytest
