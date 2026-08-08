"""ask.py -- offline, CITED question answering over the corpus. No network, no LLM: this is an EXTRACTIVE
answerer. It retrieves the most relevant pages (semantic embeddings if built + keyword FTS), then pulls the
sentences that best answer the question and returns them verbatim, each cited to its manual + page. That
keeps every answer grounded in the manuals -- it never invents text, it surfaces the exact lines a mechanic
would read, with the page to open.

extract_answer(question, passages) is pure and unit-testable; answer() wires in retrieval. Read-only."""

from __future__ import annotations
import re, sqlite3

_WORD = re.compile(r"[A-Za-z0-9]+")
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_STOP = set("the a an of to in on for and or is are be with as at by from this that it its your you "
            "if then when how do does what which where use used using into onto per not no".split())


def _terms(s):
    return [w.lower() for w in _WORD.findall(s or "") if len(w) > 1 and w.lower() not in _STOP]


def _sentences(text):
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if not text:
        return []
    return [s.strip() for s in _SENT.split(text) if len(s.strip()) > 12]


def extract_answer(question, passages, max_sentences=5):
    """passages: [{text, doc, page, tm, page_url, score?}]. Returns the best-matching sentences (verbatim)
    with citations, ranked by overlap with the question. Pure."""
    qterms = set(_terms(question))
    if not qterms:
        return {"question": question, "sentences": [], "sources": []}
    scored = []
    for p in passages or []:
        base = float(p.get("score") or 0.0)
        for sent in _sentences(p.get("text")):
            st = _terms(sent)
            if not st:
                continue
            overlap = sum(1 for w in st if w in qterms)
            if overlap == 0:
                continue
            # coverage of the QUESTION terms matters more than raw hits; short, on-point sentences win
            cover = overlap / (len(qterms) or 1)
            density = overlap / (len(st) or 1)
            score = round(cover * 2.0 + density + base * 0.25, 4)
            scored.append({"text": sent, "score": score, "doc": p.get("doc"), "page": p.get("page"),
                           "tm": p.get("tm") or p.get("vehicle") or "", "page_url": p.get("page_url")})
    scored.sort(key=lambda x: -x["score"])
    picked, seen, sources = [], set(), {}
    for s in scored:
        key = s["text"].lower()[:80]
        if key in seen:
            continue
        seen.add(key)
        picked.append(s)
        src = (str(s["doc"]), s["page"])
        if src not in sources and s.get("doc") is not None:
            sources[src] = {"doc": s["doc"], "page": s["page"], "tm": s["tm"], "page_url": s["page_url"]}
        if len(picked) >= max_sentences:
            break
    return {"question": question, "sentences": picked, "sources": list(sources.values()),
            "answered": bool(picked)}


def _fts_passages(db_path, question, limit=12):
    """v1.13: retrieval via the shared features.corpus helper (pooled in-app; leak-proof standalone)."""
    terms = [t for t in _WORD.findall(question) if len(t) > 1]
    match = " OR ".join(terms) if terms else question
    try:
        from features import corpus as _corpus
        rows = _corpus.fts_pages(match, limit=limit, with_body=True, db_path=db_path)
    except Exception:
        return []
    return [{"text": r["body_text"], "doc": r["doc_id"], "tm": r["tm_number"], "vehicle": r["vehicle"],
             "page": r["page_number"],
             "page_url": "/deepzoom?doc=%s&page=%s" % (r["doc_id"], r["page_number"])} for r in rows]


def answer(db_path, index_dir, question, k=12, max_sentences=5):
    """Retrieve passages (semantic if the embeddings index is built + keyword FTS), then extract the answer."""
    passages = _fts_passages(db_path, question, limit=k)
    try:
        import embed
        sem = embed.search(question, index_dir, top=k)
        sem_rows = (sem.get("results") if isinstance(sem, dict) else sem) or []
        # semantic hits carry doc/page but not text -> pull the page bodies
        if sem_rows:
            con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True); con.row_factory = sqlite3.Row
            try:                                       # v1.13: finally-close (no leak on error)
                for s in sem_rows:
                    try:
                        r = con.execute("SELECT d.tm_number AS tm, d.vehicle, p.body_text AS body FROM pages p "
                                        "JOIN documents d ON d.id=p.document_id WHERE p.document_id=? AND p.page_number=? LIMIT 1",
                                        (s.get("doc"), s.get("page"))).fetchone()
                        if r:
                            passages.append({"text": r["body"], "doc": s.get("doc"), "tm": r["tm"],
                                             "vehicle": r["vehicle"], "page": s.get("page"),
                                             "page_url": s.get("page_url"), "score": s.get("score", 0)})
                    except Exception:
                        pass
            finally:
                con.close()
    except Exception:
        pass
    res = extract_answer(question, passages, max_sentences=max_sentences)
    res["retrieved"] = len(passages)
    # v1.13 trust badge (R13): extractive verbatim from the corpus -> 'high' only when >=2 distinct
    # cited pages corroborate; a lone citation is 'medium' (cited). No answer -> no badge.
    try:
        import trust as _trust
        res["trust"] = (_trust.badge(source="corpus", n_samples=len(res.get("sources") or []))
                        if res.get("answered") else None)
    except Exception:
        res["trust"] = None
    return res


# --------------------------------------------------------------------------- #
# self-test: `python ask.py`  (pure extractor; no DB)                          #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    passages = [
        {"text": "General notes. The vehicle has many systems. Weather can affect operation.",
         "doc": "1", "tm": "TM-A", "page": 2},
        {"text": "To bleed the CTIS lines, open the bleeder valve at each wheel and run the pump until "
                 "clear fluid flows. Close the valve when no air remains. Torque the fitting to 20 ft-lb.",
         "doc": "2", "tm": "TM-B", "page": 44, "page_url": "/deepzoom?doc=2&page=44"},
        {"text": "The CTIS controller is mounted under the dash.", "doc": "2", "tm": "TM-B", "page": 40},
    ]
    r = extract_answer("How do I bleed the CTIS lines?", passages)
    assert r["answered"], r
    top = r["sentences"][0]["text"].lower()
    assert "bleed the ctis" in top or "bleeder valve" in top, r["sentences"][0]
    assert r["sentences"][0]["page"] == 44, r["sentences"][0]
    assert any(s["page"] == 44 for s in r["sources"]), r["sources"]
    print("ask extract_answer OK -> top: %s (%s p.%s)"
          % (r["sentences"][0]["text"][:60], r["sentences"][0]["tm"], r["sentences"][0]["page"]))

    # unanswerable -> empty, no crash
    r2 = extract_answer("price of tea in china", passages)
    assert not r2["answered"], r2
    print("ask no-answer OK (graceful)")
    print("ask self-test PASS")

# END OF FILE
