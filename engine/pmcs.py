#!/usr/bin/env python3
"""THE VIEWER -- PMCS FINDER (v0.99.23). Surface the Preventive Maintenance Checks & Services tables fast: find the
pages whose text is PMCS content (optionally for one vehicle), with the interval it covers (Before/During/After/Weekly/
Monthly/Annual) inferred from the page text, each cited to its real page. Read-only on the index (FTS); db_path passed
explicitly (like partlocate)."""
import os, re, sqlite3

_INTERVALS = [
    ("Before operation", r"\bBEFORE\b"),
    ("During operation", r"\bDURING\b"),
    ("After operation", r"\bAFTER\b"),
    ("Weekly", r"\bWEEKLY\b"),
    ("Monthly", r"\bMONTHLY\b"),
    ("Semiannually", r"\bSEMI[\s-]?ANNUAL"),
    ("Annually", r"\bANNUAL"),
]


def _db(db_path):
    con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True); con.row_factory = sqlite3.Row; return con


def _intervals_in(text):
    u = (text or "").upper()
    out = [label for label, rx in _INTERVALS if re.search(rx, u)]
    return out[:6]


_ITEM_VERB = re.compile(r"\b(CHECK|INSPECT|CLEAN|SERVICE|LUBRICAT|TIGHTEN|DRAIN|FILL|TEST|VERIFY|ENSURE)\b", re.I)

def _items_in(text, cap=12):
    """Best-effort structured check-items: numbered rows or CHECK/INSPECT/… lines. Cited page is the source of truth."""
    if not text:
        return []
    items = []; seen = set()
    for raw in re.split(r"[\r\n]+", text):
        s = raw.strip()
        if len(s) < 6 or len(s) > 180:
            continue
        m = re.match(r"^(\d{1,3})[\.\)]\s+(.+)", s)      # numbered PMCS item rows
        body = m.group(2).strip() if m else (s if _ITEM_VERB.search(s) else None)
        if not body:
            continue
        key = body[:50].lower()
        if key in seen:
            continue
        seen.add(key); items.append(body[:160])
        if len(items) >= cap:
            break
    return items


def find(db_path, vehicle="", limit=40):
    """Return {vehicle, count, results:[{doc,page,vehicle,tm,title,intervals,snippet,deepzoom_url,page_url}]}."""
    vehicle = (vehicle or "").strip()
    out = []
    # FTS phrase for PMCS tables (page-body text); keep it tolerant to OCR spacing.
    # Vehicle is a DOCUMENT attribute -> filter on documents.vehicle, NOT via the body FTS.
    match = '("preventive maintenance checks" OR PMCS OR "checks and services")'
    try:                                              # v1.13: shared corpus retrieval (leak-proof)
        from features import corpus as _corpus
        rows = _corpus.fts_pages(match, limit=limit * 2, vehicle=vehicle or None,
                                 with_body=True, db_path=db_path)
    except Exception as e:
        return {"vehicle": vehicle, "count": 0, "results": [], "error": str(e)}
    seen = set()
    for r in rows:
        key = (r["doc_id"], r["page_number"])
        if key in seen:
            continue
        seen.add(key)
        body = r["body_text"] or ""
        # a short snippet around the PMCS mention
        m = re.search(r"(?i)(preventive maintenance|checks and services|\bPMCS\b)", body)
        i = max(0, (m.start() if m else 0) - 40)
        snippet = re.sub(r"\s+", " ", body[i:i + 240]).strip()
        out.append({
            "doc": r["doc_id"], "page": r["page_number"], "vehicle": r["vehicle"], "tm": r["tm_number"],
            "title": r["title"],
            "intervals": _intervals_in(body), "items": _items_in(body), "snippet": snippet,
            "deepzoom_url": "/deepzoom?doc=%s&page=%s" % (r["doc_id"], r["page_number"]),
            "page_url": "/page?doc=%s&page=%s&dpi=200" % (r["doc_id"], r["page_number"]),
        })
        if len(out) >= limit:
            break
    return {"vehicle": vehicle, "count": len(out), "results": out}


if __name__ == "__main__":
    import tempfile
    d = tempfile.mkdtemp(); db = os.path.join(d, "v.db"); c = sqlite3.connect(db)
    c.execute("CREATE TABLE documents(id INTEGER PRIMARY KEY, vehicle TEXT, tm_number TEXT, title TEXT)")
    c.execute("CREATE TABLE pages(id INTEGER PRIMARY KEY, document_id INT, page_number INT, body_text TEXT)")
    c.execute("CREATE VIRTUAL TABLE pages_fts USING fts5(body_text, content='pages', content_rowid='id')")
    c.execute("INSERT INTO documents VALUES(1,'HMMWV M998','TM 9-2320-280-10','Operator')")
    c.executemany("INSERT INTO pages(document_id,page_number,body_text) VALUES(?,?,?)", [
        (1, 40, "TABLE 2-1. PREVENTIVE MAINTENANCE CHECKS AND SERVICES. Interval: BEFORE, DURING, AFTER, WEEKLY. Item: engine oil level."),
        (1, 41, "Continued PMCS table. MONTHLY and ANNUAL checks: inspect the suspension and brakes."),
        (1, 99, "Unrelated page about wiring harness routing."),
    ])
    c.execute("INSERT INTO pages_fts(rowid, body_text) SELECT id, body_text FROM pages")
    c.commit(); c.close()
    r = find(db, "HMMWV")
    print("count:", r["count"])
    for x in r["results"]:
        print("  p%s intervals=%s :: %s" % (x["page"], x["intervals"], x["snippet"][:60]))
# END OF FILE
