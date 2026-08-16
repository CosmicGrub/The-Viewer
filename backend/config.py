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
from pathlib import Path

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
