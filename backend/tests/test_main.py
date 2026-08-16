"""
Tests for the FastAPI app skeleton (backend/main.py).

Run with `pytest` from the backend/ directory (or repo root with
`pytest backend/tests`) — see conftest.py for the sys.path setup that
makes `from main import app` resolve.
"""
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "TM Search Engine API"
    assert body["docs"] == "/docs"


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_status_reports_config_shape():
    response = client.get("/api/status")
    assert response.status_code == 200
    body = response.json()
    assert "source_dir_configured" in body
    assert "output_dir" in body


def test_search_not_yet_implemented():
    # Documents the current stub behavior: search isn't wired up to
    # Meilisearch yet, so it should fail loudly (501) rather than return
    # a fake empty result set.
    response = client.get("/api/search", params={"q": "hydraulic pump"})
    assert response.status_code == 501


def test_search_requires_query_param():
    response = client.get("/api/search")
    assert response.status_code == 422
