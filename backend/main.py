"""
TM Search Engine API — FastAPI application skeleton.

This is a starting point, not a finished API: it exposes liveness/status
endpoints and a stubbed-out search route so the shape of the service is in
place before the Meilisearch indexing pipeline (see README roadmap) is
wired up behind it.

Run from the repo root:
    uvicorn main:app --reload --app-dir backend

or from backend/:
    cd backend
    uvicorn main:app --reload

Either way, docs are served at /docs (Swagger UI) and /redoc.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import SOURCE_DIR, OUTPUT_DIR
from routers import search

app = FastAPI(
    title="TM Search Engine API",
    description="Search API for indexed Technical Manuals (TMs).",
    version="0.1.0",
)

# Local frontend dev server origins. Tighten this (or drive it from an env
# var) before deploying anywhere beyond a developer's own machine.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    }
