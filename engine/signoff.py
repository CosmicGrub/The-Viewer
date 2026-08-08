"""signoff.py -- human sign-off + immutable audit trail (R13: extracted -> HUMAN-VERIFIED). A machine can
extract a torque value; only a subject-matter expert can VOUCH for it. This module gives low-confidence
values (torque / NSN / procedure / dimension) a review queue: an SME approves, rejects, or overrides, and
the value becomes 'verified & locked' with a permanent who / what / when record.

The store is APPEND-ONLY by design (the audit requirement): every action is a new event row; nothing is
ever updated or deleted, so the full history is always recoverable. Current status = the latest event for
a (kind, key). Its own sidecar (signoff.db), never the corpus. Pure stdlib; unit-testable."""

from __future__ import annotations
import os, sqlite3, threading, time

_DDL = """
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,
  kind TEXT NOT NULL,          -- torque | nsn | procedure | dimension | ...
  key TEXT NOT NULL,           -- the subject (e.g. 'HMMWV mounting bolt' or an NSN)
  action TEXT NOT NULL,        -- submit | approve | reject | override
  value TEXT,                  -- proposed / corrected value
  source TEXT,                 -- where it came from (doc/page)
  by TEXT,                     -- who acted
  note TEXT
);
CREATE INDEX IF NOT EXISTS ix_ev_kk ON events(kind, key, id);
"""

_ACTIONS = {"submit", "approve", "reject", "override"}
_STATUS = {"submit": "pending", "approve": "verified", "reject": "rejected", "override": "verified"}


_SCHEMA_DONE = set()             # db paths whose DDL has been ensured this process (v1.13: was every open)
_SCHEMA_LOCK = threading.Lock()


def _con(db_path, ro=False):
    """v1.13: read paths open mode=ro (no accidental writes, no file creation); the DDL runs ONCE per
    db path per process instead of on every open (it used to run executescript on every read too)."""
    if ro:
        con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
        con.row_factory = sqlite3.Row
        return con
    fresh = not os.path.exists(db_path)      # deleted underneath us (tests) -> re-ensure schema
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    if fresh or db_path not in _SCHEMA_DONE:
        with _SCHEMA_LOCK:
            con.executescript(_DDL)          # idempotent (IF NOT EXISTS)
            _SCHEMA_DONE.add(db_path)
    return con


def _emit(db_path, kind, key, action, value=None, source=None, by=None, note=None):
    if action not in _ACTIONS:
        raise ValueError("bad action %r" % action)
    con = _con(db_path)
    try:
        cur = con.execute("INSERT INTO events(ts,kind,key,action,value,source,by,note) VALUES(?,?,?,?,?,?,?,?)",
                          (int(time.time()), kind, key, action, None if value is None else str(value),
                           source, by, note))
        con.commit()
        return cur.lastrowid
    finally:
        con.close()


def submit(db_path, kind, key, value, source=None, by="system", note=None):
    """Queue a low-confidence value for SME review. Returns the event id."""
    return _emit(db_path, kind, key, "submit", value=value, source=source, by=by, note=note)


def decide(db_path, kind, key, action, by, value=None, note=None):
    """Record an SME decision (approve / reject / override). Append-only. Returns the event id."""
    if action not in ("approve", "reject", "override"):
        raise ValueError("decision must be approve/reject/override")
    return _emit(db_path, kind, key, action, value=value, source=None, by=by, note=note)


def status_of(db_path, kind, key):
    """Current status for a (kind,key): the latest event decides. Returns {status, value, by, ts, action}."""
    if not os.path.exists(db_path):
        return {"status": "none"}
    con = _con(db_path, ro=True)
    try:
        r = con.execute("SELECT * FROM events WHERE kind=? AND key=? ORDER BY id DESC LIMIT 1",
                        (kind, key)).fetchone()
        if not r:
            return {"status": "none"}
        return {"status": _STATUS.get(r["action"], "pending"), "action": r["action"], "value": r["value"],
                "by": r["by"], "ts": r["ts"], "note": r["note"]}
    except sqlite3.OperationalError:
        return {"status": "none"}            # db exists but no events table yet (nothing recorded)
    finally:
        con.close()


def queue(db_path, status="pending", limit=200):
    """List subjects currently in a given status (default: pending review)."""
    if not os.path.exists(db_path):
        return []
    con = _con(db_path, ro=True)
    try:
        rows = con.execute("SELECT kind,key,MAX(id) AS mid FROM events GROUP BY kind,key").fetchall()
        out = []
        for r in rows:
            last = con.execute("SELECT * FROM events WHERE id=?", (r["mid"],)).fetchone()
            st = _STATUS.get(last["action"], "pending")
            if st == status:
                out.append({"kind": last["kind"], "key": last["key"], "value": last["value"],
                            "source": last["source"], "by": last["by"], "ts": last["ts"], "status": st})
            if len(out) >= limit:
                break
        return out
    except sqlite3.OperationalError:
        return []                            # db exists but no events table yet
    finally:
        con.close()


def audit(db_path, kind, key):
    """Full immutable event history for a subject (oldest first)."""
    if not os.path.exists(db_path):
        return []
    con = _con(db_path, ro=True)
    try:
        return [dict(r) for r in con.execute("SELECT * FROM events WHERE kind=? AND key=? ORDER BY id",
                                             (kind, key)).fetchall()]
    except sqlite3.OperationalError:
        return []                            # db exists but no events table yet
    finally:
        con.close()


# --------------------------------------------------------------------------- #
# self-test: `python signoff.py`                                              #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import tempfile
    db = os.path.join(tempfile.gettempdir(), "signoff_test.db")
    if os.path.exists(db):
        os.remove(db)

    submit(db, "torque", "HMMWV mount bolt", "35 ft-lb", source="TM-A p.4-12", by="ocr")
    assert status_of(db, "torque", "HMMWV mount bolt")["status"] == "pending"
    assert len(queue(db, "pending")) == 1, queue(db, "pending")

    decide(db, "torque", "HMMWV mount bolt", "override", by="SFC Diaz", value="40 ft-lb", note="matches -20 change 3")
    s = status_of(db, "torque", "HMMWV mount bolt")
    assert s["status"] == "verified" and s["value"] == "40 ft-lb" and s["by"] == "SFC Diaz", s
    assert queue(db, "pending") == [], "should be cleared from pending"
    print("signoff submit->override OK -> %s by %s (%s)" % (s["value"], s["by"], s["status"]))

    # audit trail is complete + append-only (2 events, in order)
    hist = audit(db, "torque", "HMMWV mount bolt")
    assert len(hist) == 2 and hist[0]["action"] == "submit" and hist[1]["action"] == "override", hist
    print("audit trail OK -> %d immutable events" % len(hist))

    # a rejection flips status and is itself recorded
    submit(db, "nsn", "alt-2920", "2920-01-000-0000", by="ocr")
    decide(db, "nsn", "alt-2920", "reject", by="SME", note="wrong FSC")
    assert status_of(db, "nsn", "alt-2920")["status"] == "rejected"
    assert len(audit(db, "nsn", "alt-2920")) == 2
    print("reject + trail OK")
    print("signoff self-test PASS")

# END OF FILE
