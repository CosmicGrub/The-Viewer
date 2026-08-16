import argparse
import io
import shutil
import pdfplumber
import json
import pymupdf
import pytesseract
from pathlib import Path
from datetime import datetime, timezone

from config import SOURCE_DIR, OUTPUT_DIR, MAX_PDF_PAGES, MAX_PDF_FILE_SIZE_MB, logger

# Resolution (DPI) to rasterize pages at before handing them to Tesseract.
# Higher = more accurate OCR but slower / more memory.
OCR_DPI = 300

# Tesseract page-segmentation/engine mode tuned for dense, multi-column
# technical-manual pages rather than Tesseract's default (which assumes a
# single uniform block of text) — finding #17. --psm 6 treats the page as
# a single block of *uniform* text, which in practice performs better than
# the default (--psm 3, full automatic layout analysis) on manual pages
# that mix body text with tables/diagram labels, without needing per-page
# layout detection. --oem 3 uses the LSTM engine (Tesseract's most
# accurate) with the legacy engine as a fallback.
TESSERACT_CONFIG = "--oem 3 --psm 6"
OCR_LANGUAGE = "eng"

# Whether the tesseract binary is actually on PATH, checked once at import
# time rather than inferred from the first page's OCR failure. Finding #18:
# previously, one failed OCR attempt (for *any* reason, including a
# genuinely corrupt single page) silently disabled OCR for every later page
# in the same file. Now a missing binary is detected up front, and a
# per-page OCR failure no longer blocks OCR on subsequent pages.
TESSERACT_AVAILABLE = shutil.which("tesseract") is not None


class PdfTooLargeError(Exception):
    """Raised when a source PDF exceeds MAX_PDF_PAGES or MAX_PDF_FILE_SIZE_MB.

    Without a ceiling here, a single pathological file (a multi-thousand
    page manual, a multi-gigabyte scan) can hang or OOM an entire
    extraction run — see audit finding #19. Set the corresponding env var
    to 0 to disable a given limit.
    """


def preprocess_for_ocr(image):
    """
    Clean up a rasterized page image before handing it to Tesseract
    (finding #16). Scanned technical manuals are frequently skewed,
    low-contrast, or carry stamps/watermarks that hurt raw OCR accuracy;
    opencv-python is already a project dependency but was unused for this.

    Steps: grayscale -> deskew (via minAreaRect of thresholded content) ->
    adaptive threshold (binarization). Returns a PIL Image; falls back to
    the original image untouched if OpenCV/numpy aren't importable or the
    image is degenerate (e.g. blank page), so this never turns a working
    extraction into a failed one.
    """
    try:
        import cv2
        import numpy as np
        from PIL import Image

        gray = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2GRAY)

        # Deskew: find the minimum-area bounding box of the dark (text)
        # pixels and rotate the page to level it out.
        coords = cv2.findNonZero(cv2.bitwise_not(cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]))
        if coords is not None and len(coords) > 0:
            angle = cv2.minAreaRect(coords)[-1]
            angle = -(90 + angle) if angle < -45 else -angle
            if abs(angle) > 0.1:  # skip the rotation entirely if already ~level
                (h, w) = gray.shape
                matrix = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
                gray = cv2.warpAffine(
                    gray, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
                )

        # Adaptive threshold copes with uneven scan lighting far better
        # than a single global threshold would across a whole manual.
        binarized = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
        )
        return Image.fromarray(binarized)
    except Exception:
        # Preprocessing is a quality improvement, not a correctness
        # requirement — never let it be the reason extraction fails.
        logger.debug("OCR preprocessing skipped, using raw image", exc_info=True)
        return image


def ocr_page(doc, page_number, dpi=OCR_DPI):
    """
    Render a single page of an already-open pymupdf document and run OCR on it.
    `page_number` is 1-indexed, to match pdfplumber's numbering.
    Returns the extracted text (str), or raises on failure.
    """
    page = doc[page_number - 1]
    zoom = dpi / 72  # PDF pages are natively 72 DPI
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
    image_bytes = pixmap.tobytes("png")

    from PIL import Image
    image = Image.open(io.BytesIO(image_bytes))
    image = preprocess_for_ocr(image)
    return pytesseract.image_to_string(image, lang=OCR_LANGUAGE, config=TESSERACT_CONFIG)


def extract_pdf_text(pdf_path):
    """
    Extract text from PDF file.
    Returns: dict with text content and metadata
    """
    pdf_path = Path(pdf_path)

    try:
        if MAX_PDF_FILE_SIZE_MB:
            size_mb = pdf_path.stat().st_size / (1024 * 1024)
            if size_mb > MAX_PDF_FILE_SIZE_MB:
                raise PdfTooLargeError(
                    f"{size_mb:.0f} MB exceeds the {MAX_PDF_FILE_SIZE_MB} MB limit "
                    "(set TM_MAX_PDF_FILE_SIZE_MB to change)."
                )

        with pdfplumber.open(pdf_path) as pdf:
            metadata = pdf.metadata
            num_pages = len(pdf.pages)

            if MAX_PDF_PAGES and num_pages > MAX_PDF_PAGES:
                raise PdfTooLargeError(
                    f"{num_pages} pages exceeds the {MAX_PDF_PAGES}-page limit "
                    "(set TM_MAX_PDF_PAGES to change)."
                )

            # Extract text from all pages, falling back to OCR for pages
            # with no extractable text (e.g. scanned/image-only pages).
            # Accumulated as a list and joined once at the end rather than
            # repeated string concatenation, which was O(n^2) over page
            # count for long manuals (finding #42).
            text_parts = []
            ocr_pages = []
            ocr_doc = None
            ocr_unavailable_reason = None if TESSERACT_AVAILABLE else "tesseract binary not found on PATH"

            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()

                if (not text or not text.strip()) and TESSERACT_AVAILABLE:
                    try:
                        if ocr_doc is None:
                            ocr_doc = pymupdf.open(pdf_path)
                        text = ocr_page(ocr_doc, page_num)
                        if text and text.strip():
                            ocr_pages.append(page_num)
                    except Exception as ocr_exc:
                        # A single page's OCR failing (corrupt page image,
                        # transient rasterization error, ...) no longer
                        # disables OCR for the rest of this file — only a
                        # missing tesseract binary (checked once, above)
                        # does that. Keep going without this page's OCR text.
                        logger.warning("OCR failed on %s page %d: %s", pdf_path.name, page_num, ocr_exc)
                        text = None

                if text:
                    text_parts.append(f"\n--- PAGE {page_num} ---\n{text}")

            if ocr_doc is not None:
                ocr_doc.close()

            full_text = "".join(text_parts)

            result = {
                'status': 'success',
                'filename': pdf_path.name,
                'filepath': str(pdf_path),
                'file_size': pdf_path.stat().st_size,
                'num_pages': num_pages,
                'metadata': {
                    'title': metadata.get('Title', 'N/A') if metadata else 'N/A',
                    'author': metadata.get('Author', 'N/A') if metadata else 'N/A',
                    'subject': metadata.get('Subject', 'N/A') if metadata else 'N/A',
                },
                'text': full_text,
                'text_length': len(full_text),
                'ocr_pages_used': ocr_pages,
                'extracted_at': datetime.now(timezone.utc).isoformat(),
            }
            if ocr_unavailable_reason:
                result['ocr_unavailable_reason'] = ocr_unavailable_reason

            return result

    except Exception as e:
        # Deliberately broad: one malformed/oversized/corrupt file shouldn't
        # abort a whole extraction batch. But it used to fail *silently* —
        # str(e) landed only in the JSON output, with no stack trace
        # anywhere (finding #4). Log the full traceback so a real bug in
        # here (vs. an expected bad input file) is actually diagnosable.
        logger.exception("Failed to extract %s", pdf_path)
        return {
            'status': 'error',
            'filename': pdf_path.name,
            'filepath': str(pdf_path),
            'error': str(e)
        }

def extract_from_directory(directory, max_files=5):
    """
    Extract text from multiple PDFs in directory.
    Limits to max_files for testing.
    """
    directory = Path(directory)
    pdf_files = list(directory.rglob('*.pdf'))[:max_files]

    results = []
    for idx, pdf_file in enumerate(pdf_files, 1):
        print(f"  Extracting {idx}/{len(pdf_files)}: {pdf_file.name}...", end=" ")
        result = extract_pdf_text(pdf_file)
        results.append(result)

        if result['status'] == 'success':
            ocr_note = f", {len(result['ocr_pages_used'])} page(s) via OCR" if result['ocr_pages_used'] else ""
            print(f"✓ ({result['num_pages']} pages, {result['text_length']} chars{ocr_note})")
        else:
            print(f"✗ Error: {result['error']}")

    return results

def save_results(results, output_file):
    """Save extraction results to JSON"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract text from PDFs in a directory. For DOCX/images "
                     "too, and for incremental/resumable extraction across a "
                     "large corpus, use extract_documents.py instead."
    )
    parser.add_argument(
        "source_dir",
        nargs="?",
        default=SOURCE_DIR,
        help="Directory to scan for PDFs (defaults to TM_SOURCE_DIR from env/.env)",
    )
    parser.add_argument(
        "--output-dir",
        default=OUTPUT_DIR,
        help="Directory to write extraction_test_results.json to (defaults to TM_OUTPUT_DIR from env/.env)",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=5,
        help="Maximum number of PDFs to extract (default: 5)",
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    test_dir = args.source_dir

    print("\n" + "=" * 70)
    print(f"PDF TEXT EXTRACTION TEST - {test_dir or '(no source directory set)'}")
    print("=" * 70)

    if not test_dir:
        print("\n✗ No source directory provided.")
        print("Pass one as an argument, or set TM_SOURCE_DIR in your environment or .env file.")
    elif Path(test_dir).exists():
        print(f"\nScanning for PDFs in {test_dir}...")
        print(f"Extracting first {args.max_files} PDFs for testing...")

        results = extract_from_directory(test_dir, max_files=args.max_files)

        # Save results
        output_file = Path(args.output_dir) / "extraction_test_results.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        save_results(results, output_file)

        print(f"\n✓ Extraction complete. Results saved to: {output_file}")

        # Summary
        successful = sum(1 for r in results if r['status'] == 'success')
        failed = sum(1 for r in results if r['status'] == 'error')
        total_chars = sum(r.get('text_length', 0) for r in results if r['status'] == 'success')

        print(f"\nSummary:")
        print(f"  Successful: {successful}/{len(results)}")
        print(f"  Failed: {failed}/{len(results)}")
        print(f"  Total characters extracted: {total_chars:,}")

    else:
        print(f"\n✗ Directory not found: {test_dir}")
