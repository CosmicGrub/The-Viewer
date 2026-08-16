"""
Extract text from standalone image files (scans saved directly as
PNG/JPEG/TIFF/BMP/GIF, not embedded in a PDF) via OCR.

Reuses the same preprocessing and Tesseract tuning as the PDF OCR fallback
in extract_pdf_text.py, so a scanned page indexes the same whether it
arrived as an image-only PDF or a bare image file. See
extract_documents.py for the orchestrator that dispatches to this,
extract_pdf_text.py, and extract_docx_text.py (audit finding #5 — image
files were classified by detect_format.py but never actually extracted).
"""
from pathlib import Path
from datetime import datetime, timezone

from PIL import Image
import pytesseract

from config import logger
from extract_pdf_text import TESSERACT_AVAILABLE, TESSERACT_CONFIG, OCR_LANGUAGE, preprocess_for_ocr


def extract_image_text(image_path):
    """
    OCR a standalone image file.
    Returns: dict with text content and metadata, same shape as
    extract_pdf_text.extract_pdf_text() so both flow through the same
    indexing path unmodified.
    """
    image_path = Path(image_path)

    if not TESSERACT_AVAILABLE:
        return {
            'status': 'error',
            'filename': image_path.name,
            'filepath': str(image_path),
            'error': "tesseract binary not found on PATH — required to OCR standalone images",
        }

    try:
        with Image.open(image_path) as image:
            processed = preprocess_for_ocr(image)
            text = pytesseract.image_to_string(processed, lang=OCR_LANGUAGE, config=TESSERACT_CONFIG)

        return {
            'status': 'success',
            'filename': image_path.name,
            'filepath': str(image_path),
            'file_size': image_path.stat().st_size,
            'num_pages': 1,
            'metadata': {'title': 'N/A', 'author': 'N/A', 'subject': 'N/A'},
            'text': text,
            'text_length': len(text),
            'ocr_pages_used': [1] if text.strip() else [],
            'extracted_at': datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.exception("Failed to extract %s", image_path)
        return {
            'status': 'error',
            'filename': image_path.name,
            'filepath': str(image_path),
            'error': str(e),
        }
