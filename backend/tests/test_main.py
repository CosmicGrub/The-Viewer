"""
Tests for the FastAPI app (backend/main.py) and its routers.

Search tests mock the Meilisearch client (routers.search.get_client) so
this suite stays hermetic and fast — it doesn't require a live
Meilisearch server. See backend/index_documents.py and search_index.py
for the real integration, which was verified manually against a live
server (see commit history / README) rather than in this suite.
"""
import json

from fastapi.testclient import TestClient
from meilisearch.errors import MeilisearchApiError, MeilisearchCommunicationError

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


def test_search_requires_query_param():
    # FastAPI validates `q` before the handler runs, so this doesn't need
    # a mocked Meilisearch client.
    response = client.get("/api/search")
    assert response.status_code == 422


class _FakeDocument:
    """Stands in for meilisearch.models.document.Document — attribute access, not dict-style."""

    def __init__(self, **fields):
        self.__dict__.update(fields)


class _FakeIndex:
    """Stands in for meilisearch.Index — returns a canned response or raises."""

    def __init__(self, response=None, exc=None, document=None):
        self._response = response
        self._exc = exc
        self._document = document

    def search(self, q, opt_params):
        if self._exc:
            raise self._exc
        return self._response

    def get_document(self, document_id):
        if self._exc:
            raise self._exc
        return self._document


class _FakeClient:
    """Stands in for meilisearch.Client — just hands back a fixed index."""

    def __init__(self, index):
        self._index = index

    def index(self, name):
        return self._index


def _fake_meilisearch_api_error(code, message="error", status_code=404):
    """Build a MeilisearchApiError the same way the real client would from an HTTP response."""

    class _FakeResponse:
        def __init__(self):
            self.status_code = status_code
            self.text = json.dumps(
                {"message": message, "code": code, "link": None, "type": "invalid_request"}
            )

    return MeilisearchApiError("error", _FakeResponse())


def test_search_success(monkeypatch):
    fake_response = {
        "hits": [
            {
                "id": "abc123",
                "filename": "hydraulic_pump_manual.pdf",
                "filepath": "C:\\docs\\hydraulic_pump_manual.pdf",
                "text": "full page text goes here",
                "_formatted": {"text": "...cropped snippet..."},
                "_rankingScore": 0.87,
            }
        ],
        "estimatedTotalHits": 1,
    }
    monkeypatch.setattr(
        "routers.search.get_client",
        lambda: _FakeClient(_FakeIndex(response=fake_response)),
    )

    response = client.get("/api/search", params={"q": "hydraulic pump"})

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "hydraulic pump"
    assert body["total_hits"] == 1
    assert body["results"] == [
        {
            "document_id": "abc123",
            "filename": "hydraulic_pump_manual.pdf",
            "filepath": "C:\\docs\\hydraulic_pump_manual.pdf",
            "snippet": "...cropped snippet...",
            "score": 0.87,
        }
    ]


def test_search_index_not_found_returns_503(monkeypatch):
    exc = _fake_meilisearch_api_error(code="index_not_found", message="Index `documents` not found.")
    monkeypatch.setattr(
        "routers.search.get_client",
        lambda: _FakeClient(_FakeIndex(exc=exc)),
    )

    response = client.get("/api/search", params={"q": "pump"})

    assert response.status_code == 503
    assert "index_documents.py" in response.json()["detail"]


def test_search_unreachable_meilisearch_returns_503(monkeypatch):
    exc = MeilisearchCommunicationError("Connection refused")
    monkeypatch.setattr(
        "routers.search.get_client",
        lambda: _FakeClient(_FakeIndex(exc=exc)),
    )

    response = client.get("/api/search", params={"q": "pump"})

    assert response.status_code == 503
    assert "Connection refused" in response.json()["detail"]


def test_get_document_success(monkeypatch):
    fake_doc = _FakeDocument(
        id="abc123",
        filename="hydraulic_pump_manual.pdf",
        filepath="C:\\docs\\hydraulic_pump_manual.pdf",
        text="the full extracted text",
        num_pages=3,
        file_size=12345,
        ocr_pages_used=[2],
        extracted_at="2026-08-16T12:00:00",
    )
    monkeypatch.setattr(
        "routers.search.get_client",
        lambda: _FakeClient(_FakeIndex(document=fake_doc)),
    )

    response = client.get("/api/search/documents/abc123")

    assert response.status_code == 200
    assert response.json() == {
        "document_id": "abc123",
        "filename": "hydraulic_pump_manual.pdf",
        "filepath": "C:\\docs\\hydraulic_pump_manual.pdf",
        "text": "the full extracted text",
        "num_pages": 3,
        "file_size": 12345,
        "ocr_pages_used": [2],
        "extracted_at": "2026-08-16T12:00:00",
    }


def test_get_document_not_found_returns_404(monkeypatch):
    exc = _fake_meilisearch_api_error(code="document_not_found", message="Document not found")
    monkeypatch.setattr(
        "routers.search.get_client",
        lambda: _FakeClient(_FakeIndex(exc=exc)),
    )

    response = client.get("/api/search/documents/does-not-exist")

    assert response.status_code == 404
    assert "does-not-exist" in response.json()["detail"]
