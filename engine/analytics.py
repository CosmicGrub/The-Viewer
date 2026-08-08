#!/usr/bin/env python3
"""THE VIEWER -- LOCAL USAGE ANALYTICS (v0.99.24). Privacy-preserving, OFFLINE, local-only: an append-only JSONL of
what got looked at (search queries, parts, pages), used to (a) show a "most-used" panel on the home page and
(b) prioritize OCR/enrichment on the hottest documents. Never leaves the machine; no network, no accounts, no PII
beyond the search text the user typed. Stored at index/analytics.jsonl. Read/append only on its own sidecar (R1/R6)."""
import os, json, time, re
from collections import Counter

FNAME = "analytics.jsonl"
_VALID = {"search", "part", "page", "tool", "torque", "pmcs",
          "gap"}   # v1.13 (#19): a search that returned ZERO results (the corpus couldn't answer)


def _path(index_dir):
    return os.path.join(index_dir, FNAME)


def log(index_dir, kind, key, extra=None):
    """Append one event. kind in _VALID; key = the query/part/route; extra = optional dict. Best-effort, never raises."""
    try:
        kind = (kind or "").strip().lower()
        if kind not in _VALID:
            kind = "tool"
        key = (str(key or "")).strip()[:160]
        if not key:
            return False
        rec = {"t": int(time.time()), "k": kind, "q": key}
        if extra and isinstance(extra, dict):
            for kk in ("doc", "page", "nsn"):
                if extra.get(kk) is not None:
                    rec[kk] = str(extra[kk])[:40]
        with open(_path(index_dir), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return True
    except Exception:
        return False


def _read(index_dir, limit_lines=200000):
    out = []
    p = _path(index_dir)
    if not os.path.exists(p):
        return out
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            for i, ln in enumerate(f):
                if i >= limit_lines:
                    break
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    out.append(json.loads(ln))
                except Exception:
                    continue
    except Exception:
        pass
    return out


def top(index_dir, kind=None, n=10, since_days=None):
    """Most-frequent keys, optionally filtered by kind / recency. Returns [{key,count,kind}]."""
    n = max(1, min(int(n or 10), 100))
    rows = _read(index_dir)
    cutoff = (time.time() - since_days * 86400) if since_days else None
    c = Counter(); knd = {}
    for r in rows:
        if kind and r.get("k") != kind:
            continue
        if cutoff and r.get("t", 0) < cutoff:
            continue
        k = r.get("q")
        if not k:
            continue
        c[k] += 1; knd[k] = r.get("k")
    return [{"key": k, "count": v, "kind": knd.get(k)} for k, v in c.most_common(n)]


def summary(index_dir):
    rows = _read(index_dir)
    by_kind = Counter(r.get("k") for r in rows)
    return {"events": len(rows), "by_kind": dict(by_kind),
            "top_searches": top(index_dir, "search", 8),
            "top_parts": top(index_dir, "part", 8),
            "recent_days": _events_recent(rows, 7)}


def _events_recent(rows, days):
    cutoff = time.time() - days * 86400
    return sum(1 for r in rows if r.get("t", 0) >= cutoff)


def gaps(index_dir, n=12):
    """v1.13 (#19): ZERO-RESULT GAP LOG -- the queries the corpus could NOT answer, ranked by how
    often they were asked (kind='gap' events, appended by the search route). Append-only JSONL is
    the store (R6); this is a pure reader. Returns {total_events, distinct, top:[{query,count,last}]}."""
    n = max(1, min(int(n or 12), 100))
    rows = [r for r in _read(index_dir) if r.get("k") == "gap"]
    c = Counter(); last = {}
    for r in rows:
        k = (r.get("q") or "").strip()
        if not k:
            continue
        c[k] += 1
        last[k] = max(last.get(k, 0), int(r.get("t") or 0))
    top = [{"query": k, "count": v,
            "last": time.strftime("%Y-%m-%d %H:%M", time.localtime(last.get(k, 0))) if last.get(k) else None}
           for k, v in c.most_common(n)]
    return {"total_events": len(rows), "distinct": len(c), "top": top}


def hot_docs(index_dir, n=20):
    """Docs referenced most (by 'doc' in events) -> for prioritizing OCR/enrichment on what people actually use."""
    rows = _read(index_dir)
    c = Counter(r.get("doc") for r in rows if r.get("doc"))
    return [{"doc": d, "count": v} for d, v in c.most_common(max(1, min(int(n or 20), 200)))]


if __name__ == "__main__":
    import tempfile
    d = tempfile.mkdtemp()
    for _ in range(5): log(d, "search", "alternator")
    for _ in range(3): log(d, "search", "water pump gasket")
    log(d, "part", "2920-01-111-1111", {"doc": "5"}); log(d, "part", "2920-01-111-1111", {"doc": "5"})
    log(d, "page", "x", {"doc": "5", "page": "40"})
    log(d, "bogus-kind", "should-become-tool")
    log(d, "search", "")  # empty -> ignored
    print("top searches:", top(d, "search", 5))
    print("summary events:", summary(d)["events"], "by_kind:", summary(d)["by_kind"])
    print("hot docs:", hot_docs(d))
    assert top(d, "search", 5)[0] == {"key": "alternator", "count": 5, "kind": "search"}, "top ranking wrong"
    assert summary(d)["events"] == 12, "event count wrong (empty search should be dropped)"
    assert hot_docs(d)[0]["doc"] == "5", "hot doc wrong"
    # v1.13 (#19): gap log -- upcounted per distinct query, last-seen kept
    log(d, "gap", "flux capacitor seal"); log(d, "gap", "flux capacitor seal"); log(d, "gap", "warp coil")
    g = gaps(d)
    assert g["total_events"] == 3 and g["distinct"] == 2, g
    assert g["top"][0] == {"query": "flux capacitor seal", "count": 2, "last": g["top"][0]["last"]}, g
    assert g["top"][0]["last"], g            # last-seen timestamp present
    print("gaps:", g["top"])
    print("analytics self-test OK")
# END OF FILE
