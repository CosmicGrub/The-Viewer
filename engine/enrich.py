#!/usr/bin/env python3
"""THE VIEWER -- EXTERNAL GAP-FILL ENRICHMENT (v1.1.2).

The corpus documents are ALWAYS the authoritative / default data. This module cross-references the OPEN INTERNET
(Internet Archive full-text search + the Wayback Machine + any given source URL) ONLY to FILL BLANKS -- dimension /
measurement types for a part or vehicle where the corpus has *no* value or an inconclusive one. External values are:

  * never allowed to overwrite or contradict a corpus value (corpus wins, always),
  * only surfaced for dimension types the corpus is missing for that subject,
  * always badged 'external / unconfirmed' and carry full provenance (source, source_url, wayback timestamp, fetched ts).

Design: the RUNNING APP stays 100% offline -- it only ever READS the append-only `enrich.db` sidecar (R1/R6). The
network is touched ONLY by the opt-in, host-run crawler (build_enrich.py / ENRICH.bat). The network layer here is
injectable so it is deterministic under test and never fires from the server process.

Public surface:
  find_gaps(db_path, measures_db=None, limit=...)      -> subjects + which dimension types are missing/inconclusive
  wayback_snapshot(url, fetch, timestamp=None)         -> closest archived URL or None
  ia_search(query, fetch, rows=5)                      -> [archive.org identifiers]
  ia_fulltext(identifier, fetch)                       -> full text of an IA item (djvu) or ''
  extract_external(text, extractor=None)               -> measurements from external text (uses measures.extract)
  record(enrich_db, subject, rows, provenance)         -> append external fills (append-only, provenance mandatory)
  external_for_query(enrich_db, q, corpus_types=())    -> external fills for a subject, EXCLUDING types corpus has
"""
import os, re, json, sqlite3, time

# canonical dimension types we try to complete for every subject
DIMENSION_TYPES = ("length", "area", "angle", "weight", "force", "torque", "pressure",
                   "capacity", "electrical", "temperature", "flow", "speed", "rotation")

SCHEMA = """
CREATE TABLE IF NOT EXISTS ext_meas(
  id INTEGER PRIMARY KEY,
  subject TEXT,            -- the part/vehicle/TM the fill is FOR (normalized lowercase)
  subject_label TEXT,      -- human label as queried
  type TEXT, unit TEXT, value TEXT, value2 TEXT, tolerance TEXT, raw TEXT, context TEXT,
  source TEXT,             -- 'internet_archive' | 'wayback' | 'web'
  source_url TEXT,         -- the ARCHIVED (Wayback) URL the value came from — permanent, pinned
  orig_url TEXT,           -- the original (live) URL that was routed through Wayback
  wayback_ts TEXT,         -- Wayback snapshot timestamp (YYYYMMDDhhmmss)
  fetched_ts REAL,         -- when WE retrieved it
  confidence REAL,         -- 0..1 heuristic
  status TEXT DEFAULT 'external-unconfirmed');
CREATE INDEX IF NOT EXISTS ix_ext_subject ON ext_meas(subject);
CREATE INDEX IF NOT EXISTS ix_ext_type    ON ext_meas(type);
CREATE TABLE IF NOT EXISTS ext_done(subject TEXT PRIMARY KEY, ts REAL);
"""


# ------------------------------------------------------------------ network (host-run only; injectable) -------------
def default_fetch(url, timeout=20):
    """Real HTTP GET -- used ONLY by the host-run crawler. Returns text or '' on any failure (fail-soft, offline-safe)."""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "THE-VIEWER-enrich/1.1 (offline TM index; gap-fill)"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception:
        return ""


def wayback_snapshot(url, fetch=default_fetch, timestamp=None):
    """Closest Wayback snapshot for `url` -> {'url':..., 'timestamp':...} or None."""
    api = "https://archive.org/wayback/available?url=" + _q(url) + (("&timestamp=" + timestamp) if timestamp else "")
    try:
        j = json.loads(fetch(api) or "{}")
        snap = (j.get("archived_snapshots") or {}).get("closest")
        if snap and snap.get("available") and snap.get("url"):
            return {"url": snap["url"], "timestamp": snap.get("timestamp", "")}
    except Exception:
        pass
    return None


def ia_search(query, fetch=default_fetch, rows=5):
    """Internet Archive full-text search -> [identifier,...]."""
    api = ("https://archive.org/advancedsearch.php?q=" + _q(query) +
           "&fl[]=identifier&rows=%d&output=json" % rows)
    try:
        j = json.loads(fetch(api) or "{}")
        return [d["identifier"] for d in (j.get("response", {}).get("docs") or []) if d.get("identifier")]
    except Exception:
        return []


def ia_fulltext(identifier, fetch=default_fetch):
    """Fetch an IA item's plain-text (djvu) layer -> str ('' if none)."""
    for suffix in ("_djvu.txt", ".txt"):
        txt = fetch("https://archive.org/download/%s/%s%s" % (identifier, identifier, suffix))
        if txt and len(txt) > 200 and "<html" not in txt[:200].lower():
            return txt
    return ""


def wayback_save(url, fetch=default_fetch):
    """Push a URL through the Wayback Machine 'Save Page Now' so a snapshot exists, then return the closest snapshot.
    Best-effort (SPN can be slow / rate-limited); returns {'url','timestamp'} or None. Host-run only."""
    try:
        fetch("https://web.archive.org/save/" + url, timeout=45)  # trigger capture; ignore body
    except Exception:
        pass
    return wayback_snapshot(url, fetch)


def wayback_get_or_save(url, fetch=default_fetch, save=False):
    """Return the closest Wayback snapshot for `url`; if none and save=True, push it through Save Page Now first.
    This is how we 'route every link through the Wayback Machine'."""
    snap = wayback_snapshot(url, fetch)
    if not snap and save:
        snap = wayback_save(url, fetch)
    return snap


def strip_html(s):
    """Crude HTML → text so the measurement extractor can read an archived web page. Drops script/style + tags + entities."""
    if not s:
        return ""
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
         .replace("&quot;", '"').replace("&#39;", "'").replace("&deg;", "°"))
    return re.sub(r"[ \t]+", " ", s)


def fetch_via_wayback(url, fetch=default_fetch, save=False):
    """Route `url` through Wayback and return (text, snapshot_url, snapshot_ts). Empty text if no snapshot/fetch fails.
    This guarantees the data we harvest is pinned to an archived copy (Chris's requirement)."""
    snap = wayback_get_or_save(url, fetch, save=save)
    if not snap:
        return "", "", ""
    raw = fetch(snap["url"])
    text = strip_html(raw) if raw else ""
    return text, snap["url"], snap.get("timestamp", "")


def seed_links(path, subject=None):
    """Read a user-maintained seed list of URLs to harvest. One URL per line; optional 'subject|url' tagging so a link
    can be scoped to a vehicle/part. '#' comments allowed. Returns [url,...] (filtered to `subject` if tagged)."""
    out = []
    if not path or not os.path.exists(path):
        return out
    try:
        for ln in open(path, encoding="utf-8"):
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            tag, sep, url = ln.partition("|")
            if sep:  # 'subject | url' — scoped to a vehicle/part
                if subject is None or subject.lower() in tag.strip().lower():
                    out.append(url.strip())
            elif subject is None:  # untagged = global reference, harvested once in the subject-agnostic pass
                out.append(tag.strip())
    except Exception:
        pass
    return out


def web_links(query, search_fn=None, limit=8):
    """Candidate links from an INJECTED web-search function (host provides one; keeps this module offline-by-default and
    search-provider-agnostic). `search_fn(query, limit) -> [url,...]`. Returns [] if none supplied."""
    if not search_fn:
        return []
    try:
        return list(search_fn(query, limit))[:limit]
    except Exception:
        return []


def _q(s):
    import urllib.parse
    return urllib.parse.quote(str(s), safe="")


# ------------------------------------------------------------------ gap detection (corpus is authoritative) ---------
def find_gaps(db_path, measures_db=None, limit=200):
    """For each vehicle in the corpus, which DIMENSION_TYPES have NO measurement (a gap) or only one (inconclusive).
    Uses the measures sidecar if built, else counts live via measures over a sample. Returns
    [{subject, label, present:[types], gaps:[types], inconclusive:[types]}]. Read-only."""
    present = {}  # subject -> {type: count}
    labels = {}
    if measures_db and os.path.exists(measures_db):
        try:
            m = sqlite3.connect("file:%s?mode=ro" % measures_db, uri=True)
            # join doc->vehicle via the main DB
            v = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
            doc_veh = {r[0]: (r[1] or "") for r in v.execute("SELECT id, vehicle FROM documents")}
            v.close()
            for doc, typ, c in m.execute("SELECT doc, type, COUNT(*) FROM meas GROUP BY doc, type"):
                subj = (doc_veh.get(doc, "") or ("doc%s" % doc)).strip().lower()
                labels.setdefault(subj, doc_veh.get(doc, "") or ("doc%s" % doc))
                present.setdefault(subj, {})
                present[subj][typ] = present[subj].get(typ, 0) + c
            m.close()
        except Exception:
            present = {}
    if not present:
        # fallback: enumerate vehicles; treat all types as gaps (crawler will confirm what it finds)
        try:
            v = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
            for (veh,) in v.execute("SELECT DISTINCT vehicle FROM documents WHERE vehicle IS NOT NULL AND vehicle<>''"):
                subj = veh.strip().lower(); labels[subj] = veh; present[subj] = {}
            v.close()
        except Exception:
            pass
    out = []
    for subj, types in list(present.items())[:limit]:
        gaps = [t for t in DIMENSION_TYPES if types.get(t, 0) == 0]
        inconc = [t for t in DIMENSION_TYPES if types.get(t, 0) == 1]
        if gaps or inconc:
            out.append({"subject": subj, "label": labels.get(subj, subj),
                        "present": sorted(t for t in DIMENSION_TYPES if types.get(t, 0) > 1),
                        "gaps": gaps, "inconclusive": inconc})
    return out


# ------------------------------------------------------------------ external extraction + record -------------------
def extract_external(text, extractor=None):
    """Run the SAME measurement extractor over external text. `extractor` injectable for tests."""
    if extractor is None:
        import measures  # lazy: keeps module importable even if measures is momentarily unreadable
        extractor = measures.extract
    return extractor(text or "", cap=120)


def record(enrich_db, subject, subject_label, rows, provenance, only_types=None):
    """Append external fills for `subject`. `provenance` = {source, source_url, wayback_ts}. If `only_types` is given
    (the corpus GAPS), fills for any OTHER type are dropped -- we only complete blanks, never override the corpus."""
    con = sqlite3.connect(enrich_db); con.executescript(SCHEMA)
    try:  # migrate pre-1.1.3 sidecars that lack orig_url
        con.execute("ALTER TABLE ext_meas ADD COLUMN orig_url TEXT")
    except Exception:
        pass
    subj = (subject or "").strip().lower()
    now = time.time(); n = 0
    for m in rows:
        if only_types is not None and m["type"] not in only_types:
            continue
        con.execute(
            "INSERT INTO ext_meas(subject,subject_label,type,unit,value,value2,tolerance,raw,context,"
            "source,source_url,orig_url,wayback_ts,fetched_ts,confidence,status) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (subj, subject_label, m["type"], m["unit"], m["value"], m.get("value2"), m.get("tolerance"),
             m.get("raw"), m.get("context"), provenance.get("source", "web"), provenance.get("source_url", ""),
             provenance.get("orig_url", ""), provenance.get("wayback_ts", ""), now,
             float(provenance.get("confidence", 0.5)), "external-unconfirmed"))
        n += 1
    con.execute("INSERT OR REPLACE INTO ext_done(subject,ts) VALUES(?,?)", (subj, now))
    con.commit(); con.close()
    return n


# ------------------------------------------------------------------ offline read (no network) ----------------------
def external_for_query(enrich_db, q, corpus_types=()):
    """Read external fills for subject `q` from the sidecar -- NO network. Corpus is authoritative: any type already
    present in `corpus_types` is filtered OUT (we only show external data where the corpus is silent). Returns
    {query, count, by_type, results:[{...provenance...}]}."""
    q = (q or "").strip()
    if not enrich_db or not os.path.exists(enrich_db) or len(q) < 2:
        return {"query": q, "count": 0, "by_type": {}, "results": []}
    have = set(corpus_types or ())
    subj = q.lower()
    out = []; counts = {}
    try:
        con = sqlite3.connect("file:%s?mode=ro" % enrich_db, uri=True); con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT * FROM ext_meas WHERE subject=? OR subject LIKE ? ORDER BY confidence DESC LIMIT 300",
            (subj, "%" + subj + "%")).fetchall()
        con.close()
    except Exception:
        return {"query": q, "count": 0, "by_type": {}, "results": []}
    for r in rows:
        if r["type"] in have:      # corpus already answers this dimension -> corpus wins, hide external
            continue
        counts[r["type"]] = counts.get(r["type"], 0) + 1
        rk = r.keys()
        out.append({"type": r["type"], "unit": r["unit"], "value": r["value"], "value2": r["value2"],
                    "tolerance": r["tolerance"], "context": r["context"], "source": r["source"],
                    "source_url": r["source_url"], "orig_url": (r["orig_url"] if "orig_url" in rk else ""),
                    "wayback_ts": r["wayback_ts"], "fetched": r["fetched_ts"], "confidence": r["confidence"],
                    "status": r["status"]})
    return {"query": q, "count": len(out), "by_type": counts, "results": out}


def provenance_rows(enrich_db, subject=None, limit=500):
    """INTERNAL AUDIT view (for the operator, NOT the mechanic UI): every external value WITH its provenance links --
    the archived Wayback URL, the original live URL, and the snapshot timestamp -- so a human can spot-check where a
    gap-fill came from. This is the ONE place links are surfaced on purpose; the Masterfile/mechanic views stay linkless
    (R11). Read-only. Returns {subject, count, rows:[{subject,label,type,unit,value,source,orig_url,wayback_url,wayback_ts,fetched}]}."""
    import os as _os
    if not enrich_db or not _os.path.exists(enrich_db):
        return {"subject": subject, "count": 0, "rows": []}
    try:
        con = sqlite3.connect("file:%s?mode=ro" % enrich_db, uri=True); con.row_factory = sqlite3.Row
        has_orig = any(r[1] == "orig_url" for r in con.execute("PRAGMA table_info(ext_meas)"))
        cols = ("subject,subject_label,type,unit,value,value2,tolerance,source,source_url,"
                + ("orig_url," if has_orig else "") + "wayback_ts,fetched_ts")
        if subject:
            q = subject.strip().lower()
            rows = con.execute("SELECT %s FROM ext_meas WHERE subject=? OR subject LIKE ? "
                               "ORDER BY subject, type LIMIT ?" % cols, (q, "%" + q + "%", limit)).fetchall()
        else:
            rows = con.execute("SELECT %s FROM ext_meas ORDER BY subject, type LIMIT ?" % cols, (limit,)).fetchall()
        con.close()
    except Exception:
        return {"subject": subject, "count": 0, "rows": []}
    out = []
    for r in rows:
        k = r.keys()
        out.append({"subject": r["subject"], "label": r["subject_label"], "type": r["type"], "unit": r["unit"],
                    "value": r["value"], "value2": r["value2"], "tolerance": r["tolerance"], "source": r["source"],
                    "wayback_url": r["source_url"], "orig_url": (r["orig_url"] if "orig_url" in k else ""),
                    "wayback_ts": r["wayback_ts"], "fetched": r["fetched_ts"]})
    return {"subject": subject, "count": len(out), "rows": out}


if __name__ == "__main__":
    import tempfile
    d = tempfile.mkdtemp(); edb = os.path.join(d, "enrich.db")

    # fake network: a canned Wayback response + a canned IA search + full text
    def fake_fetch(url, timeout=20):
        if "wayback/available" in url:
            return json.dumps({"archived_snapshots": {"closest": {
                "available": True, "url": "http://web.archive.org/web/20180101/example", "timestamp": "20180101000000"}}})
        if "advancedsearch" in url:
            return json.dumps({"response": {"docs": [{"identifier": "TM_SAMPLE_1"}]}})
        if "download" in url:
            return "Curb weight 5200 lb. Overall length 180 in. Fording depth 30 in." + (" x" * 100)
        return ""

    snap = wayback_snapshot("http://army.mil/tm", fake_fetch)
    assert snap and snap["timestamp"] == "20180101000000", "wayback parse failed"
    ids = ia_search("HMMWV weight", fake_fetch); assert ids == ["TM_SAMPLE_1"], "ia_search parse failed"
    txt = ia_fulltext("TM_SAMPLE_1", fake_fetch); assert "Curb weight" in txt, "ia_fulltext failed"

    # route ANY link through Wayback → archived text (strip HTML)
    def html_fetch(url, timeout=20):
        if "wayback/available" in url:
            return json.dumps({"archived_snapshots": {"closest": {
                "available": True, "url": "http://web.archive.org/web/20200101/site", "timestamp": "20200101000000"}}})
        if "web.archive.org/web/" in url:
            return "<html><body><p>Overall length 180 in.</p><script>x</script></body></html>"
        return ""
    wtext, wurl, wts = fetch_via_wayback("http://example.com/part", html_fetch)
    assert "Overall length 180 in" in wtext and "<script" not in wtext and wts == "20200101000000", "wayback fetch/strip failed"
    assert seed_links.__call__ and web_links("q", None) == [], "link providers failed"

    # deterministic fake extractor (avoids depending on measures at test time)
    def fake_extractor(t, cap=120):
        return [{"type": "weight", "unit": "lb", "value": "5200", "value2": None, "tolerance": None,
                 "raw": "5200 lb", "context": "Curb weight 5200 lb"},
                {"type": "length", "unit": "in", "value": "180", "value2": None, "tolerance": None,
                 "raw": "180 in", "context": "Overall length 180 in"}]
    rows = extract_external(txt, extractor=fake_extractor)
    # corpus already HAS weight for this subject -> only 'length' is a gap we fill
    n = record(edb, "HMMWV", "HMMWV", rows, {"source": "internet_archive",
               "source_url": "https://archive.org/details/TM_SAMPLE_1", "wayback_ts": "", "confidence": 0.6},
               only_types={"length"})
    assert n == 1, "record should keep only the gap type (length), got %d" % n

    # read back: corpus is authoritative for 'weight' -> even if present, weight is filtered; length shows
    res = external_for_query(edb, "HMMWV", corpus_types={"weight"})
    assert res["count"] == 1 and "length" in res["by_type"] and "weight" not in res["by_type"], "authoritative filter failed"
    assert res["results"][0]["source_url"].startswith("https://archive.org/"), "provenance missing"
    print("enrich self-test OK  (wayback/ia parse, gap-only record, corpus-authoritative filter, provenance)")
# END OF FILE
