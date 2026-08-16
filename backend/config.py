"""
Shared configuration for TM Search Engine backend scripts.

Paths are resolved in this order (highest priority first):
  1. A CLI argument explicitly passed to a script
  2. An environment variable (loaded from a .env file if present)
  3. A sensible repo-relative default

Set TM_SOURCE_DIR / TM_OUTPUT_DIR in a .env file (see .env.example) or in
your shell environment to point these scripts at your own document set.
"""
import logging
import os
import sys
from pathlib import Path
from urllib.parse import urlparse


def ensure_utf8_stdio():
    """
    Make stdout/stderr encode as UTF-8.

    On Windows, a console's default encoding is usually a legacy codepage
    (e.g. cp1252) rather than UTF-8. print()-ing characters like the ✓/✗/⚠
    used throughout these scripts then raises UnicodeEncodeError and kills
    the whole run. TextIOWrapper.reconfigure (Python 3.7+) lets us switch
    the already-open stdout/stderr streams to UTF-8 without needing
    PYTHONUTF8=1 or PYTHONIOENCODING set externally.

    Safe to call unconditionally: reconfigure() is a no-op cost-wise if
    already UTF-8, and any failure (e.g. a stream that isn't a real
    TextIOWrapper, such as under some test runners) is swallowed rather
    than crashing the import.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


ensure_utf8_stdio()

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv is optional; env vars set another way still work.
    pass

logger = logging.getLogger("tm_search_engine")
if not logger.handlers:
    # Basic stderr logging so failures in the API and CLI scripts leave a
    # trail beyond uvicorn's bare access log (see audit finding #44). Callers
    # that want structured/production logging (JSON, log aggregation, etc.)
    # can reconfigure this logger's handlers without touching call sites.
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

# Repo root = parent of the backend/ directory this file lives in.
REPO_ROOT = Path(__file__).resolve().parent.parent

# Directory to scan for source documents (PDFs, DOCX, images).
SOURCE_DIR = os.environ.get("TM_SOURCE_DIR", "")

# Directory where extraction results are written.
OUTPUT_DIR = os.environ.get("TM_OUTPUT_DIR", str(REPO_ROOT / "data" / "extracted"))

# Meilisearch connection. No master key by default, matching a local
# `meilisearch --env development` instance with auth disabled — set
# MEILISEARCH_API_KEY once a real (production or master) key is in use.
MEILISEARCH_URL = os.environ.get("MEILISEARCH_URL", "http://127.0.0.1:7700")
MEILISEARCH_API_KEY = os.environ.get("MEILISEARCH_API_KEY") or None
# Deliberately a single, fixed index name — this is a single-corpus,
# single-tenant design (finding #46). Splitting document sets (e.g.
# separate TM libraries by branch or classification) isn't supported by
# changing this value alone: routers/search.py hardcodes MEILISEARCH_INDEX
# as the index it queries, and there's no per-request or per-user routing
# to a different one. Extending to multiple indexes would mean threading
# an index selector through the API (as a path segment or an allow-listed
# query param — never an arbitrary client-supplied index name, to avoid
# exposing indexes the caller shouldn't reach) and through
# extract_documents.py/index_documents.py's --output-dir /
# TM_OUTPUT_DIR-per-corpus story. Out of scope until an actual second
# corpus exists to design against.
MEILISEARCH_INDEX = os.environ.get("MEILISEARCH_INDEX", "documents")


def _is_local_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in ("127.0.0.1", "localhost", "::1")


# Fail loud (rather than silently querying an unauthenticated production
# Meilisearch) if MEILISEARCH_URL points off-box with no API key configured.
# Set TM_ALLOW_INSECURE_MEILISEARCH=1 to explicitly opt out (e.g. a trusted
# internal network that terminates auth elsewhere).
if (
    not MEILISEARCH_API_KEY
    and not _is_local_url(MEILISEARCH_URL)
    and os.environ.get("TM_ALLOW_INSECURE_MEILISEARCH") != "1"
):
    raise RuntimeError(
        f"MEILISEARCH_URL ({MEILISEARCH_URL}) is not localhost, but no "
        "MEILISEARCH_API_KEY is set. Refusing to start against an "
        "unauthenticated remote Meilisearch instance. Set "
        "MEILISEARCH_API_KEY, or TM_ALLOW_INSECURE_MEILISEARCH=1 to "
        "override if this is intentional."
    )

# Backend API access control. Unset (the default) leaves the API open,
# which is only appropriate on a single developer machine — see README.
# Set TM_API_KEY to require `X-API-Key: <value>` on every /api/* request.
API_KEY = os.environ.get("TM_API_KEY") or None

# Frontend origins allowed to call the API via CORS, comma-separated.
# Defaults to the local Vite dev server. Set CORS_ORIGINS for any other
# deployment (e.g. "https://tm-search.example.internal").
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if origin.strip()
]

# Extraction safety limits (finding #19) — a pathological source file
# (huge page count or huge file size) shouldn't be able to hang or OOM an
# extraction run. Set to 0 to disable a given limit.
MAX_PDF_PAGES = int(os.environ.get("TM_MAX_PDF_PAGES", "2000"))
MAX_PDF_FILE_SIZE_MB = int(os.environ.get("TM_MAX_PDF_FILE_SIZE_MB", "500"))

# Rate limit for /api/search — requests per client IP per window (finding
# #45). Set TM_SEARCH_RATE_LIMIT=0 to disable (e.g. hermetic tests).
SEARCH_RATE_LIMIT = int(os.environ.get("TM_SEARCH_RATE_LIMIT", "60"))
SEARCH_RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("TM_SEARCH_RATE_LIMIT_WINDOW_SECONDS", "60"))
