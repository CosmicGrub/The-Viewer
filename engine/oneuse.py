#!/usr/bin/env python3
"""oneuse.py -- ONE-TIME-USE / TORQUE-TO-YIELD fastener flags (roadmap #41/#42 -- SAFETY, v1.13.0).

Reusing a torque-to-yield bolt or a "do not reuse" fastener is a classic, dangerous mistake: the TM
says so in a sentence a mechanic can miss. This module finds those sentences for a part/NSN across
the corpus and returns them as structured flags:

    kind in {one_time_use, torque_to_yield, discard_after_removal}

R13 (extractive + cited, never fabricate): every flag carries the manual's EXACT sentence (<=200
chars) plus doc_id / tm / page. Nothing is inferred -- if the TM doesn't say it, no flag exists.
'mentions_query' marks whether the cited sentence itself names the queried part (flags from the
same matched page that don't are still shown, ranked lower, so a human can judge the context).

Retrieval goes through features.corpus.fts_pages (the one shared FTS helper): pooled connection
inside the running app, private read-only connection standalone. Read-only always."""
from __future__ import annotations
import re

from features import corpus as _corpus

# trigger phrases OR'd into the FTS match (hyphens tokenize to spaces in FTS5, so "torque to
# yield" also hits "torque-to-yield"); the query terms are AND'd in so pages are on-subject.
_TRIGGERS = ('("do not reuse" OR "not be reused" OR "one time use" OR discard OR '
             '"torque to yield" OR "additional turn" OR "plus an additional")')

# sentence-level classifiers: kind -> pattern. Purely lexical; the sentence is the evidence.
_PATTERNS = [
    ("one_time_use", re.compile(
        r"one[-\s]?time[-\s]?use|do\s+not\s+re-?use|must\s+not\s+be\s+re-?used|"
        r"never\s+re-?use|shall\s+not\s+be\s+re-?used|not\s+to\s+be\s+re-?used", re.I)),
    ("torque_to_yield", re.compile(
        r"torque[-\s]?to[-\s]?yield|\bTTY\b|plus\s+an\s+additional|"
        r"additional\s+(?:\d{1,3}\s*(?:deg(?:rees?)?|°)|(?:\d+\s*/\s*\d+|\d+)?\s*turns?)", re.I)),
    ("discard_after_removal", re.compile(
        r"\bdiscard(?:ed)?\b|replace\s+(?:each\s+time|whenever)\s+(?:it\s+is\s+)?removed", re.I)),
]
_KIND_ORDER = {"torque_to_yield": 0, "one_time_use": 1, "discard_after_removal": 2}

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def _q_match(q):
    toks = re.findall(r"[A-Za-z0-9]+", q or "")[:6]
    if not toks:
        return None
    return " AND ".join('"%s"' % t for t in toks)


def find_flags(text, cap=8):
    """Scan one page's text sentence-by-sentence; return [{kind, sentence}] (sentence <=200 chars,
    verbatim modulo whitespace collapse). One entry per (kind, sentence). Pure + unit-testable."""
    out, seen = [], set()
    for sent in _SENT_SPLIT.split(text or ""):
        s = re.sub(r"\s+", " ", sent).strip()
        if len(s) < 8:
            continue
        for kind, rx in _PATTERNS:
            if rx.search(s):
                key = (kind, s[:200])
                if key in seen:
                    continue
                seen.add(key)
                out.append({"kind": kind, "sentence": s[:200]})
                if len(out) >= cap:
                    return out
    return out


def find_for_query(db_path, q, limit=10, per_page=4):
    """Flags for a part/NSN query across the corpus. FTS: (query terms AND'd) AND (trigger phrases).
    Returns {ok, query, n_pages, flags:[{kind, sentence, mentions_query, doc_id, tm, vehicle, page}]}.
    Extractive + cited (R13); [] when the manuals never say it."""
    q = (q or "").strip()
    qm = _q_match(q)
    if not qm:
        return {"ok": False, "query": q, "flags": [], "error": "query too short"}
    match = "(" + qm + ") AND " + _TRIGGERS
    pages = _corpus.fts_pages(match, limit=limit, with_body=True, db_path=db_path)
    toks = {t.lower() for t in re.findall(r"[A-Za-z0-9]+", q) if len(t) > 2}
    flags = []
    for pg in pages:
        for f in find_flags(pg.get("body_text") or "", cap=per_page):
            sl = f["sentence"].lower()
            f["mentions_query"] = bool(toks) and any(t in sl for t in toks)
            f["doc_id"] = pg.get("doc_id"); f["tm"] = pg.get("tm_number")
            f["vehicle"] = pg.get("vehicle"); f["page"] = pg.get("page_number")
            flags.append(f)
    flags.sort(key=lambda f: (0 if f.get("mentions_query") else 1, _KIND_ORDER.get(f["kind"], 9)))
    return {"ok": True, "query": q, "n_pages": len(pages), "flags": flags[:24],
            "note": "extractive: every flag cites the manual's exact sentence + page; nothing inferred"}


# --------------------------------------------------------------------------- #
# self-test: `python oneuse.py` (run from engine/)                            #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    # 1) pure sentence classifier on synthetic text
    txt = ("Remove the connecting rod bolts. Connecting rod bolts are torque-to-yield; do not reuse. "
           "Remove and discard the gasket. Tighten to 25 ft-lb plus an additional 90 degrees. "
           "Inspect the cover for cracks.")
    fl = find_flags(txt)
    kinds = {f["kind"] for f in fl}
    assert "torque_to_yield" in kinds and "one_time_use" in kinds and "discard_after_removal" in kinds, fl
    assert all(len(f["sentence"]) <= 200 for f in fl), fl
    assert not any("Inspect the cover" in f["sentence"] for f in fl), fl   # no false flag
    print("find_flags OK ->", sorted(kinds))

    # 2) end-to-end against a synthetic corpus db (standalone path of features.corpus)
    import os, sqlite3, tempfile
    d = tempfile.mkdtemp(); db = os.path.join(d, "c.db"); c = sqlite3.connect(db)
    c.execute("CREATE TABLE documents(id INTEGER PRIMARY KEY, vehicle TEXT, tm_number TEXT, title TEXT)")
    c.execute("CREATE TABLE pages(id INTEGER PRIMARY KEY, document_id INT, page_number INT, body_text TEXT)")
    c.execute("CREATE VIRTUAL TABLE pages_fts USING fts5(body_text, content='pages', content_rowid='id')")
    c.execute("INSERT INTO documents VALUES(1,'M915 Truck','TM 9-2320-363-20','Maintenance')")
    c.execute("INSERT INTO pages(document_id,page_number,body_text) VALUES(1,88,"
              "'Head bolt removal. The head bolts are torque-to-yield and must not be reused. "
              "Discard head bolts after removal and install new bolts.')")
    c.execute("INSERT INTO pages(document_id,page_number,body_text) VALUES(1,90,"
              "'Install the valve cover. Torque the screws to 8 ft-lb.')")
    c.execute("INSERT INTO pages_fts(rowid, body_text) SELECT id, body_text FROM pages")
    c.commit(); c.close()
    res = find_for_query(db, "head bolt")
    assert res["ok"] and res["flags"], res
    assert all(f["page"] == 88 and f["tm"] == "TM 9-2320-363-20" for f in res["flags"]), res
    got = {f["kind"] for f in res["flags"]}
    assert "torque_to_yield" in got and "one_time_use" in got and "discard_after_removal" in got, res
    assert all(f["mentions_query"] for f in res["flags"] if "head bolt" in f["sentence"].lower()), res
    clean = find_for_query(db, "valve cover")
    assert clean["ok"] and clean["flags"] == [], clean     # nothing flagged -> no fabricated flags
    assert find_for_query(db, "")["ok"] is False
    print("find_for_query OK -> %d flag(s) on p.88, none on the clean page" % len(res["flags"]))
    print("oneuse self-test PASS")

# END OF FILE
