"""
Unified, incremental extraction across PDFs, DOCX, and standalone images.

extract_pdf_text.py's own CLI is PDF-only and always reprocesses everything
from scratch (fine for a quick manual test run). This script is the
recommended entry point for a real corpus:

  - Dispatches each file to extract_pdf_text.py / extract_docx_text.py /
    extract_image_text.py based on detect_format.py's classification
    (finding #5 — DOCX/image files were previously never extracted at all).
  - Skips files that haven't changed (by mtime + size) since they were last
    successfully extracted, tracked in an on-disk manifest (finding #21 —
    every prior run rescanned and re-extracted everything unconditionally).
  - Writes results to disk after every file, not just at the end, so a
    crash or Ctrl-C partway through a large batch doesn't lose already-done
    work — re-running picks up where it left off via the manifest
    (finding #6 — no batch/background run had any resumability).

Usage:
    python backend/extract_documents.py
    python backend/extract_documents.py "K:\\ALL MILITARY TMS" --max-files 200
    python backend/extract_documents.py --force   # ignore the manifest, redo everything
"""
import argparse
import json
from pathlib import Path

from config import SOURCE_DIR, OUTPUT_DIR, logger
from detect_format import scan_directory
from extract_pdf_text import extract_pdf_text
from extract_docx_text import extract_docx_text
from extract_image_text import extract_image_text

RESULTS_FILENAME = "extraction_test_results.json"
MANIFEST_FILENAME = "extraction_manifest.json"

EXTRACTORS = {
    "pdf": extract_pdf_text,
    "docx": extract_docx_text,
    "image": extract_image_text,
}


def _load_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read %s (%s) — starting fresh.", path, exc)
        return default


def _file_fingerprint(path: Path):
    stat = path.stat()
    return {"mtime": stat.st_mtime, "size": stat.st_size}


def _write_progress(results_by_path, manifest, output_dir):
    """Flush current state to disk. Called after every file so progress
    survives an interruption partway through a large batch."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = [results_by_path[k] for k in sorted(results_by_path)]
    with open(output_dir / RESULTS_FILENAME, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    with open(output_dir / MANIFEST_FILENAME, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def extract_directory(source_dir, output_dir, max_files=None, force=False):
    """
    Extract every PDF/DOCX/image file under source_dir, incrementally.

    max_files caps how many files are *newly processed* this run (files
    skipped because they're unchanged don't count against it) — so
    resuming a big corpus in bounded chunks doesn't silently shrink each
    chunk by however many files happened to already be up to date.

    Returns (results_by_path, stats) where stats has counts of processed/
    skipped/failed files.
    """
    source_dir = Path(source_dir)
    output_dir = Path(output_dir)

    manifest = {} if force else _load_json(output_dir / MANIFEST_FILENAME, {})
    existing_results = _load_json(output_dir / RESULTS_FILENAME, [])
    results_by_path = {r["filepath"]: r for r in existing_results if "filepath" in r}

    scan_results, total_scanned = scan_directory(source_dir)
    all_files = [(p, "pdf") for p in scan_results["pdf"]]
    all_files += [(p, "docx") for p in scan_results["docx"]]
    all_files += [(p, "image") for p in scan_results["image"]]

    print(f"\nFound {len(all_files)} extractable file(s) of {total_scanned} scanned in {source_dir}.")

    stats = {"processed": 0, "skipped_unchanged": 0, "failed": 0}

    for filepath_str, kind in all_files:
        if max_files is not None and stats["processed"] >= max_files:
            print(f"\nReached --max-files {max_files}; stopping (re-run to continue).")
            break

        path = Path(filepath_str)
        try:
            fingerprint = _file_fingerprint(path)
        except OSError as exc:
            logger.warning("Could not stat %s (%s) — skipping.", path, exc)
            continue

        cached = manifest.get(filepath_str)
        unchanged = (
            cached is not None
            and cached.get("mtime") == fingerprint["mtime"]
            and cached.get("size") == fingerprint["size"]
            and filepath_str in results_by_path
        )
        if unchanged:
            stats["skipped_unchanged"] += 1
            continue

        print(f"  Extracting ({kind}): {path.name}...", end=" ")
        result = EXTRACTORS[kind](path)
        results_by_path[filepath_str] = result
        manifest[filepath_str] = {**fingerprint, "status": result["status"]}
        stats["processed"] += 1

        if result["status"] == "success":
            ocr_note = f", {len(result.get('ocr_pages_used', []))} page(s) via OCR" if result.get("ocr_pages_used") else ""
            print(f"✓ ({result.get('text_length', 0)} chars{ocr_note})")
        else:
            stats["failed"] += 1
            print(f"✗ {result.get('error')}")

        # Flush after every file — this is the whole point of the
        # manifest: a crash on file 400/1000 shouldn't cost files 1-399.
        _write_progress(results_by_path, manifest, output_dir)

    if stats["skipped_unchanged"]:
        print(f"\n  ({stats['skipped_unchanged']} file(s) unchanged since last run, skipped — use --force to redo them.)")

    return results_by_path, stats


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract text from PDFs, DOCX, and images in a directory — "
                     "incrementally, with resumability across runs."
    )
    parser.add_argument(
        "source_dir",
        nargs="?",
        default=SOURCE_DIR,
        help="Directory to scan (defaults to TM_SOURCE_DIR from env/.env)",
    )
    parser.add_argument(
        "--output-dir",
        default=OUTPUT_DIR,
        help="Directory to write extraction_test_results.json / extraction_manifest.json to "
             "(defaults to TM_OUTPUT_DIR from env/.env)",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Cap on newly-processed files this run (unchanged/skipped files don't count). "
             "Default: no cap — process everything found.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore the manifest and re-extract every file, even unchanged ones.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    print("\n" + "=" * 70)
    print(f"DOCUMENT EXTRACTION - {args.source_dir or '(no source directory set)'}")
    print("=" * 70)

    if not args.source_dir:
        print("\n✗ No source directory provided.")
        print("Pass one as an argument, or set TM_SOURCE_DIR in your environment or .env file.")
        raise SystemExit(1)
    if not Path(args.source_dir).exists():
        print(f"\n✗ Directory not found: {args.source_dir}")
        raise SystemExit(1)

    results_by_path, stats = extract_directory(
        args.source_dir, args.output_dir, max_files=args.max_files, force=args.force
    )

    total_chars = sum(r.get("text_length", 0) for r in results_by_path.values() if r["status"] == "success")
    print(f"\n✓ Extraction complete. Results saved to: {Path(args.output_dir) / RESULTS_FILENAME}")
    print("\nThis run:")
    print(f"  Processed: {stats['processed']} (failed: {stats['failed']})")
    print(f"  Skipped (unchanged): {stats['skipped_unchanged']}")
    print(f"\nTotals across all runs so far:")
    print(f"  Documents indexed-ready: {len(results_by_path)}")
    print(f"  Total characters extracted: {total_chars:,}")
