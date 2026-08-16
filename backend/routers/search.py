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
    except meilisearch.errors.MeilisearchApiError as exc:
        if exc.code == "index_not_found":
            raise HTTPException(
                status_code=503,
                detail=(
                    f"Search index '{MEILISEARCH_INDEX}' doesn't exist yet — "
                    "run `python backend/index_documents.py` after extracting "
                    "documents with extract_pdf_text.py."
                ),
            ) from exc
        raise HTTPException(status_code=503, detail=f"Meilisearch error: {exc.message}") from exc
    except meilisearch.errors.MeilisearchCommunicationError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Could not reach Meilisearch at {MEILISEARCH_URL}: {exc.message}",
        ) from exc

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
