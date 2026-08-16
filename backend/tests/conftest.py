"""
Pytest configuration for backend/tests/.

The backend scripts (config.py, main.py, detect_format.py, ...) use flat
imports like `from config import ...` rather than package-relative
imports, matching how they're run directly (`python backend/main.py`,
`uvicorn main:app --app-dir backend`). Pytest's default import mode only
puts this tests/ directory on sys.path, not its parent — so without this,
`from main import app` in test_main.py would fail regardless of which
directory `pytest` is invoked from. Add backend/ explicitly.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
