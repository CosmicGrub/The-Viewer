"""fieldnotes.py -- captured FIELD NOTES / tips on a part or procedure (R13: institutional knowledge that
compounds, with an audit trail). A seasoned mechanic knows things the manual doesn't spell out ('this bolt
seizes -- anti-seize it', 'the -20 change 3 supersedes this torque'). This lets them attach a cited note to
a subject; an SME can ENDORSE it so young mechanics see which tips are vouched for. The store is APPEND-ONLY
(same discipline as signoff.py): notes are never edited or deleted, endorsements are their own events, so the
full history is always recoverable.

Its own sidecar (notes.db). Pure stdlib; unit-testable."""

from __future__ import annotations
import os, sqlite3, time

_DDL = """
CREATE TABLE IF NOT EXISTS notes(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,
  subject TEXT NOT NULL,        -- part / procedure the note is about (normalized lower)
  action TEXT NOT NULL,         -- note | endorse | retract
  text TEXT,
  by TEXT,
  cite_doc TEXT,
  cite_page TEXT,
  ref_id INTEGER                -- for endorse/retract: the note id being acted on
);
CREATE INDEX IF NOT EXISTS ix_notes_subj ON notes(subject, id);
"""


def _con(db_path):
    con = sqlite3.connect(db_path); con.row_factory = sqlite3.Row
    con.executescript(_DDL); return con


def _norm(s):
    return " ".join((s or "").lower().split())


def add(db_path, subject, text, by="anonymous", cite_doc=None, cite_page=None):
    if not (subject and (text or "").strip()):
        raise ValueError("subject and text required")
    con = _con(db_path)
    try:
        cur = con.execute("INSERT INTO notes(ts,subject,action,text,by,cite_doc,cite_page) VALUES(?,?,?,?,?,?,?)",
                          (int(time.time()), _norm(subject), "note", text.strip(), by, cite_doc, str(cite_page) if cite_page else None))
        con.commit(); return cur.lastrowid
    finally:
        con.close()


def endorse(db_path, note_id, by, retract=False):
    con = _con(db_path)
    try:
        cur = con.execute("INSERT INTO notes(ts,subject,action,by,ref_id) "
                          "SELECT ?,subject,?,?,? FROM notes WHERE id=? LIMIT 1",
                          (int(time.time()), "retract" if retract else "endorse", by, note_id, note_id))
        con.commit(); return cur.lastrowid
    finally:
        con.close()


def for_subject(db_path, subject, limit=100):
    """List notes for a subject with their endorsement counts (newest first). Retracted notes are marked."""
    if not os.path.exists(db_path):
        return []
    con = _con(db_path)
    try:
        sub = _norm(subject)
        notes = con.execute("SELECT * FROM notes WHERE subject=? AND action='note' ORDER BY id DESC LIMIT ?",
                           (sub, limit)).fetchall()
        out = []
        for n in notes:
            evs = con.execute("SELECT action,by,ts FROM notes WHERE ref_id=? ORDER BY id", (n["id"],)).fetchall()
            endorsers = sorted({e["by"] for e in evs if e["action"] == "endorse"})
            retracted = any(e["action"] == "retract" for e in evs)
            out.append({"id": n["id"], "text": n["text"], "by": n["by"], "ts": n["ts"],
                        "cite_doc": n["cite_doc"], "cite_page": n["cite_page"],
                        "endorsements": len(endorsers), "endorsers": endorsers, "retracted": retracted,
                        "verified": len(endorsers) > 0 and not retracted})
        return out
    finally:
        con.close()


def recent(db_path, limit=30):
    if not os.path.exists(db_path):
        return []
    con = _con(db_path)
    try:
        return [dict(r) for r in con.execute("SELECT subject,text,by,ts FROM notes WHERE action='note' "
                                             "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]
    finally:
        con.close()


# --------------------------------------------------------------------------- #
# self-test: `python fieldnotes.py`                                           #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import tempfile
    db = os.path.join(tempfile.gettempdir(), "fieldnotes_test.db")
    if os.path.exists(db):
        os.remove(db)

    nid = add(db, "HMMWV half-shaft", "This bolt seizes -- use anti-seize on reassembly.", by="SSG Lee", cite_doc="1", cite_page="4-12")
    add(db, "HMMWV half-shaft", "Torque updated by -20 Change 3.", by="SFC Diaz")
    lst = for_subject(db, "HMMWV Half-Shaft")           # case/space-insensitive
    assert len(lst) == 2, lst
    assert lst[0]["text"].startswith("Torque updated"), lst  # newest first
    assert lst[0]["verified"] is False
    print("add + for_subject OK -> %d notes" % len(lst))

    endorse(db, nid, by="SME Warrant")
    endorse(db, nid, by="MSG Cole")
    n = [x for x in for_subject(db, "HMMWV half-shaft") if x["id"] == nid][0]
    assert n["endorsements"] == 2 and n["verified"] is True, n
    print("endorse OK -> %d endorsements, verified=%s" % (n["endorsements"], n["verified"]))

    endorse(db, nid, by="SME Warrant", retract=True)
    n2 = [x for x in for_subject(db, "HMMWV half-shaft") if x["id"] == nid][0]
    assert n2["retracted"] is True and n2["verified"] is False, n2
    print("retract OK -> retracted=%s" % n2["retracted"])
    assert len(recent(db)) == 2
    print("fieldnotes self-test PASS")

# END OF FILE
