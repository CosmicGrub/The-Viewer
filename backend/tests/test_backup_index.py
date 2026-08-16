"""
Tests for backup_index.py (finding #50).
"""
import pytest

import backup_index


class _FakeTask:
    task_uid = 7


class _FakeTaskStatus:
    def __init__(self, status, error=None, details=None):
        self.status = status
        self.error = error
        self.details = details


class _FakeClient:
    def __init__(self, statuses):
        self._statuses = list(statuses)
        self.dumps_created = 0

    def create_dump(self):
        self.dumps_created += 1
        return _FakeTask()

    def get_task(self, task_uid):
        # Return the next queued status, repeating the last one if polled
        # more times than expected (keeps a timeout test from IndexError-ing).
        if len(self._statuses) > 1:
            return self._statuses.pop(0)
        return self._statuses[0]


def test_create_dump_waits_for_success(monkeypatch):
    client = _FakeClient([
        _FakeTaskStatus("enqueued"),
        _FakeTaskStatus("processing"),
        _FakeTaskStatus("succeeded", details={"dumpUid": "20260816-120000000"}),
    ])
    monkeypatch.setattr(backup_index.time, "sleep", lambda s: None)

    result = backup_index.create_dump(client=client, poll_interval_seconds=0)

    assert result.status == "succeeded"
    assert client.dumps_created == 1


def test_create_dump_surfaces_failure(monkeypatch):
    client = _FakeClient([_FakeTaskStatus("failed", error="disk full")])
    monkeypatch.setattr(backup_index.time, "sleep", lambda s: None)

    result = backup_index.create_dump(client=client, poll_interval_seconds=0)

    assert result.status == "failed"
    assert result.error == "disk full"


def test_create_dump_times_out(monkeypatch):
    client = _FakeClient([_FakeTaskStatus("processing")])
    times = iter([0, 1, 100, 200])
    monkeypatch.setattr(backup_index.time, "monotonic", lambda: next(times))
    monkeypatch.setattr(backup_index.time, "sleep", lambda s: None)

    with pytest.raises(TimeoutError):
        backup_index.create_dump(client=client, poll_interval_seconds=0, timeout_seconds=5)
