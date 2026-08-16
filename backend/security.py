"""
Backend access control: API-key auth and a basic rate limiter.

Both are intentionally simple (no external dependency, no shared state
across processes) — this is a single-instance FastAPI app today. If it's
ever run behind multiple workers/replicas, the rate limiter's in-memory
counters won't be shared between them and should move to something like
Redis; the API-key check has no such limitation.
"""
import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Request

from config import API_KEY, SEARCH_RATE_LIMIT, SEARCH_RATE_LIMIT_WINDOW_SECONDS


def require_api_key(x_api_key: str = Header(default=None)):
    """
    FastAPI dependency enforcing TM_API_KEY (see config.py) on a route.

    A no-op (API stays open) if TM_API_KEY isn't set — that's the default
    for a single developer machine, per the README. Once TM_API_KEY is
    set, every request must carry a matching `X-API-Key` header or gets
    a 401.
    """
    if API_KEY is None:
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key header.")


class _SlidingWindowRateLimiter:
    """Per-client-IP sliding-window request counter."""

    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)

    def check(self, client_id: str) -> None:
        if self.limit <= 0:
            return  # rate limiting disabled
        now = time.monotonic()
        hits = self._hits[client_id]
        cutoff = now - self.window_seconds
        while hits and hits[0] < cutoff:
            hits.popleft()
        if len(hits) >= self.limit:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Rate limit exceeded ({self.limit} requests per "
                    f"{self.window_seconds}s). Try again shortly."
                ),
            )
        hits.append(now)


search_rate_limiter = _SlidingWindowRateLimiter(SEARCH_RATE_LIMIT, SEARCH_RATE_LIMIT_WINDOW_SECONDS)


def enforce_search_rate_limit(request: Request):
    """FastAPI dependency limiting /api/search to SEARCH_RATE_LIMIT req/window per client IP."""
    client_id = request.client.host if request.client else "unknown"
    search_rate_limiter.check(client_id)
