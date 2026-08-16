"""
TM Search Engine API.

Exposes liveness/status endpoints plus a real Meilisearch-backed search
route (see routers/search.py and search_index.py). Requires a running
Meilisearch server and a built index — see README's "Running Meilisearch"
and "Building the search index" sections.

Run from the repo root:
    uvicorn main:app --reload --app-dir backend

or from backend/:
    cd backend
    uvicorn main:app --reload

Either way, docs are served at /docs (Swagger UI) and /redoc.
"""
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from config import API_KEY, CORS_ORIGINS, SOURCE_DIR, OUTPUT_DIR, logger
from routers import search

app = FastAPI(
    title="TM Search Engine API",
    description="Search API for indexed Technical Manuals (TMs).",
    version="0.1.0",
)

# Allowed frontend origins, driven by CORS_ORIGINS (defaults to the local
# Vite dev server — see config.py). Set CORS_ORIGINS before deploying
# anywhere beyond a developer's own machine.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Structured request logging (finding #44). uvicorn's own access log
    exists, but nothing here previously logged through the app's own
    logger — meaning a deployment that redirects/filters uvicorn's output
    separately from application logs had no request trail at all, and
    failures had no way to be flagged (>=500) distinctly from normal
    traffic (<500) in that log stream.
    """
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = (time.monotonic() - start) * 1000
    log = logger.warning if response.status_code >= 500 else logger.info
    log(
        "%s %s -> %d (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


app.include_router(search.router)


@app.get("/", tags=["meta"])
def root():
    """Basic info endpoint — confirms the API is up and points at the docs."""
    return {
        "name": app.title,
        "version": app.version,
        "docs": "/docs",
    }


@app.get("/health", tags=["meta"])
def health():
    """Health check for uptime monitors / deploy checks."""
    return {"status": "ok"}


@app.get("/api/status", tags=["meta"])
def status():
    """
    Reports whether required configuration is present, so a misconfigured
    environment (e.g. TM_SOURCE_DIR unset) is obvious from an HTTP call
    rather than a confusing downstream failure.
    """
    return {
        "source_dir_configured": bool(SOURCE_DIR),
        "source_dir": SOURCE_DIR or None,
        "output_dir": OUTPUT_DIR,
        "api_key_required": API_KEY is not None,
    }
