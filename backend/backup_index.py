"""
Trigger a full Meilisearch dump (every index, restorable into a fresh
instance) — see README's "Backing up the search index" section.

Previously there was no backup/restore path for the search index at all
(finding #50): data/meilisearch/ is gitignored, holds no version history,
and a bad re-run or disk failure had no documented recovery.

Usage:
    python backend/backup_index.py
"""
import time

from config import MEILISEARCH_URL, logger
from search_index import get_client


def create_dump(client=None, poll_interval_seconds=2, timeout_seconds=300):
    """
    Trigger a dump and wait for it to finish. Returns the dump's status
    dict from Meilisearch (includes its final on-disk location as `dumpUid`
    — Meilisearch names the file `<dumpUid>.dump` inside its configured
    dumps directory, default `./dumps` relative to wherever the server
    process runs).
    """
    client = client or get_client()
    task = client.create_dump()
    deadline = time.monotonic() + timeout_seconds

    while True:
        finished = client.get_task(task.task_uid)
        if finished.status in ("succeeded", "failed", "canceled"):
            return finished
        if time.monotonic() > deadline:
            raise TimeoutError(f"Dump did not finish within {timeout_seconds}s (last status: {finished.status})")
        time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print(f"MEILISEARCH DUMP - {MEILISEARCH_URL}")
    print("=" * 70)

    try:
        result = create_dump()
    except Exception as exc:
        logger.exception("Dump failed")
        print(f"\n✗ Dump failed: {exc}")
        raise SystemExit(1)

    if result.status != "succeeded":
        print(f"\n✗ Dump task finished with status '{result.status}': {result.error}")
        raise SystemExit(1)

    dump_uid = getattr(result, "details", None)
    dump_uid = dump_uid.get("dumpUid") if isinstance(dump_uid, dict) else None
    print("\n✓ Dump complete.")
    if dump_uid:
        print(f"  File: <meilisearch dumps directory>/{dump_uid}.dump")
    print("  Restore by starting Meilisearch with --import-dump <path to that file>.")
