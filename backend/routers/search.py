"""
Search endpoints, backed by the Meilisearch index built by
index_documents.py (see search_index.py for the shared client/index
helpers both modules use).
"""
from typing import List, Optional

import meilisearch
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from config import MEILISEARCH_URL, MEILISEARCH_INDEX, logger
from search_index import get_client
from security import enforce_search_rate_limit, require_api_key

router = APIRouter(
    prefix="/api/search",
    tags=["search"],
    dependencies=[Depends(require_api_key)],
)

# Longest query string Meilisearch will be asked to search — well beyond
# any real search phrase, just a backstop against unbounded input (finding
# #45; min_length is enforced separately per-route below).
MAX_QUERY_LENGTH = 512

# Length (in words) that cropped snippets are trimmed to around the best
# matching span, via Meilisearch's attributesToCrop/cropLength.
SNIPPET_CROP_LENGTH = 40


class SearchResult(BaseModel):
    document_id: str
    filename: str
    filepath: str
    title: Optional[str] = None
    snippet: str
    score: Optional[float] = None


class SearchResponse(BaseModel):
    query: str
    total_hits: int
    results: List[SearchResult]


class DocumentDetail(BaseModel):
    document_id: str
    filename: str
    filepath: str
    title: Optional[str] = None
    author: Optional[str] = None
    text: str
    num_pages: Optional[int] = None
    file_size: Optional[int] = None
    ocr_pages_used: List[int] = []
    extracted_at: Optional[str] = None


def _meilisearch_error_to_http(exc, *, not_found_detail: str) -> HTTPException:
    """Shared mapping from meilisearch errors to the HTTPException to raise."""
    # Finding #44: these used to only ever surface as an HTTP response —
    # nothing landed in a log a server operator would actually be watching.
    logger.warning("Meilisearch error mapped to HTTP response: %s", exc)
    if isinstance(exc, meilisearch.errors.MeilisearchApiError):
        if exc.code == "index_not_found":
            return HTTPException(
                status_code=503,
                detail=(
                    f"Search index '{MEILISEARCH_INDEX}' doesn't exist yet — "
                    "run `python backend/index_documents.py` after extracting "
                    "documents with extract_pdf_text.py."
                ),
            )
        if exc.code == "document_not_found":
            return HTTPException(status_code=404, detail=not_found_detail)
        return HTTPException(status_code=503, detail=f"Meilisearch error: {exc.message}")
    return HTTPException(
        status_code=503,
        detail=f"Could not reach Meilisearch at {MEILISEARCH_URL}: {exc.message}",
    )


@router.get("", response_model=SearchResponse, dependencies=[Depends(enforce_search_rate_limit)])
def search(
    q: str = Query(..., min_length=1, max_length=MAX_QUERY_LENGTH, description="Search query text"),
    limit: int = Query(20, ge=1, le=100, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Results to skip, for pagination"),
    min_pages: Optional[int] = Query(None, ge=0, description="Only include documents with at least this many pages"),
    max_pages: Optional[int] = Query(None, ge=0, description="Only include documents with at most this many pages"),
    sort: Optional[str] = Query(
        None,
        pattern="^(relevance|newest|oldest)$",
        description="relevance (default), newest, or oldest (by extracted_at)",
    ),
):
    """
    Full-text search over indexed document text.

    Returns 503 (not 500) when Meilisearch itself is the problem — unreachable,
    or the index hasn't been created yet by index_documents.py — since that's
    an infrastructure/setup issue distinct from a bug in this endpoint.

    Rate-limited per client IP (see security.py / TM_SEARCH_RATE_LIMIT) and,
    if TM_API_KEY is set, requires a matching X-API-Key header.

    min_pages/max_pages/sort expose num_pages/extracted_at — already
    Meilisearch filterableAttributes/sortableAttributes that nothing in
    the API surfaced before (finding #8).
    """
    client = get_client()

    filters = []
    if min_pages is not None:
        filters.append(f"num_pages >= {min_pages}")
    if max_pages is not None:
        filters.append(f"num_pages <= {max_pages}")

    search_params = {
        "limit": limit,
        "offset": offset,
        "attributesToCrop": ["text"],
        "cropLength": SNIPPET_CROP_LENGTH,
        "showRankingScore": True,
    }
    if filters:
        search_params["filter"] = " AND ".join(filters)
    if sort == "newest":
        search_params["sort"] = ["extracted_at:desc"]
    elif sort == "oldest":
        search_params["sort"] = ["extracted_at:asc"]

    try:
        index = client.index(MEILISEARCH_INDEX)
        raw = index.search(q, search_params)
    except (meilisearch.errors.MeilisearchApiError, meilisearch.errors.MeilisearchCommunicationError) as exc:
        raise _meilisearch_error_to_http(exc, not_found_detail="") from exc

    results = [
        SearchResult(
            document_id=hit["id"],
            filename=hit["filename"],
            filepath=hit["filepath"],
            title=hit.get("title") or None,
            snippet=hit.get("_formatted", {}).get("text", hit.get("text", "")),
            score=hit.get("_rankingScore"),
        )
        for hit in raw["hits"]
    ]

    return SearchResponse(
        query=q,
        total_hits=raw.get("estimatedTotalHits", len(results)),
        results=results,
    )


@router.get("/documents/{document_id}", response_model=DocumentDetail)
def get_document(document_id: str):
    """
    Fetch one document's full text and metadata by id.

    Search results deliberately carry only a cropped snippet, not full
    text — indexing full text into every hit would bloat every search
    response for the (usually rare) case a result is actually opened.
    This is the endpoint that backs "open full text" in the frontend.
    """
    client = get_client()

    try:
        index = client.index(MEILISEARCH_INDEX)
        doc = index.get_document(document_id)
    except (meilisearch.errors.MeilisearchApiError, meilisearch.errors.MeilisearchCommunicationError) as exc:
        raise _meilisearch_error_to_http(
            exc, not_found_detail=f"No document with id '{document_id}'."
        ) from exc

    # meilisearch's Document wraps the raw dict with attribute access
    # (doc.id), not dict-style (doc["id"]) — getattr covers fields that
    # might be absent on older/partially-indexed documents.
    return DocumentDetail(
        document_id=doc.id,
        filename=doc.filename,
        filepath=doc.filepath,
        title=getattr(doc, "title", None) or None,
        author=getattr(doc, "author", None) or None,
        text=getattr(doc, "text", ""),
        num_pages=getattr(doc, "num_pages", None),
        file_size=getattr(doc, "file_size", None),
        ocr_pages_used=getattr(doc, "ocr_pages_used", None) or [],
        extracted_at=getattr(doc, "extracted_at", None),
    )
