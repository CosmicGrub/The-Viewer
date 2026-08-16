"""
Search endpoints, backed by the Meilisearch index built by
index_documents.py (see search_index.py for the shared client/index
helpers both modules use).
"""
from typing import List, Optional

import meilisearch
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from config import MEILISEARCH_URL, MEILISEARCH_INDEX
from search_index import get_client

router = APIRouter(prefix="/api/search", tags=["search"])

# Length (in words) that cropped snippets are trimmed to around the best
# matching span, via Meilisearch's attributesToCrop/cropLength.
SNIPPET_CROP_LENGTH = 40


class SearchResult(BaseModel):
    document_id: str
    filename: str
    filepath: str
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
    text: str
    num_pages: Optional[int] = None
    file_size: Optional[int] = None
    ocr_pages_used: List[int] = []
    extracted_at: Optional[str] = None


def _meilisearch_error_to_http(exc, *, not_found_detail: str) -> HTTPException:
    """Shared mapping from meilisearch errors to the HTTPException to raise."""
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


@router.get("", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1, description="Search query text"),
    limit: int = Query(20, ge=1, le=100, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Results to skip, for pagination"),
):
    """
    Full-text search over indexed document text.

    Returns 503 (not 500) when Meilisearch itself is the problem — unreachable,
    or the index hasn't been created yet by index_documents.py — since that's
    an infrastructure/setup issue distinct from a bug in this endpoint.
    """
    client = get_client()

    try:
        index = client.index(MEILISEARCH_INDEX)
        raw = index.search(
            q,
            {
                "limit": limit,
                "offset": offset,
                "attributesToCrop": ["text"],
                "cropLength": SNIPPET_CROP_LENGTH,
                "showRankingScore": True,
            },
        )
    except (meilisearch.errors.MeilisearchApiError, meilisearch.errors.MeilisearchCommunicationError) as exc:
        raise _meilisearch_error_to_http(exc, not_found_detail="") from exc

    results = [
        SearchResult(
            document_id=hit["id"],
            filename=hit["filename"],
            filepath=hit["filepath"],
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
        text=getattr(doc, "text", ""),
        num_pages=getattr(doc, "num_pages", None),
        file_size=getattr(doc, "file_size", None),
        ocr_pages_used=getattr(doc, "ocr_pages_used", None) or [],
        extracted_at=getattr(doc, "extracted_at", None),
    )
