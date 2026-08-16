import pdfplumber
import json
from pathlib import Path
from datetime import datetime

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

            # Extract text from all pages
            full_text = ""
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    full_text += f"\n--- PAGE {page_num} ---\n{text}"

            return {
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
                'text_length': len(full_text),
                'text_preview': full_text[:500] + "..." if len(full_text) > 500 else full_text,
                'extracted_at': datetime.now().isoformat()
            }

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
            print(f"✓ ({result['num_pages']} pages, {result['text_length']} chars)")
        else:
            print(f"✗ Error: {result['error']}")

    return results

def save_results(results, output_file):
    """Save extraction results to JSON"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    test_dir = "K:\\ALL MILITARY TMS"

    print("\n" + "=" * 70)
    print("PDF TEXT EXTRACTION TEST - K:\\ALL MILITARY TMS")
    print("=" * 70)

    if Path(test_dir).exists():
        print(f"\nScanning for PDFs in {test_dir}...")
        print("Extracting first 5 PDFs for testing...")

        results = extract_from_directory(test_dir, max_files=5)

        # Save results
        output_file = "K:\\tm_search_engine\\data\\extracted\\extraction_test_results.json"
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
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
        print(f"✗ Directory not found: {test_dir}")
