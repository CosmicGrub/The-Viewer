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

The current scripts point at a hardcoded source directory (`K:\ALL MILITARY TMS`) — update the `test_dir` path in `backend/detect_format.py` / `backend/extract_pdf_text.py` before running, or point them at your own document set.

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
