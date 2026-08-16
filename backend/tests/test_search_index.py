"""
Tests for search_index.py — the Meilisearch write path (index creation,
document id derivation, pruning). Previously untested (finding #9); these
specifically cover the critical-tier fixes for findings #24, #25, #41.
"""
import meilisearch
import pytest

import search_index


# ---------------------------------------------------------------------------
# document_id (finding #24) — stable across a relocated TM_SOURCE_DIR
# ---------------------------------------------------------------------------

def test_document_id_stable_when_source_dir_moves(monkeypatch, tmp_path):
    old_root = tmp_path / "old_root"
    new_root = tmp_path / "new_root"
    (old_root / "manuals").mkdir(parents=True)
    (new_root / "manuals").mkdir(parents=True)
    old_file = old_root / "manuals" / "hydraulic_pump.pdf"
    new_file = new_root / "manuals" / "hydraulic_pump.pdf"
    old_file.write_bytes(b"fake pdf")
    new_file.write_bytes(b"fake pdf")

    monkeypatch.setattr(search_index, "SOURCE_DIR", str(old_root))
    id_before_move = search_index.document_id(old_file)

    monkeypatch.setattr(search_index, "SOURCE_DIR", str(new_root))
    id_after_move = search_index.document_id(new_file)

    assert id_before_move == id_after_move


def test_document_id_differs_for_different_relative_paths(monkeypatch, tmp_path):
    root = tmp_path / "root"
    (root / "a").mkdir(parents=True)
    (root / "b").mkdir(parents=True)
    file_a = root / "a" / "manual.pdf"
    file_b = root / "b" / "manual.pdf"
    file_a.write_bytes(b"a")
    file_b.write_bytes(b"b")
    monkeypatch.setattr(search_index, "SOURCE_DIR", str(root))

    assert search_index.document_id(file_a) != search_index.document_id(file_b)


def test_document_id_falls_back_outside_source_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(search_index, "SOURCE_DIR", str(tmp_path / "unrelated"))
    outside_file = tmp_path / "elsewhere.pdf"
    # Should not raise even though outside_file isn't under SOURCE_DIR.
    assert search_index.document_id(outside_file)


# ---------------------------------------------------------------------------
# ensure_index (finding #41) — tolerates a concurrent create-index race
# ---------------------------------------------------------------------------

class _FakeSettingsIndex:
    def __init__(self, current_settings=None):
        self._current_settings = current_settings or {}
        self.update_settings_calls = 0

    def get_settings(self):
        return self._current_settings

    def update_settings(self, settings):
        self.update_settings_calls += 1
        self._current_settings.update(settings)
        return _FakeTask()

    def get_documents(self, params):
        return {"results": []}

    def delete_documents(self, ids):
        return _FakeTask()


class _FakeTask:
    task_uid = 1


class _FakeFinishedTask:
    status = "succeeded"


def _not_found_error():
    class _Resp:
        status_code = 404
        text = '{"message": "not found", "code": "index_not_found", "link": null, "type": "invalid_request"}'
    return meilisearch.errors.MeilisearchApiError("error", _Resp())


def _already_exists_error():
    class _Resp:
        status_code = 409
        text = '{"message": "already exists", "code": "index_already_exists", "link": null, "type": "invalid_request"}'
    return meilisearch.errors.MeilisearchApiError("error", _Resp())


class _RacingClient:
    """Simulates another process creating the index between get_index and create_index."""

    def __init__(self):
        self.get_index_calls = 0

    def get_index(self, name):
        self.get_index_calls += 1
        if self.get_index_calls == 1:
            raise _not_found_error()
        return _FakeSettingsIndex()

    def create_index(self, name, opts):
        raise _already_exists_error()  # someone else won the race

    def wait_for_task(self, task_uid):
        return _FakeFinishedTask()


def test_ensure_index_tolerates_concurrent_create(monkeypatch):
    client = _RacingClient()
    # Should not raise, despite create_index() reporting index_already_exists.
    index = search_index.ensure_index(client=client)
    assert index is not None


# ---------------------------------------------------------------------------
# ensure_index settings diffing (finding #26)
# ---------------------------------------------------------------------------

class _SettingsClient:
    def __init__(self, index):
        self._index = index

    def get_index(self, name):
        return self._index

    def wait_for_task(self, task_uid):
        return _FakeFinishedTask()


def test_ensure_index_skips_update_when_settings_already_match():
    index = _FakeSettingsIndex(current_settings=dict(search_index.INDEX_SETTINGS))
    client = _SettingsClient(index)

    search_index.ensure_index(client=client)

    assert index.update_settings_calls == 0


def test_ensure_index_applies_update_when_settings_differ():
    index = _FakeSettingsIndex(current_settings={"searchableAttributes": ["filename"]})
    client = _SettingsClient(index)

    search_index.ensure_index(client=client)

    assert index.update_settings_calls == 1
    assert index._current_settings["searchableAttributes"] == search_index.INDEX_SETTINGS["searchableAttributes"]


class _AlwaysBrokenClient(_RacingClient):
    def create_index(self, name, opts):
        raise _not_found_error()  # a genuinely different error — must propagate


def test_ensure_index_reraises_unrelated_create_errors():
    client = _AlwaysBrokenClient()
    with pytest.raises(meilisearch.errors.MeilisearchApiError):
        search_index.ensure_index(client=client)


# ---------------------------------------------------------------------------
# prune_missing_documents (finding #25)
# ---------------------------------------------------------------------------

class _FakeDoc:
    def __init__(self, doc_id):
        self.id = doc_id


class _PruneIndex(_FakeSettingsIndex):
    def __init__(self, doc_ids):
        super().__init__()
        self._doc_ids = doc_ids
        self.deleted = None

    def get_documents(self, params):
        offset, limit = params["offset"], params["limit"]
        page = self._doc_ids[offset: offset + limit]
        return {"results": [_FakeDoc(d) for d in page]}

    def delete_documents(self, ids):
        self.deleted = list(ids)
        return _FakeTask()


class _PruneClient:
    def __init__(self, index):
        self._index = index

    def get_index(self, name):
        return self._index

    def wait_for_task(self, task_uid):
        return _FakeFinishedTask()


def test_prune_removes_documents_not_in_known_set(monkeypatch, tmp_path):
    root = tmp_path
    kept_file = root / "kept.pdf"
    kept_file.write_bytes(b"kept")
    monkeypatch.setattr(search_index, "SOURCE_DIR", str(root))

    kept_id = search_index.document_id(kept_file)
    stale_id = "a" * 40  # not derivable from any known file

    index = _PruneIndex([kept_id, stale_id])
    client = _PruneClient(index)

    pruned_count, task = search_index.prune_missing_documents([kept_file], client=client)

    assert pruned_count == 1
    assert index.deleted == [stale_id]


def test_prune_no_op_when_nothing_stale(tmp_path, monkeypatch):
    root = tmp_path
    kept_file = root / "kept.pdf"
    kept_file.write_bytes(b"kept")
    monkeypatch.setattr(search_index, "SOURCE_DIR", str(root))
    kept_id = search_index.document_id(kept_file)

    index = _PruneIndex([kept_id])
    client = _PruneClient(index)

    pruned_count, task = search_index.prune_missing_documents([kept_file], client=client)

    assert pruned_count == 0
    assert task is None
    assert index.deleted is None


# ---------------------------------------------------------------------------
# to_document (finding #22) — PDF/DOCX metadata actually gets indexed
# ---------------------------------------------------------------------------

def test_to_document_indexes_title_and_author():
    extraction_result = {
        "filepath": "C:\\docs\\hydraulic_pump.pdf",
        "filename": "hydraulic_pump.pdf",
        "text": "some body text",
        "metadata": {"title": "Hydraulic Pump Manual", "author": "Dept. of the Army", "subject": "N/A"},
    }

    doc = search_index.to_document(extraction_result)

    assert doc["title"] == "Hydraulic Pump Manual"
    assert doc["author"] == "Dept. of the Army"


def test_to_document_normalizes_na_placeholder():
    extraction_result = {
        "filepath": "C:\\docs\\no_metadata.pdf",
        "filename": "no_metadata.pdf",
        "text": "some body text",
        "metadata": {"title": "N/A", "author": "N/A", "subject": "N/A"},
    }

    doc = search_index.to_document(extraction_result)

    assert doc["title"] == ""
    assert doc["author"] == ""


# ---------------------------------------------------------------------------
# index_extraction_results (finding #9) — the actual Meilisearch write path
# ---------------------------------------------------------------------------

class _IndexingIndex(_FakeSettingsIndex):
    def __init__(self):
        super().__init__(current_settings=dict(search_index.INDEX_SETTINGS))
        self.added_documents = None

    def add_documents(self, documents):
        self.added_documents = documents
        return _FakeTask()


class _IndexingClient:
    def __init__(self, index):
        self._index = index

    def get_index(self, name):
        return self._index

    def wait_for_task(self, task_uid):
        return _FakeFinishedTask()


def test_index_extraction_results_skips_failed_extractions():
    index = _IndexingIndex()
    client = _IndexingClient(index)
    results = [
        {"status": "success", "filepath": "a.pdf", "filename": "a.pdf", "text": "hello"},
        {"status": "error", "filepath": "b.pdf", "filename": "b.pdf", "error": "boom"},
    ]

    indexed_count, skipped_count, task = search_index.index_extraction_results(results, client=client)

    assert indexed_count == 1
    assert skipped_count == 1
    assert len(index.added_documents) == 1
    assert index.added_documents[0]["filepath"] == "a.pdf"


def test_index_extraction_results_no_op_when_nothing_succeeded():
    index = _IndexingIndex()
    client = _IndexingClient(index)
    results = [{"status": "error", "filepath": "b.pdf", "filename": "b.pdf", "error": "boom"}]

    indexed_count, skipped_count, task = search_index.index_extraction_results(results, client=client)

    assert indexed_count == 0
    assert skipped_count == 1
    assert task is None
    assert index.added_documents is None


class _FailingTask:
    status = "failed"
    error = "disk full"


class _FailingIndexingClient(_IndexingClient):
    def wait_for_task(self, task_uid):
        return _FailingTask()


def test_index_extraction_results_raises_on_failed_task():
    index = _IndexingIndex()
    client = _FailingIndexingClient(index)
    results = [{"status": "success", "filepath": "a.pdf", "filename": "a.pdf", "text": "hello"}]

    with pytest.raises(RuntimeError, match="disk full"):
        search_index.index_extraction_results(results, client=client)


def test_to_document_handles_missing_metadata_key():
    # extract_docx_text.py-style results without a "metadata" key at all
    # shouldn't blow up building the document.
    extraction_result = {
        "filepath": "C:\\docs\\bare.pdf",
        "filename": "bare.pdf",
        "text": "some body text",
    }

    doc = search_index.to_document(extraction_result)

    assert doc["title"] == ""
    assert doc["author"] == ""
