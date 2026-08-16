import argparse
import io
import pdfplumber
import json
import pymupdf
import pytesseract
from pathlib import Path
from datetime import datetime

from config import SOURCE_DIR, OUTPUT_DIR

# Resolution (DPI) to rasterize pages at before handing them to Tesseract.
# Higher = more accurate OCR but slower / more memory.
OCR_DPI = 300


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
    return pytesseract.image_to_string(image)

def extract_pdf_text(pdf_path):
    """
    Extract text from PDF file.
    Returns: dict with text content and metadata
    """
    pdf_path = Path(pdf_path)

    try:
        with pdfplumber.open(pdf_path) as pdf:
            metadata = pdf.metadata
            num_pages = len(pdf.pages)

            # Extract text from all pages, falling back to OCR for pages
            # with no extractable text (e.g. scanned/image-only pages).
            full_text = ""
            ocr_pages = []
            ocr_doc = None
            ocr_error = None

            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()

                if not text or not text.strip():
                    if ocr_error is None:
                        try:
                            if ocr_doc is None:
                                ocr_doc = pymupdf.open(pdf_path)
                            text = ocr_page(ocr_doc, page_num)
                            if text and text.strip():
                                ocr_pages.append(page_num)
                        except Exception as ocr_exc:
                            # Keep going without OCR (e.g. Tesseract not
                            # installed) rather than failing the whole file.
                            ocr_error = str(ocr_exc)
                            text = None

                if text:
                    full_text += f"\n--- PAGE {page_num} ---\n{text}"

            if ocr_doc is not None:
                ocr_doc.close()

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
                'text_preview': full_text[:500] + "..." if len(full_text) > 500 else full_text,
                'ocr_pages_used': ocr_pages,
                'extracted_at': datetime.now().isoformat()
            }
            if ocr_error:
                result['ocr_error'] = ocr_error

            return result

    except Exception as e:
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
            if result.get('ocr_error'):
                print(f"    ⚠ OCR unavailable for some pages: {result['ocr_error']}")
        else:
            print(f"✗ Error: {result['error']}")

    return results

def save_results(results, output_file):
    """Save extraction results to JSON"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

def parse_args():
    parser = argparse.ArgumentParser(description="Extract text from PDFs in a directory.")
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
