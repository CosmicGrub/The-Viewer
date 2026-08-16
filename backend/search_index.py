"""
Meilisearch integration: index management and document indexing for
extracted TM text (see extract_pdf_text.py, which produces the source
data this module pushes into the search index).

Used by both index_documents.py (the CLI indexing script) and
routers/search.py (the /api/search endpoint).
"""
import hashlib

import meilisearch

from config import MEILISEARCH_URL, MEILISEARCH_API_KEY, MEILISEARCH_INDEX

# Kept intentionally small for Phase 1: full text is searchable, filename
# gets a slight boost by being listed first. Extend as real query patterns
# emerge (e.g. filtering by num_pages, sorting by extracted_at).
INDEX_SETTINGS = {
    "searchableAttributes": ["filename", "text"],
    "filterableAttributes": ["num_pages", "extracted_at"],
    "sortableAttributes": ["extracted_at", "file_size"],
}


def get_client():
    """Return a Meilisearch client configured from config.py / env vars."""
    return meilisearch.Client(MEILISEARCH_URL, MEILISEARCH_API_KEY)


def document_id(filepath):
    """
    Derive a stable Meilisearch primary key from a filepath.

    Meilisearch document ids may only contain [a-zA-Z0-9_-], so a raw
    Windows path (backslashes, colons, spaces) can't be used directly.
    Hashing keeps the id stable across re-indexing runs, so re-extracting
    and re-indexing the same file updates its existing document instead
    of creating a duplicate.
    """
    return hashlib.sha1(str(filepath).encode("utf-8")).hexdigest()


def to_document(extraction_result):
    """Convert one extract_pdf_text.py result dict into a Meilisearch document."""
    return {
        "id": document_id(extraction_result["filepath"]),
        "filename": extraction_result["filename"],
        "filepath": extraction_result["filepath"],
        "text": extraction_result.get("text", ""),
        "num_pages": extraction_result.get("num_pages"),
        "file_size": extraction_result.get("file_size"),
        "ocr_pages_used": extraction_result.get("ocr_pages_used", []),
        "extracted_at": extraction_result.get("extracted_at"),
    }


def ensure_index(client=None):
    """
    Get the documents index, creating it (and applying INDEX_SETTINGS) if
    it doesn't exist yet. Safe to call repeatedly — both creation and the
    settings update are idempotent, so this also doubles as "make sure the
    index is configured correctly" for callers that don't care whether it
    already existed.
    """
    client = client or get_client()
    try:
        index = client.get_index(MEILISEARCH_INDEX)
    except meilisearch.errors.MeilisearchApiError as exc:
        if exc.code != "index_not_found":
            raise
        task = client.create_index(MEILISEARCH_INDEX, {"primaryKey": "id"})
        client.wait_for_task(task.task_uid)
        index = client.get_index(MEILISEARCH_INDEX)

    settings_task = index.update_settings(INDEX_SETTINGS)
    client.wait_for_task(settings_task.task_uid)
    return index


def index_extraction_results(results, client=None):
    """
    Index a list of extract_pdf_text.py result dicts (as loaded from
    extraction_test_results.json). Entries with status != 'success' are
    skipped — a failed extraction has no text to search.

    Returns (indexed_count, skipped_count, finished_task_or_None).
    Raises RuntimeError if Meilisearch reports the indexing task failed.
    """
    client = client or get_client()
    index = ensure_index(client)

    documents = [to_document(r) for r in results if r.get("status") == "success"]
    skipped = len(results) - len(documents)

    if not documents:
        return 0, skipped, None

    task = index.add_documents(documents)
    finished = client.wait_for_task(task.task_uid)
    if finished.status != "succeeded":
        raise RuntimeError(f"Meilisearch indexing task failed: {finished.error}")

    return len(documents), skipped, finished
