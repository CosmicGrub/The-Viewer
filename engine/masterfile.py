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
import os, sqlite3, statistics, time
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


def _canonical_core(counter, low, high):
    """Shared math for the representative value + numeric span, given an already-aggregated
    Counter of values and a running (low, high) numeric span (either or both may be None if no
    numeric value was seen). Both _canonical() (batch, from a raw value list) and build()'s
    streaming accumulator reduce to this one implementation -- review finding: the streaming
    rewrite (medium finding #25) originally duplicated this most_common()/min-max-formatting logic
    inline instead of sharing it, leaving _canonical() itself dead in the production path.

    Masterfile comparison audit (data-consistency finding): the representative value used to be
    Counter.most_common(1) -- the STRING mode. For continuous physical measurements this is nearly
    always "arbitrary first-seen tiebreak dressed as most common": two documents rarely produce a
    byte-identical value string (180 vs 180.5 vs 179.8 are three distinct Counter keys, each count
    1), so most_common(1) silently picked whichever document happened to be scanned/inserted first
    -- verified directly against this exact case (3 real documents, 3 real close-but-different
    lengths) before this fix: value="180" purely because doc 1 was crawled first, with a "high"
    confidence badge next to it despite the pick being uncorrelated with which value is actually
    most representative. Now: the representative value is the NUMERIC MEDIAN of every value in the
    group that parses as a number (weighted by how many rows shared that exact string -- expanded
    from `counter`, which is already retained for the non-numeric fallback below, so this doesn't
    reintroduce the O(total rows) list finding #25 specifically eliminated; it's bounded by this
    ONE group's own row count at finalization time, not the whole corpus). Falls back to the old
    mode-on-string pick only when NOTHING in the group parses as a number at all (e.g. a thread-
    size/MIL-STD callout from specparse.py, which isn't a magnitude to average in the first
    place -- median has no meaning there, mode is still the right answer)."""
    n = sum(counter.values())
    if not n:
        return "", "", "", 0
    numeric = []
    for v, c in counter.items():
        nv = _num(v)
        if nv is not None:
            numeric.extend([nv] * c)
    rep = ("%g" % statistics.median(numeric)) if numeric else counter.most_common(1)[0][0]
    low_s = ("%g" % low) if low is not None else ""
    high_s = ("%g" % high) if high is not None else ""
    return rep, low_s, high_s, n


def _canonical(vals):
    """Given a list of value strings for one (subject,type,unit,origin): representative value (most common), plus the
    numeric low/high span and the count. Returns (value, low, high, n). Kept as a public, list-based
    convenience wrapper around _canonical_core() -- build() below calls _canonical_core() directly
    against its incrementally-aggregated Counter instead of materializing a list to pass here."""
    vals = [v for v in vals if v not in (None, "")]
    counter = Counter(vals)
    nums = [x for x in (_num(v) for v in vals) if x is not None]
    low = min(nums) if nums else None
    high = max(nums) if nums else None
    return _canonical_core(counter, low, high)


def build(db_path, measures_db, enrich_db, master_db, md_path=None):
    """Consolidate corpus + external into master_db (+ optional Markdown export). Returns a summary dict.

    Medium finding #25: streams both sources directly into master_raw + an incremental (subject,
    type,unit,origin)->Counter aggregator instead of first materializing EVERY measurement row
    (including its free-text context field) into one flat Python list -- unlike build_tables.py's
    per-document streaming, this had no bound, and at 85GB/~40k-file corpus scale the accumulated
    list could grow arbitrarily large before a single byte was written. Peak Python-side memory is
    now O(distinct (subject,type,unit,origin,value) combinations feeding master_filtered), not
    O(total measurement rows) -- except transiently per-group at finalization, when a numeric
    group's distinct values are expanded back out for the median calc (_canonical_core(); bounded
    by that ONE group's own row count, not the whole corpus). Output is exactly equivalent to the
    prior list-based implementation for the null/empty-value edge case (a group whose only rows had
    val in (None,"") still yields an n=0/""/""/"" row) -- the representative-value TIE-BREAK is
    deliberately NOT preserved (see _canonical_core()'s own docstring: it's now a numeric median,
    not Counter.most_common(1)'s arbitrary first-seen pick).

    Masterfile comparison audit (architecture-alignment finding): builds into a temp file via
    safeguard.atomic_sqlite_build() and only swaps it into master_db on a clean exit -- master_db
    itself is never touched by the DROP/CREATE/INSERT sequence below, matching kg.py's build() /
    dedup.py's build() (the exact crash-safety pattern kg.py's own comments describe adopting after
    finding the same bare-DROP-then-late-commit pattern this function used to have could leave
    kg.db permanently half-written on a crash mid-build)."""
    import safeguard
    with safeguard.atomic_sqlite_build(master_db) as (con, _tmp):
        con.executescript(SCHEMA)   # CREATE TABLE IF NOT EXISTS -- the temp file starts empty, no DROP needed

        # subject label map from the authoritative DB
        # v1.13.4: v/m/e=None + finally for all three optional-source connections below -- each used to
        # close() only at the end of its try block, so an execute()/iteration throwing partway (e.g. against
        # a corrupted or partially-written measures.db/enrich.db, left mid-write by a previously killed
        # build -- exactly the scenario safeguard.py's whole premise designs around elsewhere) leaked the
        # connection, which can then block a subsequent rebuild or snapshot/replace targeting the same path.
        doc_veh = {}
        v = None
        try:
            v = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
            for did, veh in v.execute("SELECT id, COALESCE(vehicle,'') FROM documents"):
                doc_veh[did] = (veh or "").strip()
        except Exception:
            pass
        finally:
            if v is not None:
                v.close()

        raw_buf = []                       # small rolling buffer -- flushed periodically, never holds the whole corpus
        groups = defaultdict(Counter)      # (subj,ty,unit,origin) -> Counter({value: count}), None/"" never counted
        bounds = {}                        # (subj,ty,unit,origin) -> (min_numeric, max_numeric) running span
        labels = {}                        # also doubles as the distinct-subjects set (labels.keys())
        corpus_have = defaultdict(set)
        n_raw = corpus_raw = external_raw = 0
        FLUSH_AT = 2000

        def flush():
            if raw_buf:
                con.executemany(
                    "INSERT INTO master_raw(subject,subject_label,doc,page,type,unit,value,value2,tolerance,context,origin) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?)", raw_buf)
                raw_buf.clear()

        def accumulate(subj, label, doc, page, ty, unit, val, val2, tol, ctx, origin):
            nonlocal n_raw, corpus_raw, external_raw
            raw_buf.append((subj, label, doc, page, ty, unit, val, val2, tol, ctx, origin))
            if len(raw_buf) >= FLUSH_AT:
                flush()
            labels[subj] = label; n_raw += 1
            if origin == "corpus": corpus_raw += 1
            else: external_raw += 1
            key = (subj, ty, unit, origin)
            counter = groups[key]        # touch the group even for a null/empty value -- matches the
            if val not in (None, ""):    # original's unconditional groups[key].append(val) + _canonical's
                counter[val] += 1        # later filtering, so an all-null group still yields an n=0 row
                n = _num(val)
                if n is not None:
                    lo, hi = bounds.get(key, (n, n))
                    bounds[key] = (min(lo, n), max(hi, n))

        # (1) CORPUS measurements (authoritative), page-cited to the real TM files
        if measures_db and os.path.exists(measures_db):
            m = None
            try:
                m = sqlite3.connect("file:%s?mode=ro" % measures_db, uri=True)
                for doc, page, ty, unit, val, val2, tol, ctx in m.execute(
                        "SELECT doc,page,type,unit,value,value2,tolerance,context FROM meas"):
                    label = doc_veh.get(doc, "") or ("doc%s" % doc)
                    subj = label.strip().lower()
                    corpus_have[subj].add(ty)   # must be complete before the enrich loop below reads it
                    accumulate(subj, label, doc, page, ty, unit, val, val2, tol, ctx, "corpus")
            except Exception:
                pass
            finally:
                if m is not None:
                    m.close()

        # (2) EXTERNAL gap-fills (supplemental) -- NO url carried into the Masterfile; only where corpus is silent
        if enrich_db and os.path.exists(enrich_db):
            e = None
            try:
                e = sqlite3.connect("file:%s?mode=ro" % enrich_db, uri=True)
                for subj, label, ty, unit, val, val2, tol, ctx in e.execute(
                        "SELECT subject,subject_label,type,unit,value,value2,tolerance,context FROM ext_meas"):
                    subj = (subj or "").strip().lower()
                    if ty in corpus_have.get(subj, ()):   # corpus wins -> skip
                        continue
                    accumulate(subj, label or subj, None, None, ty, unit, val, val2, tol, ctx, "external")
            except Exception:
                pass
            finally:
                if e is not None:
                    e.close()

        flush()

        # FILTERED layer: one canonical row per (subject,type,unit,origin)
        filt = []
        for (subj, ty, unit, origin), counter in groups.items():
            lo, hi = bounds.get((subj, ty, unit, origin), (None, None))
            rep, low, high, n = _canonical_core(counter, lo, hi)
            auth = 1 if origin == "corpus" else 0
            note = "authoritative (corpus)" if auth else "external reference — unconfirmed"
            filt.append((subj, labels.get(subj, subj), ty, unit, rep, low, high, n, origin, auth, note))
        con.executemany(
            "INSERT INTO master_filtered(subject,subject_label,type,unit,value,low,high,n,origin,authoritative,note) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)", filt)

        meta = {"built_ts": str(time.time()), "n_subjects": str(len(labels)), "n_raw": str(n_raw),
                "n_filtered": str(len(filt)), "corpus_raw": str(corpus_raw), "external_raw": str(external_raw)}
        con.executemany("INSERT OR REPLACE INTO master_meta(k,v) VALUES(?,?)", list(meta.items()))
        con.commit()

    if md_path:
        _export_md(master_db, md_path, meta)
    return {"subjects": len(labels), "raw": n_raw, "filtered": len(filt),
            "corpus": corpus_raw, "external": external_raw}


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
    are lists of measurement rows.

    Masterfile comparison audit (architecture-alignment finding): the os.path.exists() gate below
    already matched kg.neighbors()'s/dedup.editions_for()'s "sidecar not built yet -> empty result"
    contract, but a master_db that EXISTS in a mid-build/torn state (a real reachable state before
    the atomic-write fix above) used to raise sqlite3.OperationalError straight out of this
    function, uncaught, and leak the connection -- kg.py/dedup.py both guard exactly this case
    (\"a db from before this schema existed, or mid-build -- degrade, never 500\"). Matched here too."""
    q = (q or "").strip()
    if not master_db or not os.path.exists(master_db) or len(q) < 2:
        return {"query": q, "filtered": [], "raw": [], "counts": {}}
    subj = q.lower()
    con = sqlite3.connect("file:%s?mode=ro" % master_db, uri=True); con.row_factory = sqlite3.Row
    try:
        filt = [dict(r) for r in con.execute(
            "SELECT type,unit,value,low,high,n,origin,authoritative,note,subject_label FROM master_filtered "
            "WHERE subject=? OR subject LIKE ? ORDER BY authoritative DESC, type LIMIT ?",
            (subj, "%" + subj + "%", limit))]
        raw = [dict(r) for r in con.execute(
            "SELECT type,unit,value,value2,tolerance,context,doc,page,origin FROM master_raw "
            "WHERE subject=? OR subject LIKE ? ORDER BY origin, type LIMIT ?",
            (subj, "%" + subj + "%", limit))]
    except sqlite3.OperationalError:
        return {"query": q, "filtered": [], "raw": [], "counts": {}}
    finally:
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
    # Masterfile comparison audit (architecture-alignment finding): same OperationalError/finally
    # guard as for_subject() above, for the same reason -- a mid-build/torn master_db must degrade
    # to an empty list here too, not raise/leak, matching kg.py's/dedup.py's read-side contract.
    con = sqlite3.connect("file:%s?mode=ro" % master_db, uri=True); con.row_factory = sqlite3.Row
    try:
        subs = con.execute("SELECT DISTINCT subject, subject_label FROM master_filtered ORDER BY subject").fetchall()
        for s in subs[:limit]:
            rows = con.execute("SELECT type, origin, authoritative FROM master_filtered WHERE subject=?",
                               (s["subject"],)).fetchall()
            have = {r["type"] for r in rows}
            out.append({"subject": s["subject"], "label": s["subject_label"],
                        "n": len(have), "corpus": sum(1 for r in rows if r["authoritative"]),
                        "external": sum(1 for r in rows if not r["authoritative"]),
                        "missing": [d for d in dims if d not in have]})
    except sqlite3.OperationalError:
        return []
    finally:
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
    a.executemany("INSERT INTO documents VALUES(?,?)",
                  [(1, "HMMWV"), (2, "HMMWV"), (3, "HMMWV"), (4, "HMMWV"), (5, "HMMWV")])
    a.commit(); a.close()
    # corpus measures: HMMWV has length + weight (authoritative)
    m = sqlite3.connect(mdb)
    m.execute("CREATE TABLE meas(doc INT,page INT,type TEXT,unit TEXT,value TEXT,value2 TEXT,tolerance TEXT,context TEXT)")
    m.executemany("INSERT INTO meas VALUES(?,?,?,?,?,?,?,?)", [
        (1, 12, "length", "in", "180", None, None, "Overall length 180 in"),
        (1, 12, "length", "in", "180", None, None, "len 180 in (dup)"),
        (1, 20, "weight", "lb", "7700", None, None, "Curb weight 7700 lb"),
        # torque: 4 genuinely different real values, deliberately NOT all-distinct (100 appears
        # twice) so the OLD mode-on-string pick and the NEW numeric-median pick provably diverge --
        # mode would pick "100" (count=2, the only repeated value); median of [100,100,105,200]
        # sorted is (100+105)/2 = 102.5, a real statistical center none of the four rows even states.
        (2, 5, "torque", "ft-lb", "100", None, None, "Torque 100 ft-lb (doc 2)"),
        (3, 5, "torque", "ft-lb", "100", None, None, "Torque 100 ft-lb (doc 3, repeat)"),
        (4, 5, "torque", "ft-lb", "105", None, None, "Torque 105 ft-lb (doc 4)"),
        (5, 5, "torque", "ft-lb", "200", None, None, "Torque 200 ft-lb (doc 5, outlier)")])
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
    # Masterfile comparison audit (data-consistency fix): the representative value is now a real
    # numeric median, not an arbitrary first-seen-string tiebreak -- torque's 4 rows (100,100,105,200)
    # median to 102.5, a number NONE of the 4 individual manuals even states, proving this isn't
    # just "whichever document got scanned first" (the old algorithm would have picked "100").
    torque = next(f for f in res["filtered"] if f["type"] == "torque")
    assert torque["value"] == "102.5", ("median fix regressed -- got %r, want '102.5'" % torque["value"], torque)
    assert torque["low"] == "100" and torque["high"] == "200" and torque["n"] == 4, torque
    # a group with only ONE distinct value (length: "180" x2) is unaffected -- median of a single
    # repeated value is trivially that value, same as the old mode pick would have given.
    length = next(f for f in res["filtered"] if f["type"] == "length")
    assert length["value"] == "180", length
    print("masterfile self-test OK (merge, corpus-authoritative, no links surfaced, authoritative page "
          "refs kept, numeric-median representative value)")
# END OF FILE
