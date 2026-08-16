"""
Meilisearch integration: index management and document indexing for
extracted TM text (see extract_pdf_text.py, which produces the source
data this module pushes into the search index).

Used by both index_documents.py (the CLI indexing script) and
routers/search.py (the /api/search endpoint).
"""
import hashlib
from pathlib import Path

import meilisearch

from config import MEILISEARCH_URL, MEILISEARCH_API_KEY, MEILISEARCH_INDEX, SOURCE_DIR, logger

# searchableAttributes order sets Meilisearch's attribute-ranking priority
# (earlier = weighted higher) — title/filename matches rank above a hit
# buried in body text. `title` comes from PDF/DOCX metadata (finding #22:
# it was extracted but never indexed) and is often a more readable, more
# reliable manual name than the filename on disk.
#
# rankingRules default order is
# ["words","typo","proximity","attribute","sort","exactness"]. Technical
# manuals are dense with part numbers and NSN-style codes (e.g.
# "5310-01-234-5678") where a fuzzy/typo-tolerant match is usually a
# *wrong* result, not a helpful one — so `exactness` is promoted ahead of
# `typo` here (finding #47: this was never tuned from the library default).
#
# typoTolerance.minWordSizeForTypos raises the bar for when typo-tolerance
# even kicks in: the library default (5/9 chars) happily "corrects" a
# 5-character part-number segment into a different one. Segments in codes
# like "5310-01-234-5678" (Meilisearch tokenizes on the hyphens) are
# usually 2-4 characters — well under even the raised threshold here — so
# they're matched exactly by default, while genuine prose words still get
# reasonable typo tolerance (finding #23).
INDEX_SETTINGS = {
    "searchableAttributes": ["title", "filename", "text"],
    "filterableAttributes": ["num_pages", "extracted_at"],
    "sortableAttributes": ["extracted_at", "file_size"],
    "rankingRules": ["words", "exactness", "proximity", "attribute", "sort", "typo"],
    "typoTolerance": {"minWordSizeForTypos": {"oneTypo": 6, "twoTypos": 10}},
}

# Batch size for paging through index.get_documents() in prune_missing_documents.
_PRUNE_PAGE_SIZE = 1000


def get_client():
    """Return a Meilisearch client configured from config.py / env vars."""
    return meilisearch.Client(MEILISEARCH_URL, MEILISEARCH_API_KEY)


def _id_key_for_path(filepath) -> str:
    """
    Normalize a filepath into the string that document_id() hashes.

    Uses the path relative to TM_SOURCE_DIR (with forward slashes) when the
    file lives under it, so a document's id stays stable if the source
    corpus is remounted at a different absolute location (a different
    drive letter, a different mount point, moved to another machine) —
    only the relative structure has to stay the same. Falls back to the
    raw absolute path for files outside SOURCE_DIR (e.g. one-off files
    passed directly to extract_pdf_text.py).

    This is what actually re-keys re-indexed files onto the *same*
    document instead of silently duplicating the whole index (finding
    #24) — without it, moving the source drive alone would do that.
    """
    path = Path(filepath)
    if SOURCE_DIR:
        try:
            rel = path.resolve().relative_to(Path(SOURCE_DIR).resolve())
            return str(rel).replace("\\", "/")
        except (OSError, ValueError):
            pass  # not under SOURCE_DIR (or SOURCE_DIR itself unresolvable) — fall through
    return str(path)


def document_id(filepath):
    """
    Derive a stable Meilisearch primary key from a filepath.

    Meilisearch document ids may only contain [a-zA-Z0-9_-], so a raw
    Windows path (backslashes, colons, spaces) can't be used directly.
    Hashing keeps the id stable across re-indexing runs, so re-extracting
    and re-indexing the same file updates its existing document instead
    of creating a duplicate.
    """
    return hashlib.sha1(_id_key_for_path(filepath).encode("utf-8")).hexdigest()


def to_document(extraction_result):
    """Convert one extract_pdf_text.py result dict into a Meilisearch document."""
    metadata = extraction_result.get("metadata") or {}
    # Source metadata uses the placeholder "N/A" for an absent field
    # (matching extract_pdf_text.py's PDF-metadata convention) — normalize
    # that to "" so it doesn't literally become searchable/displayed text.
    title = metadata.get("title") or ""
    author = metadata.get("author") or ""
    if title == "N/A":
        title = ""
    if author == "N/A":
        author = ""

    return {
        "id": document_id(extraction_result["filepath"]),
        "filename": extraction_result["filename"],
        "filepath": extraction_result["filepath"],
        "title": title,
        "author": author,
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

    Tolerates a concurrent caller winning the create-index race: if two
    processes both see index_not_found and both call create_index(), the
    loser's create_index() raises index_already_exists rather than an
    index that's simply there — that's treated as success, not an error
    (finding #41).
    """
    client = client or get_client()
    try:
        index = client.get_index(MEILISEARCH_INDEX)
    except meilisearch.errors.MeilisearchApiError as exc:
        if exc.code != "index_not_found":
            raise
        try:
            task = client.create_index(MEILISEARCH_INDEX, {"primaryKey": "id"})
            client.wait_for_task(task.task_uid)
        except meilisearch.errors.MeilisearchApiError as create_exc:
            if create_exc.code != "index_already_exists":
                raise
        index = client.get_index(MEILISEARCH_INDEX)

    # Only push a settings update (and wait on the resulting task) if the
    # live settings actually differ from INDEX_SETTINGS. Previously this
    # ran on every single call — including every index_documents.py
    # invocation — triggering a full settings-reprocessing task each time
    # even when nothing had changed (finding #26).
    current = index.get_settings()
    if not _settings_match(current, INDEX_SETTINGS):
        settings_task = index.update_settings(INDEX_SETTINGS)
        client.wait_for_task(settings_task.task_uid)
    return index


def _settings_match(current, desired) -> bool:
    """True if every key in `desired` already matches `current`'s value.

    `current` (from index.get_settings()) carries many more keys than
    INDEX_SETTINGS sets explicitly — only compare the ones we actually
    manage, so unrelated Meilisearch defaults don't cause a spurious
    "changed" result forever.
    """
    current = current if isinstance(current, dict) else vars(current)
    for key, value in desired.items():
        if current.get(key) != value:
            return False
    return True


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
        logger.error("Meilisearch indexing task failed: %s", finished.error)
        raise RuntimeError(f"Meilisearch indexing task failed: {finished.error}")

    return len(documents), skipped, finished


def prune_missing_documents(known_filepaths, client=None):
    """
    Delete indexed documents whose source file isn't in known_filepaths.

    `known_filepaths` must be the *complete* current set of extractable
    files (e.g. from detect_format.scan_directory() over the whole
    TM_SOURCE_DIR) — not just the files a single extraction batch happened
    to process. Passing a partial list here would prune documents that are
    still valid but simply weren't part of this run, which is why
    index_documents.py only calls this from its explicit --prune path
    (which does a full directory scan first), never automatically after
    every indexing run.

    Without this, deleting/moving a source file leaves its old entry
    searchable forever (finding #25). Returns (pruned_count, finished_task_or_None).
    """
    client = client or get_client()
    index = ensure_index(client)
    known_ids = {document_id(p) for p in known_filepaths}

    stale_ids = []
    offset = 0
    while True:
        page = index.get_documents({"offset": offset, "limit": _PRUNE_PAGE_SIZE, "fields": ["id"]})
        docs = getattr(page, "results", None)
        if docs is None:
            docs = page["results"]
        if not docs:
            break
        for doc in docs:
            doc_id = doc.id if hasattr(doc, "id") else doc["id"]
            if doc_id not in known_ids:
                stale_ids.append(doc_id)
        if len(docs) < _PRUNE_PAGE_SIZE:
            break
        offset += _PRUNE_PAGE_SIZE

    if not stale_ids:
        return 0, None

    task = index.delete_documents(stale_ids)
    finished = client.wait_for_task(task.task_uid)
    if finished.status != "succeeded":
        logger.error("Meilisearch prune task failed: %s", finished.error)
        raise RuntimeError(f"Meilisearch prune task failed: {finished.error}")

    return len(stale_ids), finished
