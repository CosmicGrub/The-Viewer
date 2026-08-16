"""
Search endpoints.

Stubbed out for now: the Meilisearch indexing pipeline (see README
roadmap) hasn't been wired up yet. This documents the intended
request/response shape and returns 501 rather than a fake empty result
set, so callers get an honest signal.
"""
from typing import List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchResult(BaseModel):
    document_id: str
    filename: str
    snippet: str
    score: float


class SearchResponse(BaseModel):
    query: str
    total_hits: int
    results: List[SearchResult]


@router.get("", response_model=SearchResponse)
def search(q: str = Query(..., min_length=1, description="Search query text")):
    """
    Search indexed documents.

    Not yet implemented. Raises 501 until a Meilisearch index is wired up
    behind this route.
    """
    raise HTTPException(
        status_code=501,
        detail=(
            "Search is not implemented yet — the Meilisearch indexing "
            "pipeline hasn't been wired up."
        ),
    )
