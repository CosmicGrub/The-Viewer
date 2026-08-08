#!/usr/bin/env python3
"""THE VIEWER -- MASTERFILE (v1.1.4). The single, all-encompassing consolidation of measurement/dimensional data for the
whole project. It MERGES the corpus's authoritative measurements (from measures.db, page-cited to the real TM files)
with the external gap-fills (from enrich.db) into ONE congruent dataset keyed to the authoritative subjects, so the rest
of the project sees a unified picture instead of scattered sources.

Design goals (Chris's ask):
  * ONE Masterfile that is compatible / complementary / congruent with the existing data and sidecars.
  * The reader sees the RAW values AND a FILTERED (deduped, canonical) view, correlated to the authoritative files.
  * NO links surfaced. Corpus rows keep their page cite (a pointer INTO the authoritative TM — desired). External rows
    carry NO URL in the Masterfile or UI; their web provenance stays inside enrich.db for audit only.
  * Corpus is authoritative: external values appear only for (subject, dimension type) the corpus is silent on.

Read-only on the corpus/index; writes only the append-only sidecar index/masterfile.db (R1/R6). Rebuilt by
build_masterfile.py / BUILD-MASTERFILE.bat. Degrades gracefully if a source sidecar is absent."""
import os, sqlite3, time
from collections import Counter, defaultdict

SCHEMA = """
CREATE TABLE IF NOT EXISTS master_raw(
  id INTEGER PRIMARY KEY, subject TEXT, subject_label TEXT, doc INTEGER, page INTEGER,
  type TEXT, unit TEXT, value TEXT, value2 TEXT, tolerance TEXT, context TEXT,
  origin TEXT);                       -- 'corpus' (authoritative) | 'external' (supplemental, unconfirmed)
CREATE INDEX IF NOT EXISTS ix_mraw_subj ON master_raw(subject);
CREATE INDEX IF NOT EXISTS ix_mraw_type ON master_raw(type);
CREATE TABLE IF NOT EXISTS master_filtered(
  id INTEGER PRIMARY KEY, subject TEXT, subject_label TEXT, type TEXT, unit TEXT,
  value TEXT, low TEXT, high TEXT, n INTEGER, origin TEXT, authoritative INTEGER, note TEXT);
CREATE INDEX IF NOT EXISTS ix_mflt_subj ON master_filtered(subject);
CREATE TABLE IF NOT EXISTS master_meta(k TEXT PRIMARY KEY, v TEXT);
"""


def _num(v):
    try:
        return float(str(v).replace(",", ""))
    except Exception:
        return None


def _canonical(vals):
    """Given a list of value strings for one (subject,type,unit,origin): representative value (most common), plus the
    numeric low/high span and the count. Returns (value, low, high, n)."""
    vals = [v for v in vals if v not in (None, "")]
    n = len(vals)
    if not n:
        return "", "", "", 0
    rep = Counter(vals).most_common(1)[0][0]
    nums = [x for x in (_num(v) for v in vals) if x is not None]
    low = ("%g" % min(nums)) if nums else ""
    high = ("%g" % max(nums)) if nums else ""
    return rep, low, high, n


def build(db_path, measures_db, enrich_db, master_db, md_path=None):
    """Consolidate corpus + external into master_db (+ optional Markdown export). Returns a summary dict."""
    con = sqlite3.connect(master_db)
    con.executescript("DROP TABLE IF EXISTS master_raw; DROP TABLE IF EXISTS master_filtered; "
                      "DROP TABLE IF EXISTS master_meta;")
    con.executescript(SCHEMA)

    # subject label map from the authoritative DB
    doc_veh = {}
    veh_label = {}
    try:
        v = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
        for did, veh in v.execute("SELECT id, COALESCE(vehicle,'') FROM documents"):
            doc_veh[did] = (veh or "").strip()
            if veh:
                veh_label[(veh or "").strip().lower()] = veh.strip()
        v.close()
    except Exception:
        pass

    raw = []  # (subject, label, doc, page, type, unit, value, value2, tol, context, origin)

    # (1) CORPUS measurements (authoritative), page-cited to the real TM files
    if measures_db and os.path.exists(measures_db):
        try:
            m = sqlite3.connect("file:%s?mode=ro" % measures_db, uri=True)
            for doc, page, ty, unit, val, val2, tol, ctx in m.execute(
                    "SELECT doc,page,type,unit,value,value2,tolerance,context FROM meas"):
                label = doc_veh.get(doc, "") or ("doc%s" % doc)
                subj = label.strip().lower()
                raw.append((subj, label, doc, page, ty, unit, val, val2, tol, ctx, "corpus"))
            m.close()
        except Exception:
            pass

    # which (subject,type) the corpus already answers -> corpus is authoritative there
    corpus_have = defaultdict(set)
    for r in raw:
        corpus_have[r[0]].add(r[4])

    # (2) EXTERNAL gap-fills (supplemental) -- NO url carried into the Masterfile; only where corpus is silent
    if enrich_db and os.path.exists(enrich_db):
        try:
            e = sqlite3.connect("file:%s?mode=ro" % enrich_db, uri=True)
            for subj, label, ty, unit, val, val2, tol, ctx in e.execute(
                    "SELECT subject,subject_label,type,unit,value,value2,tolerance,context FROM ext_meas"):
                subj = (subj or "").strip().lower()
                if ty in corpus_have.get(subj, ()):   # corpus wins -> skip
                    continue
                raw.append((subj, label or subj, None, None, ty, unit, val, val2, tol, ctx, "external"))
            e.close()
        except Exception:
            pass

    # write RAW layer
    con.executemany(
        "INSERT INTO master_raw(subject,subject_label,doc,page,type,unit,value,value2,tolerance,context,origin) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?)", raw)

    # FILTERED layer: one canonical row per (subject,type,unit,origin)
    groups = defaultdict(list)
    labels = {}
    for subj, label, doc, page, ty, unit, val, val2, tol, ctx, origin in raw:
        groups[(subj, ty, unit, origin)].append(val)
        labels[subj] = label
    filt = []
    for (subj, ty, unit, origin), vals in groups.items():
        rep, low, high, n = _canonical(vals)
        auth = 1 if origin == "corpus" else 0
        note = "authoritative (corpus)" if auth else "external reference — unconfirmed"
        filt.append((subj, labels.get(subj, subj), ty, unit, rep, low, high, n, origin, auth, note))
    con.executemany(
        "INSERT INTO master_filtered(subject,subject_label,type,unit,value,low,high,n,origin,authoritative,note) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?)", filt)

    n_subj = len({r[0] for r in raw})
    meta = {"built_ts": str(time.time()), "n_subjects": str(n_subj), "n_raw": str(len(raw)),
            "n_filtered": str(len(filt)), "corpus_raw": str(sum(1 for r in raw if r[10] == "corpus")),
            "external_raw": str(sum(1 for r in raw if r[10] == "external"))}
    con.executemany("INSERT OR REPLACE INTO master_meta(k,v) VALUES(?,?)", list(meta.items()))
    con.commit(); con.close()

    if md_path:
        _export_md(master_db, md_path, meta)
    return {"subjects": n_subj, "raw": len(raw), "filtered": len(filt),
            "corpus": int(meta["corpus_raw"]), "external": int(meta["external_raw"])}


def _export_md(master_db, md_path, meta):
    con = sqlite3.connect("file:%s?mode=ro" % master_db, uri=True); con.row_factory = sqlite3.Row
    subs = [r[0] for r in con.execute("SELECT DISTINCT subject FROM master_filtered ORDER BY subject")]
    lines = ["# THE VIEWER — MASTERFILE (consolidated measurement & dimensional data)", "",
             "One congruent view of every measured value in the project: the corpus's **authoritative** figures "
             "(cited to the manual page) merged with **external** supplemental values that only fill gaps the manuals "
             "leave open. No external links are shown — external provenance is kept internally for audit.", "",
             "Built: %s · subjects: %s · raw values: %s (corpus %s / external %s) · filtered rows: %s" % (
                 meta.get("built_ts", ""), meta.get("n_subjects", ""), meta.get("n_raw", ""),
                 meta.get("corpus_raw", ""), meta.get("external_raw", ""), meta.get("n_filtered", "")), "", "---", ""]
    for subj in subs:
        lbl = con.execute("SELECT subject_label FROM master_filtered WHERE subject=? LIMIT 1", (subj,)).fetchone()
        lines.append("## %s" % (lbl[0] if lbl else subj))
        for r in con.execute("SELECT type,unit,value,low,high,n,origin,note FROM master_filtered "
                             "WHERE subject=? ORDER BY authoritative DESC, type", (subj,)):
            span = (" (range %s–%s)" % (r["low"], r["high"])) if r["low"] and r["high"] and r["low"] != r["high"] else ""
            tag = "" if r["origin"] == "corpus" else "  _[external — unconfirmed]_"
            lines.append("- **%s**: %s %s%s  · n=%s%s" % (r["type"], r["value"], r["unit"], span, r["n"], tag))
        lines.append("")
    con.close()
    open(md_path, "w", encoding="utf-8").write("\n".join(lines) + "\n<!-- END OF FILE -->\n")


def for_subject(master_db, q, limit=400):
    """Read the Masterfile for one subject -- NO links. Returns {query, filtered, raw, counts} where filtered and raw
    are lists of measurement rows."""
    q = (q or "").strip()
    if not master_db or not os.path.exists(master_db) or len(q) < 2:
        return {"query": q, "filtered": [], "raw": [], "counts": {}}
    subj = q.lower()
    con = sqlite3.connect("file:%s?mode=ro" % master_db, uri=True); con.row_factory = sqlite3.Row
    filt = [dict(r) for r in con.execute(
        "SELECT type,unit,value,low,high,n,origin,authoritative,note,subject_label FROM master_filtered "
        "WHERE subject=? OR subject LIKE ? ORDER BY authoritative DESC, type LIMIT ?",
        (subj, "%" + subj + "%", limit))]
    raw = [dict(r) for r in con.execute(
        "SELECT type,unit,value,value2,tolerance,context,doc,page,origin FROM master_raw "
        "WHERE subject=? OR subject LIKE ? ORDER BY origin, type LIMIT ?",
        (subj, "%" + subj + "%", limit))]
    con.close()
    counts = {"corpus": sum(1 for r in raw if r["origin"] == "corpus"),
              "external": sum(1 for r in raw if r["origin"] == "external")}
    # add a page pointer to the authoritative file for corpus rows (internal reference, NOT an external link)
    for r in raw:
        r["page_url"] = ("/deepzoom?doc=%s&page=%s" % (r["doc"], r["page"])) if r["origin"] == "corpus" and r["doc"] else ""
    # enrich filtered rows at READ time (no rebuild): dual-unit display + a wide-variance flag
    try:
        import units
    except Exception:
        units = None
    for f in filt:
        f["alt"] = units.dual(f.get("value"), f.get("unit")) if units else ""
        f["system"] = units.system_of(f.get("unit")) if units else ""
        f["spread"] = _spread(f)
        f["confidence"] = _confidence(f)
    return {"query": q, "filtered": filt, "raw": raw, "counts": counts}


def _confidence(f):
    """A pragmatic trust score per dimension (no per-method tracking needed): authoritative + multiple agreeing samples
    = high; authoritative single sample = medium; sources disagree widely = review; external = low. Returns one of
    'high' | 'medium' | 'review' | 'low'."""
    if not f.get("authoritative"):
        return "low"                      # external reference, unconfirmed
    if f.get("spread") == "wide":
        return "review"                   # corpus values disagree -> needs a human check
    return "high" if (f.get("n") or 0) >= 2 else "medium"


def _spread(f):
    """Flag a filtered row whose sampled values disagree widely (high-low span > 25% of the representative). Signals a
    dimension where sources/variants differ and the reader should check which one applies. Returns '' or 'wide'."""
    try:
        lo = float(str(f.get("low")).replace(",", "")); hi = float(str(f.get("high")).replace(",", ""))
        rep = float(str(f.get("value")).replace(",", "")) or 1.0
        if hi > lo and (hi - lo) > 0.25 * abs(rep) and (f.get("n") or 0) > 1:
            return "wide"
    except Exception:
        pass
    return ""


def coverage(master_db, limit=2000):
    """Gap dashboard: for every subject in the Masterfile, how many dimension types are covered and which of the 13 are
    still MISSING (no value at all). Read-only, no links. Returns a list of
    {subject,label,n,corpus,external,missing} dicts where missing is the list of dimension types with no value."""
    dims = ("length", "area", "angle", "weight", "force", "torque", "pressure",
            "capacity", "electrical", "temperature", "flow", "speed", "rotation")
    out = []
    if not master_db or not os.path.exists(master_db):
        return out
    con = sqlite3.connect("file:%s?mode=ro" % master_db, uri=True); con.row_factory = sqlite3.Row
    subs = con.execute("SELECT DISTINCT subject, subject_label FROM master_filtered ORDER BY subject").fetchall()
    for s in subs[:limit]:
        rows = con.execute("SELECT type, origin, authoritative FROM master_filtered WHERE subject=?",
                           (s["subject"],)).fetchall()
        have = {r["type"] for r in rows}
        out.append({"subject": s["subject"], "label": s["subject_label"],
                    "n": len(have), "corpus": sum(1 for r in rows if r["authoritative"]),
                    "external": sum(1 for r in rows if not r["authoritative"]),
                    "missing": [d for d in dims if d not in have]})
    con.close()
    return out


if __name__ == "__main__":
    import tempfile
    d = tempfile.mkdtemp()
    dbp = os.path.join(d, "viewer.db"); mdb = os.path.join(d, "measures.db")
    edb = os.path.join(d, "enrich.db"); mf = os.path.join(d, "masterfile.db")
    # authoritative DB
    a = sqlite3.connect(dbp)
    a.execute("CREATE TABLE documents(id INTEGER PRIMARY KEY, vehicle TEXT)")
    a.execute("INSERT INTO documents VALUES(1,'HMMWV')"); a.commit(); a.close()
    # corpus measures: HMMWV has length + weight (authoritative)
    m = sqlite3.connect(mdb)
    m.execute("CREATE TABLE meas(doc INT,page INT,type TEXT,unit TEXT,value TEXT,value2 TEXT,tolerance TEXT,context TEXT)")
    m.executemany("INSERT INTO meas VALUES(?,?,?,?,?,?,?,?)", [
        (1, 12, "length", "in", "180", None, None, "Overall length 180 in"),
        (1, 12, "length", "in", "180", None, None, "len 180 in (dup)"),
        (1, 20, "weight", "lb", "7700", None, None, "Curb weight 7700 lb")])
    m.commit(); m.close()
    # external enrich: capacity (gap) + weight (corpus already has -> must be dropped)
    e = sqlite3.connect(edb)
    e.execute("CREATE TABLE ext_meas(subject TEXT,subject_label TEXT,type TEXT,unit TEXT,value TEXT,value2 TEXT,"
              "tolerance TEXT,context TEXT,source TEXT,source_url TEXT,orig_url TEXT,wayback_ts TEXT,fetched_ts REAL,"
              "confidence REAL,status TEXT)")
    e.executemany("INSERT INTO ext_meas(subject,subject_label,type,unit,value,context,source_url) VALUES(?,?,?,?,?,?,?)", [
        ("hmmwv", "HMMWV", "capacity", "gal", "25", "Fuel 25 gal", "http://web.archive.org/x"),
        ("hmmwv", "HMMWV", "weight", "lb", "9999", "bogus weight", "http://web.archive.org/y")])
    e.commit(); e.close()

    summ = build(dbp, mdb, edb, mf, md_path=os.path.join(d, "MASTERFILE.md"))
    print("summary:", summ)
    res = for_subject(mf, "HMMWV")
    ftypes = {(f["type"], f["origin"]) for f in res["filtered"]}
    assert ("length", "corpus") in ftypes and ("weight", "corpus") in ftypes, "corpus rows missing"
    assert ("capacity", "external") in ftypes, "external gap-fill missing"
    assert ("weight", "external") not in ftypes, "corpus-authoritative filter failed (external weight leaked)"
    # no links exposed in filtered/raw payloads
    blob = repr(res["filtered"]) + repr([{k: v for k, v in r.items() if k != "page_url"} for r in res["raw"]])
    assert "http://" not in blob and "web.archive" not in blob, "a link leaked into the Masterfile view"
    # corpus rows point to the authoritative file (internal page ref), external rows do not
    assert any(r["page_url"] for r in res["raw"] if r["origin"] == "corpus"), "corpus page ref missing"
    assert all(not r["page_url"] for r in res["raw"] if r["origin"] == "external"), "external row must have no ref"
    print("masterfile self-test OK (merge, corpus-authoritative, no links surfaced, authoritative page refs kept)")
# END OF FILE
