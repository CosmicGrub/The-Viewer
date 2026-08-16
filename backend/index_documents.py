"""
Push extracted document text into Meilisearch.

Reads the JSON produced by extract_pdf_text.py (a list of per-file result
dicts) and indexes the successful ones. Run extract_pdf_text.py first —
this script doesn't extract anything itself, it only indexes what's
already been extracted.

Usage:
    python backend/index_documents.py
    python backend/index_documents.py path/to/extraction_test_results.json
"""
import argparse
import json
from pathlib import Path

from config import OUTPUT_DIR, SOURCE_DIR, MEILISEARCH_URL, MEILISEARCH_INDEX, logger
from detect_format import scan_directory
from search_index import index_extraction_results, get_client, prune_missing_documents


def parse_args():
    parser = argparse.ArgumentParser(description="Index extracted document text into Meilisearch.")
    parser.add_argument(
        "input_file",
        nargs="?",
        default=str(Path(OUTPUT_DIR) / "extraction_test_results.json"),
        help="Path to the extraction results JSON produced by extract_pdf_text.py "
             "(defaults to TM_OUTPUT_DIR/extraction_test_results.json)",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="After indexing, remove documents whose source file no longer "
             "exists under --source-dir (default: TM_SOURCE_DIR). Does a full "
             "directory scan first, so this is safe to run even when "
             "input_file only covers a partial batch — see finding #25.",
    )
    parser.add_argument(
        "--source-dir",
        default=SOURCE_DIR,
        help="Directory to scan when --prune is set (defaults to TM_SOURCE_DIR).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    input_path = Path(args.input_file)

    print("\n" + "=" * 70)
    print(f"INDEXING - {input_path}")
    print(f"Meilisearch: {MEILISEARCH_URL} (index: {MEILISEARCH_INDEX})")
    print("=" * 70)

    if not input_path.exists():
        print(f"\n✗ Input file not found: {input_path}")
        print("Run extract_pdf_text.py first to produce it.")
        raise SystemExit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    print(f"\nLoaded {len(results)} extraction result(s).")

    try:
        client = get_client()
        client.health()
    except Exception as exc:
        print(f"\n✗ Could not reach Meilisearch at {MEILISEARCH_URL}: {exc}")
        print("Is the server running? e.g. bin/meilisearch.exe --db-path data/meilisearch --http-addr 127.0.0.1:7700")
        raise SystemExit(1)

    try:
        indexed, skipped, task = index_extraction_results(results, client=client)
    except RuntimeError as exc:
        logger.error("Indexing run failed: %s", exc)
        print(f"\n✗ {exc}")
        raise SystemExit(1)

    logger.info("Indexed %d document(s) from %s (%d skipped)", indexed, input_path, skipped)
    print(f"\n✓ Indexed {indexed} document(s).")
    if skipped:
        print(f"  Skipped {skipped} (failed extractions have no text to index).")
    if task is not None:
        print(f"  Task status: {task.status}")

    if args.prune:
        if not args.source_dir:
            print("\n✗ --prune requires --source-dir or TM_SOURCE_DIR to be set.")
            raise SystemExit(1)
        print(f"\nScanning {args.source_dir} to find the current file set...")
        scan_results, total_scanned = scan_directory(args.source_dir)
        known_filepaths = scan_results["pdf"] + scan_results["docx"] + scan_results["image"]
        print(f"  {len(known_filepaths)} extractable file(s) found (of {total_scanned} scanned).")

        pruned, prune_task = prune_missing_documents(known_filepaths, client=client)
        if pruned:
            print(f"✓ Pruned {pruned} stale document(s) no longer present under {args.source_dir}.")
            if prune_task is not None:
                print(f"  Task status: {prune_task.status}")
        else:
            print("✓ No stale documents to prune.")
