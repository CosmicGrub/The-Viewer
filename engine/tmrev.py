"""tmrev.py -- technical-manual REVISION / currency tracking (R13). A mechanic must never work from a
superseded manual. Army TMs carry a base publication date and incremental CHANGES ('C1', 'Change 3'); a
higher change number (or a later date) is more current. This module parses that revision info and, given a
corpus, flags which copy of a TM is CURRENT and which are superseded.

parse_revision() and compare_revisions() are pure and unit-testable; currency() runs over the documents
table. Read-only."""

from __future__ import annotations
import re, sqlite3

_TM = re.compile(r"\bTM\s*[\dA-Z]+(?:-[\dA-Z]+)+", re.I)
_CHANGE = re.compile(r"\b(?:CHANGE|CHG|C)\s*[.:]?\s*(\d{1,2})\b", re.I)
_MONTHS = {m: i for i, m in enumerate(
    ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST",
     "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"], start=1)}
_DATE = re.compile(r"\b(\d{1,2})\s+([A-Z]+)\s+(\d{4})\b", re.I)


def _norm_tm(s):
    return re.sub(r"\s+", "", (s or "").upper())


def parse_revision(text):
    """Extract {tm_number, change_no, date, date_sort} from a TM header/title/page. Missing pieces are None.
    change_no defaults to 0 (base issue) when a TM number is present but no change is stated."""
    text = text or ""
    tm = _TM.search(text)
    tm_number = _norm_tm(tm.group(0)) if tm else None
    ch = _CHANGE.search(text)
    change_no = int(ch.group(1)) if ch else (0 if tm_number else None)
    d = _DATE.search(text)
    date = date_sort = None
    if d:
        day, mon, yr = int(d.group(1)), d.group(2).upper(), int(d.group(3))
        mi = _MONTHS.get(mon)
        if mi and 1 <= day <= 31 and 1900 <= yr <= 2100:
            date = "%02d %s %d" % (day, mon.title(), yr)
            date_sort = yr * 10000 + mi * 100 + day
    return {"tm_number": tm_number, "change_no": change_no, "date": date, "date_sort": date_sort}


def compare_revisions(a, b):
    """Order two parsed revisions of the SAME TM. Returns >0 if a is NEWER, <0 if older, 0 if equal/unknown.
    Change number dominates; date breaks ties."""
    ca, cb = a.get("change_no"), b.get("change_no")
    if ca is not None and cb is not None and ca != cb:
        return 1 if ca > cb else -1
    da, db = a.get("date_sort"), b.get("date_sort")
    if da is not None and db is not None and da != db:
        return 1 if da > db else -1
    return 0


def currency(db_path, tm_number):
    """For a TM base number, find every copy in the corpus and mark the CURRENT one + supersessions.
    Returns {tm, current record, superseded list, n}. Best-effort over the documents table."""
    base = _norm_tm(tm_number)
    if not base:
        return {"tm": tm_number, "current": None, "superseded": [], "n": 0}
    # v1.13.4: con=None + finally -- same close()-inside-try shape as the other leaks fixed today; the
    # documents table can throw mid-ingest/dedup (viewer.db briefly unreadable during an os.replace()),
    # and the except used to return without closing, leaking a handle on the primary index db.
    con = None
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True); con.row_factory = sqlite3.Row
        # v1.13.5: exact match on the full normalized TM number, not a 12-char prefix. For standard Army TM
        # numbering (e.g. "TM 9-2320-280-24P" vs "TM 9-2320-280-20") a short prefix is exactly the shared
        # weapon-system/model segment, so it used to match every manual TYPE for that platform (operator,
        # unit maintenance, parts, direct-support, ...) instead of just other copies/revisions of THIS one
        # manual. The title LIKE stays a substring fallback for docs whose tm_number field is missing/dirty.
        rows = con.execute("SELECT id, tm_number, title FROM documents WHERE REPLACE(UPPER(tm_number),' ','') = ? "
                           "OR REPLACE(UPPER(title),' ','') LIKE ? LIMIT 50", (base, "%" + base + "%")).fetchall()
    except Exception as e:
        return {"tm": tm_number, "current": None, "superseded": [], "n": 0, "error": str(e)}
    finally:
        if con is not None:
            con.close()
    cand = []
    for r in rows:
        rev = parse_revision((r["tm_number"] or "") + " " + (r["title"] or ""))
        rev["doc"] = r["id"]; rev["title"] = r["title"]
        cand.append(rev)
    if not cand:
        return {"tm": base, "current": None, "superseded": [], "n": 0}
    cand.sort(key=lambda x: (x.get("change_no") or 0, x.get("date_sort") or 0), reverse=True)
    return {"tm": base, "current": cand[0], "superseded": cand[1:], "n": len(cand)}


# --------------------------------------------------------------------------- #
# self-test: `python tmrev.py`                                                #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    a = parse_revision("TM 9-2320-280-20 CHANGE 3  15 MARCH 2014")
    assert a["tm_number"] == "TM9-2320-280-20" and a["change_no"] == 3, a
    assert a["date"] == "15 March 2014" and a["date_sort"] == 20140315, a
    print("parse_revision OK ->", a)

    base = parse_revision("TM 9-2320-280-20  1 JANUARY 2010")
    assert base["change_no"] == 0, base
    assert compare_revisions(a, base) > 0, "change 3 must be newer than base"
    assert compare_revisions(base, a) < 0
    print("compare_revisions OK -> change 3 newer than base")

    older = parse_revision("TM 9-2320-280-20 CHANGE 1  1 JUNE 2011")
    assert compare_revisions(a, older) > 0
    # date tie-break when change numbers equal
    x = parse_revision("TM 1  1 JANUARY 2020"); y = parse_revision("TM 1  1 JANUARY 2018")
    assert compare_revisions(x, y) > 0, "later date newer"
    print("date tie-break OK")

    # regression: currency() must match only OTHER COPIES of the same TM, not sibling manual types that
    # share a weapon-system/model prefix (e.g. -24P parts manual vs -20 unit-maintenance manual for the
    # same platform). A prefix-based match used to conflate them and wrongly label one "superseded".
    import os, tempfile
    _d = tempfile.mkdtemp(prefix="tmrev_")
    _db = os.path.join(_d, "v.db")
    _con = sqlite3.connect(_db)
    _con.execute("CREATE TABLE documents(id INTEGER PRIMARY KEY, tm_number TEXT, title TEXT)")
    _con.executemany("INSERT INTO documents(id, tm_number, title) VALUES (?,?,?)", [
        (1, "TM 9-2320-280-24P", "Parts Manual"),
        (2, "TM 9-2320-280-20", "Unit Maintenance Manual"),                       # different manual, same platform
        (3, "TM 9-2320-280-24P", "Parts Manual CHANGE 1  1 JUNE 2015"),           # a newer copy of doc 1
    ])
    _con.commit(); _con.close()

    res = currency(_db, "TM 9-2320-280-24P")
    assert res["n"] == 2, "expected only the two -24P copies, got n=%r (%r)" % (res["n"], res)
    _ids = {res["current"]["doc"]} | {s["doc"] for s in res["superseded"]}
    assert _ids == {1, 3}, "wrong doc set matched -> %r" % (_ids,)
    assert 2 not in _ids, "must not treat the sibling -20 manual as a copy/revision of the -24P manual"
    assert res["current"]["doc"] == 3, "the CHANGE 1 copy must rank current over the base copy"
    print("currency OK -> matched only same-TM copies, excluded sibling manual type ->", res["tm"])
    assert parse_revision("no tm here")["tm_number"] is None
    print("tmrev self-test PASS")

# END OF FILE
