"""
Shared configuration for TM Search Engine backend scripts.

Paths are resolved in this order (highest priority first):
  1. A CLI argument explicitly passed to a script
  2. An environment variable (loaded from a .env file if present)
  3. A sensible repo-relative default

Set TM_SOURCE_DIR / TM_OUTPUT_DIR in a .env file (see .env.example) or in
your shell environment to point these scripts at your own document set.
"""
import os
import sys
from pathlib import Path


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
MEILISEARCH_INDEX = os.environ.get("MEILISEARCH_INDEX", "documents")
