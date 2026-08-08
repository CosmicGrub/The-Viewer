#!/usr/bin/env python3
"""THE VIEWER -- SAFETY CALLOUT EXTRACTOR (v1.2.2, catalog §3.9). Pulls WARNING / CAUTION / NOTE / DANGER blocks out of
the manual text as first-class, severity-ranked objects -- so a mechanic can see every hazard for a task up front
instead of hoping to spot a boxed callout mid-procedure. Pure stdlib regex; read-only; cited to the page. Feeds the Job
Card + a corpus-wide /api/cautions. Corpus authoritative."""
import re

_RANK = {"DANGER": 3, "WARNING": 2, "CAUTION": 1, "NOTE": 0}
# a callout keyword (often its own line / boxed / all-caps), then the text that follows on the line or next lines
_KW = re.compile(r"(?i)\b(DANGER|WARNING|CAUTION|NOTE)\b\s*[:.\-]?\s*")


def extract(text, page=None, cap=100):
    """Return [{severity, rank, text, context, [page]}] for each safety callout in `text`, de-duped, highest severity
    first."""
    if not text:
        return []
    out = []; seen = set()
    for m in _KW.finditer(text):
        sev = m.group(1).upper()
        # grab up to ~220 chars after the keyword, stopping at the next callout keyword or a hard break
        tail = text[m.end():m.end() + 260]
        tail = re.split(r"(?i)\b(?:DANGER|WARNING|CAUTION|NOTE)\b", tail)[0]
        body = re.sub(r"\s+", " ", tail).strip(" .-–—")
        if len(body) < 4:  # bare keyword with no readable body -> skip
            continue
        key = (sev, body[:40].lower())
        if key in seen:
            continue
        seen.add(key)
        rec = {"severity": sev, "rank": _RANK[sev], "text": body[:220],
               "context": re.sub(r"\s+", " ", text[max(0, m.start() - 10):m.end() + 200]).strip()[:240]}
        if page is not None:
            rec["page"] = page
        out.append(rec)
        if len(out) >= cap:
            break
    out.sort(key=lambda r: -r["rank"])
    return out


def by_severity(text):
    c = {}
    for r in extract(text):
        c[r["severity"]] = c.get(r["severity"], 0) + 1
    return c


def find_for_query(db_path, q, limit=40):
    """FTS-match pages for `q`, pull every safety callout, grouped by severity + cited. No prebuilt index."""
    import sqlite3
    q = (q or "").strip()
    if len(q) < 2:
        return {"query": q, "count": 0, "by_severity": {}, "results": []}
    terms = [t for t in re.findall(r"[A-Za-z0-9]+", q) if len(t) > 1]
    match = " OR ".join(terms) if terms else q
    rows = []
    try:                                              # v1.13: shared corpus retrieval (leak-proof)
        from features import corpus as _corpus
        rows = _corpus.fts_pages(match, limit=limit, with_body=True, db_path=db_path)
    except Exception as e:
        return {"query": q, "count": 0, "by_severity": {}, "results": [], "error": str(e)}
    try:
        import textquality as _tq
    except Exception:
        _tq = None
    out = []; counts = {}
    for r in rows:
        for c in extract(r["body_text"] or "", page=r["page_number"], cap=30):
            c["doc"] = r["doc_id"]; c["vehicle"] = r["vehicle"]; c["tm"] = r["tm_number"]
            c["page_url"] = "/deepzoom?doc=%s&page=%s" % (r["doc_id"], r["page_number"])
            if _tq:
                _tq.annotate(c, context_key="text")  # flag callouts pulled from poor-OCR pages
            counts[c["severity"]] = counts.get(c["severity"], 0) + 1
            out.append(c)
    out.sort(key=lambda r: -r["rank"])
    return {"query": q, "count": len(out), "by_severity": counts, "results": out}


if __name__ == "__main__":
    sample = (
        "WARNING\nHigh voltage present. Disconnect battery ground before servicing to avoid electric shock.\n"
        "Remove the panel. CAUTION: Do not overtighten the fitting; damage to threads will result.\n"
        "NOTE: Torque values are for dry threads.\n"
        "DANGER - Never work under a raised vehicle without jack stands.\n"
        "WARNING\n"  # bare keyword, no body -> must be skipped
    )
    rows = extract(sample, page=12)
    sev = by_severity(sample)
    for need in ("DANGER", "WARNING", "CAUTION", "NOTE"):
        assert need in sev, "missing %s (%s)" % (need, sev)
    assert rows[0]["severity"] == "DANGER", "highest severity must sort first (%s)" % rows[0]["severity"]
    assert any("electric shock" in r["text"] for r in rows), "warning body not captured"
    assert all(len(r["text"]) >= 4 for r in rows), "bare keyword not skipped"
    assert all("page" in r for r in rows)
    print("cautions self-test OK  (DANGER/WARNING/CAUTION/NOTE, severity-sorted, bare-keyword skipped — %s)" % sev)
# END OF FILE
