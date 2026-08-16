import argparse
import os
from pathlib import Path
from collections import defaultdict

from config import SOURCE_DIR

def detect_format(file_path):
    """
    Detect file format and return classification.
    Returns: 'pdf', 'docx', 'image', 'unsupported'
    """
    file_path = Path(file_path)
    extension = file_path.suffix.lower()

    # PDF files
    if extension == '.pdf':
        return 'pdf'

    # Word documents
    if extension in ['.docx', '.doc']:
        return 'docx'

    # Images (OCR candidates)
    if extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']:
        return 'image'

    # Unsupported
    return 'unsupported'

def scan_directory(directory):
    """
    Scan directory and classify all files by format.
    Returns: dict with format counts and file lists
    """
    directory = Path(directory)
    results = {
        'pdf': [],
        'docx': [],
        'image': [],
        'unsupported': []
    }

    total_files = 0

    for file_path in directory.rglob('*'):
        if file_path.is_file():
            total_files += 1
            file_format = detect_format(file_path)
            results[file_format].append(str(file_path))

    return results, total_files

def print_results(results, total_files, directory):
    """Print formatted results"""
    print("\n" + "=" * 70)
    print(f"FORMAT DETECTION RESULTS - {directory}")
    print("=" * 70)
    print(f"\nTotal files scanned: {total_files}")
    print(f"\nClassification Summary:")
    print(f"  PDFs:       {len(results['pdf']):5d} files")
    print(f"  Word Docs:  {len(results['docx']):5d} files")
    print(f"  Images:     {len(results['image']):5d} files")
    print(f"  Unsupported: {len(results['unsupported']):5d} files")

    print(f"\n✓ Extraction Priority (PDF + DOCX + Images):")
    extraction_count = len(results['pdf']) + len(results['docx']) + len(results['image'])
    print(f"  Total extractable: {extraction_count} files")

    if results['pdf']:
        print(f"\nSample PDFs (first 5):")
        for pdf in results['pdf'][:5]:
            print(f"  - {Path(pdf).name}")

    if results['docx']:
        print(f"\nSample Word Docs (first 5):")
        for docx in results['docx'][:5]:
            print(f"  - {Path(docx).name}")

    if results['image']:
        print(f"\nSample Images (first 5):")
        for img in results['image'][:5]:
            print(f"  - {Path(img).name}")

def parse_args():
    parser = argparse.ArgumentParser(description="Scan a directory and classify files by format.")
    parser.add_argument(
        "source_dir",
        nargs="?",
        default=SOURCE_DIR,
        help="Directory to scan (defaults to TM_SOURCE_DIR from env/.env)",
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    test_dir = args.source_dir

    if not test_dir:
        print("✗ No source directory provided.")
        print("Pass one as an argument, or set TM_SOURCE_DIR in your environment or .env file.")
    elif os.path.exists(test_dir):
        results, total = scan_directory(test_dir)
        print_results(results, total, test_dir)
    else:
        print(f"✗ Directory not found: {test_dir}")
